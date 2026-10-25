import os
import sys
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.abspath("backend"))

from storage import read_json, append_json, upsert_record
from services.gender_salient_scenarios import GENDER_SALIENT_SCENARIOS

SCENARIOS_FILE = "scenarios.json"
SCAFFOLDS_FILE = "scaffolds.json"
EXPERIMENTS_FILE = "experiments.json"
CANONICAL_MODELS = ["llama3.2:latest", "mistral:latest"]

def setup_salient_pack():
    print("=== Step 1: Checking and inserting the 10 gender-salient scenarios ===")
    existing_scenarios = read_json(SCENARIOS_FILE)
    existing_scen_ids = {s.get("id") for s in existing_scenarios}
    existing_scen_titles = {s.get("title") for s in existing_scenarios}

    new_scenarios_to_add = []
    for s in GENDER_SALIENT_SCENARIOS:
        if s["id"] not in existing_scen_ids and s["title"] not in existing_scen_titles:
            new_scenarios_to_add.append(s)

    if new_scenarios_to_add:
        print(f"Adding {len(new_scenarios_to_add)} new scenarios to {SCENARIOS_FILE}...")
        for s in new_scenarios_to_add:
            upsert_record(SCENARIOS_FILE, s)
        print("Scenarios inserted successfully.")
    else:
        print("All 10 gender-salient scenarios already exist in storage.")

    print("\n=== Step 2: Fetching scaffolds and verifying factorial dimensions ===")
    scaffolds = read_json(SCAFFOLDS_FILE)
    scaffold_ids = [sc["id"] for sc in scaffolds if sc.get("id")]
    salient_scenario_ids = [s["id"] for s in GENDER_SALIENT_SCENARIOS]

    print(f"Scenarios (Salient): {len(salient_scenario_ids)}")
    print(f"Scaffolds: {len(scaffold_ids)}")
    print(f"Models: {len(CANONICAL_MODELS)}")
    total_expected = len(salient_scenario_ids) * len(scaffold_ids) * len(CANONICAL_MODELS)
    print(f"Total factorial cells expected: {total_expected}")

    print("\n=== Step 3: Generating and registering the 60 experimental cells ===")
    existing_experiments = read_json(EXPERIMENTS_FILE)
    existing_combos = {
        (e.get("scenario_id"), e.get("scaffold_id"), e.get("model"))
        for e in existing_experiments
    }

    new_experiments = []
    for sc_id in salient_scenario_ids:
        for sf_id in scaffold_ids:
            for model_name in CANONICAL_MODELS:
                combo = (sc_id, sf_id, model_name)
                if combo in existing_combos:
                    continue

                exp_id = str(uuid.uuid4())
                exp_record = {
                    "id": exp_id,
                    "scenario_id": sc_id,
                    "scaffold_id": sf_id,
                    "model": model_name,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 512,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "seed": 42,
                    "num_replicates": 20,
                    "swap_type": "npc",
                    "status": "configured",
                    "tag": "gender_salient_pack",
                    "created_at": datetime.utcnow().isoformat(),
                }
                new_experiments.append(exp_record)

    if new_experiments:
        print(f"Registering {len(new_experiments)} new experiments in {EXPERIMENTS_FILE}...")
        append_json(EXPERIMENTS_FILE, new_experiments)
        print(f"Successfully registered {len(new_experiments)} experiments!")
    else:
        print("All 60 salient experiments already registered.")

    # Verification count
    all_exps = read_json(EXPERIMENTS_FILE)
    salient_exps = [e for e in all_exps if e.get("tag") == "gender_salient_pack"]
    baseline_exps = [e for e in all_exps if e.get("tag") != "gender_salient_pack"]
    print(f"\nFinal Inventory Summary:")
    print(f"- Baseline Neutral Experiments: {len(baseline_exps)}")
    print(f"- Gender-Salient Experiments: {len(salient_exps)}")
    print(f"- Total Experiments in Storage: {len(all_exps)}")

if __name__ == "__main__":
    setup_salient_pack()
