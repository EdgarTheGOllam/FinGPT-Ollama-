#!/usr/bin/env python3
"""
Dashboard Konfiguration
Zentralisierte Konfiguration für das Dashboard-Layout und -Verhalten
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from gui.design_system import DesignSystem


@dataclass
class MetricConfig:
    """Konfiguration für eine Metrik-Karte"""
    key: str
    title: str
    icon: str = 'default'
    default_value: str = '---'
    show_trend: bool = True
    trend_format: str = '{value:+.2f}%'
    color_positive: bool = True  # Grün bei positiv, Rot bei negativ


@dataclass
class DashboardConfig:
    """Hauptkonfiguration für das Dashboard"""
    
    # Metrik-Karten
    metrics: List[MetricConfig] = field(default_factory=lambda: [
        MetricConfig('balance', 'Kontostand', 'balance', '€--', True, '€{value:,.2f}', True),
        MetricConfig('positions', 'Offene Positionen', 'positions', '-', False),
        MetricConfig('trades', 'Heutige Trades', 'trades', '-', True, '+{value}', False),
        MetricConfig('pnl', 'Gewinn/Verlust', 'pnl', '€--', True, '€{value:,.2f}', True),
        MetricConfig('winrate', 'Win Rate', 'winrate', '-%', True, '{value:.1f}%', True),
        MetricConfig('risk', 'Freie Margin', 'risk', '€--', True, '€{value:,.2f}', True),
    ])
    
    # Symbole für Live-Daten
    symbols: List[str] = field(default_factory=lambda: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD'])
    
    # Update-Intervalle (in Millisekunden)
    update_intervals: Dict[str, int] = field(default_factory=lambda: {
        'ticks': 1000,
        'positions': 5000,
        'signals': 30000,
        'account': 5000,
        'charts': 10000,
    })
    
    # AI-Visualizer Einstellungen
    ai_visualizer: Dict[str, bool] = field(default_factory=lambda: {
        'show_daily_goal': True,
        'show_sonar': True,
        'show_mvp': True,
    })
    
    # Layout-Einstellungen
    layout: Dict[str, Any] = field(default_factory=lambda: {
        'header': {
            'show_balance': True,
            'show_equity': True,
            'show_connection_status': True,
            'show_last_update': True,
        },
        'metrics': {
            'columns': 3,
            'min_card_width': 150,
        },
        'live_data': {
            'columns': ['symbol', 'price', 'change', 'trend', 'signal'],
            'show_sparklines': True,
            'show_trend_dots': True,
        },
    })
    
    # Spalten-Konfiguration für Live-Daten
    live_data_columns: List[Dict[str, str]] = field(default_factory=lambda: [
        {'key': 'symbol', 'title': 'Symbol', 'width': '60'},
        {'key': 'price', 'title': 'Preis', 'width': '80'},
        {'key': 'change', 'title': 'Änderung', 'width': '60'},
        {'key': 'trend', 'title': 'Trend (M15|H1|H4)', 'width': '70'},
        {'key': 'signal', 'title': 'Signal', 'width': '50'},
    ])


# Singleton-Instanz
_default_config: Optional[DashboardConfig] = None


def get_dashboard_config() -> DashboardConfig:
    """Gibt die Dashboard-Konfiguration zurück (Singleton)"""
    global _default_config
    if _default_config is None:
        _default_config = DashboardConfig()
    return _default_config


def update_dashboard_config(config: DashboardConfig):
    """Aktualisiert die Dashboard-Konfiguration"""
    global _default_config
    _default_config = config


def get_metric_config(key: str) -> Optional[MetricConfig]:
    """Gibt die Konfiguration für eine bestimmte Metrik zurück"""
    config = get_dashboard_config()
    for metric in config.metrics:
        if metric.key == key:
            return metric
    return None


def get_symbols() -> List[str]:
    """Gibt die konfigurierten Symbole zurück"""
    return get_dashboard_config().symbols


def get_update_interval(update_type: str) -> int:
    """Gibt das Update-Intervall für einen bestimmten Typ zurück"""
    intervals = get_dashboard_config().update_intervals
    return intervals.get(update_type, 1000)


# Konfiguration laden/speichern
import json
import os


def load_config_from_file(filepath: str) -> DashboardConfig:
    """Lädt die Konfiguration aus einer JSON-Datei"""
    if not os.path.exists(filepath):
        return get_dashboard_config()
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Konvertiere Dictionary zurück zu DashboardConfig
    metrics = [MetricConfig(**m) for m in data.get('metrics', [])]
    
    config = DashboardConfig(
        metrics=metrics,
        symbols=data.get('symbols', ['EURUSD', 'GBPUSD', 'USDJPY']),
        update_intervals=data.get('update_intervals', {}),
        ai_visualizer=data.get('ai_visualizer', {}),
        layout=data.get('layout', {}),
    )
    
    return config


def save_config_to_file(config: DashboardConfig, filepath: str):
    """Speichert die Konfiguration in eine JSON-Datei"""
    data = {
        'metrics': [
            {
                'key': m.key,
                'title': m.title,
                'icon': m.icon,
                'default_value': m.default_value,
                'show_trend': m.show_trend,
                'trend_format': m.trend_format,
                'color_positive': m.color_positive,
            }
            for m in config.metrics
        ],
        'symbols': config.symbols,
        'update_intervals': config.update_intervals,
        'ai_visualizer': config.ai_visualizer,
        'layout': config.layout,
    }
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


# Standard-Konfigurationsdatei
DEFAULT_CONFIG_PATH = 'config/dashboard_config.json'


def load_config() -> DashboardConfig:
    """Lädt die Konfiguration (aus Datei oder Standard)"""
    try:
        return load_config_from_file(DEFAULT_CONFIG_PATH)
    except Exception:
        return get_dashboard_config()


def save_config(config: DashboardConfig):
    """Speichert die Konfiguration"""
    save_config_to_file(config, DEFAULT_CONFIG_PATH)


# Beispiel-Usage
if __name__ == "__main__":
    # Konfiguration abrufen
    config = get_dashboard_config()
    
    print("=== Dashboard Konfiguration ===")
    print(f"\nMetriken ({len(config.metrics)}):")
    for metric in config.metrics:
        print(f"  - {metric.key}: {metric.title} (icon: {metric.icon})")
    
    print(f"\nSymbole: {config.symbols}")
    print(f"\nUpdate-Intervalle:")
    for key, value in config.update_intervals.items():
        print(f"  - {key}: {value}ms")
    
    print(f"\nAI-Visualizer:")
    for key, value in config.ai_visualizer.items():
        print(f"  - {key}: {value}")
    
    # Metrik-Konfiguration abrufen
    balance_config = get_metric_config('balance')
    if balance_config:
        print(f"\nBalance Metrik: {balance_config.title}, Trend: {balance_config.show_trend}")
