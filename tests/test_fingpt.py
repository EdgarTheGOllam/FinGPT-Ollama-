#!/usr/bin/env python3
"""
FinGPT Unit Tests
Umfassende Test-Suite für alle FinGPT Komponenten
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import time

# Pfad zum Projektverzeichnis hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import der zu testenden Module
try:
    from core.input_validator import InputValidator, SafeInput, ValidationResult
    from core.exception_handler import (
        FinGPTError, ErrorHandler, ErrorSeverity, safe_execute, 
        retry_on_exception, CircuitBreaker, safe_execute_with_default,
        global_error_handler
    )
    from core.performance_optimizer import (
        PerformanceMetrics, CacheManager, ResourceLimiter, 
        performance_monitor, cached
    )
    ENHANCED_MODULES = True
except ImportError as e:
    print(f"Warning: Enhanced modules nicht verfügbar: {e}")
    ENHANCED_MODULES = False

class TestInputValidator(unittest.TestCase):
    """Test-Klasse für InputValidator"""
    
    def setUp(self):
        self.validator = InputValidator()
    
    def test_validate_symbol_valid(self):
        """Test gültiger Symbole"""
        valid_symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        for symbol in valid_symbols:
            result = InputValidator.validate_symbol(symbol)
            self.assertTrue(result.is_valid, f"Symbol {symbol} sollte gültig sein")
            self.assertEqual(result.value, symbol.upper())
            self.assertTrue(result.sanitized)
    
    def test_validate_symbol_invalid(self):
        """Test ungültiger Symbole"""
        invalid_symbols = ["EU", "EURUS", "eurusd", "EURUSD1", "EUR-USD", "", None]
        for symbol in invalid_symbols:
            result = InputValidator.validate_symbol(symbol)
            self.assertFalse(result.is_valid, f"Symbol {symbol} sollte ungültig sein")
            self.assertIsNotNone(result.error_message)
    
    def test_validate_action_valid(self):
        """Test gültiger Aktionen"""
        valid_actions = ["BUY", "SELL", "buy", "sell"]
        for action in valid_actions:
            result = InputValidator.validate_action(action)
            self.assertTrue(result.is_valid, f"Aktion {action} sollte gültig sein")
            self.assertEqual(result.value, action.upper())
    
    def test_validate_action_invalid(self):
        """Test ungültiger Aktionen"""
        invalid_actions = ["HOLD", "EXIT", "", None, "BUYY", "SELLL"]
        for action in invalid_actions:
            result = InputValidator.validate_action(action)
            self.assertFalse(result.is_valid, f"Aktion {action} sollte ungültig sein")
    
    def test_validate_lot_size_valid(self):
        """Test gültiger Lot Sizes"""
        valid_lots = ["0.01", "0.1", "1.0", "0.05"]
        for lot in valid_lots:
            result = InputValidator.validate_lot_size(lot)
            self.assertTrue(result.is_valid, f"Lot Size {lot} sollte gültig sein")
            self.assertIsInstance(result.value, float)
    
    def test_validate_lot_size_invalid(self):
        """Test ungültiger Lot Sizes"""
        invalid_lots = ["0.001", "10.1", "-0.1", "abc", "", None]
        for lot in invalid_lots:
            result = InputValidator.validate_lot_size(lot)
            self.assertFalse(result.is_valid, f"Lot Size {lot} sollte ungültig sein")
    
    def test_validate_interval_valid(self):
        """Test gültiger Intervalle"""
        valid_intervals = ["10", "60", "300", "3600"]
        for interval in valid_intervals:
            result = InputValidator.validate_interval(interval)
            self.assertTrue(result.is_valid, f"Intervall {interval} sollte gültig sein")
            self.assertIsInstance(result.value, int)
    
    def test_validate_interval_invalid(self):
        """Test ungültiger Intervalle"""
        invalid_intervals = ["5", "4000", "-10", "abc", "", None]
        for interval in invalid_intervals:
            result = InputValidator.validate_interval(interval)
            self.assertFalse(result.is_valid, f"Intervall {interval} sollte ungültig sein")
    
    def test_validate_pairs_list_valid(self):
        """Test gültiger Paar-Listen"""
        valid_pairs = ["EURUSD", "EURUSD,GBPUSD", "EURUSD,GBPUSD,USDJPY"]
        for pairs in valid_pairs:
            result = InputValidator.validate_pairs_list(pairs)
            self.assertTrue(result.is_valid, f"Paar-Liste {pairs} sollte gültig sein")
            self.assertIsInstance(result.value, list)
    
    def test_validate_pairs_list_invalid(self):
        """Test ungültiger Paar-Listen"""
        invalid_pairs = ["EU", "EURUS,GBP", "EURUSD,GBPUSD,USDJPY,AUDUSD,CADUSD,NZDUSD,CHFUSD,JPYUSD,EURGBP,EURCHF", ""]
        for pairs in invalid_pairs:
            result = InputValidator.validate_pairs_list(pairs)
            self.assertFalse(result.is_valid, f"Paar-Liste {pairs} sollte ungültig sein")

@unittest.skipUnless(ENHANCED_MODULES, "Enhanced modules nicht verfügbar")
class TestExceptionHandler(unittest.TestCase):
    """Test-Klasse für Exception Handler"""
    
    def setUp(self):
        self.error_handler = ErrorHandler()
    
    def test_fin_gpt_error_creation(self):
        """Test Erstellung von FinGPTError"""
        error = FinGPTError("Test Fehler", "TEST_ERROR", {"key": "value"})
        self.assertEqual(error.message, "Test Fehler")
        self.assertEqual(error.error_code, "TEST_ERROR")
        self.assertEqual(error.details["key"], "value")
        self.assertIsInstance(error.timestamp, datetime)
    
    def test_error_handler_handle_exception(self):
        """Test Exception-Behandlung"""
        try:
            raise ValueError("Test ValueError")
        except Exception as e:
            error_info = self.error_handler.handle_exception(e, "test_context", ErrorSeverity.MEDIUM)
            
            self.assertEqual(error_info["exception_type"], "ValueError")
            self.assertEqual(error_info["message"], "Test ValueError")
            self.assertEqual(error_info["context"], "test_context")
            self.assertEqual(error_info["severity"], ErrorSeverity.MEDIUM.value)
    
    def test_safe_execute_decorator(self):
        """Test safe_execute Decorator"""
        @safe_execute(self.error_handler, default_return="default", context="test")
        def failing_function():
            raise ValueError("Test Fehler")
        
        result = failing_function()
        self.assertEqual(result, "default")
    
    def test_retry_on_exception_decorator(self):
        """Test retry_on_exception Decorator"""
        call_count = 0
        
        @retry_on_exception(max_retries=3, delay=0.1)
        def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = sometimes_failing()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_circuit_breaker(self):
        """Test Circuit Breaker"""
        call_count = 0
        
        @CircuitBreaker(failure_threshold=2, timeout=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        # Erste Aufrufe sollten durchgehen
        with self.assertRaises(ValueError):
            failing_function()
        with self.assertRaises(ValueError):
            failing_function()
        
        # Dritter Aufruf sollte Circuit Breaker auslösen
        with self.assertRaises(FinGPTError) as cm:
            failing_function()
        self.assertIn("CIRCUIT_BREAKER_OPEN", str(cm.exception))

@unittest.skipUnless(ENHANCED_MODULES, "Enhanced modules nicht verfügbar")
class TestPerformanceOptimizer(unittest.TestCase):
    """Test-Klasse für Performance Optimizer"""
    
    def setUp(self):
        self.metrics = PerformanceMetrics()
    
    def test_performance_metrics_record(self):
        """Test Metrik-Aufzeichnung"""
        self.metrics.record_metric("test_metric", 1.5)
        stats = self.metrics.get_metric_stats("test_metric")
        
        self.assertEqual(stats["count"], 1)
        self.assertEqual(stats["total"], 1.5)
        self.assertEqual(stats["avg"], 1.5)
        self.assertEqual(stats["min"], 1.5)
        self.assertEqual(stats["max"], 1.5)
    
    def test_performance_metrics_function_time(self):
        """Test Funktionszeit-Aufzeichnung"""
        self.metrics.record_function_time("test_function", 0.1)
        self.metrics.record_function_time("test_function", 0.2)
        
        stats = self.metrics.get_function_stats("test_function")
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["total"], 0.3)
        self.assertAlmostEqual(stats["avg"], 0.15)
    
    def test_cache_manager_basic_operations(self):
        """Test Cache Manager Grundoperationen"""
        cache = CacheManager(max_size=2, ttl=1.0)
        
        # Test set/get
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # Test nicht existierender Key
        self.assertIsNone(cache.get("nonexistent"))
        
        # Test TTL
        import time
        time.sleep(1.1)
        self.assertIsNone(cache.get("key1"))
    
    def test_cache_manager_eviction(self):
        """Test Cache Eviction"""
        cache = CacheManager(max_size=2, ttl=10.0)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Sollte key1 entfernen
        
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
    
    def test_resource_limiter(self):
        """Test Resource Limiter"""
        limiter = ResourceLimiter(max_concurrent=2, rate_limit=10.0)
        
        # Test acquire/release
        limiter.acquire()
        limiter.release()
        
        # Test context manager
        with limiter:
            self.assertTrue(True)  # Sollte ohne Fehler durchgehen
    
    def test_performance_monitor_decorator(self):
        """Test performance_monitor Decorator"""
        @performance_monitor("test_function")
        def test_function():
            time.sleep(0.01)
            return "result"
        
        result = test_function()
        self.assertEqual(result, "result")
    
    def test_cached_decorator(self):
        """Test cached Decorator"""
        call_count = 0
        
        @cached(ttl=1.0, max_size=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # Erster Aufruf
        result1 = expensive_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)
        
        # Zweiter Aufruf sollte gecached sein
        result2 = expensive_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1)  # Sollte nicht erhöht werden
        
        # Dritter Aufruf mit anderem Parameter
        result3 = expensive_function(10)
        self.assertEqual(result3, 20)
        self.assertEqual(call_count, 2)

class TestFinGPTIntegration(unittest.TestCase):
    """Integration-Tests für FinGPT"""
    
    def setUp(self):
        """Setup für Integration-Tests"""
        # Mock für externe Abhängigkeiten
        self.mt5_mock = Mock()
        self.requests_mock = Mock()
    
    @patch('sys.stdin')
    def test_safe_input_integration(self, mock_stdin):
        """Test SafeInput Integration"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        # Mock für input()
        mock_stdin.readline.return_value = "EURUSD\n"
        
        with patch('builtins.input', return_value="EURUSD"):
            result = SafeInput.get_symbol("Test: ")
            self.assertEqual(result, "EURUSD")
    
    def test_error_handling_integration(self):
        """Test Error Handling Integration"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        global_error_handler.reset_error_counts()
        
        @safe_execute_with_default(default_return="error_handled")
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        self.assertEqual(result, "error_handled")
        
        # Prüfen ob Fehler protokolliert wurde
        summary = global_error_handler.get_error_summary()
        self.assertEqual(summary["total_errors"], 1)

class TestEdgeCases(unittest.TestCase):
    """Test für Edge Cases und Grenzfälle"""
    
    def test_empty_and_none_inputs(self):
        """Test mit leeren und None Inputs"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        # Test verschiedene leere Inputs
        test_cases = ["", None, "   ", "\n", "\t"]
        
        for case in test_cases:
            symbol_result = InputValidator.validate_symbol(case)
            self.assertFalse(symbol_result.is_valid)
            
            action_result = InputValidator.validate_action(case)
            self.assertFalse(action_result.is_valid)
    
    def test_extreme_values(self):
        """Test mit extremen Werten"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        # Test extrem große Lot Sizes
        large_lot_result = InputValidator.validate_lot_size("999.99")
        self.assertFalse(large_lot_result.is_valid)
        
        # Test extrem kleine Lot Sizes
        small_lot_result = InputValidator.validate_lot_size("0.001")
        self.assertFalse(small_lot_result.is_valid)
        
        # Test extrem große Intervalle
        large_interval_result = InputValidator.validate_interval("99999")
        self.assertFalse(large_interval_result.is_valid)
    
    def test_unicode_and_special_characters(self):
        """Test mit Unicode und Sonderzeichen"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        # Test mit Unicode-Zeichen
        unicode_inputs = ["€URUSD", "£GBPUSD", "¥USDJPY", "EURUSD€"]
        
        for case in unicode_inputs:
            result = InputValidator.validate_symbol(case)
            self.assertFalse(result.is_valid)
    
    def test_concurrent_access(self):
        """Test für nebenläufigen Zugriff"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        import threading
        import time
        
        cache = CacheManager(max_size=100, ttl=10.0)
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    cache.set(key, value)
                    time.sleep(0.001)  # Kurze Pause
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Thread {thread_id}: Expected {value}, got {retrieved}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Mehrere Threads starten
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Warten auf Abschluss
        for thread in threads:
            thread.join()
        
        # Prüfen ob keine Fehler auftraten
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")

def create_test_suite():
    """Erstellt die komplette Test-Suite"""
    suite = unittest.TestSuite()
    
    # Test-Klassen hinzufügen
    test_classes = [
        TestInputValidator,
        TestFinGPTIntegration,
        TestEdgeCases
    ]
    
    if ENHANCED_MODULES:
        test_classes.extend([
            TestExceptionHandler,
            TestPerformanceOptimizer
        ])
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite

def run_tests_with_coverage():
    """Führt Tests mit Coverage-Bericht aus"""
    try:
        import coverage
        
        # Coverage initialisieren
        cov = coverage.Coverage()
        cov.start()
        
        # Tests ausführen
        suite = create_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Coverage stoppen und berichten
        cov.stop()
        cov.save()
        
        print("\n" + "="*70)
        print("COVERAGE REPORT")
        print("="*70)
        cov.report()
        
        # HTML Coverage Report (optional)
        try:
            cov.html_report(directory='tests/coverage_html')
            print("\nHTML Coverage Report erstellt in 'tests/coverage_html/'")
        except Exception:
            pass
        
        return result.wasSuccessful()
        
    except ImportError:
        print("Coverage nicht verfügbar, führe Tests ohne Coverage aus...")
        suite = create_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()

if __name__ == '__main__':
    print("FinGPT Unit Test Suite")
    print("="*50)
    
    # Prüfen ob enhanced modules verfügbar sind
    if ENHANCED_MODULES:
        print("✅ Enhanced modules verfügbar - umfassende Tests aktiv")
    else:
        print("⚠️ Enhanced modules nicht verfügbar - Basis-Tests aktiv")
    
    print("="*50)
    
    # Tests ausführen
    success = run_tests_with_coverage()
    
    if success:
        print("\n🎉 Alle Tests erfolgreich!")
        sys.exit(0)
    else:
        print("\n❌ Einige Tests fehlgeschlagen!")
        sys.exit(1)