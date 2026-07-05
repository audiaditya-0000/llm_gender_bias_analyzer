from fastapi import APIRouter, HTTPException
from models import Scaffold, ScaffoldCreate
from storage import read_json, write_json, find_by_id, delete_by_id

router = APIRouter(prefix="/api/scaffolds", tags=["scaffolds"])

FILENAME = "scaffolds.json"


@router.get("")
def list_scaffolds():
    """Return all scaffolds."""
    return read_json(FILENAME)


@router.get("/{scaffold_id}")
def get_scaffold(scaffold_id: str):
    """Return a single scaffold by ID."""
    item = find_by_id(FILENAME, scaffold_id)
    if not item:
        raise HTTPException(status_code=404, detail="Scaffold not found")
    return item


@router.post("", status_code=201)
def create_scaffold(payload: ScaffoldCreate):
    """Create a new scaffold."""
    scaffold = Scaffold(**payload.model_dump())
    data = read_json(FILENAME)
    data.append(scaffold.model_dump())
    write_json(FILENAME, data)
    return scaffold.model_dump()


@router.put("/{scaffold_id}")
def update_scaffold(scaffold_id: str, payload: ScaffoldCreate):
    """Update an existing scaffold."""
    data = read_json(FILENAME)
    for i, item in enumerate(data):
        if item.get("id") == scaffold_id:
            data[i] = {**item, **payload.model_dump()}
            write_json(FILENAME, data)
            return data[i]
    raise HTTPException(status_code=404, detail="Scaffold not found")


@router.delete("/{scaffold_id}")
def remove_scaffold(scaffold_id: str):
    """Delete a scaffold by ID."""
    if not delete_by_id(FILENAME, scaffold_id):
        raise HTTPException(status_code=404, detail="Scaffold not found")
    return {"deleted": True}
