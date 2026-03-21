#!/usr/bin/env python3
"""
GUI Config Package
Enthält Konfigurationsklassen für die GUI
"""

from gui.config.dashboard_config import (
    DashboardConfig,
    MetricConfig,
    get_dashboard_config,
    update_dashboard_config,
    get_metric_config,
    get_symbols,
    get_update_interval,
    load_config,
    save_config,
)

__all__ = [
    'DashboardConfig',
    'MetricConfig',
    'get_dashboard_config',
    'update_dashboard_config',
    'get_metric_config',
    'get_symbols',
    'get_update_interval',
    'load_config',
    'save_config',
]
