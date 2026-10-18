"""
Experiment runner.

Executes game NPC simulation experiments.
For each replicate, runs:
  1. "original": male scenario text (canonical mapping)
  2. "swapped": female scenario text (canonical mapping)

Both runs share a unique pair_id.
Scaffold acts as the NPC persona/instructions.
Scenario is formatted as SCENARIO:\n{text}.
"""

import asyncio
import uuid
from fastapi import APIRouter, HTTPException

from models import ExperimentResponse
from storage import read_json, write_json, append_json, find_by_id
from services.ollama import generate
from services.gender_swap import render_scenario

router = APIRouter(prefix="/api/runner", tags=["runner"])

EXPERIMENTS_FILE = "experiments.json"
RESPONSES_FILE = "responses.json"
SCAFFOLDS_FILE = "scaffolds.json"
SCENARIOS_FILE = "scenarios.json"

_progress: dict[str, dict] = {}

def _update_status(experiment_id: str, status: str):
    """Update experiment status in experiments.json."""
    data = read_json(EXPERIMENTS_FILE)
    for i, item in enumerate(data):
        if item.get("id") == experiment_id:
            data[i]["status"] = status
            break
    write_json(EXPERIMENTS_FILE, data)

async def _run_experiment(experiment_id: str):
    """
    Execute all replicates for an NPC experiment.

    For each replicate:
        1. "original" condition -> male scenario text
        2. "swapped" condition  -> female scenario text

    Both responses in each replicate share a unique pair_id.
    """
    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        return

    scenario = find_by_id(SCENARIOS_FILE, experiment["scenario_id"])
    scaffold = find_by_id(SCAFFOLDS_FILE, experiment["scaffold_id"])

    if not scenario or not scaffold:
        _update_status(experiment_id, "failed")
        return

    _update_status(experiment_id, "running")

    num_replicates = experiment.get("num_replicates", 20)
    total = 2 * num_replicates
    completed = 0

    _progress[experiment_id] = {
        "completed": 0,
        "total": total,
        "status": "running",
    }

    scaffold_prompt = scaffold["prompt"]
    original_scenario_text = scenario["scenario_text"]
    
    male_scenario_text = render_scenario(original_scenario_text, "male")
    female_scenario_text = render_scenario(original_scenario_text, "female")

    conditions = [
        ("original", male_scenario_text),
        ("swapped", female_scenario_text),
    ]

    responses_batch: list[dict] = []
    base_seed = experiment.get("seed")

    for replicate in range(1, num_replicates + 1):
        pair_id = str(uuid.uuid4())

        for condition_label, scenario_text in conditions:
            formatted_scenario = f"SCENARIO:\n{scenario_text}"

            if base_seed is not None:
                condition_offset = 0 if condition_label == "original" else num_replicates
                current_seed = base_seed + condition_offset + replicate
            else:
                current_seed = None

            try:
                generated = await generate(
                    scaffold=scaffold_prompt,
                    scenario=formatted_scenario,
                    model=experiment["model"],
                    temperature=experiment.get("temperature", 0.7),
                    top_p=experiment.get("top_p", 0.9),
                    max_tokens=experiment.get("max_tokens", 512),
                    top_k=experiment.get("top_k") if experiment.get("top_k") is not None else 40,
                    repeat_penalty=experiment.get("repeat_penalty") if experiment.get("repeat_penalty") is not None else 1.1,
                    seed=current_seed,
                )

                response = ExperimentResponse(
                    pair_id=pair_id,
                    experiment_id=experiment_id,
                    scenario_id=experiment["scenario_id"],
                    scaffold_id=experiment["scaffold_id"],
                    scaffold_version=scaffold.get("version", "1.0"),
                    model=experiment["model"],
                    temperature=experiment.get("temperature", 0.7),
                    seed=current_seed,
                    condition=condition_label,
                    replicate_number=replicate,
                    scaffold_prompt=scaffold_prompt,
                    scenario_prompt=formatted_scenario,
                    generated_response=generated,
                    top_p=experiment.get("top_p", 0.9),
                    top_k=experiment.get("top_k", 40),
                    repeat_penalty=experiment.get("repeat_penalty", 1.1),
                    max_tokens=experiment.get("max_tokens", 512),
                    tag=experiment.get("tag"),
                )
                responses_batch.append(response.model_dump())

            except Exception as e:
                error_response = ExperimentResponse(
                    pair_id=pair_id,
                    experiment_id=experiment_id,
                    scenario_id=experiment["scenario_id"],
                    scaffold_id=experiment["scaffold_id"],
                    scaffold_version=scaffold.get("version", "1.0"),
                    model=experiment["model"],
                    temperature=experiment.get("temperature", 0.7),
                    seed=current_seed,
                    condition=condition_label,
                    replicate_number=replicate,
                    scaffold_prompt=scaffold_prompt,
                    scenario_prompt=formatted_scenario,
                    generated_response=f"[ERROR] {str(e)}",
                    top_p=experiment.get("top_p", 0.9),
                    top_k=experiment.get("top_k", 40),
                    repeat_penalty=experiment.get("repeat_penalty", 1.1),
                    max_tokens=experiment.get("max_tokens", 512),
                    tag=experiment.get("tag"),
                )
                responses_batch.append(error_response.model_dump())

            completed += 1
            _progress[experiment_id]["completed"] = completed

    append_json(RESPONSES_FILE, responses_batch)
    _update_status(experiment_id, "completed")
    _progress[experiment_id]["status"] = "completed"

@router.post("/start")
async def start_experiment(body: dict):
    """
    Start an experiment.
    Expected request: {"experiment_id": "..."}
    """
    experiment_id = body.get("experiment_id")
    if not experiment_id:
        raise HTTPException(status_code=400, detail="experiment_id is required")

    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") == "running":
        raise HTTPException(status_code=409, detail="Experiment is already running")

    asyncio.create_task(_run_experiment(experiment_id))

    return {
        "message": "Experiment started",
        "experiment_id": experiment_id,
    }

@router.get("/status/{experiment_id}")
def get_status(experiment_id: str):
    """Return experiment execution progress."""
    if experiment_id in _progress:
        return _progress[experiment_id]

    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "completed": 0,
        "total": 0,
        "status": experiment.get("status", "configured"),
    }
