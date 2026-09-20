from __future__ import annotations

from typing import Any

from hive_connectome.workers import WorkerSpec


_STAGE_NAMES = {
    "worm_link": "C. elegans",
    "fly_core": "MaleCNS",
    "larval_mb": "Larval mushroom body",
    "synthetic": "Synthetic neural stage",
}

_ENGINE_LABELS = {
    "cook2019_connectome": "Cook full C. elegans",
    "malecns_full_v1": "Full MaleCNS v1.0",
    "malecns_locomotor": "MaleCNS locomotor control",
    "synthetic": "Synthetic recurrent network",
}

_BRIDGE_LABELS = {
    "state_projection_v1": "Neural state projection",
    "hash_projection_v1": "Hash projection control",
    "identity_payload_v1": "Payload handoff",
}


def build_experiment_plan(
    worker: WorkerSpec,
    *,
    connectomes: list[dict[str, Any]],
    runtime_status: dict[str, Any],
    provider_config: dict[str, Any],
) -> dict[str, Any]:
    packs = {item.get("id"): item for item in connectomes}
    stages: list[dict[str, Any]] = []

    for stage in worker.brain_chain:
        pack_id = stage.config.get("pack_id") or stage.connectome_pack
        pack = packs.get(pack_id, {}) if pack_id else {}
        role = "experimental"
        if stage.engine == "malecns_locomotor":
            role = "control"
        elif stage.engine in {"cook2019_connectome", "malecns_full_v1"}:
            role = "primary"
        details: list[str] = []
        expected_neurons = stage.config.get("expected_neurons") or stage.state_size
        expected_edges = stage.config.get("expected_directed_connections")
        expected_synapses = stage.config.get("expected_synapses")
        if expected_neurons:
            details.append(f"{int(expected_neurons):,} neurons/state units")
        if expected_edges:
            details.append(f"{int(expected_edges):,} directed connections")
        if expected_synapses:
            details.append(f"{int(expected_synapses):,} synaptic contacts")

        stages.append({
            "id": stage.id,
            "name": _STAGE_NAMES.get(stage.kind.value, stage.id),
            "kind": stage.kind.value,
            "engine": stage.engine,
            "engine_label": _ENGINE_LABELS.get(stage.engine, stage.engine),
            "enabled": stage.enabled,
            "input_from": list(stage.input_from),
            "pack_id": pack_id,
            "dataset_name": pack.get("name"),
            "dataset_installed": bool(pack.get("installed")) if pack_id else True,
            "role": role,
            "details": details,
            "config": stage.config,
        })

    bridges = [{
        "id": bridge.id,
        "source": bridge.source,
        "target": bridge.target,
        "engine": bridge.engine,
        "label": _BRIDGE_LABELS.get(bridge.engine, bridge.engine),
        "enabled": bridge.enabled,
        "config": bridge.config,
    } for bridge in worker.bridges]

    venice_ready = bool(provider_config.get("venice_api_key_configured"))
    llm_provider = worker.llm.provider
    llm_configured = venice_ready if llm_provider == "venice" else bool(provider_config.get("lmstudio_base_url"))

    active_stage_ids = {item["id"] for item in stages if item["enabled"]}
    sequence: list[dict[str, Any]] = [{"type": "input", "label": "Input"}]
    for stage in stages:
        if stage["enabled"]:
            sequence.append({"type": "neural", "id": stage["id"], "label": stage["name"], "engine": stage["engine_label"]})
    if worker.jev.enabled:
        sequence.append({"type": "jev", "label": "JEV", "provider": "Venice", "model": worker.jev.model})
    if worker.llm.enabled:
        sequence.append({"type": "llm", "label": "LLM", "provider": worker.llm.provider, "model": worker.llm.model})
    sequence.append({"type": "output", "label": "Recorded result"})

    warnings: list[str] = []
    for stage in stages:
        if stage["enabled"] and stage["pack_id"] and not stage["dataset_installed"]:
            warnings.append(f"{stage['name']} is enabled but its dataset is not installed.")
    for bridge in bridges:
        if bridge["enabled"] and (bridge["source"] not in active_stage_ids or bridge["target"] not in active_stage_ids):
            warnings.append(f"Bridge {bridge['source']} → {bridge['target']} is configured but one endpoint is disabled.")
    if worker.jev.enabled and not venice_ready:
        warnings.append("JEV is enabled but the Venice API key is not configured.")
    if worker.llm.enabled and not worker.llm.model and not provider_config.get("default_llm_model"):
        warnings.append("LLM is enabled but no model is selected.")
    if worker.llm.enabled and not llm_configured:
        warnings.append(f"LLM provider {worker.llm.provider} is enabled but not configured.")

    is_primary = any(s["enabled"] and s["engine"] == "cook2019_connectome" for s in stages) and any(
        s["enabled"] and s["engine"] == "malecns_full_v1" for s in stages
    )
    primary_ready = bool(runtime_status.get("primary_experiment_ready"))

    return {
        "core_id": worker.id,
        "name": worker.name,
        "description": worker.description,
        "objective": worker.experiment.objective,
        "task_prompt": worker.experiment.task_prompt,
        "stages": stages,
        "bridges": bridges,
        "jev": {
            "enabled": worker.jev.enabled,
            "provider": worker.jev.provider,
            "model": worker.jev.model,
            "configured": venice_ready,
            "feedback_to_brain": worker.jev.feedback_to_brain,
            "feedback_targets": list(worker.jev.feedback_targets),
        },
        "llm": {
            "enabled": worker.llm.enabled,
            "provider": worker.llm.provider,
            "model": worker.llm.model or provider_config.get("default_llm_model"),
            "activation": worker.llm.activation,
            "configured": llm_configured,
            "verify_with_jev": worker.llm.verify_with_jev,
        },
        "recording": worker.outputs.recording_level,
        "persist_state": worker.runtime.persist_brain_state,
        "sequence": sequence,
        "warnings": warnings,
        "is_primary_topology": is_primary,
        "primary_experiment_ready": primary_ready,
        "primary_blockers": runtime_status.get("primary", {}).get("blockers", []) if is_primary else [],
    }
