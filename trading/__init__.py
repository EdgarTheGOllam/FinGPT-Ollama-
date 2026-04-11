#!/usr/bin/env python3
"""
FinGPT Trading System - Trading Module
===================================
Hauptklassen und Funktionen für das Trading-System.
"""

from .base_strategy import (
    BaseStrategy,
    TradingSignal,
    MarketPhase,
    StructurePoint,
    StrategyRegistry,
    create_signal,
)
from .risk_manager import RiskManager
from .advanced_indicators import AdvancedIndicators, IndicatorIntegration
from .trading_companion import TradingCompanion
from .ai_fulldrive_engine import (
    AIFulldriveEngine,
    MarketFeatureExtractor,
    LSTMPatternNetwork,
    FullDriveRiskManager,
    PerformanceKPITracker,
)

__all__ = [
    # Base Strategy
    "BaseStrategy",
    "TradingSignal",
    "MarketPhase",
    "StructurePoint",
    "StrategyRegistry",
    "create_signal",
    # Risk Manager
    "RiskManager",
    # Advanced Indicators
    "AdvancedIndicators",
    "IndicatorIntegration",
    # Trading Companion
    "TradingCompanion",
    # AI Fulldrive Engine
    "AIFulldriveEngine",
    "MarketFeatureExtractor",
    "LSTMPatternNetwork",
    "FullDriveRiskManager",
    "PerformanceKPITracker",
]

__version__ = "1.0.0"
