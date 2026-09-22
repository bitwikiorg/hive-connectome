from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from hive_connectome.schemas import EventEnvelope, TaskResult


class EvalCase(BaseModel):
    id: str
    event: EventEnvelope
    expected_answer: Any = None
    expected_route: str | None = None
    expected_meaningful: float | None = Field(default=None, ge=0, le=1)
    scorer: Literal["auto", "exact", "route"] = "auto"


class ToggleCase(BaseModel):
    """Legacy 2x2 JEV/LLM ablation surface."""

    id: str
    jev: bool
    llm: bool


DEFAULT_TOGGLES = [
    ToggleCase(id="jev_off_llm_off", jev=False, llm=False),
    ToggleCase(id="jev_on_llm_off", jev=True, llm=False),
    ToggleCase(id="jev_off_llm_on", jev=False, llm=True),
    ToggleCase(id="jev_on_llm_on", jev=True, llm=True),
]


class ArchitectureVariant(BaseModel):
    """One frozen composition condition in a matched experiment."""

    id: str
    jev: bool = False
    llm: bool = False
    architecture: list[str] | None = None
    harness_passes: int | None = Field(default=None, ge=1, le=8)
    feedback_enabled: bool | None = None


DEFAULT_VARIANTS = [
    ArchitectureVariant(id=item.id, jev=item.jev, llm=item.llm)
    for item in DEFAULT_TOGGLES
]


class EvalRequest(BaseModel):
    worker_id: str
    cases: list[EvalCase]
    variants: list[ArchitectureVariant] | None = None
    # Kept for compatibility with the existing GUI/API. New experiments should
    # use variants so architecture, passes and feedback are explicit.
    toggles: list[ToggleCase] = Field(default_factory=lambda: list(DEFAULT_TOGGLES))
    reset_policy: Literal["reset_per_case", "reset_per_variant", "persistent_sequence"] = "reset_per_case"
    repetitions: int = Field(default=1, ge=1, le=100)
    condition_order_seed: int | None = 0
    scorer_version: str = "task-result-v1"

    def resolved_variants(self) -> list[ArchitectureVariant]:
        if self.variants is not None:
            return list(self.variants)
        return [
            ArchitectureVariant(id=item.id, jev=item.jev, llm=item.llm)
            for item in self.toggles
        ]


def canonical_task_set_hash(cases: list[EvalCase]) -> str:
    payload = [case.model_dump(mode="json") for case in cases]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def score_task_result(case: EvalCase, result: TaskResult, route: str | None) -> float | None:
    scorer = case.scorer
    if scorer == "auto":
        if case.expected_answer is not None:
            scorer = "exact"
        elif case.expected_route is not None:
            scorer = "route"
        else:
            return None

    if scorer == "route":
        if case.expected_route is None:
            return None
        return 1.0 if route == case.expected_route else 0.0

    if scorer == "exact":
        if case.expected_answer is None:
            return None
        return 1.0 if result.answer == case.expected_answer else 0.0

    return None


def summarize_eval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get("variant_id") or row.get("toggle_case") or "unknown"
        grouped.setdefault(key, []).append(row)

    summary: dict[str, Any] = {}
    for name, items in grouped.items():
        scored = [x for x in items if x.get("task_score") is not None]
        route_scored = [x for x in items if x.get("route_correct") is not None]
        summary[name] = {
            "cases": len(items),
            "task_score": (
                sum(float(x["task_score"]) for x in scored) / len(scored)
                if scored else None
            ),
            "route_accuracy": (
                sum(bool(x["route_correct"]) for x in route_scored) / len(route_scored)
                if route_scored else None
            ),
            "mean_latency_ms": sum(float(x["latency_ms"]) for x in items) / len(items),
            "llm_calls": sum(int(x.get("llm_calls", 1 if x.get("llm_called") else 0)) for x in items),
            "jev_calls": sum(int(x.get("jev_calls", 1 if x.get("jev_called") else 0)) for x in items),
            "neural_passes": sum(int(x.get("harness_passes") or 1) for x in items),
            "failures": sum(1 for x in items if x.get("error")),
        }
    return summary
