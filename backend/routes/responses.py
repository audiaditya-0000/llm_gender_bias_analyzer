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
            or search_lower in r.get("scenario_prompt", r.get("user_prompt", "")).lower()
            or search_lower in r.get("scaffold_prompt", r.get("system_prompt", "")).lower()
        ]

    total = len(data)
    paginated = data[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": paginated,
    }


@router.get("/pairs")
def list_response_pairs(
    experiment_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List responses grouped by pair_id.
    Each item contains { pair_id, original, swapped, replicate_number, ... }.
    """
    data = read_json(FILENAME)

    if experiment_id:
        data = [r for r in data if r.get("experiment_id") == experiment_id]

    if search:
        search_lower = search.lower()
        data = [
            r
            for r in data
            if search_lower in r.get("generated_response", "").lower()
            or search_lower in r.get("scenario_prompt", r.get("user_prompt", "")).lower()
            or search_lower in r.get("scaffold_prompt", r.get("system_prompt", "")).lower()
        ]

    pairs_map = {}
    for r in data:
        pid = r.get("pair_id") or r.get("id")
        if pid not in pairs_map:
            pairs_map[pid] = {
                "pair_id": pid,
                "original": None,
                "swapped": None,
                "replicate_number": r.get("replicate_number", 1),
                "scenario_id": r.get("scenario_id", ""),
                "scaffold_id": r.get("scaffold_id", ""),
                "model": r.get("model", ""),
                "timestamp": r.get("timestamp", ""),
            }
        cond = r.get("condition", "")
        if cond == "original" or "male" in cond:
            pairs_map[pid]["original"] = r
        elif cond == "swapped" or "female" in cond:
            pairs_map[pid]["swapped"] = r
        else:
            if not pairs_map[pid]["original"]:
                pairs_map[pid]["original"] = r
            else:
                pairs_map[pid]["swapped"] = r

    pairs_list = list(pairs_map.values())
    total = len(pairs_list)
    paginated = pairs_list[offset : offset + limit]

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
        from database import is_db_configured, db_delete_where
        if is_db_configured():
            try:
                db_delete_where("responses", "experiment_id = %s", (experiment_id,))
            except Exception:
                pass
    else:
        data = []

    removed = original_len - len(data)
    write_json(FILENAME, data)
    return {"deleted": removed}
