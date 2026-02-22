#!/usr/bin/env python3
"""
FinGPT Exception Handler Module
Spezialisierte Exception-Klassen und robuste Fehlerbehandlung
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime
from enum import Enum

class FinGPTError(Exception):
    """Base Exception für alle FinGPT Fehler"""
    def __init__(self, message: str, error_code: str = "FG_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()

class MT5ConnectionError(FinGPTError):
    """MT5 Verbindungsfehler"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MT5_CONN_ERROR", details)

class OllamaConnectionError(FinGPTError):
    """Ollama Verbindungsfehler"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "OLLAMA_CONN_ERROR", details)

class TradingError(FinGPTError):
    """Trading-spezifische Fehler"""
    def __init__(self, message: str, symbol: str = "", action: str = "", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"symbol": symbol, "action": action})
        super().__init__(message, "TRADING_ERROR", details)

class RiskManagementError(FinGPTError):
    """Risk Management Fehler"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RISK_ERROR", details)

class ValidationError(FinGPTError):
    """Validierungsfehler"""
    def __init__(self, message: str, field: str = "", value: Any = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"field": field, "value": value})
        super().__init__(message, "VALIDATION_ERROR", details)

class ConfigurationError(FinGPTError):
    """Konfigurationsfehler"""
    def __init__(self, message: str, config_key: str = "", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"config_key": config_key})
        super().__init__(message, "CONFIG_ERROR", details)

class DataError(FinGPTError):
    """Daten-bezogene Fehler"""
    def __init__(self, message: str, data_source: str = "", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"data_source": data_source})
        super().__init__(message, "DATA_ERROR", details)

class ErrorSeverity(Enum):
    """Fehler-Schweregrade"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ErrorHandler:
    """Zentraler Error Handler für FinGPT"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
        self.max_history = 1000
        
    def handle_exception(self, exception: Exception, context: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> Dict[str, Any]:
        """
        Zentrale Exception-Behandlung
        
        Args:
            exception: Die aufgetretene Exception
            context: Kontextinformationen
            severity: Schweregrad des Fehlers
            
        Returns:
            Dict mit Fehlerinformationen
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "context": context,
            "severity": severity.value,
            "traceback": traceback.format_exc()
        }
        
        # Spezielle FinGPT Exceptions behandeln
        if isinstance(exception, FinGPTError):
            error_info.update({
                "error_code": exception.error_code,
                "details": exception.details
            })
            
        # Fehler zählen
        error_key = f"{type(exception).__name__}_{context}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # In History speichern
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Logging
        self._log_error(error_info, severity)
        
        # Bei kritischen Fehlern spezielle Behandlung
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error_info)
        
        return error_info
    
    def _log_error(self, error_info: Dict[str, Any], severity: ErrorSeverity):
        """Fehler entsprechend dem Schweregrad loggen"""
        log_message = f"[{error_info['error_code'] if 'error_code' in error_info else 'ERROR'}] {error_info['message']}"
        
        if error_info['context']:
            log_message += f" | Context: {error_info['context']}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _handle_critical_error(self, error_info: Dict[str, Any]):
        """Spezielle Behandlung für kritische Fehler"""
        # Hier könnten Notfall-Maßnahmen ergriffen werden
        # z.B. Trading stoppen, Benachrichtigungen senden, etc.
        self.logger.critical("🚨 KRITISCHER FEHLER - Notfall-Prozeduren aktiviert!")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Zusammenfassung der Fehlerstatistik"""
        return {
            "total_errors": len(self.error_history),
            "error_counts": dict(sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)),
            "recent_errors": self.error_history[-10:],
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }
    
    def reset_error_counts(self):
        """Fehler-Zähler zurücksetzen"""
        self.error_counts.clear()
        self.error_history.clear()

def safe_execute(
    error_handler: ErrorHandler,
    default_return: Any = None,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = False
):
    """
    Decorator für sichere Ausführung von Funktionen
    
    Args:
        error_handler: ErrorHandler Instanz
        default_return: Rückgabewert bei Fehler
        context: Kontext für Fehler
        severity: Schweregrad bei Fehler
        reraise: Exception neu auslösen
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_context = f"{context}.{func.__name__}" if context else func.__name__
                error_handler.handle_exception(e, func_context, severity)
                
                if reraise:
                    raise
                    
                return default_return
        return wrapper
    return decorator

def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    error_handler: Optional[ErrorHandler] = None
):
    """
    Decorator für Retry-Logik bei bestimmten Exceptions
    
    Args:
        max_retries: Maximale Wiederholungsversuche
        delay: Initiale Verzögerung
        backoff: Backoff-Faktor
        exceptions: Exception-Typen für Retry
        error_handler: Optionaler ErrorHandler
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        if error_handler:
                            error_handler.handle_exception(e, f"{func.__name__}_retry_failed", ErrorSeverity.HIGH)
                        raise
                    
                    if error_handler:
                        error_handler.handle_exception(e, f"{func.__name__}_retry_{attempt}", ErrorSeverity.LOW)
                    
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit Breaker Pattern für resilienten Code"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, error_handler: Optional[ErrorHandler] = None):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.error_handler = error_handler
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    # Include error code in message for test detection
                    raise FinGPTError("CIRCUIT_BREAKER_OPEN: Circuit Breaker ist OPEN", "CIRCUIT_BREAKER_OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                if self.error_handler:
                    self.error_handler.handle_exception(e, f"circuit_breaker_{func.__name__}", ErrorSeverity.MEDIUM)
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Prüft ob Circuit Breaker zurückgesetzt werden sollte"""
        import time
        return time.time() - self.last_failure_time > self.timeout
    
    def _on_success(self):
        """Bei erfolgreicher Ausführung"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Bei fehlgeschlagener Ausführung"""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Globale ErrorHandler Instanz
global_error_handler = ErrorHandler()

# Convenience Decorators
def safe_execute_with_default(default_return: Any = None, context: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Convenience Decorator mit globalem ErrorHandler"""
    return safe_execute(global_error_handler, default_return, context, severity)

def retry_with_circuit_breaker(max_retries: int = 3, delay: float = 1.0, failure_threshold: int = 5):
    """Convenience Decorator mit Retry und Circuit Breaker"""
    def decorator(func: Callable):
        circuit_breaker = CircuitBreaker(failure_threshold=failure_threshold, error_handler=global_error_handler)
        retry_decorator = retry_on_exception(max_retries, delay, error_handler=global_error_handler)
        return circuit_breaker(retry_decorator(func))
    return decorator