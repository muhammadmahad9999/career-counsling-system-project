"""
=============================================================================
FuturePath — High Accuracy Training Pipeline
=============================================================================
Resolves low accuracy by:
1. Merging 384-dimensional Deep Learning Sentence Embeddings with tabular data.
2. Applying proper Class Balancing / Sample Weights for the 4.76x imbalance.
=============================================================================
"""

import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import lightgbm as lgb
import warnings
warnings.filterwarnings("ignore")

def main():
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_DIR = os.path.join(ROOT, "models")
    DATA_CSV = os.path.join(ROOT, "data", "TrainingReady.csv")
    
    print("=" * 60)
    print("  HIGH-ACCURACY TRAINING PIPELINE (WITH EMBEDDINGS)")
    print("=" * 60)

    # ═════════════════════════════════════════════════════════════════════════════
    # 1. Load and Merge Data
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[1/6] Loading Base Data & Embeddings...")
    df = pd.read_csv(DATA_CSV)
    y = df["Recommended_Career"].values
    
    DROP_COLS = ["Recommended_Career", "Career_Label", "Class_Weight", "Career_Roadmap_Short"]
    X_tabular = df.drop(columns=DROP_COLS).values
    tabular_cols = df.drop(columns=DROP_COLS).columns.tolist()
    
    print("      Loading Sentence Embeddings (384 dims)...")
    embeddings = np.load(os.path.join(MODEL_DIR, "embeddings_interest.npy"))
    print(f"      Tabular shape: {X_tabular.shape}, Embeddings shape: {embeddings.shape}")
    
    # Concatenate features horizontally
    X_full = np.hstack([X_tabular, embeddings])
    print(f"      Combined Features shape: {X_full.shape} (121 + 384 = 505 features)")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 2. Stratified Splitting & Scaling
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[2/6] Stratified Splitting & Scaling...")
    # Using the exact same random_state guarantees the exact same rows in each split!
    X_train_full, X_temp, y_train_full, y_temp = train_test_split(
        X_full, y, test_size=0.30, stratify=y, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=42
    )
    
    # Scale ONLY the 16 original numerical columns to preserve Embeddings and TF-IDF
    NUMERIC_COLS = [
        "Age", "Matric_Marks", "FSc_Marks",
        "Marks_Math", "Marks_Physics", "Marks_Computer", "Marks_Biology",
        "Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math",
        "Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion",
        "Psych_Agreeableness", "Psych_Neuroticism",
    ]
    numeric_indices = [tabular_cols.index(c) for c in NUMERIC_COLS if c in tabular_cols]
    
    scaler = StandardScaler()
    X_train_full[:, numeric_indices] = scaler.fit_transform(X_train_full[:, numeric_indices])
    X_val[:, numeric_indices] = scaler.transform(X_val[:, numeric_indices])
    X_test[:, numeric_indices] = scaler.transform(X_test[:, numeric_indices])
    
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    
    # Save the huge new arrays securely
    np.save(os.path.join(MODEL_DIR, "X_train.npy"), X_train_full)
    np.save(os.path.join(MODEL_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(MODEL_DIR, "X_test.npy"), X_test)
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 3. Class Balancing
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[3/6] Computing Class Balancing Weights (Fixing 4.76x Imbalance)...")
    sample_weights = compute_sample_weight(class_weight='balanced', y=y_train_full)
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 4. Initialize Models with Balancing
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[4/6] Initializing Models...")
    # Base Models - Native 'balanced' weight handling used where possible
    xgb_base = xgb.XGBClassifier(
        n_estimators=200, 
        learning_rate=0.05, 
        use_label_encoder=False, 
        eval_metric='mlogloss', 
        random_state=42,
        n_jobs=4
    )
    rf_base = RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42, n_jobs=4)
    lgbm_base = lgb.LGBMClassifier(n_estimators=200, class_weight='balanced', random_state=42, n_jobs=4, verbose=-1)

    # ═════════════════════════════════════════════════════════════════════════════
    # 5. Training
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[5/6] Training High-Accuracy Models (This will take a few minutes)...")
    
    # 1. XGBoost
    print("\n--- Training XGBoost ---")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=500,
        learning_rate=0.05,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
        n_jobs=-1
    )
    start = time.time()
    # Explicitly pass sample_weights to XGBoost
    xgb_clf.fit(X_train_full, y_train_full, sample_weight=sample_weights)
    xgb_time = time.time() - start
    xgb_val_acc = accuracy_score(y_val, xgb_clf.predict(X_val))
    print(f"      ✓ Trained in {xgb_time:.2f}s | Validation Accuracy: {xgb_val_acc:.4f}")
    joblib.dump(xgb_clf, os.path.join(MODEL_DIR, "xgboost.pkl"))

    # 2. Voting Ensemble
    print("\n--- Training Voting Ensemble ---")
    voting_clf = VotingClassifier(
        estimators=[('xgb', xgb_base), ('lgbm', lgbm_base), ('rf', rf_base)],
        voting='soft',
        n_jobs=1
    )
    start = time.time()
    # Voting/Stacking wrap the fit correctly in modern scikit-learn
    try:
        voting_clf.fit(X_train_full, y_train_full, sample_weight=sample_weights)
    except Exception as e:
        print("      Falling back to base fit for Voting:", e)
        voting_clf.fit(X_train_full, y_train_full)
    voting_time = time.time() - start
    voting_val_acc = accuracy_score(y_val, voting_clf.predict(X_val))
    print(f"      ✓ Trained in {voting_time:.2f}s | Validation Accuracy: {voting_val_acc:.4f}")
    joblib.dump(voting_clf, os.path.join(MODEL_DIR, "voting.pkl"))

    # 3. Stacking Ensemble
    print("\n--- Training Stacking Ensemble ---")
    # Meta learner also handles balanced class weight
    lr_meta = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    stacking_clf = StackingClassifier(
        estimators=[('rf', rf_base), ('xgb', xgb_base), ('lgbm', lgbm_base)],
        final_estimator=lr_meta,
        cv=3,
        n_jobs=1
    )
    start = time.time()
    try:
        stacking_clf.fit(X_train_full, y_train_full, sample_weight=sample_weights)
    except Exception as e:
        print("      Falling back to base fit for Stacking:", e)
        stacking_clf.fit(X_train_full, y_train_full)
    
    stacking_time = time.time() - start
    stacking_val_acc = accuracy_score(y_val, stacking_clf.predict(X_val))
    print(f"      ✓ Trained in {stacking_time:.2f}s | Validation Accuracy: {stacking_val_acc:.4f}")
    joblib.dump(stacking_clf, os.path.join(MODEL_DIR, "stacking.pkl"))

    # ═════════════════════════════════════════════════════════════════════════════
    # 6. Evaluation
    # ═════════════════════════════════════════════════════════════════════════════
    print("\n[6/6] Final Evaluation on Test Set...")
    xgb_test_acc = accuracy_score(y_test, xgb_clf.predict(X_test))
    voting_test_acc = accuracy_score(y_test, voting_clf.predict(X_test))
    stacking_test_acc = accuracy_score(y_test, stacking_clf.predict(X_test))

    print(f"\n      XGBoost Test Accuracy:   {xgb_test_acc:.4f}")
    print(f"      Voting Test Accuracy:    {voting_test_acc:.4f}")
    print(f"      Stacking Test Accuracy:  {stacking_test_acc:.4f}")

    report_path = os.path.join(ROOT, "reports", "model_performance.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("FuturePath - High Accuracy Performance Report\n")
        f.write("="*50 + "\n\n")
        f.write(f"1. XGBoost\n")
        f.write(f"   Validation Accuracy: {xgb_val_acc:.4f}\n")
        f.write(f"   Test Accuracy:       {xgb_test_acc:.4f}\n")
        f.write(f"   Training Time:       {xgb_time:.2f}s\n\n")
        f.write(f"2. Voting Ensemble (XGB + LGBM + RF)\n")
        f.write(f"   Validation Accuracy: {voting_val_acc:.4f}\n")
        f.write(f"   Test Accuracy:       {voting_test_acc:.4f}\n")
        f.write(f"   Training Time:       {voting_time:.2f}s\n\n")
        f.write(f"3. Stacking Ensemble\n")
        f.write(f"   Validation Accuracy: {stacking_val_acc:.4f}\n")
        f.write(f"   Test Accuracy:       {stacking_test_acc:.4f}\n")
        f.write(f"   Training Time:       {stacking_time:.2f}s\n\n")

    print(f"\n[OK] Saved performance report to {report_path}")
    print("=" * 60)
    print("  HIGH-ACCURACY TRAINING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
