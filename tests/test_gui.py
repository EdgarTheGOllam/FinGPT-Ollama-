#!/usr/bin/env python3
"""
FinGPT Configuration GUI Test Suite
Unit-Tests für die Konfigurations-GUI
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path

# Import der zu testenden Module
from core.config_manager import ConfigManager, FinGPTConfig, FinGPTExtendedConfig


class TestConfigManager(unittest.TestCase):
    """Test-Klasse für ConfigManager"""
    
    def setUp(self):
        """Setup für Tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def tearDown(self):
        """Cleanup nach Tests"""
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_creation(self):
        """Testet die Erstellung von Standard-Konfigurationen"""
        config = FinGPTConfig()
        self.assertEqual(config.ollama_url, "http://localhost:11434")
        self.assertEqual(config.default_lot_size, 0.5)
        self.assertEqual(config.rsi_period, 14)
        
        extended_config = FinGPTExtendedConfig()
        self.assertTrue(extended_config.show_original_menu)
        self.assertEqual(extended_config.menu_style, "grouped")
    
    def test_config_validation(self):
        """Testet die Konfigurations-Validierung"""
        config = FinGPTConfig()
        
        # Gültige Konfiguration
        errors = self.config_manager.validate_config(config)
        self.assertEqual(len(errors), 0)
        
        # Ungültige Konfiguration
        config.default_lot_size = -1
        errors = self.config_manager.validate_config(config)
        self.assertGreater(len(errors), 0)
        
        # RSI-Validierung
        config = FinGPTConfig()
        config.rsi_oversold = 80
        config.rsi_overbought = 70
        errors = self.config_manager.validate_config(config)
        self.assertGreater(len(errors), 0)
    
    def test_config_save_load(self):
        """Testet das Speichern und Laden von Konfigurationen"""
        # Konfiguration ändern
        self.config_manager.fingpt_config.default_lot_size = 1.0
        self.config_manager.fingpt_extended_config.menu_style = "original"
        
        # Speichern
        self.assertTrue(self.config_manager.save_configs())
        
        # Neuen Manager erstellen und laden
        new_manager = ConfigManager(self.temp_dir)
        
        # Prüfen ob Werte korrekt geladen wurden
        self.assertEqual(new_manager.fingpt_config.default_lot_size, 1.0)
        self.assertEqual(new_manager.fingpt_extended_config.menu_style, "original")
    
    def test_backup_creation(self):
        """Testet die Erstellung von Backups"""
        # Konfiguration speichern
        self.config_manager.save_configs()
        
        # Backup erstellen
        self.assertTrue(self.config_manager.create_backup())
        
        # Prüfen ob Backup-Datei existiert
        backup_files = list(Path(self.temp_dir) / "backups" / "*.json")
        self.assertGreater(len(backup_files), 0)
    
    def test_reset_to_defaults(self):
        """Testet das Zurücksetzen auf Standardwerte"""
        # Konfiguration ändern
        self.config_manager.fingpt_config.default_lot_size = 2.0
        self.config_manager.fingpt_extended_config.menu_style = "original"
        
        # Zurücksetzen
        self.assertTrue(self.config_manager.reset_to_defaults())
        
        # Prüfen ob Standardwerte wiederhergestellt wurden
        self.assertEqual(self.config_manager.fingpt_config.default_lot_size, 0.5)
        self.assertEqual(self.config_manager.fingpt_extended_config.menu_style, "grouped")
    
    def test_export_import(self):
        """Testet den Export und Import von Konfigurationen"""
        # Konfiguration ändern
        self.config_manager.fingpt_config.default_lot_size = 1.5
        self.config_manager.fingpt_extended_config.menu_style = "original"
        
        # Exportieren
        export_file = Path(self.temp_dir) / "export.json"
        self.assertTrue(self.config_manager.export_config(str(export_file)))
        self.assertTrue(export_file.exists())
        
        # Zurücksetzen und importieren
        self.config_manager.reset_to_defaults()
        self.assertTrue(self.config_manager.import_config(str(export_file)))
        
        # Prüfen ob Werte korrekt importiert wurden
        self.assertEqual(self.config_manager.fingpt_config.default_lot_size, 1.5)
        self.assertEqual(self.config_manager.fingpt_extended_config.menu_style, "original")


class TestFinGPTConfig(unittest.TestCase):
    """Test-Klasse für FinGPTConfig"""
    
    def test_post_init(self):
        """Testet die Post-Init Methode"""
        config = FinGPTConfig(auto_trade_symbols=None)
        self.assertEqual(config.auto_trade_symbols, ["EURUSD"])
        
        config = FinGPTConfig(auto_trade_symbols=["GBPUSD", "EURJPY"])
        self.assertEqual(config.auto_trade_symbols, ["GBPUSD", "EURJPY"])
    
    def test_config_ranges(self):
        """Testet gültige Wertebereiche"""
        config = FinGPTConfig()
        
        # Gültige Werte
        config.default_lot_size = 0.1
        config.max_risk_percent = 5.0
        config.rsi_period = 20
        
        # Grenzwerte testen
        config.default_lot_size = 0.01  # Minimum
        config.default_lot_size = 10.0  # Maximum
        
        config.rsi_period = 2   # Minimum
        config.rsi_period = 100  # Maximum


class TestFinGPTExtendedConfig(unittest.TestCase):
    """Test-Klasse für FinGPTExtendedConfig"""
    
    def test_default_values(self):
        """Testet Standardwerte"""
        config = FinGPTExtendedConfig()
        
        self.assertTrue(config.show_original_menu)
        self.assertTrue(config.show_extended_menu)
        self.assertEqual(config.menu_style, "grouped")
        self.assertTrue(config.enable_advanced_indicators)
        self.assertEqual(config.color_scheme, "default")


def run_gui_tests():
    """Führt alle GUI-Tests durch"""
    print("FinGPT Configuration GUI Test Suite")
    print("=" * 50)
    
    # Test-Suite erstellen
    test_suite = unittest.TestSuite()
    
    # Tests hinzufügen
    test_suite.addTest(unittest.makeSuite(TestConfigManager))
    test_suite.addTest(unittest.makeSuite(TestFinGPTConfig))
    test_suite.addTest(unittest.makeSuite(TestFinGPTExtendedConfig))
    
    # Tests ausführen
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Ergebnis ausgeben
    print("\\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ Alle Tests erfolgreich!")
    else:
        print(f"❌ {len(result.failures)} Fehler, {len(result.errors)} Errors")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_gui_tests()
    sys.exit(0 if success else 1)