import logging
import numpy as np

class MarketAnalyzer:
    def __init__(self, broker=None, logger=None):
        self.broker = broker  # Needs MT5Broker instance
        self.logger = logger or logging.getLogger(__name__)

        # Settings mapped from FinGPT.py
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        
        self.sr_lookback_period = 50
        self.sr_tolerance = 0.0002
        self.sr_strength_threshold = 3
        
        self.trend_ema_period = 50
        self.trend_strength_threshold = 0.0010

    def log(self, level, message, category="ANALYSIS"):
        if self.logger:
             formatted_message = f"[{category}] {message}"
             if level == "INFO": self.logger.info(formatted_message)
             elif level == "WARNING": self.logger.warning(formatted_message)
             elif level == "ERROR": self.logger.error(formatted_message)
             elif level == "DEBUG": self.logger.debug(formatted_message)

    def calculate_rsi(self, symbol, timeframe, period=None):
        """Berechnet RSI für ein Symbol"""
        if not self.broker or not self.broker.mt5_connected:
            return None
        
        try:
            import MetaTrader5 as mt5
            if period is None:
                period = self.rsi_period
            
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + 10)
            if rates is None or len(rates) < period + 1:
                return None
            
            closes = np.array([rate['close'] for rate in rates])
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return round(rsi, 2)
            
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

    def calculate_macd(self, symbol, timeframe, fast_period=12, slow_period=26, signal_period=9):
        """Berechnet MACD für ein Symbol"""
        if not self.broker or not self.broker.mt5_connected:
            return None

        try:
            import MetaTrader5 as mt5
            required_bars = max(slow_period, signal_period) + signal_period + 20
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, required_bars)
        
            if rates is None or len(rates) < required_bars:
                return None
        
            closes = np.array([rate['close'] for rate in rates])
        
            def calculate_ema(data, period):
                alpha = 2 / (period + 1)
                ema = np.zeros_like(data)
                ema[0] = data[0]
                for i in range(1, len(data)):
                    ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
                return ema
        
            fast_ema = calculate_ema(closes, fast_period)
            slow_ema = calculate_ema(closes, slow_period)
            macd_line = fast_ema - slow_ema
            signal_line = calculate_ema(macd_line, signal_period)
            histogram = macd_line - signal_line
        
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            current_histogram = histogram[-1]
        
            prev_macd = macd_line[-2] if len(macd_line) > 1 else current_macd
            prev_signal = signal_line[-2] if len(signal_line) > 1 else current_signal
            prev_histogram = histogram[-2] if len(histogram) > 1 else current_histogram
        
            if len(histogram) >= 3:
                histogram_trend = "STEIGEND" if histogram[-1] > histogram[-2] > histogram[-3] else \
                                "FALLEND" if histogram[-1] < histogram[-2] < histogram[-3] else "SEITWÄRTS"
            else:
                histogram_trend = "UNBEKANNT"
        
            return {
                'macd': round(current_macd, 6),
                'signal': round(current_signal, 6),
                'histogram': round(current_histogram, 6),
                'prev_macd': round(prev_macd, 6),
                'prev_signal': round(prev_signal, 6),
                'prev_histogram': round(prev_histogram, 6),
                'histogram_trend': histogram_trend,
                'macd_line': macd_line[-10:],
                'signal_line': signal_line[-10:],
                'histogram_values': histogram[-10:]
            }
        except Exception as e:
            self.log("ERROR", f"MACD Berechnung Fehler: {e}")
            return None

    def get_macd_signal(self, macd_data):
         """Interpretiert MACD-Werte für Trading-Signal"""
         if not macd_data:
             return "NEUTRAL", "MACD nicht verfügbar"

         try:
             macd = macd_data['macd']
             signal = macd_data['signal']
             histogram = macd_data['histogram']
             prev_macd = macd_data['prev_macd']
             prev_signal = macd_data['prev_signal']
             prev_histogram = macd_data['prev_histogram']
             histogram_trend = macd_data['histogram_trend']
         
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
                 description = f"Starkes Kaufsignal ({signal_strength}): {', '.join(signals[:2])}"
             elif signal_strength >= 1:
                 main_signal = "BUY"
                 description = f"Kaufsignal ({signal_strength}): {', '.join(signals[:2])}"
             elif signal_strength <= -3:
                 main_signal = "SELL"
                 description = f"Starkes Verkaufssignal ({signal_strength}): {', '.join(signals[:2])}"
             elif signal_strength <= -1:
                 main_signal = "SELL"
                 description = f"Verkaufssignal ({signal_strength}): {', '.join(signals[:2])}"
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
             if lookback is None:
                 lookback = self.sr_lookback_period
             
             rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, lookback)
             if rates is None or len(rates) < 20:
                 return None
             
             highs = np.array([rate['high'] for rate in rates])
             lows = np.array([rate['low'] for rate in rates])
             closes = np.array([rate['close'] for rate in rates])
             
             resistance_levels = []
             support_levels = []
             
             for i in range(2, len(highs) - 2):
                 if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                     highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                     resistance_levels.append(highs[i])
                 
                 if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                     lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                     support_levels.append(lows[i])
             
             def group_levels(levels, tolerance):
                 if not levels: return []
                 grouped = []
                 levels_sorted = sorted(levels)
                 current_group = [levels_sorted[0]]
                 
                 for level in levels_sorted[1:]:
                     if abs(level - current_group[-1]) <= tolerance:
                         current_group.append(level)
                     else:
                         avg_level = sum(current_group) / len(current_group)
                         strength = len(current_group)
                         grouped.append((avg_level, strength))
                         current_group = [level]
                 
                 if current_group:
                     avg_level = sum(current_group) / len(current_group)
                     strength = len(current_group)
                     grouped.append((avg_level, strength))
                 return grouped
             
             grouped_resistance = group_levels(resistance_levels, self.sr_tolerance)
             grouped_support = group_levels(support_levels, self.sr_tolerance)
             
             strong_resistance = [(level, strength) for level, strength in grouped_resistance if strength >= self.sr_strength_threshold]
             strong_support = [(level, strength) for level, strength in grouped_support if strength >= self.sr_strength_threshold]
             
             strong_resistance.sort(key=lambda x: x[1], reverse=True)
             strong_support.sort(key=lambda x: x[1], reverse=True)
             
             current_price = closes[-1]
             nearest_resistance = next(((lvl, s) for lvl, s in strong_resistance if lvl > current_price), None)
             nearest_support = next(((lvl, s) for lvl, s in strong_support if lvl < current_price), None)
             
             return {
                 'current_price': current_price,
                 'nearest_resistance': nearest_resistance,
                 'nearest_support': nearest_support,
                 'all_resistance': strong_resistance[:5],
                 'all_support': strong_support[:5]
             }
             
         except Exception as e:
             self.log("ERROR", f"S/R Berechnung Fehler: {e}")
             return None

    def get_sr_signal(self, sr_data, current_price):
         """Interpretiert Support/Resistance für Trading-Signal"""
         if not sr_data:
             return "NEUTRAL", "S/R nicht verfügbar"
         
         try:
             signals = []
             
             if sr_data['nearest_support']:
                 support_level, support_strength = sr_data['nearest_support']
                 dist = abs(current_price - support_level) / current_price * 100
                 if dist < 0.1:
                     signals.append(f"BUY - An starkem Support ({support_level:.5f}, Stärke: {support_strength})")
                 elif dist < 0.2:
                     signals.append(f"WATCH - Nahe Support ({support_level:.5f})")
             
             if sr_data['nearest_resistance']:
                 resistance_level, resistance_strength = sr_data['nearest_resistance']
                 dist = abs(current_price - resistance_level) / current_price * 100
                 if dist < 0.1:
                     signals.append(f"SELL - An starker Resistance ({resistance_level:.5f}, Stärke: {resistance_strength})")
                 elif dist < 0.2:
                     signals.append(f"WATCH - Nahe Resistance ({resistance_level:.5f})")
             
             if not signals:
                 return "NEUTRAL", "Zwischen S/R Levels"
             
             if any("BUY" in signal for signal in signals):
                 return "BUY", [s for s in signals if "BUY" in s][0]
             elif any("SELL" in signal for signal in signals):
                 return "SELL", [s for s in signals if "SELL" in s][0]
             else:
                 return "WATCH", signals[0]
                 
         except Exception as e:
             return "NEUTRAL", f"S/R Analyse Fehler: {e}"

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
         
             closes = np.array([rate['close'] for rate in rates])
             highs = np.array([rate['high'] for rate in rates])
             lows = np.array([rate['low'] for rate in rates])
         
             def calculate_ema(data, period):
                 alpha = 2 / (period + 1)
                 ema = np.zeros_like(data)
                 ema[0] = data[0]
                 for i in range(1, len(data)):
                     ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
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
             higher_highs = len([i for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1]]) >= 6
             lower_lows = len([i for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i-1]]) >= 6
         
             if price_above_ema and ema_rising:
                 direction = "BULLISH" if trend_strength >= self.trend_strength_threshold else "WEAK_BULLISH"
             elif not price_above_ema and not ema_rising:
                 direction = "BEARISH" if trend_strength >= self.trend_strength_threshold else "WEAK_BEARISH"
             else:
                 direction = "NEUTRAL"
         
             if direction == "BULLISH" and not higher_highs: direction = "WEAK_BULLISH"
             elif direction == "BEARISH" and not lower_lows: direction = "WEAK_BEARISH"
         
             trend_quality = "STRONG" if trend_strength >= self.trend_strength_threshold * 2 else \
                            "MODERATE" if trend_strength >= self.trend_strength_threshold else "WEAK"
         
             momentum_bars = 5
             if len(closes) >= momentum_bars:
                 momentum = closes[-1] - closes[-momentum_bars]
                 momentum_direction = "UP" if momentum > 0 else "DOWN" if momentum < 0 else "FLAT"
             else:
                 momentum = 0
                 momentum_direction = "FLAT"
         
             return {
                 'direction': direction,
                 'strength': trend_strength,
                 'quality': trend_quality,
                 'current_price': current_price,
                 'ema_level': current_ema,
                 'ema_slope': ema_slope,
                 'price_above_ema': price_above_ema,
                 'ema_rising': ema_rising,
                 'momentum': momentum,
                 'momentum_direction': momentum_direction,
                 'higher_highs': higher_highs,
                 'lower_lows': lower_lows,
                 'timeframe': trend_timeframe
             }
         except Exception as e:
             self.log("ERROR", f"Trend-Analyse Fehler: {e}")
             return None
