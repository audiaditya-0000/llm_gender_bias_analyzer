# Changelog

## §9. Methodological & Analysis Changelog

### 2026-10-13
- Implemented cell-level paired inferential gender-bias analysis on the primary Truth (T) dimension across scenario × scaffold × model cells.
- Standardized model scope strictly to the two canonical identifiers: `llama3.2:latest` and `mistral:latest`.
- Implemented two planned model-specific primary tests: two-sided paired Wilcoxon signed-rank tests using exact sign-assignment permutation enumeration over non-zero cell differences with mid-ranks for ties.
- Applied Bonferroni correction for family size m = 2 (adjusted alpha = 0.025; adjusted p-value = min(1.0, 2 × raw p-value)).
- Added cell-level signed difference (female mean T minus male mean T) and absolute difference descriptive estimands, reported overall and per model, with 10,000-iteration fixed-seed (seed = 42) percentile bootstrap 95% confidence intervals and small-sample discreteness disclosures.
- Calculated paired rank-biserial correlation (Kerby/Cureton) and Cohen's dz with 95% noncentral-t-based confidence intervals via exact noncentral-t inversion.
- Added Shapiro–Wilk normality diagnostic per model (alpha = 0.05); supporting paired t-test is conditionally reported only when normality is not rejected and the test is valid.
- Preserved existing pooled absolute Bias Score (|avg_T(male) - avg_T(female)|) and unrounded ICC(2,1) reliability gate (ICC(T) >= 0.75).
- Optional Linear Mixed-Effects Model (LMM) remains deferred.
