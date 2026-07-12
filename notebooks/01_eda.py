"""
=============================================================================
FuturePath -- Exploratory Data Analysis (EDA)
=============================================================================
Generates all dissertation-grade plots and saves them to reports/eda/
Run from the project root:  python notebooks/01_eda.py
=============================================================================
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")                       # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter

# -- paths --------------------------------------------------------------------
ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(ROOT, "data", "HumanReadable.csv")
OUTDIR = os.path.join(ROOT, "reports", "eda")
os.makedirs(OUTDIR, exist_ok=True)

# -- global styling -----------------------------------------------------------
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
})
sns.set_style("whitegrid")
PALETTE = sns.color_palette("coolwarm", 38)

# -- load ---------------------------------------------------------------------
print("[1/9] Loading dataset …")
df = pd.read_csv(DATA)
print(f"      Shape: {df.shape}  |  Careers: {df['Recommended_Career'].nunique()}")
print(f"      Streams: {df['Stream'].unique().tolist()}")

# -- numeric columns ---------------------------------------------------------
NUMERIC_COLS = [
    "Age", "Matric_Marks", "FSc_Marks",
    "Marks_Math", "Marks_Physics", "Marks_Computer", "Marks_Biology",
    "Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math",
    "Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion",
    "Psych_Agreeableness", "Psych_Neuroticism",
]

# =============================================================================
# 1. Distribution histograms -- every numeric column
# =============================================================================
print("[2/9] Distribution histograms …")
fig, axes = plt.subplots(4, 4, figsize=(20, 14))
axes = axes.ravel()
colors = sns.color_palette("viridis", len(NUMERIC_COLS))

for i, col in enumerate(NUMERIC_COLS):
    ax = axes[i]
    ax.hist(df[col].dropna(), bins=25, color=colors[i], edgecolor="white", alpha=0.85)
    ax.set_title(col, fontweight="bold")
    ax.set_ylabel("Count")
    # add skew annotation
    skew_val = df[col].skew()
    ax.annotate(f"skew={skew_val:.2f}", xy=(0.72, 0.88), xycoords="axes fraction",
                fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

# hide any unused axes
for j in range(len(NUMERIC_COLS), len(axes)):
    axes[j].set_visible(False)

fig.suptitle("Distribution of All Numeric Features", fontsize=18, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "01_numeric_distributions.png"), bbox_inches="tight")
plt.close(fig)
print("      [OK] Saved 01_numeric_distributions.png")

# =============================================================================
# 2. Class distribution bar chart -- 38 careers sorted by count
# =============================================================================
print("[3/9] Class distribution bar chart …")
career_counts = df["Recommended_Career"].value_counts()
imbalance_ratio = career_counts.iloc[0] / career_counts.iloc[-1]

fig, ax = plt.subplots(figsize=(12, 14))
colors_bar = sns.color_palette("RdYlGn_r", len(career_counts))
bars = ax.barh(career_counts.index[::-1], career_counts.values[::-1], color=colors_bar[::-1],
               edgecolor="white", linewidth=0.5)

# annotate counts on bars
for bar, val in zip(bars, career_counts.values[::-1]):
    ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", fontsize=9, fontweight="bold")

ax.set_xlabel("Number of Samples", fontsize=13)
ax.set_title(f"Career Class Distribution  (Imbalance Ratio: {imbalance_ratio:.2f}x)",
             fontsize=16, fontweight="bold")
ax.axvline(career_counts.mean(), color="red", linestyle="--", linewidth=1.5, label=f"Mean = {career_counts.mean():.0f}")
ax.legend(fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "02_class_distribution.png"), bbox_inches="tight")
plt.close(fig)
print(f"      [OK] Saved 02_class_distribution.png  (imbalance {imbalance_ratio:.2f}x)")

# =============================================================================
# 3. Correlation heatmap -- 15 numeric features
# =============================================================================
print("[4/9] Correlation heatmap …")
corr = df[NUMERIC_COLS].corr()

fig, ax = plt.subplots(figsize=(16, 13))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
cmap = sns.diverging_palette(240, 10, as_cmap=True)
sns.heatmap(corr, mask=mask, cmap=cmap, center=0, vmin=-1, vmax=1,
            annot=True, fmt=".2f", linewidths=0.8,
            square=True, ax=ax, cbar_kws={"shrink": 0.75, "label": "Pearson r"})
ax.set_title("Correlation Heatmap -- All Numeric Features", fontsize=16, fontweight="bold", pad=20)

# highlight key correlations
key_corrs = [
    ("Aptitude_Spatial", "Aptitude_Math"),
    ("Marks_Biology", "Psych_Agreeableness"),
    ("Marks_Computer", "Marks_Biology"),
]
textstr = "Key findings:\n"
for a, b in key_corrs:
    r = corr.loc[a, b]
    textstr += f"  * {a.split('_')[-1]}<->{b.split('_')[-1]}: {r:+.2f}\n"
ax.text(1.02, 0.02, textstr, transform=ax.transAxes, fontsize=10,
        verticalalignment="bottom", bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.9))

fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "03_correlation_heatmap.png"), bbox_inches="tight")
plt.close(fig)
print("      [OK] Saved 03_correlation_heatmap.png")

# =============================================================================
# 4. Stream x Career cross-tab
# =============================================================================
print("[5/9] Stream x Career cross-tab …")
ct = pd.crosstab(df["Stream"], df["Recommended_Career"])

fig, ax = plt.subplots(figsize=(22, 8))
ct_norm = ct.div(ct.sum(axis=0), axis=1)  # column-normalized
sns.heatmap(ct_norm, cmap="YlOrRd", ax=ax, linewidths=0.4,
            cbar_kws={"label": "Proportion within Career"}, annot=False)
ax.set_title("Stream x Career Cross-Tabulation (Column-Normalized)", fontsize=16, fontweight="bold")
ax.set_ylabel("Stream")
ax.set_xlabel("Recommended Career")
plt.xticks(rotation=45, ha="right", fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "04_stream_career_crosstab.png"), bbox_inches="tight")
plt.close(fig)

# also save raw crosstab as CSV
ct.to_csv(os.path.join(OUTDIR, "04_stream_career_crosstab.csv"))
print("      [OK] Saved 04_stream_career_crosstab.png + .csv")

# =============================================================================
# 5. Big Five boxplots per career -- personality signatures
# =============================================================================
print("[6/9] Big Five personality boxplots …")
big5 = ["Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion",
        "Psych_Agreeableness", "Psych_Neuroticism"]

fig, axes = plt.subplots(1, 5, figsize=(28, 10), sharey=False)
for i, trait in enumerate(big5):
    # order careers by median of this trait
    order = df.groupby("Recommended_Career")[trait].median().sort_values(ascending=False).index
    sns.boxplot(data=df, y="Recommended_Career", x=trait, ax=axes[i],
                order=order, palette="coolwarm", fliersize=1, linewidth=0.6)
    axes[i].set_title(trait.replace("Psych_", ""), fontsize=13, fontweight="bold")
    axes[i].set_ylabel("" if i > 0 else "Career")
    axes[i].tick_params(axis="y", labelsize=7)

fig.suptitle("Big Five Personality Traits -- Box Plots per Career",
             fontsize=18, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "05_big5_boxplots.png"), bbox_inches="tight")
plt.close(fig)
print("      [OK] Saved 05_big5_boxplots.png")

# =============================================================================
# 6. Scatter-plot matrix -- marks vs aptitude vs psych by stream
# =============================================================================
print("[7/9] Scatter-plot matrix …")
scatter_cols = ["Marks_Math", "Aptitude_Math", "Aptitude_Spatial",
                "Psych_Openness", "Psych_Conscientiousness"]

sample = df.sample(n=min(5000, len(df)), random_state=42)
stream_palette = {"Pre-Engineering": "#e74c3c", "Pre-Medical": "#2ecc71",
                  "ICS": "#3498db", "Arts": "#f39c12"}

g = sns.pairplot(sample, vars=scatter_cols, hue="Stream",
                 palette=stream_palette, diag_kind="kde",
                 plot_kws={"alpha": 0.35, "s": 12},
                 diag_kws={"linewidth": 1.5},
                 height=2.2, aspect=1)
g.figure.suptitle("Scatter-Plot Matrix -- Marks x Aptitude x Psych (by Stream)",
                  fontsize=16, fontweight="bold", y=1.02)
g.savefig(os.path.join(OUTDIR, "06_scatter_matrix.png"), bbox_inches="tight")
plt.close(g.figure)
print("      [OK] Saved 06_scatter_matrix.png")

# =============================================================================
# 7. Text analysis -- TF-IDF top terms & word clouds
# =============================================================================
print("[8/9] Text analysis -- TF-IDF unigrams/bigrams + word clouds …")

try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    print("      [!] wordcloud not installed -- skipping word clouds, using bar charts instead")

streams = df["Stream"].unique()
fig_wc, axes_wc = plt.subplots(2, 2, figsize=(18, 14))
axes_wc = axes_wc.ravel()

fig_tfidf, axes_tf = plt.subplots(2, 2, figsize=(18, 14))
axes_tf = axes_tf.ravel()

for idx, stream in enumerate(sorted(streams)):
    texts = df.loc[df["Stream"] == stream, "Interest_Text"].dropna().tolist()

    # TF-IDF -- top 20 unigrams + bigrams
    vec = TfidfVectorizer(max_features=500, ngram_range=(1, 2), stop_words="english")
    tfidf_matrix = vec.fit_transform(texts)
    mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
    top_idx = mean_scores.argsort()[-20:][::-1]
    top_terms = [vec.get_feature_names_out()[i] for i in top_idx]
    top_scores = mean_scores[top_idx]

    # bar chart for TF-IDF
    ax = axes_tf[idx]
    ax.barh(top_terms[::-1], top_scores[::-1],
            color=sns.color_palette("magma", 20)[::-1], edgecolor="white")
    ax.set_title(f"{stream} -- Top TF-IDF Terms", fontweight="bold")
    ax.set_xlabel("Mean TF-IDF Score")

    # word cloud
    ax_wc = axes_wc[idx]
    if HAS_WORDCLOUD:
        term_freq = dict(zip(top_terms, top_scores))
        all_text = " ".join(texts)
        wc = WordCloud(width=800, height=500, background_color="white",
                       colormap="viridis", max_words=80,
                       prefer_horizontal=0.7).generate(all_text)
        ax_wc.imshow(wc, interpolation="bilinear")
        ax_wc.set_title(f"{stream} -- Interest Text Word Cloud", fontweight="bold")
    else:
        # fallback -- simple frequency bar
        all_words = " ".join(texts).lower().split()
        freq = Counter(all_words).most_common(20)
        words, counts = zip(*freq)
        ax_wc.barh(words[::-1], counts[::-1], color=sns.color_palette("crest", 20))
        ax_wc.set_title(f"{stream} -- Top Words (fallback)", fontweight="bold")
    ax_wc.axis("off") if HAS_WORDCLOUD else None

fig_tfidf.suptitle("TF-IDF Analysis of Interest_Text by Stream",
                   fontsize=16, fontweight="bold", y=1.01)
fig_tfidf.tight_layout()
fig_tfidf.savefig(os.path.join(OUTDIR, "07_tfidf_interest_text.png"), bbox_inches="tight")
plt.close(fig_tfidf)

fig_wc.suptitle("Word Clouds -- Interest_Text per Stream",
                fontsize=16, fontweight="bold", y=1.01)
fig_wc.tight_layout()
fig_wc.savefig(os.path.join(OUTDIR, "07_wordclouds_interest.png"), bbox_inches="tight")
plt.close(fig_wc)
print("      [OK] Saved 07_tfidf_interest_text.png + 07_wordclouds_interest.png")

# =============================================================================
# 8. Summary statistics -- save to CSV
# =============================================================================
print("[9/9] Saving summary statistics …")
desc = df[NUMERIC_COLS].describe().T
desc["skew"] = df[NUMERIC_COLS].skew()
desc["kurtosis"] = df[NUMERIC_COLS].kurtosis()
desc.to_csv(os.path.join(OUTDIR, "08_summary_statistics.csv"))
print("      [OK] Saved 08_summary_statistics.csv")

# -- done ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("  EDA COMPLETE -- all plots saved to reports/eda/")
print("=" * 60)
print(f"  Total files: {len(os.listdir(OUTDIR))}")
for f in sorted(os.listdir(OUTDIR)):
    size = os.path.getsize(os.path.join(OUTDIR, f))
    print(f"    * {f}  ({size / 1024:.0f} KB)")
print("=" * 60)
