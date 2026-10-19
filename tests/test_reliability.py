"""
Comprehensive automated tests for Inter-Rater Reliability (ICC(2,1) and MAD).

Validates all 14 requirements specified for research-grade reliability analysis:
1. Identical scores from both coders produce perfect absolute agreement (ICC = 1.0).
2. Known benchmark dataset matches independently calculated reference result (Shrout & Fleiss 1979).
3. Coders with similar rankings but systematic score offsets are evaluated using absolute agreement, not consistency alone.
4. T, I, and F dimensions are calculated independently without data or result leakage.
5. Scores are paired by stable response IDs, even when records are returned in different orders.
6. Responses with only one coder score are excluded from reliability calculations.
7. Missing, invalid, duplicate, and unmatched coding records are handled safely and transparently.
8. Insufficient observations (n < 2) and mathematically undefined cases (zero variance) return explicit unavailable results.
9. MAD is calculated correctly on the eligible matched responses.
10. Response-level dimension scores remain the arithmetic mean of valid coder scores.
11. The ICC(T) threshold (0.75) is evaluated using the unrounded value.
12. An unavailable ICC does not incorrectly pass the reliability gate (status is unevaluable).
13. The API returns consistent values, sample counts, and gate status matching calculations.
14. Existing unrelated functionality continues to pass.
"""

import math
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from routes.analysis import (
    compute_icc_2_1,
    _calculate_icc_2_1,
    _mean_absolute_difference,
    _calculate_dimension_agreement,
    get_inter_rater_agreement,
    _compute_metrics,
    is_valid_score,
)


def mock_storage(responses, codings):
    """Helper to mock read_json in routes.analysis for dataset simulation."""
    def _mock_read(filename):
        if "responses" in filename:
            return responses
        if "coding" in filename:
            return codings
        return []
    return patch("routes.analysis.read_json", side_effect=_mock_read)


class TestInterRaterReliability(unittest.TestCase):

    # --------------------------------------------------------------------------
    # 1. Identical scores produce perfect absolute agreement (ICC = 1.0)
    # --------------------------------------------------------------------------
    def test_1_identical_scores_perfect_agreement(self):
        """Identical scores from both coders across varying items produce ICC = 1.0 and MAD = 0.0."""
        # Items vary across the scale [0.1, 0.5, 0.9], but coders agree exactly on each item
        matrix = [
            [0.1, 0.1],
            [0.5, 0.5],
            [0.9, 0.9],
        ]
        rounded_icc, raw_icc, reason = compute_icc_2_1(matrix)

        self.assertIsNone(reason)
        self.assertIsNotNone(raw_icc)
        self.assertEqual(raw_icc, 1.0)
        self.assertEqual(rounded_icc, 1.0)

        # Backward compatibility wrapper
        self.assertEqual(_calculate_icc_2_1(matrix), 1.0)

        # MAD must be 0.0
        mad = _mean_absolute_difference([0.1, 0.5, 0.9], [0.1, 0.5, 0.9])
        self.assertEqual(mad, 0.0)

    # --------------------------------------------------------------------------
    # 2. Known dataset matches verifiable benchmark result
    # --------------------------------------------------------------------------
    def test_2_known_dataset_reference_match(self):
        """
        Shrout & Fleiss (1979) Table 1 benchmark dataset:
        6 targets, 4 raters.
        Published ICC(2,1) = 0.29 (0.2898).
        """
        sf_table1_raw = [
            [9, 2, 5, 8],
            [6, 1, 3, 2],
            [8, 4, 6, 8],
            [7, 1, 2, 6],
            [10, 5, 6, 9],
            [6, 2, 4, 7],
        ]
        # Rescale to [0.0, 1.0] to satisfy rubric scale requirements
        sf_normalized = [[v / 10.0 for v in row] for row in sf_table1_raw]

        rounded_icc, raw_icc, reason = compute_icc_2_1(sf_normalized)
        self.assertIsNone(reason)
        self.assertIsNotNone(raw_icc)

        # Exact Shrout & Fleiss (1979) reference value is 0.28976...
        self.assertAlmostEqual(raw_icc, 0.28976, places=4)
        self.assertEqual(rounded_icc, 0.2898)

    # --------------------------------------------------------------------------
    # 3. Systematic score offsets evaluated by absolute agreement, not consistency
    # --------------------------------------------------------------------------
    def test_3_systematic_score_offsets_penalized(self):
        """
        Coders with identical relative rankings but systematic offsets are evaluated
        using absolute agreement. Consistency ICC would be 1.0, but ICC(2,1) < 1.0.
        """
        # Coder 2 is systematically 0.20 higher on every item
        c1 = [0.1, 0.4, 0.7]
        c2 = [0.3, 0.6, 0.9]
        matrix = [[c1[i], c2[i]] for i in range(len(c1))]

        rounded_icc, raw_icc, reason = compute_icc_2_1(matrix)
        self.assertIsNone(reason)

        # Pearson correlation = 1.0, Consistency ICC = 1.0,
        # but ICC(2,1) absolute agreement = 9/11 ~ 0.8182 < 1.0
        self.assertLess(raw_icc, 1.0)
        self.assertAlmostEqual(raw_icc, 9.0 / 11.0, places=4)
        self.assertEqual(rounded_icc, 0.8182)

        # MAD accurately reflects the 0.2 systematic offset
        mad = _mean_absolute_difference(c1, c2)
        self.assertEqual(mad, 0.2)

    # --------------------------------------------------------------------------
    # 4. T, I, and F calculated independently without leakage
    # --------------------------------------------------------------------------
    def test_4_dimensions_calculated_independently(self):
        """T, I, and F are calculated independently and do not share data or results."""
        pairs_t = [(0.1, 0.1), (0.5, 0.5), (0.9, 0.9)]  # Perfect agreement
        pairs_i = [(0.1, 0.9), (0.8, 0.2)]              # Severe disagreement
        pairs_f = [(0.1, 0.3), (0.4, 0.6), (0.7, 0.9)]  # Offset agreement

        dim_t = _calculate_dimension_agreement(pairs_t, "truth")
        dim_i = _calculate_dimension_agreement(pairs_i, "indeterminacy")
        dim_f = _calculate_dimension_agreement(pairs_f, "falsity")

        self.assertEqual(dim_t["icc"], 1.0)
        self.assertEqual(dim_t["status"], "acceptable")
        self.assertTrue(dim_t["threshold_passed"])

        self.assertLess(dim_i["icc"], 0.0)  # Severe disagreement -> negative ICC
        self.assertEqual(dim_i["status"], "below_threshold")
        self.assertFalse(dim_i["threshold_passed"])

        self.assertAlmostEqual(dim_f["icc"], 0.8182, places=3)
        self.assertEqual(dim_f["status"], "acceptable")

        # Independent sample sizes and MAD
        self.assertEqual(dim_t["n"], 3)
        self.assertEqual(dim_i["n"], 2)
        self.assertEqual(dim_f["n"], 3)

        self.assertEqual(dim_t["mean_absolute_difference"], 0.0)
        self.assertAlmostEqual(dim_i["mean_absolute_difference"], 0.7, places=4)
        self.assertEqual(dim_f["mean_absolute_difference"], 0.2)

    # --------------------------------------------------------------------------
    # 5. Scores paired using response IDs, order-independent
    # --------------------------------------------------------------------------
    def test_5_pairing_by_response_id_order_independent(self):
        """Records are matched strictly by stable response ID regardless of array ordering."""
        responses = [
            {"id": "resp-A", "experiment_id": "exp-1", "condition": "original"},
            {"id": "resp-B", "experiment_id": "exp-1", "condition": "original"},
            {"id": "resp-C", "experiment_id": "exp-1", "condition": "original"},
        ]

        # Natural order
        codings_natural = [
            {"response_id": "resp-A", "coder_id": "coder_1", "truth": 0.2, "indeterminacy": 0.1, "falsity": 0.7},
            {"response_id": "resp-B", "coder_id": "coder_1", "truth": 0.5, "indeterminacy": 0.2, "falsity": 0.3},
            {"response_id": "resp-C", "coder_id": "coder_1", "truth": 0.8, "indeterminacy": 0.1, "falsity": 0.1},
            {"response_id": "resp-A", "coder_id": "coder_2", "truth": 0.25, "indeterminacy": 0.15, "falsity": 0.65},
            {"response_id": "resp-B", "coder_id": "coder_2", "truth": 0.55, "indeterminacy": 0.25, "falsity": 0.25},
            {"response_id": "resp-C", "coder_id": "coder_2", "truth": 0.85, "indeterminacy": 0.15, "falsity": 0.05},
        ]

        # Scrambled order for coder 2
        codings_scrambled = [
            {"response_id": "resp-B", "coder_id": "coder_2", "truth": 0.55, "indeterminacy": 0.25, "falsity": 0.25},
            {"response_id": "resp-C", "coder_id": "coder_1", "truth": 0.8, "indeterminacy": 0.1, "falsity": 0.1},
            {"response_id": "resp-A", "coder_id": "coder_2", "truth": 0.25, "indeterminacy": 0.15, "falsity": 0.65},
            {"response_id": "resp-A", "coder_id": "coder_1", "truth": 0.2, "indeterminacy": 0.1, "falsity": 0.7},
            {"response_id": "resp-C", "coder_id": "coder_2", "truth": 0.85, "indeterminacy": 0.15, "falsity": 0.05},
            {"response_id": "resp-B", "coder_id": "coder_1", "truth": 0.5, "indeterminacy": 0.2, "falsity": 0.3},
        ]

        with mock_storage(responses, codings_natural):
            res_nat = get_inter_rater_agreement(experiment_id="exp-1", coder_1="coder_1", coder_2="coder_2")

        with mock_storage(responses, codings_scrambled):
            res_scr = get_inter_rater_agreement(experiment_id="exp-1", coder_1="coder_1", coder_2="coder_2")

        self.assertEqual(res_nat["dimensions"]["T"]["icc"], res_scr["dimensions"]["T"]["icc"])
        self.assertEqual(res_nat["dimensions"]["T"]["mean_absolute_difference"], res_scr["dimensions"]["T"]["mean_absolute_difference"])
        self.assertEqual(res_nat["dimensions"]["T"]["n"], res_scr["dimensions"]["T"]["n"])

    # --------------------------------------------------------------------------
    # 6. Responses with only one coder score excluded
    # --------------------------------------------------------------------------
    def test_6_single_coder_responses_excluded(self):
        """Responses scored by only one coder are excluded from reliability calculations."""
        responses = [{"id": f"r-{i}", "experiment_id": "exp-1"} for i in range(1, 6)]
        codings = [
            # Doubly coded: r-1, r-2, r-3
            {"response_id": "r-1", "coder_id": "c1", "truth": 0.1, "indeterminacy": 0.2, "falsity": 0.7},
            {"response_id": "r-1", "coder_id": "c2", "truth": 0.1, "indeterminacy": 0.2, "falsity": 0.7},
            {"response_id": "r-2", "coder_id": "c1", "truth": 0.4, "indeterminacy": 0.3, "falsity": 0.3},
            {"response_id": "r-2", "coder_id": "c2", "truth": 0.4, "indeterminacy": 0.3, "falsity": 0.3},
            {"response_id": "r-3", "coder_id": "c1", "truth": 0.9, "indeterminacy": 0.1, "falsity": 0.0},
            {"response_id": "r-3", "coder_id": "c2", "truth": 0.9, "indeterminacy": 0.1, "falsity": 0.0},
            # Singly coded: r-4 (c1 only), r-5 (c2 only)
            {"response_id": "r-4", "coder_id": "c1", "truth": 0.5, "indeterminacy": 0.5, "falsity": 0.5},
            {"response_id": "r-5", "coder_id": "c2", "truth": 0.6, "indeterminacy": 0.6, "falsity": 0.6},
        ]

        with mock_storage(responses, codings):
            res = get_inter_rater_agreement(experiment_id="exp-1", coder_1="c1", coder_2="c2")

            # Only r-1, r-2, r-3 are doubly coded
            self.assertEqual(res["total_shared_responses"], 3)
            self.assertEqual(res["dimensions"]["T"]["n"], 3)
            self.assertEqual(res["dimensions"]["T"]["icc"], 1.0)

    # --------------------------------------------------------------------------
    # 7. Missing, invalid, duplicate, and unmatched records handled safely
    # --------------------------------------------------------------------------
    def test_7_invalid_duplicate_and_missing_records(self):
        """Duplicates are deduplicated and invalid or missing values do not crash or corrupt scores."""
        # Score validator checks
        self.assertTrue(is_valid_score(0.0))
        self.assertTrue(is_valid_score(1.0))
        self.assertTrue(is_valid_score(0.5))
        self.assertFalse(is_valid_score(-0.01))
        self.assertFalse(is_valid_score(1.01))
        self.assertFalse(is_valid_score(None))
        self.assertFalse(is_valid_score("0.5"))
        self.assertFalse(is_valid_score(True))   # bool is int subclass in Python
        self.assertFalse(is_valid_score(float("nan")))
        self.assertFalse(is_valid_score(float("inf")))

        responses = [{"id": "r-1", "experiment_id": "exp-1"}, {"id": "r-2", "experiment_id": "exp-1"}]
        codings = [
            # Coder 1 duplicate for r-1: older record should be superseded by newer
            {"response_id": "r-1", "coder_id": "c1", "truth": 0.0, "indeterminacy": 0.0, "falsity": 0.0, "coded_at": "2026-01-01T00:00:00"},
            {"response_id": "r-1", "coder_id": "c1", "truth": 0.2, "indeterminacy": 0.4, "falsity": 0.4, "coded_at": "2026-01-02T00:00:00"},
            {"response_id": "r-1", "coder_id": "c2", "truth": 0.2, "indeterminacy": 0.4, "falsity": 0.4, "coded_at": "2026-01-01T00:00:00"},
            # r-2 has valid T, but invalid I for c2
            {"response_id": "r-2", "coder_id": "c1", "truth": 0.8, "indeterminacy": 0.3, "falsity": 0.2},
            {"response_id": "r-2", "coder_id": "c2", "truth": 0.8, "indeterminacy": None, "falsity": 0.2},
        ]

        with mock_storage(responses, codings):
            res = get_inter_rater_agreement(experiment_id="exp-1", coder_1="c1", coder_2="c2")

            # T has 2 valid responses (r-1 and r-2)
            self.assertEqual(res["dimensions"]["T"]["n"], 2)
            self.assertEqual(res["dimensions"]["T"]["icc"], 1.0)

            # I has only 1 valid pair (r-1), so ICC for I is unavailable
            self.assertEqual(res["dimensions"]["I"]["n"], 1)
            self.assertIsNone(res["dimensions"]["I"]["icc"])
            self.assertEqual(res["dimensions"]["I"]["status"], "insufficient_data")
            self.assertIn("at least 2", res["dimensions"]["I"]["unavailable_reason"])

    # --------------------------------------------------------------------------
    # 8. Insufficient observations & zero variance return explicit unavailable results
    # --------------------------------------------------------------------------
    def test_8_insufficient_and_zero_variance_unavailable(self):
        """Under n < 2 or zero variance across items, returns None with explicit explanation."""
        # Empty
        r_icc, raw_icc, reason = compute_icc_2_1([])
        self.assertIsNone(r_icc)
        self.assertIn("Insufficient", reason)

        # n = 1
        r_icc, raw_icc, reason = compute_icc_2_1([[0.5, 0.6]])
        self.assertIsNone(r_icc)
        self.assertIn("at least 2 shared responses required (found 1)", reason)

        # Zero variance across all items and coders (all scores identical to 0.5)
        r_icc, raw_icc, reason = compute_icc_2_1([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
        self.assertIsNone(r_icc)
        self.assertIn("Zero variance", reason)

    # --------------------------------------------------------------------------
    # 9. MAD calculated correctly on eligible matched responses
    # --------------------------------------------------------------------------
    def test_9_mad_calculated_correctly(self):
        """Mean Absolute Difference is the arithmetic mean of absolute coder differences."""
        c1 = [0.10, 0.35, 0.80]
        c2 = [0.20, 0.45, 0.95]
        # Differences: |0.10 - 0.20| = 0.10; |0.35 - 0.45| = 0.10; |0.80 - 0.95| = 0.15
        # Average: (0.10 + 0.10 + 0.15) / 3 = 0.35 / 3 = 0.116666...
        mad = _mean_absolute_difference(c1, c2)
        self.assertEqual(mad, round(0.35 / 3.0, 4))

        # Single eligible pair MAD
        mad_single = _mean_absolute_difference([0.2], [0.5])
        self.assertEqual(mad_single, 0.3)

    # --------------------------------------------------------------------------
    # 10. Response-level aggregate remains arithmetic mean of valid coder scores
    # --------------------------------------------------------------------------
    def test_10_score_aggregation_arithmetic_mean(self):
        """Multi-coder responses use arithmetic mean for experimental dimension scores."""
        responses = [
            {"id": "r-male", "experiment_id": "exp-1", "condition": "male"},
            {"id": "r-female", "experiment_id": "exp-1", "condition": "female"},
        ]
        codings = [
            # Two coders for r-male
            {"response_id": "r-male", "coder_id": "c1", "truth": 0.2, "indeterminacy": 0.4, "falsity": 0.4},
            {"response_id": "r-male", "coder_id": "c2", "truth": 0.8, "indeterminacy": 0.6, "falsity": 0.2},
            # One coder for r-female
            {"response_id": "r-female", "coder_id": "c1", "truth": 0.1, "indeterminacy": 0.2, "falsity": 0.7},
        ]

        with mock_storage(responses, codings):
            metrics = _compute_metrics("exp-1")

            # Male condition: (0.2 + 0.8) / 2 = 0.50
            self.assertEqual(metrics["male"]["avg_T"], 0.5)
            self.assertEqual(metrics["male"]["avg_I"], 0.5)
            self.assertEqual(metrics["male"]["avg_F"], 0.3)

            # Female condition: 0.10
            self.assertEqual(metrics["female"]["avg_T"], 0.1)

            # Bias score: |0.50 - 0.10| = 0.40
            self.assertEqual(metrics["bias_score"], 0.4)

    # --------------------------------------------------------------------------
    # 11. ICC(T) threshold (0.75) evaluated using unrounded value
    # --------------------------------------------------------------------------
    def test_11_threshold_evaluated_unrounded(self):
        """
        Threshold check uses unrounded ICC.
        An ICC value of 0.74997 (which rounds to 0.7500) must NOT pass the >= 0.75 gate.
        An ICC value of 0.75007 (which rounds to 0.7501) MUST pass the >= 0.75 gate.
        """
        # Exact construction: n=3, c1 = [0.1, 0.4, 0.7], c2 = [0.1+d, 0.4+d, 0.7+d]
        # raw_icc = 0.18 / (0.18 + d^2)
        # For raw_icc = 0.74997: d^2 = 0.18/0.74997 - 0.18 => d ~ 0.24496857
        d_just_below = math.sqrt(0.18 / 0.74997 - 0.18)
        matrix_below = [[0.1, 0.1 + d_just_below], [0.4, 0.4 + d_just_below], [0.7, 0.7 + d_just_below]]
        rounded_below, raw_below, _ = compute_icc_2_1(matrix_below)

        # Proves it rounds to 0.75, but raw is strictly < 0.75
        self.assertEqual(rounded_below, 0.75)
        self.assertLess(raw_below, 0.75)

        pairs_below = [(row[0], row[1]) for row in matrix_below]
        res_below = _calculate_dimension_agreement(pairs_below, "truth", threshold=0.75)
        self.assertFalse(res_below["threshold_passed"])
        self.assertEqual(res_below["status"], "below_threshold")

        # End-to-end check via get_inter_rater_agreement for below-threshold case
        responses_below = [{"id": f"r-{i}", "experiment_id": "exp-test"} for i in range(3)]
        codings_below = []
        for i, row in enumerate(matrix_below):
            codings_below.append({"response_id": f"r-{i}", "coder_id": "c1", "truth": row[0], "indeterminacy": 0.5, "falsity": 0.5})
            codings_below.append({"response_id": f"r-{i}", "coder_id": "c2", "truth": row[1], "indeterminacy": 0.5, "falsity": 0.5})

        with mock_storage(responses_below, codings_below):
            api_res_below = get_inter_rater_agreement(experiment_id="exp-test", coder_1="c1", coder_2="c2")
            self.assertEqual(api_res_below["dimensions"]["T"]["icc"], 0.75)
            self.assertLess(api_res_below["dimensions"]["T"]["unrounded_icc"], 0.75)
            self.assertFalse(api_res_below["dimensions"]["T"]["threshold_passed"])
            self.assertEqual(api_res_below["dimensions"]["T"]["status"], "below_threshold")
            self.assertFalse(api_res_below["reliability_gate"]["passed"])
            self.assertEqual(api_res_below["reliability_gate"]["status"], "not_passed")

        # Now test just above: d = 0.2449 => raw_icc ~ 0.75007 >= 0.75
        matrix_above = [[0.1, 0.1 + 0.2449], [0.4, 0.4 + 0.2449], [0.7, 0.7 + 0.2449]]
        rounded_above, raw_above, _ = compute_icc_2_1(matrix_above)
        self.assertGreaterEqual(raw_above, 0.75)

        pairs_above = [(row[0], row[1]) for row in matrix_above]
        res_above = _calculate_dimension_agreement(pairs_above, "truth", threshold=0.75)
        self.assertTrue(res_above["threshold_passed"])
        self.assertEqual(res_above["status"], "acceptable")

        # End-to-end check via get_inter_rater_agreement for above-threshold case
        responses_above = [{"id": f"r-{i}", "experiment_id": "exp-test"} for i in range(3)]
        codings_above = []
        for i, row in enumerate(matrix_above):
            codings_above.append({"response_id": f"r-{i}", "coder_id": "c1", "truth": row[0], "indeterminacy": 0.5, "falsity": 0.5})
            codings_above.append({"response_id": f"r-{i}", "coder_id": "c2", "truth": row[1], "indeterminacy": 0.5, "falsity": 0.5})

        with mock_storage(responses_above, codings_above):
            api_res_above = get_inter_rater_agreement(experiment_id="exp-test", coder_1="c1", coder_2="c2")
            self.assertGreaterEqual(api_res_above["dimensions"]["T"]["unrounded_icc"], 0.75)
            self.assertTrue(api_res_above["dimensions"]["T"]["threshold_passed"])
            self.assertEqual(api_res_above["dimensions"]["T"]["status"], "acceptable")
            self.assertTrue(api_res_above["reliability_gate"]["passed"])
            self.assertEqual(api_res_above["reliability_gate"]["status"], "passed")

    # --------------------------------------------------------------------------
    # 12. Unavailable ICC does not pass reliability gate
    # --------------------------------------------------------------------------
    def test_12_unavailable_icc_does_not_pass_gate(self):
        """When ICC(T) cannot be calculated, the reliability gate is not passed and marked unevaluable."""
        responses = [{"id": "r-1", "experiment_id": "exp-1"}]
        codings = [
            {"response_id": "r-1", "coder_id": "c1", "truth": 0.5, "indeterminacy": 0.5, "falsity": 0.5},
            {"response_id": "r-1", "coder_id": "c2", "truth": 0.5, "indeterminacy": 0.5, "falsity": 0.5},
        ]

        with mock_storage(responses, codings):
            res = get_inter_rater_agreement(experiment_id="exp-1", coder_1="c1", coder_2="c2")

            gate = res["reliability_gate"]
            self.assertFalse(gate["passed"])
            self.assertFalse(gate["evaluable"])
            self.assertEqual(gate["status"], "unevaluable")
            self.assertIsNone(gate["icc"])
            self.assertIn("unavailable", gate["message"].lower())

    # --------------------------------------------------------------------------
    # 13. API returns consistent values and sample counts on existing data
    # --------------------------------------------------------------------------
    def test_13_api_production_dataset_consistent(self):
        """Tests the actual dataset on disk to ensure consistent counts, valid stats, and gate status."""
        res = get_inter_rater_agreement()
        if res["total_shared_responses"] == 0:
            self.assertEqual(res["total_shared_responses"], 0)
            self.assertFalse(res["reliability_gate"]["passed"])
            for dim_key in ["T", "I", "F"]:
                dim = res["dimensions"][dim_key]
                self.assertIn("icc", dim)
                self.assertFalse(dim["evaluable"])
            return

        self.assertEqual(res["total_shared_responses"], 10)

        # Verify all 4 required fields across T, I, and F dimensions
        for dim_key in ["T", "I", "F"]:
            dim = res["dimensions"][dim_key]
            # 1. ICC(2,1)
            self.assertIn("icc", dim)
            self.assertIsNotNone(dim["icc"])
            self.assertIn("unrounded_icc", dim)
            self.assertTrue(dim["is_primary_metric"])

            # 2. MAD
            self.assertIn("mean_absolute_difference", dim)
            self.assertIsNotNone(dim["mean_absolute_difference"])

            # 3. Number of shared responses
            self.assertIn("n", dim)
            self.assertEqual(dim["n"], 10)

            # 4. Clear reliability status and evaluability
            self.assertIn("evaluable", dim)
            self.assertTrue(dim["evaluable"])
            self.assertIn("status", dim)
            self.assertIn("status_label", dim)

        # Dimension T specific gate
        dim_t = res["dimensions"]["T"]
        self.assertEqual(dim_t["status"], "acceptable")
        self.assertTrue(dim_t["threshold_passed"])
        self.assertGreaterEqual(dim_t["icc"], 0.75)
        self.assertAlmostEqual(dim_t["icc"], 0.9939, places=4)

        gate = res["reliability_gate"]
        self.assertTrue(gate["passed"])
        self.assertTrue(gate["evaluable"])
        self.assertEqual(gate["status"], "passed")
        self.assertEqual(gate["threshold"], 0.75)

    # --------------------------------------------------------------------------
    # 14. Section 6 Consistency across all edge cases (n=0, n=1, zero variance)
    # --------------------------------------------------------------------------
    def test_14_edge_cases_consistency_across_dimensions(self):
        """
        Verify evaluable, status, status_label, threshold_passed across:
        - n = 0 (empty): insufficient_data, evaluable=False
        - n = 1: insufficient_data, evaluable=False
        - n >= 2 zero variance: unevaluable, evaluable=False
        """
        for dim_name in ["truth", "indeterminacy", "falsity"]:
            # Case A: n = 0
            dim_0 = _calculate_dimension_agreement([], dim_name)
            self.assertFalse(dim_0["evaluable"])
            self.assertIsNone(dim_0["icc"])
            self.assertIsNone(dim_0["unrounded_icc"])
            self.assertIsNone(dim_0["mean_absolute_difference"])
            self.assertEqual(dim_0["status"], "insufficient_data")
            self.assertEqual(dim_0["status_label"], "Insufficient data")
            self.assertFalse(dim_0["threshold_passed"])
            self.assertEqual(dim_0["n"], 0)
            self.assertIn("no eligible shared responses", dim_0["unavailable_reason"])

            # Case B: n = 1
            dim_1 = _calculate_dimension_agreement([(0.2, 0.5)], dim_name)
            self.assertFalse(dim_1["evaluable"])
            self.assertIsNone(dim_1["icc"])
            self.assertIsNone(dim_1["unrounded_icc"])
            self.assertEqual(dim_1["mean_absolute_difference"], 0.3)
            self.assertEqual(dim_1["status"], "insufficient_data")
            self.assertEqual(dim_1["status_label"], "Insufficient data")
            self.assertFalse(dim_1["threshold_passed"])
            self.assertEqual(dim_1["n"], 1)
            self.assertIn("at least 2 shared responses required (found 1)", dim_1["unavailable_reason"])

            # Case C: n >= 2 zero-variance
            pairs_zero_var = [(0.5, 0.5), (0.5, 0.5), (0.5, 0.5)]
            dim_zv = _calculate_dimension_agreement(pairs_zero_var, dim_name)
            self.assertFalse(dim_zv["evaluable"])
            self.assertIsNone(dim_zv["icc"])
            self.assertIsNone(dim_zv["unrounded_icc"])
            self.assertEqual(dim_zv["mean_absolute_difference"], 0.0)
            self.assertEqual(dim_zv["status"], "unevaluable")
            self.assertEqual(dim_zv["status_label"], "Unevaluable")
            self.assertFalse(dim_zv["threshold_passed"])
            self.assertEqual(dim_zv["n"], 3)
            self.assertIn("Zero variance", dim_zv["unavailable_reason"])

    # --------------------------------------------------------------------------
    # 15. Existing tests for unrelated functionality continue to pass
    # --------------------------------------------------------------------------
    def test_15_gender_swap_unaffected(self):
        """Confirms gender_swap rendering remains untouched and functioning."""
        from services.gender_swap import render_scenario
        template = "The {PC_NOUN} blamed {PC_REFLEXIVE}."
        self.assertEqual(render_scenario(template, "male"), "The man blamed himself.")
        self.assertEqual(render_scenario(template, "female"), "The woman blamed herself.")


if __name__ == "__main__":
    unittest.main()
