"""
=============================================================================
FuturePath — New Dataset Preprocessing and Model Training Pipeline
=============================================================================
This script:
1. Loads d:/career c fyp/futurepath/data/FuturePath_Dataset_Cleaned.xlsx
2. Drops Student_ID and Gender
3. Encodes target Recommended_Career (saves label_encoder.pkl & career_label_map.pkl)
4. Casts Stream and Extracurricular_Activity to 'category' dtypes
5. Prepares feature engineered features (FSc_Percentage, Avg_Subject_Marks, etc.)
6. Splits into stratified train/test sets (80/20)
7. Trains LightGBM, XGBoost, CatBoost, RandomForest, and a Stacking Ensemble
8. Evaluates all models (Macro-F1, Accuracy, Top-3 Accuracy, and Within-stream Accuracy)
9. Saves final models and metadata to models/ directory
=============================================================================
"""

import os
import time
import joblib
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# -- paths --------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_EXCEL = os.path.join(ROOT, "data", "FuturePath_Dataset_Cleaned.xlsx")
DATA_CSV = os.path.join(ROOT, "data", "FuturePath_Dataset_Cleaned.csv")
MODEL_DIR = os.path.join(ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 42

def load_data():
    # Load from CSV if exists to speed up, otherwise read Excel and save CSV
    if os.path.exists(DATA_CSV):
        print(f"Loading data from CSV: {DATA_CSV} ...")
        df = pd.read_csv(DATA_CSV)
    else:
        print(f"Loading data from Excel: {DATA_EXCEL} (this may take a minute) ...")
        df = pd.read_excel(DATA_EXCEL)
        df.to_csv(DATA_CSV, index=False)
        print(f"Saved CSV version to {DATA_CSV} for faster future loads.")
    return df

def top_3_accuracy(y_true, y_proba):
    top3 = np.argsort(y_proba, axis=1)[:, -3:]
    correct = np.any(top3 == y_true[:, None], axis=1)
    return np.mean(correct)

def compute_metrics(y_true, y_pred, y_proba):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro")
    top3 = top_3_accuracy(y_true, y_proba)
    return acc, f1, top3

# Preprocessor for non-tree models (RandomForest and Logistic Regression)
class NonTreePreprocessor:
    def __init__(self, num_cols, cat_cols, mark_cols):
        self.num_cols = num_cols
        self.cat_cols = cat_cols
        self.mark_cols = mark_cols
        self.ohe = None
        self.scaler = None
        self.ohe_feature_names = []
        self.continuous_cols_to_scale = []
        
    def fit(self, X_train):
        # 1. Fit One-hot encoder on categorical columns
        self.ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        self.ohe.fit(X_train[self.cat_cols])
        self.ohe_feature_names = list(self.ohe.get_feature_names_out(self.cat_cols))
        
        # 2. Fit StandardScaler on numeric columns after imputation
        X_imputed = self._impute_and_flag(X_train)
        continuous_cols = [c for c in X_train.columns if c not in self.cat_cols]
        # Include the newly added binary flag columns
        self.continuous_cols_to_scale = continuous_cols + [f"Has_{col}" for col in self.mark_cols]
        
        self.scaler = StandardScaler()
        self.scaler.fit(X_imputed[self.continuous_cols_to_scale])
        
    def _impute_and_flag(self, df):
        df = df.copy()
        for col in self.mark_cols:
            df[f"Has_{col}"] = df[col].notna().astype(int)
            df[col] = df[col].fillna(-1)
        if "Avg_Subject_Marks" in df.columns:
            df["Avg_Subject_Marks"] = df["Avg_Subject_Marks"].fillna(-1)
        return df
        
    def transform(self, X):
        X_imp = self._impute_and_flag(X)
        # Scale numeric columns
        X_imp[self.continuous_cols_to_scale] = self.scaler.transform(X_imp[self.continuous_cols_to_scale])
        # One-hot encode categoricals
        X_ohe = self.ohe.transform(X[self.cat_cols])
        X_ohe_df = pd.DataFrame(X_ohe, columns=self.ohe_feature_names, index=X.index)
        # Drop categoricals and concat one-hot features
        X_final = pd.concat([X_imp.drop(columns=self.cat_cols), X_ohe_df], axis=1)
        return X_final

def main():
    print("=" * 60)
    print("  FuturePath -- Model Training and Comparison Pipeline")
    print("=" * 60)

    # 1. Load Data
    df = load_data()
    print(f"Dataset shape: {df.shape}")

    # 2. Extract Features & Target
    X = df.drop(columns=["Student_ID", "Gender", "Recommended_Career"])
    y = df["Recommended_Career"]

    # 3. Target Encoding
    print("\n[Step 2] Encoding target labels...")
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    n_classes = len(le.classes_)
    print(f"      Mapped {n_classes} recommended career paths.")
    
    # Save label encoder and career label map
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))
    career_map = {i: name for i, name in enumerate(le.classes_)}
    joblib.dump(career_map, os.path.join(MODEL_DIR, "career_label_map.pkl"))
    print("      Saved label_encoder.pkl and career_label_map.pkl")

    # 4. Handle Categorical Features & Category Mapping
    print("\n[Step 3] Handling categorical columns...")
    cat_cols = ["Stream", "Extracurricular_Activity"]
    categorical_mappings = {}
    for col in cat_cols:
        X[col] = X[col].astype("category")
        categorical_mappings[col] = list(X[col].cat.categories)
        print(f"      Column '{col}': {len(categorical_mappings[col])} categories")
    
    # Save categorical mappings for the API
    joblib.dump(categorical_mappings, os.path.join(MODEL_DIR, "categorical_mappings.pkl"))
    print("      Saved categorical_mappings.pkl")

    # 5. Feature Engineering
    print("\n[Step 6] Running feature engineering...")
    X["FSc_Percentage"] = X["FSc_Marks"] / 1100.0 * 100.0
    mark_cols = ["Marks_Biology", "Marks_Physics", "Marks_Chemistry", "Marks_Math", "Marks_Computer"]
    X["Avg_Subject_Marks"] = X[mark_cols].mean(axis=1)
    apt_cols = ["Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math"]
    X["Aptitude_Avg"] = X[apt_cols].mean(axis=1)
    riasec_cols = ["Interest_R", "Interest_I", "Interest_A", "Interest_S", "Interest_E", "Interest_C"]
    X["Top_RIASEC_Score"] = X[riasec_cols].max(axis=1)
    print(f"      Engineered 4 new features. Feature count: {X.shape[1]}")

    # 6. Stratified Split
    print("\n[Step 7] Splitting data (80/20 Stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=RANDOM_STATE
    )
    print(f"      Train set size: {X_train.shape[0]:,} samples")
    print(f"      Test set size:  {X_test.shape[0]:,} samples")

    # 7. Non-Tree Prep (For RandomForest and Logistic Regression scaling)
    print("\n[Step 4 & 5] Fitting Preprocessor for Non-Tree Models...")
    preprocessor = NonTreePreprocessor(
        num_cols=[c for c in X_train.columns if c not in cat_cols],
        cat_cols=cat_cols,
        mark_cols=mark_cols
    )
    preprocessor.fit(X_train)
    X_train_nontree = preprocessor.transform(X_train)
    X_test_nontree = preprocessor.transform(X_test)
    print(f"      Non-tree preprocessed features shape: {X_train_nontree.shape}")
    
    # Save the fitted scaler (for compatibility with the API)
    # The API expects scaler to be fitted on numeric columns
    joblib.dump(preprocessor.scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    print("      Saved scaler.pkl")

    # 8. Training Base Models
    print("\n[Training] Training Models...")

    # 1. LightGBM
    print("\n--- Training LightGBM ---")
    t0 = time.time()
    lgb_model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=n_classes,
        class_weight="balanced",
        n_estimators=150,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1
    )
    lgb_model.fit(X_train, y_train)
    lgb_time = time.time() - t0
    lgb_proba = lgb_model.predict_proba(X_test)
    lgb_pred = np.argmax(lgb_proba, axis=1)
    lgb_acc, lgb_f1, lgb_top3 = compute_metrics(y_test, lgb_pred, lgb_proba)
    print(f"      Done in {lgb_time:.2f}s | Acc: {lgb_acc:.4f} | Macro-F1: {lgb_f1:.4f} | Top-3 Acc: {lgb_top3:.4f}")

    # 2. XGBoost
    print("\n--- Training XGBoost ---")
    t0 = time.time()
    xgb_weights = compute_sample_weight(class_weight="balanced", y=y_train)
    xgb_model = xgb.XGBClassifier(
        tree_method="hist",
        enable_categorical=True,
        n_estimators=150,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric='mlogloss'
    )
    xgb_model.fit(X_train, y_train, sample_weight=xgb_weights)
    xgb_time = time.time() - t0
    xgb_proba = xgb_model.predict_proba(X_test)
    xgb_pred = np.argmax(xgb_proba, axis=1)
    xgb_acc, xgb_f1, xgb_top3 = compute_metrics(y_test, xgb_pred, xgb_proba)
    print(f"      Done in {xgb_time:.2f}s | Acc: {xgb_acc:.4f} | Macro-F1: {xgb_f1:.4f} | Top-3 Acc: {xgb_top3:.4f}")

    # 3. CatBoost
    print("\n--- Training CatBoost ---")
    t0 = time.time()
    cat_model = CatBoostClassifier(
        loss_function="MultiClass",
        cat_features=cat_cols,
        auto_class_weights="Balanced",
        iterations=60,
        depth=4,
        learning_rate=0.15,
        one_hot_max_size=30,
        thread_count=-1,
        random_state=RANDOM_STATE,
        verbose=0
    )
    cat_model.fit(X_train, y_train)
    cat_time = time.time() - t0
    cat_proba = cat_model.predict_proba(X_test)
    cat_pred = np.argmax(cat_proba, axis=1)
    cat_acc, cat_f1, cat_top3 = compute_metrics(y_test, cat_pred, cat_proba)
    print(f"      Done in {cat_time:.2f}s | Acc: {cat_acc:.4f} | Macro-F1: {cat_f1:.4f} | Top-3 Acc: {cat_top3:.4f}")

    # 4. RandomForest (needs imputation and one-hot encoding)
    print("\n--- Training RandomForest ---")
    t0 = time.time()
    rf_model = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    rf_model.fit(X_train_nontree, y_train)
    rf_time = time.time() - t0
    rf_proba = rf_model.predict_proba(X_test_nontree)
    rf_pred = np.argmax(rf_proba, axis=1)
    rf_acc, rf_f1, rf_top3 = compute_metrics(y_test, rf_pred, rf_proba)
    print(f"      Done in {rf_time:.2f}s | Acc: {rf_acc:.4f} | Macro-F1: {rf_f1:.4f} | Top-3 Acc: {rf_top3:.4f}")

    # 9. Stacking Ensemble using 5-fold OOF
    print("\n--- Training Stacking Ensemble ---")
    t0 = time.time()
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    
    n_samples = X_train.shape[0]
    oof_lgb = np.zeros((n_samples, n_classes))
    oof_xgb = np.zeros((n_samples, n_classes))
    oof_cat = np.zeros((n_samples, n_classes))
    
    print("      Generating Out-Of-Fold (OOF) predictions...")
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
        fold_X_tr, fold_X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        fold_y_tr, fold_y_val = y_train[train_idx], y_train[val_idx]
        
        # Fold LGBM
        fold_lgb = lgb.LGBMClassifier(
            objective="multiclass", num_class=n_classes, class_weight="balanced",
            n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1
        )
        fold_lgb.fit(fold_X_tr, fold_y_tr)
        oof_lgb[val_idx] = fold_lgb.predict_proba(fold_X_val)
        
        # Fold XGBoost
        fold_weights = compute_sample_weight(class_weight="balanced", y=fold_y_tr)
        fold_xgb = xgb.XGBClassifier(
            tree_method="hist", enable_categorical=True, n_estimators=100,
            random_state=RANDOM_STATE, n_jobs=-1, eval_metric="mlogloss"
        )
        fold_xgb.fit(fold_X_tr, fold_y_tr, sample_weight=fold_weights)
        oof_xgb[val_idx] = fold_xgb.predict_proba(fold_X_val)
        
        fold_cat = CatBoostClassifier(
            loss_function="MultiClass", cat_features=cat_cols, auto_class_weights="Balanced",
            iterations=40, depth=4, learning_rate=0.15, one_hot_max_size=30, thread_count=-1, random_state=RANDOM_STATE, verbose=0
        )
        fold_cat.fit(fold_X_tr, fold_y_tr)
        oof_cat[val_idx] = fold_cat.predict_proba(fold_X_val)
        print(f"        Fold {fold + 1} complete!")
        
    # Combine OOF features
    oof_features = np.hstack([oof_lgb, oof_xgb, oof_cat])
    
    # Train Logistic Regression meta-learner
    meta_learner = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)
    meta_learner.fit(oof_features, y_train)
    stack_time = time.time() - t0
    
    # Evaluate stacking on test set
    stack_test_features = np.hstack([lgb_proba, xgb_proba, cat_proba])
    stack_proba = meta_learner.predict_proba(stack_test_features)
    stack_pred = np.argmax(stack_proba, axis=1)
    stack_acc, stack_f1, stack_top3 = compute_metrics(y_test, stack_pred, stack_proba)
    print(f"      Stacking trained in {stack_time:.2f}s | Acc: {stack_acc:.4f} | Macro-F1: {stack_f1:.4f} | Top-3 Acc: {stack_top3:.4f}")

    # 10. Within-Stream Accuracy Comparison
    print("\n--- Within-Stream Accuracy Comparison ---")
    streams = X_test["Stream"].unique()
    within_stream_results = {}
    
    # Helper dictionary of models for evaluation
    eval_models = {
        "LightGBM": (lambda x: lgb_model.predict_proba(x)),
        "XGBoost": (lambda x: xgb_model.predict_proba(x)),
        "CatBoost": (lambda x: cat_model.predict_proba(x)),
        "RandomForest": (lambda x: rf_model.predict_proba(preprocessor.transform(x))),
        "Stacking": (lambda x: meta_learner.predict_proba(
            np.hstack([
                lgb_model.predict_proba(x),
                xgb_model.predict_proba(x),
                cat_model.predict_proba(x)
            ])
        ))
    }
    
    for stream in streams:
        mask = (X_test["Stream"] == stream)
        X_sub = X_test[mask]
        y_sub = y_test[mask]
        print(f"  Stream: {stream} ({len(y_sub)} samples)")
        
        within_stream_results[stream] = {}
        for name, predict_fn in eval_models.items():
            proba_sub = predict_fn(X_sub)
            pred_sub = np.argmax(proba_sub, axis=1)
            acc_sub = accuracy_score(y_sub, pred_sub)
            within_stream_results[stream][name] = acc_sub
            print(f"    * {name:15} Accuracy: {acc_sub:.4f}")

    # 11. Print Performance Summary Report
    print("\n" + "=" * 60)
    print("  MODEL PERFORMANCE REPORT")
    print("=" * 60)
    print(f"{'Model Name':25} | {'Accuracy':10} | {'Macro-F1':10} | {'Top-3 Acc':10}")
    print("-" * 60)
    print(f"{'LightGBM':25} | {lgb_acc:.4f}     | {lgb_f1:.4f}     | {lgb_top3:.4f}")
    print(f"{'XGBoost':25} | {xgb_acc:.4f}     | {xgb_f1:.4f}     | {xgb_top3:.4f}")
    print(f"{'CatBoost':25} | {cat_acc:.4f}     | {cat_f1:.4f}     | {cat_top3:.4f}")
    print(f"{'RandomForest':25} | {rf_acc:.4f}     | {rf_f1:.4f}     | {rf_top3:.4f}")
    print(f"{'Stacking Ensemble':25} | {stack_acc:.4f}     | {stack_f1:.4f}     | {stack_top3:.4f}")
    print("=" * 60)

    # 12. Save Models and Metadata
    print("\n[Saving] Saving final model artifacts...")
    
    # Save standard XGBoost model directly (so it can be used for SHAP explainer)
    joblib.dump(xgb_model, os.path.join(MODEL_DIR, "xgboost_model.pkl"))
    print("      [OK] Saved xgboost_model.pkl")

    # Save Stacking Ensemble as a dictionary of fit models + meta-learner
    stacking_data = {
        "base_estimators": {
            "lgbm": lgb_model,
            "xgb": xgb_model,
            "cat": cat_model
        },
        "meta_learner": meta_learner
    }
    joblib.dump(stacking_data, os.path.join(MODEL_DIR, "stacking_model.pkl"))
    print("      [OK] Saved stacking_model.pkl")

    # Save Voting Ensemble as a dictionary of the 3 base estimators (soft vote averages their predict_proba)
    voting_data = {
        "lgbm": lgb_model,
        "xgb": xgb_model,
        "cat": cat_model
    }
    joblib.dump(voting_data, os.path.join(MODEL_DIR, "voting_model.pkl"))
    print("      [OK] Saved voting_model.pkl")

    # Save features list
    feature_names = list(X.columns)
    joblib.dump(feature_names, os.path.join(MODEL_DIR, "feature_names.pkl"))
    print(f"      [OK] Saved feature_names.pkl ({len(feature_names)} features)")

    # Save Split Info
    split_info = {
        "train_size": X_train.shape[0],
        "test_size":  X_test.shape[0],
        "n_features": X_train.shape[1],
        "n_classes":  n_classes,
        "random_state": RANDOM_STATE,
    }
    joblib.dump(split_info, os.path.join(MODEL_DIR, "split_info.pkl"))
    print("      [OK] Saved split_info.pkl")

    # Write summary text file
    report_path = os.path.join(ROOT, "reports", "model_performance.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("FuturePath — Model Performance Report (New Dataset)\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Dataset File: {DATA_EXCEL}\n")
        f.write(f"Features:     {len(feature_names)} features\n")
        f.write(f"Classes:      {n_classes} careers\n\n")
        f.write("--- Metrics Table ---\n")
        f.write(f"{'Model Name':25} | {'Accuracy':10} | {'Macro-F1':10} | {'Top-3 Acc':10}\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'LightGBM':25} | {lgb_acc:.4f}     | {lgb_f1:.4f}     | {lgb_top3:.4f}\n")
        f.write(f"{'XGBoost':25} | {xgb_acc:.4f}     | {xgb_f1:.4f}     | {xgb_top3:.4f}\n")
        f.write(f"{'CatBoost':25} | {cat_acc:.4f}     | {cat_f1:.4f}     | {cat_top3:.4f}\n")
        f.write(f"{'RandomForest':25} | {rf_acc:.4f}     | {rf_f1:.4f}     | {rf_top3:.4f}\n")
        f.write(f"{'Stacking Ensemble':25} | {stack_acc:.4f}     | {stack_f1:.4f}     | {stack_top3:.4f}\n\n")
        
        f.write("--- Within-Stream Accuracy ---\n")
        for stream, res in within_stream_results.items():
            f.write(f"Stream: {stream}\n")
            for model_name, val in res.items():
                f.write(f"  * {model_name:15} : {val:.4f}\n")
            f.write("\n")
            
    print(f"\n[OK] Saved final text performance report to {report_path}")
    print("=" * 60)
    print("  PREPROCESSING AND TRAINING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
