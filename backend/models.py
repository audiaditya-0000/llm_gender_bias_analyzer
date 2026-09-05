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