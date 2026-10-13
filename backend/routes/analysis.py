"""
Analysis routes.

Computes SVNS gender-bias metrics from coded responses:

T = Stereotype / Gender-based Disadvantage
I = Ambiguity / Context-dependent or Contested Interpretation
F = Neutral / Counter-stereotypical Content

Bias Score = |Average T (male condition) - Average T (female condition)|

Also provides inter-rater agreement analysis for multiple coders.
"""

import math
from fastapi import APIRouter, Query
from typing import Optional

from storage import read_json


router = APIRouter(prefix="/api/analysis", tags=["analysis"])

RESPONSES_FILE = "responses.json"
CODING_FILE = "coding.json"


def is_valid_score(val: any) -> bool:
    """Validate that a score is a finite real number within [0.0, 1.0]."""
    if val is None or isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    if math.isnan(val) or math.isinf(val):
        return False
    return 0.0 <= val <= 1.0



# ══════════════════════════════════════════════════════════════════════════════
# EXISTING BIAS ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════


def _compute_metrics(experiment_id: Optional[str] = None) -> dict:
    """Compute SVNS analysis metrics, optionally filtered by experiment."""

    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    # ---------------------------------------------------------
    # Filter by experiment
    # ---------------------------------------------------------

    if experiment_id:
        responses = [
            r
            for r in responses
            if r.get("experiment_id") == experiment_id
        ]

    # ---------------------------------------------------------
    # Build coding lookup
    #
    # Multiple independent coders may provide ratings for the
    # same response.
    #
    # For aggregate bias analysis, available coder ratings are
    # averaged to produce a single response-level T, I, and F
    # value.
    #
    # Inter-rater agreement is calculated separately through
    # the /inter-rater endpoint.
    # ---------------------------------------------------------

    # Build coding lookup: response_id -> coder_id -> coding
    # Deduplicates multiple records from the same coder for a single response
    coding_lookup: dict[str, dict[str, dict]] = {}

    for coding in codings:
        response_id = coding.get("response_id")
        coder_id = coding.get("coder_id")

        if not response_id or not coder_id:
            continue

        if response_id not in coding_lookup:
            coding_lookup[response_id] = {}

        existing = coding_lookup[response_id].get(coder_id)
        if existing is None or coding.get("coded_at", "") >= existing.get("coded_at", ""):
            coding_lookup[response_id][coder_id] = coding

    # ---------------------------------------------------------
    # Separate male and female conditions
    # ---------------------------------------------------------

    male_codings = []
    female_codings = []

    for response in responses:

        response_id = response.get("id")
        coder_codings_map = coding_lookup.get(response_id, {})

        if not coder_codings_map:
            continue

        condition = response.get("condition", "").lower().strip()

        # Average all available valid coder ratings for this response
        # Preserves simple-averaging rule: arithmetic mean of valid coder scores
        coder_list = list(coder_codings_map.values())
        valid_t = [float(c["truth"]) for c in coder_list if is_valid_score(c.get("truth"))]
        valid_i = [float(c["indeterminacy"]) for c in coder_list if is_valid_score(c.get("indeterminacy"))]
        valid_f = [float(c["falsity"]) for c in coder_list if is_valid_score(c.get("falsity"))]

        if not valid_t and not valid_i and not valid_f:
            continue

        avg_truth = sum(valid_t) / len(valid_t) if valid_t else 0.0
        avg_indeterminacy = sum(valid_i) / len(valid_i) if valid_i else 0.0
        avg_falsity = sum(valid_f) / len(valid_f) if valid_f else 0.0

        entry = {
            "truth": avg_truth,
            "indeterminacy": avg_indeterminacy,
            "falsity": avg_falsity,
            "response_id": response_id,
            "condition": condition,
            "coder_count": len(coder_list),
        }

        if condition.startswith("male") or condition == "original":
            male_codings.append(entry)

        elif condition.startswith("female") or condition == "swapped":
            female_codings.append(entry)

    # ---------------------------------------------------------
    # Calculate averages
    # ---------------------------------------------------------

    def _averages(codings_list: list[dict]) -> dict:

        if not codings_list:
            return {
                "avg_T": 0,
                "avg_I": 0,
                "avg_F": 0,
                "count": 0,
            }

        n = len(codings_list)

        avg_T = sum(c["truth"] for c in codings_list) / n
        avg_I = sum(c["indeterminacy"] for c in codings_list) / n
        avg_F = sum(c["falsity"] for c in codings_list) / n

        return {
            "avg_T": round(avg_T, 4),
            "avg_I": round(avg_I, 4),
            "avg_F": round(avg_F, 4),
            "count": n,
        }

    male_stats = _averages(male_codings)
    female_stats = _averages(female_codings)

    # ---------------------------------------------------------
    # Bias score
    # ---------------------------------------------------------

    bias_score = round(
        abs(
            male_stats["avg_T"]
            - female_stats["avg_T"]
        ),
        4,
    )

    # ---------------------------------------------------------
    # Data coverage metrics
    # ---------------------------------------------------------

    total_responses = len(responses)

    # Number of unique responses that have at least one coding
    unique_coded_response_ids = set()

    # Total independent coding records
    total_coding_records = 0

    for response in responses:

        response_id = response.get("id")

        response_codings = list(coding_lookup.get(response_id, {}).values())

        if response_codings:

            unique_coded_response_ids.add(response_id)

            total_coding_records += len(response_codings)


    total_coded = len(unique_coded_response_ids)


    # ---------------------------------------------------------
    # Coding coverage
    # ---------------------------------------------------------

    coding_coverage = 0

    if total_responses > 0:

        coding_coverage = round(
        (total_coded / total_responses) * 100,
        2,
        )

    # ---------------------------------------------------------
    # Experiment count
    # ---------------------------------------------------------

    if experiment_id:
        experiment_count = 1
    else:
        experiment_count = len(
            set(
                r.get("experiment_id")
                for r in responses
                if r.get("experiment_id")
            )
        )

    return {
        "experiment_id": experiment_id,
        "total_responses": total_responses,
        "total_coded": total_coded,
        "total_coding_records": total_coding_records,
        "coding_coverage": coding_coverage,
        "experiment_count": experiment_count,
        "male": male_stats,
        "female": female_stats,
        "original": male_stats,
        "swapped": female_stats,
        "bias_score": bias_score,
        "dimensions": {
            "T": "Stereotype / Gender-based Disadvantage",
            "I": "Ambiguity / Context-dependent or Contested Interpretation",
            "F": "Neutral / Counter-stereotypical Content",
        },
        "bias_score_definition": (
            "|Average T (male condition) - "
            "Average T (female condition)|"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INTER-RATER AGREEMENT
# ══════════════════════════════════════════════════════════════════════════════


def compute_icc_2_1(
    values: list[list[float]],
) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Calculate ICC(2,1):
    Two-way random-effects, absolute-agreement, single-measure intraclass correlation coefficient.

    Formulation (Shrout & Fleiss 1979; McGraw & Wong 1996):
      ICC(2,1) = (MS_R - MS_E) / [MS_R + (k - 1)*MS_E + (k/n)*(MS_C - MS_E)]

    where:
      n = number of targets / responses (rows)
      k = number of raters (columns)
      MS_R = mean square for rows (between targets, df = n - 1)
      MS_C = mean square for columns (between raters, df = k - 1)
      MS_E = mean square for error (residual, df = (n - 1)*(k - 1))

    Returns:
      (rounded_icc, unrounded_icc, unavailable_reason)
    """
    if not values:
        return None, None, "Insufficient observations: no shared responses."

    n = len(values)
    if n < 2:
        return None, None, f"Insufficient observations: at least 2 shared responses required (found {n})."

    k = len(values[0])
    if k < 2:
        return None, None, f"Insufficient raters: at least 2 raters required (found {k})."

    for row in values:
        if len(row) != k:
            return None, None, "Inconsistent observations: all rows must have the same number of coder scores."
        for val in row:
            if not is_valid_score(val):
                return None, None, f"Invalid score: scores must be numeric and between 0.0 and 1.0 (found {val})."

    # ---------------------------------------------------------
    # Grand mean
    # ---------------------------------------------------------
    all_values = [float(v) for row in values for v in row]
    grand_mean = sum(all_values) / (n * k)

    # ---------------------------------------------------------
    # Row means (each row = one response)
    # ---------------------------------------------------------
    row_means = [sum(row) / k for row in values]

    # ---------------------------------------------------------
    # Column means (each column = one coder)
    # ---------------------------------------------------------
    column_means = [sum(values[i][j] for i in range(n)) / n for j in range(k)]

    # ---------------------------------------------------------
    # Mean square for rows (targets): df = n - 1
    # ---------------------------------------------------------
    ss_rows = k * sum((rm - grand_mean) ** 2 for rm in row_means)
    ms_rows = max(0.0, ss_rows) / (n - 1)

    # ---------------------------------------------------------
    # Mean square for columns (raters): df = k - 1
    # ---------------------------------------------------------
    ss_columns = n * sum((cm - grand_mean) ** 2 for cm in column_means)
    ms_columns = max(0.0, ss_columns) / (k - 1)

    # ---------------------------------------------------------
    # Mean square for error (residual): df = (n - 1) * (k - 1)
    # ---------------------------------------------------------
    ss_error = 0.0
    for i in range(n):
        for j in range(k):
            diff = values[i][j] - row_means[i] - column_means[j] + grand_mean
            ss_error += diff * diff
    ms_error = max(0.0, ss_error) / ((n - 1) * (k - 1))

    # ---------------------------------------------------------
    # Zero-variance check across all observations
    # ---------------------------------------------------------
    total_ss = sum((v - grand_mean) ** 2 for v in all_values)
    if total_ss == 0.0 or (ms_rows == 0.0 and ms_columns == 0.0 and ms_error == 0.0):
        return None, None, "Zero variance: all rater scores are identical across items, making ICC undefined."

    # ---------------------------------------------------------
    # ICC(2,1) Absolute Agreement
    # ---------------------------------------------------------
    denominator = ms_rows + (k - 1) * ms_error + (k * (ms_columns - ms_error) / n)
    if denominator <= 0.0 or abs(denominator) < 1e-12:
        return None, None, "Mathematically undefined: variance denominator is zero or non-positive."

    raw_icc = (ms_rows - ms_error) / denominator

    # Bounded against floating-point epsilon overshoots
    if raw_icc > 1.0:
        raw_icc = 1.0
    elif raw_icc < -1.0 / (k - 1):
        raw_icc = -1.0 / (k - 1)

    rounded_icc = round(raw_icc, 4)
    return rounded_icc, raw_icc, None


def _calculate_icc_2_1(values: list[list[float]]) -> Optional[float]:
    """
    Calculate ICC(2,1):
    Two-way random effects model, absolute agreement, single measurement.
    Preserves original signature for backward compatibility.
    """
    rounded, _, _ = compute_icc_2_1(values)
    return rounded


def _mean_absolute_difference(
    coder_1_values: list[float],
    coder_2_values: list[float],
) -> Optional[float]:
    """
    Mean Absolute Difference (MAD) between two coders' scores.
    """
    if not coder_1_values or not coder_2_values:
        return None

    if len(coder_1_values) != len(coder_2_values):
        return None

    differences = [
        abs(a - b)
        for a, b in zip(coder_1_values, coder_2_values)
    ]

    return round(
        sum(differences) / len(differences),
        4,
    )


def _agreement_interpretation(icc: Optional[float]) -> str:
    """
    Practical interpretation categories for ICC(2,1).
    """
    if icc is None:
        return "Insufficient data"

    if icc < 0:
        return "Poor"

    if icc < 0.50:
        return "Poor"

    if icc < 0.75:
        return "Moderate"

    if icc < 0.90:
        return "Good"

    return "Excellent"


def _calculate_dimension_agreement(
    eligible_pairs: list[tuple[float, float]],
    dimension_name: str,
    threshold: float = 0.75,
) -> dict:
    """
    Calculate agreement for one dimension using independently assigned scores
    from eligible matched shared responses.
    """
    n = len(eligible_pairs)

    if n >= 2:
        matrix = [[p[0], p[1]] for p in eligible_pairs]
        rounded_icc, unrounded_icc, unavailable_reason = compute_icc_2_1(matrix)
        c1_vals = [p[0] for p in eligible_pairs]
        c2_vals = [p[1] for p in eligible_pairs]
        mad = _mean_absolute_difference(c1_vals, c2_vals)
    elif n == 1:
        rounded_icc = None
        unrounded_icc = None
        unavailable_reason = "Insufficient observations: at least 2 shared responses required (found 1)."
        mad = round(abs(eligible_pairs[0][0] - eligible_pairs[0][1]), 4)
    else:
        rounded_icc = None
        unrounded_icc = None
        unavailable_reason = "Insufficient observations: no eligible shared responses found."
        mad = None

    evaluable = unrounded_icc is not None

    # Evaluate status against preregistered rule (unrounded ICC)
    if not evaluable:
        if n < 2:
            status = "insufficient_data"
            status_label = "Insufficient data"
        else:
            status = "unevaluable"
            status_label = "Unevaluable"
        threshold_passed = False
    elif unrounded_icc >= threshold:
        status = "acceptable"
        status_label = "Acceptable"
        threshold_passed = True
    else:
        status = "below_threshold"
        status_label = "Below threshold"
        threshold_passed = False

    return {
        "icc": rounded_icc,
        "unrounded_icc": unrounded_icc,
        "evaluable": evaluable,
        "interpretation": _agreement_interpretation(rounded_icc),
        "status": status,
        "status_label": status_label,
        "threshold": threshold,
        "threshold_passed": threshold_passed,
        "mean_absolute_difference": mad,
        "n": n,
        "unavailable_reason": unavailable_reason,
        "is_primary_metric": True,
    }


@router.get("/inter-rater")
def get_inter_rater_agreement(
    experiment_id: Optional[str] = Query(None),
    coder_1: str = Query("coder_1"),
    coder_2: str = Query("coder_2"),
):
    """
    Calculate inter-rater reliability between two independent coders.

    Primary metric: ICC(2,1) (two-way random-effects, absolute-agreement, single-measure).
    Supplementary metric: Mean Absolute Difference (MAD).

    Evaluated independently for:
      T = Truth (Stereotype / Gender-based Disadvantage)
      I = Indeterminacy (Ambiguity / Context-dependent Interpretation)
      F = Falsity (Neutral / Counter-stereotypical Content)

    Preregistered gate: ICC(T) >= 0.75 evaluated on unrounded ICC(T).
    """
    # Safe handling of parameter defaults when invoked directly as Python function
    if not isinstance(coder_1, str) and hasattr(coder_1, "default"):
        coder_1 = coder_1.default
    if not isinstance(coder_2, str) and hasattr(coder_2, "default"):
        coder_2 = coder_2.default
    if experiment_id is not None and not isinstance(experiment_id, str) and hasattr(experiment_id, "default"):
        experiment_id = experiment_id.default

    responses = read_json(RESPONSES_FILE)
    codings = read_json(CODING_FILE)

    # ---------------------------------------------------------
    # Filter responses by experiment
    # ---------------------------------------------------------
    if experiment_id:
        responses = [
            r
            for r in responses
            if r.get("experiment_id") == experiment_id
        ]

    response_lookup = {
        r.get("id"): r
        for r in responses
        if r.get("id")
    }

    # ---------------------------------------------------------
    # Build deduplicated coding lookup: response_id -> coder_id -> coding
    # Prevents repeated database records from being treated as multiple observations
    # ---------------------------------------------------------
    coding_lookup: dict[str, dict[str, dict]] = {}

    for coding in codings:
        response_id = coding.get("response_id")
        c_id = coding.get("coder_id")

        if not response_id or not c_id:
            continue

        if response_id not in response_lookup:
            continue

        if response_id not in coding_lookup:
            coding_lookup[response_id] = {}

        existing = coding_lookup[response_id].get(c_id)
        if existing is None or coding.get("coded_at", "") >= existing.get("coded_at", ""):
            coding_lookup[response_id][c_id] = coding

    # ---------------------------------------------------------
    # Identify responses coded by BOTH coders
    # Matched by stable response_id in deterministic sorted order
    # ---------------------------------------------------------
    shared_response_ids = sorted([
        resp_id
        for resp_id, coder_data in coding_lookup.items()
        if coder_1 in coder_data and coder_2 in coder_data
    ])
    total_shared_responses = len(shared_response_ids)

    # ---------------------------------------------------------
    # Helper to extract eligible paired scores independently per dimension
    # ---------------------------------------------------------
    def _extract_pairs_for_dimension(dim_key: str) -> list[tuple[float, float]]:
        pairs: list[tuple[float, float]] = []
        for resp_id in shared_response_ids:
            c1_entry = coding_lookup[resp_id][coder_1]
            c2_entry = coding_lookup[resp_id][coder_2]

            val_1 = c1_entry.get(dim_key)
            val_2 = c2_entry.get(dim_key)

            if is_valid_score(val_1) and is_valid_score(val_2):
                pairs.append((float(val_1), float(val_2)))
        return pairs

    t_pairs = _extract_pairs_for_dimension("truth")
    i_pairs = _extract_pairs_for_dimension("indeterminacy")
    f_pairs = _extract_pairs_for_dimension("falsity")

    # ---------------------------------------------------------
    # Calculate agreement independently for T, I, and F
    # ---------------------------------------------------------
    truth = _calculate_dimension_agreement(t_pairs, "truth", threshold=0.75)
    indeterminacy = _calculate_dimension_agreement(i_pairs, "indeterminacy", threshold=0.75)
    falsity = _calculate_dimension_agreement(f_pairs, "falsity", threshold=0.75)

    # ---------------------------------------------------------
    # Preregistered Reliability Gate: ICC(T) >= 0.75
    # Evaluated on unrounded ICC(T) value
    # ---------------------------------------------------------
    gate_evaluable = truth["evaluable"]
    if not gate_evaluable:
        gate_status = "unevaluable"
        gate_passed = False
        gate_message = (
            f"ICC(T) is unavailable ({truth['unavailable_reason'] or 'insufficient data'}); "
            "reliability gate cannot be evaluated."
        )
    elif truth["unrounded_icc"] >= 0.75:
        gate_status = "passed"
        gate_passed = True
        gate_message = (
            f"ICC(T) ({truth['icc']:.4f}) meets the preregistered threshold (>= 0.75); "
            "reliability gate passed for inferential analysis."
        )
    else:
        gate_status = "not_passed"
        gate_passed = False
        gate_message = (
            f"ICC(T) ({truth['icc']:.4f}) is below the preregistered threshold of 0.75; "
            "reliability gate not passed for inferential analysis."
        )

    reliability_gate = {
        "dimension": "T",
        "threshold": 0.75,
        "passed": gate_passed,
        "evaluable": gate_evaluable,
        "status": gate_status,
        "icc": truth["icc"],
        "unrounded_icc": truth["unrounded_icc"],
        "message": gate_message,
    }

    # ---------------------------------------------------------
    # Overall reference ICC across shared responses
    # Kept for backward compatibility
    # ---------------------------------------------------------
    overall_pairs = []
    for resp_id in shared_response_ids:
        c1_entry = coding_lookup[resp_id][coder_1]
        c2_entry = coding_lookup[resp_id][coder_2]

        t1, i1, f1 = c1_entry.get("truth"), c1_entry.get("indeterminacy"), c1_entry.get("falsity")
        t2, i2, f2 = c2_entry.get("truth"), c2_entry.get("indeterminacy"), c2_entry.get("falsity")

        if (
            is_valid_score(t1) and is_valid_score(i1) and is_valid_score(f1) and
            is_valid_score(t2) and is_valid_score(i2) and is_valid_score(f2)
        ):
            c1_mean = (float(t1) + float(i1) + float(f1)) / 3.0
            c2_mean = (float(t2) + float(i2) + float(f2)) / 3.0
            overall_pairs.append([c1_mean, c2_mean])

    overall_icc = None
    if len(overall_pairs) >= 2:
        overall_icc, _, _ = compute_icc_2_1(overall_pairs)

    return {
        "experiment_id": experiment_id,
        "coder_1": coder_1,
        "coder_2": coder_2,
        "total_shared_responses": total_shared_responses,
        "dimensions": {
            "T": {
                **truth,
                "label": "Stereotype / Gender-based Disadvantage",
            },
            "I": {
                **indeterminacy,
                "label": "Ambiguity / Context-dependent Interpretation",
            },
            "F": {
                **falsity,
                "label": "Neutral / Counter-stereotypical Content",
            },
        },
        "reliability_gate": reliability_gate,
        "overall": {
            "icc": overall_icc,
            "interpretation": _agreement_interpretation(overall_icc),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/summary")
def get_summary(
    experiment_id: Optional[str] = Query(None)
):
    """
    Get analysis summary.

    If experiment_id is not provided,
    aggregate across all experiments.
    """

    return _compute_metrics(experiment_id)


@router.get("/by-experiment/{experiment_id}")
def get_experiment_analysis(experiment_id: str):
    """Get analysis metrics for a specific experiment."""

    return _compute_metrics(experiment_id)


@router.get("/all-experiments")
def get_all_experiments_analysis():
    """Get per-experiment analysis."""

    responses = read_json(RESPONSES_FILE)

    experiment_ids = sorted(
        set(
            r.get("experiment_id")
            for r in responses
            if r.get("experiment_id")
        )
    )

    results = []

    for experiment_id in experiment_ids:

        metrics = _compute_metrics(experiment_id)

        if metrics["total_coded"] > 0:
            results.append(metrics)

    return results