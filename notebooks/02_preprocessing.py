"""
=============================================================================
FuturePath -- Data Preprocessing Pipeline
=============================================================================
1. Load TrainingReady.csv
2. Drop leaky columns (Career_Roadmap_Short, Career_Label, Class_Weight)
3. Stratified train / val / test split (70 / 15 / 15)
4. StandardScaler on 15 numeric columns only (not TF-IDF / one-hot)
5. Generate sentence embeddings from Interest_Text using
   paraphrase-multilingual-MiniLM-L12-v2 (384 dims)
6. Save all artefacts to models/

Run from project root:  python notebooks/02_preprocessing.py
=============================================================================
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# -- paths --------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_CSV  = os.path.join(ROOT, "data", "TrainingReady.csv")
HR_CSV     = os.path.join(ROOT, "data", "HumanReadable.csv")
MODEL_DIR  = os.path.join(ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 42

# =============================================================================
# 1. Load training-ready data
# =============================================================================
print("=" * 60)
print("  FuturePath -- Preprocessing Pipeline")
print("=" * 60)

print("\n[1/6] Loading TrainingReady.csv …")
df = pd.read_csv(TRAIN_CSV)
print(f"      Shape: {df.shape}")
print(f"      Columns: {len(df.columns)}")
print(f"      Target classes: {df['Recommended_Career'].nunique()}")

# =============================================================================
# 2. Prepare features and target
# =============================================================================
print("\n[2/6] Preparing features & target …")

# Target
y = df["Recommended_Career"].values
career_labels = df["Career_Label"].values  # keep for reference

# Drop target + leaky / meta columns
DROP_COLS = ["Recommended_Career", "Career_Label", "Class_Weight", "Career_Roadmap_Short"]
X = df.drop(columns=DROP_COLS)

print(f"      Features (X): {X.shape}")
print(f"      Target  (y): {y.shape}  -- {len(np.unique(y))} classes")

# Save class weights for later use during training
class_weights = df.groupby("Recommended_Career")["Class_Weight"].first().to_dict()
joblib.dump(class_weights, os.path.join(MODEL_DIR, "class_weights.pkl"))
print("      [OK] Saved class_weights.pkl")

# Save career label mapping
career_map = df.groupby("Recommended_Career")["Career_Label"].first().to_dict()
joblib.dump(career_map, os.path.join(MODEL_DIR, "career_label_map.pkl"))
print("      [OK] Saved career_label_map.pkl")

# =============================================================================
# 3. Stratified train / val / test split  (70 / 15 / 15)
# =============================================================================
print("\n[3/6] Stratified splitting (70/15/15) …")

X_train_full, X_temp, y_train_full, y_temp = train_test_split(
    X, y, test_size=0.30, stratify=y, random_state=RANDOM_STATE
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=RANDOM_STATE
)

print(f"      Train : {X_train_full.shape[0]:,} samples  ({X_train_full.shape[0]/len(y)*100:.1f}%)")
print(f"      Val   : {X_val.shape[0]:,} samples  ({X_val.shape[0]/len(y)*100:.1f}%)")
print(f"      Test  : {X_test.shape[0]:,} samples  ({X_test.shape[0]/len(y)*100:.1f}%)")

# Verify stratification
from collections import Counter
train_dist = Counter(y_train_full)
test_dist  = Counter(y_test)
print(f"      Stratification check -- train min/max: {min(train_dist.values())}/{max(train_dist.values())}")

# =============================================================================
# 4. StandardScaler on numeric columns ONLY
# =============================================================================
print("\n[4/6] Standard-scaling 15 numeric columns …")

NUMERIC_COLS = [
    "Age", "Matric_Marks", "FSc_Marks",
    "Marks_Math", "Marks_Physics", "Marks_Computer", "Marks_Biology",
    "Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math",
    "Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion",
    "Psych_Agreeableness", "Psych_Neuroticism",
]

# Validate all numeric cols exist
missing = [c for c in NUMERIC_COLS if c not in X_train_full.columns]
if missing:
    # Age might be named differently; adapt
    print(f"      [WARN] Missing cols (will skip): {missing}")
    NUMERIC_COLS = [c for c in NUMERIC_COLS if c in X_train_full.columns]

scaler = StandardScaler()
X_train_full[NUMERIC_COLS] = scaler.fit_transform(X_train_full[NUMERIC_COLS])
X_val[NUMERIC_COLS]        = scaler.transform(X_val[NUMERIC_COLS])
X_test[NUMERIC_COLS]       = scaler.transform(X_test[NUMERIC_COLS])

joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
print(f"      Scaled {len(NUMERIC_COLS)} columns: {NUMERIC_COLS}")
print("      [OK] Saved scaler.pkl")

# =============================================================================
# 5. Sentence embeddings from Interest_Text (deep learning branch)
# =============================================================================
print("\n[5/6] Generating sentence embeddings (paraphrase-multilingual-MiniLM-L12-v2) …")
print("      This may take a few minutes on first run (model download) …")

try:
    from sentence_transformers import SentenceTransformer

    # Load the human-readable CSV to get Interest_Text
    df_hr = pd.read_csv(HR_CSV)
    interest_texts = df_hr["Interest_Text"].fillna("").tolist()

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    st_model = SentenceTransformer(model_name)

    print(f"      Encoding {len(interest_texts):,} texts with {model_name} …")
    embeddings = st_model.encode(
        interest_texts,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    print(f"      Embedding shape: {embeddings.shape}")  # (50000, 384)
    np.save(os.path.join(MODEL_DIR, "embeddings_interest.npy"), embeddings)
    print("      [OK] Saved embeddings_interest.npy")

except ImportError:
    print("      [WARN] sentence-transformers not installed -- skipping embeddings")
    print("        Install with: pip install sentence-transformers")
except Exception as e:
    print(f"      [WARN] Error generating embeddings: {e}")

# =============================================================================
# 6. Save processed splits
# =============================================================================
print("\n[6/6] Saving processed splits …")

# Save as numpy arrays for fast loading during training
np.save(os.path.join(MODEL_DIR, "X_train.npy"), X_train_full.values)
np.save(os.path.join(MODEL_DIR, "X_val.npy"),   X_val.values)
np.save(os.path.join(MODEL_DIR, "X_test.npy"),  X_test.values)
np.save(os.path.join(MODEL_DIR, "y_train.npy"), y_train_full)
np.save(os.path.join(MODEL_DIR, "y_val.npy"),   y_val)
np.save(os.path.join(MODEL_DIR, "y_test.npy"),  y_test)

# Also save feature names for later reference
feature_names = X_train_full.columns.tolist()
joblib.dump(feature_names, os.path.join(MODEL_DIR, "feature_names.pkl"))

# Save split indices for reproducibility
split_info = {
    "train_size": X_train_full.shape[0],
    "val_size":   X_val.shape[0],
    "test_size":  X_test.shape[0],
    "n_features": X_train_full.shape[1],
    "n_classes":  len(np.unique(y)),
    "numeric_cols": NUMERIC_COLS,
    "random_state": RANDOM_STATE,
}
joblib.dump(split_info, os.path.join(MODEL_DIR, "split_info.pkl"))

print(f"      [OK] Saved X_train.npy  ({X_train_full.shape})")
print(f"      [OK] Saved X_val.npy    ({X_val.shape})")
print(f"      [OK] Saved X_test.npy   ({X_test.shape})")
print(f"      [OK] Saved y_train.npy  ({y_train_full.shape})")
print(f"      [OK] Saved y_val.npy    ({y_val.shape})")
print(f"      [OK] Saved y_test.npy   ({y_test.shape})")
print(f"      [OK] Saved feature_names.pkl  ({len(feature_names)} features)")
print(f"      [OK] Saved split_info.pkl")

# -- summary ------------------------------------------------------------------
print("\n" + "=" * 60)
print("  PREPROCESSING COMPLETE")
print("=" * 60)
print(f"  Files saved to: {MODEL_DIR}")
for f in sorted(os.listdir(MODEL_DIR)):
    size = os.path.getsize(os.path.join(MODEL_DIR, f))
    print(f"    * {f}  ({size / 1024:.0f} KB)")
print("=" * 60)
