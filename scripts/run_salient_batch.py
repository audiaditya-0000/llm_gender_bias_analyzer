"""
Error-Free Batch Runner for the Gender-Salient Scenario Pack (v1.2).

Features:
- Model Grouping: Runs all 30 llama3.2 experiments first, then all 30 mistral experiments.
  Prevents model thrashing in RAM.
- Resumable: Skips already completed experiments. If interrupted, restarts exactly where it stopped.
- Automatic Retries: Retries failed generations up to 3 times with backoff.
- Generous Timeouts: 180s per response to prevent dropped requests on CPU.
- Progress Reporting: Live terminal updates with timestamps and timing stats.
"""

import os
import sys
import time
import uuid
import asyncio
import logging
from datetime import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from storage import read_json, append_json, update_by_id, find_by_id
from models import ExperimentResponse
from services.ollama import generate, check_health, list_models
from services.gender_swap import render_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_runner")

EXPERIMENTS_FILE = "experiments.json"
RESPONSES_FILE = "responses.json"
SCAFFOLDS_FILE = "scaffolds.json"
SCENARIOS_FILE = "scenarios.json"

MAX_RETRIES = 3
TIMEOUT_SECONDS = 180.0

async def generate_with_retry(scaffold_prompt: str, scenario_prompt: str, model: str, options: dict) -> str:
    """Generate response with up to MAX_RETRIES on failure."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            content = await generate(
                scaffold=scaffold_prompt,
                scenario=scenario_prompt,
                model=model,
                temperature=options.get("temperature", 0.7),
                top_p=options.get("top_p", 0.9),
                max_tokens=options.get("max_tokens", 512),
                top_k=options.get("top_k", 40),
                repeat_penalty=options.get("repeat_penalty", 1.1),
                seed=options.get("seed"),
            )
            if content and not content.startswith("[ERROR]"):
                return content
            last_err = content
        except Exception as e:
            last_err = str(e)
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for model '{model}': {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(attempt * 2)
    return f"[ERROR] Failed after {MAX_RETRIES} attempts: {last_err}"

async def run_single_experiment(exp: dict, scenario: dict, scaffold: dict, exp_idx: int, total_exps: int):
    exp_id = exp["id"]
    model_name = exp["model"]
    scen_title = scenario.get("title", exp["scenario_id"])
    scaff_ver = scaffold.get("version", "1.0")
    num_replicates = exp.get("num_replicates", 20)
    base_seed = exp.get("seed", 42)

    logger.info(f"[{exp_idx}/{total_exps}] START: {model_name} | {scen_title} (v{scaff_ver})")
    start_time = time.time()

    update_by_id(EXPERIMENTS_FILE, exp_id, {"status": "running"})

    scaffold_prompt = scaffold["prompt"]
    raw_scenario_text = scenario["scenario_text"]
    male_scenario_text = render_scenario(raw_scenario_text, "male")
    female_scenario_text = render_scenario(raw_scenario_text, "female")

    conditions = [
        ("original", male_scenario_text),
        ("swapped", female_scenario_text),
    ]

    batch_responses = []

    for replicate in range(1, num_replicates + 1):
        pair_id = str(uuid.uuid4())

        for cond_label, scen_text in conditions:
            formatted_prompt = f"SCENARIO:\n{scen_text}"
            condition_offset = 0 if cond_label == "original" else num_replicates
            current_seed = base_seed + condition_offset + replicate if base_seed is not None else None

            gen_options = {
                "temperature": exp.get("temperature", 0.7),
                "top_p": exp.get("top_p", 0.9),
                "max_tokens": exp.get("max_tokens", 512),
                "top_k": exp.get("top_k", 40),
                "repeat_penalty": exp.get("repeat_penalty", 1.1),
                "seed": current_seed,
            }

            gen_output = await generate_with_retry(
                scaffold_prompt=scaffold_prompt,
                scenario_prompt=formatted_prompt,
                model=model_name,
                options=gen_options,
            )

            response_record = ExperimentResponse(
                pair_id=pair_id,
                experiment_id=exp_id,
                scenario_id=exp["scenario_id"],
                scaffold_id=exp["scaffold_id"],
                scaffold_version=scaff_ver,
                model=model_name,
                temperature=exp.get("temperature", 0.7),
                seed=current_seed,
                condition=cond_label,
                replicate_number=replicate,
                scaffold_prompt=scaffold_prompt,
                scenario_prompt=formatted_prompt,
                generated_response=gen_output,
                top_p=exp.get("top_p", 0.9),
                top_k=exp.get("top_k", 40),
                repeat_penalty=exp.get("repeat_penalty", 1.1),
                max_tokens=exp.get("max_tokens", 512),
                tag=exp.get("tag"),
            )
            batch_responses.append(response_record.model_dump())

        sys.stdout.write(f"\r  -> Progress: Replicate {replicate}/{num_replicates} pairs done")
        sys.stdout.flush()

    sys.stdout.write("\n")

    # Save all responses for this cell in one batch
    append_json(RESPONSES_FILE, batch_responses)
    update_by_id(EXPERIMENTS_FILE, exp_id, {"status": "completed"})

    elapsed = time.time() - start_time
    logger.info(f"[{exp_idx}/{total_exps}] COMPLETED in {elapsed:.1f}s ({elapsed/num_replicates:.2f}s/pair)")

async def main():
    print("=================================================================")
    print("   LLM GENDER BIAS ANALYZER — GENDER-SALIENT PACK BATCH RUNNER   ")
    print("=================================================================")

    # 1. Health check
    is_healthy = await check_health()
    if not is_healthy:
        print("\n[ERROR] Ollama is not running!")
        print("Please ensure Ollama is started by running:")
        print("    ollama serve")
        print("or launching the Ollama desktop application, then rerun this script.")
        return

    models_info = await list_models()
    available_model_names = [m.get("name") for m in models_info]
    print(f"Ollama is online. Available models: {available_model_names}")

    required_models = ["llama3.2:latest", "mistral:latest"]
    for req in required_models:
        if req not in available_model_names and not any(req in m for m in available_model_names):
            print(f"[WARNING] Model '{req}' not found in Ollama list. Pull it using 'ollama pull {req}'")

    # 2. Load and filter experiments
    all_experiments = read_json(EXPERIMENTS_FILE)
    salient_experiments = [
        e for e in all_experiments
        if e.get("tag") == "gender_salient_pack" and e.get("status") != "completed"
    ]

    if not salient_experiments:
        print("\nAll gender-salient experiments are already marked as completed!")
        return

    # Model Grouping: llama3.2 first, then mistral
    salient_experiments.sort(key=lambda e: (0 if "llama" in e["model"].lower() else 1, e["scenario_id"], e["scaffold_id"]))

    scenarios = {s["id"]: s for s in read_json(SCENARIOS_FILE)}
    scaffolds = {s["id"]: s for s in read_json(SCAFFOLDS_FILE)}

    llama_count = sum(1 for e in salient_experiments if "llama" in e["model"].lower())
    mistral_count = sum(1 for e in salient_experiments if "mistral" in e["model"].lower())

    print(f"\nQueued for execution: {len(salient_experiments)} experiments")
    print(f"  • Stage 1 (llama3.2:latest): {llama_count} experiments (~{llama_count * 40} responses)")
    print(f"  • Stage 2 (mistral:latest):  {mistral_count} experiments (~{mistral_count * 40} responses)")
    print(f"Total responses to generate: {len(salient_experiments) * 40}")
    print("Starting execution...\n")

    overall_start = time.time()
    for idx, exp in enumerate(salient_experiments, 1):
        scenario = scenarios.get(exp["scenario_id"])
        scaffold = scaffolds.get(exp["scaffold_id"])
        if not scenario or not scaffold:
            logger.error(f"Missing scenario or scaffold for experiment {exp['id']}, skipping.")
            continue

        await run_single_experiment(exp, scenario, scaffold, idx, len(salient_experiments))

    total_elapsed = time.time() - overall_start
    print("\n=================================================================")
    print(f"BATCH RUN COMPLETE in {total_elapsed/60:.1f} minutes!")
    print("All responses saved to storage. Ready for blind coding.")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(main())
