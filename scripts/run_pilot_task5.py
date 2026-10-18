"""
Controlled Pilot Generation and Quality Checks (Task 5).

Executes a 24-response pilot:
- 2 representative scenarios:
  1. Tavern Keeper Vouches for Mercenary Escort (ID: 74ea8c66-f108-4054-8a1e-a6f9b1ffae62) [Combat / Manual labor / Peer vouching]
  2. The Enchanted Weapon Purchase (ID: 006fa958-884c-42e0-bb9e-4459fd588745) [Trading / Resource allocation / Commercial trust]
- 3 universal scaffolds (v1.0 Detailed, v1.1 Concise, v1.2 Narrative)
- 2 canonical models: llama3.2:latest, mistral:latest
- 2 conditions: original (male) and swapped (female)
- 1 replicate per cell = 12 cells * 2 conditions = 24 responses
- Generation settings: top_k=40, repeat_penalty=1.1, temperature=0.7, top_p=0.9, max_tokens=512

Reuses the existing backend runner (_run_experiment) and storage mechanisms.
"""

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(BACKEND_DIR))

from storage import read_json, write_json, append_json
from models import Experiment
from routes.runner import _run_experiment


# ── Configuration ─────────────────────────────────────────────────────────────

SCENARIO_IDS = [
    "74ea8c66-f108-4054-8a1e-a6f9b1ffae62",  # Tavern Keeper Vouches for Mercenary Escort (General / Combat-Labor)
    "006fa958-884c-42e0-bb9e-4459fd588745",  # The Enchanted Weapon Purchase (Trading / Commercial)
]

SCAFFOLD_IDS = [
    "a9714fe2-ca9f-4d86-bf87-4c1046319718",  # v1.0 Standard NPC Prompt (Detailed Persona)
    "72859fca-c908-4f0d-9099-7dd4ee53b839",  # v1.1 Direct NPC Prompt (Concise Instructions)
    "ad07cd93-7943-49be-8b36-849e882ffd7b",  # v1.2 Narrative NPC Prompt (Immersive Roleplay)
]

CANONICAL_MODELS = [
    "llama3.2:latest",
    "mistral:latest",
]

TEMPERATURE = 0.7
TOP_P = 0.9
MAX_TOKENS = 512
TOP_K = 40
REPEAT_PENALTY = 1.1
PILOT_TAG = "pilot_task5"


async def setup_pilot_experiments() -> list[dict]:
    """Create and register the 12 pilot experiment configurations in experiments.json."""
    existing_experiments = read_json("experiments.json")
    
    # Check if pilot experiments already exist
    existing_pilot = [e for e in existing_experiments if e.get("tag") == PILOT_TAG]
    if len(existing_pilot) == 12:
        print(f"Found {len(existing_pilot)} existing pilot experiment configurations.")
        return existing_pilot

    new_experiments = []
    base_seed_counter = 1000

    # Group by model so Ollama only loads each model once
    for model in CANONICAL_MODELS:
        for scen_id in SCENARIO_IDS:
            for scaff_id in SCAFFOLD_IDS:
                exp_id = str(uuid.uuid4())
                exp_record = {
                    "id": exp_id,
                    "scenario_id": scen_id,
                    "scaffold_id": scaff_id,
                    "model": model,
                    "temperature": TEMPERATURE,
                    "top_p": TOP_P,
                    "max_tokens": MAX_TOKENS,
                    "top_k": TOP_K,
                    "repeat_penalty": REPEAT_PENALTY,
                    "seed": base_seed_counter,
                    "num_replicates": 1,
                    "swap_type": "npc",
                    "status": "configured",
                    "tag": PILOT_TAG,
                }
                new_experiments.append(exp_record)
                base_seed_counter += 10

    append_json("experiments.json", new_experiments)
    print(f"Registered {len(new_experiments)} new pilot experiment records in experiments.json.")
    return new_experiments


async def run_pilot_grid(experiments: list[dict]):
    """Execute all pilot experiments sequentially using the existing runner."""
    total = len(experiments)
    print(f"\nStarting execution of {total} pilot experiment cells (24 responses total)...")
    
    for idx, exp in enumerate(experiments, start=1):
        exp_id = exp["id"]
        print(f"[{idx}/{total}] Running Cell: Model={exp['model']} | Scenario={exp['scenario_id'][:8]} | Scaffold={exp['scaffold_id'][:8]} (Replicates=1, Pairs=1)")
        try:
            await _run_experiment(exp_id)
            print(f"       -> Cell completed successfully.")
        except Exception as e:
            print(f"       -> ERROR in cell {exp_id}: {e}")


def run_automated_quality_checks(pilot_responses: list[dict]) -> dict:
    """Run rigorous automated quality checks against the generated pilot responses."""
    checks = {
        "total_responses": len(pilot_responses),
        "expected_responses": 24,
        "missing_or_empty": [],
        "errors_detected": [],
        "unresolved_pc_tokens": [],
        "prompt_leakage": [],
        "unexpected_models": [],
        "unexpected_scaffolds": [],
        "parameter_mismatches": [],
        "pair_id_integrity": {
            "valid_pairs_count": 0,
            "broken_pairs": [],
        },
        "coverage": {
            "llama3.2_count": 0,
            "mistral_count": 0,
            "male_original_count": 0,
            "female_swapped_count": 0,
            "cells_covered": set(),
        }
    }

    # Leakage marker phrases from system scaffolds and scenario templates
    leakage_markers = [
        "Respond only as this character",
        "Never reveal, hint at",
        "stay fully in character",
        "Stay in character at all times",
        "You have learned the hard way",
        "SCENARIO:",
        "Base your response strictly",
        "{PC_",
    ]

    pairs_dict = {}

    for r in pilot_responses:
        r_id = r.get("id")
        text = r.get("generated_response", "")
        scen_id = r.get("scenario_id")
        scaff_id = r.get("scaffold_id")
        model = r.get("model")
        condition = r.get("condition")
        pair_id = r.get("pair_id")

        # 1. Check for empty or error responses
        if not text or not text.strip():
            checks["missing_or_empty"].append(r_id)
        if text.startswith("[ERROR]"):
            checks["errors_detected"].append({"id": r_id, "error": text})

        # 2. Check for unresolved PC tokens
        pc_matches = re.findall(r"\{PC_[A-Z_]+\}", text)
        if pc_matches:
            checks["unresolved_pc_tokens"].append({"id": r_id, "tokens": pc_matches})

        # Also check prompts for unresolved tokens
        scen_prompt = r.get("scenario_prompt", "")
        scen_pc_matches = re.findall(r"\{PC_[A-Z_]+\}", scen_prompt)
        if scen_pc_matches:
            checks["unresolved_pc_tokens"].append({"id": r_id, "prompt_tokens": scen_pc_matches})

        # 3. Check for prompt or instruction leakage
        leaked = [m for m in leakage_markers if m.lower() in text.lower()]
        if leaked:
            checks["prompt_leakage"].append({"id": r_id, "leaked_markers": leaked})

        # 4. Check model and scaffold identifiers
        if model not in CANONICAL_MODELS:
            checks["unexpected_models"].append({"id": r_id, "model": model})
        if scaff_id not in SCAFFOLD_IDS:
            checks["unexpected_scaffolds"].append({"id": r_id, "scaffold": scaff_id})

        # 5. Check generation settings
        if r.get("top_k") != TOP_K or r.get("repeat_penalty") != REPEAT_PENALTY:
            checks["parameter_mismatches"].append({
                "id": r_id,
                "top_k": r.get("top_k"),
                "repeat_penalty": r.get("repeat_penalty")
            })

        # 6. Pair tracking
        if pair_id not in pairs_dict:
            pairs_dict[pair_id] = []
        pairs_dict[pair_id].append(r)

        # 7. Coverage counts
        if model == "llama3.2:latest":
            checks["coverage"]["llama3.2_count"] += 1
        elif model == "mistral:latest":
            checks["coverage"]["mistral_count"] += 1

        if condition == "original":
            checks["coverage"]["male_original_count"] += 1
        elif condition == "swapped":
            checks["coverage"]["female_swapped_count"] += 1

        cell_tuple = (scen_id, scaff_id, model)
        checks["coverage"]["cells_covered"].add(cell_tuple)

    # Validate pairs
    for pid, pair_members in pairs_dict.items():
        if len(pair_members) != 2:
            checks["pair_id_integrity"]["broken_pairs"].append({
                "pair_id": pid,
                "reason": f"Expected 2 members, got {len(pair_members)}"
            })
        else:
            conds = {m.get("condition") for m in pair_members}
            if conds != {"original", "swapped"}:
                checks["pair_id_integrity"]["broken_pairs"].append({
                    "pair_id": pid,
                    "reason": f"Expected original and swapped, got {conds}"
                })
            else:
                checks["pair_id_integrity"]["valid_pairs_count"] += 1

    checks["coverage"]["cells_covered_count"] = len(checks["coverage"]["cells_covered"])
    checks["coverage"]["cells_covered"] = [list(c) for c in checks["coverage"]["cells_covered"]]
    return checks


async def main():
    print("=" * 70)
    print("TASK 5: CONTROLLED PILOT GENERATION AND QUALITY CHECKS")
    print("=" * 70)

    # Step 1: Setup experiments
    experiments = await setup_pilot_experiments()

    # Step 2: Run generation grid
    await run_pilot_grid(experiments)

    # Step 3: Extract pilot responses
    all_responses = read_json("responses.json")
    pilot_exp_ids = {e["id"] for e in experiments}
    pilot_responses = [r for r in all_responses if r.get("experiment_id") in pilot_exp_ids or r.get("tag") == PILOT_TAG]

    print(f"\nExtracted {len(pilot_responses)} pilot responses from responses.json.")

    # Save isolated snapshot to data/pilot_task5_responses.json
    snapshot_path = DATA_DIR / "pilot_task5_responses.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(pilot_responses, f, indent=2, ensure_ascii=False)
    print(f"Saved isolated pilot snapshot to {snapshot_path}")

    # Step 4: Quality Checks
    print("\nRunning automated quality checks...")
    qc = run_automated_quality_checks(pilot_responses)
    
    qc_path = DATA_DIR / "pilot_task5_quality_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(qc, f, indent=2, ensure_ascii=False)
    print(f"Saved quality report to {qc_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("QUALITY CHECK SUMMARY")
    print("=" * 70)
    print(f"Total Responses Generated: {qc['total_responses']} / {qc['expected_responses']}")
    print(f"Missing or Empty:          {len(qc['missing_or_empty'])}")
    print(f"Errors Detected:           {len(qc['errors_detected'])}")
    print(f"Unresolved PC Tokens:      {len(qc['unresolved_pc_tokens'])}")
    print(f"Prompt Leakage Incidents:  {len(qc['prompt_leakage'])}")
    print(f"Valid Paired Observations: {qc['pair_id_integrity']['valid_pairs_count']} / 12")
    print(f"Broken Pairs:              {len(qc['pair_id_integrity']['broken_pairs'])}")
    print(f"Llama 3.2 Responses:       {qc['coverage']['llama3.2_count']} (expected 12)")
    print(f"Mistral Responses:         {qc['coverage']['mistral_count']} (expected 12)")
    print(f"Male Conditions:           {qc['coverage']['male_original_count']} (expected 12)")
    print(f"Female Conditions:         {qc['coverage']['female_swapped_count']} (expected 12)")
    print(f"Experimental Cells Covered:{qc['coverage']['cells_covered_count']} / 12")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
