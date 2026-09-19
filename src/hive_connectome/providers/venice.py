from __future__ import annotations
from typing import Any
import httpx
from hive_connectome.schemas import DecisionBundle,JevQuestion

class VeniceJev:
    def __init__(self,base_url:str,api_key:str,model:str="jev-latest",transport=None):
        self.base_url=base_url.rstrip("/");self.api_key=api_key;self.model=model;self.transport=transport
    @property
    def headers(self):return {"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}
    async def list_models(self)->dict[str,Any]:
        async with httpx.AsyncClient(timeout=20,transport=self.transport) as client:
            r=await client.get(f"{self.base_url}/models",params={"type":"decision"},headers=self.headers);r.raise_for_status();return r.json()
    async def decide(self,state:Any,questions:dict[str,JevQuestion])->DecisionBundle:
        payload={"model":self.model,"state":state,"questions":{k:v.model_dump(exclude_none=True) for k,v in questions.items()}}
        async with httpx.AsyncClient(timeout=45,transport=self.transport) as client:
            r=await client.post(f"{self.base_url}/decisions",json=payload,headers=self.headers);r.raise_for_status();raw=r.json()
        confidences=[float(v["confidence"]) for v in raw.get("answers",{}).values() if isinstance(v,dict) and v.get("confidence") is not None]
        return DecisionBundle(provider="venice",model=raw.get("model",self.model),answers=raw.get("answers",{}),confidence=(sum(confidences)/len(confidences)) if confidences else None,raw=raw)
