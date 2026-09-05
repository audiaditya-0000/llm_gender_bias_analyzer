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


import hashlib

def _is_a_first(pair_id: str, seed: Optional[int] = None) -> bool:
    h = hashlib.md5(f"{seed}_{pair_id}".encode()).hexdigest()
    return int(h, 16) % 2 == 0


# ── Blind Responses ──────────────────────────────────────────────────────────

@router.get("/blind")
def get_blind_responses(
    experiment_id: Optional[str] = Query(None),
    shuffle_seed: Optional[int] = Query(None),
    coder_id: Optional[str] = Query(None),
):
    """
    Return responses grouped as blind pairs with condition labels hidden.
    Each pair has Version A and Version B (counterbalanced/randomized).
    """
    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    if experiment_id:
        responses = [
            r for r in responses
            if r.get("experiment_id") == experiment_id
        ]

    if coder_id:
        codings = [
            c for c in codings
            if c.get("coder_id") == coder_id
        ]

    coding_lookup = {
        c["response_id"]: c
        for c in codings
        if c.get("response_id")
    }

    # Group responses by pair_id
    pairs_dict: dict[str, list[dict]] = {}
    for r in responses:
        pid = r.get("pair_id") or r.get("id")
        if pid not in pairs_dict:
            pairs_dict[pid] = []
        pairs_dict[pid].append(r)

    blind_pairs = []
    for pid, res_list in pairs_dict.items():
        if len(res_list) >= 2:
            r1, r2 = res_list[0], res_list[1]
            if not _is_a_first(pid, shuffle_seed):
                r1, r2 = r2, r1
        else:
            r1 = res_list[0]
            r2 = None

        coding_a = coding_lookup.get(r1["id"])
        coding_b = coding_lookup.get(r2["id"]) if r2 else None

        blind_pair = {
            "pair_id": pid,
            "experiment_id": r1.get("experiment_id"),
            "scenario_id": r1.get("scenario_id"),
            "model": r1.get("model"),
            "replicate_number": r1.get("replicate_number", 1),
            "scenario_prompt": r1.get("scenario_prompt", r1.get("user_prompt", "")),
            "scaffold_prompt": r1.get("scaffold_prompt", r1.get("system_prompt", "")),
            "version_a": {
                "response_id": r1["id"],
                "generated_response": r1.get("generated_response", ""),
                "coding": coding_a,
            },
            "version_b": {
                "response_id": r2["id"],
                "generated_response": r2.get("generated_response", ""),
                "coding": coding_b,
            } if r2 else None,
            "is_coded": bool(coding_a and (coding_b or r2 is None)),
        }
        blind_pairs.append(blind_pair)

    if shuffle_seed is not None:
        rng = random.Random(shuffle_seed)
        rng.shuffle(blind_pairs)

    total = len(blind_pairs)
    coded = sum(1 for p in blind_pairs if p["is_coded"])

    return {
        "total": total,
        "coded": coded,
        "remaining": total - coded,
        "coder_id": coder_id,
        "data": blind_pairs,
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