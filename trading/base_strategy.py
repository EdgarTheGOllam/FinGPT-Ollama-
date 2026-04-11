#!/usr/bin/env python3
"""
Base Strategy Classes für FinGPT Trading System
Gemeinsame Basis-Klassen und Interfaces für alle Trading-Styles
"""

import numpy as np
import MetaTrader5 as mt5
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class TradingSignal:
    """Standardisiertes Trading-Signal Format"""

    action: str  # "BUY", "SELL", "HOLD"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0  # 0.0 - 1.0
    reason: str = ""
    pattern_type: str = ""
    rr_ratio: float = 0.0
    market_phase: str = "NEUTRAL"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Prüft ob Signal gültig für Trading ist"""
        return self.action in ["BUY", "SELL"] and self.confidence >= 0.3


@dataclass
class MarketPhase:
    """Marktphasen-Klassifikation"""

    phase: str  # "TRENDING", "RANGE", "VOLATILE", "NEUTRAL"
    strength: float = 0.0  # 0.0 - 1.0
    direction: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructurePoint:
    """Strukturpunkt für Trend-Analyse"""

    index: int
    price: float
    type: str  # "SWING_HIGH", "SWING_LOW"
    timestamp: int = 0


class BaseStrategy(ABC):
    """
    Abstrakte Basis-Klasse für alle Trading-Strategien.
    Jede Strategie muss diese Methoden implementieren.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or self._default_config()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.name = self.__class__.__name__

    @abstractmethod
    def _default_config(self) -> Dict[str, Any]:
        """Gibt Standard-Konfiguration zurück"""
        pass

    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiere Markt und gebe Analyse-Ergebnis zurück.

        Args:
            symbol: Trading-Symbol (z.B. "EURUSD")
            data: Marktdaten (OHLCV)

        Returns:
            dict mit Analyse-Ergebnissen
        """
        pass

    @abstractmethod
    def get_signal(self, symbol: str) -> TradingSignal:
        """
        Generiert Trading-Signal für Symbol.

        Returns:
            TradingSignal Objekt mit Einstiegs-Informationen
        """
        pass

    def validate_entry(self, signal: TradingSignal) -> bool:
        """
        Validiert ob Einstieg valide ist.
        Kann in Subclasses überschrieben werden.
        """
        return signal.is_valid()

    def get_market_phase(self, symbol: str, timeframe: int = None) -> MarketPhase:
        """
        Bestimme Marktphase.
        Kann in Subclasses überschrieben werden.

        Args:
            symbol: Trading-Symbol
            timeframe: Zeitrahmen (optional). Falls None, wird MT5 TIMEFRAME_M15 verwendet.
        """
        if timeframe is None:
            try:
                import MetaTrader5 as mt5

                timeframe = mt5.TIMEFRAME_M15
            except Exception:
                return MarketPhase(
                    phase="NEUTRAL",
                    strength=0.0,
                    details={"error": "MT5 nicht verfügbar"},
                )
        return self._analyze_market_phase(symbol, timeframe)

    def _analyze_market_phase(self, symbol: str, timeframe: int) -> MarketPhase:
        """Basis-Implementierung der Marktphasen-Analyse"""
        try:
            import MetaTrader5 as mt5

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 50)
            if rates is None or len(rates) < 20:
                return MarketPhase(phase="NEUTRAL", strength=0.0)

            closes = np.array([r["close"] for r in rates])
            highs = np.array([r["high"] for r in rates])
            lows = np.array([r["low"] for r in rates])

            # Berechne Trend-Stärke
            ema20 = self._calculate_ema(closes, 20)
            ema50 = self._calculate_ema(closes, 50)

            price_above_ema = closes[-1] > ema20[-1]
            ema_rising = ema20[-1] > ema20[-2]

            # Swing-Analyse
            swing_highs, swing_lows = self._detect_swings(highs, lows, 5)

            # Bestimme Phase
            if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                hh = swing_highs[-1][1] > swing_highs[-2][1]
                hl = swing_lows[-1][1] > swing_lows[-2][1]
                lh = swing_highs[-1][1] < swing_highs[-2][1]
                ll = swing_lows[-1][1] < swing_lows[-2][1]

                if hh and hl:
                    direction = "BULLISH"
                    strength = 0.7
                elif lh and ll:
                    direction = "BEARISH"
                    strength = 0.7
                else:
                    direction = "NEUTRAL"
                    strength = 0.3
            else:
                direction = "NEUTRAL"
                strength = 0.2

            # Range vs Trending
            price_range = (max(highs[-20:]) - min(lows[-20:])) / closes[-1] * 100

            if price_range < 0.5:
                phase = "RANGE"
            elif price_range > 1.5:
                phase = "VOLATILE"
            else:
                phase = "TRENDING" if direction != "NEUTRAL" else "NEUTRAL"

            return MarketPhase(phase=phase, strength=strength, direction=direction)

        except Exception as e:
            self.logger.error(f"Marktphasen-Analyse Fehler: {e}")
            return MarketPhase(phase="NEUTRAL", strength=0.0)

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Berechnet EMA"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data, dtype=float)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _detect_swings(
        self, highs: np.ndarray, lows: np.ndarray, period: int = 5
    ) -> Tuple[List, List]:
        """Erkennt Swing-Highs und Swing-Lows (Fraktale)"""
        swing_highs = []
        swing_lows = []

        for i in range(period, len(highs) - period):
            # Bullisher Swing
            if highs[i] > max(highs[i - period : i]) and highs[i] > max(
                highs[i + 1 : i + period + 1]
            ):
                swing_highs.append((i, highs[i]))

            # Bearischer Swing
            if lows[i] < min(lows[i - period : i]) and lows[i] < min(
                lows[i + 1 : i + period + 1]
            ):
                swing_lows.append((i, lows[i]))

        return swing_highs, swing_lows

    def _get_pip_size(self, symbol: str) -> float:
        """Ermittelt Pip-Größe für Symbol"""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return 0.0001
            point = info.point
            return point * 10 if info.digits in (3, 5) else point
        except:
            return 0.0001

    def _calculate_rr_ratio(
        self, entry: float, sl: float, tp: float, action: str
    ) -> float:
        """Berechnet Risk-Reward Ratio"""
        try:
            if action == "BUY":
                risk = abs(entry - sl)
                reward = abs(tp - entry)
            else:
                risk = abs(entry - sl)
                reward = abs(entry - tp)

            if risk > 0:
                return round(reward / risk, 2)
            return 0.0
        except:
            return 0.0

    def log(self, level: str, message: str):
        """Logging-Hilfsfunktion"""
        if self.logger:
            getattr(self.logger, level.lower(), self.logger.info)(
                f"[{self.name}] {message}"
            )
        else:
            print(f"[{self.name}] {message}")


class StrategyRegistry:
    """Registry für alle verfügbaren Strategien"""

    _strategies: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Registriert eine neue Strategie"""
        cls._strategies[name] = strategy_class

    @classmethod
    def get_strategy(cls, name: str) -> Optional[type]:
        """Gibt Strategie-Klasse zurück"""
        return cls._strategies.get(name)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """Liste aller registrierten Strategien"""
        return list(cls._strategies.keys())


# Convenience-Funktionen
def create_signal(
    action: str,
    entry: float,
    sl: float,
    tp: float,
    confidence: float,
    reason: str,
    pattern: str = "",
    **kwargs,
) -> TradingSignal:
    """Hilfsfunktion zum Erstellen von TradingSignal"""
    rr = 0.0
    if sl > 0 and tp > 0:
        if action == "BUY":
            rr = abs(tp - entry) / abs(entry - sl) if entry != sl else 0
        else:
            rr = abs(entry - tp) / abs(sl - entry) if sl != entry else 0

    return TradingSignal(
        action=action,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        confidence=confidence,
        reason=reason,
        pattern_type=pattern,
        rr_ratio=round(rr, 2),
        **kwargs,
    )
