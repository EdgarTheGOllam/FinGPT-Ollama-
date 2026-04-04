#!/usr/bin/env python3
"""
Structure Trading Strategy - Pure Price Action
================================================
Implementiert reines HH/HL/LH/LL System ohne externe Indikatoren.

Konzepte:
- HH/HL: Higher High / Higher Low = Aufwärtstrend
- LH/LL: Lower High / Lower Low = Abwärtstrend
- Break of Structure (BOS): Durchbruch durch vorheriges Hoch/Tief
- Liquidity Sweep: Stop-Lock-Bereich wird angesteuert
- Change of Character (CHOCH): Trendwende durch Strukturwechsel

Keine externen Indikatoren - rein strukturbasiert!
"""

import numpy as np
import MetaTrader5 as mt5
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from trading.base_strategy import BaseStrategy, TradingSignal, create_signal


@dataclass
class StructureState:
    """Marktstruktur-Zustand"""
    trend: str  # "BULLISH", "BEARISH", "NEUTRAL"
    direction: str  # "UP", "DOWN", "NEUTRAL"
    swing_highs: List[Tuple[int, float]] = field(default_factory=list)
    swing_lows: List[Tuple[int, float]] = field(default_factory=list)
    last_bos: str = ""  # "BULLISH", "BEARISH", ""
    last_choch: str = ""  # "BULLISH", "BEARISH", ""
    liquidity_sweeps: List[str] = field(default_factory=list)


@dataclass
class LiquiditySweep:
    """Liquidity Sweep Datenstruktur"""
    price: float
    sweep_type: str  # "STOP_HUNT", "EQUAL_HIGH", "EQUAL_LOW"
    direction: str
    strength: float = 0.0


class StructureStrategy(BaseStrategy):
    """
    Structure Trading Strategy - Pure Price Action
    
    Implementiert:
    - HH/HL und LH/LL Erkennung
    - Break of Structure (BOS) Detection
    - Liquidity Sweep Erkennung
    - Change of Character (CHOCH) Detection
    - Reines Preis-Action System ohne Indikatoren
    """
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            # Struktur-Einstellungen
            "structure_lookback": 50,
            "swing_detection_window": 5,
            "fractal_period": 5,
            
            # BOS
            "bos_confirmation_bars": 1,
            "bos_min_break_pips": 5,
            "bos_requires_volume": False,
            
            # Liquidity
            "liquidity_sweep_detection": True,
            "stop_hunt_buffer_pips": 2,
            "equal_highs_min_touches": 2,
            "fib_liquidity_levels": [0.618, 0.786, 1.0],
            
            # CHOCH
            "choch_detection": True,
            "choch_require_fvg": True,
            
            # Einstiegs-Trigger
            "entry_on_bos": True,
            "entry_on_liquidity_sweep": True,
            "entry_on_choch": True,
            
            # Stop-Loss
            "sl_below_structure": True,
            "sl_buffer_pips": 5,
            
            # Take-Profit
            "tp_next_structure": True,
            "tp_2r": True,
            "tp_3r": True,
            
            # Risiko
            "min_rr_ratio": 2.0,
            "max_risk_percent": 1.5,
            
            # Marktphasen
            "allowed_phases": ["TRENDING", "BOUTS"]
        }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # Cache
        self._structure_cache: Dict[str, StructureState] = {}
        self._last_analysis: Dict[str, Dict] = {}
        
        self.log("INFO", "Structure Strategy initialisiert")
    
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Structure-Analyse durch"""
        try:
            rates = mt5.copy_rates_from_pos(
                symbol, mt5.TIMEFRAME_M15, 0, 
                self.config["structure_lookback"]
            )
            if rates is None or len(rates) < 30:
                return {"error": "Unzureichende Marktdaten"}
            
            pip_size = self._get_pip_size(symbol)
            
            closes = np.array([r['close'] for r in rates], dtype=float)
            highs = np.array([r['high'] for r in rates], dtype=float)
            lows = np.array([r['low'] for r in rates], dtype=float)
            
            # Analysiere Marktstruktur
            structure = self._analyze_structure(highs, lows, closes, pip_size)
            self._structure_cache[symbol] = structure
            
            # Finde Liquidity Sweeps
            liquidity_sweeps = self._find_liquidity_sweeps(
                rates, highs, lows, closes, pip_size
            )
            
            # Generiere Signal
            signal = self._generate_structure_signal(
                symbol, rates, structure, liquidity_sweeps, pip_size
            )
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "structure": {
                    "trend": structure.trend,
                    "direction": structure.direction,
                    "swing_highs": [
                        (idx, round(price, 5)) 
                        for idx, price in structure.swing_highs[-5:]
                    ],
                    "swing_lows": [
                        (idx, round(price, 5)) 
                        for idx, price in structure.swing_lows[-5:]
                    ],
                    "last_bos": structure.last_bos,
                    "last_choch": structure.last_choch
                },
                "liquidity_sweeps": [
                    {
                        "price": round(ls.price, 5),
                        "type": ls.sweep_type,
                        "direction": ls.direction
                    }
                    for ls in liquidity_sweeps[:3]
                ],
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
    
    def _analyze_structure(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> StructureState:
        """
        Analysiert Marktstruktur: HH/HL/LH/LL
        """
        state = StructureState(trend="NEUTRAL", direction="NEUTRAL")
        
        # Erkenne Swing Highs und Lows
        swing_highs, swing_lows = self._detect_swings(
            highs, lows, self.config["fractal_period"]
        )
        
        state.swing_highs = swing_highs
        state.swing_lows = swing_lows
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return state
        
        # Analysiere HH/HL Sequenz
        last_high = swing_highs[-1][1]
        prev_high = swing_highs[-2][1]
        last_low = swing_lows[-1][1]
        prev_low = swing_lows[-2][1]
        
        # Higher High / Higher Low = Bullish
        hh = last_high > prev_high
        hl = last_low > prev_low
        
        # Lower High / Lower Low = Bearish
        lh = last_high < prev_high
        ll = last_low < prev_low
        
        if hh and hl:
            state.trend = "BULLISH"
            state.direction = "UP"
        elif lh and ll:
            state.trend = "BEARISH"
            state.direction = "DOWN"
        else:
            state.trend = "NEUTRAL"
            state.direction = "NEUTRAL"
        
        # BOS Detection
        min_break = self.config["bos_min_break_pips"] * pip_size
        
        # Bullish BOS: Preis bricht letztes High
        if len(swing_highs) >= 2:
            if closes[-1] > last_high and (last_high - prev_high) > min_break:
                state.last_choch = "BULLISH"
                state.last_bos = "BULLISH"
        
        # Bearish BOS: Preis bricht letztes Low
        if len(swing_lows) >= 2:
            if closes[-1] < last_low and (prev_low - last_low) > min_break:
                state.last_choch = "BEARISH"
                state.last_bos = "BEARISH"
        
        # CHOCH Detection (Change of Character)
        if self.config["choch_detection"]:
            # Wenn vorheriger Trend bullish und jetzt bearish BOS
            if state.trend == "BULLISH" and state.last_bos == "BEARISH":
                state.last_choch = "BEARISH"
            # Wenn vorheriger Trend bearish und jetzt bullish BOS
            elif state.trend == "BEARISH" and state.last_bos == "BULLISH":
                state.last_choch = "BULLISH"
        
        return state
    
    def _find_liquidity_sweeps(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[LiquiditySweep]:
        """
        Findet Liquidity Sweeps.
        
        Ein Liquidity Sweep occurs wenn der Preis einen Bereich
        mit gestoppten Orders "sweept" (ansteuert und durchbricht).
        """
        sweeps = []
        window = 10
        tolerance = self.config["stop_hunt_buffer_pips"] * pip_size
        
        # Suche nach Equal Highs
        for i in range(window, len(highs) - window):
            equal_count = 0
            for j in range(max(0, i - window), min(len(highs), i + window + 1)):
                if abs(highs[i] - highs[j]) < tolerance:
                    equal_count += 1
            
            if equal_count >= self.config["equal_highs_min_touches"]:
                # Preis nähert sich diesem Bereich
                if closes[-1] > highs[i]:
                    sweeps.append(LiquiditySweep(
                        price=highs[i],
                        sweep_type="STOP_HUNT",
                        direction="UP",
                        strength=min(1.0, equal_count / window)
                    ))
        
        # Suche nach Equal Lows
        for i in range(window, len(lows) - window):
            equal_count = 0
            for j in range(max(0, i - window), min(len(lows), i + window + 1)):
                if abs(lows[i] - lows[j]) < tolerance:
                    equal_count += 1
            
            if equal_count >= self.config["equal_highs_min_touches"]:
                if closes[-1] < lows[i]:
                    sweeps.append(LiquiditySweep(
                        price=lows[i],
                        sweep_type="STOP_HUNT",
                        direction="DOWN",
                        strength=min(1.0, equal_count / window)
                    ))
        
        return sweeps[:5]
    
    def _generate_structure_signal(
        self,
        symbol: str,
        rates: np.ndarray,
        structure: StructureState,
        liquidity_sweeps: List[LiquiditySweep],
        pip_size: float
    ) -> TradingSignal:
        """Generiert Structure Trading Signal"""
        
        current_price = rates[-1]['close']
        
        # BOS Entry
        if self.config["entry_on_bos"] and structure.last_bos:
            if structure.last_bos == "BULLISH":
                sl = current_price - 20 * pip_size
                tp = current_price + (current_price - sl) * 2.5
                
                return create_signal(
                    action="BUY",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.75,
                    reason="Bullish Break of Structure",
                    pattern="BOS"
                )
            
            elif structure.last_bos == "BEARISH":
                sl = current_price + 20 * pip_size
                tp = current_price - (sl - current_price) * 2.5
                
                return create_signal(
                    action="SELL",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.75,
                    reason="Bearish Break of Structure",
                    pattern="BOS"
                )
        
        # CHOCH Entry
        if self.config["entry_on_choch"] and structure.last_choch:
            if structure.last_choch == "BULLISH":
                sl = current_price - 25 * pip_size
                tp = current_price + (current_price - sl) * 3
                
                return create_signal(
                    action="BUY",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.8,
                    reason="Change of Character - Bullish",
                    pattern="CHOCH"
                )
            
            elif structure.last_choch == "BEARISH":
                sl = current_price + 25 * pip_size
                tp = current_price - (sl - current_price) * 3
                
                return create_signal(
                    action="SELL",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.8,
                    reason="Change of Character - Bearish",
                    pattern="CHOCH"
                )
        
        # Liquidity Sweep Entry
        if self.config["entry_on_liquidity_sweep"] and liquidity_sweeps:
            for sweep in liquidity_sweeps:
                if sweep.direction == "UP":
                    sl = current_price - 15 * pip_size
                    tp = current_price + (current_price - sl) * 2
                    
                    return create_signal(
                        action="BUY",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.65,
                        reason=f"Liquidity Sweep (Price: {sweep.price:.5f})",
                        pattern="LIQUIDITY_SWEEP"
                    )
                
                elif sweep.direction == "DOWN":
                    sl = current_price + 15 * pip_size
                    tp = current_price - (sl - current_price) * 2
                    
                    return create_signal(
                        action="SELL",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.65,
                        reason=f"Liquidity Sweep (Price: {sweep.price:.5f})",
                        pattern="LIQUIDITY_SWEEP"
                    )
        
        # Trend-Follow Entry (bei HH/HL oder LH/LL)
        if structure.trend == "BULLISH" and structure.direction == "UP":
            # Einstieg bei Retest eines vorherigen Lows
            if len(structure.swing_lows) >= 2:
                last_low = structure.swing_lows[-1][1]
                if abs(current_price - last_low) < 15 * pip_size:
                    sl = last_low - self.config["sl_buffer_pips"] * pip_size
                    tp = current_price + (current_price - sl) * 2
                    
                    return create_signal(
                        action="BUY",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason="Trend Follow - HH/HL",
                        pattern="TREND_FOLLOW"
                    )
        
        elif structure.trend == "BEARISH" and structure.direction == "DOWN":
            if len(structure.swing_highs) >= 2:
                last_high = structure.swing_highs[-1][1]
                if abs(current_price - last_high) < 15 * pip_size:
                    sl = last_high + self.config["sl_buffer_pips"] * pip_size
                    tp = current_price - (sl - current_price) * 2
                    
                    return create_signal(
                        action="SELL",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason="Trend Follow - LH/LL",
                        pattern="TREND_FOLLOW"
                    )
        
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein Structure Setup gefunden"
        )


# Registriere Strategie
from trading.base_strategy import StrategyRegistry
StrategyRegistry.register("Structure Trading", StructureStrategy)
StrategyRegistry.register("Pure Price Action", StructureStrategy)
