from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from hive_connectome.schemas import BrainKind, BrainStageSpec, BridgeSpec, JevQuestion


class BrainSpec(BaseModel):
    engine: str = "synthetic"
    enabled: bool = True
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
    feedback_to_brain: bool = True
    feedback_targets: list[str] = Field(default_factory=list)
    feedback_adapter: Literal["meaningful_novelty_v1"] = "meaningful_novelty_v1"


class LLMConfig(BaseModel):
    enabled: bool = False
    provider: Literal["lmstudio", "venice"] = "lmstudio"
    model: str | None = None
    prompt: str = ""
    temperature: float = Field(default=0.2, ge=0, le=2)
    verify_with_jev: bool = True
    feedback_to_brain: bool = True
    feedback_targets: list[str] = Field(default_factory=list)
    feedback_adapter: Literal["direct_scalar_v1"] = "direct_scalar_v1"


class RuntimeSpec(BaseModel):
    enabled: bool = False
    mode: Literal["on_demand", "daemon", "cron"] = "on_demand"
    interval_seconds: int = Field(default=60, ge=5)
    cron: str | None = None
    persist_brain_state: bool = True
    max_events_per_tick: int = Field(default=25, ge=1, le=1000)
    harness_passes: int = Field(
        default=2,
        ge=1,
        le=8,
        validation_alias=AliasChoices("harness_passes", "integration_cycles"),
        description="Number of complete architecture passes over the same input.",
    )

    @property
    def integration_cycles(self) -> int:
        """Backward-compatible attribute alias for pre-composition configs."""
        return self.harness_passes

    @integration_cycles.setter
    def integration_cycles(self, value: int) -> None:
        self.harness_passes = int(value)

    @property
    def resolved_harness_passes(self) -> int:
        return int(self.harness_passes)


class OutputSpec(BaseModel):
    save_event: bool = True
    save_run: bool = True
    write_labels: bool = True
    emit_to_hivemind: bool = False
    next_workers: list[str] = Field(default_factory=list)
    recording_level: Literal["summary", "trace", "full"] = "trace"


class WorkerSpec(BaseModel):
    id: str
    name: str
    description: str = ""
    role: str
    experiment: ExperimentSpec
    data_environment: DataEnvironmentSpec

    # Legacy v0.6 fields are retained as a migration surface. The executor uses
    # brain_chain + bridges. When brain_chain is omitted these two fields are
    # deterministically promoted into the generic graph.
    larva: BrainSpec | None = None
    bee: BrainSpec | None = None
    brain_chain: list[BrainStageSpec] = Field(default_factory=list)
    bridges: list[BridgeSpec] = Field(default_factory=list)
    architecture: list[str] = Field(
        default_factory=list,
        description="Ordered executable component tags. Accepts a comma-separated string on input.",
    )

    jev: JevConfig
    llm: LLMConfig
    runtime: RuntimeSpec = Field(default_factory=RuntimeSpec)
    outputs: OutputSpec = Field(default_factory=OutputSpec)

    @field_validator("architecture", mode="before")
    @classmethod
    def parse_architecture(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        return value

    @model_validator(mode="after")
    def migrate_legacy_pair(self):
        if not self.brain_chain:
            chain: list[BrainStageSpec] = []
            if self.larva is not None:
                chain.append(BrainStageSpec(
                    id="worm",
                    kind=BrainKind.WORM_LINK,
                    engine=self.larva.engine,
                    enabled=self.larva.enabled,
                    state_size=self.larva.state_size,
                    connectome_pack=self.larva.config.get("pack_id"),
                    input_from=[],
                    config={**self.larva.config, "substrate": self.larva.substrate},
                ))
            if self.bee is not None:
                upstream = ["worm"] if self.larva is not None and self.larva.enabled else []
                chain.append(BrainStageSpec(
                    id="fly",
                    kind=BrainKind.FLY_CORE,
                    engine=self.bee.engine,
                    enabled=self.bee.enabled,
                    state_size=self.bee.state_size,
                    connectome_pack=self.bee.config.get("pack_id"),
                    input_from=upstream,
                    config={**self.bee.config, "substrate": self.bee.substrate},
                ))
            self.brain_chain = chain

        known = {stage.id for stage in self.brain_chain}
        for owner, targets in (
            ("jev", self.jev.feedback_targets),
            ("llm", self.llm.feedback_targets),
        ):
            unknown_targets = [target for target in targets if target not in known]
            if unknown_targets:
                raise ValueError(
                    f"{owner} feedback targets reference unknown neural stages: {unknown_targets}"
                )

        for stage in self.brain_chain:
            missing = [source for source in stage.input_from if source not in known]
            if missing:
                raise ValueError(f"brain stage {stage.id} references unknown input stages: {missing}")
            if stage.id in stage.input_from:
                raise ValueError(f"brain stage {stage.id} cannot input from itself")

        if not self.bridges:
            for stage in self.brain_chain:
                for source in stage.input_from:
                    self.bridges.append(BridgeSpec(
                        id=f"{source}-to-{stage.id}",
                        source=source,
                        target=stage.id,
                        engine="whole_state_projection_v1",
                        config={"target_count": 24, "gain": 1.0},
                    ))

        for bridge in self.bridges:
            if bridge.source not in known or bridge.target not in known:
                raise ValueError(f"bridge {bridge.id} references unknown stage")
            # v0.7 generated this exact first-32 bridge implicitly. Upgrade it
            # to the whole-state projection unless a researcher explicitly
            # marks it as a legacy excerpt control.
            if (
                bridge.engine == "state_projection_v1"
                and int(bridge.config.get("source_excerpt", 32)) == 32
                and int(bridge.config.get("target_count", 24)) == 24
                and float(bridge.config.get("gain", 1.0)) == 1.0
                and not bool(bridge.config.get("preserve_legacy_excerpt"))
            ):
                bridge.engine = "whole_state_projection_v1"
                bridge.config.pop("source_excerpt", None)

        reserved = {"readout", "jev", "llm", "jev_verify", "feedback"}
        stage_ids = [stage.id for stage in self.brain_chain]
        bridge_ids = [bridge.id for bridge in self.bridges]
        collisions = reserved.intersection(stage_ids + bridge_ids)
        if collisions:
            raise ValueError(f"component IDs collide with reserved architecture tags: {sorted(collisions)}")
        duplicate_ids = {item for item in stage_ids + bridge_ids if (stage_ids + bridge_ids).count(item) > 1}
        if duplicate_ids:
            raise ValueError(f"component IDs must be unique across stages and bridges: {sorted(duplicate_ids)}")

        if not self.architecture:
            sequence: list[str] = []
            emitted_bridges: set[str] = set()
            for stage in self.brain_chain:
                for bridge in self.bridges:
                    if bridge.enabled and bridge.target == stage.id and bridge.id not in emitted_bridges:
                        sequence.append(bridge.id)
                        emitted_bridges.add(bridge.id)
                if stage.enabled:
                    sequence.append(stage.id)
            sequence.extend(["readout", "jev", "llm", "jev_verify", "feedback"])
            self.architecture = sequence

        valid_tags = set(stage_ids) | set(bridge_ids) | reserved
        unknown = [tag for tag in self.architecture if tag not in valid_tags]
        if unknown:
            raise ValueError(f"architecture contains unknown component tags: {unknown}")
        return self


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
