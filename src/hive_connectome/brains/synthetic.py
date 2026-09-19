from __future__ import annotations
import hashlib,json,math
from typing import Any
from hive_connectome.brains.base import MiniBrain
from hive_connectome.schemas import BrainKind,NeuralObservation

def _scalarize(value:Any)->float:
    if value is None:return 0.0
    if isinstance(value,bool):return 1.0 if value else -1.0
    if isinstance(value,(int,float)):return math.tanh(float(value)/100.0)
    if isinstance(value,str):
        h=hashlib.sha256(value.encode()).digest()
        return (int.from_bytes(h[:4],"big")/2**32)*2-1
    return _scalarize(json.dumps(value,sort_keys=True,default=str))

class DeterministicMiniBrain(MiniBrain):
    """Stateful deterministic reservoir for orchestration tests. Not a biological connectome."""
    def __init__(self,brain_id:str,kind:BrainKind,size:int):
        self.brain_id=brain_id;self.kind=kind;self.size=size;self.state=[0.0]*size;self.step_no=0;self.prev_energy=0.0;self._feedback=0.0
    def _weight(self,idx:int)->float:
        d=hashlib.sha256(f"{self.brain_id}:{idx}".encode()).digest()
        return (int.from_bytes(d[:4],"big")/2**32)*2-1
    def step(self,payload:Any)->NeuralObservation:
        drive=_scalarize(payload);old=list(self.state)
        for i in range(self.size):
            recurrent=0.72*old[i]+0.12*old[(i-1)%self.size]-0.05*old[(i+1)%self.size]
            self.state[i]=math.tanh(recurrent+drive*self._weight(i)+self._feedback*0.15)
        self._feedback*=0.5;self.step_no+=1
        energy=sum(v*v for v in self.state)/max(1,self.size);novelty=abs(energy-self.prev_energy);self.prev_energy=energy
        metrics={"mean":sum(self.state)/self.size,"energy":energy,"max_abs":max(abs(v) for v in self.state),"novelty":novelty}
        return NeuralObservation(brain_id=self.brain_id,brain_kind=self.kind,engine="synthetic-deterministic-v1",step=self.step_no,state_vector=list(self.state),metrics=metrics)
    def feedback(self,value:float)->None:self._feedback=max(-1.0,min(1.0,float(value)))
    def reset(self)->None:self.state=[0.0]*self.size;self.step_no=0;self.prev_energy=0.0;self._feedback=0.0
