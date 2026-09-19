from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _secret(name: str, env_name: str) -> str | None:
    path = Path("/run/secrets") / name
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = os.getenv(env_name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    config_dir: Path
    venice_base_url: str
    venice_api_key: str | None
    venice_decision_model: str
    lmstudio_base_url: str
    lmstudio_api_token: str | None
    llm_provider: str
    llm_model: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("HIVE_DATA_DIR", "./data")).resolve(),
            config_dir=Path(os.getenv("HIVE_CONFIG_DIR", "./config")).resolve(),
            venice_base_url=os.getenv("VENICE_BASE_URL", "https://api.venice.ai/api/v1").rstrip("/"),
            venice_api_key=_secret("venice_api_key", "VENICE_API_KEY"),
            venice_decision_model=os.getenv("VENICE_DECISION_MODEL", "jev-latest"),
            lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/"),
            lmstudio_api_token=_secret("lmstudio_api_token", "LMSTUDIO_API_TOKEN"),
            llm_provider=os.getenv("HIVE_LLM_PROVIDER", "lmstudio"),
            llm_model=os.getenv("HIVE_LLM_MODEL", "").strip() or None,
        )
