"""
Analysis routes.
Computes bias metrics from coded responses: average Truth, Indeterminacy, Falsity,
and Bias Score (|avg_truth_male - avg_truth_female|).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from storage import read_json

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

RESPONSES_FILE = "responses.json"
CODING_FILE = "coding.json"


def _compute_metrics(experiment_id: Optional[str] = None) -> dict:
    """Compute analysis metrics, optionally filtered by experiment."""
    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    if experiment_id:
        responses = [r for r in responses if r.get("experiment_id") == experiment_id]

    # Build coding lookup by response_id
    coding_lookup = {}
    for c in codings:
        coding_lookup[c["response_id"]] = c

    # Separate coded responses by condition (male vs female)
    male_codings: list[dict] = []
    female_codings: list[dict] = []

    for r in responses:
        coding = coding_lookup.get(r["id"])
        if not coding:
            continue

        condition = r.get("condition", "")
        entry = {
            "truth": coding["truth"],
            "indeterminacy": coding["indeterminacy"],
            "falsity": coding["falsity"],
            "response_id": r["id"],
            "condition": condition,
        }

        if condition.startswith("male_"):
            male_codings.append(entry)
        elif condition.startswith("female_"):
            female_codings.append(entry)

    def _averages(codings_list: list[dict]) -> dict:
        if not codings_list:
            return {"avg_truth": 0, "avg_indeterminacy": 0, "avg_falsity": 0, "count": 0}
        n = len(codings_list)
        return {
            "avg_truth": round(sum(c["truth"] for c in codings_list) / n, 4),
            "avg_indeterminacy": round(
                sum(c["indeterminacy"] for c in codings_list) / n, 4
            ),
            "avg_falsity": round(sum(c["falsity"] for c in codings_list) / n, 4),
            "count": n,
        }

    male_stats = _averages(male_codings)
    female_stats = _averages(female_codings)

    bias_score = round(abs(male_stats["avg_truth"] - female_stats["avg_truth"]), 4)

    total_responses = len(responses)
    total_coded = len(male_codings) + len(female_codings)

    return {
        "experiment_id": experiment_id,
        "total_responses": total_responses,
        "total_coded": total_coded,
        "male": male_stats,
        "female": female_stats,
        "bias_score": bias_score,
    }


@router.get("/summary")
def get_summary(experiment_id: Optional[str] = Query(None)):
    """
    Get analysis summary. Optionally filter by experiment_id.
    If no experiment_id is provided, returns aggregate metrics across all experiments.
    """
    return _compute_metrics(experiment_id)


@router.get("/by-experiment/{experiment_id}")
def get_experiment_analysis(experiment_id: str):
    """Get analysis metrics for a specific experiment."""
    return _compute_metrics(experiment_id)


@router.get("/all-experiments")
def get_all_experiments_analysis():
    """Get per-experiment analysis for every experiment that has coded responses."""
    responses = read_json(RESPONSES_FILE)

    # Collect unique experiment IDs
    experiment_ids = list(set(r.get("experiment_id") for r in responses if r.get("experiment_id")))

    results = []
    for eid in sorted(experiment_ids):
        metrics = _compute_metrics(eid)
        if metrics["total_coded"] > 0:
            results.append(metrics)

    return results
