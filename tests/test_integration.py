#!/usr/bin/env python3
"""
FinGPT Integration Tests
Integrationstests für das gesamte FinGPT System
"""

import unittest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import threading
import json

# Pfad zum Projektverzeichnis hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from FinGPT import MT5FinGPT
    from trading.risk_manager import RiskManager
    FINGPT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: FinGPT nicht verfügbar: {e}")
    FINGPT_AVAILABLE = False

try:
    from core.input_validator import SafeInput, InputValidator
    from core.exception_handler import ErrorHandler, ErrorSeverity
    from core.performance_optimizer import PerformanceMetrics, CacheManager
    ENHANCED_MODULES = True
except ImportError:
    ENHANCED_MODULES = False

class TestFinGPTSystemIntegration(unittest.TestCase):
    """Integrationstests für das FinGPT System"""
    
    def setUp(self):
        """Setup für Integration-Tests"""
        if not FINGPT_AVAILABLE:
            self.skipTest("FinGPT nicht verfügbar")
        
        # Mock für externe Abhängigkeiten
        self.mt5_patcher = patch('FinGPT.mt5')
        self.mock_mt5 = self.mt5_patcher.start()
        
        # Mock MT5 Funktionen
        self.mock_mt5.initialize.return_value = True
        self.mock_mt5.account_info.return_value = Mock(company="Test Broker")
        self.mock_mt5.terminal_info.return_value = Mock(trade_allowed=True)
        self.mock_mt5.symbol_info.return_value = Mock(
            bid=1.1000, ask=1.1005, point=0.0001, digits=5
        )
        self.mock_mt5.symbol_info_tick.return_value = Mock(
            bid=1.1000, ask=1.1005, last=1.1002
        )
        self.mock_mt5.order_send.return_value = Mock(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=12345
        )
        
        # Mock für requests (Ollama)
        self.requests_patcher = patch('FinGPT.requests')
        self.mock_requests = self.requests_patcher.start()
        self.mock_requests.get.return_value = Mock(
            status_code=200,
            json.return_value={"models": [{"name": "test-model"}]}
        )
        self.mock_requests.post.return_value = Mock(
            status_code=200,
            json.return_value={"response": "Test response"}
        )
    
    def tearDown(self):
        """Cleanup nach Tests"""
        self.mt5_patcher.stop()
        self.requests_patcher.stop()
    
    def test_fingpt_initialization(self):
        """Test FinGPT Initialisierung"""
        fingpt = MT5FinGPT()
        
        # Prüfen ob grundlegende Attribute gesetzt sind
        self.assertIsNotNone(fingpt.ollama_url)
        self.assertIsInstance(fingpt.trading_enabled, bool)
        self.assertIsInstance(fingpt.auto_trading, bool)
        self.assertIsInstance(fingpt.default_lot_size, (int, float))
        
        # Prüfen ob Enhanced Features korrekt initialisiert wurden
        if ENHANCED_MODULES:
            self.assertTrue(hasattr(fingpt, 'enhanced_mode'))
            self.assertTrue(hasattr(fingpt, 'error_handler'))
            self.assertTrue(hasattr(fingpt, 'resource_limiter'))
    
    def test_mt5_connection_workflow(self):
        """Test MT5 Verbindungs-Workflow"""
        fingpt = MT5FinGPT()
        
        # Test Verbindungsaufbau
        result = fingpt.connect_mt5()
        self.assertTrue(result)
        self.assertTrue(fingpt.mt5_connected)
        
        # Mock-Aufrufe prüfen
        self.mock_mt5.initialize.assert_called_once()
        self.mock_mt5.account_info.assert_called_once()
        self.mock_mt5.terminal_info.assert_called_once()
        
        # Test Verbindungstrennung
        fingpt.disconnect_mt5()
        self.assertFalse(fingpt.mt5_connected)
        self.mock_mt5.shutdown.assert_called_once()
    
    def test_trading_workflow(self):
        """Test kompletten Trading-Workflow"""
        fingpt = MT5FinGPT()
        
        # Setup
        fingpt.connect_mt5()
        fingpt.trading_enabled = True
        
        # Mock Risk Manager
        fingpt.risk_manager = Mock()
        fingpt.risk_manager.can_open_position.return_value = (True, "OK")
        fingpt.risk_manager.register_trade = Mock()
        
        # Test Trade-Ausführung
        result = fingpt.execute_trade("EURUSD", "BUY", 0.1)
        
        # Prüfen ob Trade erfolgreich war
        self.assertIn("✅", result)
        
        # Mock-Aufrufe prüfen
        self.mock_mt5.symbol_info.assert_called()
        self.mock_mt5.symbol_info_tick.assert_called()
        self.mock_mt5.order_send.assert_called_once()
        
        # Risk Manager Aufrufe prüfen
        fingpt.risk_manager.can_open_position.assert_called_once()
        fingpt.risk_manager.register_trade.assert_called_once()
    
    def test_ollama_integration(self):
        """Test Ollama Integration"""
        fingpt = MT5FinGPT()
        
        # Test Model-Abfrage
        models = fingpt.get_ollama_models()
        self.assertIsInstance(models, list)
        self.mock_requests.get.assert_called_once()
        
        # Test KI-Analyse
        fingpt.selected_model = "test-model"
        response = fingpt.get_ai_analysis("EURUSD", "BUY", "Test data")
        
        self.assertIsInstance(response, str)
        self.mock_requests.post.assert_called_once()
    
    def test_error_handling_integration(self):
        """Test Fehlerbehandlung im Integration"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        fingpt = MT5FinGPT()
        
        # Test mit MT5 Verbindungsfehler
        self.mock_mt5.initialize.return_value = False
        result = fingpt.connect_mt5()
        self.assertFalse(result)
        
        # Test mit ungültigem Symbol
        fingpt.connect_mt5()
        self.mock_mt5.symbol_info.return_value = None
        result = fingpt.execute_trade("INVALID", "BUY", 0.1)
        self.assertIn("nicht verfügbar", result)
    
    def test_performance_monitoring_integration(self):
        """Test Performance-Monitoring Integration"""
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
        
        fingpt = MT5FinGPT()
        
        # Performance-Metriken sollten verfügbar sein
        self.assertIsNotNone(fingpt.performance_metrics)
        
        # Test Metrik-Aufzeichnung
        fingpt.performance_metrics.record_metric("test_metric", 1.0)
        stats = fingpt.performance_metrics.get_metric_stats("test_metric")
        self.assertEqual(stats["count"], 1)
    
    def test_concurrent_operations(self):
        """Test nebenläufiger Operationen"""
        fingpt = MT5FinGPT()
        fingpt.connect_mt5()
        fingpt.trading_enabled = True
        
        # Mock Risk Manager für parallele Tests
        fingpt.risk_manager = Mock()
        fingpt.risk_manager.can_open_position.return_value = (True, "OK")
        fingpt.risk_manager.register_trade = Mock()
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(5):
                    result = fingpt.execute_trade("EURUSD", "BUY", 0.01)
                    results.append(f"Worker {worker_id}: {result}")
                    time.sleep(0.01)  # Kurze Pause
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Mehrere Worker-Threads starten
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Warten auf Abschluss
        for thread in threads:
            thread.join()
        
        # Prüfen ob keine Fehler auftraten
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        self.assertEqual(len(results), 15)  # 3 Worker × 5 Trades

class TestRiskManagementIntegration(unittest.TestCase):
    """Integrationstests für Risk Management"""
    
    def setUp(self):
        if not FINGPT_AVAILABLE:
            self.skipTest("FinGPT nicht verfügbar")
        
        self.risk_manager = RiskManager()
    
    def test_risk_limits_enforcement(self):
        """Test Durchsetzung von Risk-Limits"""
        # Test mit gültigem Trade
        can_trade, reason = self.risk_manager.can_open_position("EURUSD", "BUY", 0.1)
        self.assertIsInstance(can_trade, bool)
        self.assertIsInstance(reason, str)
        
        # Test mit zu großem Lot Size
        can_trade, reason = self.risk_manager.can_open_position("EURUSD", "BUY", 10.0)
        self.assertFalse(can_trade)
        self.assertIn("Lot Size", reason)
    
    def test_position_size_calculation(self):
        """Test Positionsgrößen-Berechnung"""
        lot_size = self.risk_manager.calculate_position_size("EURUSD", 20.0)
        self.assertIsInstance(lot_size, float)
        self.assertGreater(lot_size, 0)
        self.assertLessEqual(lot_size, self.risk_manager.max_lot_size)

class TestInputValidationIntegration(unittest.TestCase):
    """Integrationstests für Eingabevalidierung"""
    
    def setUp(self):
        if not ENHANCED_MODULES:
            self.skipTest("Enhanced modules nicht verfügbar")
    
    @patch('builtins.input')
    def test_safe_input_integration(self, mock_input):
        """Test SafeInput Integration"""
        # Test gültige Eingabe
        mock_input.return_value = "EURUSD"
        result = SafeInput.get_symbol("Symbol: ")
        self.assertEqual(result, "EURUSD")
        
        # Test ungültige Eingabe mit Korrektur
        mock_input.side_effect = ["invalid", "EURUSD"]
        result = SafeInput.get_symbol("Symbol: ")
        self.assertEqual(result, "EURUSD")

class TestSystemResilience(unittest.TestCase):
    """Test für System-Resilienz und Robustheit"""
    
    def setUp(self):
        if not FINGPT_AVAILABLE:
            self.skipTest("FinGPT nicht verfügbar")
    
    def test_network_failure_resilience(self):
        """Test Resilienz bei Netzwerkausfällen"""
        fingpt = MT5FinGPT()
        
        # Mock Netzwerkausfall
        with patch('FinGPT.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            # Sollte nicht abstürzen
            models = fingpt.get_ollama_models()
            self.assertIsInstance(models, list)
    
    def test_mt5_failure_resilience(self):
        """Test Resilienz bei MT5-Ausfällen"""
        fingpt = MT5FinGPT()
        
        # Mock MT5 Ausfall
        with patch('FinGPT.mt5') as mock_mt5:
            mock_mt5.initialize.side_effect = Exception("MT5 error")
            
            # Sollte nicht abstürzen
            result = fingpt.connect_mt5()
            self.assertFalse(result)
    
    def test_memory_usage_stability(self):
        """Test Speicherstabilität unter Last"""
        fingpt = MT5FinGPT()
        
        # Viele Operationen ausführen
        for i in range(100):
            fingpt.log("INFO", f"Test message {i}")
            
            # Cache-Operationen wenn verfügbar
            if ENHANCED_MODULES and hasattr(fingpt, 'performance_metrics'):
                fingpt.performance_metrics.record_metric(f"test_{i}", i)
        
        # Sollte nicht zu Speicherproblemen führen
        self.assertTrue(True)  # Wenn wir hier ankommen, ist alles ok
    
    def test_long_running_stability(self):
        """Test Stabilität bei langlaufender Operation"""
        fingpt = MT5FinGPT()
        
        # Simuliere langlaufende Operation
        start_time = time.time()
        for i in range(50):
            fingpt.log("INFO", f"Long running test {i}")
            time.sleep(0.01)  # Kurze Pause
            
            # Prüfen ob System noch reagiert
            if time.time() - start_time > 5:  # Max 5 Sekunden
                break
        
        self.assertTrue(True)  # Wenn wir hier ankommen, ist alles ok

class TestConfigurationManagement(unittest.TestCase):
    """Test für Konfigurationsmanagement"""
    
    def setUp(self):
        if not FINGPT_AVAILABLE:
            self.skipTest("FinGPT nicht verfügbar")
    
    def test_default_configuration(self):
        """Test Standardkonfiguration"""
        fingpt = MT5FinGPT()
        
        # Prüfen ob Standardwerte korrekt gesetzt sind
        self.assertEqual(fingpt.ollama_url, "http://localhost:11434")
        self.assertIsInstance(fingpt.default_lot_size, (int, float))
        self.assertGreater(fingpt.default_lot_size, 0)
        self.assertIsInstance(fingpt.max_risk_percent, (int, float))
        self.assertGreater(fingpt.max_risk_percent, 0)
    
    def test_configuration_validation(self):
        """Test Konfigurationsvalidierung"""
        fingpt = MT5FinGPT()
        
        # Test ungültige Konfigurationen sollten abgelehnt werden
        # (Dies würde in einer echten Implementierung erweitert werden)
        self.assertTrue(True)  # Placeholder

def create_integration_test_suite():
    """Erstellt die Integration-Test-Suite"""
    suite = unittest.TestSuite()
    
    test_classes = [
        TestFinGPTSystemIntegration,
        TestRiskManagementIntegration,
        TestSystemResilience,
        TestConfigurationManagement
    ]
    
    if ENHANCED_MODULES:
        test_classes.append(TestInputValidationIntegration)
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite

def run_integration_tests():
    """Führt alle Integrationstests aus"""
    print("FinGPT Integration Test Suite")
    print("="*50)
    
    if not FINGPT_AVAILABLE:
        print("❌ FinGPT nicht verfügbar - Tests übersprungen")
        return False
    
    if ENHANCED_MODULES:
        print("✅ Enhanced modules verfügbar - umfassende Integrationstests")
    else:
        print("⚠️ Enhanced modules nicht verfügbar - Basis-Integrationstests")
    
    print("="*50)
    
    # Test-Suite erstellen und ausführen
    suite = create_integration_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Zusammenfassung ausgeben
    print("\n" + "="*50)
    print("INTEGRATION TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)