from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict, Any


class OutcomeEffect(BaseModel):
    name: str
    effect_metric: Literal["MD", "SMD", "OR", "RR", "HR", "logOR", "logRR", "logHR"] = (
        "logRR"
    )
    effect: float  # log effect if log scale, otherwise raw
    var: float  # variance of effect (SE^2)


class StudyRecord(BaseModel):
    study_id: str
    design: Optional[str] = None
    n_total: Optional[int] = None
    outcomes: List[OutcomeEffect] = Field(default_factory=list)


class SearchDescriptor(BaseModel):
    db: str
    platform: Optional[str] = None
    dates: Optional[str] = None
    strategy: Optional[str] = None
    limits: List[str] = Field(default_factory=list)


class ExclusionReason(BaseModel):
    reason: str
    n: int


class FlowCounts(BaseModel):
    identified: Optional[int] = None
    deduplicated: Optional[int] = None
    screened: Optional[int] = None
    fulltext: Optional[int] = None
    included: Optional[int] = None
    excluded: Optional[List[ExclusionReason]] = None


class PICO(BaseModel):
    framework: Literal["PICO", "PECO", "PS", "Other"] = "PICO"
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcomes: List[str] = Field(default_factory=list)


class Manuscript(BaseModel):
    manuscript_id: str
    title: Optional[str] = None
    journal: Optional[str] = None
    submission_date: Optional[str] = None
    question: Optional[PICO] = None
    protocol: Optional[Dict[str, Any]] = None
    search: List[SearchDescriptor] = Field(default_factory=list)
    flow: Optional[FlowCounts] = None
    included_studies: List[StudyRecord] = Field(default_factory=list)


class Issue(BaseModel):
    id: str
    severity: Literal["low", "medium", "high"]
    category: Literal["PICO", "PRISMA", "STATS", "DATA", "OTHER"]
    item: str
    evidence: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None
    agent: Optional[str] = None


class MetaResult(BaseModel):
    outcome: str
    k: int
    model: Literal["fixed", "random"]
    pooled: float
    se: float
    ci_low: float
    ci_high: float
    Q: Optional[float] = None
    I2: Optional[float] = None
    tau2: Optional[float] = None
    evidence: Optional[Dict[str, Any]] = None


class AnalysisMethod(BaseModel):
    """Information about the analysis method used by an agent."""

    agent: str
    method: Literal["rule-based", "llm-enhanced", "hybrid"]
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    fallback_reason: Optional[str] = None


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis process and methods used."""

    analysis_methods: List[AnalysisMethod]
    llm_available: bool
    total_llm_calls: int = 0
    total_tokens_used: Optional[int] = None
    estimated_cost: Optional[float] = None


class StreamingEvent(BaseModel):
    """Event for streaming orchestrator progress to clients."""

    event_type: Literal[
        "agent_start", "agent_complete", "progress", "complete", "error"
    ]
    agent: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class ReviewResult(BaseModel):
    issues: List[Issue]
    meta: List[MetaResult]
    extraction_info: Optional[Dict[str, Any]] = None
    analysis_metadata: Optional[AnalysisMetadata] = None
