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
        "blockers": blockers,
        "controls": contract.get("controls", []),
        "note": "Primary readiness requires full Cook + full MaleCNS data, supported engines, and successful execution receipts. Controls cannot satisfy this gate.",
    }
