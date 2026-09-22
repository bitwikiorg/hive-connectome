from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from hive_connectome.providers.venice import ProviderRequestError
from hive_connectome.schemas import LLMResult


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LMStudio:
    def __init__(self, base_url: str, api_token: str | None = None, transport=None):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.transport = transport

    @property
    def headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    async def list_models(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10, transport=self.transport) as client:
            r = await client.get(f"{self.base_url}/models", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def chat(self, model: str, prompt: str, context: Any, temperature: float = 0.2) -> LLMResult:
        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": "You are an integrated reasoning member of HIVE. Process every supplied input with the neural and JEV state. Use supplied evidence only. Return ONLY JSON with keys analysis (string), unresolved (array of strings), and neural_feedback (number from -1.0 to 1.0; 0.0 means no recurrent modulation)."},
                {"role": "user", "content": f"Task:\n{prompt}\n\nState:\n{context}"},
            ],
        }
        endpoint = f"{self.base_url}/chat/completions"
        started = time.perf_counter()
        response = None
        try:
            async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
                response = await client.post(endpoint, headers=self.headers, json=payload)
                response.raise_for_status()
                raw = response.json()
        except Exception as exc:
            status = response.status_code if response is not None else None
            body = response.text[:4000] if response is not None else None
            receipt = {
                "call_id": str(uuid4()), "provider": "lmstudio", "capability": "chat", "endpoint": endpoint,
                "requested_model": model, "returned_model": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": (time.perf_counter() - started) * 1000, "http_status": status,
                "request_hash": _digest(payload), "response_hash": _digest(body) if body is not None else None,
                "response_headers": {}, "error": str(exc),
            }
            raise ProviderRequestError(str(exc), receipt) from exc

        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        returned_model = raw.get("model", model)
        transport = {
            "call_id": str(uuid4()), "provider": "lmstudio", "capability": "chat", "endpoint": endpoint,
            "requested_model": model, "returned_model": returned_model,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": (time.perf_counter() - started) * 1000, "http_status": response.status_code,
            "request_hash": _digest(payload), "response_hash": _digest(raw),
            "response_headers": {k: response.headers.get(k) for k in ("x-request-id", "request-id") if response.headers.get(k)},
            "error": None,
        }
        return LLMResult(provider="lmstudio", model=returned_model, text=text, raw=raw, transport=transport)
