from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_experiment_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pack_file_status(data_dir: Path, pack_id: str, files: list[str]) -> dict[str, Any]:
    root = data_dir / "connectomes" / pack_id
    present = {name: (root / name).exists() for name in files}
    return {
        "pack_id": pack_id,
        "installed": all(present.values()) if files else root.exists(),
        "files": present,
    }


def _execution_status(data_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    engine = spec["engine"]
    pack_id = spec["pack_id"]
    path = data_dir / "execution_receipts" / f"{engine}--{pack_id}.json"
    status: dict[str, Any] = {
        "required": bool(spec.get("execution_required")),
        "executed": False,
        "receipt": str(path.relative_to(data_dir)),
    }
    if not path.exists():
        return status
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {**status, "error": f"invalid execution receipt: {exc}"}

    valid = (
        receipt.get("requested_engine") == engine
        and receipt.get("pack_id") == pack_id
        and int(receipt.get("step") or 0) >= 1
        and bool(receipt.get("metadata", {}).get("real_connectome_topology"))
    )
    if spec.get("scope") == "full_connectome":
        valid = valid and bool(receipt.get("full_connectome") or engine == "cook2019_connectome")
    expected = {
        "node_count": spec.get("expected_neurons"),
        "edge_count": spec.get("expected_directed_connections"),
        "synaptic_contacts": spec.get("expected_synapses"),
    }
    mismatches = {}
    for key, target in expected.items():
        if target is None:
            continue
        observed = receipt.get(key)
        if observed is None or int(observed) != int(target):
            mismatches[key] = {"expected": int(target), "observed": observed}
            valid = False
    status.update({
        "executed": valid,
        "observed": {
            "engine": receipt.get("observed_engine"),
            "node_count": receipt.get("node_count"),
            "edge_count": receipt.get("edge_count"),
            "synaptic_contacts": receipt.get("synaptic_contacts"),
            "state_hash": receipt.get("state_hash"),
        },
        "mismatches": mismatches,
    })
    return status



def _primary_end_to_end_status(data_dir: Path, contract: dict[str, Any]) -> dict[str, Any]:
    path = data_dir / "execution_receipts" / "primary--latest.json"
    status: dict[str, Any] = {
        "required": True,
        "executed": False,
        "receipt": str(path.relative_to(data_dir)),
    }
    if not path.exists():
        return status
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {**status, "error": f"invalid primary execution receipt: {exc}"}

    primary = contract["primary_pipeline"]
    larva = primary["larva"]
    bee = primary["bee"]
    stages = receipt.get("stages") or {}
    stage_items = [
        (stage_id, value)
        for stage_id, value in stages.items()
        if isinstance(value, dict)
    ]
    larva_item = next(
        ((stage_id, value) for stage_id, value in stage_items
         if value.get("requested_engine") == larva["engine"]),
        None,
    )
    bee_item = next(
        ((stage_id, value) for stage_id, value in stage_items
         if value.get("requested_engine") == bee["engine"]),
        None,
    )

    valid = bool(receipt.get("end_to_end")) and larva_item is not None and bee_item is not None
    mismatches: dict[str, Any] = {}

    if bee_item is not None:
        bee_meta = bee_item[1].get("metadata") or {}
        expected = {
            "node_count": bee.get("expected_neurons"),
            "edge_count": bee.get("expected_directed_connections"),
            "synaptic_contacts": bee.get("expected_synapses"),
        }
        for key, target in expected.items():
            if target is None:
                continue
            observed = bee_meta.get(key)
            if observed is None or int(observed) != int(target):
                mismatches[f"bee.{key}"] = {
                    "expected": int(target),
                    "observed": observed,
                }
                valid = False
        if not bool(bee_meta.get("full_connectome")):
            mismatches["bee.full_connectome"] = {
                "expected": True,
                "observed": bee_meta.get("full_connectome"),
            }
            valid = False

    matching_bridge = None
    canonical_bridge_engine = (
        primary.get("bridge", {}).get("engine")
        or "whole_state_projection_v1"
    )
    if larva_item is not None and bee_item is not None:
        larva_id, bee_id = larva_item[0], bee_item[0]
        for bridge in receipt.get("bridges") or []:
            if (
                bridge.get("source") == larva_id
                and bridge.get("target") == bee_id
                and bridge.get("engine") == canonical_bridge_engine
                and int(bridge.get("source_values_used") or 0) > 0
            ):
                matching_bridge = bridge
                break
    if matching_bridge is None:
        valid = False
        mismatches["bridge"] = (
            f"no executed canonical Cook -> MaleCNS bridge found: {canonical_bridge_engine}"
        )

    if not receipt.get("resolved_config_hash"):
        valid = False
        mismatches["resolved_config_hash"] = "missing"

    for artifact_kind in ("recording_artifacts", "context_artifacts"):
        artifacts = receipt.get(artifact_kind) or []
        if not artifacts:
            valid = False
            mismatches[artifact_kind] = "missing"
            continue
        missing_artifacts = [
            relative for relative in artifacts
            if not (data_dir / str(relative)).is_file()
        ]
        if missing_artifacts:
            valid = False
            mismatches[artifact_kind] = {
                "missing_files": missing_artifacts,
            }

    if (receipt.get("input_encoders") or {}).get(
        larva_item[0] if larva_item else "", "engine_default"
    ) != "engine_default":
        valid = False
        mismatches["larva.input_encoder"] = "primary readiness requires engine_default"

    datasets = receipt.get("datasets") or {}
    dataset_hashes: dict[str, dict[str, str]] = {}
    for spec in (larva, bee):
        pack_id = spec["pack_id"]
        dataset = datasets.get(pack_id)
        if not isinstance(dataset, dict) or dataset.get("error"):
            valid = False
            mismatches[f"dataset.{pack_id}"] = "verified install receipt missing"
            continue
        files = dataset.get("files") or []
        if not files or any(not item.get("sha256") for item in files):
            valid = False
            mismatches[f"dataset.{pack_id}"] = "dataset receipt lacks SHA-256 evidence"
            continue
        dataset_hashes[pack_id] = {
            str(item.get("name")): str(item.get("sha256"))
            for item in files
            if item.get("name") and item.get("sha256")
        }

    if larva_item is not None:
        larva_meta = larva_item[1].get("metadata") or {}
        installed = dataset_hashes.get(larva["pack_id"], {})
        expected_cook_hash = installed.get("cook_2020_adjacency.xlsx")
        observed_cook_hash = larva_meta.get("source_sha256")
        if not expected_cook_hash or observed_cook_hash != expected_cook_hash:
            valid = False
            mismatches["larva.source_sha256"] = {
                "expected": expected_cook_hash,
                "observed": observed_cook_hash,
            }

    if bee_item is not None:
        bee_meta = bee_item[1].get("metadata") or {}
        installed = dataset_hashes.get(bee["pack_id"], {})
        compiled_sources = bee_meta.get("compiled_source_hashes") or {}
        for name, expected_hash in installed.items():
            observed_hash = compiled_sources.get(name)
            if observed_hash != expected_hash:
                valid = False
                mismatches[f"bee.compiled_source_hashes.{name}"] = {
                    "expected": expected_hash,
                    "observed": observed_hash,
                }
        compiled_arrays = bee_meta.get("compiled_array_hashes") or {}
        if not compiled_arrays or any(not value for value in compiled_arrays.values()):
            valid = False
            mismatches["bee.compiled_array_hashes"] = "missing compiled array hash evidence"
        if not bee_meta.get("compiled_manifest_sha256"):
            valid = False
            mismatches["bee.compiled_manifest_sha256"] = "missing"

    status.update({
        "executed": bool(valid),
        "run_id": receipt.get("run_id"),
        "core_id": receipt.get("core_id"),
        "worker_hash": receipt.get("worker_hash"),
        "resolved_config_hash": receipt.get("resolved_config_hash"),
        "architecture": receipt.get("architecture"),
        "harness_passes": receipt.get("harness_passes"),
        "bridge": matching_bridge,
        "mismatches": mismatches,
    })
    return status


def experiment_readiness(
    contract: dict[str, Any],
    *,
    data_dir: Path,
    supported_engines: set[str],
) -> dict[str, Any]:
    primary = contract["primary_pipeline"]
    larva = primary["larva"]
    bee = primary["bee"]

    larva_files = list(larva.get("required_files") or ["cook_2020_adjacency.xlsx"])
    bee_files = list(bee.get("required_files", []))
    larva_data = _pack_file_status(data_dir, larva["pack_id"], larva_files)
    bee_data = _pack_file_status(data_dir, bee["pack_id"], bee_files)
    larva_engine_supported = larva["engine"] in supported_engines
    bee_engine_supported = bee["engine"] in supported_engines
    larva_execution = _execution_status(data_dir, larva)
    bee_execution = _execution_status(data_dir, bee)
    primary_execution = _primary_end_to_end_status(data_dir, contract)

    blockers: list[str] = []
    if not larva_data["installed"]:
        blockers.append("full Cook C. elegans dataset is not installed")
    if not larva_engine_supported:
        blockers.append(f"primary Larva engine is not implemented: {larva['engine']}")
    if larva.get("execution_required") and not larva_execution["executed"]:
        blockers.append("full Cook C. elegans primary stage has not produced a valid execution receipt")

    if not bee_data["installed"]:
        blockers.append("full MaleCNS dataset is not installed")
    if not bee_engine_supported:
        blockers.append(f"full MaleCNS execution engine is not implemented: {bee['engine']}")
    if bee.get("execution_required") and not bee_execution["executed"]:
        blockers.append("full MaleCNS primary stage has not produced a valid execution receipt")
    if not primary_execution["executed"]:
        blockers.append(
            "canonical full Cook → bridge → full MaleCNS pipeline has not produced one valid end-to-end execution receipt"
        )

    ready = not blockers
    return {
        "experiment_id": contract["experiment_id"],
        "status": "ready" if ready else "blocked",
        "primary_experiment_ready": ready,
        "primary_pipeline": {
            "larva": {
                **larva,
                "data": larva_data,
                "engine_supported": larva_engine_supported,
                "execution": larva_execution,
            },
            "bee": {
                **bee,
                "data": bee_data,
                "engine_supported": bee_engine_supported,
                "execution": bee_execution,
            },
        },
        "end_to_end_execution": primary_execution,
        "blockers": blockers,
        "controls": contract.get("controls", []),
        "note": "Primary readiness requires verified full Cook + full MaleCNS data, matching stage receipts, and one canonical end-to-end Cook → bridge → MaleCNS execution receipt. Controls cannot satisfy this gate.",
    }
