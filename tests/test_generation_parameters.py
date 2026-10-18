"""
Automated tests for Ollama generation parameters.

Verifies:
1. Outgoing HTTP request payload to Ollama /api/chat contains top_k=40 and repeat_penalty=1.1 by default.
2. Custom generation parameters are not discarded or overwritten.
3. Both experimental conditions ("original" and "swapped") pass top_k and repeat_penalty to Ollama.
4. All configured models (e.g., llama3.2:latest, mistral:latest) receive top_k and repeat_penalty.
5. Historical experiments without explicit top_k/repeat_penalty default safely to 40 and 1.1.
6. Pydantic models (ExperimentCreate, Experiment) parse and default top_k and repeat_penalty correctly.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from models import ExperimentCreate, Experiment
from services.ollama import generate, OLLAMA_BASE_URL
from routes.runner import _run_experiment


class TestOllamaGenerationRequestPayload(unittest.IsolatedAsyncioTestCase):
    """Verify that generate() constructs the exact HTTP request expected by Ollama."""

    async def test_default_generation_parameters_included(self):
        """Default call to generate() must include top_k=40 and repeat_penalty=1.1 in options."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Sample generated response"}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("services.ollama.httpx.AsyncClient", return_value=mock_client):
            result = await generate(
                scaffold="System persona instructions.",
                scenario="SCENARIO:\nA character acts.",
                model="llama3.2:latest",
                temperature=0.7,
                top_p=0.9,
                max_tokens=512,
                seed=42,
            )

        self.assertEqual(result, "Sample generated response")
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify target endpoint
        self.assertEqual(call_args.args[0], f"{OLLAMA_BASE_URL}/api/chat")

        payload = call_args.kwargs["json"]
        self.assertEqual(payload["model"], "llama3.2:latest")
        self.assertFalse(payload["stream"])

        options = payload["options"]
        # Required parameters under audit:
        self.assertIn("top_k", options, "top_k must be included in outgoing Ollama options")
        self.assertEqual(options["top_k"], 40)
        self.assertIn("repeat_penalty", options, "repeat_penalty must be included in outgoing Ollama options")
        self.assertEqual(options["repeat_penalty"], 1.1)

        # Baseline generation options
        self.assertEqual(options["temperature"], 0.7)
        self.assertEqual(options["top_p"], 0.9)
        self.assertEqual(options["num_predict"], 512)
        self.assertEqual(options["seed"], 42)

        # Verify messages structure
        messages = payload["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "System persona instructions.")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "SCENARIO:\nA character acts.")

    async def test_custom_parameters_not_overwritten_or_discarded(self):
        """Custom generation parameters must be faithfully passed without being overwritten."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Custom response"}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("services.ollama.httpx.AsyncClient", return_value=mock_client):
            await generate(
                scaffold="Scaffold",
                scenario="Scenario",
                model="mistral:latest",
                temperature=0.4,
                top_p=0.85,
                max_tokens=256,
                top_k=25,
                repeat_penalty=1.35,
                seed=999,
            )

        payload = mock_client.post.call_args.kwargs["json"]
        options = payload["options"]

        self.assertEqual(payload["model"], "mistral:latest")
        self.assertEqual(options["top_k"], 25)
        self.assertEqual(options["repeat_penalty"], 1.35)
        self.assertEqual(options["temperature"], 0.4)
        self.assertEqual(options["top_p"], 0.85)
        self.assertEqual(options["num_predict"], 256)
        self.assertEqual(options["seed"], 999)


class TestRunnerGenerationPath(unittest.IsolatedAsyncioTestCase):
    """Verify that backend/routes/runner.py correctly passes parameters across conditions and models."""

    async def test_runner_passes_parameters_to_both_conditions(self):
        """_run_experiment must invoke generate() with top_k and repeat_penalty for both original and swapped conditions."""
        sample_experiment = {
            "id": "exp-test-params",
            "scenario_id": "scen-1",
            "scaffold_id": "scaff-1",
            "model": "llama3.2:latest",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 512,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "seed": 42,
            "num_replicates": 1,
            "status": "configured",
        }
        sample_scenario = {
            "id": "scen-1",
            "title": "Test Scenario",
            "scenario_text": "A {PC_ADJECTIVE} character walks in. {PC_SUBJECT} speaks.",
        }
        sample_scaffold = {
            "id": "scaff-1",
            "name": "Test Scaffold",
            "prompt": "You are an NPC.",
            "version": "1.0",
        }

        generated_calls = []

        async def mock_generate(**kwargs):
            generated_calls.append(kwargs)
            return "Simulated response"

        with patch("routes.runner.find_by_id") as mock_find, \
             patch("routes.runner.generate", side_effect=mock_generate), \
             patch("routes.runner.append_json"), \
             patch("routes.runner._update_status"):

            def mock_find_impl(filename, item_id):
                if "experiments" in filename:
                    return sample_experiment
                if "scenarios" in filename:
                    return sample_scenario
                if "scaffolds" in filename:
                    return sample_scaffold
                return None

            mock_find.side_effect = mock_find_impl

            await _run_experiment("exp-test-params")

        # 1 replicate * 2 conditions = 2 calls
        self.assertEqual(len(generated_calls), 2)

        # Call 1: "original" (male)
        call_orig = generated_calls[0]
        self.assertEqual(call_orig["model"], "llama3.2:latest")
        self.assertEqual(call_orig["top_k"], 40)
        self.assertEqual(call_orig["repeat_penalty"], 1.1)
        self.assertEqual(call_orig["temperature"], 0.7)
        self.assertEqual(call_orig["top_p"], 0.9)
        self.assertEqual(call_orig["max_tokens"], 512)
        self.assertIn("A male character", call_orig["scenario"])

        # Call 2: "swapped" (female)
        call_swap = generated_calls[1]
        self.assertEqual(call_swap["model"], "llama3.2:latest")
        self.assertEqual(call_swap["top_k"], 40)
        self.assertEqual(call_swap["repeat_penalty"], 1.1)
        self.assertEqual(call_swap["temperature"], 0.7)
        self.assertEqual(call_swap["top_p"], 0.9)
        self.assertEqual(call_swap["max_tokens"], 512)
        self.assertIn("A female character", call_swap["scenario"])

    async def test_runner_defaults_historical_experiments_without_keys(self):
        """Historical experiment records lacking top_k/repeat_penalty keys must default to 40 and 1.1."""
        historical_experiment = {
            "id": "exp-historical",
            "scenario_id": "scen-1",
            "scaffold_id": "scaff-1",
            "model": "mistral:latest",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 512,
            # top_k and repeat_penalty omitted as in existing data/experiments.json
            "seed": 42,
            "num_replicates": 1,
            "status": "configured",
        }
        sample_scenario = {
            "id": "scen-1",
            "scenario_text": "Character {PC_SUBJECT}.",
        }
        sample_scaffold = {
            "id": "scaff-1",
            "prompt": "NPC prompt.",
            "version": "1.0",
        }

        calls = []

        async def mock_generate(**kwargs):
            calls.append(kwargs)
            return "Response"

        with patch("routes.runner.find_by_id") as mock_find, \
             patch("routes.runner.generate", side_effect=mock_generate), \
             patch("routes.runner.append_json"), \
             patch("routes.runner._update_status"):

            mock_find.side_effect = lambda f, i: (
                historical_experiment if "experiments" in f
                else sample_scenario if "scenarios" in f
                else sample_scaffold
            )

            await _run_experiment("exp-historical")

        self.assertEqual(len(calls), 2)
        for c in calls:
            self.assertEqual(c["model"], "mistral:latest")
            self.assertEqual(c["top_k"], 40, "Must default missing top_k to 40")
            self.assertEqual(c["repeat_penalty"], 1.1, "Must default missing repeat_penalty to 1.1")


class TestPydanticModelDefaults(unittest.TestCase):
    """Verify that models.py correctly parses and defaults the generation parameters."""

    def test_experiment_create_defaults(self):
        payload = {
            "scenario_id": "scen-1",
            "scaffold_id": "scaff-1",
            "model": "llama3.2:latest",
        }
        exp_create = ExperimentCreate(**payload)
        self.assertEqual(exp_create.top_k, 40)
        self.assertEqual(exp_create.repeat_penalty, 1.1)

    def test_experiment_create_custom_values(self):
        payload = {
            "scenario_id": "scen-1",
            "scaffold_id": "scaff-1",
            "model": "mistral:latest",
            "top_k": 50,
            "repeat_penalty": 1.25,
        }
        exp_create = ExperimentCreate(**payload)
        self.assertEqual(exp_create.top_k, 50)
        self.assertEqual(exp_create.repeat_penalty, 1.25)

    def test_experiment_defaults_and_serialization(self):
        exp = Experiment(
            scenario_id="scen-1",
            scaffold_id="scaff-1",
            model="llama3.2:latest",
        )
        data = exp.model_dump()
        self.assertEqual(data["top_k"], 40)
        self.assertEqual(data["repeat_penalty"], 1.1)


if __name__ == "__main__":
    unittest.main()
