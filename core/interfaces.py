from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IBroker(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_live_data(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute_trade(self, symbol: str, action: str, lot_size: float, **kwargs) -> Dict[str, Any]:
        pass

class IStrategy(ABC):
    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_recommendation(self, symbol: str) -> str:
        pass
