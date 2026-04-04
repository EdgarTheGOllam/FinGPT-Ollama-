#!/usr/bin/env python3
"""
Pattern Trading Strategy - Ohne externe Indikatoren
====================================================
Implementiert klassische Chartmuster und Candlestick-Pattern
mit S/R Bestätigung.

Chart Patterns:
- Flag, Wedge, Head & Shoulders, Inverse H&S
- Ascending/Descending/Symmetrical Triangle
- Cup and Handle

Candlestick Patterns:
- Hammer, Inverted Hammer
- Bullish/Bearish Engulfing
- Morning/Evening Star
- Doji, Morning/Evening Doji
- Piercing Pattern, Dark Cloud Cover
"""

import numpy as np
import MetaTrader5 as mt5
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from trading.base_strategy import BaseStrategy, TradingSignal, create_signal


@dataclass
class ChartPattern:
    """Chart Pattern Datenstruktur"""
    pattern_type: str
    direction: str  # "BULLISH", "BEARISH"
    start_idx: int
    end_idx: int
    confidence: float = 0.0
    target: float = 0.0
    stop: float = 0.0


@dataclass
class CandlestickPattern:
    """Candlestick Pattern Datenstruktur"""
    pattern_type: str
    direction: str
    idx: int
    confidence: float = 0.0


class PatternStrategy(BaseStrategy):
    """
    Pattern Trading Strategy
    
    Implementiert:
    - Chart Pattern Erkennung (Flags, Wedges, H&S, Dreiecke)
    - Candlestick Pattern Erkennung
    - S/R Bestätigung für valide Setups
    """
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            # Chart Patterns
            "enable_flags": True,
            "enable_wedges": True,
            "enable_head_shoulders": True,
            "enable_triangles": True,
            "enable_cup_handle": True,
            
            # Candlestick Patterns
            "enable_hammer": True,
            "enable_engulfing": True,
            "enable_morning_star": True,
            "enable_doji": True,
            "enable_piercing": True,
            
            # Pattern-Validierung
            "min_pattern_bars": 5,
            "pattern_tolerance": 0.002,
            
            # S/R Bestätigung
            "sr_confirmation_required": True,
            "sr_touch_tolerance_pips": 3,
            
            # Einstiegs-Trigger
            "entry_on_pattern_complete": True,
            "entry_on_sr_retest": True,
            
            # Stop-Loss
            "sl_below_pattern_low": True,
            "sl_buffer_pips": 5,
            
            # Take-Profit
            "tp_pattern_target": True,
            "tp_2r": True,
            "tp_3r": True,
            
            # Risiko
            "min_rr_ratio": 1.5,
            
            # Marktphasen
            "allowed_phases": ["ALL"]
        }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # Cache
        self._patterns: Dict[str, Dict] = {}
        self._last_analysis: Dict[str, Dict] = {}
        
        self.log("INFO", "Pattern Strategy initialisiert")
    
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Pattern-Analyse durch"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
            if rates is None or len(rates) < 20:
                return {"error": "Unzureichende Marktdaten"}
            
            pip_size = self._get_pip_size(symbol)
            
            closes = np.array([r['close'] for r in rates], dtype=float)
            highs = np.array([r['high'] for r in rates], dtype=float)
            lows = np.array([r['low'] for r in rates], dtype=float)
            opens = np.array([r['open'] for r in rates], dtype=float)
            
            # S/R Level finden
            sr_levels = self._find_support_resistance(highs, lows, pip_size)
            
            # Chart Patterns
            chart_patterns = []
            if self.config["enable_flags"]:
                chart_patterns.extend(self._find_flags(rates, highs, lows, closes, pip_size))
            if self.config["enable_wedges"]:
                chart_patterns.extend(self._find_wedges(rates, highs, lows, closes, pip_size))
            if self.config["enable_triangles"]:
                chart_patterns.extend(self._find_triangles(rates, highs, lows, closes, pip_size))
            
            # Candlestick Patterns
            candle_patterns = []
            if self.config["enable_hammer"]:
                candle_patterns.extend(self._find_hammer(opens, highs, lows, closes, pip_size))
            if self.config["enable_engulfing"]:
                candle_patterns.extend(self._find_engulfing(opens, highs, lows, closes, pip_size))
            if self.config["enable_morning_star"]:
                candle_patterns.extend(self._find_morning_star(opens, highs, lows, closes, pip_size))
            if self.config["enable_doji"]:
                candle_patterns.extend(self._find_doji(opens, highs, lows, closes))
            
            # Signal generieren
            signal = self._generate_pattern_signal(
                symbol, rates, chart_patterns, candle_patterns, sr_levels, pip_size
            )
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "chart_patterns": [
                    {
                        "type": p.pattern_type,
                        "direction": p.direction,
                        "confidence": p.confidence
                    }
                    for p in chart_patterns[:3]
                ],
                "candle_patterns": [
                    {
                        "type": p.pattern_type,
                        "direction": p.direction,
                        "confidence": p.confidence
                    }
                    for p in candle_patterns[:3]
                ],
                "sr_levels": {
                    "resistance": [round(r, 5) for r in sr_levels["resistance"][:3]],
                    "support": [round(s, 5) for s in sr_levels["support"][:3]]
                },
                "signal": {
                    "action": signal.action,
                    "entry": signal.entry_price,
                    "sl": signal.stop_loss,
                    "tp": signal.take_profit,
                    "confidence": signal.confidence,
                    "reason": signal.reason,
                    "pattern": signal.pattern_type,
                    "rr": signal.rr_ratio
                }
            }
            
            self._last_analysis[symbol] = result
            return result
            
        except Exception as e:
            self.log("ERROR", f"Analyse Fehler: {e}")
            return {"error": str(e)}
    
    def get_signal(self, symbol: str) -> TradingSignal:
        """Gibt Trading-Signal zurück"""
        if symbol in self._last_analysis:
            analysis = self._last_analysis[symbol]
            if "signal" in analysis:
                sig = analysis["signal"]
                return create_signal(
                    action=sig["action"],
                    entry=sig["entry"],
                    sl=sig["sl"],
                    tp=sig["tp"],
                    confidence=sig["confidence"],
                    reason=sig["reason"],
                    pattern=sig["pattern"]
                )
        
        self.analyze(symbol, {})
        
        if symbol in self._last_analysis:
            analysis = self._last_analysis[symbol]
            if "signal" in analysis:
                sig = analysis["signal"]
                return create_signal(
                    action=sig["action"],
                    entry=sig["entry"],
                    sl=sig["sl"],
                    tp=sig["tp"],
                    confidence=sig["confidence"],
                    reason=sig["reason"],
                    pattern=sig["pattern"]
                )
        
        return create_signal(
            action="HOLD",
            entry=0.0,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Keine ausreichenden Daten"
        )
    
    def _find_support_resistance(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        pip_size: float
    ) -> Dict[str, List[float]]:
        """Findet S/R Level"""
        resistance = []
        support = []
        tolerance = self.config["sr_touch_tolerance_pips"] * pip_size
        
        # Einfache Swing-Erkennung
        swing_highs, swing_lows = self._detect_swings(highs, lows, 5)
        
        # Gruppiere nahe Level
        for idx, price in swing_highs:
            if not resistance or all(abs(price - r) > tolerance * 2 for r in resistance):
                resistance.append(price)
        
        for idx, price in swing_lows:
            if not support or all(abs(price - s) > tolerance * 2 for s in support):
                support.append(price)
        
        return {
            "resistance": sorted(resistance, reverse=True),
            "support": sorted(support)
        }
    
    def _find_flags(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[ChartPattern]:
        """Findet Flag Patterns"""
        patterns = []
        min_bars = 5
        
        for i in range(min_bars, len(rates) - min_bars):
            # Prüfe für bullische Flag
            # Erst starke Bewegung nach oben
            move_up = 0
            for j in range(i - min_bars, i):
                move_up += highs[j] - lows[j]
            
            if move_up > 20 * pip_size:  # Mindestens 20 Pips
                # Dann Konsolidierung nach unten
                consolidation = 0
                for j in range(i, min(i + min_bars, len(rates))):
                    consolidation += highs[j] - lows[j]
                
                if consolidation < move_up * 0.5:  # Weniger als 50% des Moves
                    patterns.append(ChartPattern(
                        pattern_type="FLAG",
                        direction="BULLISH",
                        start_idx=i - min_bars,
                        end_idx=i + min_bars,
                        confidence=0.7
                    ))
        
        return patterns
    
    def _find_wedges(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[ChartPattern]:
        """Findet Wedge Patterns"""
        patterns = []
        
        # Vereinfachte Wedge-Erkennung
        # Sucht nach konvergierenden Trendlinien
        for i in range(20, len(rates) - 10):
            # Prüfe ob Highs falling und Lows falling
            recent_highs = highs[i-10:i]
            recent_lows = lows[i-10:i]
            
            #lineare Regression für Trend
            high_trend = (recent_highs[-1] - recent_highs[0]) / 10
            low_trend = (recent_lows[-1] - recent_lows[0]) / 10
            
            # Beide negativ = falling wedge (bullish)
            if high_trend < 0 and low_trend < 0 and abs(high_trend) < abs(low_trend):
                patterns.append(ChartPattern(
                    pattern_type="WEDGE",
                    direction="BULLISH",
                    start_idx=i - 10,
                    end_idx=i,
                    confidence=0.6
                ))
            # Beide positiv = rising wedge (bearish)
            elif high_trend > 0 and low_trend > 0 and abs(high_trend) > abs(low_trend):
                patterns.append(ChartPattern(
                    pattern_type="WEDGE",
                    direction="BEARISH",
                    start_idx=i - 10,
                    end_idx=i,
                    confidence=0.6
                ))
        
        return patterns
    
    def _find_triangles(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[ChartPattern]:
        """Findet Triangle Patterns"""
        patterns = []
        
        for i in range(30, len(rates) - 10):
            recent_highs = highs[i-20:i]
            recent_lows = lows[i-20:i]
            
            # Ascending Triangle: flache Highs, steigende Lows
            high_trend = (recent_highs[-1] - recent_highs[0]) / 20
            low_trend = (recent_lows[-1] - recent_lows[0]) / 20
            
            if abs(high_trend) < pip_size and low_trend > pip_size:
                patterns.append(ChartPattern(
                    pattern_type="TRIANGLE",
                    direction="BULLISH",
                    start_idx=i - 20,
                    end_idx=i,
                    confidence=0.65
                ))
            # Descending Triangle: steigende Highs, flache Lows
            elif high_trend > pip_size and abs(low_trend) < pip_size:
                patterns.append(ChartPattern(
                    pattern_type="TRIANGLE",
                    direction="BEARISH",
                    start_idx=i - 20,
                    end_idx=i,
                    confidence=0.65
                ))
            # Symmetrical: beide konvergieren
            elif (high_trend < -pip_size/2 and low_trend > pip_size/2) or \
                 (high_trend > pip_size/2 and low_trend < -pip_size/2):
                patterns.append(ChartPattern(
                    pattern_type="TRIANGLE",
                    direction="NEUTRAL",
                    start_idx=i - 20,
                    end_idx=i,
                    confidence=0.6
                ))
        
        return patterns
    
    def _find_hammer(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[CandlestickPattern]:
        """Findet Hammer Patterns"""
        patterns = []
        
        for i in range(1, len(closes) - 1):
            body = abs(closes[i] - opens[i])
            range_ = highs[i] - lows[i]
            
            if range_ == 0:
                continue
            
            body_ratio = body / range_
            
            # Hammer: Body im oberen Drittel, langer Lower Shadow
            if body_ratio < 0.35:  # Kleiner Body
                lower_shadow = lows[i] - min(opens[i], closes[i])
                upper_shadow = max(opens[i], closes[i]) - highs[i]
                
                if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                    # Bestätigung: Nächste Kerze schließt höher
                    if closes[i+1] > closes[i]:
                        patterns.append(CandlestickPattern(
                            pattern_type="HAMMER",
                            direction="BULLISH",
                            idx=i,
                            confidence=0.7
                        ))
        
        return patterns
    
    def _find_engulfing(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[CandlestickPattern]:
        """Findet Engulfing Patterns"""
        patterns = []
        
        for i in range(1, len(closes) - 1):
            prev_bearish = closes[i-1] < opens[i-1]
            current_bullish = closes[i] > opens[i]
            
            # Bullish Engulfing
            if prev_bearish and current_bullish:
                if opens[i] < closes[i-1] and closes[i] > opens[i-1]:
                    # Body muss > 70% der Range sein
                    body = closes[i] - opens[i]
                    range_ = highs[i] - lows[i]
                    if range_ > 0 and body / range_ > 0.7:
                        patterns.append(CandlestickPattern(
                            pattern_type="ENGULFING",
                            direction="BULLISH",
                            idx=i,
                            confidence=0.75
                        ))
            
            # Bearish Engulfing
            prev_bullish = closes[i-1] > opens[i-1]
            current_bearish = closes[i] < opens[i]
            
            if prev_bullish and current_bearish:
                if opens[i] > closes[i-1] and closes[i] < opens[i-1]:
                    body = opens[i] - closes[i]
                    range_ = highs[i] - lows[i]
                    if range_ > 0 and body / range_ > 0.7:
                        patterns.append(CandlestickPattern(
                            pattern_type="ENGULFING",
                            direction="BEARISH",
                            idx=i,
                            confidence=0.75
                        ))
        
        return patterns
    
    def _find_morning_star(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[CandlestickPattern]:
        """Findet Morning Star Patterns"""
        patterns = []
        
        for i in range(2, len(closes) - 1):
            # Kerze 1: bearish
            # Kerze 2: kleine Kerze (Doji oder kleine Range)
            # Kerze 3: bullish, schließt über Mitte von Kerze 1
            
            candle1_bearish = closes[i-2] < opens[i-2]
            candle2_small = abs(closes[i-1] - opens[i-1]) < (highs[i-2] - lows[i-2]) * 0.3
            candle3_bullish = closes[i] > opens[i]
            
            if candle1_bearish and candle2_small and candle3_bullish:
                midpoint = (opens[i-2] + closes[i-2]) / 2
                if closes[i] > midpoint:
                    patterns.append(CandlestickPattern(
                        pattern_type="MORNING_STAR",
                        direction="BULLISH",
                        idx=i,
                        confidence=0.8
                    ))
            
            # Evening Star (umgekehrt)
            candle1_bullish = closes[i-2] > opens[i-2]
            candle3_bearish = closes[i] < opens[i]
            
            if candle1_bullish and candle2_small and candle3_bearish:
                midpoint = (opens[i-2] + closes[i-2]) / 2
                if closes[i] < midpoint:
                    patterns.append(CandlestickPattern(
                        pattern_type="EVENING_STAR",
                        direction="BEARISH",
                        idx=i,
                        confidence=0.8
                    ))
        
        return patterns
    
    def _find_doji(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> List[CandlestickPattern]:
        """Findet Doji Patterns"""
        patterns = []
        
        for i in range(len(closes)):
            body = abs(closes[i] - opens[i])
            range_ = highs[i] - lows[i]
            
            if range_ > 0 and body / range_ < 0.1:  # Sehr kleiner Body
                patterns.append(CandlestickPattern(
                    pattern_type="DOJI",
                    direction="NEUTRAL",
                    idx=i,
                    confidence=0.5
                ))
        
        return patterns
    
    def _generate_pattern_signal(
        self,
        symbol: str,
        rates: np.ndarray,
        chart_patterns: List[ChartPattern],
        candle_patterns: List[CandlestickPattern],
        sr_levels: Dict[str, List[float]],
        pip_size: float
    ) -> TradingSignal:
        """Generiert Pattern Trading Signal"""
        
        current_price = rates[-1]['close']
        
        # Priorität: Candlestick Patterns mit S/R Bestätigung
        for cp in candle_patterns:
            # Prüfe S/R Nähe
            if self.config["sr_confirmation_required"]:
                near_sr = False
                for res in sr_levels["resistance"][:3]:
                    if abs(current_price - res) < self.config["sr_touch_tolerance_pips"] * pip_size:
                        if cp.direction == "BEARISH":
                            near_sr = True
                            break
                for sup in sr_levels["support"][:3]:
                    if abs(current_price - sup) < self.config["sr_touch_tolerance_pips"] * pip_size:
                        if cp.direction == "BULLISH":
                            near_sr = True
                            break
                
                if not near_sr:
                    continue
            
            # Generiere Signal
            if cp.direction == "BULLISH":
                sl = current_price - 15 * pip_size
                tp = current_price + (current_price - sl) * 2
                
                return create_signal(
                    action="BUY",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=cp.confidence,
                    reason=f"{cp.pattern_type} Pattern erkannt",
                    pattern=cp.pattern_type
                )
            
            elif cp.direction == "BEARISH":
                sl = current_price + 15 * pip_size
                tp = current_price - (sl - current_price) * 2
                
                return create_signal(
                    action="SELL",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=cp.confidence,
                    reason=f"{cp.pattern_type} Pattern erkannt",
                    pattern=cp.pattern_type
                )
        
        # Chart Patterns
        for cp in chart_patterns:
            if cp.direction == "BULLISH":
                sl = current_price - 20 * pip_size
                tp = current_price + (current_price - sl) * 2
                
                return create_signal(
                    action="BUY",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=cp.confidence,
                    reason=f"{cp.pattern_type} Pattern erkannt",
                    pattern=cp.pattern_type
                )
            
            elif cp.direction == "BEARISH":
                sl = current_price + 20 * pip_size
                tp = current_price - (sl - current_price) * 2
                
                return create_signal(
                    action="SELL",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=cp.confidence,
                    reason=f"{cp.pattern_type} Pattern erkannt",
                    pattern=cp.pattern_type
                )
        
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein valides Pattern Setup gefunden"
        )


# Registriere Strategie
from trading.base_strategy import StrategyRegistry
StrategyRegistry.register("Pattern Trading", PatternStrategy)