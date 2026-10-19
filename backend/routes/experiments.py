from fastapi import APIRouter, HTTPException
from models import Experiment, ExperimentCreate
from storage import read_json, write_json, find_by_id, delete_by_id, upsert_record

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

FILENAME = "experiments.json"


@router.get("")
def list_experiments():
    """Return all experiment configurations."""
    return read_json(FILENAME)


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    """Return a single experiment by ID."""
    item = find_by_id(FILENAME, experiment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return item


@router.post("", status_code=201)
def create_experiment(payload: ExperimentCreate):
    """Create a new experiment configuration."""
    experiment = Experiment(**payload.model_dump())
    upsert_record(FILENAME, experiment.model_dump())
    return experiment.model_dump()


@router.delete("/{experiment_id}")
def remove_experiment(experiment_id: str):
    """Delete an experiment configuration."""
    if not delete_by_id(FILENAME, experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"deleted": True}
