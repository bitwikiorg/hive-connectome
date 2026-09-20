"""Real-connectome neural engines.

The topology is measured connectome data. Input encoding and the compact
dynamics used by HIVE are engineered experimental layers and are reported as
such in every observation.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from hive_connectome.brains.base import MiniBrain
from hive_connectome.connectomes.xlsx import read_sheet
from hive_connectome.schemas import BrainKind, NeuralObservation


SENSORY_C_ELEGANS = (
    "ADFL", "ADFR", "ADLL", "ADLR", "AFDL", "AFDR", "ALML", "ALMR", "ASEL", "ASER",
    "ASHL", "ASHR", "ASJL", "ASJR", "ASKL", "ASKR", "AWAL", "AWAR", "AWBL", "AWBR",
    "AWCL", "AWCR", "AVM", "PLML", "PLMR", "PVM", "URXL", "URXR",
)


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")


def _encoded_targets(payload: Any, candidates: list[int], count: int) -> list[tuple[int, float]]:
    if not candidates:
        return []
    digest = hashlib.sha256(_canonical_bytes(payload)).digest()
    out: list[tuple[int, float]] = []
    used: set[int] = set()
    for k in range(min(count, len(candidates))):
        block = hashlib.sha256(digest + k.to_bytes(2, "big")).digest()
        idx = candidates[int.from_bytes(block[:4], "big") % len(candidates)]
        if idx in used:
            continue
        used.add(idx)
        amplitude = 0.55 + (block[4] / 255.0) * 0.45
        out.append((idx, amplitude))
    return out


def _metrics(state: list[float], previous_energy: float) -> tuple[dict[str, float], float]:
    n = max(1, len(state))
    energy = sum(value * value for value in state) / n
    return {
        "mean": sum(state) / n,
        "energy": energy,
        "max_abs": max((abs(value) for value in state), default=0.0),
        "novelty": abs(energy - previous_energy),
        "active_fraction": sum(1 for value in state if abs(value) >= 0.2) / n,
    }, energy


class CookConnectomeBrain(MiniBrain):
    """Cook et al. corrected hermaphrodite wiring with graded recurrent dynamics.

    The sheet parsing follows OpenWorm/celeganssim conventions. Chemical edge
    signs are not available in the adjacency workbook alone, so HIVE treats the
    anatomical chemical weights as unsigned coupling in this compact generic
    experiment engine. This is real wiring with engineered dynamics, not a
    claim of complete C. elegans physiology.
    """

    engine_name = "cook2019-corrected-connectome-graded-v1"

    def __init__(self, brain_id: str, workbook: Path, substeps: int = 8):
        if not workbook.exists():
            raise FileNotFoundError(f"Cook connectome is not installed: {workbook}")
        self.brain_id = brain_id
        self.workbook = workbook
        self.substeps = max(1, int(substeps))
        self.names, self.edges, self.chemical_edges, self.gap_edges = self._load_graph(workbook)
        if not self.names or not self.edges:
            raise ValueError("Cook connectome workbook produced an empty neural graph")
        self.index = {name: i for i, name in enumerate(self.names)}
        self.state = [0.0] * len(self.names)
        self.prev_energy = 0.0
        self.step_no = 0
        self._feedback = 0.0
        self.input_candidates = [self.index[name] for name in SENSORY_C_ELEGANS if name in self.index]
        if not self.input_candidates:
            self.input_candidates = list(range(len(self.names)))
        incoming = [0.0] * len(self.names)
        for _, post, weight, kind in self.edges:
            incoming[post] += abs(weight) * (0.35 if kind == "gap" else 1.0)
        self.scale = [1.0 / max(1.0, value) for value in incoming]

    @staticmethod
    def _load_graph(workbook: Path):
        chemical = read_sheet(workbook, "hermaphrodite chemical")
        gap = read_sheet(workbook, "hermaphrodite gap jn symmetric")
        # In the corrected Cook workbook: row 3 (index 2) has postsynaptic
        # labels, column C (index 2) has presynaptic labels, body starts row 4.
        pre_names = []
        for row in chemical[3:]:
            if len(row) > 2 and row[2]:
                name = str(row[2]).strip()
                if name and name not in pre_names:
                    pre_names.append(name)
        names = pre_names
        index = {name: i for i, name in enumerate(names)}
        edges: list[tuple[int, int, float, str]] = []
        chem_count = 0
        gap_count = 0
        for grid, kind in ((chemical, "chemical"), (gap, "gap")):
            if len(grid) < 4:
                continue
            header = {str(cell).strip(): j for j, cell in enumerate(grid[2]) if cell and str(cell).strip() in index}
            for row in grid[3:]:
                if len(row) <= 2 or not row[2]:
                    continue
                pre = str(row[2]).strip()
                pre_idx = index.get(pre)
                if pre_idx is None:
                    continue
                for post, column in header.items():
                    if column >= len(row):
                        continue
                    try:
                        weight = float(row[column])
                    except (TypeError, ValueError):
                        continue
                    if weight <= 0:
                        continue
                    edges.append((pre_idx, index[post], weight, kind))
                    if kind == "chemical":
                        chem_count += 1
                    else:
                        gap_count += 1
        return names, edges, chem_count, gap_count

    def step(self, payload: Any) -> NeuralObservation:
        drives = _encoded_targets(payload, self.input_candidates, 18)
        for substep in range(self.substeps):
            recurrent = [0.0] * len(self.state)
            for pre, post, weight, kind in self.edges:
                if kind == "chemical":
                    # graded release proxy: [-1,1] state -> [0,1] release
                    release = (math.tanh(self.state[pre] * 2.0) + 1.0) * 0.5
                    recurrent[post] += weight * release
                else:
                    recurrent[post] += 0.35 * weight * (self.state[pre] - self.state[post])
            external = {idx: amp for idx, amp in drives} if substep < 2 else {}
            new_state = [0.0] * len(self.state)
            for i, old in enumerate(self.state):
                normalized = recurrent[i] * self.scale[i]
                drive = external.get(i, 0.0)
                new_state[i] = math.tanh(0.78 * old + 0.32 * normalized + drive + self._feedback * 0.08)
            self.state = new_state
        self._feedback *= 0.5
        self.step_no += 1
        metrics, self.prev_energy = _metrics(self.state, self.prev_energy)
        metrics.update({
            "nodes": float(len(self.names)),
            "edges": float(len(self.edges)),
            "chemical_edges": float(self.chemical_edges),
            "gap_edges": float(self.gap_edges),
            "input_nodes": float(len(drives)),
        })
        return NeuralObservation(
            brain_id=self.brain_id,
            brain_kind=BrainKind.WORM_LINK,
            engine=self.engine_name,
            step=self.step_no,
            state_vector=list(self.state),
            metrics=metrics,
            metadata={
                "real_connectome_topology": True,
                "source": "Cook et al. 2019; corrected July 2020 adjacency workbook",
                "data_file": str(self.workbook),
                "node_count": len(self.names),
                "edge_count": len(self.edges),
                "dynamics": "engineered graded recurrent dynamics over measured wiring",
                "input_encoding": "engineered deterministic payload-to-sensory-neuron stimulation",
            },
        )

    def feedback(self, value: float) -> None:
        self._feedback = max(-1.0, min(1.0, float(value)))

    def reset(self) -> None:
        self.state = [0.0] * len(self.names)
        self.prev_energy = 0.0
        self.step_no = 0
        self._feedback = 0.0


class MaleCNSLocomotorBrain(MiniBrain):
    """LIF engine over the measured MaleCNS v1.0 1,045-neuron locomotor subgraph.

    The network file and LIF constants are adapted from DesktopFly's public
    MaleCNS implementation. HIVE uses a deterministic generic input encoder in
    place of DesktopFly's body-specific sensory environment.
    """

    engine_name = "malecns-v1-locomotor-lif-v1"
    decay = 0.9512
    threshold = 1.0
    refractory_ms = 2
    weight_scale = 0.0008

    def __init__(self, brain_id: str, circuit_path: Path, ms_per_event: int = 10):
        if not circuit_path.exists():
            raise FileNotFoundError(f"MaleCNS locomotor connectome is not installed: {circuit_path}")
        raw = json.loads(circuit_path.read_text(encoding="utf-8"))
        self.brain_id = brain_id
        self.circuit_path = circuit_path
        self.neurons = raw.get("neurons", [])
        self.edges = raw.get("edges", [])
        if not self.neurons or not self.edges:
            raise ValueError("MaleCNS locomotor circuit produced an empty graph")
        self.n = len(self.neurons)
        self.ms_per_event = max(1, int(ms_per_event))
        self.v = [0.0] * self.n
        self.refr = [0] * self.n
        self.pending = [0.0] * self.n
        self.outgoing: list[list[tuple[int, float]]] = [[] for _ in range(self.n)]
        for edge in self.edges:
            pre, post, weight = int(edge[0]), int(edge[1]), float(edge[2])
            if 0 <= pre < self.n and 0 <= post < self.n:
                self.outgoing[pre].append((post, weight * self.weight_scale))
        candidates = [
            i for i, neuron in enumerate(self.neurons)
            if str(neuron.get("role", "")).lower() in {"sensory", "ascending"}
            or str(neuron.get("annotations", {}).get("superclass", "")).lower() in {"sensory_neuron", "ascending_neuron"}
        ]
        self.input_candidates = candidates or list(range(self.n))
        self.step_no = 0
        self.prev_energy = 0.0
        self._feedback = 0.0
        self.total_spikes = 0

    def step(self, payload: Any) -> NeuralObservation:
        drives = _encoded_targets(payload, self.input_candidates, 24)
        drive_map = {idx: amp for idx, amp in drives}
        event_spikes = 0
        active_indices: set[int] = set()
        for millisecond in range(self.ms_per_event):
            for i in range(self.n):
                if self.refr[i] > 0:
                    self.refr[i] -= 1
                    self.v[i] = 0.0
                    continue
                self.v[i] = self.v[i] * self.decay + self.pending[i]
                if millisecond < 3:
                    self.v[i] += drive_map.get(i, 0.0) * 0.55
                self.v[i] += self._feedback * 0.01
            self.pending = [0.0] * self.n
            spiked: list[int] = []
            for i, value in enumerate(self.v):
                if self.refr[i] == 0 and value >= self.threshold:
                    spiked.append(i)
                    active_indices.add(i)
                    self.v[i] = 0.0
                    self.refr[i] = self.refractory_ms
            for pre in spiked:
                for post, weight in self.outgoing[pre]:
                    self.pending[post] += weight
            event_spikes += len(spiked)
        self._feedback *= 0.5
        self.step_no += 1
        self.total_spikes += event_spikes
        metrics, self.prev_energy = _metrics(self.v, self.prev_energy)
        metrics.update({
            "nodes": float(self.n),
            "edges": float(len(self.edges)),
            "spikes": float(event_spikes),
            "spike_fraction": len(active_indices) / max(1, self.n),
            "input_nodes": float(len(drives)),
            "total_spikes": float(self.total_spikes),
        })
        return NeuralObservation(
            brain_id=self.brain_id,
            brain_kind=BrainKind.FLY_CORE,
            engine=self.engine_name,
            step=self.step_no,
            state_vector=list(self.v),
            metrics=metrics,
            metadata={
                "real_connectome_topology": True,
                "source": "MaleCNS v1.0 public 1,045-neuron locomotor subgraph; DesktopFly extraction",
                "data_file": str(self.circuit_path),
                "node_count": self.n,
                "edge_count": len(self.edges),
                "dynamics": "LIF-style dynamics adapted from DesktopFly over measured signed weights",
                "input_encoding": "engineered deterministic payload-to-sensory/ascending-neuron stimulation",
            },
        )

    def feedback(self, value: float) -> None:
        self._feedback = max(-1.0, min(1.0, float(value)))

    def reset(self) -> None:
        self.v = [0.0] * self.n
        self.refr = [0] * self.n
        self.pending = [0.0] * self.n
        self.step_no = 0
        self.prev_energy = 0.0
        self._feedback = 0.0
        self.total_spikes = 0
