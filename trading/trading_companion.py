#!/usr/bin/env python3
"""
Trading Companion - Erweiterte Analyse-Tools
Ergänzung zum FinGPT MT5 System
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")


class TradingCompanion:
    def __init__(self):
        self.mt5_connected = False
        self.data_cache = {}
        self.cache_duration = 60  # Cache für 60 Sekunden

        # MACD Settings
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9

        # Bollinger Band Settings
        self.bb_period = 20
        self.bb_deviation = 2.0

        # Stochastic Settings
        self.stoch_k_period = 14
        self.stoch_d_period = 3
        self.stoch_slowing = 3

        # ATR Settings
        self.atr_period = 14

        # Multi-Timeframe Settings
        self.timeframes = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

        # Trade Journal
        self.trade_log_file = "trade_journal.json"

        # Error Handling
        self.last_error = None
        self.error_log = []

    def start(self):
        """Startet den Trading Companion"""
        try:
            if not self.mt5_connected:
                if not self.connect_mt5():
                    raise Exception("MT5 Verbindung konnte nicht hergestellt werden")

            print("Trading Companion gestartet")
            print("=" * 50)

            # Test der Datenverbindung
            test_symbol = "EURUSD"
            if not self.test_connection(test_symbol):
                raise Exception(f"Datenverbindung für {test_symbol} fehlgeschlagen")

            return True

        except Exception as e:
            self.log_error("Start fehlgeschlagen", str(e))
            return False

    def test_connection(self, symbol):
        """Testet die Datenverbindung"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return False
            print(f"Datenverbindung OK - {symbol}: {(tick.bid + tick.ask) / 2:.5f}")
            return True
        except:
            return False

    def log_error(self, context, error_msg):
        """Protokolliert Fehler"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_entry = {
            "timestamp": timestamp,
            "context": context,
            "error": str(error_msg),
        }
        self.error_log.append(error_entry)
        self.last_error = error_entry
        print(f"Fehler: {context} - {error_msg}")

    def connect_mt5(self):
        """Verbindet zu MT5"""
        try:
            if not mt5.initialize():
                return False
            self.mt5_connected = True
            print("Trading Companion: MT5 verbunden")
            return True
        except Exception as e:
            print(f"MT5 Verbindung fehlgeschlagen: {e}")
            return False

    def get_cached_data(self, symbol, timeframe, bars):
        """Holt Daten mit Caching"""
        cache_key = f"{symbol}_{timeframe}_{bars}"
        now = time.time()

        if cache_key in self.data_cache:
            data, timestamp = self.data_cache[cache_key]
            if now - timestamp < self.cache_duration:
                return data

        # Neue Daten holen
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is not None:
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            self.data_cache[cache_key] = (df, now)
            return df
        return None

    def calculate_macd(self, symbol, timeframe=mt5.TIMEFRAME_M15, bars=100):
        """Berechnet MACD Indikator"""
        try:
            df = self.get_cached_data(symbol, timeframe, bars)
            if df is None or len(df) < self.macd_slow:
                return None

            close = df["close"]

            # EMA Berechnung
            ema_fast = close.ewm(span=self.macd_fast).mean()
            ema_slow = close.ewm(span=self.macd_slow).mean()

            # MACD Line
            macd_line = ema_fast - ema_slow

            # Signal Line
            signal_line = macd_line.ewm(span=self.macd_signal).mean()

            # Histogram
            histogram = macd_line - signal_line

            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1]
            prev_histogram = histogram.iloc[-2]

            # Signal bestimmen
            signal = "NEUTRAL"
            description = ""

            if current_macd > current_signal and prev_histogram < 0 < current_histogram:
                signal = "BUY"
                description = "MACD Bullish Crossover"
            elif (
                current_macd < current_signal and prev_histogram > 0 > current_histogram
            ):
                signal = "SELL"
                description = "MACD Bearish Crossover"
            elif current_histogram > 0:
                signal = "BULLISH"
                description = "MACD über Signal"
            elif current_histogram < 0:
                signal = "BEARISH"
                description = "MACD unter Signal"

            return {
                "macd": round(current_macd, 6),
                "signal": round(current_signal, 6),
                "histogram": round(current_histogram, 6),
                "signal_type": signal,
                "description": description,
            }

        except Exception as e:
            print(f"MACD Fehler: {e}")
            return None

    def calculate_bollinger_bands(self, symbol, timeframe=mt5.TIMEFRAME_M15, bars=50):
        """Berechnet Bollinger Bänder"""
        try:
            df = self.get_cached_data(symbol, timeframe, bars)
            if df is None or len(df) < self.bb_period:
                return None

            close = df["close"]

            # Moving Average
            sma = close.rolling(window=self.bb_period).mean()

            # Standard Deviation
            std = close.rolling(window=self.bb_period).std()

            # Bollinger Bands
            upper_band = sma + (std * self.bb_deviation)
            lower_band = sma - (std * self.bb_deviation)

            current_price = close.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_middle = sma.iloc[-1]

            # Position relativ zu den Bändern
            bb_position = (current_price - current_lower) / (
                current_upper - current_lower
            )

            # Bandwidth (Volatilität)
            bandwidth = (current_upper - current_lower) / current_middle * 100

            # Signal bestimmen
            signal = "NEUTRAL"
            description = ""

            if current_price >= current_upper:
                signal = "SELL"
                description = "Preis an oberem Band (überkauft)"
            elif current_price <= current_lower:
                signal = "BUY"
                description = "Preis an unterem Band (überverkauft)"
            elif bb_position > 0.8:
                signal = "BEARISH"
                description = "Nahe oberem Band"
            elif bb_position < 0.2:
                signal = "BULLISH"
                description = "Nahe unterem Band"

            return {
                "upper": round(current_upper, 5),
                "middle": round(current_middle, 5),
                "lower": round(current_lower, 5),
                "position": round(bb_position, 2),
                "bandwidth": round(bandwidth, 2),
                "signal_type": signal,
                "description": description,
            }

        except Exception as e:
            print(f"Bollinger Bands Fehler: {e}")
            return None

    def calculate_stochastic(self, symbol, timeframe=mt5.TIMEFRAME_M15, bars=50):
        """Berechnet Stochastic Oscillator"""
        try:
            df = self.get_cached_data(symbol, timeframe, bars)
            if df is None or len(df) < self.stoch_k_period:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]

            # %K Berechnung
            lowest_low = low.rolling(window=self.stoch_k_period).min()
            highest_high = high.rolling(window=self.stoch_k_period).max()

            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))

            # %K Smoothing
            k_percent = k_percent.rolling(window=self.stoch_slowing).mean()

            # %D Berechnung (Signal Line)
            d_percent = k_percent.rolling(window=self.stoch_d_period).mean()

            current_k = k_percent.iloc[-1]
            current_d = d_percent.iloc[-1]
            prev_k = k_percent.iloc[-2]
            prev_d = d_percent.iloc[-2]

            # Signal bestimmen
            signal = "NEUTRAL"
            description = ""

            if current_k < 20 and current_d < 20:
                signal = "BUY"
                description = "Stochastic überverkauft"
            elif current_k > 80 and current_d > 80:
                signal = "SELL"
                description = "Stochastic überkauft"
            elif prev_k <= prev_d and current_k > current_d:
                signal = "BUY"
                description = "Stochastic Bullish Crossover"
            elif prev_k >= prev_d and current_k < current_d:
                signal = "SELL"
                description = "Stochastic Bearish Crossover"

            return {
                "k_percent": round(current_k, 2),
                "d_percent": round(current_d, 2),
                "signal_type": signal,
                "description": description,
            }

        except Exception as e:
            print(f"Stochastic Fehler: {e}")
            return None

    def calculate_atr(self, symbol, timeframe=mt5.TIMEFRAME_M15, bars=50):
        """Berechnet Average True Range"""
        try:
            df = self.get_cached_data(symbol, timeframe, bars)
            if df is None or len(df) < self.atr_period + 1:
                return None

            high = df["high"]
            low = df["low"]
            close = df["close"]
            prev_close = close.shift(1)

            # True Range berechnen
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR als gleitender Durchschnitt
            atr = true_range.rolling(window=self.atr_period).mean()

            current_atr = atr.iloc[-1]
            current_price = close.iloc[-1]

            # ATR als Prozent des Preises
            atr_percent = (current_atr / current_price) * 100

            # Volatilitäts-Klassifizierung
            if atr_percent < 0.5:
                volatility = "NIEDRIG"
            elif atr_percent < 1.0:
                volatility = "NORMAL"
            elif atr_percent < 2.0:
                volatility = "HOCH"
            else:
                volatility = "EXTREM"

            return {
                "atr": round(current_atr, 5),
                "atr_percent": round(atr_percent, 2),
                "volatility": volatility,
                "stop_distance": round(current_atr * 2, 5),  # 2x ATR für Stop-Loss
            }

        except Exception as e:
            print(f"ATR Fehler: {e}")
            return None

    def multi_timeframe_analysis(self, symbol):
        """Analysiert mehrere Zeitrahmen"""
        try:
            analysis = {}
            timeframes_to_check = ["M15", "H1", "H4", "D1"]

            for tf_name in timeframes_to_check:
                tf = self.timeframes[tf_name]

                # RSI für jeden Zeitrahmen
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 30)
                if rates is not None and len(rates) > 14:
                    closes = np.array([rate["close"] for rate in rates])
                    deltas = np.diff(closes)
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)

                    avg_gain = np.mean(gains[-14:])
                    avg_loss = np.mean(losses[-14:])

                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    else:
                        rsi = 100

                    # Trend bestimmen
                    if rsi > 70:
                        trend = "BULLISH_STRONG"
                    elif rsi > 50:
                        trend = "BULLISH"
                    elif rsi < 30:
                        trend = "BEARISH_STRONG"
                    elif rsi < 50:
                        trend = "BEARISH"
                    else:
                        trend = "NEUTRAL"

                    analysis[tf_name] = {"rsi": round(rsi, 2), "trend": trend}

            # Consensus bestimmen
            bullish_count = sum(
                1 for tf in analysis.values() if "BULLISH" in tf["trend"]
            )
            bearish_count = sum(
                1 for tf in analysis.values() if "BEARISH" in tf["trend"]
            )

            if bullish_count >= 3:
                consensus = "BULLISH"
            elif bearish_count >= 3:
                consensus = "BEARISH"
            else:
                consensus = "MIXED"

            return {
                "timeframes": analysis,
                "consensus": consensus,
                "strength": max(bullish_count, bearish_count),
            }

        except Exception as e:
            print(f"Multi-Timeframe Fehler: {e}")
            return None

    def comprehensive_analysis(self, symbol):
        """Führt umfassende technische Analyse durch"""
        try:
            print(f"\n{'=' * 50}")
            print(f"UMFASSENDE ANALYSE: {symbol}")
            print(f"{'=' * 50}")

            # Aktuelle Marktdaten
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return "Keine Marktdaten verfügbar"

            current_price = (tick.bid + tick.ask) / 2
            spread = tick.ask - tick.bid

            print(f"Aktueller Preis: {current_price:.5f}")
            print(f"Spread: {spread:.5f}")
            print(f"Zeit: {datetime.fromtimestamp(tick.time).strftime('%H:%M:%S')}")

            # MACD Analyse
            print(f"\n--- MACD ANALYSE ---")
            macd_data = self.calculate_macd(symbol)
            if macd_data:
                print(f"MACD: {macd_data['macd']:.6f}")
                print(f"Signal: {macd_data['signal']:.6f}")
                print(f"Histogram: {macd_data['histogram']:.6f}")
                print(
                    f"Signal: {macd_data['signal_type']} - {macd_data['description']}"
                )
            else:
                print("MACD Daten nicht verfügbar")

            # Bollinger Bands Analyse
            print(f"\n--- BOLLINGER BANDS ---")
            bb_data = self.calculate_bollinger_bands(symbol)
            if bb_data:
                print(f"Oberes Band: {bb_data['upper']:.5f}")
                print(f"Mittleres Band: {bb_data['middle']:.5f}")
                print(f"Unteres Band: {bb_data['lower']:.5f}")
                print(f"Position: {bb_data['position']} (0=unten, 1=oben)")
                print(f"Bandwidth: {bb_data['bandwidth']:.2f}%")
                print(f"Signal: {bb_data['signal_type']} - {bb_data['description']}")
            else:
                print("Bollinger Bands Daten nicht verfügbar")

            # Stochastic Analyse
            print(f"\n--- STOCHASTIC ---")
            stoch_data = self.calculate_stochastic(symbol)
            if stoch_data:
                print(f"%K: {stoch_data['k_percent']:.2f}")
                print(f"%D: {stoch_data['d_percent']:.2f}")
                print(
                    f"Signal: {stoch_data['signal_type']} - {stoch_data['description']}"
                )
            else:
                print("Stochastic Daten nicht verfügbar")

            # ATR Analyse
            print(f"\n--- VOLATILITÄT (ATR) ---")
            atr_data = self.calculate_atr(symbol)
            if atr_data:
                print(f"ATR: {self.atr_period} Periode")
                print(f"ATR: {atr_data['atr']:.5f}")
                print(f"ATR %: {atr_data['atr_percent']:.2f}%")
                print(f"Volatilität: {atr_data['volatility']}")
                print(f"Empfohlener Stop-Loss Abstand: {atr_data['stop_distance']:.5f}")
            else:
                print("ATR Daten nicht verfügbar")

            # Multi-Timeframe Analyse
            print(f"\n--- MULTI-TIMEFRAME TREND ---")
            mtf_data = self.multi_timeframe_analysis(symbol)
            if mtf_data:
                for tf, data in mtf_data["timeframes"].items():
                    print(f"{tf}: RSI {data['rsi']:.1f} - {data['trend']}")
                print(
                    f"Consensus: {mtf_data['consensus']} (Stärke: {mtf_data['strength']}/4)"
                )
            else:
                print("Multi-Timeframe Daten nicht verfügbar")

            # Zusammenfassung und Empfehlung
            print(f"\n--- TRADING EMPFEHLUNG ---")
            signals = []

            if macd_data and macd_data["signal_type"] in ["BUY", "SELL"]:
                signals.append(f"MACD: {macd_data['signal_type']}")

            if bb_data and bb_data["signal_type"] in ["BUY", "SELL"]:
                signals.append(f"BB: {bb_data['signal_type']}")

            if stoch_data and stoch_data["signal_type"] in ["BUY", "SELL"]:
                signals.append(f"STOCH: {stoch_data['signal_type']}")

            if mtf_data:
                if mtf_data["consensus"] == "BULLISH" and mtf_data["strength"] >= 3:
                    signals.append("MTF: BULLISH")
                elif mtf_data["consensus"] == "BEARISH" and mtf_data["strength"] >= 3:
                    signals.append("MTF: BEARISH")

            if signals:
                buy_signals = sum(1 for s in signals if "BUY" in s or "BULLISH" in s)
                sell_signals = sum(1 for s in signals if "SELL" in s or "BEARISH" in s)

                if buy_signals > sell_signals:
                    recommendation = "BUY"
                elif sell_signals > buy_signals:
                    recommendation = "SELL"
                else:
                    recommendation = "NEUTRAL"

                print(f"Empfehlung: {recommendation}")
                print(f"Signale: {', '.join(signals)}")

                if atr_data:
                    if recommendation == "BUY":
                        suggested_sl = current_price - atr_data["stop_distance"]
                        suggested_tp = current_price + (atr_data["stop_distance"] * 2)
                        print(f"Stop-Loss: {suggested_sl:.5f}")
                        print(f"Take-Profit: {suggested_tp:.5f}")
                    elif recommendation == "SELL":
                        suggested_sl = current_price + atr_data["stop_distance"]
                        suggested_tp = current_price - (atr_data["stop_distance"] * 2)
                        print(f"Stop-Loss: {suggested_sl:.5f}")
                        print(f"Take-Profit: {suggested_tp:.5f}")
            else:
                print("Empfehlung: WARTEN - Keine klaren Signale")

            return "Analyse abgeschlossen"

        except Exception as e:
            return f"Analyse Fehler: {e}"

    def scan_multiple_pairs(self, symbols=None):
        """Scannt mehrere Währungspaare nach Trading-Gelegenheiten"""
        if symbols is None:
            symbols = [
                "EURUSD",
                "GBPUSD",
                "USDJPY",
                "USDCHF",
                "AUDUSD",
                "USDCAD",
                "NZDUSD",
            ]

        print(f"\n{'=' * 60}")
        print("MARKT-SCANNER")
        print(f"{'=' * 60}")

        opportunities = []

        for symbol in symbols:
            try:
                # Schnelle Analyse für jeden Symbol
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    continue

                current_price = (tick.bid + tick.ask) / 2

                # MACD Check
                macd_data = self.calculate_macd(symbol)
                bb_data = self.calculate_bollinger_bands(symbol)
                atr_data = self.calculate_atr(symbol)

                score = 0
                signals = []

                if macd_data:
                    if macd_data["signal_type"] == "BUY":
                        score += 2
                        signals.append("MACD+")
                    elif macd_data["signal_type"] == "SELL":
                        score -= 2
                        signals.append("MACD-")

                if bb_data:
                    if bb_data["signal_type"] == "BUY":
                        score += 1
                        signals.append("BB+")
                    elif bb_data["signal_type"] == "SELL":
                        score -= 1
                        signals.append("BB-")

                if atr_data:
                    volatility_bonus = 0
                    if atr_data["volatility"] == "NORMAL":
                        volatility_bonus = 1
                    elif atr_data["volatility"] == "NIEDRIG":
                        volatility_bonus = -1
                    score += volatility_bonus

                if abs(score) >= 2:  # Mindest-Score für Gelegenheit
                    direction = "BUY" if score > 0 else "SELL"
                    opportunities.append(
                        {
                            "symbol": symbol,
                            "price": current_price,
                            "direction": direction,
                            "score": score,
                            "signals": signals,
                            "volatility": atr_data["volatility"]
                            if atr_data
                            else "UNBEKANNT",
                        }
                    )

                print(
                    f"{symbol}: {current_price:.5f} | Score: {score:+d} | {', '.join(signals) if signals else 'Neutral'}"
                )

            except Exception as e:
                print(f"{symbol}: Fehler - {e}")

        if opportunities:
            print(f"\n--- TRADING-GELEGENHEITEN ---")
            # Sortiere nach Score
            opportunities.sort(key=lambda x: abs(x["score"]), reverse=True)

            for opp in opportunities:
                print(
                    f"{opp['symbol']}: {opp['direction']} | Score: {opp['score']:+d} | {', '.join(opp['signals'])}"
                )
        else:
            print("\nKeine Trading-Gelegenheiten gefunden")

        return opportunities

    def log_trade_decision(self, symbol, decision, reasoning, indicators):
        """Protokolliert Trading-Entscheidungen"""
        try:
            # Lade existierendes Log
            try:
                with open(self.trade_log_file, "r") as f:
                    log_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                log_data = []

            # Neuer Eintrag
            entry = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "decision": decision,
                "reasoning": reasoning,
                "indicators": indicators,
                "price": None,
            }

            # Aktueller Preis
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                entry["price"] = (tick.bid + tick.ask) / 2

            log_data.append(entry)

            # Behalte nur die letzten 1000 Einträge
            if len(log_data) > 1000:
                log_data = log_data[-1000:]

            # Speichere Log
            with open(self.trade_log_file, "w") as f:
                json.dump(log_data, f, indent=2)

            print(f"Trade-Entscheidung protokolliert: {symbol} - {decision}")

        except Exception as e:
            print(f"Logging Fehler: {e}")

    def interactive_menu(self):
        """Interaktives Menü für Trading Companion"""
        while True:
            print(f"\n{'=' * 50}")
            print("TRADING COMPANION")
            print(f"{'=' * 50}")
            print(f"MT5: {'✅' if self.mt5_connected else '❌'}")

            print("\nOptionen:")
            print("1. Umfassende Analyse (einzelnes Paar)")
            print("2. Markt-Scanner (mehrere Paare)")
            print("3. MACD Analyse")
            print("4. Bollinger Bands Analyse")
            print("5. Stochastic Analyse")
            print("6. ATR/Volatilität Analyse")
            print("7. Multi-Timeframe Analyse")
            print("8. Indikator-Einstellungen")
            print("9. MT5 Verbindung")
            print("10. Beenden")

            choice = input("\nOption (1-10): ").strip()

            if choice == "1":
                symbol = input("Symbol: ").upper()
                if symbol:
                    self.comprehensive_analysis(symbol)

            elif choice == "2":
                symbols_input = input("Symbole (leer für Standard): ").upper()
                if symbols_input:
                    symbols = [s.strip() for s in symbols_input.split(",")]
                    self.scan_multiple_pairs(symbols)
                else:
                    self.scan_multiple_pairs()

            elif choice == "3":
                symbol = input("Symbol für MACD: ").upper()
                if symbol:
                    macd_data = self.calculate_macd(symbol)
                    if macd_data:
                        print(f"\nMACD Analyse für {symbol}:")
                        for key, value in macd_data.items():
                            print(f"{key}: {value}")
                    else:
                        print("MACD Daten nicht verfügbar")

            elif choice == "4":
                symbol = input("Symbol für Bollinger Bands: ").upper()
                if symbol:
                    bb_data = self.calculate_bollinger_bands(symbol)
                    if bb_data:
                        print(f"\nBollinger Bands für {symbol}:")
                        for key, value in bb_data.items():
                            print(f"{key}: {value}")
                    else:
                        print("Bollinger Bands Daten nicht verfügbar")

            elif choice == "5":
                symbol = input("Symbol für Stochastic: ").upper()
                if symbol:
                    stoch_data = self.calculate_stochastic(symbol)
                    if stoch_data:
                        print(f"\nStochastic für {symbol}:")
                        for key, value in stoch_data.items():
                            print(f"{key}: {value}")
                    else:
                        print("Stochastic Daten nicht verfügbar")

            elif choice == "6":
                symbol = input("Symbol für ATR: ").upper()
                if symbol:
                    atr_data = self.calculate_atr(symbol)
                    if atr_data:
                        print(f"\nATR/Volatilität für {symbol}:")
                        for key, value in atr_data.items():
                            print(f"{key}: {value}")
                    else:
                        print("ATR Daten nicht verfügbar")

            elif choice == "7":
                symbol = input("Symbol für Multi-Timeframe: ").upper()
                if symbol:
                    mtf_data = self.multi_timeframe_analysis(symbol)
                    if mtf_data:
                        print(f"\nMulti-Timeframe Analyse für {symbol}:")
                        for tf, data in mtf_data["timeframes"].items():
                            print(f"{tf}: RSI {data['rsi']:.1f} - {data['trend']}")
                        print(
                            f"Consensus: {mtf_data['consensus']} (Stärke: {mtf_data['strength']}/4)"
                        )
                    else:
                        print("Multi-Timeframe Daten nicht verfügbar")

            elif choice == "8":
                print("\nIndikator-Einstellungen:")
                print(f"MACD: {self.macd_fast}/{self.macd_slow}/{self.macd_signal}")
                print(
                    f"Bollinger: {self.bb_period} Periode, {self.bb_deviation} Abweichung"
                )
                print(
                    f"Stochastic: {self.stoch_k_period}/{self.stoch_d_period}/{self.stoch_slowing}"
                )
                print(f"ATR: {self.atr_period}")

            elif choice == "9":
                if self.mt5_connected:
                    mt5.shutdown()
                    self.mt5_connected = False
                    print("MT5 getrennt")
                else:
                    self.connect_mt5()

            elif choice == "10":
                if self.mt5_connected:
                    mt5.shutdown()
                print("Trading Companion beendet")
                break

            else:
                print("Ungültige Option")


def main():
    print("Trading Companion - Erweiterte Analyse-Tools")
    print("=" * 50)

    companion = TradingCompanion()

    try:
        if not companion.start():
            print("Trading Companion konnte nicht gestartet werden")
            if companion.last_error:
                print(f"Letzter Fehler: {companion.last_error['error']}")
            return

        import sys

        if "--daemon" in sys.argv:
            print("Läuft im Daemon-Modus (Hintergrund-Analyse)...")
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
            while True:
                companion.scan_multiple_pairs(symbols)
                time.sleep(300)  # Alle 5 Minuten scannen
        else:
            companion.interactive_menu()
    except KeyboardInterrupt:
        print("\nBeendet durch Benutzer")
    finally:
        if companion.mt5_connected:
            mt5.shutdown()


if __name__ == "__main__":
    main()
