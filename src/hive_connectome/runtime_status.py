from __future__ import annotations


def neural_runtime_status() -> dict[str, object]:
    """Static compatibility helper. Live readiness comes from /api/health."""
    return {
        "backend": "connectome-runtime-v0.6-state-reset",
        "primary_experiment_ready": False,
        "real_connectome_runtime_ready": False,
        "study_mode": "CONTROL_ONLY",
        "note": "Primary study requires full Cook + full MaleCNS execution. Use /api/health for live blockers.",
    }
