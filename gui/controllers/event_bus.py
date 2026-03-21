#!/usr/bin/env python3
"""
Event Bus für das FinGPT Dashboard
Ermöglicht lose Kopplung zwischen Komponenten durch ereignisbasierte Kommunikation
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


# Event-Typen für Dashboard-Updates
class DashboardEvents:
    """Event-Typen für das Dashboard"""
    BALANCE_UPDATED = "balance_updated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    TRADE_EXECUTED = "trade_executed"
    SIGNAL_GENERATED = "signal_generated"
    CONNECTION_STATUS_CHANGED = "connection_status_changed"
    MARGIN_WARNING = "margin_warning"
    ACCOUNT_DATA_UPDATED = "account_data_updated"
    MARKET_DATA_UPDATED = "market_data_updated"
    AI_STATUS_UPDATED = "ai_status_updated"


@dataclass
class DashboardEvent:
    """Event-Datenstruktur"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


class EventBus:
    """
    Zentraler Event-Bus für Dashboard-Kommunikation.
    Ermöglicht Subscription und Publishing von Events zwischen entkoppelten Komponenten.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton-Pattern für globalen Zugriff"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[DashboardEvent] = []
        self._max_history = 100
        self._logger = logging.getLogger("EventBus")
        self._initialized = True
        
    def subscribe(self, event_type: str, callback: Callable[[DashboardEvent], None]) -> None:
        """
        Registriert einen Callback für einen bestimmten Event-Typ.
        
        Args:
            event_type: Der Event-Typ (z.B. DashboardEvents.BALANCE_UPDATED)
            callback: Die Funktion, die bei Events aufgerufen wird
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            self._logger.debug(f"Subscriber registriert für {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable[[DashboardEvent], None]) -> None:
        """
        Entfernt einen Callback von einem Event-Typ.
        
        Args:
            event_type: Der Event-Typ
            callback: Der zu entfernende Callback
        """
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                self._logger.debug(f"Subscriber entfernt für {event_type}")
    
    def publish(self, event_type: str, data: Dict[str, Any], source: Optional[str] = None) -> None:
        """
        Published ein Event an alle Subscriber.
        
        Args:
            event_type: Der Event-Typ
            data: Die Event-Daten
            source: Optional die Quelle des Events
        """
        event = DashboardEvent(
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=source
        )
        
        # Event zur Historie hinzufügen
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Event an Subscriber senden
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    self._logger.error(f"Fehler bei Event-Callback für {event_type}: {e}")
        
        # Auch an "all" Subscriber senden
        if "all" in self._subscribers:
            for callback in self._subscribers["all"]:
                try:
                    callback(event)
                except Exception as e:
                    self._logger.error(f"Fehler bei All-Event-Callback: {e}")
    
    def subscribe_all(self, callback: Callable[[DashboardEvent], None]) -> None:
        """Abonniert alle Events"""
        self.subscribe("all", callback)
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 10) -> List[DashboardEvent]:
        """
        Gibt die Event-Historie zurück.
        
        Args:
            event_type: Optional filtern nach Event-Typ
            limit: Maximale Anzahl zurückzugebender Events
            
        Returns:
            Liste von Events
        """
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        return history[-limit:]
    
    def clear_history(self) -> None:
        """Löscht die Event-Historie"""
        self._event_history.clear()
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Gibt die Anzahl der Subscriber für einen Event-Typ zurück"""
        return len(self._subscribers.get(event_type, []))


# Convenience-Funktionen
def get_event_bus() -> EventBus:
    """Gibt die globale EventBus-Instanz zurück"""
    return EventBus()


def publish_event(event_type: str, data: Dict[str, Any], source: Optional[str] = None) -> None:
    """Convenience-Funktion zum Publishen eines Events"""
    get_event_bus().publish(event_type, data, source)


def subscribe_event(event_type: str, callback: Callable[[DashboardEvent], None]) -> None:
    """Convenience-Funktion zum Subscriben eines Events"""
    get_event_bus().subscribe(event_type, callback)


# Beispiel-Usage
if __name__ == "__main__":
    # Konfiguration
    logging.basicConfig(level=logging.DEBUG)
    
    # Event-Bus Instanz
    bus = EventBus()
    
    # Callback-Funktionen
    def on_balance_update(event: DashboardEvent):
        print(f"📊 Balance Update: {event.data}")
    
    def on_trade_executed(event: DashboardEvent):
        print(f"📈 Trade ausgeführt: {event.data}")
    
    def on_all_events(event: DashboardEvent):
        print(f"📝 Event empfangen: {event.event_type}")
    
    # Subscriber registrieren
    bus.subscribe(DashboardEvents.BALANCE_UPDATED, on_balance_update)
    bus.subscribe(DashboardEvents.TRADE_EXECUTED, on_trade_executed)
    bus.subscribe_all(on_all_events)
    
    # Events publishen
    bus.publish(DashboardEvents.BALANCE_UPDATED, {"balance": 10000.50, "equity": 10500.00}, "MT5")
    bus.publish(DashboardEvents.TRADE_EXECUTED, {"symbol": "EURUSD", "type": "BUY", "volume": 0.1}, "AI")
    
    # Historie abfragen
    print("\n--- Event Historie ---")
    for event in bus.get_event_history(limit=5):
        print(f"{event.timestamp.strftime('%H:%M:%S')} - {event.event_type}: {event.data}")
