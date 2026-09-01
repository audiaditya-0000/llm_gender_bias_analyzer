"""
Blind coding routes.

Serves responses without gender condition labels for unbiased researcher coding.

Supports independent coding by multiple coders. Each coder has their own
coding record for each response.
"""

import random
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import Coding, CodingCreate
from storage import read_json, write_json, find_by_id


router = APIRouter(prefix="/api/coding", tags=["coding"])


CODING_FILE = "coding.json"
RESPONSES_FILE = "responses.json"


# ── List Codings ──────────────────────────────────────────────────────────────

@router.get("")
def list_codings(
    coder_id: Optional[str] = Query(None),
):
    """
    Return coding entries.

    If coder_id is provided, only that coder's entries are returned.
    """
    codings = read_json(CODING_FILE)

    if coder_id:
        codings = [
            c for c in codings
            if c.get("coder_id") == coder_id
        ]

    return codings


# ── Blind Responses ──────────────────────────────────────────────────────────

@router.get("/blind")
def get_blind_responses(
    experiment_id: Optional[str] = Query(None),
    shuffle_seed: Optional[int] = Query(None),
    coder_id: Optional[str] = Query(None),
):
    """
    Return responses with gender condition hidden.

    If coder_id is provided, only that coder's existing coding
    is returned for each response.

    Responses are shuffled using the supplied seed.
    """

    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    # ---------------------------------------------------------
    # Filter by experiment
    # ---------------------------------------------------------

    if experiment_id:
        responses = [
            r for r in responses
            if r.get("experiment_id") == experiment_id
        ]

    # ---------------------------------------------------------
    # Filter coding records by coder
    # ---------------------------------------------------------

    if coder_id:
        codings = [
            c for c in codings
            if c.get("coder_id") == coder_id
        ]

    # ---------------------------------------------------------
    # Build lookup
    # ---------------------------------------------------------

    coding_lookup = {
        c["response_id"]: c
        for c in codings
        if c.get("response_id")
    }

    # ---------------------------------------------------------
    # Shuffle
    # ---------------------------------------------------------

    if shuffle_seed is not None:
        random.seed(shuffle_seed)

    random.shuffle(responses)

    # ---------------------------------------------------------
    # Build blind response objects
    # ---------------------------------------------------------

    blind_responses = []

    for r in responses:

        existing_coding = coding_lookup.get(r["id"])

        blind_item = {
            "id": r["id"],
            "experiment_id": r.get("experiment_id"),
            "scenario_id": r.get("scenario_id"),
            "model": r.get("model"),
            "replicate_number": r.get("replicate_number"),
            "generated_response": r.get("generated_response"),
            "user_prompt": r.get("user_prompt"),

            # Only this coder's coding is returned
            "codings": existing_coding,
        }

        blind_responses.append(blind_item)

    total = len(blind_responses)

    coded = sum(
        1
        for item in blind_responses
        if item["codings"] is not None
    )

    return {
        "total": total,
        "coded": coded,
        "remaining": total - coded,
        "coder_id": coder_id,
        "data": blind_responses,
    }


# ── Save Coding ──────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def save_coding(payload: CodingCreate):
    """Save or update a coding entry for a response and coder."""

    # Verify the response exists
    response = find_by_id(RESPONSES_FILE, payload.response_id)

    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    data = read_json(CODING_FILE)

    # Check if this coder has already coded this response
    for i, item in enumerate(data):
        if (
            item.get("response_id") == payload.response_id
            and item.get("coder_id") == payload.coder_id
        ):
            coding = Coding(**payload.model_dump())

            coding_dict = coding.model_dump()

            # Keep original coding ID
            coding_dict["id"] = item["id"]

            data[i] = coding_dict

            write_json(CODING_FILE, data)

            return data[i]

    # Create new coding
    coding = Coding(**payload.model_dump())

    data.append(coding.model_dump())

    write_json(CODING_FILE, data)

    return coding.model_dump()


# ── Get Single Coding ────────────────────────────────────────────────────────

@router.get("/{coding_id}")
def get_coding(coding_id: str):
    """
    Return a single coding entry.
    """

    item = find_by_id(
        CODING_FILE,
        coding_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Coding not found"
        )

    return item