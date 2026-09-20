from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from hive_connectome.schemas import EventEnvelope


class EvalCase(BaseModel):
    id: str
    event: EventEnvelope
    expected_route: str | None = None
    expected_meaningful: float | None = Field(default=None, ge=0, le=1)


class ToggleCase(BaseModel):
    id: str
    jev: bool
    llm: bool


DEFAULT_TOGGLES = [
    ToggleCase(id="jev_off_llm_off", jev=False, llm=False),
    ToggleCase(id="jev_on_llm_off", jev=True, llm=False),
    ToggleCase(id="jev_off_llm_on", jev=False, llm=True),
    ToggleCase(id="jev_on_llm_on", jev=True, llm=True),
]


class EvalRequest(BaseModel):
    worker_id: str
    cases: list[EvalCase]
    toggles: list[ToggleCase] = Field(default_factory=lambda: list(DEFAULT_TOGGLES))


def summarize_eval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["toggle_case"], []).append(row)

    summary = {}
    for name, items in grouped.items():
        scored = [x for x in items if x["route_correct"] is not None]
        summary[name] = {
            "cases": len(items),
            "route_accuracy": (sum(bool(x["route_correct"]) for x in scored) / len(scored)) if scored else None,
            "mean_latency_ms": sum(x["latency_ms"] for x in items) / len(items),
            "llm_calls": sum(1 for x in items if x["llm_called"]),
            "jev_calls": sum(1 for x in items if x["jev_called"]),
            "failures": sum(1 for x in items if x.get("error")),
        }
    return summary
