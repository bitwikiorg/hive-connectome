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


def experiment_readiness(
    contract: dict[str, Any],
    *,
    data_dir: Path,
    supported_engines: set[str],
) -> dict[str, Any]:
    primary = contract["primary_pipeline"]
    larva = primary["larva"]
    bee = primary["bee"]

    larva_files = ["cook_2020_adjacency.xlsx"]
    bee_files = list(bee.get("required_files", []))
    larva_data = _pack_file_status(data_dir, larva["pack_id"], larva_files)
    bee_data = _pack_file_status(data_dir, bee["pack_id"], bee_files)
    larva_engine_supported = larva["engine"] in supported_engines
    bee_engine_supported = bee["engine"] in supported_engines

    blockers: list[str] = []
    if not larva_data["installed"]:
        blockers.append("full Cook C. elegans dataset is not installed")
    if not larva_engine_supported:
        blockers.append(f"primary Larva engine is not implemented: {larva['engine']}")
    if not bee_data["installed"]:
        blockers.append("full MaleCNS dataset is not installed")
    if not bee_engine_supported:
        blockers.append(f"full MaleCNS execution engine is not implemented: {bee['engine']}")

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
            },
            "bee": {
                **bee,
                "data": bee_data,
                "engine_supported": bee_engine_supported,
            },
        },
        "blockers": blockers,
        "controls": contract.get("controls", []),
        "note": "Primary readiness requires full Cook + full MaleCNS execution. Controls cannot satisfy this gate.",
    }
