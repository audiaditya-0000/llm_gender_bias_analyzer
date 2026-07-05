"""
Experiment runner.
Executes experiments by generating counterfactual prompts and calling Ollama
for N replicates per gender condition.
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from models import ExperimentResponse
from storage import read_json, write_json, append_json, find_by_id
from services.ollama import generate
from routes.counterfactual import _swap_gendered_terms

router = APIRouter(prefix="/api/runner", tags=["runner"])

EXPERIMENTS_FILE = "experiments.json"
RESPONSES_FILE = "responses.json"
SCAFFOLDS_FILE = "scaffolds.json"
SCENARIOS_FILE = "scenarios.json"

# In-memory progress tracking
_progress: dict[str, dict] = {}


def _get_conditions(swap_type: str = "npc") -> list[tuple[str, str]]:
    """Return (condition_label, direction) pairs for the swap type."""
    return [
        (f"male_{swap_type}", "to_male"),
        (f"female_{swap_type}", "to_female"),
    ]


async def _run_experiment(experiment_id: str):
    """Execute all replicates for an experiment."""
    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        return

    scenario = find_by_id(SCENARIOS_FILE, experiment["scenario_id"])
    scaffold = find_by_id(SCAFFOLDS_FILE, experiment["scaffold_id"])

    if not scenario or not scaffold:
        _update_status(experiment_id, "failed")
        return

    _update_status(experiment_id, "running")

    conditions = _get_conditions(experiment.get("swap_type", "npc"))
    num_replicates = experiment.get("num_replicates", 20)
    total = len(conditions) * num_replicates
    completed = 0

    _progress[experiment_id] = {
        "completed": 0,
        "total": total,
        "status": "running",
    }

    base_system_prompt = scaffold["prompt"]
    base_user_prompt = scenario["scenario_text"]

    responses_batch: list[dict] = []

    for condition_label, direction in conditions:
        system_prompt, _ = _swap_gendered_terms(base_system_prompt, direction)
        user_prompt, _ = _swap_gendered_terms(base_user_prompt, direction)

        for replicate in range(1, num_replicates + 1):
            try:
                seed = experiment.get("seed")
                if seed is not None:
                    # Vary seed per replicate to get different outputs
                    current_seed = seed + replicate
                else:
                    current_seed = None

                generated = await generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=experiment["model"],
                    temperature=experiment.get("temperature", 0.7),
                    top_p=experiment.get("top_p", 0.9),
                    max_tokens=experiment.get("max_tokens", 512),
                    seed=current_seed,
                )

                response = ExperimentResponse(
                    experiment_id=experiment_id,
                    scenario_id=experiment["scenario_id"],
                    scaffold_id=experiment["scaffold_id"],
                    scaffold_version=scaffold.get("version", "1.0"),
                    model=experiment["model"],
                    temperature=experiment.get("temperature", 0.7),
                    seed=current_seed,
                    condition=condition_label,
                    replicate_number=replicate,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    generated_response=generated,
                )

                responses_batch.append(response.model_dump())
            except Exception as e:
                # Log the error but continue with other replicates
                responses_batch.append(
                    ExperimentResponse(
                        experiment_id=experiment_id,
                        scenario_id=experiment["scenario_id"],
                        scaffold_id=experiment["scaffold_id"],
                        scaffold_version=scaffold.get("version", "1.0"),
                        model=experiment["model"],
                        temperature=experiment.get("temperature", 0.7),
                        seed=experiment.get("seed"),
                        condition=condition_label,
                        replicate_number=replicate,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        generated_response=f"[ERROR] {str(e)}",
                    ).model_dump()
                )

            completed += 1
            _progress[experiment_id]["completed"] = completed

    # Append all responses at once (never overwrite)
    append_json(RESPONSES_FILE, responses_batch)

    _update_status(experiment_id, "completed")
    _progress[experiment_id]["status"] = "completed"


def _update_status(experiment_id: str, status: str):
    """Update the experiment status in the experiments file."""
    data = read_json(EXPERIMENTS_FILE)
    for i, item in enumerate(data):
        if item.get("id") == experiment_id:
            data[i]["status"] = status
            break
    write_json(EXPERIMENTS_FILE, data)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/start")
async def start_experiment(body: dict):
    """Start running an experiment. Expects {"experiment_id": "..."}"""
    experiment_id = body.get("experiment_id")
    if not experiment_id:
        raise HTTPException(status_code=400, detail="experiment_id is required")

    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") == "running":
        raise HTTPException(status_code=409, detail="Experiment is already running")

    # Launch the experiment as a background task
    asyncio.create_task(_run_experiment(experiment_id))

    return {"message": "Experiment started", "experiment_id": experiment_id}


@router.get("/status/{experiment_id}")
def get_status(experiment_id: str):
    """Get the progress of a running experiment."""
    if experiment_id in _progress:
        return _progress[experiment_id]

    # Check stored status
    experiment = find_by_id(EXPERIMENTS_FILE, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "completed": 0,
        "total": 0,
        "status": experiment.get("status", "configured"),
    }
