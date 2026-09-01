"""
Analysis routes.

Computes SVNS gender-bias metrics from coded responses:

T = Stereotype / Gender-based Disadvantage
I = Ambiguity / Context-dependent or Contested Interpretation
F = Neutral / Counter-stereotypical Content

Bias Score = |Average T (male condition) - Average T (female condition)|

Also provides inter-rater agreement analysis for multiple coders.
"""

from fastapi import APIRouter, Query
from typing import Optional

from storage import read_json


router = APIRouter(prefix="/api/analysis", tags=["analysis"])

RESPONSES_FILE = "responses.json"
CODING_FILE = "coding.json"


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

    coding_lookup: dict[str, list[dict]] = {}

    for coding in codings:
        response_id = coding.get("response_id")

        if not response_id:
            continue

        if response_id not in coding_lookup:
            coding_lookup[response_id] = []

        coding_lookup[response_id].append(coding)

    # ---------------------------------------------------------
    # Separate male and female conditions
    # ---------------------------------------------------------

    male_codings = []
    female_codings = []

    for response in responses:

        response_id = response.get("id")
        response_codings = coding_lookup.get(response_id, [])

        if not response_codings:
            continue

        condition = response.get("condition", "").lower().strip()

        # Average all available coder ratings for this response

        n_coders = len(response_codings)

        avg_truth = sum(
    float(c.get("truth", 0))
    for c in response_codings
    ) / n_coders

        avg_indeterminacy = sum(
    float(c.get("indeterminacy", 0))
    for c in response_codings
    ) / n_coders

        avg_falsity = sum(
    float(c.get("falsity", 0))
    for c in response_codings
    ) / n_coders

        entry = {
            "truth": avg_truth,
            "indeterminacy": avg_indeterminacy,
            "falsity": avg_falsity,
            "response_id": response_id,
            "condition": condition,
            "coder_count": n_coders,
        }

        if condition.startswith("male_"):
            male_codings.append(entry)

        elif condition.startswith("female_"):
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

        response_codings = coding_lookup.get(
        response_id,
        []
        )

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


def _calculate_icc_2_1(values: list[list[float]]) -> Optional[float]:
    """
    Calculate ICC(2,1):

    Two-way random effects model,
    absolute agreement,
    single measurement.

    Expected input:

        [
            [coder1_response1, coder2_response1],
            [coder1_response2, coder2_response2],
            ...
        ]

    Returns None when ICC cannot be calculated.
    """

    n = len(values)

    if n < 2:
        return None

    k = len(values[0])

    if k < 2:
        return None

    # ---------------------------------------------------------
    # Grand mean
    # ---------------------------------------------------------

    all_values = [
        value
        for row in values
        for value in row
    ]

    grand_mean = sum(all_values) / len(all_values)

    # ---------------------------------------------------------
    # Row means
    # Each row = one response
    # ---------------------------------------------------------

    row_means = [
        sum(row) / k
        for row in values
    ]

    # ---------------------------------------------------------
    # Column means
    # Each column = one coder
    # ---------------------------------------------------------

    column_means = [
        sum(values[i][j] for i in range(n)) / n
        for j in range(k)
    ]

    # ---------------------------------------------------------
    # Mean square for rows
    # ---------------------------------------------------------

    ms_rows = (
        k
        * sum(
            (row_mean - grand_mean) ** 2
            for row_mean in row_means
        )
        / (n - 1)
    )

    # ---------------------------------------------------------
    # Mean square for columns
    # ---------------------------------------------------------

    ms_columns = (
        n
        * sum(
            (column_mean - grand_mean) ** 2
            for column_mean in column_means
        )
        / (k - 1)
    )

    # ---------------------------------------------------------
    # Residual/error mean square
    # ---------------------------------------------------------

    ss_error = 0

    for i in range(n):
        for j in range(k):
            ss_error += (
                values[i][j]
                - row_means[i]
                - column_means[j]
                + grand_mean
            ) ** 2

    ms_error = ss_error / ((n - 1) * (k - 1))

    # ---------------------------------------------------------
    # ICC(2,1)
    #
    # Absolute agreement
    # ---------------------------------------------------------

    denominator = (
        ms_rows
        + (k - 1) * ms_error
        + (k * (ms_columns - ms_error) / n)
    )

    if denominator == 0:
        return None

    icc = (
        ms_rows - ms_error
    ) / denominator

    return round(icc, 4)


def _mean_absolute_difference(
    coder_1_values: list[float],
    coder_2_values: list[float],
) -> Optional[float]:

    if not coder_1_values or not coder_2_values:
        return None

    if len(coder_1_values) != len(coder_2_values):
        return None

    differences = [
        abs(a - b)
        for a, b in zip(
            coder_1_values,
            coder_2_values
        )
    ]

    return round(
        sum(differences) / len(differences),
        4,
    )


def _agreement_interpretation(icc: Optional[float]) -> str:
    """
    Simple interpretation of ICC.

    These are intended as practical reporting categories,
    not absolute scientific thresholds.
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
    shared_pairs: list[dict],
    dimension: str,
) -> dict:
    """Calculate agreement for one SVNS dimension."""

    coder_1_values = [
        pair["coder_1"][dimension]
        for pair in shared_pairs
    ]

    coder_2_values = [
        pair["coder_2"][dimension]
        for pair in shared_pairs
    ]

    matrix = [
        [coder_1_values[i], coder_2_values[i]]
        for i in range(len(shared_pairs))
    ]

    icc = _calculate_icc_2_1(matrix)

    mad = _mean_absolute_difference(
        coder_1_values,
        coder_2_values,
    )

    return {
        "icc": icc,
        "interpretation": _agreement_interpretation(icc),
        "mean_absolute_difference": mad,
        "n": len(shared_pairs),
    }


@router.get("/inter-rater")
def get_inter_rater_agreement(
    experiment_id: Optional[str] = Query(None),
    coder_1: str = Query("coder_1"),
    coder_2: str = Query("coder_2"),
):
    """
    Calculate inter-rater agreement between two coders.

    Only responses coded by BOTH coders are included.

    Agreement is calculated independently for:

        T = Truth
        I = Indeterminacy
        F = Falsity

    ICC(2,1) is used because the ratings are continuous
    values between 0 and 1.
    """

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
    # Build coding lookup
    #
    # response_id -> coder_id -> coding
    # ---------------------------------------------------------

    coding_lookup: dict[str, dict[str, dict]] = {}

    for coding in codings:

        response_id = coding.get("response_id")
        coder_id = coding.get("coder_id")

        if not response_id or not coder_id:
            continue

        if response_id not in response_lookup:
            continue

        if response_id not in coding_lookup:
            coding_lookup[response_id] = {}

        coding_lookup[response_id][coder_id] = coding

    # ---------------------------------------------------------
    # Find responses coded by BOTH coders
    # ---------------------------------------------------------

    shared_pairs = []

    for response_id, coder_data in coding_lookup.items():

        if (
            coder_1 not in coder_data
            or coder_2 not in coder_data
        ):
            continue

        coding_1 = coder_data[coder_1]
        coding_2 = coder_data[coder_2]

        shared_pairs.append(
            {
                "response_id": response_id,

                "coder_1": {
                    "truth": float(
                        coding_1.get("truth", 0)
                    ),
                    "indeterminacy": float(
                        coding_1.get("indeterminacy", 0)
                    ),
                    "falsity": float(
                        coding_1.get("falsity", 0)
                    ),
                },

                "coder_2": {
                    "truth": float(
                        coding_2.get("truth", 0)
                    ),
                    "indeterminacy": float(
                        coding_2.get("indeterminacy", 0)
                    ),
                    "falsity": float(
                        coding_2.get("falsity", 0)
                    ),
                },
            }
        )

    # ---------------------------------------------------------
    # Calculate agreement
    # ---------------------------------------------------------

    truth = _calculate_dimension_agreement(
        shared_pairs,
        "truth",
    )

    indeterminacy = _calculate_dimension_agreement(
        shared_pairs,
        "indeterminacy",
    )

    falsity = _calculate_dimension_agreement(
        shared_pairs,
        "falsity",
    )

    # ---------------------------------------------------------
    # Overall ICC
    #
    # Overall reliability is only meaningful when there are
    # at least 2 shared responses.
    #
    # IMPORTANT:
    # Do not treat T/I/F dimensions from the same response
    # as separate responses. One response = one observation.
    # ---------------------------------------------------------

    overall_icc = None

    if len(shared_pairs) >= 2:

        # Average the three SVNS dimensions for each response
        # for each coder.
        #
        # Each row represents ONE shared response.
        overall_values = []

        for pair in shared_pairs:

            coder_1_overall = (
            pair["coder_1"]["truth"]
            + pair["coder_1"]["indeterminacy"]
            + pair["coder_1"]["falsity"]
            ) / 3

            coder_2_overall = (
            pair["coder_2"]["truth"]
            + pair["coder_2"]["indeterminacy"]
            + pair["coder_2"]["falsity"]
            ) / 3

            overall_values.append(
                [
                    coder_1_overall,
                    coder_2_overall,
                ]
            )

        overall_icc = _calculate_icc_2_1(
        overall_values
        )

    # ---------------------------------------------------------
    # Final response
    # ---------------------------------------------------------

    return {
        "experiment_id": experiment_id,

        "coder_1": coder_1,

        "coder_2": coder_2,

        "total_shared_responses": len(shared_pairs),

        "dimensions": {
            "T": {
                **truth,
                "label": (
                    "Stereotype / "
                    "Gender-based Disadvantage"
                ),
            },

            "I": {
                **indeterminacy,
                "label": (
                    "Ambiguity / "
                    "Context-dependent Interpretation"
                ),
            },

            "F": {
                **falsity,
                "label": (
                    "Neutral / "
                    "Counter-stereotypical Content"
                ),
            },
        },

        "overall": {
            "icc": overall_icc,
            "interpretation": (
                _agreement_interpretation(
                    overall_icc
                )
            ),
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