from __future__ import annotations
from typing import Any
import httpx
from hive_connectome.schemas import LLMResult

class LMStudio:
    def __init__(self,base_url:str,api_token:str|None=None,transport=None):
        self.base_url=base_url.rstrip("/");self.api_token=api_token;self.transport=transport
    @property
    def headers(self):
        h={"Content-Type":"application/json"}
        if self.api_token:h["Authorization"]=f"Bearer {self.api_token}"
        return h
    async def list_models(self)->dict[str,Any]:
        async with httpx.AsyncClient(timeout=10,transport=self.transport) as client:
            r=await client.get(f"{self.base_url}/models",headers=self.headers);r.raise_for_status();return r.json()
    async def chat(self,model:str,prompt:str,context:Any)->LLMResult:
        payload={"model":model,"temperature":0.2,"messages":[{"role":"system","content":"You are the occasional reasoning layer inside HIVE. Use supplied evidence only. Return concise analysis and unresolved questions."},{"role":"user","content":f"Task:\n{prompt}\n\nState:\n{context}"}]}
        async with httpx.AsyncClient(timeout=120,transport=self.transport) as client:
            r=await client.post(f"{self.base_url}/chat/completions",headers=self.headers,json=payload);r.raise_for_status();raw=r.json()
        return LLMResult(provider="lmstudio",model=model,text=raw.get("choices",[{}])[0].get("message",{}).get("content",""),raw=raw)
