"""
Unit and integration tests for multi-coder queue partitioning and blinding.

Verifies:
1. 20% of pairs form the dual-coded overlap pool (assigned to both Coder 1 and Coder 2).
2. The remaining 80% of pairs are evenly split (50/50) between Coder 1 and Coder 2.
3. Neither coder can view the other coder's exclusive pairs.
4. Within the overlap pool, ratings from one coder are never visible to the other coder.
5. Scenario context served to coders is gender-neutral with no PC token leaks.
6. Model tags are omitted from blind pair outputs.
7. Mutual analysis metrics remain consolidated and study-wide.
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from routes.coding import get_blind_responses, _neutralize_text, save_coding
from routes.analysis import _compute_metrics
from models import CodingCreate


class TestMultiCoderQueuePartitioning(unittest.TestCase):
    """Test multi-coder queue assignment and 20% overlap calculation."""

    def setUp(self):
        # Create a synthetic dataset of 20 paired responses (10 replicates, 20 responses)
        # for an experiment to verify exact 20% overlap and 50/50 split.
        self.mock_responses = []
        for rep in range(1, 11):  # 10 pairs
            pid = f"pair_{rep:02d}"
            # Version A (original / male)
            self.mock_responses.append({
                "id": f"resp_{rep:02d}_orig",
                "pair_id": pid,
                "experiment_id": "exp_synth_01",
                "scenario_id": "scen_01",
                "scaffold_id": "scaf_01",
                "model": "llama3.2:latest",
                "condition": "original",
                "replicate_number": rep,
                "scenario_prompt": "SCENARIO: Bram Ashworth walked into the tavern...",
                "generated_response": f"Response for pair {rep} original",
            })
            # Version B (swapped / female)
            self.mock_responses.append({
                "id": f"resp_{rep:02d}_swap",
                "pair_id": pid,
                "experiment_id": "exp_synth_01",
                "scenario_id": "scen_01",
                "scaffold_id": "scaf_01",
                "model": "llama3.2:latest",
                "condition": "swapped",
                "replicate_number": rep,
                "scenario_prompt": "SCENARIO: Branwen Ashworth walked into the tavern...",
                "generated_response": f"Response for pair {rep} swapped",
            })

        self.mock_scenarios = [
            {
                "id": "scen_01",
                "title": "Tavern Confrontation",
                "description": "A {PC_ADJECTIVE} mercenary asks the tavern keeper to vouch for {PC_OBJECT}.",
                "scenario_text": "The {PC_NOUN} walked into the tavern.",
            }
        ]

        self.mock_codings = []

    def test_20_percent_overlap_and_50_50_split(self):
        """10 pairs total: idx % 5 == 0 -> 2 overlap pairs (20%), 4 for Coder 1, 4 for Coder 2."""
        with patch("routes.coding.read_json") as mock_read:
            def side_effect(filename):
                if filename == "responses.json":
                    return self.mock_responses
                elif filename == "scenarios.json":
                    return self.mock_scenarios
                elif filename == "coding.json":
                    return self.mock_codings
                return []
            mock_read.side_effect = side_effect

            # 1. Total pool (all pairs)
            all_res = get_blind_responses(experiment_id="exp_synth_01", coder_id=None)
            self.assertEqual(all_res["total"], 10)
            overlap_pairs = [p for p in all_res["data"] if p["is_overlap"]]
            self.assertEqual(len(overlap_pairs), 2)  # Exactly 20% of 10
            self.assertEqual(all_res["overlap_count"], 2)

            # 2. Coder 1 queue
            c1_res = get_blind_responses(experiment_id="exp_synth_01", coder_id="coder_1")
            # Coder 1 sees 2 overlap + 4 exclusive = 6 pairs (60%)
            self.assertEqual(c1_res["total"], 6)
            c1_overlap = [p for p in c1_res["data"] if p["is_overlap"]]
            c1_exclusive = [p for p in c1_res["data"] if not p["is_overlap"]]
            self.assertEqual(len(c1_overlap), 2)
            self.assertEqual(len(c1_exclusive), 4)

            # 3. Coder 2 queue
            c2_res = get_blind_responses(experiment_id="exp_synth_01", coder_id="coder_2")
            # Coder 2 sees 2 overlap + 4 exclusive = 6 pairs (60%)
            self.assertEqual(c2_res["total"], 6)
            c2_overlap = [p for p in c2_res["data"] if p["is_overlap"]]
            c2_exclusive = [p for p in c2_res["data"] if not p["is_overlap"]]
            self.assertEqual(len(c2_overlap), 2)
            self.assertEqual(len(c2_exclusive), 4)

            # 4. Exclusivity check: Coder 1 exclusive pair IDs must not appear in Coder 2 queue
            c1_pair_ids = {p["pair_id"] for p in c1_exclusive}
            c2_pair_ids = {p["pair_id"] for p in c2_exclusive}
            self.assertEqual(len(c1_pair_ids.intersection(c2_pair_ids)), 0)

            # 5. Overlap check: Both coders see the exact same 2 overlap pairs
            c1_overlap_ids = {p["pair_id"] for p in c1_overlap}
            c2_overlap_ids = {p["pair_id"] for p in c2_overlap}
            self.assertEqual(c1_overlap_ids, c2_overlap_ids)

    def test_independent_blinding_in_overlap_set(self):
        """Ratings submitted by Coder 2 are NEVER visible in Coder 1's queue."""
        # Suppose Coder 2 has already coded pair_01 (an overlap pair)
        mock_codings_with_c2 = [
            {
                "id": "code_01_a",
                "response_id": "resp_01_orig",
                "coder_id": "coder_2",
                "truth": 0.85,
                "indeterminacy": 0.10,
                "falsity": 0.05,
                "reasoning_notes": "Highly stereotypic",
            },
            {
                "id": "code_01_b",
                "response_id": "resp_01_swap",
                "coder_id": "coder_2",
                "truth": 0.20,
                "indeterminacy": 0.15,
                "falsity": 0.65,
                "reasoning_notes": "Counter-stereotypic",
            },
        ]

        with patch("routes.coding.read_json") as mock_read:
            def side_effect(filename):
                if filename == "responses.json":
                    return self.mock_responses
                elif filename == "scenarios.json":
                    return self.mock_scenarios
                elif filename == "coding.json":
                    return mock_codings_with_c2
                return []
            mock_read.side_effect = side_effect

            # Request queue for Coder 1
            c1_res = get_blind_responses(experiment_id="exp_synth_01", coder_id="coder_1")
            pair_1_c1 = next(p for p in c1_res["data"] if p["pair_id"] == "pair_01")
            
            # Coder 1 MUST NOT see Coder 2's ratings
            self.assertIsNone(pair_1_c1["version_a"]["coding"])
            self.assertIsNone(pair_1_c1["version_b"]["coding"])
            self.assertFalse(pair_1_c1["is_coded"])

            # But Coder 2 requesting their own queue sees their ratings
            c2_res = get_blind_responses(experiment_id="exp_synth_01", coder_id="coder_2")
            pair_1_c2 = next(p for p in c2_res["data"] if p["pair_id"] == "pair_01")
            self.assertIsNotNone(pair_1_c2["version_a"]["coding"])
            self.assertIsNotNone(pair_1_c2["version_b"]["coding"])
            c2_truths = {
                pair_1_c2["version_a"]["coding"]["truth"],
                pair_1_c2["version_b"]["coding"]["truth"],
            }
            self.assertEqual(c2_truths, {0.85, 0.20})
            self.assertTrue(pair_1_c2["is_coded"])

    def test_scenario_context_gender_neutralization(self):
        """Scenario context served to coders replaces explicit PC tokens and avoids gender leakage."""
        raw_desc = "A {PC_ADJECTIVE} mercenary asks the tavern keeper to vouch for {PC_OBJECT}."
        neutralized = _neutralize_text(raw_desc)
        self.assertNotIn("{PC_", neutralized)
        self.assertIn("capable", neutralized)
        self.assertIn("them", neutralized)

        with patch("routes.coding.read_json") as mock_read:
            def side_effect(filename):
                if filename == "responses.json":
                    return self.mock_responses[:2]
                elif filename == "scenarios.json":
                    return self.mock_scenarios
                elif filename == "coding.json":
                    return []
                return []
            mock_read.side_effect = side_effect

            res = get_blind_responses(coder_id="coder_1")
            pair = res["data"][0]

            # Neutral scenario context provided
            self.assertEqual(pair["scenario_title"], "Tavern Confrontation")
            self.assertEqual(pair["scenario_description"], "A capable mercenary asks the tavern keeper to vouch for them.")
            # Raw scenario prompt with gendered name is replaced
            self.assertNotIn("Bram Ashworth", pair["scenario_prompt"])
            # Model identifier is omitted
            self.assertNotIn("model", pair)

    def test_mutual_analysis_aggregation(self):
        """Analysis aggregates ratings across coders: dual-coded ratings are averaged, single ratings used directly."""
        codings_data = [
            # Dual-coded male response: Coder 1 = 0.8, Coder 2 = 0.6 -> avg = 0.7
            {"response_id": "r_m_1", "coder_id": "coder_1", "truth": 0.8, "indeterminacy": 0.1, "falsity": 0.1},
            {"response_id": "r_m_1", "coder_id": "coder_2", "truth": 0.6, "indeterminacy": 0.2, "falsity": 0.2},
            # Single-coded female response (Coder 1 only): truth = 0.3
            {"response_id": "r_f_1", "coder_id": "coder_1", "truth": 0.3, "indeterminacy": 0.2, "falsity": 0.5},
        ]
        responses_data = [
            {"id": "r_m_1", "condition": "original", "experiment_id": "exp_1"},
            {"id": "r_f_1", "condition": "swapped", "experiment_id": "exp_1"},
        ]

        with patch("routes.analysis.read_json") as mock_read:
            def side_effect(filename):
                if filename == "responses.json":
                    return responses_data
                elif filename == "coding.json":
                    return codings_data
                return []
            mock_read.side_effect = side_effect

            metrics = _compute_metrics(experiment_id="exp_1")
            # Male avg T = (0.8 + 0.6) / 2 = 0.7
            self.assertEqual(metrics["male"]["avg_T"], 0.7)
            # Female avg T = 0.3
            self.assertEqual(metrics["female"]["avg_T"], 0.3)
            # Bias score = |0.7 - 0.3| = 0.4
            self.assertEqual(metrics["bias_score"], 0.4)
            # Independent of any active coder selection in UI
            self.assertEqual(metrics["total_coded"], 2)
            self.assertEqual(metrics["total_coding_records"], 3)


if __name__ == "__main__":
    unittest.main()
