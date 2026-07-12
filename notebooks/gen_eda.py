import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(src): return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)

# ── SECTION 0 – Title ────────────────────────────────────────────────
cells.append(md("""# 📊 FuturePath Dataset – Full EDA & Data Quality Notebook
> **Dataset:** 50,000 Pakistani students | 26 columns  
> **Covers:** Data Quality → Cleaning → Univariate → Bivariate → Multivariate → Preprocessing → Splitting
"""))

# ── SECTION 1 – Imports & Load ───────────────────────────────────────
cells.append(md("## 1. 📦 Imports & Load Data"))
cells.append(code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# Plot style
sns.set_theme(style='darkgrid', palette='muted')
plt.rcParams['figure.dpi'] = 100
plt.rcParams['font.size'] = 11
"""))

cells.append(code("""\
df = pd.read_csv('../data/HumanReadable.csv')
print(f"Shape: {df.shape}")
df.head()
"""))

# ── SECTION 2 – Data Quality Report ──────────────────────────────────
cells.append(md("## 2. 🔍 Data Quality Report"))

cells.append(code("""\
# Quick overview
print("=" * 50)
print(f"Rows     : {df.shape[0]:,}")
print(f"Columns  : {df.shape[1]}")
print(f"Duplicates: {df.duplicated().sum()}")
print(f"Total Missing: {df.isnull().sum().sum()}")
print("=" * 50)
df.info()
"""))

cells.append(code("""\
# Missing values summary table
missing = pd.DataFrame({
    'Missing Count': df.isnull().sum(),
    'Missing %': (df.isnull().sum() / len(df) * 100).round(2),
    'Dtype': df.dtypes
})
missing[missing['Missing Count'] > 0] if missing['Missing Count'].sum() > 0 else print("✅ No missing values found!")
"""))

cells.append(code("""\
# Data types breakdown
type_counts = df.dtypes.value_counts()
fig, ax = plt.subplots(figsize=(6, 4))
type_counts.plot(kind='bar', ax=ax, color=['#4C72B0','#DD8452','#55A868'], edgecolor='white', width=0.5)
ax.set_title('Column Data Types Breakdown', fontweight='bold')
ax.set_xlabel('Data Type'); ax.set_ylabel('Count')
for bar in ax.patches:
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
            int(bar.get_height()), ha='center', va='bottom', fontweight='bold')
plt.xticks(rotation=0); plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Unique values per column
uniq = df.nunique().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 5))
uniq.plot(kind='bar', ax=ax, color='#4C72B0', edgecolor='white')
ax.set_title('Unique Values per Column', fontweight='bold')
ax.set_ylabel('Unique Count'); ax.set_xlabel('')
plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""))

# ── SECTION 3 – Data Cleaning ────────────────────────────────────────
cells.append(md("## 3. 🧹 Data Cleaning"))

cells.append(md("### 3.1 Deduplication"))
cells.append(code("""\
before = len(df)
df = df.drop_duplicates()
after = len(df)
print(f"Rows before: {before:,} | Rows after: {after:,} | Removed: {before - after}")
"""))

cells.append(md("### 3.2 Handle Missing Values"))
cells.append(code("""\
num_cols  = df.select_dtypes(include=np.number).columns.tolist()
cat_cols  = df.select_dtypes(include='object').columns.tolist()

# Fill numerics with median
for col in num_cols:
    df[col].fillna(df[col].median(), inplace=True)

# Fill categoricals with mode
for col in cat_cols:
    df[col].fillna(df[col].mode()[0], inplace=True)

print("Missing after cleaning:", df.isnull().sum().sum())
"""))

cells.append(md("### 3.3 Fix Structural Errors – Standardize Text"))
cells.append(code("""\
# Columns that should be clean categorical labels
label_cols = ['Gender', 'City', 'Stream', 'Sentiment_Label', 'Extracurricular_Activity']
for col in label_cols:
    df[col] = df[col].astype(str).str.strip().str.title()

print("Sample after standardisation:")
df[label_cols].head(3)
"""))

cells.append(md("### 3.4 Outlier Detection & Capping (IQR Method)"))
cells.append(code("""\
marks_cols = ['Matric_Marks','FSc_Marks','Marks_Math','Marks_Physics','Marks_Computer','Marks_Biology']

fig, axes = plt.subplots(2, 3, figsize=(14, 6))
for ax, col in zip(axes.flat, marks_cols):
    sns.boxplot(y=df[col], ax=ax, color='#4C72B0')
    ax.set_title(col, fontsize=10)
fig.suptitle('Outlier Detection – Marks Columns (Boxplots)', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Cap outliers using 1st – 99th percentile
outlier_cols = num_cols.copy()
outlier_cols.remove('Student_ID')

clipped = 0
for col in outlier_cols:
    lo = df[col].quantile(0.01)
    hi = df[col].quantile(0.99)
    before = ((df[col] < lo) | (df[col] > hi)).sum()
    df[col] = df[col].clip(lo, hi)
    clipped += before

print(f"Total outlier values capped: {clipped:,}")
"""))

# ── SECTION 4 – Univariate Analysis ──────────────────────────────────
cells.append(md("## 4. 📊 Univariate Analysis"))

cells.append(md("### 4.1 Numeric Distributions"))
cells.append(code("""\
plot_cols = ['Age','Matric_Marks','FSc_Marks','Marks_Math','Marks_Physics',
             'Marks_Computer','Marks_Biology','Aptitude_Logic','Aptitude_Verbal']

fig, axes = plt.subplots(3, 3, figsize=(15, 10))
for ax, col in zip(axes.flat, plot_cols):
    sns.histplot(df[col], bins=25, kde=True, ax=ax, color='#4C72B0', edgecolor='white')
    ax.set_title(col, fontsize=10)
    ax.set_xlabel(''); ax.set_ylabel('')
fig.suptitle('Numeric Feature Distributions', fontweight='bold', fontsize=14)
plt.tight_layout(); plt.show()
"""))

cells.append(md("### 4.2 Personality Traits Distribution"))
cells.append(code("""\
psych_cols = ['Psych_Openness','Psych_Conscientiousness','Psych_Extraversion',
              'Psych_Agreeableness','Psych_Neuroticism']

fig, axes = plt.subplots(1, 5, figsize=(18, 4))
colors = ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B3']
for ax, col, c in zip(axes, psych_cols, colors):
    sns.violinplot(y=df[col], ax=ax, color=c)
    ax.set_title(col.replace('Psych_',''), fontsize=9)
fig.suptitle('Personality Traits – Violin Plots', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(md("### 4.3 Categorical Feature Distributions"))
cells.append(code("""\
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

for ax, col in zip(axes, ['Gender','Stream','Sentiment_Label']):
    counts = df[col].value_counts()
    ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=90,
           colors=sns.color_palette('muted', len(counts)))
    ax.set_title(col, fontweight='bold')

plt.suptitle('Categorical Feature Proportions', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# City distribution
city_counts = df['City'].value_counts()
fig, ax = plt.subplots(figsize=(12, 4))
sns.barplot(x=city_counts.index, y=city_counts.values, palette='muted', ax=ax)
ax.set_title('Student Distribution by City', fontweight='bold')
ax.set_xlabel('City'); ax.set_ylabel('Count')
for bar in ax.patches:
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+20,
            f'{int(bar.get_height()):,}', ha='center', va='bottom', fontsize=9)
plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Top 15 Recommended Careers
top_careers = df['Recommended_Career'].value_counts().head(15)
fig, ax = plt.subplots(figsize=(12, 5))
sns.barplot(x=top_careers.values, y=top_careers.index, palette='viridis', ax=ax)
ax.set_title('Top 15 Recommended Careers', fontweight='bold')
ax.set_xlabel('Count'); ax.set_ylabel('')
plt.tight_layout(); plt.show()
"""))

# ── SECTION 5 – Bivariate Analysis ───────────────────────────────────
cells.append(md("## 5. 🔗 Bivariate Analysis"))

cells.append(code("""\
# Matric vs FSc marks scatter
fig, ax = plt.subplots(figsize=(7, 5))
scatter = ax.scatter(df['Matric_Marks'], df['FSc_Marks'],
                     c=df['Age'], cmap='viridis', alpha=0.3, s=5)
plt.colorbar(scatter, ax=ax, label='Age')
ax.set_title('Matric Marks vs FSc Marks (coloured by Age)', fontweight='bold')
ax.set_xlabel('Matric Marks'); ax.set_ylabel('FSc Marks')
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Marks by Stream
marks_stream = ['Matric_Marks','FSc_Marks','Marks_Math','Marks_Physics']
fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, col in zip(axes, marks_stream):
    sns.boxplot(data=df, x='Stream', y=col, ax=ax, palette='muted')
    ax.set_title(col, fontsize=10)
    ax.set_xlabel(''); plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
fig.suptitle('Marks by Stream', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Aptitude scores by Gender
apt_cols = ['Aptitude_Logic','Aptitude_Verbal','Aptitude_Spatial','Aptitude_Math']
fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, col in zip(axes, apt_cols):
    sns.boxplot(data=df, x='Gender', y=col, palette=['#DD8452','#4C72B0'], ax=ax)
    ax.set_title(col.replace('Aptitude_',''), fontsize=10)
fig.suptitle('Aptitude Scores by Gender', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Sentiment distribution per Stream
ct = pd.crosstab(df['Stream'], df['Sentiment_Label'], normalize='index') * 100
ct.plot(kind='bar', figsize=(10, 4), colormap='Set2', edgecolor='white')
plt.title('Sentiment Distribution by Stream (%)', fontweight='bold')
plt.xlabel('Stream'); plt.ylabel('Percentage')
plt.legend(title='Sentiment', bbox_to_anchor=(1,1))
plt.xticks(rotation=0); plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Average Matric & FSc marks per City
city_marks = df.groupby('City')[['Matric_Marks','FSc_Marks']].mean().sort_values('Matric_Marks', ascending=False)
city_marks.plot(kind='bar', figsize=(12, 4), colormap='viridis', edgecolor='white')
plt.title('Average Matric & FSc Marks by City', fontweight='bold')
plt.ylabel('Average Marks'); plt.xticks(rotation=45, ha='right')
plt.legend(loc='lower right'); plt.tight_layout(); plt.show()
"""))

# ── SECTION 6 – Multivariate Analysis ────────────────────────────────
cells.append(md("## 6. 🌐 Multivariate Analysis"))

cells.append(code("""\
# Correlation heatmap – numeric features
corr_cols = ['Age','Matric_Marks','FSc_Marks','Marks_Math','Marks_Physics',
             'Marks_Computer','Marks_Biology','Aptitude_Logic','Aptitude_Verbal',
             'Aptitude_Spatial','Aptitude_Math']
corr = df[corr_cols].corr()

fig, ax = plt.subplots(figsize=(11, 8))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='coolwarm',
            center=0, linewidths=0.5, ax=ax, annot_kws={'size': 8})
ax.set_title('Correlation Heatmap (Lower Triangle)', fontweight='bold', fontsize=13)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Personality traits correlation
psych_cols = ['Psych_Openness','Psych_Conscientiousness','Psych_Extraversion',
              'Psych_Agreeableness','Psych_Neuroticism']
psych_corr = df[psych_cols].corr()

fig, ax = plt.subplots(figsize=(7, 5))
sns.heatmap(psych_corr, annot=True, fmt='.2f', cmap='PuOr', center=0,
            linewidths=0.5, ax=ax)
ax.set_title('Personality Traits Correlation', fontweight='bold')
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Pairplot – Aptitude scores coloured by Sentiment
sample = df[['Aptitude_Logic','Aptitude_Verbal','Aptitude_Spatial','Aptitude_Math','Sentiment_Label']].sample(2000, random_state=42)
g = sns.pairplot(sample, hue='Sentiment_Label', diag_kind='kde',
                 plot_kws={'alpha': 0.4, 's': 15}, palette='muted')
g.fig.suptitle('Pairplot – Aptitude Scores by Sentiment', y=1.02, fontweight='bold')
plt.show()
"""))

cells.append(code("""\
# Heatmap – avg Math marks by City × Stream
pivot = df.pivot_table(values='Marks_Math', index='City', columns='Stream', aggfunc='mean')
fig, ax = plt.subplots(figsize=(10, 7))
sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlGnBu', linewidths=0.5, ax=ax)
ax.set_title('Average Math Marks – City × Stream', fontweight='bold')
plt.tight_layout(); plt.show()
"""))

# ── SECTION 7 – Statistical Summary ──────────────────────────────────
cells.append(md("## 7. 📋 Statistical Summary"))

cells.append(code("""\
print("--- Descriptive Statistics (Numeric) ---")
df[corr_cols].describe().round(2)
"""))

cells.append(code("""\
print("--- Skewness ---")
print(df[corr_cols].skew().sort_values(ascending=False).round(3))
print()
print("--- Kurtosis ---")
print(df[corr_cols].kurtosis().sort_values(ascending=False).round(3))
"""))

# ── SECTION 8 – Preprocessing ────────────────────────────────────────
cells.append(md("## 8. ⚙️ Data Preprocessing & Transformation"))

cells.append(md("### 8.1 Feature Encoding"))
cells.append(code("""\
df_proc = df.copy()
encode_cols = ['Gender', 'City', 'Stream', 'Sentiment_Label',
               'Extracurricular_Activity', 'Recommended_Career']

le = LabelEncoder()
for col in encode_cols:
    df_proc[col] = le.fit_transform(df_proc[col].astype(str))

# Drop text columns not needed for ML
df_proc.drop(columns=['Interest_Text','Chat_Message','Career_Roadmap_Short'], inplace=True)
print("Encoding done. Shape:", df_proc.shape)
df_proc.head(3)
"""))

cells.append(md("### 8.2 Feature Scaling"))
cells.append(code("""\
scale_cols = ['Matric_Marks','FSc_Marks','Marks_Math','Marks_Physics',
              'Marks_Computer','Marks_Biology','Aptitude_Logic','Aptitude_Verbal',
              'Aptitude_Spatial','Aptitude_Math','Psych_Openness',
              'Psych_Conscientiousness','Psych_Extraversion','Psych_Agreeableness',
              'Psych_Neuroticism']

scaler = StandardScaler()
df_proc[scale_cols] = scaler.fit_transform(df_proc[scale_cols])
print("Scaling done.")
df_proc[scale_cols].describe().round(2)
"""))

cells.append(md("### 8.3 Feature Engineering"))
cells.append(code("""\
# Total Academic Score
df_proc['Total_Academic'] = (df['Matric_Marks'] + df['FSc_Marks']) / 2

# Average Aptitude Score
apt = ['Aptitude_Logic','Aptitude_Verbal','Aptitude_Spatial','Aptitude_Math']
df_proc['Avg_Aptitude'] = df[apt].mean(axis=1)

# Average Personality Score
psych = ['Psych_Openness','Psych_Conscientiousness','Psych_Extraversion',
         'Psych_Agreeableness','Psych_Neuroticism']
df_proc['Avg_Psych'] = df[psych].mean(axis=1)

print("New engineered features: Total_Academic, Avg_Aptitude, Avg_Psych")
df_proc[['Total_Academic','Avg_Aptitude','Avg_Psych']].describe().round(2)
"""))

cells.append(code("""\
# Visualise new features
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for ax, col in zip(axes, ['Total_Academic','Avg_Aptitude','Avg_Psych']):
    sns.histplot(df_proc[col], bins=30, kde=True, ax=ax, color='#55A868', edgecolor='white')
    ax.set_title(col, fontweight='bold')
plt.suptitle('Engineered Feature Distributions', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.show()
"""))

cells.append(md("### 8.4 Dimensionality Reduction (PCA)"))
cells.append(code("""\
pca_input = df_proc[scale_cols].values
pca = PCA(n_components=2, random_state=42)
pca_result = pca.fit_transform(pca_input)

print(f"Explained Variance (PC1): {pca.explained_variance_ratio_[0]*100:.1f}%")
print(f"Explained Variance (PC2): {pca.explained_variance_ratio_[1]*100:.1f}%")
print(f"Total Explained         : {sum(pca.explained_variance_ratio_)*100:.1f}%")
"""))

cells.append(code("""\
fig, ax = plt.subplots(figsize=(8, 5))
scatter = ax.scatter(pca_result[:,0], pca_result[:,1],
                     c=df_proc['Recommended_Career'], cmap='tab20',
                     alpha=0.3, s=5)
ax.set_title('PCA – 2D Projection of All Numeric Features', fontweight='bold')
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Explained variance curve
pca_full = PCA(random_state=42).fit(pca_input)
cumvar = np.cumsum(pca_full.explained_variance_ratio_) * 100

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(cumvar, color='#4C72B0', linewidth=2)
ax.axhline(95, color='red', linestyle='--', label='95% threshold')
ax.set_title('PCA – Cumulative Explained Variance', fontweight='bold')
ax.set_xlabel('Number of Components'); ax.set_ylabel('Cumulative Variance %')
ax.legend(); plt.tight_layout(); plt.show()
"""))

# ── SECTION 9 – Train-Test Split ─────────────────────────────────────
cells.append(md("## 9. ✂️ Data Splitting (Train / Validation / Test)"))

cells.append(code("""\
X = df_proc.drop(columns=['Student_ID','Recommended_Career'])
y = df_proc['Recommended_Career']

# 70 / 15 / 15 split
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
X_val,   X_test, y_val,   y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)

print(f"Training set   : {X_train.shape[0]:>7,} rows ({X_train.shape[0]/len(X)*100:.1f}%)")
print(f"Validation set : {X_val.shape[0]:>7,} rows ({X_val.shape[0]/len(X)*100:.1f}%)")
print(f"Test set       : {X_test.shape[0]:>7,} rows ({X_test.shape[0]/len(X)*100:.1f}%)")
print(f"Features       : {X_train.shape[1]}")
"""))

cells.append(code("""\
# Visual – split proportions
sizes = [len(X_train), len(X_val), len(X_test)]
labels = [f'Train\\n{sizes[0]:,}', f'Validation\\n{sizes[1]:,}', f'Test\\n{sizes[2]:,}']
colors_pie = ['#4C72B0','#DD8452','#55A868']

fig, ax = plt.subplots(figsize=(6, 4))
ax.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%',
       startangle=90, wedgeprops={'edgecolor':'white','linewidth':2})
ax.set_title('Train / Validation / Test Split', fontweight='bold')
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Class balance check – are all career classes represented?
train_dist = y_train.value_counts(normalize=True)
test_dist  = y_test.value_counts(normalize=True)

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
train_dist.plot(kind='bar', ax=axes[0], color='#4C72B0', edgecolor='white')
axes[0].set_title('Class Distribution – Training Set', fontweight='bold')
axes[0].set_ylabel('Proportion'); axes[0].set_xlabel('')

test_dist.plot(kind='bar', ax=axes[1], color='#55A868', edgecolor='white')
axes[1].set_title('Class Distribution – Test Set', fontweight='bold')
axes[1].set_ylabel('Proportion'); axes[1].set_xlabel('')

plt.setp(axes[0].get_xticklabels(), rotation=45, ha='right', fontsize=7)
plt.setp(axes[1].get_xticklabels(), rotation=45, ha='right', fontsize=7)
plt.tight_layout(); plt.show()
print("✅ Stratified split ensures balanced class proportions.")
"""))

cells.append(md("""\
## ✅ Summary

| Step | Status |
|------|--------|
| Data Quality Report | ✅ Done |
| Deduplication | ✅ Done |
| Missing Value Handling | ✅ Done |
| Structural Error Fixing | ✅ Done |
| Outlier Detection & Capping | ✅ Done |
| Univariate Analysis | ✅ Done |
| Bivariate Analysis | ✅ Done |
| Multivariate Analysis | ✅ Done |
| Feature Encoding | ✅ Done |
| Feature Scaling | ✅ Done |
| Feature Engineering | ✅ Done |
| Dimensionality Reduction (PCA) | ✅ Done |
| Train / Val / Test Split | ✅ Done |

> Model training is intentionally **not included** in this notebook.
"""))

nb.cells = cells

import os
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eda.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"Notebook written to: {out_path}")
