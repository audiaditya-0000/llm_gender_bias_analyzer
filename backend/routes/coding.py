"""
Blind coding routes.

Serves responses without gender condition labels for unbiased researcher coding.

Supports independent coding by multiple coders. Responses are partitioned such that:
- 20% of pairs form a shared overlap pool assigned to BOTH Coder 1 and Coder 2 (for ICC / MAD).
- The remaining 80% of pairs are evenly split (50/50: 40% Coder 1 exclusive, 40% Coder 2 exclusive).
- Neither coder can view the other coder's responses or scores outside the overlap set.
- Within the overlap set, ratings are submitted and viewed independently by each coder.
"""

import hashlib
import random
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from models import Coding, CodingCreate, generate_id
from storage import read_json, upsert_record, find_by_id


router = APIRouter(prefix="/api/coding", tags=["coding"])


CODING_FILE = "coding.json"
RESPONSES_FILE = "responses.json"
SCENARIOS_FILE = "scenarios.json"


# ── Neutralization Helper ────────────────────────────────────────────────────

NEUTRAL_TOKENS = {
    r"\{PC_NOUN\}": "person",
    r"\{PC_SUBJECT\}": "they",
    r"\{PC_OBJECT\}": "them",
    r"\{PC_POSSESSIVE\}": "their",
    r"\{PC_REFLEXIVE\}": "themself",
    r"\{PC_ADJECTIVE\}": "capable",
}


def _neutralize_text(text: str) -> str:
    """Replace explicit PC gender tokens with neutral phrasing."""
    if not text:
        return ""
    result = text
    for pattern, replacement in NEUTRAL_TOKENS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _is_a_first(pair_id: str, seed: Optional[int] = None) -> bool:
    """Deterministically randomize Version A / Version B assignment per pair."""
    s = seed if isinstance(seed, int) else 0
    h = hashlib.md5(f"{s}_{pair_id}".encode()).hexdigest()
    return int(h, 16) % 2 == 0


# ── List Codings ──────────────────────────────────────────────────────────────

@router.get("")
def list_codings(
    coder_id: Optional[str] = Query(None),
):
    """
    Return coding entries.
    If coder_id is provided, only that coder's entries are returned.
    """
    active_coder = coder_id if isinstance(coder_id, str) and coder_id else None
    codings = read_json(CODING_FILE)

    if active_coder:
        codings = [
            c for c in codings
            if c.get("coder_id") == active_coder
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
    Return responses grouped as blind pairs with gender condition labels hidden.
    Each pair has Version A and Version B (counterbalanced/randomized).

    Multi-coder queue partitioning:
    - 20% overlap pool assigned to BOTH Coder 1 and Coder 2.
    - 40% exclusive queue for Coder 1.
    - 40% exclusive queue for Coder 2.
    - If coder_id is provided, only that coder's assigned pairs are returned,
      and only that coder's existing scores are attached.
    """
    active_exp = experiment_id if isinstance(experiment_id, str) and experiment_id else None
    active_coder = coder_id if isinstance(coder_id, str) and coder_id in ("coder_1", "coder_2") else None
    active_seed = shuffle_seed if isinstance(shuffle_seed, int) else None

    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)
    scenarios = read_json(SCENARIOS_FILE)

    scenario_map = {s["id"]: s for s in scenarios if s.get("id")}

    if active_exp:
        responses = [
            r for r in responses
            if r.get("experiment_id") == active_exp
        ]

    # Only include the requesting coder's codings in the lookup
    if active_coder:
        codings = [
            c for c in codings
            if c.get("coder_id") == active_coder
        ]

    coding_lookup = {
        c["response_id"]: c
        for c in codings
        if c.get("response_id")
    }

    # Group all responses by pair_id to establish global deterministic assignment
    all_pairs_dict: dict[str, list[dict]] = {}
    for r in responses:
        pid = r.get("pair_id") or r.get("id")
        if pid not in all_pairs_dict:
            all_pairs_dict[pid] = []
        all_pairs_dict[pid].append(r)

    # Sort all pairs deterministically across the study by scenario, scaffold, model, replicate, pair_id
    sorted_study_pairs = sorted(
        all_pairs_dict.items(),
        key=lambda item: (
            item[1][0].get("scenario_id", ""),
            item[1][0].get("scaffold_id", ""),
            item[1][0].get("model", ""),
            item[1][0].get("replicate_number", 1),
            item[0],
        )
    )

    pair_assignment: dict[str, dict] = {}
    for idx, (pid, _) in enumerate(sorted_study_pairs):
        if idx % 5 == 0:
            # 20% Overlap pool: assigned to both coders
            pair_assignment[pid] = {
                "is_overlap": True,
                "assigned_coders": ["coder_1", "coder_2"],
            }
        elif idx % 5 in (1, 2):
            # 40% Coder 1 exclusive pool
            pair_assignment[pid] = {
                "is_overlap": False,
                "assigned_coders": ["coder_1"],
            }
        else:
            # 40% Coder 2 exclusive pool
            pair_assignment[pid] = {
                "is_overlap": False,
                "assigned_coders": ["coder_2"],
            }

    pairs_dict = all_pairs_dict

    blind_pairs = []
    for pid, res_list in pairs_dict.items():
        assign_info = pair_assignment.get(
            pid,
            {"is_overlap": False, "assigned_coders": ["coder_1", "coder_2"]},
        )

        # Queue filtering: if coder_id is provided, only return pairs assigned to them
        if active_coder and active_coder not in assign_info["assigned_coders"]:
            continue

        if len(res_list) >= 2:
            r1, r2 = res_list[0], res_list[1]
            if not _is_a_first(pid, active_seed):
                r1, r2 = r2, r1
        else:
            r1 = res_list[0]
            r2 = None

        coding_a = coding_lookup.get(r1["id"])
        coding_b = coding_lookup.get(r2["id"]) if r2 else None

        # Look up neutral scenario title and description (without PC gender tokens)
        scenario = scenario_map.get(r1.get("scenario_id", ""))
        if scenario:
            scenario_title = scenario.get("title", "")
            scenario_desc = _neutralize_text(scenario.get("description", ""))
        else:
            scenario_title = ""
            scenario_desc = ""

        blind_pair = {
            "pair_id": pid,
            "experiment_id": r1.get("experiment_id"),
            "scenario_id": r1.get("scenario_id"),
            "scenario_title": scenario_title,
            "scenario_description": scenario_desc,
            "scenario_prompt": scenario_desc,  # Replaces raw prompt to prevent gender leak
            "scaffold_prompt": r1.get("scaffold_prompt", r1.get("system_prompt", "")),
            "replicate_number": r1.get("replicate_number", 1),
            "is_overlap": assign_info["is_overlap"],
            "assigned_coders": assign_info["assigned_coders"],
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

    if isinstance(shuffle_seed, int):
        rng = random.Random(shuffle_seed)
        rng.shuffle(blind_pairs)

    total = len(blind_pairs)
    coded = sum(1 for p in blind_pairs if p["is_coded"])
    overlap_count = sum(1 for p in blind_pairs if p.get("is_overlap"))

    return {
        "total": total,
        "coded": coded,
        "remaining": total - coded,
        "overlap_count": overlap_count,
        "coder_id": coder_id,
        "data": blind_pairs,
    }


# ── Save Coding ──────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def save_coding(payload: CodingCreate):
    """Save or update a coding entry for a response and coder."""
    response = find_by_id(RESPONSES_FILE, payload.response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    existing_codings = read_json(CODING_FILE)
    existing_id = None
    for c in existing_codings:
        if (
            c.get("response_id") == payload.response_id
            and c.get("coder_id") == payload.coder_id
        ):
            existing_id = c.get("id")
            break

    coding = Coding(
        id=existing_id or generate_id(),
        response_id=payload.response_id,
        coder_id=payload.coder_id,
        truth=payload.truth,
        indeterminacy=payload.indeterminacy,
        falsity=payload.falsity,
        reasoning_notes=payload.reasoning_notes or "",
    )

    saved = upsert_record(CODING_FILE, coding.model_dump())
    return saved


# ── Get Single Coding ────────────────────────────────────────────────────────

@router.get("/{coding_id}")
def get_coding(coding_id: str):
    """Return a single coding entry."""
    item = find_by_id(CODING_FILE, coding_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Coding not found"
        )
    return item