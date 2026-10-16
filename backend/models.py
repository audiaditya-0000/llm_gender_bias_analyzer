from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


# ── Scenario ──────────────────────────────────────────────────────────────────

SCENARIO_CATEGORIES = [
    "Combat",
    "Dialogue",
    "Quest",
    "Exploration",
    "Trading",
    "Social Interaction",
    "Puzzle",
    "Tutorial",
    "General",
    "Other",
]


class ScenarioCreate(BaseModel):
    title: str
    description: str
    scenario_text: str
    category: str
    category_other: Optional[str] = None


class Scenario(BaseModel):
    id: str = Field(default_factory=generate_id)
    title: str
    description: str
    scenario_text: str
    category: str
    category_other: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ── Scaffold ──────────────────────────────────────────────────────────────────

class ScaffoldCreate(BaseModel):
    name: str
    prompt: str
    version: str
    notes: Optional[str] = ""


class Scaffold(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    prompt: str
    version: str
    notes: Optional[str] = ""
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ── Counterfactual ────────────────────────────────────────────────────────────

class CounterfactualRequest(BaseModel):
    prompt: str


class CounterfactualResponse(BaseModel):
    male_prompt: str
    female_prompt: str
    swaps_made: list[dict]


# ── Experiment ────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    scenario_id: str
    scaffold_id: str
    model: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    seed: Optional[int] = None
    num_replicates: int = 20
    swap_type: Optional[str] = "npc"


class Experiment(BaseModel):
    id: str = Field(default_factory=generate_id)
    scenario_id: str
    scaffold_id: str
    model: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    seed: Optional[int] = None
    num_replicates: int = 20
    swap_type: Optional[str] = "npc"
    status: str = "configured"  # configured, running, completed, failed
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ── Response ──────────────────────────────────────────────────────────────────

class ExperimentResponse(BaseModel):
    id: str = Field(default_factory=generate_id)
    pair_id: str = Field(default_factory=generate_id)
    experiment_id: str
    scenario_id: str
    scaffold_id: str
    scaffold_version: str
    model: str
    temperature: float
    seed: Optional[int] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    condition: str  # "original", "swapped"
    replicate_number: int
    scaffold_prompt: str = ""
    scenario_prompt: str = ""
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    generated_response: str

    @model_validator(mode="before")
    @classmethod
    def populate_prompt_aliases(cls, data):
        if isinstance(data, dict):
            if "scaffold_prompt" not in data and "system_prompt" in data:
                data["scaffold_prompt"] = data["system_prompt"]
            if "scenario_prompt" not in data and "user_prompt" in data:
                data["scenario_prompt"] = data["user_prompt"]
            if "system_prompt" not in data and "scaffold_prompt" in data:
                data["system_prompt"] = data["scaffold_prompt"]
            if "user_prompt" not in data and "scenario_prompt" in data:
                data["user_prompt"] = data["scenario_prompt"]
        return data


# ── Coding ────────────────────────────────────────────────────────────────────

class CodingCreate(BaseModel):
    response_id: str
    coder_id: str
    truth: float = Field(ge=0.0, le=1.0)
    indeterminacy: float = Field(ge=0.0, le=1.0)
    falsity: float = Field(ge=0.0, le=1.0)
    reasoning_notes: Optional[str] = ""


class Coding(BaseModel):
    id: str = Field(default_factory=generate_id)
    response_id: str
    coder_id: str
    truth: float = Field(ge=0.0, le=1.0)
    indeterminacy: float = Field(ge=0.0, le=1.0)
    falsity: float = Field(ge=0.0, le=1.0)
    reasoning_notes: Optional[str] = ""
    coded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Custom Word Pair ──────────────────────────────────────────────────────────

class WordPairCreate(BaseModel):
    male_term: str
    female_term: str

class WordPair(BaseModel):
    id: str = Field(default_factory=generate_id)
    male_term: str
    female_term: str


# ── Inferential Analysis Schemas ──────────────────────────────────────────────

class CellSummary(BaseModel):
    scenario_id: str
    scenario_title: str
    scaffold_id: str
    scaffold_name: str
    model: str
    total_responses: int
    n_female: int
    n_male: int
    mean_female_T: Optional[float] = None
    mean_male_T: Optional[float] = None
    signed_difference: Optional[float] = None
    is_eligible: bool
    is_empty: bool


class CoverageSummary(BaseModel):
    planned_cells_total: int
    planned_cells_per_model: int
    represented_combinations_total: int
    empty_combinations_count: int
    unpaired_combinations_count: int
    eligible_paired_cells_total: int
    eligible_cells_llama: int
    eligible_cells_mistral: int
    absent_scenarios_count: int
    limitation_disclosure: str


class DescriptiveEstimand(BaseModel):
    mean_signed_diff: Optional[float] = None
    signed_ci_lower: Optional[float] = None
    signed_ci_upper: Optional[float] = None
    mean_abs_diff: Optional[float] = None
    abs_ci_lower: Optional[float] = None
    abs_ci_upper: Optional[float] = None
    iterations: int
    seed: int
    caveat: str


class WilcoxonTestResult(BaseModel):
    test_name: str = "Two-sided paired Wilcoxon signed-rank test"
    evaluable: bool
    reason: Optional[str] = None
    n_cells: int
    n_nonzero: int
    W_positive: Optional[float] = None
    W_negative: Optional[float] = None
    test_statistic: Optional[float] = None
    p_raw: Optional[float] = None
    p_adjusted: Optional[float] = None
    alpha_adjusted: float = 0.025
    significant: bool
    method: str = "exact_sign_enumeration_with_zero_removal"
    rank_biserial: Optional[float] = None
    permutations_evaluated: Optional[int] = None


class CohensDzResult(BaseModel):
    d_z: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    evaluable: bool
    reason: Optional[str] = None
    method: Optional[str] = None
    degrees_of_freedom: Optional[int] = None
    t_observed: Optional[float] = None


class EffectSizeSummary(BaseModel):
    rank_biserial: Optional[float] = None
    rank_biserial_sign_convention: str
    cohens_dz: CohensDzResult


class NormalityDiagnosticResult(BaseModel):
    status: str
    W: Optional[float] = None
    p_value: Optional[float] = None
    reason: str


class SupportingParametricResult(BaseModel):
    status: str
    t_statistic: Optional[float] = None
    df: Optional[int] = None
    p_value: Optional[float] = None
    reason: str


class ModelInferenceSummary(BaseModel):
    model: str
    eligible_cell_count: int
    cell_differences: list[float]
    cells: list[CellSummary]
    primary_test: WilcoxonTestResult
    effect_sizes: EffectSizeSummary
    descriptives: DescriptiveEstimand
    normality_diagnostic: NormalityDiagnosticResult
    supporting_parametric_test: SupportingParametricResult


class InferentialAnalysisResponse(BaseModel):
    coverage: CoverageSummary
    reliability_gate: dict
    gate_warning: Optional[str] = None
    overall_descriptives: DescriptiveEstimand
    models: dict[str, ModelInferenceSummary]
    represented_combinations: list[CellSummary]