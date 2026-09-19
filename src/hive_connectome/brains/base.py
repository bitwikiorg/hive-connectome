from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from hive_connectome.schemas import NeuralObservation

class MiniBrain(ABC):
    @abstractmethod
    def step(self,payload:Any)->NeuralObservation: raise NotImplementedError
    @abstractmethod
    def feedback(self,value:float)->None: raise NotImplementedError
    @abstractmethod
    def reset(self)->None: raise NotImplementedError
