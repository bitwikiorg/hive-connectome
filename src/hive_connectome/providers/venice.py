from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from hive_connectome.schemas import DecisionBundle, JevQuestion, LLMResult


class ProviderRequestError(RuntimeError):
    def __init__(self, message: str, receipt: dict[str, Any]):
        super().__init__(message)
        self.receipt = receipt


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _receipt(*, capability: str, endpoint: str, request: Any, model: str | None, started: float,
             status: int | None, response: Any = None, returned_model: str | None = None,
             headers: httpx.Headers | None = None, error: str | None = None) -> dict[str, Any]:
    selected_headers = {}
    if headers:
        for key in ("x-request-id", "request-id", "cf-ray"):
            if headers.get(key):
                selected_headers[key] = headers.get(key)
    return {
        "call_id": str(uuid4()),
        "provider": "venice",
        "capability": capability,
        "endpoint": endpoint,
        "requested_model": model,
        "returned_model": returned_model,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": (time.perf_counter() - started) * 1000,
        "http_status": status,
        "request_hash": _digest(request),
        "response_hash": _digest(response) if response is not None else None,
        "response_headers": selected_headers,
        "error": error,
    }


class VeniceJev:
    def __init__(self, base_url: str, api_key: str, model: str = "jev-latest", transport=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.transport = transport

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def list_models(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            r = await client.get(f"{self.base_url}/models", params={"type": "decision"}, headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def decide(self, state: Any, questions: dict[str, JevQuestion], model: str | None = None) -> DecisionBundle:
        payload = {
            "model": model or self.model,
            "state": state,
            "questions": {k: v.model_dump(exclude_none=True) for k, v in questions.items()},
        }
        endpoint = f"{self.base_url}/decisions"
        started = time.perf_counter()
        response = None
        try:
            async with httpx.AsyncClient(timeout=45, transport=self.transport) as client:
                r = await client.post(endpoint, json=payload, headers=self.headers)
                response = r
                r.raise_for_status()
                raw = r.json()
        except Exception as exc:
            status = response.status_code if response is not None else None
            body = response.text[:4000] if response is not None else None
            receipt = _receipt(
                capability="decisions", endpoint=endpoint, request=payload, model=payload["model"],
                started=started, status=status, response=body, headers=response.headers if response is not None else None,
                error=str(exc),
            )
            raise ProviderRequestError(str(exc), receipt) from exc

        confidences = [
            float(v["confidence"]) for v in raw.get("answers", {}).values()
            if isinstance(v, dict) and v.get("confidence") is not None
        ]
        returned_model = raw.get("model", payload["model"])
        transport = _receipt(
            capability="decisions", endpoint=endpoint, request=payload, model=payload["model"],
            started=started, status=r.status_code, response=raw, returned_model=returned_model, headers=r.headers,
        )
        return DecisionBundle(
            provider="venice",
            model=returned_model,
            answers=raw.get("answers", {}),
            confidence=(sum(confidences) / len(confidences)) if confidences else None,
            raw=raw,
            transport=transport,
        )


class VeniceChat:
    def __init__(self, base_url: str, api_key: str, transport=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.transport = transport

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, model: str, prompt: str, context: Any, temperature: float = 0.2) -> LLMResult:
        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an integrated reasoning member of HIVE. Process every supplied input with the neural and JEV state. Use supplied evidence only. Return ONLY JSON with keys answer (the task answer), analysis (string), confidence (number from 0.0 to 1.0 when meaningful), evidence_refs (array of strings), unresolved (array of strings), and neural_feedback (number from -1.0 to 1.0; 0.0 means deliberate no recurrent modulation).",
                },
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
            receipt = _receipt(
                capability="chat", endpoint=endpoint, request=payload, model=model, started=started,
                status=status, response=body, headers=response.headers if response is not None else None,
                error=str(exc),
            )
            raise ProviderRequestError(str(exc), receipt) from exc

        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        returned_model = raw.get("model", model)
        transport = _receipt(
            capability="chat", endpoint=endpoint, request=payload, model=model, started=started,
            status=response.status_code, response=raw, returned_model=returned_model, headers=response.headers,
        )
        return LLMResult(provider="venice", model=returned_model, text=text, raw=raw, transport=transport)
