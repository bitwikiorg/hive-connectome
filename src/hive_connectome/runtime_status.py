from __future__ import annotations


def neural_runtime_status() -> dict[str, object]:
    """Legacy static status helper retained for API compatibility.

    The live application reports dynamic runtime readiness through
    HivePipeline.runtime_status().
    """
    return {
        "backend": "connectome-runtime-v0.5",
        "real_connectome_runtime_ready": None,
        "note": "Use /api/health for live installed-pack readiness.",
    }
