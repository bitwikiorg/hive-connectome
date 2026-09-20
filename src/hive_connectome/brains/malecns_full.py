"""Full MaleCNS v1.0 sparse runtime.

Measured topology comes from the pinned MaleCNS v1.0 Feather tables.
The point-neuron dynamics, transmitter sign rule, normalization, input
encoding, and feedback are engineering choices and are reported as such.

The compiler follows the public MaleCNS sparse-runtime pattern used by
fly.ai and FLM while keeping HIVE's own integrity gates and execution receipts.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
from scipy import sparse

from hive_connectome.brains.base import MiniBrain
from hive_connectome.schemas import BrainKind, NeuralObservation


DEFAULT_NEURONS = 166_700
DEFAULT_DIRECTED_EDGES = 25_582_938
DEFAULT_SYNAPTIC_CONTACTS = 124_177_617
INHIBITORY_LABELS = ("gaba", "glutamate", "histamine")
COMPILED_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")


def _require_columns(table: pa.Table, names: list[str], source: str) -> None:
    missing = [name for name in names if name not in table.column_names]
    if missing:
        raise ValueError(f"{source} missing required columns: {missing}")


def compile_full_malecns(
    raw_root: Path,
    compiled_root: Path,
    *,
    expected_neurons: int | None = DEFAULT_NEURONS,
    expected_directed_edges: int | None = DEFAULT_DIRECTED_EDGES,
    expected_synaptic_contacts: int | None = DEFAULT_SYNAPTIC_CONTACTS,
) -> dict[str, Any]:
    annotations_path = raw_root / "annotations.feather"
    neurotransmitters_path = raw_root / "neurotransmitters.feather"
    edges_path = raw_root / "edges.feather"
    for path in (annotations_path, neurotransmitters_path, edges_path):
        if not path.exists():
            raise FileNotFoundError(f"full MaleCNS source file is not installed: {path}")

    annotations = feather.read_table(annotations_path)
    _require_columns(annotations, ["bodyId", "superclass"], "annotations.feather")
    body_ids = np.asarray(annotations["bodyId"].to_numpy(zero_copy_only=False), dtype=np.int64)
    superclasses = np.asarray([str(x or "") for x in annotations["superclass"].to_pylist()], dtype=object)
    if "status" in annotations.column_names:
        statuses = np.asarray([str(x or "") for x in annotations["status"].to_pylist()], dtype=object)
    else:
        statuses = np.asarray([""] * len(body_ids), dtype=object)

    keep = np.asarray(
        [bool(superclass) and status.lower() != "glia" for superclass, status in zip(superclasses, statuses)],
        dtype=bool,
    )
    kept_ids = body_ids[keep]
    kept_superclasses = superclasses[keep]
    order = np.argsort(kept_ids)
    ids = kept_ids[order]
    superclasses = kept_superclasses[order]
    if len(ids) != len(np.unique(ids)):
        raise ValueError("MaleCNS retained neuron IDs are not unique")
    n = int(len(ids))
    if expected_neurons is not None and n != int(expected_neurons):
        raise ValueError(f"MaleCNS neuron count mismatch: {n} != {expected_neurons}")

    nt = feather.read_table(neurotransmitters_path)
    _require_columns(nt, ["body", "consensus_nt"], "neurotransmitters.feather")
    nt_ids = np.asarray(nt["body"].to_numpy(zero_copy_only=False), dtype=np.int64)
    nt_labels = [str(x or "").lower() for x in nt["consensus_nt"].to_pylist()]
    nt_by_body = {int(body): label for body, label in zip(nt_ids, nt_labels)}
    sign = np.ones(n, dtype=np.float32)
    for i, body in enumerate(ids):
        label = nt_by_body.get(int(body), "")
        if any(token in label for token in INHIBITORY_LABELS):
            sign[i] = -1.0

    pre_parts: list[np.ndarray] = []
    post_parts: list[np.ndarray] = []
    count_parts: list[np.ndarray] = []
    raw_edge_rows = 0
    with pa.memory_map(str(edges_path), "r") as mapped:
        reader = pa.ipc.open_file(mapped)
        for batch_index in range(reader.num_record_batches):
            batch = reader.get_batch(batch_index)
            schema = batch.schema
            for name in ("body_pre", "body_post", "weight"):
                if schema.get_field_index(name) < 0:
                    raise ValueError(f"edges.feather missing required column: {name}")
            pre_id = np.asarray(batch.column(schema.get_field_index("body_pre")), dtype=np.int64)
            post_id = np.asarray(batch.column(schema.get_field_index("body_post")), dtype=np.int64)
            counts = np.asarray(batch.column(schema.get_field_index("weight")), dtype=np.int64)
            raw_edge_rows += int(len(pre_id))

            pre_index = np.searchsorted(ids, pre_id)
            post_index = np.searchsorted(ids, post_id)
            valid = (pre_index < n) & (post_index < n)
            valid &= ids[np.minimum(pre_index, n - 1)] == pre_id
            valid &= ids[np.minimum(post_index, n - 1)] == post_id
            pre_parts.append(pre_index[valid].astype(np.int32, copy=False))
            post_parts.append(post_index[valid].astype(np.int32, copy=False))
            count_parts.append(counts[valid].astype(np.int32, copy=False))

    if not pre_parts:
        raise ValueError("MaleCNS edges file produced no retained directed connections")
    pre = np.concatenate(pre_parts)
    post = np.concatenate(post_parts)
    counts = np.concatenate(count_parts)
    directed_edges = int(len(pre))
    contacts = int(counts.astype(np.int64).sum(dtype=np.int64))
    if expected_directed_edges is not None and directed_edges != int(expected_directed_edges):
        raise ValueError(f"MaleCNS directed-edge count mismatch: {directed_edges} != {expected_directed_edges}")
    if expected_synaptic_contacts is not None and contacts != int(expected_synaptic_contacts):
        raise ValueError(f"MaleCNS synaptic-contact count mismatch: {contacts} != {expected_synaptic_contacts}")

    weights = counts.astype(np.float32)
    weights *= sign[pre]
    incoming = np.bincount(post, weights=np.abs(weights), minlength=n).astype(np.float32)
    weights /= np.maximum(incoming[post], np.float32(1.0))

    matrix = sparse.csr_matrix((weights, (post, pre)), shape=(n, n), dtype=np.float32)
    matrix.sum_duplicates()
    matrix.sort_indices()
    if matrix.nnz != directed_edges:
        raise ValueError(
            f"MaleCNS duplicate directed edges changed sparse nnz: {matrix.nnz} != {directed_edges}"
        )

    sensory = np.asarray(
        [i for i, value in enumerate(superclasses) if "sensory" in str(value).lower()],
        dtype=np.int32,
    )
    descending = np.asarray(
        [i for i, value in enumerate(superclasses) if "descending" in str(value).lower()],
        dtype=np.int32,
    )

    compiled_root.mkdir(parents=True, exist_ok=True)
    np.save(compiled_root / "ids.npy", ids)
    np.save(compiled_root / "data.npy", matrix.data.astype(np.float32, copy=False))
    np.save(compiled_root / "indices.npy", matrix.indices.astype(np.int32, copy=False))
    np.save(compiled_root / "indptr.npy", matrix.indptr)
    np.save(compiled_root / "sensory_indices.npy", sensory)
    np.save(compiled_root / "descending_indices.npy", descending)

    manifest = {
        "compiled_version": COMPILED_VERSION,
        "release": "MaleCNS v1.0",
        "neurons": n,
        "directed_edges": int(matrix.nnz),
        "synaptic_contacts": contacts,
        "raw_edge_rows": raw_edge_rows,
        "retention": "nonempty superclass; status Glia excluded; both edge endpoints retained",
        "matrix_orientation": "row=postsynaptic; column=presynaptic",
        "weights": "synaptic contact count signed by predicted transmitter, then normalized by total absolute incoming weight",
        "transmitter_sign_rule": {
            "inhibitory_labels": list(INHIBITORY_LABELS),
            "all_other_or_unknown": "positive",
            "classification": "ENGINEERING_CHOICE informed by predicted neurotransmitter labels",
        },
        "source_files": {
            "annotations.feather": {"sha256": _sha256(annotations_path)},
            "neurotransmitters.feather": {"sha256": _sha256(neurotransmitters_path)},
            "edges.feather": {"sha256": _sha256(edges_path)},
        },
        "arrays": {
            "ids.npy": _sha256(compiled_root / "ids.npy"),
            "data.npy": _sha256(compiled_root / "data.npy"),
            "indices.npy": _sha256(compiled_root / "indices.npy"),
            "indptr.npy": _sha256(compiled_root / "indptr.npy"),
            "sensory_indices.npy": _sha256(compiled_root / "sensory_indices.npy"),
            "descending_indices.npy": _sha256(compiled_root / "descending_indices.npy"),
        },
        "input_groups": {
            "sensory_neurons": int(len(sensory)),
            "descending_neurons": int(len(descending)),
        },
    }
    tmp = compiled_root / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(compiled_root / "manifest.json")
    return manifest


class MaleCNSFullBrain(MiniBrain):
    """Deterministic LIF-style state propagation over the full retained MaleCNS graph."""

    engine_name = "malecns-full-v1-sparse-lif-v1"

    def __init__(
        self,
        brain_id: str,
        raw_root: Path,
        compiled_root: Path,
        *,
        expected_neurons: int | None = DEFAULT_NEURONS,
        expected_directed_edges: int | None = DEFAULT_DIRECTED_EDGES,
        expected_synaptic_contacts: int | None = DEFAULT_SYNAPTIC_CONTACTS,
        dt: float = 0.020,
        tau: float = 0.100,
        gain: float = 3.0,
        tonic: float = 0.14,
        threshold: float = 1.0,
        substeps: int = 5,
        sample_size: int = 2048,
    ):
        self.brain_id = brain_id
        self.raw_root = raw_root
        self.compiled_root = compiled_root
        self.expected_neurons = expected_neurons
        self.expected_directed_edges = expected_directed_edges
        self.expected_synaptic_contacts = expected_synaptic_contacts
        manifest_path = compiled_root / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = (
                expected_neurons,
                expected_directed_edges,
                expected_synaptic_contacts,
            )
            observed = (
                manifest.get("neurons"),
                manifest.get("directed_edges"),
                manifest.get("synaptic_contacts"),
            )
            mismatch = any(e is not None and int(e) != int(o) for e, o in zip(expected, observed))
            required_arrays = ["ids.npy", "data.npy", "indices.npy", "indptr.npy", "sensory_indices.npy"]
            if mismatch or manifest.get("compiled_version") != COMPILED_VERSION or not all((compiled_root / name).exists() for name in required_arrays):
                manifest = compile_full_malecns(
                    raw_root,
                    compiled_root,
                    expected_neurons=expected_neurons,
                    expected_directed_edges=expected_directed_edges,
                    expected_synaptic_contacts=expected_synaptic_contacts,
                )
        else:
            manifest = compile_full_malecns(
                raw_root,
                compiled_root,
                expected_neurons=expected_neurons,
                expected_directed_edges=expected_directed_edges,
                expected_synaptic_contacts=expected_synaptic_contacts,
            )
        self.manifest = manifest

        self.ids = np.load(compiled_root / "ids.npy", mmap_mode="r")
        self.data = np.load(compiled_root / "data.npy", mmap_mode="r")
        self.indices = np.load(compiled_root / "indices.npy", mmap_mode="r")
        self.indptr = np.load(compiled_root / "indptr.npy", mmap_mode="r")
        self.input_candidates = np.load(compiled_root / "sensory_indices.npy", mmap_mode="r").astype(np.int32, copy=False)
        if len(self.input_candidates) == 0:
            self.input_candidates = np.arange(len(self.ids), dtype=np.int32)
        self.W = sparse.csr_matrix(
            (self.data, self.indices, self.indptr),
            shape=(len(self.ids), len(self.ids)),
            copy=False,
        )
        self.n = int(len(self.ids))
        self.dt = float(dt)
        self.tau = float(tau)
        self.decay = np.float32(math.exp(-self.dt / self.tau))
        self.gain = np.float32(gain)
        self.tonic = np.float32(tonic)
        self.threshold = np.float32(threshold)
        self.substeps = max(1, int(substeps))
        self.sample_size = max(16, min(int(sample_size), self.n))
        self.sample_indices = np.linspace(0, self.n - 1, self.sample_size, dtype=np.int32)
        self.reset()

    def _drives(self, payload: Any) -> list[tuple[int, float]]:
        if isinstance(payload, dict) and "__hive_stimulus__" in payload:
            result = []
            for item in payload.get("__hive_stimulus__") or []:
                try:
                    idx, amplitude = int(item[0]), float(item[1])
                except (TypeError, ValueError, IndexError):
                    continue
                if 0 <= idx < self.n:
                    result.append((idx, max(-4.0, min(4.0, amplitude))))
            return result

        digest = hashlib.sha256(_canonical_bytes(payload)).digest()
        result = []
        used: set[int] = set()
        for i in range(min(48, len(self.input_candidates))):
            block = hashlib.sha256(digest + i.to_bytes(2, "big")).digest()
            idx = int(self.input_candidates[int.from_bytes(block[:4], "big") % len(self.input_candidates)])
            if idx in used:
                continue
            used.add(idx)
            result.append((idx, 0.55 + (block[4] / 255.0) * 0.45))
        return result

    def step(self, payload: Any) -> NeuralObservation:
        drives = self._drives(payload)
        drive_indices = np.asarray([item[0] for item in drives], dtype=np.int32)
        drive_values = np.asarray([item[1] for item in drives], dtype=np.float32)
        event_spikes = 0
        active = np.zeros(self.n, dtype=bool)

        for substep in range(self.substeps):
            current = self.W @ self.fired
            self.v *= self.decay
            self.v += current.astype(np.float32, copy=False) * self.gain
            self.v += self.tonic + np.float32(self._feedback * 0.05)
            if substep < 2 and len(drive_indices):
                np.add.at(self.v, drive_indices, drive_values)
            fired_indices = np.flatnonzero(self.v >= self.threshold)
            if len(fired_indices):
                active[fired_indices] = True
                self.v[fired_indices] = 0.0
            self.fired.fill(0.0)
            self.fired[fired_indices] = 1.0
            self.last_fired = fired_indices.astype(np.int32, copy=False)
            event_spikes += int(len(fired_indices))

        self._feedback *= 0.5
        self.step_no += 1
        energy = float(np.mean(self.v * self.v))
        novelty = abs(energy - self.prev_energy)
        self.prev_energy = energy
        state_hash = hashlib.sha256(self.v.tobytes()).hexdigest()
        sampled = self.v[self.sample_indices].astype(float).tolist()
        metrics = {
            "mean": float(np.mean(self.v)),
            "energy": energy,
            "max_abs": float(np.max(np.abs(self.v))) if self.n else 0.0,
            "novelty": float(novelty),
            "active_fraction": float(np.mean(active)),
            "nodes": float(self.n),
            "edges": float(self.W.nnz),
            "synaptic_contacts": float(self.manifest["synaptic_contacts"]),
            "spikes": float(event_spikes),
            "input_nodes": float(len(drives)),
        }
        return NeuralObservation(
            brain_id=self.brain_id,
            brain_kind=BrainKind.FLY_CORE,
            engine=self.engine_name,
            step=self.step_no,
            state_vector=sampled,
            metrics=metrics,
            metadata={
                "real_connectome_topology": True,
                "full_connectome": True,
                "source": "MaleCNS v1.0 public flat connectome",
                "compiled_manifest": str(self.compiled_root / "manifest.json"),
                "node_count": self.n,
                "edge_count": int(self.W.nnz),
                "synaptic_contacts": int(self.manifest["synaptic_contacts"]),
                "dynamics": "deterministic LIF-style sparse propagation over signed, incoming-normalized measured wiring",
                "dynamics_classification": "ENGINEERING_CHOICE",
                "input_encoding": "explicit bridge stimulus" if isinstance(payload, dict) and "__hive_stimulus__" in payload else "engineered deterministic payload-to-sensory-neuron stimulation",
                "state_vector_scope": "uniform_sample",
                "state_sample_size": self.sample_size,
                "state_hash": state_hash,
                "last_fired_count": int(len(self.last_fired)),
            },
        )

    def export_state(self) -> dict[str, np.ndarray]:
        return {
            "state": self.v.astype(np.float32, copy=True),
            "fired_indices": self.last_fired.astype(np.int32, copy=True),
            "sample_indices": self.sample_indices.astype(np.int32, copy=True),
            "step": np.asarray([self.step_no], dtype=np.int64),
        }

    def feedback(self, value: float) -> None:
        self._feedback = max(-1.0, min(1.0, float(value)))

    def reset(self) -> None:
        self.v = np.zeros(self.n, dtype=np.float32)
        self.fired = np.zeros(self.n, dtype=np.float32)
        self.last_fired = np.empty(0, dtype=np.int32)
        self.step_no = 0
        self.prev_energy = 0.0
        self._feedback = 0.0
