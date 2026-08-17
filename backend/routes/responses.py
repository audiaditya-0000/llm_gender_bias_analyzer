from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from storage import read_json, write_json, find_by_id, delete_by_id

router = APIRouter(prefix="/api/responses", tags=["responses"])

FILENAME = "responses.json"


@router.get("")
def list_responses(
    experiment_id: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List all responses with optional filtering.
    Supports pagination with limit/offset.
    """
    data = read_json(FILENAME)

    # Apply filters
    if experiment_id:
        data = [r for r in data if r.get("experiment_id") == experiment_id]
    if condition:
        data = [r for r in data if r.get("condition") == condition]
    if search:
        search_lower = search.lower()
        data = [
            r
            for r in data
            if search_lower in r.get("generated_response", "").lower()
            or search_lower in r.get("user_prompt", "").lower()
            or search_lower in r.get("system_prompt", "").lower()
        ]

    total = len(data)
    paginated = data[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": paginated,
    }


@router.get("/{response_id}")
def get_response(response_id: str):
    """Return a single response with full metadata."""
    item = find_by_id(FILENAME, response_id)
    if not item:
        raise HTTPException(status_code=404, detail="Response not found")
    return item


@router.delete("/{response_id}")
def remove_response(response_id: str):
    """Delete a single response by ID."""
    if not delete_by_id(FILENAME, response_id):
        raise HTTPException(status_code=404, detail="Response not found")
    return {"deleted": True}


@router.delete("")
def bulk_delete_responses(
    experiment_id: Optional[str] = Query(None),
):
    """
    Bulk-delete responses.
    If experiment_id is provided, deletes only responses for that experiment.
    If no filter is provided, deletes ALL responses.
    """
    data = read_json(FILENAME)
    original_len = len(data)

    if experiment_id:
        data = [r for r in data if r.get("experiment_id") != experiment_id]
    else:
        data = []

    removed = original_len - len(data)
    write_json(FILENAME, data)
    return {"deleted": removed}
