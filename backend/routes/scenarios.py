from fastapi import APIRouter, HTTPException
from models import Scenario, ScenarioCreate, SCENARIO_CATEGORIES
from storage import read_json, write_json, find_by_id, delete_by_id

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

FILENAME = "scenarios.json"


@router.get("")
def list_scenarios():
    """Return all scenarios."""
    return read_json(FILENAME)


@router.get("/categories")
def list_categories():
    """Return the predefined list of scenario categories."""
    return SCENARIO_CATEGORIES


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str):
    """Return a single scenario by ID."""
    item = find_by_id(FILENAME, scenario_id)
    if not item:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return item


@router.post("", status_code=201)
def create_scenario(payload: ScenarioCreate):
    """Create a new scenario."""
    if payload.category not in SCENARIO_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {SCENARIO_CATEGORIES}",
        )
    scenario = Scenario(**payload.model_dump())
    data = read_json(FILENAME)
    data.append(scenario.model_dump())
    write_json(FILENAME, data)
    return scenario.model_dump()


@router.put("/{scenario_id}")
def update_scenario(scenario_id: str, payload: ScenarioCreate):
    """Update an existing scenario."""
    if payload.category not in SCENARIO_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {SCENARIO_CATEGORIES}",
        )
    data = read_json(FILENAME)
    for i, item in enumerate(data):
        if item.get("id") == scenario_id:
            data[i] = {**item, **payload.model_dump()}
            write_json(FILENAME, data)
            return data[i]
    raise HTTPException(status_code=404, detail="Scenario not found")


@router.delete("/{scenario_id}")
def remove_scenario(scenario_id: str):
    """Delete a scenario by ID."""
    if not delete_by_id(FILENAME, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True}
