from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator

from hive_connectome.schemas import JevQuestion


class BrainSpec(BaseModel):
    engine: str = "synthetic"
    state_size: int = Field(default=16, ge=2, le=1_000_000)
    substrate: str
    config: dict[str, Any] = Field(default_factory=dict)


class ExperimentSpec(BaseModel):
    kind: Literal[
        "manual",
        "stream_classifier",
        "browser_dom",
        "browser_visual",
        "local_files",
        "simulation",
        "hivemind_chain",
    ] = "manual"
    objective: str
    task_prompt: str
    expected_output: str = "structured labels and evidence"
    eval_metric: str = "task-specific"
    notes: str = ""


class DataEnvironmentSpec(BaseModel):
    mode: Literal[
        "manual",
        "source_ids",
        "browser_dom",
        "browser_visual",
        "file_drop",
        "simulation",
        "worker_output",
    ] = "manual"
    source_ids: list[str] = Field(default_factory=list)
    url: str | None = None
    file_path: str | None = None
    poll_interval_seconds: int = Field(default=60, ge=5)
    always_on: bool = False
    browser_extract: Literal["dom", "accessibility", "screenshot", "ocr", "mixed"] = "dom"
    ocr_enabled: bool = False
    upstream_workers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_environment(self):
        if self.mode in {"browser_dom", "browser_visual"} and not self.url:
            raise ValueError("browser environment requires a URL")
        if self.mode == "file_drop" and not self.file_path:
            raise ValueError("file_drop environment requires file_path")
        if self.mode == "worker_output" and not self.upstream_workers:
            raise ValueError("worker_output environment requires upstream_workers")
        return self


class JevConfig(BaseModel):
    enabled: bool = True
    provider: Literal["venice"] = "venice"
    model: str = "jev-latest"
    questions: dict[str, JevQuestion] = Field(default_factory=dict)
    llm_gate_threshold: float = Field(
        default=0.65,
        ge=0,
        le=1,
        validation_alias=AliasChoices("llm_gate_threshold", "confidence_threshold"),
    )
    feedback_to_brain: bool = True


class LLMConfig(BaseModel):
    enabled: bool = False
    provider: Literal["lmstudio", "venice"] = "lmstudio"
    model: str | None = None
    activation: Literal["always", "jev_gate", "manual"] = "jev_gate"
    prompt: str = ""
    temperature: float = Field(default=0.2, ge=0, le=2)
    verify_with_jev: bool = True


class RuntimeSpec(BaseModel):
    enabled: bool = False
    mode: Literal["on_demand", "daemon", "cron"] = "on_demand"
    interval_seconds: int = Field(default=60, ge=5)
    cron: str | None = None
    persist_brain_state: bool = True
    max_events_per_tick: int = Field(default=25, ge=1, le=1000)


class OutputSpec(BaseModel):
    save_event: bool = True
    save_run: bool = True
    write_labels: bool = True
    emit_to_hivemind: bool = False
    next_workers: list[str] = Field(default_factory=list)


class WorkerSpec(BaseModel):
    id: str
    name: str
    description: str = ""
    role: str
    experiment: ExperimentSpec
    data_environment: DataEnvironmentSpec
    larva: BrainSpec
    bee: BrainSpec
    jev: JevConfig
    llm: LLMConfig
    runtime: RuntimeSpec = Field(default_factory=RuntimeSpec)
    outputs: OutputSpec = Field(default_factory=OutputSpec)


class WorkerStore:
    def __init__(self, persistent_path: Path, defaults_path: Path):
        self.path = persistent_path
        self.defaults_path = defaults_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(self.defaults_path.read_text(encoding="utf-8"), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def list(self) -> list[WorkerSpec]:
        return [WorkerSpec.model_validate(x) for x in self._load()["workers"]]

    def get(self, worker_id: str) -> WorkerSpec:
        for worker in self.list():
            if worker.id == worker_id:
                return worker
        raise KeyError(worker_id)

    def save(self, worker: WorkerSpec) -> WorkerSpec:
        data = self._load()
        found = False
        for index, raw in enumerate(data["workers"]):
            if raw["id"] == worker.id:
                data["workers"][index] = worker.model_dump(mode="json")
                found = True
                break
        if not found:
            data["workers"].append(worker.model_dump(mode="json"))
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return worker

    def delete(self, worker_id: str) -> None:
        data = self._load()
        data["workers"] = [w for w in data["workers"] if w["id"] != worker_id]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)
