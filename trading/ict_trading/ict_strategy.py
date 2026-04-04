#!/usr/bin/env python3
"""
ICT Orderblock / Supply-Demand Trading Strategy
================================================
Implementiert Orderblock-Erkennung, Fair Value Gaps, Liquidity Pools
und Break of Structure für präzise Entry-Points.

Konzepte:
- Orderblock: Zone von der starke impulsive Moves gestartet wurden
- Fair Value Gap (FVG): Bereich mit "leerem" Volumen zwischen Kerzen
- Liquidity Pool: Bereich wo Stop-Losses gesammelt werden
- Break of Structure (BOS): Kurs durchbricht vorheriges Hoch/Tief
- Return-to-Zone: Preis kehrt zurück um in Trendrichtung einzusteigen
"""

import numpy as np
import MetaTrader5 as mt5
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from trading.base_strategy import BaseStrategy, TradingSignal, MarketPhase, create_signal


@dataclass
class OrderBlock:
    """Orderblock Datenstruktur"""
    start_idx: int
    end_idx: int
    high: float
    low: float
    direction: str  # "BULLISH" oder "BEARISH"
    strength: float = 0.0
    triggered: bool = False
    touch_count: int = 0


@dataclass
class FairValueGap:
    """Fair Value Gap Datenstruktur"""
    start_idx: int
    end_idx: int
    high: float
    low: float
    direction: str
    size_pips: float = 0.0
    strength: str = "MODERATE"  # "WEAK", "MODERATE", "STRONG"


@dataclass
class LiquidityZone:
    """Liquidity Pool Datenstruktur"""
    price: float
    zone_type: str  # "STOP_HUNT", "EQUAL_HIGH", "EQUAL_LOW", "FIB"
    strength: float = 0.0
    touched: bool = False


class ICTStrategy(BaseStrategy):
    """
    ICT Orderblock Trading Strategy
    
    Implementiert:
    - Orderblock-Erkennung mit Momentum-Bestätigung
    - Fair Value Gap (FVG) Analyse
    - Liquidity Pool Erkennung
    - Break of Structure (BOS) Detection
    - Return-to-Zone Entry Trigger
    """
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            # Orderblock-Einstellungen
            "ob_lookback_bars": 100,
            "ob_min_momentum_pips": 20,
            "ob_max_retest_bars": 10,
            "ob_confluence_required": True,
            
            # FVG-Einstellungen
            "fvg_min_gap_pips": 5,
            "fvg_weak_threshold": 3,
            "fvg_strong_threshold": 10,
            
            # Liquidity
            "liquidity_sweep_tolerance": 2,
            "equal_highs_window": 5,
            "fibonacci_levels": [0.618, 0.786, 1.0, 1.272],
            
            # Einstiegs-Trigger
            "entry_trigger": "RETURN_TO_ZONE",
            "confirmation_bars": 1,
            
            # BOS Einstellungen
            "bos_min_break_pips": 5,
            
            # Stop-Loss
            "sl_placement": "BELOW_OB",
            "sl_buffer_pips": 5,
            
            # Take-Profit
            "tp_zones": [
                {"target": "NEXT_LIQUIDITY", "rr": 1.0},
                {"target": "PREVIOUS_STRUCTURE", "rr": 1.5},
                {"target": "EXTREME_HIGH_LOW", "rr": 2.0}
            ],
            
            # Risiko
            "min_rr_ratio": 1.5,
            "max_risk_percent": 1.0,
            
            # Marktphasen
            "allowed_market_phases": ["TRENDING", "BOUTS"],
            "range_filter_enabled": True
        }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # Cache für Berechnungen
        self._order_blocks: Dict[str, List[OrderBlock]] = {}
        self._fvgs: Dict[str, List[FairValueGap]] = {}
        self._liquidity_zones: Dict[str, List[LiquidityZone]] = {}
        self._last_analysis: Dict[str, Dict] = {}
        
        self.log("INFO", "ICT Strategy initialisiert")
    
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt vollständige ICT-Analyse durch.
        
        Returns:
            dict mit:
            - order_blocks: Liste gefundener Orderblocks
            - fvgs: Liste der Fair Value Gaps
            - liquidity_zones: Liquidity Pools
            - market_structure: Trend-Analyse
            - signals: Generierte Signale
        """
        try:
            # Marktdaten holen
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, self.config["ob_lookback_bars"])
            if rates is None or len(rates) < 50:
                return {"error": "Unzureichende Marktdaten"}
            
            closes = np.array([r['close'] for r in rates], dtype=float)
            highs = np.array([r['high'] for r in rates], dtype=float)
            lows = np.array([r['low'] for r in rates], dtype=float)
            volumes = np.array([r['tick_volume'] for r in rates], dtype=float)
            
            pip_size = self._get_pip_size(symbol)
            
            # 1. Orderblocks identifizieren
            order_blocks = self._identify_order_blocks(
                rates, highs, lows, closes, volumes, pip_size
            )
            self._order_blocks[symbol] = order_blocks
            
            # 2. Fair Value Gaps identifizieren
            fvgs = self._identify_fvgs(rates, highs, lows, pip_size)
            self._fvgs[symbol] = fvgs
            
            # 3. Liquidity Zones identifizieren
            liquidity_zones = self._identify_liquidity_zones(
                rates, highs, lows, closes, pip_size
            )
            self._liquidity_zones[symbol] = liquidity_zones
            
            # 4. Marktstruktur analysieren
            structure = self._analyze_market_structure(highs, lows, closes, pip_size)
            
            # 5. Signal generieren
            signal = self._generate_ict_signal(
                symbol, rates, order_blocks, fvgs, liquidity_zones, structure, pip_size
            )
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "order_blocks": [
                    {
                        "direction": ob.direction,
                        "high": ob.high,
                        "low": ob.low,
                        "strength": ob.strength,
                        "triggered": ob.triggered,
                        "touch_count": ob.touch_count
                    }
                    for ob in order_blocks[:5]
                ],
                "fvgs": [
                    {
                        "direction": fvg.direction,
                        "high": fvg.high,
                        "low": fvg.low,
                        "size_pips": fvg.size_pips,
                        "strength": fvg.strength
                    }
                    for fvg in fvgs[:5]
                ],
                "liquidity_zones": [
                    {
                        "price": lz.price,
                        "zone_type": lz.zone_type,
                        "strength": lz.strength
                    }
                    for lz in liquidity_zones[:5]
                ],
                "structure": structure,
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
        # Prüfe ob bereits analysiert
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
        
        # Neue Analyse durchführen
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
        
        # Kein Signal
        return create_signal(
            action="HOLD",
            entry=0.0,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Keine ausreichenden Daten"
        )
    
    def _identify_order_blocks(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        pip_size: float
    ) -> List[OrderBlock]:
        """
        Identifiziert Orderblocks.
        
        Ein Orderblock ist eine Zone von der aus ein starker
        impulsiver Move gestartet wurde.
        """
        order_blocks = []
        min_momentum = self.config["ob_min_momentum_pips"] * pip_size
        
        for i in range(10, len(rates) - 10):
            # Prüfe für bullische Orderblocks
            if i < len(rates) - 5:
                # Starke bullische Kerze
                body = closes[i] - lows[i]
                range_ = highs[i] - lows[i]
                
                if body > 0 and body / range_ > 0.7:  # Starkes Close
                    # Prüfe ob darauf ein impulsiver Move folgte
                    for j in range(i + 1, min(i + 6, len(rates))):
                        move = highs[j] - highs[i]
                        if move > min_momentum:
                            # Gefunden! Markiere als Orderblock
                            ob = OrderBlock(
                                start_idx=i,
                                end_idx=i,
                                high=highs[i],
                                low=lows[i],
                                direction="BULLISH",
                                strength=min(1.0, move / (min_momentum * 2))
                            )
                            order_blocks.append(ob)
                            break
            
            # Prüfe für bearische Orderblocks
            if i < len(rates) - 5:
                body = highs[i] - closes[i]
                range_ = highs[i] - lows[i]
                
                if body > 0 and body / range_ > 0.7:
                    for j in range(i + 1, min(i + 6, len(rates))):
                        move = lows[i] - lows[j]
                        if move > min_momentum:
                            ob = OrderBlock(
                                start_idx=i,
                                end_idx=i,
                                high=highs[i],
                                low=lows[i],
                                direction="BEARISH",
                                strength=min(1.0, move / (min_momentum * 2))
                            )
                            order_blocks.append(ob)
                            break
        
        # Sortiere nach Stärke
        order_blocks.sort(key=lambda x: x.strength, reverse=True)
        return order_blocks[:10]
    
    def _identify_fvgs(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        pip_size: float
    ) -> List[FairValueGap]:
        """
        Identifiziert Fair Value Gaps.
        
        Ein FVG ist ein Bereich zwischen zwei Kerzen wo kein
        Volumen gehandelt wurde.
        """
        fvgs = []
        min_gap = self.config["fvg_min_gap_pips"] * pip_size
        
        for i in range(1, len(rates) - 1):
            # Bullisches FVG: low[i] > high[i+1]
            if lows[i] > highs[i + 1]:
                gap_size = lows[i] - highs[i + 1]
                if gap_size >= min_gap:
                    strength = "WEAK"
                    if gap_size > self.config["fvg_strong_threshold"] * pip_size:
                        strength = "STRONG"
                    elif gap_size > self.config["fvg_weak_threshold"] * pip_size:
                        strength = "MODERATE"
                    
                    fvg = FairValueGap(
                        start_idx=i + 1,
                        end_idx=i,
                        high=lows[i],
                        low=highs[i + 1],
                        direction="BULLISH",
                        size_pips=gap_size / pip_size,
                        strength=strength
                    )
                    fvgs.append(fvg)
            
            # Bearisches FVG: high[i] < low[i+1]
            elif highs[i] < lows[i + 1]:
                gap_size = lows[i + 1] - highs[i]
                if gap_size >= min_gap:
                    strength = "WEAK"
                    if gap_size > self.config["fvg_strong_threshold"] * pip_size:
                        strength = "STRONG"
                    elif gap_size > self.config["fvg_weak_threshold"] * pip_size:
                        strength = "MODERATE"
                    
                    fvg = FairValueGap(
                        start_idx=i,
                        end_idx=i + 1,
                        high=lows[i + 1],
                        low=highs[i],
                        direction="BEARISH",
                        size_pips=gap_size / pip_size,
                        strength=strength
                    )
                    fvgs.append(fvg)
        
        # Sortiere nach Stärke
        fvgs.sort(key=lambda x: x.size_pips, reverse=True)
        return fvgs[:10]
    
    def _identify_liquidity_zones(
        self,
        rates: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> List[LiquidityZone]:
        """
        Identifiziert Liquidity Pools.
        
        Liquidity Pools sind Bereiche wo viele Stop-Losses
        gesammelt werden (Equal Highs, Equal Lows, etc.)
        """
        zones = []
        window = self.config["equal_highs_window"]
        tolerance = self.config["liquidity_sweep_tolerance"] * pip_size
        
        # Equal Highs finden
        for i in range(window, len(highs) - window):
            equal_count = 0
            for j in range(max(0, i - window), min(len(highs), i + window + 1)):
                if abs(highs[i] - highs[j]) < tolerance:
                    equal_count += 1
            
            if equal_count >= 2:
                # Prüfe ob bereits vorhanden
                existing = [z for z in zones if abs(z.price - highs[i]) < tolerance * 2]
                if not existing:
                    zone = LiquidityZone(
                        price=highs[i],
                        zone_type="EQUAL_HIGH",
                        strength=min(1.0, equal_count / window)
                    )
                    zones.append(zone)
        
        # Equal Lows finden
        for i in range(window, len(lows) - window):
            equal_count = 0
            for j in range(max(0, i - window), min(len(lows), i + window + 1)):
                if abs(lows[i] - lows[j]) < tolerance:
                    equal_count += 1
            
            if equal_count >= 2:
                existing = [z for z in zones if abs(z.price - lows[i]) < tolerance * 2]
                if not existing:
                    zone = LiquidityZone(
                        price=lows[i],
                        zone_type="EQUAL_LOW",
                        strength=min(1.0, equal_count / window)
                    )
                    zones.append(zone)
        
        # Fibonacci Liquidity
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        range_ = recent_high - recent_low
        
        for fib_level in self.config["fibonacci_levels"]:
            # Support Level
            fib_support = recent_low + fib_level * range_
            zone = LiquidityZone(
                price=fib_support,
                zone_type="FIB",
                strength=0.5
            )
            zones.append(zone)
        
        # Sortiere nach Stärke
        zones.sort(key=lambda x: x.strength, reverse=True)
        return zones[:10]
    
    def _analyze_market_structure(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        pip_size: float
    ) -> Dict[str, Any]:
        """Analysiert Marktstruktur für Trend"""
        swing_highs, swing_lows = self._detect_swings(highs, lows, 5)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {
                "trend": "NEUTRAL",
                "direction": "NEUTRAL",
                "swing_highs": [],
                "swing_lows": [],
                "bos": None
            }
        
        # HH/HL oder LH/LL
        hh = swing_highs[-1][1] > swing_highs[-2][1]
        hl = swing_lows[-1][1] > swing_lows[-2][1]
        lh = swing_highs[-1][1] < swing_highs[-2][1]
        ll = swing_lows[-1][1] < swing_lows[-2][1]
        
        if hh and hl:
            trend = "BULLISH"
            direction = "UP"
        elif lh and ll:
            trend = "BEARISH"
            direction = "DOWN"
        else:
            trend = "NEUTRAL"
            direction = "NEUTRAL"
        
        # BOS Detection
        bos = None
        min_break = self.config["bos_min_break_pips"] * pip_size
        
        if len(swing_highs) >= 2:
            last_high = swing_highs[-1][1]
            prev_high = swing_highs[-2][1]
            if closes[-1] > last_high and (last_high - prev_high) > min_break:
                bos = "BULLISH"
        
        if len(swing_lows) >= 2:
            last_low = swing_lows[-1][1]
            prev_low = swing_lows[-2][1]
            if closes[-1] < last_low and (prev_low - last_low) > min_break:
                bos = "BEARISH"
        
        return {
            "trend": trend,
            "direction": direction,
            "swing_highs": [(idx, round(price, 5)) for idx, price in swing_highs[-5:]],
            "swing_lows": [(idx, round(price, 5)) for idx, price in swing_lows[-5:]],
            "bos": bos
        }
    
    def _generate_ict_signal(
        self,
        symbol: str,
        rates: np.ndarray,
        order_blocks: List[OrderBlock],
        fvgs: List[FairValueGap],
        liquidity_zones: List[LiquidityZone],
        structure: Dict,
        pip_size: float
    ) -> TradingSignal:
        """Generiert ICT Trading Signal"""
        
        current_price = rates[-1]['close']
        direction = structure.get("direction", "NEUTRAL")
        trend = structure.get("trend", "NEUTRAL")
        
        # Prüfe Marktphase
        if self.config.get("range_filter_enabled"):
            allowed = self.config.get("allowed_market_phases", ["TRENDING"])
            if trend == "NEUTRAL" and "RANGE" in allowed:
                pass  # Erlaubt
            elif trend not in allowed:
                return create_signal(
                    action="HOLD",
                    entry=current_price,
                    sl=0.0,
                    tp=0.0,
                    confidence=0.0,
                    reason=f"Marktphase nicht geeignet: {trend}",
                    pattern="MARKET_PHASE_FILTER"
                )
        
        # Return-to-Zone Trigger
        if self.config["entry_trigger"] == "RETURN_TO_ZONE":
            return self._return_to_zone_signal(
                symbol, current_price, order_blocks, fvgs, 
                liquidity_zones, structure, pip_size
            )
        
        # FVG Break Trigger
        elif self.config["entry_trigger"] == "FVG_BREAK":
            return self._fvg_break_signal(
                symbol, current_price, fvgs, structure, pip_size
            )
        
        # BOS Trigger
        elif self.config["entry_trigger"] == "BOS_CONFIRM":
            return self._bos_signal(
                symbol, current_price, structure, pip_size
            )
        
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein gültiger Trigger konfiguriert"
        )
    
    def _return_to_zone_signal(
        self,
        symbol: str,
        current_price: float,
        order_blocks: List[OrderBlock],
        fvgs: List[FairValueGap],
        liquidity_zones: List[LiquidityZone],
        structure: Dict,
        pip_size: float,
        rates: np.ndarray = None
    ) -> TradingSignal:
        """Return-to-Zone Entry Trigger"""
        
        direction = structure.get("direction", "NEUTRAL")
        
        if rates is None:
            # Hole aktuelle Daten
            try:
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 5)
            except:
                pass
        
        # Suche nach passendem Orderblock
        for ob in order_blocks:
            if ob.direction == "BULLISH" and direction == "UP":
                # Preis nahe am Orderblock?
                dist_to_ob = abs(current_price - ob.low)
                if dist_to_ob < 10 * pip_size:  # Innerhalb 10 Pips
                    # Bullische Bestätigung?
                    if rates[-1]['close'] > rates[-1]['open']:
                        sl = ob.low - self.config["sl_buffer_pips"] * pip_size
                        tp = current_price + (current_price - sl) * 2
                        
                        return create_signal(
                            action="BUY",
                            entry=current_price,
                            sl=round(sl, 5),
                            tp=round(tp, 5),
                            confidence=0.7,
                            reason=f"Return to Bullish Orderblock (Strength: {ob.strength:.2f})",
                            pattern="ORDER_BLOCK_RETURN"
                        )
            
            elif ob.direction == "BEARISH" and direction == "DOWN":
                dist_to_ob = abs(current_price - ob.high)
                if dist_to_ob < 10 * pip_size:
                    if rates[-1]['close'] < rates[-1]['open']:
                        sl = ob.high + self.config["sl_buffer_pips"] * pip_size
                        tp = current_price - (sl - current_price) * 2
                        
                        return create_signal(
                            action="SELL",
                            entry=current_price,
                            sl=round(sl, 5),
                            tp=round(tp, 5),
                            confidence=0.7,
                            reason=f"Return to Bearish Orderblock (Strength: {ob.strength:.2f})",
                            pattern="ORDER_BLOCK_RETURN"
                        )
        
        # Kein Signal
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein Return-to-Zone Setup gefunden"
        )
    
    def _fvg_break_signal(
        self,
        symbol: str,
        current_price: float,
        fvgs: List[FairValueGap],
        structure: Dict,
        pip_size: float
    ) -> TradingSignal:
        """FVG Break Entry Trigger"""
        
        direction = structure.get("direction", "NEUTRAL")
        
        for fvg in fvgs:
            if fvg.direction == "BULLISH" and direction == "UP":
                # Preis bricht FVG nach oben
                if current_price > fvg.high:
                    sl = fvg.low - self.config["sl_buffer_pips"] * pip_size
                    tp = current_price + (current_price - sl) * 2
                    
                    return create_signal(
                        action="BUY",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason=f"FVG Break (Size: {fvg.size_pips:.1f} pips)",
                        pattern="FVG_BREAK"
                    )
            
            elif fvg.direction == "BEARISH" and direction == "DOWN":
                if current_price < fvg.low:
                    sl = fvg.high + self.config["sl_buffer_pips"] * pip_size
                    tp = current_price - (sl - current_price) * 2
                    
                    return create_signal(
                        action="SELL",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason=f"FVG Break (Size: {fvg.size_pips:.1f} pips)",
                        pattern="FVG_BREAK"
                    )
        
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein FVG Break Setup gefunden"
        )
    
    def _bos_signal(
        self,
        symbol: str,
        current_price: float,
        structure: Dict,
        pip_size: float
    ) -> TradingSignal:
        """Break of Structure Entry Trigger"""
        
        bos = structure.get("bos")
        
        if bos == "BULLISH":
            sl = current_price - 15 * pip_size
            tp = current_price + 30 * pip_size
            
            return create_signal(
                action="BUY",
                entry=current_price,
                sl=round(sl, 5),
                tp=round(tp, 5),
                confidence=0.75,
                reason="Bullish Break of Structure",
                pattern="BOS"
            )
        
        elif bos == "BEARISH":
            sl = current_price + 15 * pip_size
            tp = current_price - 30 * pip_size
            
            return create_signal(
                action="SELL",
                entry=current_price,
                sl=round(sl, 5),
                tp=round(tp, 5),
                confidence=0.75,
                reason="Bearish Break of Structure",
                pattern="BOS"
            )
        
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein BOS erkannt"
        )


# Registriere Strategie
from trading.base_strategy import StrategyRegistry
StrategyRegistry.register("ICT", ICTStrategy)
StrategyRegistry.register("Orderblock", ICTStrategy)
