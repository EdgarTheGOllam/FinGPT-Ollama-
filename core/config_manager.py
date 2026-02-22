#!/usr/bin/env python3
"""
FinGPT Configuration Manager
Geschäftslogik für die Verwaltung von Konfigurationsparametern
"""

import json
import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FinGPTConfig:
    """Konfigurationsklasse für FinGPT Basis-Parameter"""
    # Grundlegende Einstellungen
    ollama_url: str = "http://localhost:11434"
    selected_model: Optional[str] = None
    trading_enabled: bool = False
    default_lot_size: float = 0.5
    max_risk_percent: float = 2.0
    auto_trading: bool = False
    auto_trade_symbols: Optional[List[str]] = None
    analysis_interval: int = 300
    
    # RSI Einstellungen
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # MACD Einstellungen
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    
    # Support/Resistance Einstellungen
    sr_lookback_period: int = 50
    sr_min_touches: int = 2
    sr_tolerance: float = 0.0002
    sr_strength_threshold: int = 3
    
    # Multi-Timeframe Einstellungen
    mtf_enabled: bool = True
    trend_ema_period: int = 50
    trend_strength_threshold: float = 0.0010
    require_trend_confirmation: bool = True
    
    # Partial Close Einstellungen
    partial_close_enabled: bool = True
    first_target_percent: int = 50
    second_target_percent: int = 25
    profit_target_1: float = 1.5
    profit_target_2: float = 3.0
    
    def __post_init__(self):
        """Post-Init für Default-Werte"""
        if self.auto_trade_symbols is None:
            self.auto_trade_symbols = ["EURUSD"]


@dataclass
class FinGPTExtendedConfig:
    """Konfigurationsklasse für FinGPT Extended-Parameter"""
    # Menü-Konfiguration
    show_original_menu: bool = True
    show_extended_menu: bool = True
    menu_style: str = "grouped"  # "grouped" oder "original"
    
    # Erweiterte Funktionen
    enable_advanced_indicators: bool = True
    enable_enhanced_ai_analysis: bool = True
    enable_multi_indicator_scanner: bool = True
    enable_indicator_comparison: bool = True
    
    # UI-Einstellungen
    show_status_bar: bool = True
    show_quick_actions: bool = False
    color_scheme: str = "default"  # "default", "dark", "light"
    
    # Performance-Einstellungen
    cache_indicators: bool = True
    max_cache_size: int = 100
    update_interval: int = 5


class ConfigManager:
    """
    Manager für Konfigurationsdateien und -parameter
    
    Diese Klasse ist verantwortlich für:
    - Laden und Speichern von Konfigurationen
    - Validierung von Konfigurationsparametern
    - Konvertierung zwischen verschiedenen Formaten
    - Backup und Wiederherstellung von Konfigurationen
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialisiert den ConfigManager
        
        Args:
            config_dir: Verzeichnis für Konfigurationsdateien
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Konfigurationsdateien
        self.fingpt_config_file = self.config_dir / "fingpt_config.json"
        self.fingpt_extended_config_file = self.config_dir / "fingpt_extended_config.json"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Aktuelle Konfigurationen
        self.fingpt_config = FinGPTConfig()
        self.fingpt_extended_config = FinGPTExtendedConfig()
        
        # Lade vorhandene Konfigurationen
        self.load_configs()
    
    def load_configs(self) -> bool:
        """
        Lädt alle Konfigurationsdateien
        
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            # FinGPT Basis-Konfiguration laden
            if self.fingpt_config_file.exists():
                with open(self.fingpt_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.fingpt_config = FinGPTConfig(**config_data)
            
            # FinGPT Extended-Konfiguration laden
            if self.fingpt_extended_config_file.exists():
                with open(self.fingpt_extended_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.fingpt_extended_config = FinGPTExtendedConfig(**config_data)
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Laden der Konfiguration: {e}")
            return False
    
    def save_configs(self) -> bool:
        """
        Speichert alle Konfigurationen
        
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            # Backup erstellen
            self.create_backup()
            
            # FinGPT Basis-Konfiguration speichern
            with open(self.fingpt_config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.fingpt_config), f, indent=2, ensure_ascii=False)
            
            # FinGPT Extended-Konfiguration speichern
            with open(self.fingpt_extended_config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.fingpt_extended_config), f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Speichern der Konfiguration: {e}")
            return False
    
    def create_backup(self) -> bool:
        """
        Erstellt ein Backup der aktuellen Konfiguration
        
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_suffix = f"_{timestamp}"
            
            # FinGPT Basis-Backup
            if self.fingpt_config_file.exists():
                backup_file = self.backup_dir / f"fingpt_config{backup_suffix}.json"
                with open(self.fingpt_config_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            # FinGPT Extended-Backup
            if self.fingpt_extended_config_file.exists():
                backup_file = self.backup_dir / f"fingpt_extended_config{backup_suffix}.json"
                with open(self.fingpt_extended_config_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Erstellen des Backups: {e}")
            return False
    
    def validate_config(self, config: FinGPTConfig) -> List[str]:
        """
        Validiert die FinGPT Konfiguration
        
        Args:
            config: Zu validierende Konfiguration
            
        Returns:
            List[str]: Liste der Validierungsfehler
        """
        errors = []
        
        # Grundlegende Validierungen
        if config.default_lot_size <= 0 or config.default_lot_size > 10:
            errors.append("Default Lot Size muss zwischen 0 und 10 liegen")
        
        if config.max_risk_percent <= 0 or config.max_risk_percent > 100:
            errors.append("Max Risk Percent muss zwischen 0 und 100 liegen")
        
        if config.analysis_interval < 10 or config.analysis_interval > 3600:
            errors.append("Analysis Interval muss zwischen 10 und 3600 Sekunden liegen")
        
        # RSI Validierungen
        if config.rsi_period < 2 or config.rsi_period > 100:
            errors.append("RSI Period muss zwischen 2 und 100 liegen")
        
        if config.rsi_oversold >= config.rsi_overbought:
            errors.append("RSI Oversold muss kleiner als Overbought sein")
        
        if config.rsi_oversold < 10 or config.rsi_oversold > 40:
            errors.append("RSI Oversold muss zwischen 10 und 40 liegen")
        
        if config.rsi_overbought < 60 or config.rsi_overbought > 90:
            errors.append("RSI Overbought muss zwischen 60 und 90 liegen")
        
        # MACD Validierungen
        if config.macd_fast_period >= config.macd_slow_period:
            errors.append("MACD Fast Period muss kleiner als Slow Period sein")
        
        if config.macd_fast_period < 5 or config.macd_fast_period > 50:
            errors.append("MACD Fast Period muss zwischen 5 und 50 liegen")
        
        if config.macd_slow_period < 10 or config.macd_slow_period > 200:
            errors.append("MACD Slow Period muss zwischen 10 und 200 liegen")
        
        if config.macd_signal_period < 5 or config.macd_signal_period > 50:
            errors.append("MACD Signal Period muss zwischen 5 und 50 liegen")
        
        # Support/Resistance Validierungen
        if config.sr_lookback_period < 10 or config.sr_lookback_period > 500:
            errors.append("S/R Lookback Period muss zwischen 10 und 500 liegen")
        
        if config.sr_min_touches < 1 or config.sr_min_touches > 10:
            errors.append("S/R Min Touches muss zwischen 1 und 10 liegen")
        
        if config.sr_tolerance <= 0 or config.sr_tolerance > 0.01:
            errors.append("S/R Tolerance muss zwischen 0 und 0.01 liegen")
        
        # Multi-Timeframe Validierungen
        if config.trend_ema_period < 5 or config.trend_ema_period > 200:
            errors.append("Trend EMA Period muss zwischen 5 und 200 liegen")
        
        if config.trend_strength_threshold <= 0 or config.trend_strength_threshold > 0.1:
            errors.append("Trend Strength Threshold muss zwischen 0 und 0.1 liegen")
        
        # Partial Close Validierungen
        if config.first_target_percent < 10 or config.first_target_percent > 90:
            errors.append("First Target Percent muss zwischen 10 und 90 liegen")
        
        if config.second_target_percent < 10 or config.second_target_percent > 90:
            errors.append("Second Target Percent muss zwischen 10 und 90 liegen")
        
        if (config.first_target_percent + config.second_target_percent) > 95:
            errors.append("Summe der Target Percent darf 95% nicht überschreiten")
        
        if config.profit_target_1 <= 0 or config.profit_target_1 > 10:
            errors.append("Profit Target 1 muss zwischen 0 und 10 liegen")
        
        if config.profit_target_2 <= 0 or config.profit_target_2 > 20:
            errors.append("Profit Target 2 muss zwischen 0 und 20 liegen")
        
        if config.profit_target_2 <= config.profit_target_1:
            errors.append("Profit Target 2 muss größer als Profit Target 1 sein")
        
        return errors
    
    def get_available_models(self) -> List[str]:
        """
        Gibt verfügbare Ollama-Modelle zurück
        
        Returns:
            List[str]: Liste der verfügbaren Modelle
        """
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except:
            pass
        
        return ["llama2", "mistral", "codellama", "neural-chat", "starling-lm"]
    
    def reset_to_defaults(self, config_type: str = "both") -> bool:
        """
        Setzt Konfigurationen auf Standardwerte zurück
        
        Args:
            config_type: "fingpt", "extended", oder "both"
            
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            if config_type in ["fingpt", "both"]:
                self.fingpt_config = FinGPTConfig()
            
            if config_type in ["extended", "both"]:
                self.fingpt_extended_config = FinGPTExtendedConfig()
            
            return self.save_configs()
            
        except Exception as e:
            print(f"Fehler beim Zurücksetzen: {e}")
            return False
    
    def export_config(self, filepath: str) -> bool:
        """
        Exportiert Konfigurationen in eine Datei
        
        Args:
            filepath: Export-Dateipfad
            
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            export_data = {
                "fingpt_config": asdict(self.fingpt_config),
                "fingpt_extended_config": asdict(self.fingpt_extended_config),
                "export_timestamp": str(datetime.datetime.now()),
                "version": "1.0"
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Exportieren: {e}")
            return False
    
    def import_config(self, filepath: str) -> bool:
        """
        Importiert Konfigurationen aus einer Datei
        
        Args:
            filepath: Import-Dateipfad
            
        Returns:
            bool: True wenn erfolgreich, False bei Fehlern
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Backup erstellen
            self.create_backup()
            
            # Konfigurationen importieren
            if "fingpt_config" in import_data:
                self.fingpt_config = FinGPTConfig(**import_data["fingpt_config"])
            
            if "fingpt_extended_config" in import_data:
                self.fingpt_extended_config = FinGPTExtendedConfig(**import_data["fingpt_extended_config"])
            
            return self.save_configs()
            
        except Exception as e:
            print(f"Fehler beim Importieren: {e}")
            return False