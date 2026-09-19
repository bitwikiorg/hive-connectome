from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

class BrainKind(StrEnum):
    WORM_LINK = "worm_link"
    FLY_CORE = "fly_core"
    LARVAL_MB = "larval_mb"
    SYNTHETIC = "synthetic"

class DecisionType(StrEnum):
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"

class EventEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=now_utc)
    source_id: str = "manual"
    kind: str = "observation"
    subject: str | None = None
    payload: Any
    provenance: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    freshness_timestamp: datetime | None = None

class NeuralObservation(BaseModel):
    brain_id: str
    brain_kind: BrainKind
    engine: str
    step: int
    state_vector: list[float]
    metrics: dict[str, float]

class JevQuestion(BaseModel):
    type: DecisionType
    instructions: str
    criteria: dict[str, str | None] | list[str] | None = None

class DecisionBundle(BaseModel):
    provider: str
    model: str
    answers: dict[str, Any]
    confidence: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

class LLMResult(BaseModel):
    provider: str
    model: str | None = None
    text: str
    raw: dict[str, Any] = Field(default_factory=dict)

class PipelineRequest(BaseModel):
    event: EventEnvelope
    mode: Literal["auto", "offline", "live"] = "auto"
    force_llm: bool = False

class PipelineResult(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    event: EventEnvelope
    worm: NeuralObservation
    fly: NeuralObservation
    decisions: DecisionBundle
    llm: LLMResult | None = None
    verification: DecisionBundle | None = None
    modulation: float
    labels: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

class BrainStageSpec(BaseModel):
    id: str
    kind: BrainKind
    engine: str
    enabled: bool = True
    state_size: int | None = Field(default=None, ge=1)
    connectome_pack: str | None = None
    input_from: list[str] = Field(default_factory=list)
    output_name: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

class BeeUnitSpec(BaseModel):
    id: str
    role: str
    brain_chain: list[BrainStageSpec]
    jev_head: list[str] = Field(default_factory=list)
    llm_policy: Literal["never", "rare", "escalate-on-uncertainty", "escalate-on-semantic-merge", "always"] = "escalate-on-uncertainty"
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=lambda: ["read"])

class HivemindSpec(BaseModel):
    name: str = "HIVE"
    shared_memory: str = "comb"
    bus: str = "waggle"
    bee_units: list[BeeUnitSpec]
    default_chain: list[str] = Field(default_factory=list)

class DataSourceSpec(BaseModel):
    id: str
    name: str
    kind: Literal["http_json", "rss", "file_drop"]
    url: str | None = None
    method: Literal["GET", "POST"] = "GET"
    body: Any | None = None
    path: str | None = None
    interval_seconds: int = Field(default=60, ge=5)
    enabled: bool = False
    auto_process: bool = True

    @model_validator(mode="after")
    def validate_target(self):
        if self.kind in {"http_json", "rss"} and not self.url:
            raise ValueError("network source requires url")
        if self.kind == "file_drop" and not self.path:
            raise ValueError("file_drop requires path")
        return self

class CronTaskSpec(BaseModel):
    id: str
    name: str
    cron: str
    action: Literal["emit_event", "poll_source"]
    target_id: str | None = None
    payload: Any | None = None
    enabled: bool = True

class SimulationSpec(BaseModel):
    name: str = "simulation"
    events: list[EventEnvelope]
    mode: Literal["offline", "live"] = "offline"
    reset_brains: bool = True

class ActionProposal(BaseModel):
    tool: str
    arguments: dict[str, Any]
    risk: Literal["read", "write", "financial", "destructive"] = "read"
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    requires_approval: bool = True
