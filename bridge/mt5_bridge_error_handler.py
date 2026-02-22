#!/usr/bin/env python3
"""
MT5 Bridge Error Handling & Recovery
Robuste Fehlerbehandlung und automatische Wiederherstellung
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

class ErrorSeverity(Enum):
    """Fehler-Schweregrade"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ErrorType(Enum):
    """Fehler-Typen"""
    CONNECTION_ERROR = "CONNECTION_ERROR"
    DATA_ERROR = "DATA_ERROR"
    TRANSMISSION_ERROR = "TRANSMISSION_ERROR"
    MT5_ERROR = "MT5_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

@dataclass
class ErrorInfo:
    """Fehler-Informationen"""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    retry_count: int = 0

class RecoveryAction(Enum):
    """Wiederherstellungs-Aktionen"""
    RETRY = "RETRY"
    RECONNECT = "RECONNECT"
    RESET = "RESET"
    FALLBACK = "FALLBACK"
    ESCALATE = "ESCALATE"
    IGNORE = "IGNORE"

@dataclass
class RecoveryStrategy:
    """Wiederherstellungs-Strategie"""
    error_type: ErrorType
    max_retries: int
    retry_delay: float
    backoff_multiplier: float
    actions: List[RecoveryAction]
    fallback_function: Optional[Callable] = None

class MT5BridgeErrorHandler:
    """Fehlerbehandlung für MT5 Bridge"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Fehler-Speicher
        self.error_history: List[ErrorInfo] = []
        self.active_errors: Dict[str, ErrorInfo] = {}
        
        # Wiederherstellungs-Strategien
        self.recovery_strategies = self._setup_recovery_strategies()
        
        # Statistiken
        self.stats = {
            'total_errors': 0,
            'resolved_errors': 0,
            'escalated_errors': 0,
            'last_error_time': None,
            'uptime_percentage': 100.0
        }
        
        # Health-Status
        self.health_status = {
            'is_healthy': True,
            'last_check': datetime.now(),
            'consecutive_errors': 0,
            'max_consecutive_errors': 5
        }
        
        # Threads
        self.monitor_thread = None
        self.recovery_thread = None
        self.is_running = False
        
        # Callbacks
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Richtet Logging ein"""
        logger = logging.getLogger('MT5BridgeErrorHandler')
        logger.setLevel(logging.INFO)
        
        # File Handler
        fh = logging.FileHandler('mt5_bridge_errors.log')
        fh.setLevel(logging.INFO)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def _setup_recovery_strategies(self) -> Dict[ErrorType, RecoveryStrategy]:
        """Richtet Wiederherstellungs-Strategien ein"""
        return {
            ErrorType.CONNECTION_ERROR: RecoveryStrategy(
                error_type=ErrorType.CONNECTION_ERROR,
                max_retries=5,
                retry_delay=2.0,
                backoff_multiplier=2.0,
                actions=[RecoveryAction.RETRY, RecoveryAction.RECONNECT, RecoveryAction.FALLBACK]
            ),
            ErrorType.DATA_ERROR: RecoveryStrategy(
                error_type=ErrorType.DATA_ERROR,
                max_retries=3,
                retry_delay=1.0,
                backoff_multiplier=1.5,
                actions=[RecoveryAction.RETRY, RecoveryAction.IGNORE]
            ),
            ErrorType.TRANSMISSION_ERROR: RecoveryStrategy(
                error_type=ErrorType.TRANSMISSION_ERROR,
                max_retries=3,
                retry_delay=1.5,
                backoff_multiplier=2.0,
                actions=[RecoveryAction.RETRY, RecoveryAction.RESET, RecoveryAction.FALLBACK]
            ),
            ErrorType.MT5_ERROR: RecoveryStrategy(
                error_type=ErrorType.MT5_ERROR,
                max_retries=3,
                retry_delay=3.0,
                backoff_multiplier=2.0,
                actions=[RecoveryAction.RETRY, RecoveryAction.RECONNECT, RecoveryAction.ESCALATE]
            ),
            ErrorType.NETWORK_ERROR: RecoveryStrategy(
                error_type=ErrorType.NETWORK_ERROR,
                max_retries=5,
                retry_delay=2.0,
                backoff_multiplier=1.5,
                actions=[RecoveryAction.RETRY, RecoveryAction.RECONNECT, RecoveryAction.FALLBACK]
            ),
            ErrorType.VALIDATION_ERROR: RecoveryStrategy(
                error_type=ErrorType.VALIDATION_ERROR,
                max_retries=1,
                retry_delay=0.5,
                backoff_multiplier=1.0,
                actions=[RecoveryAction.IGNORE, RecoveryAction.ESCALATE]
            ),
            ErrorType.SYSTEM_ERROR: RecoveryStrategy(
                error_type=ErrorType.SYSTEM_ERROR,
                max_retries=2,
                retry_delay=5.0,
                backoff_multiplier=3.0,
                actions=[RecoveryAction.RESET, RecoveryAction.ESCALATE]
            )
        }
    
    def start(self):
        """Startet den Error Handler"""
        self.is_running = True
        
        # Monitor-Thread starten
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Recovery-Thread starten
        self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self.recovery_thread.start()
        
        self.logger.info("MT5 Bridge Error Handler gestartet")
    
    def stop(self):
        """Stoppt den Error Handler"""
        self.is_running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.recovery_thread:
            self.recovery_thread.join(timeout=5)
        
        self.logger.info("MT5 Bridge Error Handler gestoppt")
    
    def handle_error(self, error_type: ErrorType, message: str, 
                    context: Dict[str, Any] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    stack_trace: str = None) -> str:
        """Behandelt einen Fehler"""
        error_id = self._generate_error_id()
        
        error_info = ErrorInfo(
            error_id=error_id,
            error_type=error_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            context=context or {},
            stack_trace=stack_trace
        )
        
        # Fehler speichern
        self.error_history.append(error_info)
        self.active_errors[error_id] = error_info
        
        # Statistiken aktualisieren
        self.stats['total_errors'] += 1
        self.stats['last_error_time'] = datetime.now()
        
        # Health-Status aktualisieren
        self._update_health_status(error_info)
        
        # Loggen
        self._log_error(error_info)
        
        # Callbacks aufrufen
        self._call_error_callbacks(error_info)
        
        # Automatische Wiederherstellung einleiten
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._initiate_recovery(error_info)
        
        return error_id
    
    def resolve_error(self, error_id: str, resolution_message: str = "Resolved"):
        """Löst einen Fehler auf"""
        if error_id in self.active_errors:
            error_info = self.active_errors[error_id]
            error_info.resolved = True
            error_info.resolution_time = datetime.now()
            
            # Aus aktiven Fehlern entfernen
            del self.active_errors[error_id]
            
            # Statistiken aktualisieren
            self.stats['resolved_errors'] += 1
            
            self.logger.info(f"Fehler {error_id} gelöst: {resolution_message}")
            
            # Health-Status aktualisieren
            self._update_health_status_on_resolution()
    
    def _generate_error_id(self) -> str:
        """Generiert eindeutige Fehler-ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _update_health_status(self, error_info: ErrorInfo):
        """Aktualisiert Health-Status"""
        self.health_status['consecutive_errors'] += 1
        
        # Bei kritischen Fehlern sofort als unhealthy markieren
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.health_status['is_healthy'] = False
        
        # Bei zu vielen konsekutiven Fehlern
        if self.health_status['consecutive_errors'] >= self.health_status['max_consecutive_errors']:
            self.health_status['is_healthy'] = False
    
    def _update_health_status_on_resolution(self):
        """Aktualisiert Health-Status bei Fehlerlösung"""
        self.health_status['consecutive_errors'] = max(0, self.health_status['consecutive_errors'] - 1)
        
        # Wenn keine aktiven Fehler mehr, als healthy markieren
        if len(self.active_errors) == 0 and self.health_status['consecutive_errors'] == 0:
            self.health_status['is_healthy'] = True
    
    def _log_error(self, error_info: ErrorInfo):
        """Loggt Fehler"""
        level_map = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        level = level_map.get(error_info.severity, logging.WARNING)
        
        message = f"[{error_info.error_type.value}] {error_info.message}"
        if error_info.context:
            message += f" | Context: {error_info.context}"
        
        self.logger.log(level, message)
    
    def _call_error_callbacks(self, error_info: ErrorInfo):
        """Ruft Error-Callbacks auf"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Fehler in Error-Callback: {e}")
    
    def _initiate_recovery(self, error_info: ErrorInfo):
        """Leitet Wiederherstellung ein"""
        strategy = self.recovery_strategies.get(error_info.error_type)
        if not strategy:
            self.logger.warning(f"Keine Wiederherstellungs-Strategie für {error_info.error_type}")
            return
        
        self.logger.info(f"Leite Wiederherstellung ein für Fehler {error_info.error_id}")
        
        # Recovery in separatem Thread ausführen
        threading.Thread(
            target=self._execute_recovery,
            args=(error_info, strategy),
            daemon=True
        ).start()
    
    def _execute_recovery(self, error_info: ErrorInfo, strategy: RecoveryStrategy):
        """Führt Wiederherstellung aus"""
        retry_count = 0
        delay = strategy.retry_delay
        
        while retry_count < strategy.max_retries and not error_info.resolved:
            try:
                self.logger.info(f"Recovery Versuch {retry_count + 1}/{strategy.max_retries} für Fehler {error_info.error_id}")
                
                # Aktionen ausführen
                for action in strategy.actions:
                    if self._execute_recovery_action(action, error_info, strategy):
                        # Erfolgreich - Fehler als gelöst markieren
                        self.resolve_error(error_info.error_id, f"Recovered via {action.value}")
                        return
                
                # Warten vor nächstem Versuch
                time.sleep(delay)
                delay *= strategy.backoff_multiplier
                retry_count += 1
                
                error_info.retry_count = retry_count
                
            except Exception as e:
                self.logger.error(f"Recovery-Fehler: {e}")
                retry_count += 1
                time.sleep(delay)
                delay *= strategy.backoff_multiplier
        
        # Alle Versuche fehlgeschlagen
        self.logger.error(f"Recovery fehlgeschlagen für Fehler {error_info.error_id}")
        
        # Escalate
        if RecoveryAction.ESCALATE in strategy.actions:
            self._escalate_error(error_info)
    
    def _execute_recovery_action(self, action: RecoveryAction, error_info: ErrorInfo, 
                                strategy: RecoveryStrategy) -> bool:
        """Führt einzelne Recovery-Aktion aus"""
        try:
            if action == RecoveryAction.RETRY:
                return self._retry_operation(error_info)
            elif action == RecoveryAction.RECONNECT:
                return self._reconnect_service(error_info)
            elif action == RecoveryAction.RESET:
                return self._reset_service(error_info)
            elif action == RecoveryAction.FALLBACK:
                return self._activate_fallback(error_info, strategy)
            elif action == RecoveryAction.ESCALATE:
                self._escalate_error(error_info)
                return True
            elif action == RecoveryAction.IGNORE:
                self.resolve_error(error_info.error_id, "Ignored per strategy")
                return True
            
        except Exception as e:
            self.logger.error(f"Fehler bei Recovery-Aktion {action.value}: {e}")
            return False
        
        return False
    
    def _retry_operation(self, error_info: ErrorInfo) -> bool:
        """Wiederholt Operation"""
        # Implementierung hängt vom Kontext ab
        self.logger.info(f"Retry Operation für {error_info.error_id}")
        return True  # Placeholder
    
    def _reconnect_service(self, error_info: ErrorInfo) -> bool:
        """Verbindung wiederherstellen"""
        self.logger.info(f"Reconnect Service für {error_info.error_id}")
        
        # Implementierung für spezifische Services
        if error_info.error_type == ErrorType.MT5_ERROR:
            return self._reconnect_mt5()
        elif error_info.error_type == ErrorType.NETWORK_ERROR:
            return self._reconnect_network()
        
        return True
    
    def _reset_service(self, error_info: ErrorInfo) -> bool:
        """Setzt Service zurück"""
        self.logger.info(f"Reset Service für {error_info.error_id}")
        return True  # Placeholder
    
    def _activate_fallback(self, error_info: ErrorInfo, strategy: RecoveryStrategy) -> bool:
        """Aktiviert Fallback-Lösung"""
        self.logger.info(f"Activate Fallback für {error_info.error_id}")
        
        if strategy.fallback_function:
            try:
                strategy.fallback_function(error_info)
                return True
            except Exception as e:
                self.logger.error(f"Fallback-Funktion fehlgeschlagen: {e}")
        
        return False
    
    def _escalate_error(self, error_info: ErrorInfo):
        """Eskaliert Fehler"""
        self.stats['escalated_errors'] += 1
        self.logger.critical(f"Fehler eskaliert: {error_info.error_id} - {error_info.message}")
        
        # Hier könnten Benachrichtigungen, E-Mails, etc. gesendet werden
        self._send_escalation_notification(error_info)
    
    def _send_escalation_notification(self, error_info: ErrorInfo):
        """Sendet Eskalations-Benachrichtigung"""
        # Implementierung für Benachrichtigungen
        pass
    
    def _reconnect_mt5(self) -> bool:
        """Stellt MT5-Verbindung wieder her"""
        try:
            import MetaTrader5 as mt5
            
            # MT5 neu initialisieren
            mt5.shutdown()
            time.sleep(1)
            
            if mt5.initialize():
                self.logger.info("MT5-Verbindung wiederhergestellt")
                return True
            else:
                self.logger.error("MT5-Verbindungswiederherstellung fehlgeschlagen")
                return False
                
        except Exception as e:
            self.logger.error(f"MT5-Reconnect Fehler: {e}")
            return False
    
    def _reconnect_network(self) -> bool:
        """Stellt Netzwerkverbindung wieder her"""
        # Implementierung für Netzwerk-Reconnect
        self.logger.info("Netzwerkverbindung wird wiederhergestellt")
        return True
    
    def _monitor_loop(self):
        """Überwachungsschleife"""
        while self.is_running:
            try:
                self._perform_health_check()
                self._cleanup_old_errors()
                self._update_statistics()
                time.sleep(30)  # Alle 30 Sekunden
                
            except Exception as e:
                self.logger.error(f"Fehler in Monitor-Schleife: {e}")
                time.sleep(5)
    
    def _recovery_loop(self):
        """Wiederherstellungsschleife"""
        while self.is_running:
            try:
                # Prüfen ob unbehandelte Fehler vorhanden sind
                for error_id, error_info in list(self.active_errors.items()):
                    if not error_info.resolved and error_info.retry_count == 0:
                        strategy = self.recovery_strategies.get(error_info.error_type)
                        if strategy and error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                            self._execute_recovery(error_info, strategy)
                
                time.sleep(10)  # Alle 10 Sekunden prüfen
                
            except Exception as e:
                self.logger.error(f"Fehler in Recovery-Schleife: {e}")
                time.sleep(5)
    
    def _perform_health_check(self):
        """Führt Health-Check durch"""
        self.health_status['last_check'] = datetime.now()
        
        # Prüfen ob zu viele aktive Fehler
        if len(self.active_errors) > 10:
            self.health_status['is_healthy'] = False
        
        # Uptime berechnen
        if self.stats['total_errors'] > 0:
            resolved_rate = self.stats['resolved_errors'] / self.stats['total_errors']
            self.stats['uptime_percentage'] = resolved_rate * 100
    
    def _cleanup_old_errors(self):
        """Räumt alte Fehler auf"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Alte Fehler aus History entfernen
        self.error_history = [
            error for error in self.error_history 
            if error.timestamp > cutoff_time
        ]
        
        # Aufgelöste Fehler aus aktiven Fehlern entfernen
        resolved_errors = [
            error_id for error_id, error in self.active_errors.items()
            if error.resolved and error.resolution_time and 
               error.resolution_time < cutoff_time
        ]
        
        for error_id in resolved_errors:
            del self.active_errors[error_id]
    
    def _update_statistics(self):
        """Aktualisiert Statistiken"""
        # Berechne Error-Rate
        if self.stats['last_error_time']:
            time_since_last_error = datetime.now() - self.stats['last_error_time']
            if time_since_last_error.total_seconds() > 300:  # 5 Minuten
                self.health_status['consecutive_errors'] = 0
    
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """Fügt Error-Callback hinzu"""
        self.error_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt Error-Handler-Status zurück"""
        return {
            'is_healthy': self.health_status['is_healthy'],
            'active_errors': len(self.active_errors),
            'total_errors': self.stats['total_errors'],
            'resolved_errors': self.stats['resolved_errors'],
            'escalated_errors': self.stats['escalated_errors'],
            'uptime_percentage': self.stats['uptime_percentage'],
            'consecutive_errors': self.health_status['consecutive_errors'],
            'last_error_time': self.stats['last_error_time'].isoformat() if self.stats['last_error_time'] else None,
            'recent_errors': [
                {
                    'error_id': error.error_id,
                    'type': error.error_type.value,
                    'severity': error.severity.value,
                    'message': error.message,
                    'timestamp': error.timestamp.isoformat()
                }
                for error in self.error_history[-10:]
            ]
        }
    
    def get_error_report(self) -> str:
        """Gibt detaillierten Fehler-Bericht zurück"""
        report = "MT5 Bridge Error Report\n"
        report += "=" * 40 + "\n\n"
        
        # Zusammenfassung
        report += f"Total Errors: {self.stats['total_errors']}\n"
        report += f"Resolved Errors: {self.stats['resolved_errors']}\n"
        report += f"Active Errors: {len(self.active_errors)}\n"
        report += f"Escalated Errors: {self.stats['escalated_errors']}\n"
        report += f"Uptime Percentage: {self.stats['uptime_percentage']:.1f}%\n\n"
        
        # Aktive Fehler
        if self.active_errors:
            report += "Active Errors:\n"
            for error_id, error in self.active_errors.items():
                report += f"  {error_id}: {error.error_type.value} - {error.message}\n"
            report += "\n"
        
        # Jüngste Fehler
        if self.error_history:
            report += "Recent Errors:\n"
            for error in self.error_history[-5:]:
                report += f"  {error.timestamp}: {error.error_type.value} - {error.message}\n"
        
        return report

# Globale Error-Handler-Instanz
_global_error_handler = None

def get_error_handler() -> MT5BridgeErrorHandler:
    """Gibt globale Error-Handler-Instanz zurück"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = MT5BridgeErrorHandler()
        _global_error_handler.start()
    return _global_error_handler

def handle_error(error_type: ErrorType, message: str, context: Dict[str, Any] = None, 
                severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> str:
    """Convenience-Funktion für Fehlerbehandlung"""
    return get_error_handler().handle_error(error_type, message, context, severity)

def resolve_error(error_id: str, resolution_message: str = "Resolved"):
    """Convenience-Funktion für Fehlerlösung"""
    get_error_handler().resolve_error(error_id, resolution_message)

if __name__ == "__main__":
    # Test-Modus
    error_handler = MT5BridgeErrorHandler()
    error_handler.start()
    
    try:
        print("MT5 Bridge Error Handler - Test-Modus")
        print("Drücke Ctrl+C zum Beenden")
        
        # Test-Fehler erzeugen
        error_id = error_handler.handle_error(
            ErrorType.CONNECTION_ERROR,
            "Test-Verbindungsfehler",
            {"component": "test", "retry_count": 1},
            ErrorSeverity.MEDIUM
        )
        
        print(f"Test-Fehler erzeugt: {error_id}")
        
        while True:
            time.sleep(1)
            status = error_handler.get_status()
            print(f"Status: {status['active_errors']} aktive Fehler")
            
    except KeyboardInterrupt:
        print("Beende Error Handler...")
    finally:
        error_handler.stop()