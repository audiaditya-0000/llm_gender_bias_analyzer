"""
Blind coding routes.
Serves responses without gender condition labels for unbiased researcher coding.
"""

import random
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models import Coding, CodingCreate
from storage import read_json, write_json, find_by_id

router = APIRouter(prefix="/api/coding", tags=["coding"])

CODING_FILE = "coding.json"
RESPONSES_FILE = "responses.json"


@router.get("")
def list_codings():
    """Return all coding entries."""
    return read_json(CODING_FILE)


@router.get("/blind")
def get_blind_responses(
    experiment_id: Optional[str] = Query(None),
    shuffle_seed: Optional[int] = Query(None),
):
    """
    Return responses with gender condition hidden, merged with any existing coding data.
    Responses are shuffled to prevent order bias.
    """
    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    # Filter by experiment if specified
    if experiment_id:
        responses = [r for r in responses if r.get("experiment_id") == experiment_id]

    # Build a lookup of existing codings by response_id
    coding_lookup = {}
    for c in codings:
        coding_lookup[c["response_id"]] = c

    # Shuffle to prevent order bias
    if shuffle_seed is not None:
        random.seed(shuffle_seed)
    random.shuffle(responses)

    # Build blind response objects (condition hidden)
    blind_responses = []
    for r in responses:
        blind_item = {
            "id": r["id"],
            "experiment_id": r.get("experiment_id"),
            "scenario_id": r.get("scenario_id"),
            "model": r.get("model"),
            "replicate_number": r.get("replicate_number"),
            "generated_response": r.get("generated_response"),
            "user_prompt": r.get("user_prompt"),
            # Deliberately omit: condition, system_prompt (may leak gender info)
            "coding": coding_lookup.get(r["id"]),
        }
        blind_responses.append(blind_item)

    total = len(blind_responses)
    coded = sum(1 for b in blind_responses if b["coding"] is not None)

    return {
        "total": total,
        "coded": coded,
        "remaining": total - coded,
        "data": blind_responses,
    }


@router.post("", status_code=201)
def save_coding(payload: CodingCreate):
    """Save or update a coding entry for a response."""
    # Verify the response exists
    response = find_by_id(RESPONSES_FILE, payload.response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    data = read_json(CODING_FILE)

    # Check if a coding already exists for this response
    for i, item in enumerate(data):
        if item.get("response_id") == payload.response_id:
            # Update existing
            coding = Coding(**payload.model_dump())
            coding_dict = coding.model_dump()
            coding_dict["id"] = item["id"]  # Keep original ID
            data[i] = coding_dict
            write_json(CODING_FILE, data)
            return data[i]

    # Create new
    coding = Coding(**payload.model_dump())
    data.append(coding.model_dump())
    write_json(CODING_FILE, data)
    return coding.model_dump()


@router.get("/{coding_id}")
def get_coding(coding_id: str):
    """Return a single coding entry."""
    item = find_by_id(CODING_FILE, coding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Coding not found")
    return item
