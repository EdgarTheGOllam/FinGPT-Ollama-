#!/usr/bin/env python3
"""
Advanced Technical Indicators für FinGPT Trading System
Erweiterte Indikatoren: Williams %R, CCI, Awesome Oscillator, Ichimoku, VWAP, etc.
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import functools
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

try:
    from core.performance_optimizer import cached
except ImportError:

    def cached(ttl=2.0, max_size=50):
        """Fallback-Decorator wenn core.performance_optimizer nicht verfügbar"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator


class AdvancedIndicators:
    def __init__(self, logger=None):
        """Initialisiert die erweiterten Indikatoren"""
        self.logger = logger

        # Williams %R Settings
        self.williams_r_period = 14
        self.williams_r_overbought = -20
        self.williams_r_oversold = -80

        # CCI Settings
        self.cci_period = 20
        self.cci_overbought = 100
        self.cci_oversold = -100

        # Awesome Oscillator Settings
        self.ao_fast_period = 5
        self.ao_slow_period = 34

        # Ichimoku Settings
        self.ichimoku_tenkan = 9
        self.ichimoku_kijun = 26
        self.ichimoku_senkou_b = 52

        # VWAP Settings
        self.vwap_period = 20

        # Parabolic SAR Settings
        self.psar_step = 0.02
        self.psar_maximum = 0.2

        # Money Flow Index Settings
        self.mfi_period = 14
        self.mfi_overbought = 80
        self.mfi_oversold = 20

        # On Balance Volume Settings
        self.obv_signal_period = 10

        # Average Directional Index Settings
        self.adx_period = 14
        self.adx_trend_threshold = 25

        self.log("INFO", "Advanced Indicators initialisiert")

    def log(self, level, message, category="INDICATORS"):
        """Logging-Funktion"""
        if self.logger:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{category}] {message}"
            try:
                print(f"{timestamp} {formatted_message}")
            except UnicodeEncodeError:
                pass

    @cached(ttl=2.0, max_size=50)
    def _fetch_market_data_cached(self, symbol, timeframe):
        """Holt einen großen Block an Daten (200 Bars) und cached diesen für 2 Sekunden."""
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
            if rates is None or len(rates) == 0:
                return None
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        except Exception as e:
            self.log("ERROR", f"Cached Marktdaten Fehler: {e}")
            return None

    def get_market_data(self, symbol, timeframe, bars):
        """Holt Marktdaten von MT5 (mit intelligentem Caching)"""
        try:
            df = self._fetch_market_data_cached(symbol, timeframe)
            if df is None:
                return None

            # Falls mal mehr als 200 Bars gefordert sind, direkt holen
            if bars > 200:
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
                if rates is None or len(rates) == 0:
                    return None
                df_custom = pd.DataFrame(rates)
                df_custom["time"] = pd.to_datetime(df_custom["time"], unit="s")
                return df_custom

            return df.iloc[-bars:].copy() if len(df) >= bars else df.copy()
        except Exception as e:
            self.log("ERROR", f"Marktdaten Fehler: {e}")
            return None

    def calculate_williams_r(self, symbol, timeframe=mt5.TIMEFRAME_M15, period=None):
        """
        Berechnet Williams %R Indikator

        Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        """
        try:
            if period is None:
                period = self.williams_r_period

            df = self.get_market_data(symbol, timeframe, period + 10)
            if df is None or len(df) < period:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]

            # Rolling highest high und lowest low
            highest_high = high.rolling(window=period).max()
            lowest_low = low.rolling(window=period).min()

            # Williams %R Berechnung
            williams_r = ((highest_high - close) / (highest_high - lowest_low)) * -100

            current_wr = williams_r.iloc[-1]
            prev_wr = williams_r.iloc[-2] if len(williams_r) > 1 else current_wr

            # Signal bestimmen
            if current_wr <= self.williams_r_oversold:
                signal = "BUY"
                description = f"Williams %R überverkauft ({current_wr:.1f})"
            elif current_wr >= self.williams_r_overbought:
                signal = "SELL"
                description = f"Williams %R überkauft ({current_wr:.1f})"
            elif (
                prev_wr <= self.williams_r_oversold
                and current_wr > self.williams_r_oversold
            ):
                signal = "BUY"
                description = "Williams %R verlässt überverkauft Zone"
            elif (
                prev_wr >= self.williams_r_overbought
                and current_wr < self.williams_r_overbought
            ):
                signal = "SELL"
                description = "Williams %R verlässt überkauft Zone"
            else:
                signal = "NEUTRAL"
                description = f"Williams %R neutral ({current_wr:.1f})"

            return {
                "value": round(current_wr, 2),
                "signal": signal,
                "description": description,
                "overbought_level": self.williams_r_overbought,
                "oversold_level": self.williams_r_oversold,
            }

        except Exception as e:
            self.log("ERROR", f"Williams %R Fehler: {e}")
            return None

    def calculate_cci(self, symbol, timeframe=mt5.TIMEFRAME_M15, period=None):
        """
        Berechnet Commodity Channel Index (CCI)

        CCI = (Typical Price - SMA) / (0.015 * Mean Deviation)
        """
        try:
            if period is None:
                period = self.cci_period

            df = self.get_market_data(symbol, timeframe, period + 10)
            if df is None or len(df) < period:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]

            # Typical Price
            typical_price = (high + low + close) / 3

            # Simple Moving Average von Typical Price
            sma_tp = typical_price.rolling(window=period).mean()

            # Mean Deviation
            def mean_deviation(series, window):
                return series.rolling(window=window).apply(
                    lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
                )

            mean_dev = mean_deviation(typical_price, period)

            # CCI Berechnung
            cci = (typical_price - sma_tp) / (0.015 * mean_dev)

            current_cci = cci.iloc[-1]
            prev_cci = cci.iloc[-2] if len(cci) > 1 else current_cci

            # Signal bestimmen
            if current_cci > self.cci_overbought:
                signal = "SELL"
                description = f"CCI überkauft ({current_cci:.1f})"
            elif current_cci < self.cci_oversold:
                signal = "BUY"
                description = f"CCI überverkauft ({current_cci:.1f})"
            elif prev_cci < 0 and current_cci > 0:
                signal = "BUY"
                description = "CCI kreuzt Nulllinie nach oben"
            elif prev_cci > 0 and current_cci < 0:
                signal = "SELL"
                description = "CCI kreuzt Nulllinie nach unten"
            else:
                signal = "NEUTRAL"
                description = f"CCI neutral ({current_cci:.1f})"

            return {
                "value": round(current_cci, 2),
                "signal": signal,
                "description": description,
                "overbought_level": self.cci_overbought,
                "oversold_level": self.cci_oversold,
            }

        except Exception as e:
            self.log("ERROR", f"CCI Fehler: {e}")
            return None

    def calculate_awesome_oscillator(
        self, symbol, timeframe=mt5.TIMEFRAME_M15, fast_period=None, slow_period=None
    ):
        """
        Berechnet Awesome Oscillator (AO)

        AO = SMA(5) of Median Price - SMA(34) of Median Price
        """
        try:
            if fast_period is None:
                fast_period = self.ao_fast_period
            if slow_period is None:
                slow_period = self.ao_slow_period

            df = self.get_market_data(symbol, timeframe, slow_period + 10)
            if df is None or len(df) < slow_period:
                return None

            high = df["high"]
            low = df["low"]

            # Median Price
            median_price = (high + low) / 2

            # SMAs berechnen
            sma_fast = median_price.rolling(window=fast_period).mean()
            sma_slow = median_price.rolling(window=slow_period).mean()

            # Awesome Oscillator
            ao = sma_fast - sma_slow

            current_ao = ao.iloc[-1]
            prev_ao = ao.iloc[-2] if len(ao) > 1 else current_ao
            prev2_ao = ao.iloc[-3] if len(ao) > 2 else prev_ao

            # Signal bestimmen
            signal = "NEUTRAL"
            description = f"AO: {current_ao:.6f}"

            # Saucer Signal (3 Balken über Nulllinie)
            if (
                prev2_ao > 0
                and prev_ao > 0
                and current_ao > 0
                and prev2_ao > prev_ao
                and current_ao > prev_ao
            ):
                signal = "BUY"
                description = "AO Saucer Signal (Bullish)"

            # Twin Peaks (Divergenz)
            elif current_ao > 0 and prev_ao < current_ao:
                signal = "BUY"
                description = "AO steigend über Nulllinie"

            elif current_ao < 0 and prev_ao > current_ao:
                signal = "SELL"
                description = "AO fallend unter Nulllinie"

            # Nulllinie Kreuzung
            elif prev_ao <= 0 and current_ao > 0:
                signal = "BUY"
                description = "AO kreuzt Nulllinie nach oben"
            elif prev_ao >= 0 and current_ao < 0:
                signal = "SELL"
                description = "AO kreuzt Nulllinie nach unten"

            return {
                "value": round(current_ao, 6),
                "signal": signal,
                "description": description,
                "above_zero": current_ao > 0,
                "momentum": "STEIGEND" if current_ao > prev_ao else "FALLEND",
            }

        except Exception as e:
            self.log("ERROR", f"Awesome Oscillator Fehler: {e}")
            return None

    def calculate_ichimoku(self, symbol, timeframe=mt5.TIMEFRAME_M15):
        """
        Berechnet Ichimoku Cloud Indikator

        Tenkan-sen: (9-period high + 9-period low) / 2
        Kijun-sen: (26-period high + 26-period low) / 2
        Senkou Span A: (Tenkan-sen + Kijun-sen) / 2 (projected 26 periods ahead)
        Senkou Span B: (52-period high + 52-period low) / 2 (projected 26 periods ahead)
        Chikou Span: Close price (projected 26 periods behind)
        """
        try:
            required_bars = max(self.ichimoku_senkou_b, self.ichimoku_kijun) + 30
            df = self.get_market_data(symbol, timeframe, required_bars)
            if df is None or len(df) < required_bars:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]

            # Tenkan-sen (Conversion Line)
            tenkan_high = high.rolling(window=self.ichimoku_tenkan).max()
            tenkan_low = low.rolling(window=self.ichimoku_tenkan).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2

            # Kijun-sen (Base Line)
            kijun_high = high.rolling(window=self.ichimoku_kijun).max()
            kijun_low = low.rolling(window=self.ichimoku_kijun).min()
            kijun_sen = (kijun_high + kijun_low) / 2

            # Senkou Span A (Leading Span A)
            senkou_span_a = (tenkan_sen + kijun_sen) / 2

            # Senkou Span B (Leading Span B)
            senkou_high = high.rolling(window=self.ichimoku_senkou_b).max()
            senkou_low = low.rolling(window=self.ichimoku_senkou_b).min()
            senkou_span_b = (senkou_high + senkou_low) / 2

            # Aktuelle Werte
            current_price = close.iloc[-1]
            current_tenkan = tenkan_sen.iloc[-1]
            current_kijun = kijun_sen.iloc[-1]
            current_senkou_a = (
                senkou_span_a.iloc[-27]
                if len(senkou_span_a) > 27
                else senkou_span_a.iloc[-1]
            )
            current_senkou_b = (
                senkou_span_b.iloc[-27]
                if len(senkou_span_b) > 27
                else senkou_span_b.iloc[-1]
            )

            # Cloud-Position bestimmen
            cloud_top = max(current_senkou_a, current_senkou_b)
            cloud_bottom = min(current_senkou_a, current_senkou_b)

            if current_price > cloud_top:
                price_vs_cloud = "ABOVE"
                cloud_signal = "BULLISH"
            elif current_price < cloud_bottom:
                price_vs_cloud = "BELOW"
                cloud_signal = "BEARISH"
            else:
                price_vs_cloud = "INSIDE"
                cloud_signal = "NEUTRAL"

            # Tenkan/Kijun Kreuzung
            prev_tenkan = tenkan_sen.iloc[-2] if len(tenkan_sen) > 1 else current_tenkan
            prev_kijun = kijun_sen.iloc[-2] if len(kijun_sen) > 1 else current_kijun

            tk_signal = "NEUTRAL"
            if prev_tenkan <= prev_kijun and current_tenkan > current_kijun:
                tk_signal = "BUY"
                tk_desc = "Tenkan kreuzt Kijun nach oben"
            elif prev_tenkan >= prev_kijun and current_tenkan < current_kijun:
                tk_signal = "SELL"
                tk_desc = "Tenkan kreuzt Kijun nach unten"
            else:
                tk_desc = "Tenkan/Kijun neutral"

            # Gesamtsignal
            if cloud_signal == "BULLISH" and tk_signal == "BUY":
                overall_signal = "STRONG_BUY"
                description = "Ichimoku: Starkes Kaufsignal"
            elif cloud_signal == "BEARISH" and tk_signal == "SELL":
                overall_signal = "STRONG_SELL"
                description = "Ichimoku: Starkes Verkaufssignal"
            elif cloud_signal == "BULLISH":
                overall_signal = "BUY"
                description = "Ichimoku: Preis über Cloud"
            elif cloud_signal == "BEARISH":
                overall_signal = "SELL"
                description = "Ichimoku: Preis unter Cloud"
            else:
                overall_signal = "NEUTRAL"
                description = "Ichimoku: Neutral/Inside Cloud"

            return {
                "tenkan_sen": round(current_tenkan, 5),
                "kijun_sen": round(current_kijun, 5),
                "senkou_span_a": round(current_senkou_a, 5),
                "senkou_span_b": round(current_senkou_b, 5),
                "cloud_top": round(cloud_top, 5),
                "cloud_bottom": round(cloud_bottom, 5),
                "price_vs_cloud": price_vs_cloud,
                "cloud_signal": cloud_signal,
                "tk_signal": tk_signal,
                "tk_description": tk_desc,
                "overall_signal": overall_signal,
                "description": description,
            }

        except Exception as e:
            self.log("ERROR", f"Ichimoku Fehler: {e}")
            return None

    def calculate_vwap(self, symbol, timeframe=mt5.TIMEFRAME_M15, period=None):
        """
        Berechnet Volume Weighted Average Price (VWAP)

        VWAP = Σ(Price × Volume) / Σ(Volume)
        """
        try:
            if period is None:
                period = self.vwap_period

            df = self.get_market_data(symbol, timeframe, period + 10)
            if df is None or len(df) < period:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]
            volume = df["tick_volume"]  # MT5 verwendet tick_volume

            # Typical Price
            typical_price = (high + low + close) / 3

            # VWAP Berechnung
            price_volume = typical_price * volume

            # Rolling VWAP
            vwap = (
                price_volume.rolling(window=period).sum()
                / volume.rolling(window=period).sum()
            )

            current_vwap = vwap.iloc[-1]
            current_price = close.iloc[-1]

            # Abstand zu VWAP
            distance_pct = ((current_price - current_vwap) / current_vwap) * 100

            # Signal bestimmen
            if current_price > current_vwap:
                if distance_pct > 0.5:
                    signal = "SELL"
                    description = f"Preis weit über VWAP (+{distance_pct:.2f}%)"
                else:
                    signal = "BUY"
                    description = f"Preis über VWAP (+{distance_pct:.2f}%)"
            else:
                if distance_pct < -0.5:
                    signal = "BUY"
                    description = f"Preis weit unter VWAP ({distance_pct:.2f}%)"
                else:
                    signal = "SELL"
                    description = f"Preis unter VWAP ({distance_pct:.2f}%)"

            return {
                "vwap": round(current_vwap, 5),
                "current_price": round(current_price, 5),
                "distance_pct": round(distance_pct, 2),
                "signal": signal,
                "description": description,
                "above_vwap": current_price > current_vwap,
            }

        except Exception as e:
            self.log("ERROR", f"VWAP Fehler: {e}")
            return None

    def calculate_mfi(self, symbol, timeframe=mt5.TIMEFRAME_M15, period=None):
        """
        Berechnet Money Flow Index (MFI)

        MFI = 100 - (100 / (1 + Money Flow Ratio))
        """
        try:
            if period is None:
                period = self.mfi_period

            df = self.get_market_data(symbol, timeframe, period + 10)
            if df is None or len(df) < period + 1:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]
            volume = df["tick_volume"]

            # Typical Price
            typical_price = (high + low + close) / 3

            # Raw Money Flow
            raw_money_flow = typical_price * volume

            # Positive und Negative Money Flow
            price_change = typical_price.diff()

            positive_flow = pd.Series(index=df.index, dtype=float)
            negative_flow = pd.Series(index=df.index, dtype=float)

            positive_flow[price_change > 0] = raw_money_flow[price_change > 0]
            positive_flow[price_change <= 0] = 0

            negative_flow[price_change < 0] = raw_money_flow[price_change < 0]
            negative_flow[price_change >= 0] = 0

            # Money Flow Ratio
            positive_mf = positive_flow.rolling(window=period).sum()
            negative_mf = negative_flow.rolling(window=period).sum()

            # Vermeide Division durch Null
            money_flow_ratio = positive_mf / negative_mf.replace(0, 1)

            # MFI berechnen
            mfi = 100 - (100 / (1 + money_flow_ratio))

            current_mfi = mfi.iloc[-1]

            # Signal bestimmen
            if current_mfi >= self.mfi_overbought:
                signal = "SELL"
                description = f"MFI überkauft ({current_mfi:.1f})"
            elif current_mfi <= self.mfi_oversold:
                signal = "BUY"
                description = f"MFI überverkauft ({current_mfi:.1f})"
            else:
                signal = "NEUTRAL"
                description = f"MFI neutral ({current_mfi:.1f})"

            return {
                "value": round(current_mfi, 2),
                "signal": signal,
                "description": description,
                "overbought_level": self.mfi_overbought,
                "oversold_level": self.mfi_oversold,
            }

        except Exception as e:
            self.log("ERROR", f"MFI Fehler: {e}")
            return None

    def calculate_adx(self, symbol, timeframe=mt5.TIMEFRAME_M15, period=None):
        """
        Berechnet Average Directional Index (ADX)
        Misst die Trendstärke (nicht die Richtung)
        """
        try:
            if period is None:
                period = self.adx_period

            df = self.get_market_data(symbol, timeframe, period * 2 + 10)
            if df is None or len(df) < period * 2:
                return None

            high = df["high"].values
            low = df["low"].values
            close = df["close"].values

            # True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))

            # Directional Movement
            dm_plus = np.where(
                (high[1:] - high[:-1]) > (low[:-1] - low[1:]),
                np.maximum(high[1:] - high[:-1], 0),
                0,
            )

            dm_minus = np.where(
                (low[:-1] - low[1:]) > (high[1:] - high[:-1]),
                np.maximum(low[:-1] - low[1:], 0),
                0,
            )

            # Smoothed TR und DM
            def wilder_smooth(data, period):
                """Wilder's Smoothing"""
                smoothed = np.zeros_like(data)
                smoothed[period - 1] = np.mean(data[:period])
                for i in range(period, len(data)):
                    smoothed[i] = (smoothed[i - 1] * (period - 1) + data[i]) / period
                return smoothed

            tr_smooth = wilder_smooth(tr, period)
            dm_plus_smooth = wilder_smooth(dm_plus, period)
            dm_minus_smooth = wilder_smooth(dm_minus, period)

            # Directional Indicators
            di_plus = 100 * (dm_plus_smooth / tr_smooth)
            di_minus = 100 * (dm_minus_smooth / tr_smooth)

            # Directional Index
            dx = 100 * (np.abs(di_plus - di_minus) / (di_plus + di_minus))
            dx = np.where(np.isnan(dx), 0, dx)

            # ADX
            adx = wilder_smooth(dx, period)

            current_adx = adx[-1] if len(adx) > 0 else 0
            current_di_plus = di_plus[-1] if len(di_plus) > 0 else 0
            current_di_minus = di_minus[-1] if len(di_minus) > 0 else 0

            # Trend-Stärke bestimmen
            if current_adx > 50:
                trend_strength = "SEHR_STARK"
            elif current_adx > 25:
                trend_strength = "STARK"
            elif current_adx > 20:
                trend_strength = "MODERAT"
            else:
                trend_strength = "SCHWACH"

            # Trend-Richtung bestimmen
            if current_di_plus > current_di_minus:
                trend_direction = "BULLISH"
                signal = "BUY" if current_adx > self.adx_trend_threshold else "NEUTRAL"
            else:
                trend_direction = "BEARISH"
                signal = "SELL" if current_adx > self.adx_trend_threshold else "NEUTRAL"

            description = f"ADX: {trend_strength} {trend_direction} Trend"

            return {
                "adx": round(current_adx, 2),
                "di_plus": round(current_di_plus, 2),
                "di_minus": round(current_di_minus, 2),
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
                "signal": signal,
                "description": description,
                "strong_trend": current_adx > self.adx_trend_threshold,
            }

        except Exception as e:
            self.log("ERROR", f"ADX Fehler: {e}")
            return None

    def get_higher_timeframes(self, timeframe):
        """Ermittelt die zwei nächsthöheren Timeframes für die MTF-Analyse"""
        mapping = {
            mt5.TIMEFRAME_M1: (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15),
            mt5.TIMEFRAME_M5: (mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1),
            mt5.TIMEFRAME_M15: (mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4),
            mt5.TIMEFRAME_M30: (mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4),
            mt5.TIMEFRAME_H1: (mt5.TIMEFRAME_H4, mt5.TIMEFRAME_D1),
            mt5.TIMEFRAME_H4: (mt5.TIMEFRAME_D1, mt5.TIMEFRAME_W1),
            mt5.TIMEFRAME_D1: (mt5.TIMEFRAME_W1, mt5.TIMEFRAME_MN1)
        }
        return mapping.get(timeframe, (mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4))

    def calculate_mtf_trend(self, symbol, base_timeframe):
        """
        Analysiert den Trend über mehrere Timeframes (Multi-Timeframe Analysis).
        Gibt zurück, ob die übergeordneten Timeframes (HTF) mit dem Basis-Timeframe übereinstimmen.
        Nutzt dafür EMA 20/50 Crossover.
        """
        try:
            htf1, htf2 = self.get_higher_timeframes(base_timeframe)
            
            def get_trend_for_tf(tf):
                df = self.get_market_data(symbol, tf, 60)
                if df is None or len(df) < 50:
                    return "NEUTRAL"
                close = df["close"]
                ema20 = close.rolling(window=20).mean().iloc[-1]
                ema50 = close.rolling(window=50).mean().iloc[-1]
                current_price = close.iloc[-1]
                
                if current_price > ema20 and ema20 > ema50:
                    return "BULLISH"
                elif current_price < ema20 and ema20 < ema50:
                    return "BEARISH"
                return "NEUTRAL"

            base_trend = get_trend_for_tf(base_timeframe)
            htf1_trend = get_trend_for_tf(htf1)
            htf2_trend = get_trend_for_tf(htf2)
            
            # Alignment check
            alignment = "MIXED"
            signal = "NEUTRAL"
            
            if base_trend == htf1_trend == htf2_trend and base_trend != "NEUTRAL":
                if base_trend == "BULLISH":
                    alignment = "FULL_BULLISH_ALIGNMENT"
                    signal = "STRONG_BUY"
                elif base_trend == "BEARISH":
                    alignment = "FULL_BEARISH_ALIGNMENT"
                    signal = "STRONG_SELL"
            elif base_trend == htf1_trend and htf1_trend != "NEUTRAL":
                if base_trend == "BULLISH":
                    alignment = "PARTIAL_BULLISH_ALIGNMENT"
                    signal = "BUY"
                elif base_trend == "BEARISH":
                    alignment = "PARTIAL_BEARISH_ALIGNMENT"
                    signal = "SELL"
            
            # TF Namen ermitteln für lesbaren Output
            tf_names = {
                mt5.TIMEFRAME_M1: "M1", mt5.TIMEFRAME_M5: "M5", mt5.TIMEFRAME_M15: "M15",
                mt5.TIMEFRAME_M30: "M30", mt5.TIMEFRAME_H1: "H1", mt5.TIMEFRAME_H4: "H4",
                mt5.TIMEFRAME_D1: "D1", mt5.TIMEFRAME_W1: "W1", mt5.TIMEFRAME_MN1: "MN1"
            }
            b_name = tf_names.get(base_timeframe, "BASE")
            h1_name = tf_names.get(htf1, "HTF1")
            h2_name = tf_names.get(htf2, "HTF2")

            description = f"[{b_name}={base_trend} | {h1_name}={htf1_trend} | {h2_name}={htf2_trend}]"

            return {
                "base_trend": base_trend,
                "htf1_trend": htf1_trend,
                "htf2_trend": htf2_trend,
                "alignment": alignment,
                "signal": signal,
                "description": description
            }
            
        except Exception as e:
            self.log("ERROR", f"MTF Trend Fehler: {e}")
            return None

    def get_comprehensive_analysis(self, symbol, timeframe=mt5.TIMEFRAME_M15):
        """
        Führt eine umfassende Analyse mit allen erweiterten Indikatoren durch
        """
        try:
            self.log("INFO", f"Starte umfassende Analyse für {symbol}")

            results = {}

            # Williams %R
            williams_r = self.calculate_williams_r(symbol, timeframe)
            if williams_r:
                results["williams_r"] = williams_r

            # CCI
            cci = self.calculate_cci(symbol, timeframe)
            if cci:
                results["cci"] = cci

            # Awesome Oscillator
            ao = self.calculate_awesome_oscillator(symbol, timeframe)
            if ao:
                results["awesome_oscillator"] = ao

            # Ichimoku
            ichimoku = self.calculate_ichimoku(symbol, timeframe)
            if ichimoku:
                results["ichimoku"] = ichimoku

            # VWAP
            vwap = self.calculate_vwap(symbol, timeframe)
            if vwap:
                results["vwap"] = vwap

            # MFI
            mfi = self.calculate_mfi(symbol, timeframe)
            if mfi:
                results["mfi"] = mfi

            # ADX
            adx = self.calculate_adx(symbol, timeframe)
            if adx:
                results["adx"] = adx

            # MTF Trend
            mtf = self.calculate_mtf_trend(symbol, timeframe)
            if mtf:
                results["mtf_trend"] = mtf

            return results

        except Exception as e:
            self.log("ERROR", f"Comprehensive Analysis Fehler: {e}")
            return {}

    def get_signal_consensus(self, analysis_results):
        """
        Erstellt einen Konsens aus allen Signalen
        """
        try:
            if not analysis_results:
                return "NEUTRAL", "Keine Analyse-Daten verfügbar"

            signals = []
            weights = {
                "williams_r": 1.0,
                "cci": 1.0,
                "awesome_oscillator": 1.5,
                "ichimoku": 2.0,  # Höheres Gewicht für Ichimoku
                "vwap": 1.2,
                "mfi": 1.0,
                "adx": 1.8,  # Höheres Gewicht für Trend-Stärke
                "mtf_trend": 2.5, # Sehr hohes Gewicht für Multi-Timeframe Alignment
            }

            buy_score = 0
            sell_score = 0
            total_weight = 0

            signal_descriptions = []

            for indicator, data in analysis_results.items():
                if "signal" in data:
                    weight = weights.get(indicator, 1.0)
                    signal = data["signal"]
                    description = data.get("description", "")

                    if signal in ["BUY", "STRONG_BUY"]:
                        buy_score += weight
                        signal_descriptions.append(
                            f"{indicator.upper()}: {description}"
                        )
                    elif signal in ["SELL", "STRONG_SELL"]:
                        sell_score += weight
                        signal_descriptions.append(
                            f"{indicator.upper()}: {description}"
                        )

                    total_weight += weight

            if total_weight == 0:
                return "NEUTRAL", "Keine gültigen Signale"

            # Konsens bestimmen
            buy_ratio = buy_score / total_weight
            sell_ratio = sell_score / total_weight

            if buy_ratio >= 0.6:
                consensus = "STRONG_BUY"
                confidence = f"({buy_ratio:.1%} Bullisch)"
            elif buy_ratio >= 0.4:
                consensus = "BUY"
                confidence = f"({buy_ratio:.1%} Bullisch)"
            elif sell_ratio >= 0.6:
                consensus = "STRONG_SELL"
                confidence = f"({sell_ratio:.1%} Bearisch)"
            elif sell_ratio >= 0.4:
                consensus = "SELL"
                confidence = f"({sell_ratio:.1%} Bearisch)"
            else:
                consensus = "NEUTRAL"
                confidence = "Gemischte Signale"

            # Top 3 Signale für Beschreibung
            top_signals = signal_descriptions[:3]
            description = f"{consensus} {confidence} | {' | '.join(top_signals)}"

            return consensus, description

        except Exception as e:
            self.log("ERROR", f"Signal Consensus Fehler: {e}")
            return "NEUTRAL", "Konsens-Berechnung fehlgeschlagen"

    def print_analysis_report(self, symbol, analysis_results):
        """
        Druckt einen formatierten Analyse-Bericht
        """
        try:
            print(f"\n{'=' * 60}")
            print(f"🔬 ERWEITERTE TECHNISCHE ANALYSE: {symbol}")
            print(f"{'=' * 60}")

            if not analysis_results:
                print("❌ Keine Analyse-Daten verfügbar")
                return

            # Williams %R
            if "williams_r" in analysis_results:
                wr = analysis_results["williams_r"]
                icon = (
                    "🟢"
                    if wr["signal"] == "BUY"
                    else "🔴"
                    if wr["signal"] == "SELL"
                    else "🟡"
                )
                print(f"{icon} Williams %R: {wr['value']}% - {wr['description']}")

            # CCI
            if "cci" in analysis_results:
                cci = analysis_results["cci"]
                icon = (
                    "🟢"
                    if cci["signal"] == "BUY"
                    else "🔴"
                    if cci["signal"] == "SELL"
                    else "🟡"
                )
                print(f"{icon} CCI: {cci['value']} - {cci['description']}")

            # Awesome Oscillator
            if "awesome_oscillator" in analysis_results:
                ao = analysis_results["awesome_oscillator"]
                icon = (
                    "🟢"
                    if ao["signal"] == "BUY"
                    else "🔴"
                    if ao["signal"] == "SELL"
                    else "🟡"
                )
                print(f"{icon} Awesome Oscillator: {ao['value']} - {ao['description']}")

            # Ichimoku
            if "ichimoku" in analysis_results:
                ichi = analysis_results["ichimoku"]
                if ichi["overall_signal"] == "STRONG_BUY":
                    icon = "🚀"
                elif ichi["overall_signal"] == "BUY":
                    icon = "🟢"
                elif ichi["overall_signal"] == "STRONG_SELL":
                    icon = "💥"
                elif ichi["overall_signal"] == "SELL":
                    icon = "🔴"
                else:
                    icon = "🟡"

                print(f"{icon} Ichimoku Cloud: {ichi['description']}")
                print(f"   Tenkan: {ichi['tenkan_sen']} | Kijun: {ichi['kijun_sen']}")
                print(
                    f"   Cloud: {ichi['cloud_bottom']} - {ichi['cloud_top']} | Preis: {ichi['price_vs_cloud']}"
                )

            # VWAP
            if "vwap" in analysis_results:
                vwap = analysis_results["vwap"]
                icon = (
                    "🟢"
                    if vwap["signal"] == "BUY"
                    else "🔴"
                    if vwap["signal"] == "SELL"
                    else "🟡"
                )
                print(f"{icon} VWAP: {vwap['vwap']} - {vwap['description']}")

            # MFI
            if "mfi" in analysis_results:
                mfi = analysis_results["mfi"]
                icon = (
                    "🟢"
                    if mfi["signal"] == "BUY"
                    else "🔴"
                    if mfi["signal"] == "SELL"
                    else "🟡"
                )
                print(f"{icon} Money Flow Index: {mfi['value']} - {mfi['description']}")

            # ADX
            if "adx" in analysis_results:
                adx = analysis_results["adx"]
                trend_icon = "📈" if adx["trend_direction"] == "BULLISH" else "📉"
                strength_icon = "💪" if adx["strong_trend"] else "🤏"
                print(
                    f"{trend_icon}{strength_icon} ADX: {adx['adx']} - {adx['description']}"
                )
                print(f"   DI+: {adx['di_plus']} | DI-: {adx['di_minus']}")

            # MTF Trend
            if "mtf_trend" in analysis_results:
                mtf = analysis_results["mtf_trend"]
                icon = "🔥" if "FULL" in mtf["alignment"] else ("🟢" if mtf["signal"] in ["BUY", "STRONG_BUY"] else "🔴" if mtf["signal"] in ["SELL", "STRONG_SELL"] else "🟡")
                print(f"{icon} MTF Trend Alignment: {mtf['alignment']} - {mtf['description']}")

            print(f"{'=' * 60}")

            # Konsens
            consensus, description = self.get_signal_consensus(analysis_results)
            consensus_icon = (
                "🚀"
                if consensus == "STRONG_BUY"
                else "🟢"
                if consensus == "BUY"
                else "💥"
                if consensus == "STRONG_SELL"
                else "🔴"
                if consensus == "SELL"
                else "🟡"
            )

            print(f"\n{consensus_icon} SIGNAL-KONSENS: {description}")
            print(f"{'=' * 60}")

        except Exception as e:
            self.log("ERROR", f"Report Print Fehler: {e}")

    def update_settings(self, **kwargs):
        """
        Aktualisiert Indikator-Einstellungen
        """
        try:
            updated = []

            for key, value in kwargs.items():
                if hasattr(self, key):
                    old_value = getattr(self, key)
                    setattr(self, key, value)
                    updated.append(f"{key}: {old_value} -> {value}")

            if updated:
                self.log("INFO", f"Settings aktualisiert: {', '.join(updated)}")
                return True
            else:
                self.log("WARNING", "Keine gültigen Settings gefunden")
                return False

        except Exception as e:
            self.log("ERROR", f"Settings Update Fehler: {e}")
            return False


# Integration Helper Klasse
class IndicatorIntegration:
    """
    Hilfklasse zur Integration der erweiterten Indikatoren in das Haupt-FinGPT System
    """

    def __init__(self, fingpt_instance):
        """
        Initialisiert die Integration

        Args:
            fingpt_instance: Die Haupt-FinGPT Instanz
        """
        self.fingpt = fingpt_instance
        self.advanced_indicators = AdvancedIndicators(logger=fingpt_instance.logger)

        # Füge erweiterte Menü-Optionen hinzu
        self.add_menu_options()

    def add_menu_options(self):
        """
        Fügt neue Menü-Optionen für erweiterte Indikatoren hinzu
        """
        # Diese Methode würde das Hauptmenü erweitern
        pass

    def enhanced_ai_analysis(
        self, symbol, timeframe=mt5.TIMEFRAME_M15, include_advanced=True
    ):
        """
        Erweiterte KI-Analyse mit allen Indikatoren

        Args:
            symbol: Trading Symbol
            timeframe: Zeitrahmen für die Analyse
            include_advanced: Ob erweiterte Indikatoren einbezogen werden sollen

        Returns:
            str: Vollständige Analyse mit KI-Bewertung
        """
        try:
            # Basis-Daten vom Hauptsystem
            live_data = self.fingpt.get_mt5_live_data(symbol)

            analysis_context = live_data

            if include_advanced:
                # Erweiterte Indikatoren hinzufügen
                advanced_analysis = self.advanced_indicators.get_comprehensive_analysis(
                    symbol, timeframe
                )

                if advanced_analysis:
                    # Formatiere erweiterte Daten für KI
                    advanced_summary = self.format_advanced_data_for_ai(
                        advanced_analysis
                    )
                    analysis_context += f"\n\nERWEITERTE INDIKATOREN (TF: {timeframe}):\n{advanced_summary}"

                    # Konsens-Signal
                    consensus, consensus_desc = (
                        self.advanced_indicators.get_signal_consensus(advanced_analysis)
                    )
                    analysis_context += (
                        f"\nSIGNAL-KONSENS: {consensus} - {consensus_desc}"
                    )

            # KI-Prompt erweitern
            enhanced_prompt = f"""
Führe eine vollständige technische Analyse für {symbol} durch.

VERFÜGBARE DATEN:
{analysis_context}

Berücksichtige folgende erweiterte Indikatoren:
- Williams %R (Momentum-Oszillator)
- Commodity Channel Index (CCI) (Trend/Divergenz)
- Awesome Oscillator (Momentum-Änderungen)
- Ichimoku Cloud (Komplettes Trading-System)
- VWAP (Volumen-gewichteter Preis)
- Money Flow Index (MFI) (Volumen + Preis)
- Average Directional Index (ADX) (Trend-Stärke)
- MTF Trend Alignment (Multi-Timeframe Trend Bestätigung)

Analysiere:
1. Momentum-Indikatoren (Williams %R, CCI, AO)
2. Trend-Indikatoren (Ichimoku, ADX)
3. Volumen-Indikatoren (MFI, VWAP)
4. Konvergenz/Divergenz zwischen Indikatoren
5. Signal-Bestätigung zwischen verschiedenen Timeframes

Gib eine strukturierte Empfehlung:
- HAUPTSIGNAL: BUY/SELL/WARTEN
- KONFIDENZ: Hoch/Mittel/Niedrig
- ENTRY-PREIS: Konkreter Vorschlag
- STOP-LOSS: Basierend auf technischen Levels
- TAKE-PROFIT: Realistische Ziele
- BEGRÜNDUNG: Welche Indikatoren unterstützen die Entscheidung
- RISIKO-BEWERTUNG: Potentielle Gefahren

Antworte präzise und konkret auf Deutsch.
"""

            # KI-Analyse durchführen
            ai_response = self.fingpt.chat_with_model(enhanced_prompt, "")

            return ai_response

        except Exception as e:
            return f"Erweiterte Analyse Fehler: {e}"

    def format_advanced_data_for_ai(self, advanced_analysis):
        """
        Formatiert die erweiterten Indikator-Daten für die KI
        """
        try:
            formatted_lines = []

            for indicator, data in advanced_analysis.items():
                if indicator == "williams_r":
                    formatted_lines.append(
                        f"Williams %R: {data['value']}% ({data['signal']}) - {data['description']}"
                    )

                elif indicator == "cci":
                    formatted_lines.append(
                        f"CCI: {data['value']} ({data['signal']}) - {data['description']}"
                    )

                elif indicator == "awesome_oscillator":
                    formatted_lines.append(
                        f"Awesome Oscillator: {data['value']} ({data['signal']}) - {data['description']}"
                    )

                elif indicator == "ichimoku":
                    formatted_lines.append(
                        f"Ichimoku: {data['overall_signal']} - {data['description']}"
                    )
                    formatted_lines.append(
                        f"  Cloud Position: {data['price_vs_cloud']}, TK Signal: {data['tk_signal']}"
                    )

                elif indicator == "vwap":
                    formatted_lines.append(
                        f"VWAP: {data['vwap']} ({data['signal']}) - {data['description']}"
                    )

                elif indicator == "mfi":
                    formatted_lines.append(
                        f"Money Flow Index: {data['value']} ({data['signal']}) - {data['description']}"
                    )

                elif indicator == "adx":
                    formatted_lines.append(
                        f"ADX: {data['adx']} - {data['description']}"
                    )
                    formatted_lines.append(
                        f"  Trend Strength: {data['trend_strength']}, Direction: {data['trend_direction']}"
                    )

                elif indicator == "mtf_trend":
                    formatted_lines.append(
                        f"MTF Trend Alignment: {data['alignment']} ({data['signal']}) - {data['description']}"
                    )

            return "\n".join(formatted_lines)

        except Exception as e:
            return f"Formatierung Fehler: {e}"

    def create_trading_signal(
        self, symbol, timeframe=mt5.TIMEFRAME_M15, use_advanced=True
    ):
        """
        Erstellt ein Trading-Signal basierend auf allen verfügbaren Indikatoren

        Args:
            symbol: Trading Symbol
            timeframe: Zeitrahmen für die Analyse
            use_advanced: Ob erweiterte Indikatoren verwendet werden sollen

        Returns:
            dict: Trading-Signal mit Details
        """
        try:
            # Basis-Indikatoren vom Hauptsystem
            rsi_value = self.fingpt.calculate_rsi(symbol, timeframe)
            macd_data = self.fingpt.calculate_macd(symbol, timeframe)
            sr_data = self.fingpt.calculate_support_resistance(symbol, timeframe)

            # Basis-Signale
            signals = {}
            signal_weights = {}

            if rsi_value:
                rsi_signal, rsi_desc = self.fingpt.get_rsi_signal(rsi_value)
                signals["RSI"] = {
                    "signal": rsi_signal,
                    "description": rsi_desc,
                    "value": rsi_value,
                }
                signal_weights["RSI"] = 1.0

            if macd_data:
                macd_signal, macd_desc = self.fingpt.get_macd_signal(macd_data)
                signals["MACD"] = {"signal": macd_signal, "description": macd_desc}
                signal_weights["MACD"] = 1.5

            if sr_data:
                current_price = sr_data["current_price"]
                sr_signal, sr_desc = self.fingpt.get_sr_signal(sr_data, current_price)
                signals["S/R"] = {"signal": sr_signal, "description": sr_desc}
                signal_weights["S/R"] = 1.2

            # Erweiterte Indikatoren hinzufügen
            if use_advanced:
                advanced_analysis = self.advanced_indicators.get_comprehensive_analysis(
                    symbol
                )

                for indicator, data in advanced_analysis.items():
                    if "signal" in data:
                        signals[indicator.upper()] = {
                            "signal": data["signal"],
                            "description": data["description"],
                        }
                        # Gewichtungen für erweiterte Indikatoren
                        if indicator == "ichimoku":
                            signal_weights[indicator.upper()] = 2.0
                        elif indicator == "adx":
                            signal_weights[indicator.upper()] = 1.8
                        elif indicator == "mtf_trend":
                            signal_weights[indicator.upper()] = 2.5
                        else:
                            signal_weights[indicator.upper()] = 1.0

            # Signal-Konsens berechnen
            buy_score = 0
            sell_score = 0
            total_weight = 0

            supporting_signals = []
            conflicting_signals = []

            for indicator, signal_data in signals.items():
                weight = signal_weights.get(indicator, 1.0)
                signal = signal_data["signal"]

                if signal in ["BUY", "STRONG_BUY"]:
                    buy_score += weight
                    supporting_signals.append(
                        f"{indicator}: {signal_data['description']}"
                    )
                elif signal in ["SELL", "STRONG_SELL"]:
                    sell_score += weight
                    supporting_signals.append(
                        f"{indicator}: {signal_data['description']}"
                    )
                elif signal == "NEUTRAL":
                    conflicting_signals.append(
                        f"{indicator}: {signal_data['description']}"
                    )

                total_weight += weight

            # Finales Signal bestimmen
            if total_weight > 0:
                buy_ratio = buy_score / total_weight
                sell_ratio = sell_score / total_weight

                if buy_ratio >= 0.7:
                    final_signal = "STRONG_BUY"
                    confidence = "HOCH"
                elif buy_ratio >= 0.5:
                    final_signal = "BUY"
                    confidence = "MITTEL"
                elif sell_ratio >= 0.7:
                    final_signal = "STRONG_SELL"
                    confidence = "HOCH"
                elif sell_ratio >= 0.5:
                    final_signal = "SELL"
                    confidence = "MITTEL"
                else:
                    final_signal = "NEUTRAL"
                    confidence = "NIEDRIG"
            else:
                final_signal = "NEUTRAL"
                confidence = "NIEDRIG"

            return {
                "symbol": symbol,
                "signal": final_signal,
                "confidence": confidence,
                "buy_ratio": buy_ratio if total_weight > 0 else 0,
                "sell_ratio": sell_ratio if total_weight > 0 else 0,
                "supporting_signals": supporting_signals[:5],  # Top 5
                "conflicting_signals": conflicting_signals[:3],  # Top 3
                "total_indicators": len(signals),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            return {
                "symbol": symbol,
                "signal": "ERROR",
                "confidence": "NIEDRIG",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
