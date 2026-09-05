"""
Shared gender-swap utility.

Used by both the counterfactual generator and the experiment runner
so that the same word-pair list and swap logic is applied consistently.
"""

import re
from storage import read_json

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


def get_all_pairs() -> list[tuple[str, str]]:
    """Merge built-in pairs with any user-configured custom pairs."""
    pairs = list(BUILTIN_WORD_PAIRS)
    custom = read_json(CUSTOM_PAIRS_FILE)
    for entry in custom:
        pairs.append((entry["male_term"].lower(), entry["female_term"].lower()))
    return pairs


def swap_gendered_terms(text: str, direction: str) -> tuple[str, list[dict]]:
    """
    Swap gendered terms in the given text.

    direction: "to_male" or "to_female"

    Returns (swapped_text, list_of_swaps_made).
    """
    pairs = get_all_pairs()
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


def generate_swapped_scenario(base_text: str) -> tuple[str, list[dict]]:
    """
    Produce a gender-swapped version of a scenario text.

    Attempts to swap to female first; if no female terms exist,
    swaps to male. Returns (swapped_text, swaps_made).
    """
    female_text, female_swaps = swap_gendered_terms(base_text, "to_female")
    if female_swaps:
        return female_text, female_swaps

    male_text, male_swaps = swap_gendered_terms(base_text, "to_male")
    if male_swaps:
        return male_text, male_swaps

    # No gendered terms found — return original unchanged
    return base_text, []
