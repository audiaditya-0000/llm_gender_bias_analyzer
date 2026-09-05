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
    swap_gendered_terms,
)


def _generate_pair(base_prompt: str) -> tuple[str, str, list[dict]]:
    """
    Generate a male/female prompt pair from a base prompt.
    The base prompt is treated as gender-neutral; we produce both gendered versions.
    """
    male_prompt, male_swaps = swap_gendered_terms(base_prompt, "to_male")
    female_prompt, female_swaps = swap_gendered_terms(base_prompt, "to_female")

    # If no swaps happened in either direction, the prompt may already be gendered.
    # In that case, treat the base as one version and swap to get the other.
    all_swaps = male_swaps + female_swaps

    if not male_swaps and not female_swaps:
        # No gendered terms found at all — return the original as both
        return base_prompt, base_prompt, []

    return male_prompt, female_prompt, all_swaps


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/generate")
def generate_counterfactual(payload: CounterfactualRequest):
    """Generate a counterfactual male/female prompt pair."""
    male_prompt, female_prompt, swaps = _generate_pair(payload.prompt)

    return CounterfactualResponse(
        male_prompt=male_prompt,
        female_prompt=female_prompt,
        swaps_made=swaps,
    ).model_dump()


# ── Custom Word Pairs Management ──────────────────────────────────────────────


@router.get("/word-pairs")
def list_word_pairs():
    """Return all word pairs: built-in + custom."""
    builtin = [
        {"male_term": m, "female_term": f, "builtin": True}
        for m, f in BUILTIN_WORD_PAIRS
    ]
    custom = read_json(CUSTOM_PAIRS_FILE)
    for entry in custom:
        entry["builtin"] = False
    return builtin + custom


@router.post("/word-pairs", status_code=201)
def add_word_pair(payload: WordPairCreate):
    """Add a custom word pair."""
    pair = WordPair(**payload.model_dump())
    data = read_json(CUSTOM_PAIRS_FILE)
    data.append(pair.model_dump())
    write_json(CUSTOM_PAIRS_FILE, data)
    return pair.model_dump()


@router.delete("/word-pairs/{pair_id}")
def remove_word_pair(pair_id: str):
    """Remove a custom word pair. Built-in pairs cannot be removed."""
    if not delete_by_id(CUSTOM_PAIRS_FILE, pair_id):
        raise HTTPException(status_code=404, detail="Custom word pair not found")
    return {"deleted": True}
