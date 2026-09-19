from __future__ import annotations
import json
from typing import Any
from hive_connectome.brains.synthetic import DeterministicMiniBrain
from hive_connectome.db import HiveDB
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.providers.venice import VeniceJev
from hive_connectome.schemas import BrainKind,DecisionBundle,DecisionType,JevQuestion,PipelineRequest,PipelineResult

def default_questions()->dict[str,JevQuestion]:
    return {
      "meaningful_signal":JevQuestion(type=DecisionType.NOUL,instructions="Is this event materially meaningful for system state, considering the event and neural readouts?"),
      "novelty":JevQuestion(type=DecisionType.SCORE,instructions="How novel is this event relative to supplied state?",criteria=["routine","notable","highly novel"]),
      "route":JevQuestion(type=DecisionType.CHOICE,instructions="What should HIVE do with this event?",criteria={"store":"Store as ordinary evidence","inspect":"Inspect or classify more deeply","escalate":"Use an LLM because bounded decisions are insufficient","ignore":"No useful state change"}),
      "llm_needed":JevQuestion(type=DecisionType.NOUL,instructions="Does this event require open-ended semantic reasoning beyond bounded classification?")
    }

def local_decision(state:dict[str,Any])->DecisionBundle:
    novelty=min(2.0,float(state["fly"]["metrics"]["novelty"])*20.0);meaningful=min(0.98,0.35+float(state["fly"]["metrics"]["energy"])*2.5)
    llm_needed=0.75 if novelty>1.3 else 0.2;route="escalate" if llm_needed>0.6 else ("inspect" if novelty>0.5 else "store")
    answers={"meaningful_signal":{"type":"noul","noul":meaningful},"novelty":{"type":"score","score":novelty,"confidence":0.55},"route":{"type":"choice","choice":route,"confidence":0.55},"llm_needed":{"type":"noul","noul":llm_needed}}
    return DecisionBundle(provider="local-heuristic",model="offline-v1",answers=answers,confidence=0.55)

class HivePipeline:
    def __init__(self,db:HiveDB,venice:VeniceJev|None=None,lmstudio:LMStudio|None=None,llm_model:str|None=None):
        self.db=db;self.venice=venice;self.lmstudio=lmstudio;self.llm_model=llm_model
        self.worm=DeterministicMiniBrain("worm-link-0",BrainKind.WORM_LINK,16);self.fly=DeterministicMiniBrain("fly-core-0",BrainKind.FLY_CORE,64)
    def reset(self):self.worm.reset();self.fly.reset()
    @staticmethod
    def _noul(bundle:DecisionBundle,key:str)->float:
        try:return float(bundle.answers[key]["noul"])
        except Exception:return 0.5
    async def run(self,req:PipelineRequest)->PipelineResult:
        self.db.insert_event(req.event.model_dump(mode="json"))
        worm=self.worm.step(req.event.payload)
        fly=self.fly.step({"event":req.event.payload,"worm_metrics":worm.metrics,"worm_state_excerpt":worm.state_vector[:8]})
        decision_state={"event":req.event.model_dump(mode="json"),"worm":{"metrics":worm.metrics,"state_excerpt":worm.state_vector[:8]},"fly":{"metrics":fly.metrics,"state_excerpt":fly.state_vector[:12]}}
        use_live_jev=req.mode!="offline" and self.venice is not None
        decisions=await self.venice.decide(decision_state,default_questions()) if use_live_jev else local_decision(decision_state)
        novelty=float(decisions.answers.get("novelty",{}).get("score",1.0));meaningful=self._noul(decisions,"meaningful_signal");llm_needed=self._noul(decisions,"llm_needed");route=decisions.answers.get("route",{}).get("choice","store")
        modulation=max(-1.0,min(1.0,(meaningful-0.5)*0.8+(novelty-1.0)*0.2));self.worm.feedback(modulation);self.fly.feedback(modulation)
        should_llm=req.force_llm or llm_needed>=0.65 or route=="escalate";llm=None;unresolved=[]
        if should_llm:
            selected_model=self.llm_model
            if self.lmstudio is not None and not selected_model:
                try:
                    listed=await self.lmstudio.list_models();models=listed.get("data",[]) if isinstance(listed,dict) else []
                    if models:selected_model=models[0].get("id")
                except Exception:selected_model=None
            if self.lmstudio is not None and selected_model:
                llm=await self.lmstudio.chat(selected_model,"Explain what changed, why it may matter, and what remains unresolved. Do not propose irreversible actions.",json.dumps(decision_state,default=str))
            else:unresolved.append("LLM escalation requested but no reachable local LM Studio model is available.")
        verification=None
        if llm is not None and use_live_jev:
            verification=await self.venice.decide({"evidence":decision_state,"llm_output":llm.text},{"supported":JevQuestion(type=DecisionType.NOUL,instructions="Is the LLM output supported by supplied evidence without unsupported claims?")})
        labels=[f"route:{route}"]
        if meaningful>=0.7:labels.append("meaningful")
        if novelty>=1.4:labels.append("novel")
        result=PipelineResult(event=req.event,worm=worm,fly=fly,decisions=decisions,llm=llm,verification=verification,modulation=modulation,labels=labels,unresolved=unresolved)
        self.db.insert_run(result.model_dump(mode="json"));return result
