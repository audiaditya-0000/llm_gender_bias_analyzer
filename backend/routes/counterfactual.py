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

# ── Built-in gendered word pairs ──────────────────────────────────────────────
# Each tuple is (male_form, female_form)
BUILTIN_WORD_PAIRS: list[tuple[str, str]] = [
    # Pronouns
    ("he", "she"),
    ("him", "her"),
    ("his", "hers"),
    ("himself", "herself"),
    # Common nouns
    ("man", "woman"),
    ("male", "female"),
    ("boy", "girl"),
    # Family
    ("father", "mother"),
    ("son", "daughter"),
    ("brother", "sister"),
    ("husband", "wife"),
    # Titles
    ("king", "queen"),
    ("prince", "princess"),
    ("sir", "madam"),
    ("mr", "mrs"),
    ("actor", "actress"),
    # Domain-specific defaults
    ("emperor", "empress"),
    ("lord", "lady"),
    ("duke", "duchess"),
    ("wizard", "witch"),
    ("monk", "nun"),
    ("salesman", "saleswoman"),
    ("hero", "heroine"),
    ("waiter", "waitress"),
    ("god", "goddess"),
    ("bachelor", "bachelorette"),
]

CUSTOM_PAIRS_FILE = "custom_word_pairs.json"


def _get_all_pairs() -> list[tuple[str, str]]:
    """Merge built-in pairs with any user-configured custom pairs."""
    pairs = list(BUILTIN_WORD_PAIRS)
    custom = read_json(CUSTOM_PAIRS_FILE)
    for entry in custom:
        pairs.append((entry["male_term"].lower(), entry["female_term"].lower()))
    return pairs


def _swap_gendered_terms(text: str, direction: str) -> tuple[str, list[dict]]:
    """
    Swap gendered terms in the given text.
    direction: "to_male" or "to_female"
    Returns (swapped_text, list_of_swaps_made).
    """
    pairs = _get_all_pairs()
    swaps_made: list[dict] = []
    result = text

    for male_form, female_form in pairs:
        if direction == "to_male":
            source, target = female_form, male_form
        else:
            source, target = male_form, female_form

        # Case-sensitive replacements: lowercase, Capitalized, UPPERCASE
        for src, tgt in [
            (source, target),
            (source.capitalize(), target.capitalize()),
            (source.upper(), target.upper()),
        ]:
            pattern = re.compile(r"\b" + re.escape(src) + r"\b")
            matches = pattern.findall(result)
            if matches:
                result = pattern.sub(tgt, result)
                swaps_made.append(
                    {"original": src, "replaced_with": tgt, "count": len(matches)}
                )

    return result, swaps_made


def _generate_pair(base_prompt: str, swap_type: str) -> tuple[str, str, list[dict]]:
    """
    Generate a male/female prompt pair from a base prompt.
    The base prompt is treated as gender-neutral; we produce both gendered versions.
    """
    male_prompt, male_swaps = _swap_gendered_terms(base_prompt, "to_male")
    female_prompt, female_swaps = _swap_gendered_terms(base_prompt, "to_female")

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
    valid_types = ["npc", "player", "third_person"]
    if payload.swap_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid swap_type. Must be one of: {valid_types}",
        )

    male_prompt, female_prompt, swaps = _generate_pair(
        payload.prompt, payload.swap_type
    )

    return CounterfactualResponse(
        male_prompt=male_prompt,
        female_prompt=female_prompt,
        swap_type=payload.swap_type,
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
