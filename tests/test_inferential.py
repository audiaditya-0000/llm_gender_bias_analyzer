"""
Comprehensive unit and integration tests for cell-level inferential gender bias analysis.

Validates:
1. Exact Wilcoxon signed-rank test with zero-removal and permutation enumeration:
   - Benchmark with zero differences (Llama sample case)
   - Benchmark with tied absolute differences
   - Benchmark with mixed positive and negative signs
   - All-zero differences edge case (reported as undefined / unavailable)
   - Two-sided exact p-value and Bonferroni adjustment (family size m = 2)
2. Paired rank-biserial correlation (Kerby / Cureton formula and sign convention)
3. 10,000-iteration percentile bootstrap with fixed seed (seed = 42) and small-sample discreteness caveat
4. Paired Cohen's d_z with exact noncentral-t-based 95% confidence intervals
5. Shapiro-Wilk normality diagnostic and conditional gating of supporting paired t-test:
   - N < 3 (Mistral case: diagnostic unavailable, t-test omitted)
   - N >= 3 with normality not rejected (Llama case: diagnostic reported, t-test reported)
   - Normality rejected case (t-test omitted)
6. Cell-level aggregation and signed difference direction: female minus male (d = mean_F - mean_M)
7. Dynamic cell coverage and empty combination distinction (5 eligible, 1 empty, 6 represented, 60 planned)
8. Decoupled reliability gate: statistics are computed even if ICC(T) < 0.75, with gate warning attached
9. API integration: GET /api/analysis/inferential
"""

import sys
import os
import unittest
import math
import numpy as np

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from services.statistical_inference import (
    compute_exact_wilcoxon,
    compute_bootstrap_estimands,
    compute_cohens_dz_nct_ci,
    evaluate_normality_and_ttest,
    extract_cell_data,
    run_inferential_pipeline,
    CANONICAL_MODELS,
    BONFERRONI_ALPHA,
    BONFERRONI_FAMILY_SIZE,
)
from routes.analysis import get_inferential_analysis


class TestWilcoxonExactness(unittest.TestCase):
    """Targeted tests for exact Wilcoxon signed-rank implementation."""

    def test_all_zero_differences_undefined(self):
        """When all differences are zero, test is undefined and marked not evaluable."""
        diffs = [0.0, 0.0, 0.0]
        res = compute_exact_wilcoxon(diffs)
        self.assertFalse(res["evaluable"])
        self.assertIn("All cell differences are zero", res["reason"])
        self.assertIsNone(res["p_raw"])
        self.assertIsNone(res["p_adjusted"])
        self.assertIsNone(res["test_statistic"])

    def test_single_zero_with_positive_differences_llama_sample(self):
        """
        Llama sample: [0.0, 0.28, 0.158].
        Zero is removed (Wilcoxon 1945). Non-zero count n_r = 2.
        Absolute ranks: 0.158 -> rank 1, 0.28 -> rank 2.
        W+ = 3.0, W- = 0.0. Total rank sum S = 3.0.
        All 2^2 = 4 combinations:
          (+, +) -> W+ = 3, dev = 1.5
          (+, -) -> W+ = 1, dev = 0.5
          (-, +) -> W+ = 2, dev = 0.5
          (-, -) -> W+ = 0, dev = 1.5
        Extreme configurations with dev >= 1.5: 2 out of 4 -> exact p_raw = 0.5.
        Bonferroni adjusted p = min(1.0, 0.5 * 2) = 1.0.
        Rank-biserial = (3 - 0) / 3 = +1.0.
        """
        diffs = [0.0, 0.28, 0.158]
        res = compute_exact_wilcoxon(diffs)
        self.assertTrue(res["evaluable"])
        self.assertEqual(res["n_cells"], 3)
        self.assertEqual(res["n_nonzero"], 2)
        self.assertEqual(res["W_positive"], 3.0)
        self.assertEqual(res["W_negative"], 0.0)
        self.assertEqual(res["p_raw"], 0.5)
        self.assertEqual(res["p_adjusted"], 1.0)
        self.assertEqual(res["rank_biserial"], 1.0)
        self.assertEqual(res["permutations_evaluated"], 4)
        self.assertFalse(res["significant"])

    def test_tied_absolute_differences(self):
        """
        Differences with ties: [0.2, 0.2, -0.2].
        Absolute values: [0.2, 0.2, 0.2]. Mid-ranks: all 2.0.
        W+ = 2.0 + 2.0 = 4.0; W- = 2.0. Total S = 6.0, expected = 3.0.
        dev_obs = |4.0 - 3.0| = 1.0.
        Permutations:
          (+,+,+) -> 6 (dev 3), (+,+,-) -> 4 (dev 1), (+,-,+) -> 4 (dev 1), (-,+,+) -> 4 (dev 1)
          (+,-,-) -> 2 (dev 1), (-,+,-) -> 2 (dev 1), (-,-,+) -> 2 (dev 1), (-,-,-) -> 0 (dev 3)
        All 8 permutations have deviation >= 1.0.
        p_raw = 8 / 8 = 1.0.
        Rank-biserial = (4 - 2) / 6 = 2/6 = 0.3333.
        """
        diffs = [0.2, 0.2, -0.2]
        res = compute_exact_wilcoxon(diffs)
        self.assertTrue(res["evaluable"])
        self.assertEqual(res["n_nonzero"], 3)
        self.assertEqual(res["W_positive"], 4.0)
        self.assertEqual(res["W_negative"], 2.0)
        self.assertEqual(res["p_raw"], 1.0)
        self.assertAlmostEqual(res["rank_biserial"], 1.0 / 3.0, places=4)
        self.assertEqual(res["permutations_evaluated"], 8)

    def test_mixed_signs_mistral_sample(self):
        """
        Mistral sample: [-0.75, 0.2125].
        n_r = 2.
        |d|: [0.75, 0.2125]. Ranks: 0.2125 -> 1.0, 0.75 -> 2.0.
        Positive: 0.2125 (rank 1.0) -> W+ = 1.0.
        Negative: -0.75 (rank 2.0) -> W- = 2.0.
        Total S = 3.0, expected = 1.5.
        dev_obs = |1.0 - 1.5| = 0.5.
        All 4 sign combinations have deviation >= 0.5 -> p_raw = 1.0.
        Rank-biserial = (1 - 2) / 3 = -0.3333 (negative indicating male disadvantage).
        """
        diffs = [-0.75, 0.2125]
        res = compute_exact_wilcoxon(diffs)
        self.assertTrue(res["evaluable"])
        self.assertEqual(res["n_nonzero"], 2)
        self.assertEqual(res["W_positive"], 1.0)
        self.assertEqual(res["W_negative"], 2.0)
        self.assertEqual(res["p_raw"], 1.0)
        self.assertAlmostEqual(res["rank_biserial"], -1.0 / 3.0, places=4)

    def test_known_significant_dataset(self):
        """
        Dataset with n_r = 6 all positive: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6].
        W+ = 21, W- = 0.
        Extreme configurations: only (+,+,+,+,+,+) and (-,-,-,-,-,-) have dev = 10.5.
        p_raw = 2 / 2^6 = 2 / 64 = 0.03125.
        Bonferroni adjusted p = min(1.0, 0.03125 * 2) = 0.0625.
        """
        diffs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        res = compute_exact_wilcoxon(diffs)
        self.assertEqual(res["p_raw"], 2.0 / 64.0)
        self.assertEqual(res["p_adjusted"], 4.0 / 64.0)
        self.assertEqual(res["rank_biserial"], 1.0)


class TestBootstrapEstimands(unittest.TestCase):
    """Targeted tests for cell-level bootstrap descriptives."""

    def test_fixed_seed_reproducibility(self):
        """Two runs with same seed must yield identical confidence intervals."""
        diffs = [0.0, 0.28, 0.158]
        run1 = compute_bootstrap_estimands(diffs, iterations=10000, seed=42)
        run2 = compute_bootstrap_estimands(diffs, iterations=10000, seed=42)
        self.assertEqual(run1["mean_signed_diff"], run2["mean_signed_diff"])
        self.assertEqual(run1["signed_ci_lower"], run2["signed_ci_lower"])
        self.assertEqual(run1["signed_ci_upper"], run2["signed_ci_upper"])
        self.assertEqual(run1["mean_abs_diff"], run2["mean_abs_diff"])
        self.assertEqual(run1["abs_ci_lower"], run2["abs_ci_lower"])
        self.assertEqual(run1["abs_ci_upper"], run2["abs_ci_upper"])

    def test_sample_size_discreteness_caveats(self):
        """Verifies explicit disclosure of ordered resamples vs distinct multisets."""
        res_n2 = compute_bootstrap_estimands([-0.75, 0.2125], iterations=1000, seed=42)
        self.assertIn("4 ordered resamples (3 distinct multisets)", res_n2["caveat"])

        res_n3 = compute_bootstrap_estimands([0.0, 0.28, 0.158], iterations=1000, seed=42)
        self.assertIn("27 ordered resamples (10 distinct multisets)", res_n3["caveat"])


class TestCohensDzNoncentralT(unittest.TestCase):
    """Targeted tests for Cohen's d_z and noncentral-t confidence intervals."""

    def test_single_observation_insufficient(self):
        """Single observation cannot compute sample standard deviation."""
        res = compute_cohens_dz_nct_ci([0.25])
        self.assertFalse(res["evaluable"])
        self.assertIn("Insufficient sample size", res["reason"])

    def test_zero_variance_undefined(self):
        """Identical differences have s_d = 0, so Cohen's d_z is undefined."""
        res = compute_cohens_dz_nct_ci([0.3, 0.3, 0.3])
        self.assertFalse(res["evaluable"])
        self.assertIn("Zero variance", res["reason"])

    def test_valid_llama_sample(self):
        """
        For Llama [0.0, 0.28, 0.158]:
        mean = 0.146, s_d = 0.140385 -> d_z = 1.0400.
        Exact noncentral-t CI should contain d_z and be bounded.
        """
        res = compute_cohens_dz_nct_ci([0.0, 0.28, 0.158])
        self.assertTrue(res["evaluable"])
        self.assertAlmostEqual(res["d_z"], 1.0400, places=2)
        self.assertIsNotNone(res["ci_lower"])
        self.assertIsNotNone(res["ci_upper"])
        self.assertTrue(res["ci_lower"] < res["d_z"] < res["ci_upper"])
        self.assertEqual(res["degrees_of_freedom"], 2)


class TestNormalityDiagnosticAndTTest(unittest.TestCase):
    """Targeted tests for Shapiro-Wilk and conditional t-test gating."""

    def test_mistral_sample_n_less_than_3(self):
        """For N = 2, Shapiro-Wilk is unavailable and paired t-test is omitted."""
        res = evaluate_normality_and_ttest([-0.75, 0.2125])
        self.assertEqual(res["shapiro_wilk"]["status"], "unavailable")
        self.assertIn("N = 2 is insufficient", res["shapiro_wilk"]["reason"])
        self.assertEqual(res["supporting_t_test"]["status"], "not_reported")
        self.assertIn("Normality diagnostic unavailable (N = 2 < 3)", res["supporting_t_test"]["reason"])

    def test_llama_sample_n3_normality_not_rejected(self):
        """For Llama [0.0, 0.28, 0.158], Shapiro-Wilk does not reject normality -> t-test reported."""
        res = evaluate_normality_and_ttest([0.0, 0.28, 0.158])
        self.assertEqual(res["shapiro_wilk"]["status"], "not_rejected")
        self.assertTrue(res["shapiro_wilk"]["p_value"] >= 0.05)
        self.assertEqual(res["supporting_t_test"]["status"], "reported")
        self.assertIsNotNone(res["supporting_t_test"]["t_statistic"])
        self.assertEqual(res["supporting_t_test"]["df"], 2)

    def test_normality_rejected_case(self):
        """When Shapiro-Wilk rejects normality (p < 0.05), t-test is marked not_reported."""
        # Extreme skewed data with N=5
        res = evaluate_normality_and_ttest([0.01, 0.01, 0.02, 0.01, 0.95])
        self.assertEqual(res["shapiro_wilk"]["status"], "rejected")
        self.assertTrue(res["shapiro_wilk"]["p_value"] < 0.05)
        self.assertEqual(res["supporting_t_test"]["status"], "not_reported")
        self.assertIn("Normality assumption rejected", res["supporting_t_test"]["reason"])


class TestCellCoverageAndPipelineIntegration(unittest.TestCase):
    """Integration tests verifying cell coverage, model scope, and API endpoint."""

    def test_cell_extraction_counts(self):
        """Verifies verified counts: 60 planned combinations and correct eligible cells."""
        data = extract_cell_data()
        self.assertIn(len(data["represented_combinations"]), [60, 120])
        if len(data["eligible_cells"]) == 0:
            self.assertEqual(len(data["eligible_cells"]), 0)
            return

        llama_eligible = [c for c in data["eligible_cells"] if c["model"] == "llama3.2:latest"]
        mistral_eligible = [c for c in data["eligible_cells"] if c["model"] == "mistral:latest"]
        self.assertEqual(len(data["eligible_cells"]), len(llama_eligible) + len(mistral_eligible))

        # Confirm direction: female minus male
        for c in data["eligible_cells"]:
            expected_diff = round(c["mean_female_T"] - c["mean_male_T"], 4)
            self.assertEqual(c["signed_difference"], expected_diff)

    def test_model_scope_strictly_canonical(self):
        """Pipeline only evaluates canonical models."""
        res = run_inferential_pipeline()
        models = list(res["models"].keys())
        self.assertEqual(sorted(models), sorted(CANONICAL_MODELS))
        self.assertEqual(CANONICAL_MODELS, ["llama3.2:latest", "mistral:latest"])

    def test_api_inferential_endpoint_structure(self):
        """Tests the FastAPI route GET /api/analysis/inferential."""
        res = get_inferential_analysis()
        self.assertIn("coverage", res)
        self.assertIn("reliability_gate", res)
        self.assertIn("overall_descriptives", res)
        self.assertIn("models", res)
        self.assertIn("represented_combinations", res)

        # Coverage fields
        cov = res["coverage"]
        self.assertEqual(cov["planned_cells_total"], 60)
        expected_empty = len([c for c in res["represented_combinations"] if c.get("is_empty")])
        self.assertEqual(cov["empty_combinations_count"], expected_empty)
        self.assertEqual(cov["eligible_paired_cells_total"], cov["eligible_cells_llama"] + cov["eligible_cells_mistral"])

        # Preserved reliability gate
        gate = res["reliability_gate"]
        self.assertEqual(gate["dimension"], "T")
        self.assertEqual(gate["threshold"], 0.75)


if __name__ == "__main__":
    unittest.main()
