#!/usr/bin/env python3
"""
FinGPT Performance Optimizer Module
Performance-Monitoring und Optimierungswerkzeuge
"""

import time
import threading
import psutil
import functools
from typing import Dict, Any, Callable, Optional
from collections import defaultdict, deque

class PerformanceMetrics:
    """Performance-Metriken Sammlung"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.function_times = defaultdict(list)
        self.memory_usage = deque(maxlen=max_history)
        self.cpu_usage = deque(maxlen=max_history)
        self.start_time = time.time()
        
    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None):
        """Metric aufzeichnen"""
        if timestamp is None:
            timestamp = time.time()
        self.metrics[name].append((timestamp, value))
    
    def record_function_time(self, func_name: str, duration: float):
        """Funktionslaufzeit aufzeichnen"""
        self.function_times[func_name].append(duration)
        # Nur letzte 1000 Einträge behalten
        if len(self.function_times[func_name]) > 1000:
            self.function_times[func_name] = self.function_times[func_name][-1000:]
    
    def record_system_metrics(self):
        """System-Metriken aufzeichnen"""
        try:
            # Memory Usage
            memory = psutil.virtual_memory()
            self.memory_usage.append((time.time(), memory.percent))
            
            # CPU Usage
            cpu = psutil.cpu_percent(interval=0.1)
            self.cpu_usage.append((time.time(), cpu))
        except Exception:
            pass  # Fehler bei Metrikerfassung ignorieren
    
    def get_function_stats(self, func_name: str) -> Dict[str, float]:
        """Statistiken für eine Funktion"""
        times = self.function_times.get(func_name, [])
        if not times:
            return {}
        
        return {
            "count": len(times),
            "total": sum(times),
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "last": times[-1]
        }
    
    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Statistiken für eine Metric"""
        values = [v for _, v in self.metrics.get(name, [])]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "total": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "last": values[-1]
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Zusammenfassung aller Metriken"""
        return {
            "uptime": time.time() - self.start_time,
            "function_stats": {name: self.get_function_stats(name) for name in self.function_times},
            "metric_stats": {name: self.get_metric_stats(name) for name in self.metrics},
            "system_stats": {
                "memory": self.get_metric_stats("memory_usage"),
                "cpu": self.get_metric_stats("cpu_usage")
            }
        }

class PerformanceMonitor:
    """Performance Monitor mit automatischer Überwachung"""
    
    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 5.0  # Sekunden
        
    def start_monitoring(self):
        """Startet die Performance-Überwachung"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stoppt die Performance-Überwachung"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Überwachungsschleife"""
        while self.monitoring:
            try:
                self.metrics.record_system_metrics()
                time.sleep(self.monitor_interval)
            except Exception:
                break

def performance_monitor(func_name: Optional[str] = None):
    """
    Decorator für Performance-Monitoring von Funktionen
    
    Args:
        func_name: Optionaler Name für die Funktion
    """
    def decorator(func: Callable):
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Globale Metriken verwenden (wenn verfügbar)
                if hasattr(wrapper, '_metrics'):
                    wrapper._metrics.record_function_time(name, duration)
        return wrapper
    return decorator

class CacheManager:
    """Intelligenter Cache für Performance-Optimierung"""
    
    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Holt Wert aus Cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # TTL prüfen
            if time.time() - self.access_times[key] > self.ttl:
                self._remove(key)
                return None
            
            # Access time aktualisieren
            self.access_times[key] = time.time()
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Setzt Wert im Cache"""
        with self.lock:
            # Cache size prüfen
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def clear(self):
        """Leert den Cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def _remove(self, key: str):
        """Entfernt Eintrag aus Cache"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def _evict_lru(self):
        """Entfernt least recently used Eintrag"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times, key=self.access_times.get)
        self._remove(lru_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Cache-Statistiken"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
            }

def cached(ttl: float = 300.0, max_size: int = 1000):
    """
    Decorator für Caching von Funktionen
    
    Args:
        ttl: Time-to-live in Sekunden
        max_size: Maximale Cache-Größe
    """
    def decorator(func: Callable):
        cache = CacheManager(max_size=max_size, ttl=ttl)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Cache-Key aus Argumenten erstellen
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Versuch aus Cache zu holen
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Funktion ausführen und Ergebnis cachen
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        # Cache-Stats hinzufügen
        wrapper.cache_stats = cache.get_stats
        wrapper.cache_clear = cache.clear
        
        return wrapper
    return decorator

class AsyncExecutor:
    """Asynchroner Executor für I/O-Operationen"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = None
        self.pending_tasks = {}
        
    def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """Reicht eine Aufgabe asynchron ein"""
        import concurrent.futures
        
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        task_id = f"task_{int(time.time() * 1000000)}"
        future = self.executor.submit(func, *args, **kwargs)
        self.pending_tasks[task_id] = future
        
        return task_id
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Holt Ergebnis einer Aufgabe"""
        if task_id not in self.pending_tasks:
            raise ValueError(f"Task {task_id} nicht gefunden")
        
        future = self.pending_tasks.pop(task_id)
        return future.result(timeout=timeout)
    
    def shutdown(self, wait: bool = True):
        """Fährt den Executor herunter"""
        if self.executor:
            self.executor.shutdown(wait=wait)

class ResourceLimiter:
    """Resource Limiter zur Vermeidung von Overload"""
    
    def __init__(self, max_concurrent: int = 10, rate_limit: float = 1.0):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.semaphore = threading.Semaphore(max_concurrent)
        self.last_request_time = 0.0
        self.lock = threading.Lock()
    
    def acquire(self):
        """Acquire Resource"""
        # Rate Limiting
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.rate_limit
            
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
            
            self.last_request_time = time.time()
        
        # Concurrency Limit
        self.semaphore.acquire()
    
    def release(self):
        """Release Resource"""
        self.semaphore.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

def rate_limited(max_calls: int, time_window: float):
    """
    Decorator für Rate Limiting
    
    Args:
        max_calls: Maximale Aufrufe im Zeitfenster
        time_window: Zeitfenster in Sekunden
    """
    def decorator(func: Callable):
        calls = deque()
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()
                
                # Alte Aufrufe entfernen
                while calls and calls[0] <= current_time - time_window:
                    calls.popleft()
                
                # Rate Limit prüfen
                if len(calls) >= max_calls:
                    sleep_time = time_window - (current_time - calls[0])
                    time.sleep(sleep_time)
                    current_time = time.time()
                
                calls.append(current_time)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Globale Performance-Instanzen
global_metrics = PerformanceMetrics()
global_monitor = PerformanceMonitor(global_metrics)

# Performance-Monitoring automatisch starten
global_monitor.start_monitoring()

def get_performance_report() -> Dict[str, Any]:
    """Gibt aktuellen Performance-Report zurück"""
    return global_metrics.get_summary()

def optimize_imports():
    """Optimiert Import-Struktur"""
    import importlib
    
    # Häufig genutzte Module vorladen
    common_modules = ['json', 'time', 'datetime', 'threading', 'logging']
    for module in common_modules:
        try:
            importlib.import_module(module)
        except ImportError:
            pass

def cleanup_resources():
    """Räumt Ressourcen auf"""
    global_monitor.stop_monitoring()
    
    # Cache leeren
    for obj in globals().values():
        if hasattr(obj, 'cache_clear'):
            try:
                obj.cache_clear()
            except Exception:
                pass

# Automatische Cleanup bei Programmende
import atexit
atexit.register(cleanup_resources)