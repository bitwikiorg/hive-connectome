from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.providers.venice import VeniceChat, VeniceJev
from hive_connectome.settings import Settings


class ProviderConfigUpdate(BaseModel):
    venice_base_url: str | None = None
    venice_decision_model: str | None = None
    venice_api_key: str | None = Field(default=None, repr=False)
    clear_venice_api_key: bool = False
    lmstudio_base_url: str | None = None
    lmstudio_api_token: str | None = Field(default=None, repr=False)
    clear_lmstudio_api_token: bool = False
    default_llm_model: str | None = None
    clear_default_llm_model: bool = False


class ProviderTestRequest(BaseModel):
    capability: Literal["venice_jev", "venice_chat", "lmstudio_chat"]
    model: str | None = None


class ProviderRegistry:
    def __init__(self, data_dir: Path, defaults: Settings):
        self.data_dir = data_dir
        self.config_path = data_dir / "providers.json"
        self.secret_dir = data_dir / "provider-secrets"
        self.secret_dir.mkdir(parents=True, exist_ok=True)
        self._defaults = defaults
        self.config: dict[str, Any] = {
            "venice_base_url": defaults.venice_base_url,
            "venice_decision_model": defaults.venice_decision_model,
            "lmstudio_base_url": defaults.lmstudio_base_url,
            "default_llm_model": defaults.llm_model,
        }
        if self.config_path.exists():
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            for key in self.config:
                if key in raw:
                    self.config[key] = raw[key]
        self._seed_secret("venice_api_key", defaults.venice_api_key)
        self._seed_secret("lmstudio_api_token", defaults.lmstudio_api_token)
        self._write_public()

    def _secret_path(self, name: str) -> Path:
        return self.secret_dir / name

    def _seed_secret(self, name: str, value: str | None) -> None:
        path = self._secret_path(name)
        if path.exists() or not value:
            return
        self._write_secret(name, value)

    def _write_secret(self, name: str, value: str) -> None:
        path = self._secret_path(name)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(value.strip(), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _clear_secret(self, name: str) -> None:
        self._secret_path(name).unlink(missing_ok=True)

    def _read_secret(self, name: str) -> str | None:
        path = self._secret_path(name)
        if not path.exists():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    def _write_public(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        tmp.replace(self.config_path)

    def public(self) -> dict[str, Any]:
        return {
            **self.config,
            "venice_api_key_configured": self._read_secret("venice_api_key") is not None,
            "lmstudio_api_token_configured": self._read_secret("lmstudio_api_token") is not None,
        }

    def update(self, update: ProviderConfigUpdate) -> dict[str, Any]:
        values = update.model_dump(exclude_none=True)
        for key in ("venice_base_url", "venice_decision_model", "lmstudio_base_url", "default_llm_model"):
            if key in values:
                value = values[key]
                if isinstance(value, str):
                    value = value.strip()
                if key.endswith("_base_url") and not value:
                    raise ValueError(f"{key} may not be empty")
                self.config[key] = value or None

        if update.clear_venice_api_key:
            self._clear_secret("venice_api_key")
        elif update.venice_api_key is not None:
            if update.venice_api_key.strip():
                self._write_secret("venice_api_key", update.venice_api_key)
            else:
                self._clear_secret("venice_api_key")

        if update.clear_lmstudio_api_token:
            self._clear_secret("lmstudio_api_token")
        elif update.lmstudio_api_token is not None:
            if update.lmstudio_api_token.strip():
                self._write_secret("lmstudio_api_token", update.lmstudio_api_token)
            else:
                self._clear_secret("lmstudio_api_token")

        if update.clear_default_llm_model:
            self.config["default_llm_model"] = None

        self._write_public()
        return self.public()

    def clients(self) -> tuple[VeniceJev | None, VeniceChat | None, LMStudio]:
        venice_key = self._read_secret("venice_api_key")
        venice = (
            VeniceJev(
                str(self.config["venice_base_url"]),
                venice_key,
                str(self.config["venice_decision_model"]),
            )
            if venice_key
            else None
        )
        venice_chat = VeniceChat(str(self.config["venice_base_url"]), venice_key) if venice_key else None
        lmstudio = LMStudio(
            str(self.config["lmstudio_base_url"]),
            self._read_secret("lmstudio_api_token"),
        )
        return venice, venice_chat, lmstudio

    def apply(self, pipeline) -> None:
        venice, venice_chat, lmstudio = self.clients()
        pipeline.venice = venice
        pipeline.venice_chat = venice_chat
        pipeline.lmstudio = lmstudio
        pipeline.default_llm_model = self.config.get("default_llm_model")
