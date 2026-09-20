from __future__ import annotations


def neural_runtime_status() -> dict[str, object]:
    """Return the user-visible truth about the currently executable neural backend."""
    return {
        "backend": "synthetic-deterministic-v1",
        "biological_connectome_executing": False,
        "larva_stage": "16-state deterministic recurrent test reservoir",
        "bee_stage": "64-state deterministic recurrent test reservoir",
        "connectome_downloads_are_data_only": True,
        "note": (
            "Cook/Witvliet/MaleCNS packs can be downloaded and verified, "
            "but the current runtime does not execute them yet."
        ),
    }
