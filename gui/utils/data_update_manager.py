#!/usr/bin/env python3
"""
Data Update Manager für das FinGPT Dashboard
Zentralisiert Daten-Updates mit Throttling und Debouncing für optimale Performance
"""

import queue
import threading
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class UpdatePriority(Enum):
    """Priorität von Updates"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class DataUpdate:
    """Daten-Update-Objekt"""
    data_type: str
    data: Dict[str, Any]
    priority: UpdatePriority = UpdatePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None


class DataUpdateManager:
    """
    Zentralisiert Daten-Updates für das Dashboard mit Throttling und Debouncing.
    Verhindert zu viele UI-Updates und bündelt Updates für bessere Performance.
    """
    
    # Singleton-Instanz
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._update_queue = queue.PriorityQueue()
        self._last_updates: Dict[str, Dict[str, Any]] = {}
        self._update_intervals: Dict[str, float] = {
            'ticks': 1.0,        # 1 Sekunde
            'positions': 5.0,    # 5 Sekunden
            'signals': 30.0,     # 30 Sekunden
            'account': 5.0,      # 5 Sekunden
            'charts': 10.0,      # 10 Sekunden
        }
        self._last_update_times: Dict[str, float] = {}
        
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._logger = logging.getLogger("DataUpdateManager")
        
        # Callback-Registrierung
        self._update_callbacks: Dict[str, Callable] = {}
        
        # Batch-Verarbeitung
        self._batch_size = 10
        self._batch_timeout = 0.1  # 100ms
        
        self._initialized = True
        
    def start(self):
        """Startet den Update-Manager"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._worker_thread.start()
            self._logger.info("DataUpdateManager gestartet")
    
    def stop(self):
        """Stoppt den Update-Manager"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        self._logger.info("DataUpdateManager gestoppt")
    
    def set_update_interval(self, data_type: str, interval_seconds: float):
        """Setzt das Update-Intervall für einen bestimmten Datentyp"""
        self._update_intervals[data_type] = interval_seconds
        self._logger.debug(f"Update-Intervall für {data_type} auf {interval_seconds}s gesetzt")
    
    def register_callback(self, data_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Registriert einen Callback für einen Datentyp"""
        self._update_callbacks[data_type] = callback
    
    def schedule_update(self, data_type: str, data: Dict[str, Any], 
                       priority: UpdatePriority = UpdatePriority.NORMAL,
                       source: Optional[str] = None):
        """
        Plant ein Update mit Throttling.
        Das Update wird nur verarbeitet, wenn das letzte Update für diesen Typ
        lange genug her ist.
        """
        current_time = time.time()
        
        # Throttling: Nur verarbeiten wenn genug Zeit vergangen
        last_time = self._last_update_times.get(data_type, 0)
        interval = self._update_intervals.get(data_type, 1.0)
        
        # Für kritische Updates immer durchführen
        if priority != UpdatePriority.CRITICAL and (current_time - last_time) < interval:
            self._logger.debug(f"Update für {data_type} wegen Throttling übersprungen")
            return
        
        update = DataUpdate(
            data_type=data_type,
            data=data,
            priority=priority,
            timestamp=datetime.now(),
            source=source
        )
        
        self._update_queue.put((priority.value * -1, current_time, update))
        self._last_update_times[data_type] = current_time
        
        # Daten zwischenspeichern
        self._last_updates[data_type] = data
        
    def _process_loop(self):
        """Hintergrund-Thread für Update-Verarbeitung"""
        while self._running:
            try:
                # Versuche Update aus der Queue zu holen (mit Timeout)
                try:
                    priority, timestamp, update = self._update_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Callback aufrufen
                self._process_update(update)
                
                # Queue leeren (Batch-Verarbeitung)
                self._process_batch()
                
            except Exception as e:
                self._logger.error(f"Fehler in Update-Loop: {e}")
    
    def _process_update(self, update: DataUpdate):
        """Verarbeitet ein einzelnes Update"""
        data_type = update.data_type
        
        if data_type in self._update_callbacks:
            try:
                self._update_callbacks[data_type](update.data)
            except Exception as e:
                self._logger.error(f"Fehler bei Callback für {data_type}: {e}")
        else:
            self._logger.warning(f"Kein Callback registriert für {data_type}")
    
    def _process_batch(self):
        """Verarbeitet mehrere Updates aus der Queue"""
        processed_types = set()
        
        for _ in range(self._batch_size):
            try:
                priority, timestamp, update = self._update_queue.get_nowait()
                
                # Doppelte Updates für gleichen Typ überspringen (nur neuestes behalten)
                if update.data_type not in processed_types:
                    self._process_update(update)
                    processed_types.add(update.data_type)
                    
            except queue.Empty:
                break
    
    def get_cached_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """Gibt zwischengespeicherte Daten zurück"""
        return self._last_updates.get(data_type)
    
    def get_all_cached_data(self) -> Dict[str, Dict[str, Any]]:
        """Gibt alle zwischengespeicherten Daten zurück"""
        return self._last_updates.copy()
    
    def force_update(self, data_type: str):
        """Erzwingt ein Update für einen bestimmten Typ (setzt Throttling zurück)"""
        if data_type in self._last_update_times:
            self._last_update_times[data_type] = 0
            self._logger.debug(f"Throttling für {data_type} zurückgesetzt")
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt den Status des Update-Managers zurück"""
        return {
            'running': self._running,
            'queue_size': self._update_queue.qsize(),
            'cached_types': list(self._last_updates.keys()),
            'last_updates': {
                dt: datetime.fromtimestamp(t).isoformat() 
                for dt, t in self._last_update_times.items()
            },
            'intervals': self._update_intervals.copy()
        }


class DataUpdateMixin:
    """
    Mixin-Klasse für Komponenten, die Daten-Updates benötigen.
    Bietet eine einfache Integration mit dem DataUpdateManager.
    """
    
    def __init__(self):
        self._update_manager = DataUpdateManager()
    
    def schedule_data_update(self, data_type: str, data: Dict[str, Any],
                           priority: UpdatePriority = UpdatePriority.NORMAL):
        """Plant ein Daten-Update"""
        self._update_manager.schedule_update(
            data_type=data_type,
            data=data,
            priority=priority,
            source=self.__class__.__name__
        )
    
    def register_data_callback(self, data_type: str, callback: Callable):
        """Registriert einen Callback für Updates"""
        self._update_manager.register_callback(data_type, callback)


# Convenience-Funktionen
def get_update_manager() -> DataUpdateManager:
    """Gibt die globale DataUpdateManager-Instanz zurück"""
    return DataUpdateManager()


# Beispiel-Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    manager = DataUpdateManager()
    manager.start()
    
    # Callback registrieren
    def on_balance_update(data):
        print(f"💰 Balance Update: {data}")
    
    def on_position_update(data):
        print(f"📊 Position Update: {data}")
    
    manager.register_callback("balance", on_balance_update)
    manager.register_callback("positions", on_position_update)
    
    # Updates planen
    manager.schedule_update("balance", {"balance": 10000, "equity": 10500})
    manager.schedule_update("positions", {"count": 3, "symbols": ["EURUSD", "GBPUSD"]})
    
    # Warten auf Verarbeitung
    time.sleep(0.5)
    
    # Status abfragen
    print("\n--- Manager Status ---")
    status = manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    manager.stop()
