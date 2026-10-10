"""
Counterfactual prompt generator.
Swaps gendered terms in prompts to produce matched male/female pairs.
Supports configurable custom word pairs loaded from data/custom_word_pairs.json.
"""

import re
from fastapi import APIRouter, HTTPException
from models import CounterfactualRequest, CounterfactualResponse, WordPair, WordPairCreate
from storage import read_json, write_json, delete_by_id

router = APIRouter(prefix="/api/counterfactual", tags=["counterfactual"])

from services.gender_swap import (
    BUILTIN_WORD_PAIRS,
    CUSTOM_PAIRS_FILE,
    render_scenario
)


def _generate_pair(base_prompt: str) -> tuple[str, str, list[dict]]:
    """
    Generate a male/female prompt pair from a base template prompt.
    Returns male_prompt, female_prompt, and an empty swaps list (since we use explicit tokens now).
    """
    male_prompt = render_scenario(base_prompt, "male")
    female_prompt = render_scenario(base_prompt, "female")

    # Swaps made are no longer tracked at a granular level since it's deterministic tokens
    return male_prompt, female_prompt, []


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@router.post("/generate")
def generate_counterfactual(payload: CounterfactualRequest):
    """Generate a counterfactual male/female prompt pair."""
    male_prompt, female_prompt, swaps = _generate_pair(payload.prompt)

    return CounterfactualResponse(
        male_prompt=male_prompt,
        female_prompt=female_prompt,
        swaps_made=swaps,
    ).model_dump()


# -------------------------------------------------------------------
# Custom Word Pairs Management (Legacy/No-op but kept for UI compatibility)
# -------------------------------------------------------------------


@router.get("/word-pairs")
def list_word_pairs():
    """Return all word pairs: built-in + custom."""
    builtin = [
        {"male_term": m, "female_term": f, "builtin": True}
        for m, f in BUILTIN_WORD_PAIRS
    ]
    try:
        custom = read_json(CUSTOM_PAIRS_FILE)
        for entry in custom:
            entry["builtin"] = False
    except FileNotFoundError:
        custom = []
    return builtin + custom


@router.post("/word-pairs", status_code=201)
def add_word_pair(payload: WordPairCreate):
    """Add a custom word pair."""
    pair = WordPair(**payload.model_dump())
    try:
        data = read_json(CUSTOM_PAIRS_FILE)
    except FileNotFoundError:
        data = []
    data.append(pair.model_dump())
    write_json(CUSTOM_PAIRS_FILE, data)
    return pair.model_dump()


@router.delete("/word-pairs/{pair_id}")
def remove_word_pair(pair_id: str):
    """Remove a custom word pair. Built-in pairs cannot be removed."""
    if not delete_by_id(CUSTOM_PAIRS_FILE, pair_id):
        raise HTTPException(status_code=404, detail="Custom word pair not found")
    return {"deleted": True}

