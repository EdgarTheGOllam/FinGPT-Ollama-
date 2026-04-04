#!/usr/bin/env python3
"""
GUI Components Package für FinGPT
Enthält wiederverwendbare UI-Komponenten
"""

from .terminal_session_manager import TerminalSessionManager, get_session_manager

__all__ = [
    'TerminalSessionManager',
    'get_session_manager'
]
