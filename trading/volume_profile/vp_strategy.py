#!/usr/bin/env python3
"""
Market Profile / Volume Profile Trading Strategy
==================================================
Implementiert Value Area (VA), Point of Control (POC),
High Volume Nodes (HVN), Low Volume Nodes (LVN) und Day Types.

Konzepte:
- Value Area (VA): Bereich wo X% des Volumens stattfand (typisch 70%)
- Point of Control (POC): Preis mit höchstem Volumen
- High Volume Node (HVN): Volume-Peak = magnetischer Preis
- Low Volume Node (LVN): Volume-Tal = Unterstützungs-/Widerstandszonen
- Day Types: Normal Day, Trend Day, Double Distribution, Neutral Day
"""

import numpy as np
import MetaTrader5 as mt5
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from trading.base_strategy import BaseStrategy, TradingSignal, MarketPhase, create_signal


@dataclass
class VolumeProfile:
    """Volume Profile Datenstruktur"""
    poc: float = 0.0  # Point of Control
    poc_idx: int = 0
    va_high: float = 0.0  # Value Area High
    va_low: float = 0.0  # Value Area Low
    bin_volumes: List[float] = field(default_factory=list)
    bin_prices: List[float] = field(default_factory=list)
    hvns: List[float] = field(default_factory=list)  # High Volume Nodes
    lvns: List[float] = field(default_factory=list)  # Low Volume Nodes
    total_volume: float = 0.0


@dataclass
class DayType:
    """Day Type Klassifikation"""
    type: str  # "NORMAL", "TREND", "DOUBLE_DISTRIBUTION", "NEUTRAL"
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class VPStrategy(BaseStrategy):
    """
    Volume Profile Trading Strategy
    
    Implementiert:
    - Volume Profile Berechnung (VA, POC, HVN, LVN)
    - Day Type Classification
    - VA Breakout Trading
    - POC Retest Trading
    - HVN/LVN basierte Einstiege
    """
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            # Volume Profile Einstellungen
            "vp_bars": 20,
            "vp_bins": 20,
            "value_area_pct": 70,
            
            # POC-Einstellungen
            "poc_lookback": 3,
            "poc_weighted": True,
            
            # HVN/LVN
            "hvn_threshold": 1.5,
            "lvn_threshold": 0.5,
            
            # Day Type Classification
            "trend_threshold_pct": 0.8,
            "normal_range_pct": 0.5,
            "dd_min_touches": 2,
            
            # Einstiegs-Trigger
            "entry_on_poc_retest": True,
            "entry_on_hvn_bounce": True,
            "entry_on_va_break": True,
            
            # Stop-Loss
            "sl_outside_va": True,
            "sl_buffer_pips": 5,
            
            # Take-Profit
            "tp_poc": True,
            "tp_opposite_va": True,
            "tp_2r": True,
            
            # Risiko
            "min_rr_ratio": 1.5,
            
            # Marktphasen
            "allowed_phases": ["ALL"]
        }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # Cache
        self._vp_cache: Dict[str, VolumeProfile] = {}
        self._day_type_cache: Dict[str, DayType] = {}
        self._last_analysis: Dict[str, Dict] = {}
        
        self.log("INFO", "Volume Profile Strategy initialisiert")
    
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Volume Profile Analyse durch"""
        try:
            # Hole Marktdaten
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, self.config["vp_bars"])
            if rates is None or len(rates) < 10:
                return {"error": "Unzureichende Marktdaten"}
            
            pip_size = self._get_pip_size(symbol)
            
            # Berechne Volume Profile
            vp = self._calculate_volume_profile(rates, pip_size)
            self._vp_cache[symbol] = vp
            
            # Klassifiziere Day Type
            day_type = self._classify_day_type(rates, vp, pip_size)
            self._day_type_cache[symbol] = day_type
            
            # Generiere Signal
            signal = self._generate_vp_signal(symbol, rates, vp, day_type, pip_size)
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "volume_profile": {
                    "poc": round(vp.poc, 5),
                    "va_high": round(vp.va_high, 5),
                    "va_low": round(vp.va_low, 5),
                    "hvns": [round(h, 5) for h in vp.hvns],
                    "lvns": [round(l, 5) for l in vp.lvns],
                    "total_volume": vp.total_volume
                },
                "day_type": {
                    "type": day_type.type,
                    "confidence": day_type.confidence,
                    "details": day_type.details
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
    
    def _calculate_volume_profile(self, rates: np.ndarray, pip_size: float) -> VolumeProfile:
        """
        Berechnet Volume Profile.
        
        Teilt den Preisbereich in Bins auf und summiert das Volumen pro Bin.
        """
        bins = self.config["vp_bins"]
        
        # Berechne Preisrange
        highs = np.array([r['high'] for r in rates])
        lows = np.array([r['low'] for r in rates])
        volumes = np.array([r['tick_volume'] for r in rates])
        
        min_price = min(lows)
        max_price = max(highs)
        price_range = max_price - min_price
        
        if price_range == 0:
            return VolumeProfile()
        
        bin_size = price_range / bins
        
        # Initialisiere Bins
        bin_volumes = [0.0] * bins
        bin_prices = []
        
        for i in range(bins):
            bin_prices.append(min_price + (i + 0.5) * bin_size)
        
        # Verteile Volumen auf Bins
        for i, rate in enumerate(rates):
            avg_price = (rate['high'] + rate['low']) / 2
            vol = rate['tick_volume']
            
            bin_idx = min(int((avg_price - min_price) / bin_size), bins - 1)
            if 0 <= bin_idx < bins:
                bin_volumes[bin_idx] += vol
        
        # POC = Bin mit höchstem Volumen
        total_volume = sum(bin_volumes)
        poc_idx = bin_volumes.index(max(bin_volumes)) if bin_volumes else 0
        poc = bin_prices[poc_idx] if bin_prices else 0
        
        # Value Area
        va_pct = self.config["value_area_pct"]
        target_vol = total_volume * (va_pct / 100)
        
        # Sortiere Bins nach Volumen (absteigend)
        sorted_bins = sorted(
            [(i, v) for i, v in enumerate(bin_volumes)],
            key=lambda x: -x[1]
        )
        
        va_vol_acc = 0
        va_bins = []
        for idx, vol in sorted_bins:
            if va_vol_acc >= target_vol:
                break
            va_bins.append(idx)
            va_vol_acc += vol
        
        if va_bins:
            va_high_idx = max(va_bins)
            va_low_idx = min(va_bins)
            va_high = min_price + (va_high_idx + 1) * bin_size
            va_low = min_price + va_low_idx * bin_size
        else:
            va_high = max_price
            va_low = min_price
        
        # HVN und LVN
        avg_volume = total_volume / bins if bins > 0 else 1
        hvn_threshold = avg_volume * self.config["hvn_threshold"]
        lvn_threshold = avg_volume * self.config["lvn_threshold"]
        
        hvns = []
        lvns = []
        
        for i, vol in enumerate(bin_volumes):
            if vol >= hvn_threshold:
                hvns.append(bin_prices[i])
            if vol <= lvn_threshold:
                lvns.append(bin_prices[i])
        
        return VolumeProfile(
            poc=poc,
            poc_idx=poc_idx,
            va_high=va_high,
            va_low=va_low,
            bin_volumes=bin_volumes,
            bin_prices=bin_prices,
            hvns=hvns,
            lvns=lvns,
            total_volume=total_volume
        )
    
    def _classify_day_type(
        self,
        rates: np.ndarray,
        vp: VolumeProfile,
        pip_size: float
    ) -> DayType:
        """
        Klassifiziert den Day Type.
        
        Day Types:
        - Normal Day: VA in mittlerem Bereich der Day Range
        - Trend Day: >80% der Range außerhalb VA
        - Double Distribution: Zwei POC-Levels
        - Neutral Day: POC in Mitte, VA füllt gesamte Range
        """
        highs = np.array([r['high'] for r in rates])
        lows = np.array([r['low'] for r in rates])
        
        day_high = max(highs)
        day_low = min(lows)
        day_range = day_high - day_low
        
        if day_range == 0:
            return DayType(type="NEUTRAL", confidence=0.0)
        
        # Position von POC im Tagesrange
        poc_position = (vp.poc - day_low) / day_range
        
        # VA Position im Tagesrange
        va_mid = (vp.va_high + vp.va_low) / 2
        va_mid_position = (va_mid - day_low) / day_range
        
        # Trend Day: POC am Rand der Range
        if poc_position < 0.2 or poc_position > 0.8:
            return DayType(
                type="TREND",
                confidence=0.8,
                details={
                    "poc_position": poc_position,
                    "direction": "DOWN" if poc_position > 0.8 else "UP"
                }
            )
        
        # Normal Day: POC in der Mitte
        if 0.3 < poc_position < 0.7:
            return DayType(
                type="NORMAL",
                confidence=0.7,
                details={"poc_position": poc_position}
            )
        
        # Neutral Day
        return DayType(
            type="NEUTRAL",
            confidence=0.5,
            details={"poc_position": poc_position}
        )
    
    def _generate_vp_signal(
        self,
        symbol: str,
        rates: np.ndarray,
        vp: VolumeProfile,
        day_type: DayType,
        pip_size: float
    ) -> TradingSignal:
        """Generiert Volume Profile Trading Signal"""
        
        current_price = rates[-1]['close']
        
        # VA Breakout Trading
        if self.config["entry_on_va_break"]:
            # Bullischer VA Breakout
            if current_price > vp.va_high:
                sl = vp.va_low - self.config["sl_buffer_pips"] * pip_size
                tp = current_price + (current_price - sl) * 2
                
                return create_signal(
                    action="BUY",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.7,
                    reason=f"VA Breakout (VA High: {vp.va_high:.5f})",
                    pattern="VA_BREAKOUT"
                )
            
            # Bearischer VA Breakout
            elif current_price < vp.va_low:
                sl = vp.va_high + self.config["sl_buffer_pips"] * pip_size
                tp = current_price - (sl - current_price) * 2
                
                return create_signal(
                    action="SELL",
                    entry=current_price,
                    sl=round(sl, 5),
                    tp=round(tp, 5),
                    confidence=0.7,
                    reason=f"VA Breakout (VA Low: {vp.va_low:.5f})",
                    pattern="VA_BREAKOUT"
                )
        
        # POC Retest Trading
        if self.config["entry_on_poc_retest"]:
            dist_to_poc = abs(current_price - vp.poc)
            
            # Preis nahe am POC
            if dist_to_poc < 10 * pip_size:
                # Bullischer Retest (Preis über POC)
                if current_price > vp.poc:
                    sl = vp.poc - self.config["sl_buffer_pips"] * pip_size
                    tp = current_price + (current_price - sl) * 1.5
                    
                    return create_signal(
                        action="BUY",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason=f"POC Retest (POC: {vp.poc:.5f})",
                        pattern="POC_RETEST"
                    )
                
                # Bearischer Retest (Preis unter POC)
                elif current_price < vp.poc:
                    sl = vp.poc + self.config["sl_buffer_pips"] * pip_size
                    tp = current_price - (sl - current_price) * 1.5
                    
                    return create_signal(
                        action="SELL",
                        entry=current_price,
                        sl=round(sl, 5),
                        tp=round(tp, 5),
                        confidence=0.6,
                        reason=f"POC Retest (POC: {vp.poc:.5f})",
                        pattern="POC_RETEST"
                    )
        
        # HVN Bounce Trading
        if self.config["entry_on_hvn_bounce"]:
            for hvn in vp.hvns:
                dist_to_hvn = abs(current_price - hvn)
                if dist_to_hvn < 5 * pip_size:
                    # Preis bounced von HVN
                    if current_price > hvn:
                        sl = hvn - self.config["sl_buffer_pips"] * pip_size
                        tp = current_price + (current_price - sl) * 1.5
                        
                        return create_signal(
                            action="BUY",
                            entry=current_price,
                            sl=round(sl, 5),
                            tp=round(tp, 5),
                            confidence=0.5,
                            reason=f"HVN Bounce (HVN: {hvn:.5f})",
                            pattern="HVN_BOUNCE"
                        )
                    else:
                        sl = hvn + self.config["sl_buffer_pips"] * pip_size
                        tp = current_price - (sl - current_price) * 1.5
                        
                        return create_signal(
                            action="SELL",
                            entry=current_price,
                            sl=round(sl, 5),
                            tp=round(tp, 5),
                            confidence=0.5,
                            reason=f"HVN Bounce (HVN: {hvn:.5f})",
                            pattern="HVN_BOUNCE"
                        )
        
        # Kein Signal
        return create_signal(
            action="HOLD",
            entry=current_price,
            sl=0.0,
            tp=0.0,
            confidence=0.0,
            reason="Kein VP Setup gefunden"
        )


# Registriere Strategie
from trading.base_strategy import StrategyRegistry
StrategyRegistry.register("Market Profile", VPStrategy)
StrategyRegistry.register("Volume Profile", VPStrategy)
