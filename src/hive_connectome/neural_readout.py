from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np

from hive_connectome.schemas import NeuralObservation


def _state_array(engine: Any, observation: NeuralObservation) -> np.ndarray:
    if hasattr(engine, "v"):
        return np.asarray(getattr(engine, "v"), dtype=np.float32)
    if hasattr(engine, "state"):
        return np.asarray(getattr(engine, "state"), dtype=np.float32)
    return np.asarray(observation.state_vector, dtype=np.float32)


def _ids(engine: Any, n: int) -> list[Any]:
    if hasattr(engine, "ids"):
        raw = np.asarray(getattr(engine, "ids"))
        return [int(x) if np.issubdtype(raw.dtype, np.integer) else str(x) for x in raw[:n]]
    if hasattr(engine, "names"):
        return [str(x) for x in list(getattr(engine, "names"))[:n]]
    if hasattr(engine, "neurons"):
        out = []
        for index, neuron in enumerate(list(getattr(engine, "neurons"))[:n]):
            if isinstance(neuron, dict):
                out.append(neuron.get("id", index))
            else:
                out.append(index)
        return out
    return list(range(n))


def _quantiles(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {}
    points = [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0]
    qs = np.quantile(values, points)
    return {f"q{int(point * 100):02d}": float(value) for point, value in zip(points, qs)}


def _chunk_summary(state: np.ndarray, previous: np.ndarray | None, chunks: int) -> list[dict[str, Any]]:
    if state.size == 0:
        return []
    chunk_count = max(1, min(int(chunks), int(state.size)))
    boundaries = np.linspace(0, state.size, chunk_count + 1, dtype=np.int64)
    out: list[dict[str, Any]] = []
    for i in range(chunk_count):
        start, end = int(boundaries[i]), int(boundaries[i + 1])
        block = state[start:end]
        if block.size == 0:
            continue
        item: dict[str, Any] = {
            "chunk": i,
            "start": start,
            "end": end,
            "mean": float(np.mean(block)),
            "rms": float(math.sqrt(float(np.mean(block * block)))),
            "max_abs": float(np.max(np.abs(block))),
            "active_fraction": float(np.mean(np.abs(block) >= 0.2)),
        }
        if previous is not None and previous.size == state.size:
            delta = block - previous[start:end]
            item["delta_rms"] = float(math.sqrt(float(np.mean(delta * delta))))
            item["delta_mean"] = float(np.mean(delta))
        out.append(item)
    return out


def _top_values(state: np.ndarray, ids: list[Any], limit: int) -> list[dict[str, Any]]:
    if state.size == 0:
        return []
    k = max(1, min(int(limit), int(state.size)))
    if k == state.size:
        order = np.argsort(-np.abs(state))
    else:
        candidate = np.argpartition(np.abs(state), -k)[-k:]
        order = candidate[np.argsort(-np.abs(state[candidate]))]
    return [
        {"index": int(index), "id": ids[int(index)], "value": float(state[int(index)])}
        for index in order
    ]


def _group_summary(engine: Any, state: np.ndarray, limit: int = 64) -> list[dict[str, Any]]:
    raw_root = getattr(engine, "raw_root", None)
    ids = getattr(engine, "ids", None)
    if raw_root is None or ids is None or state.size == 0:
        return []
    try:
        cached = getattr(engine, "_hive_superclasses", None)
        if cached is None:
            import pyarrow.feather as feather

            table = feather.read_table(raw_root / "annotations.feather", columns=["bodyId", "superclass", "status"])
            body_ids = np.asarray(table["bodyId"].to_numpy(zero_copy_only=False), dtype=np.int64)
            superclasses = np.asarray([str(x or "") for x in table["superclass"].to_pylist()], dtype=object)
            statuses = np.asarray([str(x or "") for x in table["status"].to_pylist()], dtype=object)
            keep = np.asarray(
                [bool(group) and status.lower() != "glia" for group, status in zip(superclasses, statuses)],
                dtype=bool,
            )
            kept_ids = body_ids[keep]
            kept_groups = superclasses[keep]
            order = np.argsort(kept_ids)
            cached = kept_groups[order]
            setattr(engine, "_hive_superclasses", cached)
        groups = np.asarray(cached, dtype=object)
        if groups.size != state.size:
            return []
        fired = set(int(x) for x in np.asarray(getattr(engine, "last_fired", []), dtype=np.int64).tolist())
        rows: list[dict[str, Any]] = []
        for group in np.unique(groups):
            indices = np.flatnonzero(groups == group)
            values = state[indices]
            rows.append({
                "group": str(group),
                "neurons": int(indices.size),
                "mean": float(np.mean(values)),
                "rms": float(math.sqrt(float(np.mean(values * values)))),
                "max_abs": float(np.max(np.abs(values))),
                "active_fraction": float(np.mean(np.abs(values) >= 0.2)),
                "fired": int(sum(1 for index in indices.tolist() if int(index) in fired)),
            })
        rows.sort(key=lambda row: (row["rms"], row["max_abs"]), reverse=True)
        return rows[:limit]
    except Exception:
        return []


def whole_state_readout(
    engine: Any,
    observation: NeuralObservation,
    *,
    previous_state: np.ndarray | None = None,
    dense_limit: int = 4096,
    top_k: int = 256,
    chunks: int = 128,
) -> dict[str, Any]:
    """Build a JEV/LLM-facing representation from the complete neural state.

    Small states are transmitted losslessly. Large states are reduced deterministically
    using statistics that touch every neuron plus high-salience sparse details. The
    complete state is still integrity-bound by a SHA-256 hash.
    """
    state = _state_array(engine, observation)
    identifiers = _ids(engine, int(state.size))
    state_hash = hashlib.sha256(state.tobytes()).hexdigest()
    delta = None
    if previous_state is not None and previous_state.size == state.size:
        delta = state - previous_state

    result: dict[str, Any] = {
        "representation": "lossless_dense" if state.size <= dense_limit else "whole_state_multiresolution_v1",
        "neurons": int(state.size),
        "state_hash": state_hash,
        "metrics": observation.metrics,
        "metadata": observation.metadata,
        "distribution": {
            "mean": float(np.mean(state)) if state.size else 0.0,
            "rms": float(math.sqrt(float(np.mean(state * state)))) if state.size else 0.0,
            "std": float(np.std(state)) if state.size else 0.0,
            "active_fraction_0_2": float(np.mean(np.abs(state) >= 0.2)) if state.size else 0.0,
            "quantiles": _quantiles(state),
        },
    }

    if delta is not None:
        result["delta"] = {
            "rms": float(math.sqrt(float(np.mean(delta * delta)))) if delta.size else 0.0,
            "mean": float(np.mean(delta)) if delta.size else 0.0,
            "max_abs": float(np.max(np.abs(delta))) if delta.size else 0.0,
            "quantiles": _quantiles(delta),
        }

    if state.size <= dense_limit:
        result["state"] = {
            "ids": identifiers,
            "values": state.astype(float).tolist(),
        }
    else:
        result["chunks"] = _chunk_summary(state, previous_state, chunks)
        result["top_absolute"] = _top_values(state, identifiers, top_k)
        result["groups"] = _group_summary(engine, state)

        fired = np.asarray(getattr(engine, "last_fired", []), dtype=np.int64)
        if fired.size:
            fired_cap = fired[:1024]
            result["recent_firing"] = {
                "count": int(fired.size),
                "indices": fired_cap.astype(int).tolist(),
                "ids": [identifiers[int(i)] for i in fired_cap if 0 <= int(i) < len(identifiers)],
                "truncated": bool(fired.size > fired_cap.size),
            }

        candidates = np.asarray(getattr(engine, "input_candidates", []), dtype=np.int64)
        if candidates.size:
            valid = candidates[(candidates >= 0) & (candidates < state.size)]
            values = state[valid]
            result["input_population"] = {
                "count": int(valid.size),
                "mean": float(np.mean(values)) if values.size else 0.0,
                "rms": float(math.sqrt(float(np.mean(values * values)))) if values.size else 0.0,
                "active_fraction": float(np.mean(np.abs(values) >= 0.2)) if values.size else 0.0,
            }

    return result


def snapshot_state(engine: Any, observation: NeuralObservation | None = None) -> np.ndarray:
    if observation is None:
        if hasattr(engine, "v"):
            return np.asarray(getattr(engine, "v"), dtype=np.float32).copy()
        if hasattr(engine, "state"):
            return np.asarray(getattr(engine, "state"), dtype=np.float32).copy()
        return np.empty(0, dtype=np.float32)
    return _state_array(engine, observation).copy()
