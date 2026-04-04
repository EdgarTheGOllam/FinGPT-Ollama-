import logging
import numpy as np
import pandas as pd
from datetime import datetime


# Fancy console
class C:
    RESET = "\033[0m"
    YELLOW = "\033[33m"
    LGRAY = "\033[90m"


def ts():
    return datetime.now().strftime("%H:%M:%S")


try:
    import pandas_ta as ta

    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    print(
        f"{C.LGRAY}[{ts()}]{C.RESET} {C.YELLOW}⚠️ [WARNUNG] pandas_ta nicht gefunden – verwende Numpy-Fallback{C.RESET}"
    )

from typing import Optional, Dict, Any
from core.performance_optimizer import CacheManager


class MarketAnalyzer:
    def __init__(self, broker=None, logger=None, cache_ttl: float = 60.0):
        self.broker = broker  # Needs MT5Broker instance
        self.logger = logger or logging.getLogger(__name__)
        self.cache = CacheManager(max_size=200, ttl=cache_ttl)

        # Settings mapped from FinGPT.py
        self.rsi_period = 14
        self.rsi_overbought = 75
        self.rsi_oversold = 25

        self.sr_lookback_period = 50
        self.sr_tolerance = 0.0002
        self.sr_strength_threshold = 3

        self.trend_ema_period = 50
        self.trend_strength_threshold = 0.0010

    def log(self, level, message, category="ANALYSIS"):
        if self.logger:
            formatted_message = f"[{category}] {message}"
            if level == "INFO":
                self.logger.info(formatted_message)
            elif level == "WARNING":
                self.logger.warning(formatted_message)
            elif level == "ERROR":
                self.logger.error(formatted_message)
            elif level == "DEBUG":
                self.logger.debug(formatted_message)

    def calculate_rsi(self, symbol, timeframe, period=None):
        """Berechnet RSI für ein Symbol mit Caching und pandas-ta (Fallback auf numpy)"""
        if not self.broker or not self.broker.mt5_connected:
            return None

        period = period or self.rsi_period
        cache_key = f"rsi_{symbol}_{timeframe}_{period}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            import MetaTrader5 as mt5

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + 50)
            if rates is None or len(rates) < period + 1:
                return None

            if PANDAS_TA_AVAILABLE:
                df = pd.DataFrame(rates)
                rsi_series = ta.rsi(df["close"], length=period)
                if rsi_series is not None and not rsi_series.empty:
                    rsi_value = round(float(rsi_series.iloc[-1]), 2)
                    self.cache.set(cache_key, rsi_value)
                    return rsi_value

            # Fallback (Numpy) — Wilder's Smoothing (korrekte Methode)
            closes = np.array([r["close"] for r in rates], dtype=float)
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)

            # Initialisierung: einfacher Mittelwert der ersten `period` Werte
            avg_gain = float(np.mean(gains[:period]))
            avg_loss = float(np.mean(losses[:period]))

            # Wilder's Smoothing für den Rest der Daten
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi_value = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_value = round(100.0 - (100.0 / (1.0 + rs)), 2)

            self.cache.set(cache_key, rsi_value)
            return rsi_value

        except Exception as e:
            self.log("ERROR", f"RSI Berechnung Fehler: {e}")
            return None

    def get_rsi_signal(self, rsi_value):
        """Interpretiert RSI-Wert für Trading-Signal"""
        if rsi_value is None:
            return "NEUTRAL", "RSI nicht verfügbar"

        if rsi_value >= self.rsi_overbought:
            return "SELL", f"Überkauft (RSI: {rsi_value})"
        elif rsi_value <= self.rsi_oversold:
            return "BUY", f"Überverkauft (RSI: {rsi_value})"
        elif rsi_value > 60:
            return "NEUTRAL", f"Leicht überkauft (RSI: {rsi_value})"
        elif rsi_value < 40:
            return "NEUTRAL", f"Leicht überverkauft (RSI: {rsi_value})"
        else:
            return "NEUTRAL", f"Neutral (RSI: {rsi_value})"

    def calculate_macd(
        self, symbol, timeframe, fast_period=12, slow_period=26, signal_period=9
    ):
        """Berechnet MACD für ein Symbol mit Caching und pandas-ta (Fallback auf numpy)"""
        if not self.broker or not self.broker.mt5_connected:
            return None

        cache_key = (
            f"macd_{symbol}_{timeframe}_{fast_period}_{slow_period}_{signal_period}"
        )
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            import MetaTrader5 as mt5

            required_bars = max(slow_period, signal_period) + 50
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, required_bars)

            if rates is None or len(rates) < required_bars:
                return None

            if PANDAS_TA_AVAILABLE:
                df = pd.DataFrame(rates)
                macd_df = ta.macd(
                    df["close"],
                    fast=fast_period,
                    slow=slow_period,
                    signal=signal_period,
                )

                if macd_df is not None and not macd_df.empty:
                    macd_col = f"MACD_{fast_period}_{slow_period}_{signal_period}"
                    hist_col = f"MACDh_{fast_period}_{slow_period}_{signal_period}"
                    signal_col = f"MACDs_{fast_period}_{slow_period}_{signal_period}"

                    result = {
                        "macd": round(float(macd_df[macd_col].iloc[-1]), 6),
                        "signal": round(float(macd_df[signal_col].iloc[-1]), 6),
                        "histogram": round(float(macd_df[hist_col].iloc[-1]), 6),
                        "prev_macd": round(float(macd_df[macd_col].iloc[-2]), 6),
                        "prev_signal": round(float(macd_df[signal_col].iloc[-2]), 6),
                        "prev_histogram": round(float(macd_df[hist_col].iloc[-2]), 6),
                        "histogram_trend": "STEIGEND"
                        if macd_df[hist_col].iloc[-1] > macd_df[hist_col].iloc[-2]
                        else "FALLEND",
                        "macd_line": macd_df[macd_col].tail(10).tolist(),
                        "signal_line": macd_df[signal_col].tail(10).tolist(),
                        "histogram_values": macd_df[hist_col].tail(10).tolist(),
                    }
                    self.cache.set(cache_key, result)
                    return result

            # Fallback (Numpy EMA based)
            closes = np.array([rate["close"] for rate in rates])

            def calculate_ema(data, period):
                alpha = 2 / (period + 1)
                ema = np.zeros_like(data)
                ema[0] = data[0]
                for i in range(1, len(data)):
                    ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
                return ema

            fast_ema = calculate_ema(closes, fast_period)
            slow_ema = calculate_ema(closes, slow_period)
            macd_line = fast_ema - slow_ema
            signal_line = calculate_ema(macd_line, signal_period)
            histogram = macd_line - signal_line

            result = {
                "macd": round(float(macd_line[-1]), 6),
                "signal": round(float(signal_line[-1]), 6),
                "histogram": round(float(histogram[-1]), 6),
                "prev_macd": round(float(macd_line[-2]), 6),
                "prev_signal": round(float(signal_line[-2]), 6),
                "prev_histogram": round(float(histogram[-2]), 6),
                "histogram_trend": "STEIGEND"
                if histogram[-1] > histogram[-2]
                else "FALLEND",
                "macd_line": macd_line[-10:].tolist(),
                "signal_line": signal_line[-10:].tolist(),
                "histogram_values": histogram[-10:].tolist(),
            }
            self.cache.set(cache_key, result)
            return result
        except Exception as e:
            self.log("ERROR", f"MACD Berechnung Fehler: {e}")
            return None

    def get_macd_signal(self, macd_data):
        """Interpretiert MACD-Werte für Trading-Signal"""
        if not macd_data:
            return "NEUTRAL", "MACD nicht verfügbar"

        try:
            macd = macd_data["macd"]
            signal = macd_data["signal"]
            histogram = macd_data["histogram"]
            prev_macd = macd_data["prev_macd"]
            prev_signal = macd_data["prev_signal"]
            prev_histogram = macd_data["prev_histogram"]
            histogram_trend = macd_data["histogram_trend"]

            signals = []
            signal_strength = 0

            macd_above_signal = macd > signal
            prev_macd_above_signal = prev_macd > prev_signal

            if macd_above_signal and not prev_macd_above_signal:
                signals.append("BULLISCHE KREUZUNG")
                signal_strength += 2
            elif not macd_above_signal and prev_macd_above_signal:
                signals.append("BEARISCHE KREUZUNG")
                signal_strength -= 2

            macd_above_zero = macd > 0
            prev_macd_above_zero = prev_macd > 0

            if macd_above_zero and not prev_macd_above_zero:
                signals.append("NULLLINIE BULLISCH")
                signal_strength += 1
            elif not macd_above_zero and prev_macd_above_zero:
                signals.append("NULLLINIE BEARISCH")
                signal_strength -= 1

            histogram_above_zero = histogram > 0
            prev_histogram_above_zero = prev_histogram > 0

            if histogram_above_zero and not prev_histogram_above_zero:
                signals.append("MOMENTUM BULLISCH")
                signal_strength += 1
            elif not histogram_above_zero and prev_histogram_above_zero:
                signals.append("MOMENTUM BEARISCH")
                signal_strength -= 1

            if histogram_trend == "STEIGEND":
                if histogram > 0:
                    signals.append("AUFWÄRTS-MOMENTUM")
                    signal_strength += 1
                else:
                    signals.append("MOMENTUM ERHOLT SICH")
            elif histogram_trend == "FALLEND":
                if histogram < 0:
                    signals.append("ABWÄRTS-MOMENTUM")
                    signal_strength -= 1
                else:
                    signals.append("MOMENTUM SCHWÄCHT AB")

            if macd > 0 and signal > 0:
                signals.append("ÜBER NULLLINIE")
            elif macd < 0 and signal < 0:
                signals.append("UNTER NULLLINIE")

            if signal_strength >= 3:
                main_signal = "BUY"
                description = (
                    f"Starkes Kaufsignal ({signal_strength}): {', '.join(signals[:2])}"
                )
            elif signal_strength >= 1:
                main_signal = "BUY"
                description = (
                    f"Kaufsignal ({signal_strength}): {', '.join(signals[:2])}"
                )
            elif signal_strength <= -3:
                main_signal = "SELL"
                description = f"Starkes Verkaufssignal ({signal_strength}): {', '.join(signals[:2])}"
            elif signal_strength <= -1:
                main_signal = "SELL"
                description = (
                    f"Verkaufssignal ({signal_strength}): {', '.join(signals[:2])}"
                )
            else:
                main_signal = "NEUTRAL"
                if signals:
                    description = f"Neutral: {', '.join(signals[:2])}"
                else:
                    description = f"Seitwärts (MACD: {macd:.6f}, Signal: {signal:.6f})"

            return main_signal, description
        except Exception as e:
            return "NEUTRAL", f"MACD Analyse Fehler: {e}"

    def calculate_support_resistance(self, symbol, timeframe, lookback=None):
        """Erkennt Support und Resistance Level"""
        if not self.broker or not self.broker.mt5_connected:
            return None

        try:
            import MetaTrader5 as mt5

            lookback = lookback or self.sr_lookback_period

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, lookback)
            if rates is None or len(rates) < 20:
                return None

            # Extract OHLC data
            highs = np.array([rate["high"] for rate in rates])
            lows = np.array([rate["low"] for rate in rates])
            current_price = rates[-1]["close"]

            # Find local maxima and minima
            resistance_levels = []
            support_levels = []

            # Window size for local extrema
            window = 5

            for i in range(window, len(highs) - window):
                is_resistance = True
                is_support = True

                for j in range(1, window + 1):
                    if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                        is_resistance = False
                    if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                        is_support = False

                if is_resistance:
                    resistance_levels.append(highs[i])
                if is_support:
                    support_levels.append(lows[i])

            def group_levels(levels, tolerance):
                if not levels:
                    return []
                levels = sorted(levels)
                grouped = []
                current_group = [levels[0]]

                for i in range(1, len(levels)):
                    if levels[i] - current_group[-1] <= tolerance:
                        current_group.append(levels[i])
                    else:
                        avg_level = sum(current_group) / len(current_group)
                        grouped.append(
                            {"price": avg_level, "strength": len(current_group)}
                        )
                        current_group = [levels[i]]

                if current_group:
                    avg_level = sum(current_group) / len(current_group)
                    grouped.append({"price": avg_level, "strength": len(current_group)})

                return sorted(grouped, key=lambda x: x["strength"], reverse=True)

            # Calculate tolerance based on price (e.g., 0.05%)
            tolerance = current_price * 0.0005

            grouped_resistance = group_levels(resistance_levels, tolerance)
            grouped_support = group_levels(support_levels, tolerance)

            # Filter nearby levels
            resistances = [r for r in grouped_resistance if r["price"] > current_price]
            supports = [s for s in grouped_support if s["price"] < current_price]

            # Sort by proximity to current price
            resistances.sort(key=lambda x: x["price"])
            supports.sort(key=lambda x: x["price"], reverse=True)

            return {
                "current_price": current_price,
                "resistance_levels": resistances[:3],
                "support_levels": supports[:3],
                "all_resistances": resistances,
                "all_supports": supports,
            }

        except Exception as e:
            self.log("ERROR", f"S/R Berechnung Fehler: {e}")
            return None

    def get_sr_signal(self, sr_data, current_price):
        """Generiert Signal basierend auf S/R Levels"""
        if not sr_data:
            return "NEUTRAL", "Keine S/R Daten"

        try:
            nearest_resistance = (
                sr_data["resistance_levels"][0]["price"]
                if sr_data["resistance_levels"]
                else float("inf")
            )
            nearest_support = (
                sr_data["support_levels"][0]["price"]
                if sr_data["support_levels"]
                else float("-inf")
            )

            # Distances in percent
            dist_to_res = (nearest_resistance - current_price) / current_price * 100
            dist_to_sup = (current_price - nearest_support) / current_price * 100

            signal = "NEUTRAL"
            description = f"Preis: {current_price:.5f}"

            # Near Support -> Potential Buy
            if dist_to_sup < 0.1:  # Within 0.1% of support
                signal = "BUY"
                description = (
                    f"Nahe Support ({nearest_support:.5f}, {dist_to_sup:.2f}%)"
                )

            # Near Resistance -> Potential Sell
            elif dist_to_res < 0.1:  # Within 0.1% of resistance
                signal = "SELL"
                description = (
                    f"Nahe Resistance ({nearest_resistance:.5f}, {dist_to_res:.2f}%)"
                )

            return signal, description

        except Exception as e:
            return "NEUTRAL", f"S/R Signal Fehler: {e}"

    def get_higher_timeframe_trend(self, symbol, trend_timeframe):
        """Analysiert den übergeordneten Trend auf höherem Timeframe"""
        if not self.broker or not self.broker.mt5_connected:
            return None

        try:
            import MetaTrader5 as mt5

            required_bars = self.trend_ema_period + 10
            rates = mt5.copy_rates_from_pos(symbol, trend_timeframe, 0, required_bars)

            if rates is None or len(rates) < required_bars:
                return None

            closes = np.array([rate["close"] for rate in rates])
            highs = np.array([rate["high"] for rate in rates])
            lows = np.array([rate["low"] for rate in rates])

            def calculate_ema(data, period):
                alpha = 2 / (period + 1)
                ema = np.zeros_like(data)
                ema[0] = data[0]
                for i in range(1, len(data)):
                    ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
                return ema

            ema = calculate_ema(closes, self.trend_ema_period)
            current_price = closes[-1]
            current_ema = ema[-1]
            prev_ema = ema[-2] if len(ema) > 1 else current_ema
            ema_slope = current_ema - prev_ema

            price_above_ema = current_price > current_ema
            ema_rising = current_ema > prev_ema
            trend_strength = abs(current_price - current_ema)

            recent_bars = 10
            recent_highs = highs[-recent_bars:]
            recent_lows = lows[-recent_bars:]
            higher_highs = (
                len(
                    [
                        i
                        for i in range(1, len(recent_highs))
                        if recent_highs[i] > recent_highs[i - 1]
                    ]
                )
                >= 6
            )
            lower_lows = (
                len(
                    [
                        i
                        for i in range(1, len(recent_lows))
                        if recent_lows[i] < recent_lows[i - 1]
                    ]
                )
                >= 6
            )

            if price_above_ema and ema_rising:
                direction = (
                    "BULLISH"
                    if trend_strength >= self.trend_strength_threshold
                    else "WEAK_BULLISH"
                )
            elif not price_above_ema and not ema_rising:
                direction = (
                    "BEARISH"
                    if trend_strength >= self.trend_strength_threshold
                    else "WEAK_BEARISH"
                )
            else:
                direction = "NEUTRAL"

            if direction == "BULLISH" and not higher_highs:
                direction = "WEAK_BULLISH"
            elif direction == "BEARISH" and not lower_lows:
                direction = "WEAK_BEARISH"

            trend_quality = (
                "STRONG"
                if trend_strength >= self.trend_strength_threshold * 2
                else "MODERATE"
                if trend_strength >= self.trend_strength_threshold
                else "WEAK"
            )

            momentum_bars = 5
            if len(closes) >= momentum_bars:
                momentum = closes[-1] - closes[-momentum_bars]
                momentum_direction = (
                    "UP" if momentum > 0 else "DOWN" if momentum < 0 else "FLAT"
                )
            else:
                momentum = 0
                momentum_direction = "FLAT"

            return {
                "direction": direction,
                "strength": trend_strength,
                "quality": trend_quality,
                "current_price": current_price,
                "ema_level": current_ema,
                "ema_slope": ema_slope,
                "price_above_ema": price_above_ema,
                "ema_rising": ema_rising,
                "momentum": momentum,
                "momentum_direction": momentum_direction,
                "higher_highs": higher_highs,
                "lower_lows": lower_lows,
                "timeframe": trend_timeframe,
            }
        except Exception as e:
            self.log("ERROR", f"Trend-Analyse Fehler: {e}")
            return None
