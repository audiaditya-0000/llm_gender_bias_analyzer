"""
Statistical inference service for gender-bias analysis on the Truth (T) dimension.

Implements prespecified cell-level inferential statistics:
- Cell unit: Scenario x Scaffold x Model
- Signed difference: d_cell = mean(T_female) - mean(T_male)
- Primary tests: Two-sided paired Wilcoxon signed-rank tests per model
  with exact sign-assignment permutation enumeration (handling zeros via
  zero-removal and ties via mid-ranks).
- Bonferroni correction for family size m = 2 (adjusted alpha = 0.025).
- Paired rank-biserial correlation (Kerby / Cureton simple difference formula).
- Cell-level descriptive estimands: mean signed difference and mean absolute difference,
  overall and per model, with 10,000-iteration fixed-seed (seed=42) percentile bootstrap 95% CIs.
- Paired Cohen's d_z with exact noncentral-t-based 95% confidence intervals.
- Shapiro-Wilk normality diagnostic per model (alpha = 0.05), conditionally reporting
  a supporting paired t-test ONLY when normality is not rejected and the test is valid.
  If the diagnostic is unavailable (e.g. N < 3), normality is not assumed.
- Integrates with the backend ICC(2,1) reliability gate (ICC(T) >= 0.75).
- Optional Linear Mixed-Effects Model (LMM) remains deferred.
"""

import math
from typing import Optional, Any
import numpy as np
import scipy.stats as stats
import scipy.optimize as optimize

from storage import read_json

RESPONSES_FILE = "responses.json"
CODING_FILE = "coding.json"
SCENARIOS_FILE = "scenarios.json"
SCAFFOLDS_FILE = "scaffolds.json"

CANONICAL_MODELS = ["llama3.2:latest", "mistral:latest"]
BONFERRONI_FAMILY_SIZE = 2
BONFERRONI_ALPHA = 0.05 / BONFERRONI_FAMILY_SIZE  # 0.025
BOOTSTRAP_ITERATIONS = 10000
BOOTSTRAP_SEED = 42


def is_valid_score(val: Any) -> bool:
    """Validate that a score is a finite real number within [0.0, 1.0]."""
    if val is None or isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    if math.isnan(val) or math.isinf(val):
        return False
    return 0.0 <= float(val) <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# CELL DATA EXTRACTION & AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def extract_cell_data(experiment_id: Optional[str] = None) -> dict:
    """
    Extract responses, map to cells (scenario x scaffold x model),
    average valid coder ratings for response-level T,
    and compute cell means and differences.
    """
    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)
    scenarios = read_json(SCENARIOS_FILE)
    scaffolds = read_json(SCAFFOLDS_FILE)

    if experiment_id:
        responses = [r for r in responses if r.get("experiment_id") == experiment_id]

    # Coder deduplication matching backend/routes/analysis.py
    coding_lookup: dict[str, dict[str, dict]] = {}
    for c in codings:
        resp_id = c.get("response_id")
        coder_id = c.get("coder_id")
        if not resp_id or not coder_id:
            continue
        if resp_id not in coding_lookup:
            coding_lookup[resp_id] = {}
        existing = coding_lookup[resp_id].get(coder_id)
        if existing is None or c.get("coded_at", "") >= existing.get("coded_at", ""):
            coding_lookup[resp_id][coder_id] = c

    # Scenario and scaffold metadata lookups
    scenario_titles = {s.get("id"): s.get("title", s.get("id")) for s in scenarios if s.get("id")}
    scaffold_names = {sc.get("id"): f"{sc.get('name', sc.get('id'))} (v{sc.get('version', '')})" for sc in scaffolds if sc.get("id")}

    # Group responses by (scenario_id, scaffold_id, model)
    cell_responses: dict[tuple[str, str, str], list[dict]] = {}
    for r in responses:
        scen_id = r.get("scenario_id")
        scaff_id = r.get("scaffold_id")
        model = r.get("model")
        if not scen_id or not scaff_id or not model:
            continue
        key = (scen_id, scaff_id, model)
        if key not in cell_responses:
            cell_responses[key] = []
        cell_responses[key].append(r)

    # Catalog combinations for the active scenario(s)
    represented_combinations = []
    eligible_cells = []

    # Identify all active scenarios and scaffolds from files
    scenario_ids = sorted(list(scenario_titles.keys())) if scenario_titles else sorted(list({r.get("scenario_id") for r in responses if r.get("scenario_id")}))
    scaffold_ids = sorted(list(scaffold_names.keys())) if scaffold_names else sorted(list({r.get("scaffold_id") for r in responses if r.get("scaffold_id")}))

    for scen_id in scenario_ids:
        for scaff_id in scaffold_ids:
            for model in CANONICAL_MODELS:
                combo_key = (scen_id, scaff_id, model)
                resp_list = cell_responses.get(combo_key, [])
                
                female_scores = []
                male_scores = []

                for r in resp_list:
                    r_id = r.get("id")
                    c_map = coding_lookup.get(r_id, {})
                    if not c_map:
                        continue
                    valid_t = [float(c["truth"]) for c in c_map.values() if is_valid_score(c.get("truth"))]
                    if not valid_t:
                        continue
                    avg_t = sum(valid_t) / len(valid_t)
                    cond = (r.get("condition") or "").lower().strip()
                    if cond.startswith("female") or cond == "swapped":
                        female_scores.append(avg_t)
                    elif cond.startswith("male") or cond == "original":
                        male_scores.append(avg_t)

                n_f = len(female_scores)
                n_m = len(male_scores)
                mean_f = (sum(female_scores) / n_f) if n_f > 0 else None
                mean_m = (sum(male_scores) / n_m) if n_m > 0 else None
                diff = (mean_f - mean_m) if (mean_f is not None and mean_m is not None) else None

                combo_record = {
                    "scenario_id": scen_id,
                    "scenario_title": scenario_titles.get(scen_id, scen_id),
                    "scaffold_id": scaff_id,
                    "scaffold_name": scaffold_names.get(scaff_id, scaff_id),
                    "model": model,
                    "total_responses": len(resp_list),
                    "n_female": n_f,
                    "n_male": n_m,
                    "mean_female_T": round(mean_f, 4) if mean_f is not None else None,
                    "mean_male_T": round(mean_m, 4) if mean_m is not None else None,
                    "signed_difference": round(diff, 4) if diff is not None else None,
                    "is_eligible": (n_f > 0 and n_m > 0),
                    "is_empty": len(resp_list) == 0,
                }
                represented_combinations.append(combo_record)
                if n_f > 0 and n_m > 0:
                    eligible_cells.append(combo_record)

    return {
        "represented_combinations": represented_combinations,
        "eligible_cells": eligible_cells,
        "num_scenarios_defined": len(scenario_ids),
        "num_scaffolds_defined": len(scaffold_ids),
        "total_responses": len(responses),
    }


# ══════════════════════════════════════════════════════════════════════════════
# EXACT WILCOXON SIGNED-RANK TEST (HANDLING ZEROS & TIES VIA PERMUTATION)
# ══════════════════════════════════════════════════════════════════════════════

def compute_exact_wilcoxon(diffs: list[float]) -> dict:
    """
    Computes exact two-sided paired Wilcoxon signed-rank test.
    
    Zero handling: Documented zero-removal convention (Wilcoxon 1945).
    Differences with |d_i| < 1e-12 are excluded.
    
    Tie handling: Average ranks (mid-ranks) assigned to tied absolute differences
    via scipy.stats.rankdata.
    
    Exact p-value: Exhaustive enumeration over all 2^(n_r) equally likely sign
    assignments (+/- 1) to ranks.
    Two-sided p-value is the proportion of configurations whose deviation from
    expected rank sum S/2 is >= observed deviation.
    """
    nonzero = [float(d) for d in diffs if abs(d) > 1e-12]
    n_r = len(nonzero)

    if n_r == 0:
        return {
            "evaluable": False,
            "reason": "All cell differences are zero; Wilcoxon signed-rank test is undefined.",
            "n_cells": len(diffs),
            "n_nonzero": 0,
            "W_positive": None,
            "W_negative": None,
            "test_statistic": None,
            "p_raw": None,
            "p_adjusted": None,
            "alpha_adjusted": BONFERRONI_ALPHA,
            "significant": False,
            "method": "exact_sign_enumeration_with_zero_removal",
            "rank_biserial": None,
        }

    abs_vals = np.array([abs(d) for d in nonzero], dtype=float)
    signs = np.array([1 if d > 0 else -1 for d in nonzero], dtype=int)
    ranks = stats.rankdata(abs_vals)

    W_pos = float(np.sum(ranks[signs > 0]))
    W_neg = float(np.sum(ranks[signs < 0]))
    S = float(np.sum(ranks))  # Total sum of ranks: n_r*(n_r+1)/2

    # Exhaustive sign enumeration for exact distribution
    num_comb = 1 << n_r
    expected_W = S / 2.0
    dev_obs = abs(W_pos - expected_W)
    extreme_count = 0

    for i in range(num_comb):
        w_sim = 0.0
        for j in range(n_r):
            if (i >> j) & 1:
                w_sim += ranks[j]
        dev_sim = abs(w_sim - expected_W)
        if dev_sim >= dev_obs - 1e-12:
            extreme_count += 1

    p_raw = float(extreme_count / num_comb)
    p_adj = float(min(1.0, p_raw * BONFERRONI_FAMILY_SIZE))
    significant = bool(p_adj < BONFERRONI_ALPHA)

    # Paired rank-biserial correlation (Kerby 2014 simple difference formula)
    # r_rb = (W+ - W-) / (W+ + W-) = (W+ - W-) / S
    r_rb = float((W_pos - W_neg) / S) if S > 0 else 0.0

    return {
        "evaluable": True,
        "reason": None,
        "n_cells": len(diffs),
        "n_nonzero": n_r,
        "W_positive": round(W_pos, 4),
        "W_negative": round(W_neg, 4),
        "test_statistic": round(W_pos, 4),
        "p_raw": round(p_raw, 6),
        "p_adjusted": round(p_adj, 6),
        "alpha_adjusted": BONFERRONI_ALPHA,
        "significant": significant,
        "method": "exact_sign_enumeration_with_zero_removal",
        "rank_biserial": round(r_rb, 4),
        "permutations_evaluated": num_comb,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CELL-LEVEL DESCRIPTIVE ESTIMANDS & PERCENTILE BOOTSTRAP 95% CIs
# ══════════════════════════════════════════════════════════════════════════════

def compute_bootstrap_estimands(diffs: list[float], iterations: int = BOOTSTRAP_ITERATIONS, seed: int = BOOTSTRAP_SEED) -> dict:
    """
    Computes sample mean signed difference and sample mean absolute difference,
    along with 10,000-iteration percentile bootstrap 95% confidence intervals
    using cell-level resampling with replacement and fixed documented seed.
    
    Includes explicit disclosures regarding bootstrap discreteness at small N.
    """
    n = len(diffs)
    if n == 0:
        return {
            "mean_signed_diff": None,
            "signed_ci_lower": None,
            "signed_ci_upper": None,
            "mean_abs_diff": None,
            "abs_ci_lower": None,
            "abs_ci_upper": None,
            "iterations": iterations,
            "seed": seed,
            "caveat": "No cell differences available.",
        }

    arr = np.array(diffs, dtype=float)
    mean_signed = float(np.mean(arr))
    mean_abs = float(np.mean(np.abs(arr)))

    if n == 1:
        return {
            "mean_signed_diff": round(mean_signed, 4),
            "signed_ci_lower": round(mean_signed, 4),
            "signed_ci_upper": round(mean_signed, 4),
            "mean_abs_diff": round(mean_abs, 4),
            "abs_ci_lower": round(mean_abs, 4),
            "abs_ci_upper": round(mean_abs, 4),
            "iterations": iterations,
            "seed": seed,
            "caveat": "Single cell observed; bootstrap resampling yields degenerate zero-variance interval.",
        }

    rng = np.random.default_rng(seed)
    # Resample with replacement: shape (iterations, n)
    indices = rng.integers(0, n, size=(iterations, n))
    boot_samples = arr[indices]

    boot_signed_means = np.mean(boot_samples, axis=1)
    boot_abs_means = np.mean(np.abs(boot_samples), axis=1)

    signed_ci_lower = float(np.percentile(boot_signed_means, 2.5))
    signed_ci_upper = float(np.percentile(boot_signed_means, 97.5))

    abs_ci_lower = float(np.percentile(boot_abs_means, 2.5))
    abs_ci_upper = float(np.percentile(boot_abs_means, 97.5))

    # Document discreteness for small sample sizes
    if n == 2:
        caveat = (
            "Sample size N = 2 yields only 4 ordered resamples (3 distinct multisets). "
            "The percentile bootstrap interval is discrete and unstable; 10,000 iterations "
            "reflect resampling variance but cannot overcome data sparsity."
        )
    elif n == 3:
        caveat = (
            "Sample size N = 3 yields only 27 ordered resamples (10 distinct multisets). "
            "The percentile bootstrap interval is discrete and unstable; 10,000 iterations "
            "reflect resampling variance but cannot overcome data sparsity."
        )
    else:
        caveat = f"Cell-level percentile bootstrap based on {iterations:,} resamples (seed={seed})."

    return {
        "mean_signed_diff": round(mean_signed, 4),
        "signed_ci_lower": round(signed_ci_lower, 4),
        "signed_ci_upper": round(signed_ci_upper, 4),
        "mean_abs_diff": round(mean_abs, 4),
        "abs_ci_lower": round(abs_ci_lower, 4),
        "abs_ci_upper": round(abs_ci_upper, 4),
        "iterations": iterations,
        "seed": seed,
        "caveat": caveat,
    }


# ══════════════════════════════════════════════════════════════════════════════
# COHEN'S d_z & 95% NONCENTRAL-t CONFIDENCE INTERVAL
# ══════════════════════════════════════════════════════════════════════════════

def compute_cohens_dz_nct_ci(diffs: list[float]) -> dict:
    """
    Computes Cohen's d_z = mean(d) / s_d and its exact 95% confidence interval
    via inversion of the noncentral t-distribution (Cumming & Finch 2001; Steiger 2004).
    
    Parameterization:
      t_obs = d_z * sqrt(N), df = N - 1, lambda = delta_z * sqrt(N)
      Solve F(t_obs; df, lambda_L) = 0.975 for lower noncentrality parameter lambda_L
      Solve F(t_obs; df, lambda_U) = 0.025 for upper noncentrality parameter lambda_U
      Confidence interval: [lambda_L / sqrt(N), lambda_U / sqrt(N)]
    """
    n = len(diffs)
    if n < 2:
        return {
            "d_z": None,
            "ci_lower": None,
            "ci_upper": None,
            "evaluable": False,
            "reason": f"Insufficient sample size: at least 2 cells required for Cohen's d_z (found N={n}).",
        }

    arr = np.array(diffs, dtype=float)
    mean_d = float(np.mean(arr))
    s_d = float(np.std(arr, ddof=1))

    if s_d <= 1e-12 or math.isnan(s_d):
        return {
            "d_z": None,
            "ci_lower": None,
            "ci_upper": None,
            "evaluable": False,
            "reason": "Zero variance in cell differences; Cohen's d_z denominator is zero.",
        }

    dz = mean_d / s_d
    df = n - 1
    t_obs = dz * math.sqrt(n)

    def _solve_nc(p_target: float) -> Optional[float]:
        def obj(nc: float) -> float:
            return float(stats.nct.cdf(t_obs, df, nc) - p_target)

        # Dynamic search bracket expansion
        low, high = t_obs - 5.0, t_obs + 5.0
        step = 5.0
        for _ in range(30):
            try:
                val_low = obj(low)
                val_high = obj(high)
                if val_low > 0 and val_high < 0:
                    break
                if val_low <= 0:
                    low -= step
                if val_high >= 0:
                    high += step
                step *= 1.5
            except Exception:
                return None
        try:
            return float(optimize.brentq(obj, low, high))
        except Exception:
            return None

    nc_L = _solve_nc(0.975)
    nc_U = _solve_nc(0.025)

    if nc_L is None or nc_U is None:
        return {
            "d_z": round(dz, 4),
            "ci_lower": None,
            "ci_upper": None,
            "evaluable": False,
            "reason": "Numerical convergence failure in noncentral-t root finding.",
        }

    ci_lower = nc_L / math.sqrt(n)
    ci_upper = nc_U / math.sqrt(n)

    return {
        "d_z": round(dz, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "evaluable": True,
        "reason": None,
        "method": "exact_noncentral_t_inversion",
        "degrees_of_freedom": df,
        "t_observed": round(t_obs, 4),
    }


# ══════════════════════════════════════════════════════════════════════════════
# SHAPIRO-WILK NORMALITY DIAGNOSTIC & CONDITIONAL SUPPORTING PAIRED t-TEST
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_normality_and_ttest(diffs: list[float]) -> dict:
    """
    Evaluates Shapiro-Wilk test separately on cell differences.
    Conditionally reports a supporting paired t-test ONLY when the diagnostic
    does not reject normality (p >= 0.05) and the test is valid.
    
    If the diagnostic is unavailable (e.g. N < 3), normality is not assumed,
    and the supporting t-test is marked not_reported.
    """
    n = len(diffs)

    # Check sample size for Shapiro-Wilk (minimum N = 3)
    if n < 3:
        shapiro_result = {
            "status": "unavailable",
            "W": None,
            "p_value": None,
            "reason": f"Sample size N = {n} is insufficient for Shapiro-Wilk test (minimum N = 3 required).",
        }
        ttest_result = {
            "status": "not_reported",
            "t_statistic": None,
            "df": None,
            "p_value": None,
            "reason": f"Normality diagnostic unavailable (N = {n} < 3); normality cannot be assumed.",
        }
        return {
            "shapiro_wilk": shapiro_result,
            "supporting_t_test": ttest_result,
        }

    arr = np.array(diffs, dtype=float)
    s_d = float(np.std(arr, ddof=1))

    if s_d <= 1e-12:
        shapiro_result = {
            "status": "unavailable",
            "W": None,
            "p_value": None,
            "reason": "Zero variance in cell differences; Shapiro-Wilk is undefined.",
        }
        ttest_result = {
            "status": "not_reported",
            "t_statistic": None,
            "df": None,
            "p_value": None,
            "reason": "Zero variance in cell differences; paired t-test cannot be computed.",
        }
        return {
            "shapiro_wilk": shapiro_result,
            "supporting_t_test": ttest_result,
        }

    # Run Shapiro-Wilk
    w_stat, p_val = stats.shapiro(arr)
    w_stat = float(w_stat)
    p_val = float(p_val)

    if p_val < 0.05:
        shapiro_result = {
            "status": "rejected",
            "W": round(w_stat, 4),
            "p_value": round(p_val, 6),
            "reason": f"Normality assumption rejected by Shapiro-Wilk test (W = {w_stat:.4f}, p = {p_val:.4f} < 0.05).",
        }
        ttest_result = {
            "status": "not_reported",
            "t_statistic": None,
            "df": None,
            "p_value": None,
            "reason": "Normality assumption rejected; supporting parametric t-test is omitted.",
        }
    else:
        shapiro_result = {
            "status": "not_rejected",
            "W": round(w_stat, 4),
            "p_value": round(p_val, 6),
            "reason": f"Normality assumption not rejected (W = {w_stat:.4f}, p = {p_val:.4f} >= 0.05).",
        }
        # Run paired t-test against H0: mu_d = 0
        df = n - 1
        mean_d = float(np.mean(arr))
        t_stat = mean_d / (s_d / math.sqrt(n))
        p_t = 2.0 * float(1.0 - stats.t.cdf(abs(t_stat), df))

        ttest_result = {
            "status": "reported",
            "t_statistic": round(t_stat, 4),
            "df": df,
            "p_value": round(p_t, 6),
            "reason": "Supporting paired t-test reported because normality diagnostic did not reject normality.",
        }

    return {
        "shapiro_wilk": shapiro_result,
        "supporting_t_test": ttest_result,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_inferential_pipeline(experiment_id: Optional[str] = None) -> dict:
    """
    Executes the complete cell-level inferential analysis pipeline.
    
    Returns:
    - coverage: dynamic inventory of represented combinations vs 60 planned cells
    - reliability_gate: ICC(T) gate status from backend/routes/analysis.py
    - overall_descriptives: pooled cell-level descriptive estimands with bootstrap CI
    - models: model-specific inferential results for llama3.2:latest and mistral:latest
    """
    cell_data = extract_cell_data(experiment_id)
    eligible_cells = cell_data["eligible_cells"]
    represented_combos = cell_data["represented_combinations"]

    # Coverage accounting
    total_planned = 60
    planned_per_model = 30
    combos_count = len(represented_combos)
    empty_combos = [c for c in represented_combos if c["is_empty"]]
    unpaired_combos = [c for c in represented_combos if not c["is_empty"] and not c["is_eligible"]]

    llama_cells = [c for c in eligible_cells if c["model"] == "llama3.2:latest"]
    mistral_cells = [c for c in eligible_cells if c["model"] == "mistral:latest"]

    llama_diffs = [c["signed_difference"] for c in llama_cells if c["signed_difference"] is not None]
    mistral_diffs = [c["signed_difference"] for c in mistral_cells if c["signed_difference"] is not None]
    all_diffs = [c["signed_difference"] for c in eligible_cells if c["signed_difference"] is not None]

    coverage = {
        "planned_cells_total": total_planned,
        "planned_cells_per_model": planned_per_model,
        "represented_combinations_total": combos_count,
        "empty_combinations_count": len(empty_combos),
        "unpaired_combinations_count": len(unpaired_combos),
        "eligible_paired_cells_total": len(eligible_cells),
        "eligible_cells_llama": len(llama_cells),
        "eligible_cells_mistral": len(mistral_cells),
        "absent_scenarios_count": max(0, 10 - cell_data["num_scenarios_defined"]),
        "limitation_disclosure": (
            f"Experimental Coverage Notice: Out of the 60 planned scenario x scaffold x model cells "
            f"(30 per model), the current database represents {combos_count} combinations across "
            f"{cell_data['num_scenarios_defined']} scenario. Of these, {len(empty_combos)} combination has "
            f"no responses and {len(eligible_cells)} are eligible paired cells with both female and male "
            f"conditions coded (llama3.2:latest: {len(llama_cells)}/30; mistral:latest: {len(mistral_cells)}/30). "
            f"Inferential statistics are computed strictly on available cells to validate pipeline execution; "
            f"they do not represent complete experimental coverage and missing cells are not imputed."
        ),
    }

    # Overall cell-level descriptives (pooled across available cells)
    overall_descriptives = compute_bootstrap_estimands(all_diffs)

    # Per-model inferential blocks
    models_result = {}
    for model_id, diff_list, cell_list in [
        ("llama3.2:latest", llama_diffs, llama_cells),
        ("mistral:latest", mistral_diffs, mistral_cells),
    ]:
        wilcoxon = compute_exact_wilcoxon(diff_list)
        descriptives = compute_bootstrap_estimands(diff_list)
        cohens_dz = compute_cohens_dz_nct_ci(diff_list)
        parametric = evaluate_normality_and_ttest(diff_list)

        models_result[model_id] = {
            "model": model_id,
            "eligible_cell_count": len(cell_list),
            "cell_differences": [round(d, 4) for d in diff_list],
            "cells": cell_list,
            "primary_test": {
                "test_name": "Two-sided paired Wilcoxon signed-rank test",
                **wilcoxon,
            },
            "effect_sizes": {
                "rank_biserial": wilcoxon.get("rank_biserial"),
                "rank_biserial_sign_convention": (
                    "r_rb in [-1, +1]; positive indicates female stereotyping/disadvantage scores exceed male scores."
                ),
                "cohens_dz": cohens_dz,
            },
            "descriptives": descriptives,
            "normality_diagnostic": parametric["shapiro_wilk"],
            "supporting_parametric_test": parametric["supporting_t_test"],
        }

    return {
        "coverage": coverage,
        "overall_descriptives": overall_descriptives,
        "models": models_result,
        "represented_combinations": represented_combos,
    }
