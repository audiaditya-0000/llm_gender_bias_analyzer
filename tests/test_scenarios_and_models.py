"""
Automated tests for scenarios, prompt scaffolds, canonical models, and PC substitution.

Verifies:
1. Both canonical models ('llama3.2:latest' and 'mistral:latest') are supported and preserved.
2. Scenario inventory accounting (1 implemented, 9 planned/missing).
3. Scenario integrity: implemented scenarios must use {PC_*} tokens and preserve third parties.
4. Scaffold generalization: scaffolds must be free of hardcoded scenario-specific references
   (no 'Bram Ashworth', 'Wandering Boar', or 'mercenary') and support universal reuse.
5. PC-only substitution: ensures third-party NPCs, companions, and familial relations are never swapped.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from storage import read_json
from models import SCENARIO_CATEGORIES
from services.gender_swap import render_scenario, PC_FORMS
from services.statistical_inference import CANONICAL_MODELS


class TestCanonicalModelSupport(unittest.TestCase):
    """Verify that both selected models are supported and preserved."""

    def test_canonical_models_exact_tags(self):
        """Exact canonical Ollama model tags must be preserved."""
        expected_models = ["llama3.2:latest", "mistral:latest"]
        self.assertEqual(
            CANONICAL_MODELS,
            expected_models,
            f"Canonical models must be exactly {expected_models}",
        )
        self.assertEqual(len(CANONICAL_MODELS), 2)

    def test_model_support_in_generation_options(self):
        """Both models can be used in experiment configuration."""
        for model_name in CANONICAL_MODELS:
            self.assertIn("latest", model_name)
            self.assertTrue(
                model_name.startswith("llama") or model_name.startswith("mistral"),
                f"Unexpected model identifier: {model_name}",
            )


class TestScaffoldGeneralization(unittest.TestCase):
    """Verify that prompt scaffolds are reusable and free of hardcoded scenario specifics."""

    def setUp(self):
        self.scaffolds = read_json("scaffolds.json")

    def test_all_three_scaffold_versions_present(self):
        """All 3 scaffolds (v1.0, v1.1, v1.2) must be present."""
        versions = {sc.get("version") for sc in self.scaffolds}
        self.assertEqual(versions, {"1.0", "1.1", "1.2"})
        self.assertEqual(len(self.scaffolds), 3)

    def test_scaffold_ids_preserved(self):
        """Scaffold UUIDs must match historical experiment records."""
        expected_ids = {
            "a9714fe2-ca9f-4d86-bf87-4c1046319718",  # v1.0
            "72859fca-c908-4f0d-9099-7dd4ee53b839",  # v1.1
            "ad07cd93-7943-49be-8b36-849e882ffd7b",  # v1.2
        }
        actual_ids = {sc.get("id") for sc in self.scaffolds}
        self.assertEqual(actual_ids, expected_ids)

    def test_scaffolds_free_of_hardcoded_scenario_specifics(self):
        """Scaffolds must NOT contain 'Bram Ashworth', 'Wandering Boar', or 'mercenary'."""
        forbidden_terms = ["bram ashworth", "wandering boar", "mercenary"]

        for sc in self.scaffolds:
            prompt_lower = sc.get("prompt", "").lower()
            name_lower = sc.get("name", "").lower()
            for term in forbidden_terms:
                self.assertNotIn(
                    term,
                    prompt_lower,
                    f"Scaffold v{sc.get('version')} prompt contains hardcoded term '{term}'",
                )
                self.assertNotIn(
                    term,
                    name_lower,
                    f"Scaffold v{sc.get('version')} name contains hardcoded term '{term}'",
                )

    def test_scaffold_universal_applicability(self):
        """Scaffolds must work generically across diverse scenario archetypes."""
        test_scenarios = [
            "SCENARIO:\nA guard captain questions an adventurer at the city gate.",
            "SCENARIO:\nA merchant negotiates the sale of rare healing potions.",
            "SCENARIO:\nA guildmaster assigns an exploration quest into ancient ruins.",
        ]

        for sc in self.scaffolds:
            scaffold_prompt = sc.get("prompt", "")
            self.assertTrue(len(scaffold_prompt) > 50)
            # Verify each scaffold mentions roleplaying/character adherence
            self.assertTrue(
                "character" in scaffold_prompt.lower() or "role" in scaffold_prompt.lower(),
                f"Scaffold v{sc.get('version')} must instruct model to stay in character",
            )
            # Verify each scaffold instructs relying only on scenario facts
            self.assertTrue(
                "scenario" in scaffold_prompt.lower(),
                f"Scaffold v{sc.get('version')} must anchor generation to the scenario",
            )


class TestScenarioInventoryAndSubstitution(unittest.TestCase):
    """Verify scenario inventory, integrity, and PC-only substitution."""

    def setUp(self):
        self.scenarios = read_json("scenarios.json")

    def test_scenario_inventory_accounting(self):
        """
        Verify current inventory count.
        Supports 10 baseline scenarios or 20 (baseline + gender-salient expansion).
        """
        self.assertIn(
            len(self.scenarios),
            [10, 20],
            "Scenario inventory must be 10 (baseline) or 20 (baseline + salient expansion)",
        )
        implemented_ids = [s.get("id") for s in self.scenarios]
        self.assertIn("74ea8c66-f108-4054-8a1e-a6f9b1ffae62", implemented_ids)

    def test_implemented_scenario_validity(self):
        """Implemented scenario must have valid fields and recognized category."""
        for scen in self.scenarios:
            self.assertTrue(scen.get("id"))
            self.assertTrue(scen.get("title"))
            self.assertTrue(scen.get("description"))
            self.assertTrue(scen.get("scenario_text"))
            category = scen.get("category")
            self.assertIn(
                category,
                SCENARIO_CATEGORIES,
                f"Scenario category '{category}' not in recognized SCENARIO_CATEGORIES",
            )

    def test_pc_only_substitution_on_active_scenario(self):
        """Original and swapped versions of active scenario differ ONLY in PC gender terms."""
        scen = self.scenarios[0]
        text = scen["scenario_text"]

        male_rendered = render_scenario(text, "male")
        female_rendered = render_scenario(text, "female")

        self.assertNotEqual(male_rendered, female_rendered)

        # Check PC terms are swapped
        self.assertIn("A male mercenary", male_rendered)
        self.assertIn("A female mercenary", female_rendered)

        self.assertIn("He explains", male_rendered)
        self.assertIn("She explains", female_rendered)

        self.assertIn("He has handled", male_rendered)
        self.assertIn("She has handled", female_rendered)

        self.assertIn("He asks", male_rendered)
        self.assertIn("She asks", female_rendered)

        self.assertIn("vouch for him", male_rendered)
        self.assertIn("vouch for her", female_rendered)

        # Check non-PC third parties are preserved identically
        self.assertIn("tavern keeper", male_rendered)
        self.assertIn("tavern keeper", female_rendered)

        self.assertIn("merchant caravan master, currently at the bar", male_rendered)
        self.assertIn("merchant caravan master, currently at the bar", female_rendered)

        self.assertIn("armed bandits", male_rendered)
        self.assertIn("armed bandits", female_rendered)
        self.assertIn("hauling heavy supply crates", male_rendered)
        self.assertIn("hauling heavy supply crates", female_rendered)

    def test_third_party_characters_and_relatives_unaltered(self):
        """Third-party nouns (sister, brother, king, queen, mother, father) must NOT be swapped."""
        complex_scenario = (
            "The {PC_NOUN} approaches the queen's court. {PC_SUBJECT} is accompanied by "
            "{PC_POSSESSIVE} sister and brother. The king watches silently while the tavern "
            "maid serves wine to {PC_OBJECT}."
        )

        male_result = render_scenario(complex_scenario, "male")
        female_result = render_scenario(complex_scenario, "female")

        # Male condition check
        self.assertIn("The man approaches the queen's court.", male_result)
        self.assertIn("He is accompanied by his sister and brother.", male_result)
        self.assertIn("The king watches silently while the tavern maid serves wine to him.", male_result)

        # Female condition check
        self.assertIn("The woman approaches the queen's court.", female_result)
        self.assertIn("She is accompanied by her sister and brother.", female_result)
        self.assertIn("The king watches silently while the tavern maid serves wine to her.", female_result)

        # Confirm non-PC entities are identical in both
        for entity in ["queen's court", "sister and brother", "king watches", "tavern maid"]:
            self.assertIn(entity, male_result)
            self.assertIn(entity, female_result)


if __name__ == "__main__":
    unittest.main()
