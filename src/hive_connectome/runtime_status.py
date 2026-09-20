from __future__ import annotations


def neural_runtime_status() -> dict[str, object]:
    """Static compatibility helper. Live readiness comes from /api/health."""
    return {
        "backend": "connectome-runtime-v0.7-core-graph",
        "primary_experiment_ready": False,
        "real_connectome_runtime_ready": False,
        "study_mode": "CONTROL_ONLY",
        "core_graph_runtime": True,
        "note": "v0.7 implements composable Core graphs and malecns_full_v1. Live primary readiness still requires exact full-data execution receipts; use /api/health.",
    }
