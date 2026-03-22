#!/usr/bin/env python3
"""
GUI Widgets Package für FinGPT
Enthält wiederverwendbare UI-Komponenten für Trading-Features
"""

from .order_book import OrderBookWidget, MarketDepthWidget
from .risk_calculator import RiskCalculatorWidget, QuickTradeWidget
from .multi_account import MultiAccountManager, AccountSwitcherWidget

__all__ = [
    'OrderBookWidget',
    'MarketDepthWidget',
    'RiskCalculatorWidget', 
    'QuickTradeWidget',
    'MultiAccountManager',
    'AccountSwitcherWidget'
]
