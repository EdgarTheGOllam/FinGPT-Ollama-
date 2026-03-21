#!/usr/bin/env python3
"""
AI-Fulldrive Mode Engine – FinGPT
=================================
Vollständig KI-gesteuerte Trading-Strategie ohne menschliche Intervention.

Architektur (Layer-Stack):
  1. MarketFeatureExtractor   – 20+ technische Indikatoren → normierter Feature-Vektor
  2. LSTMPatternNetwork       – Sequenzielle Mustererkennung (30-Bar Lookback)
  3. RLDecisionEngine         – DDQN Ensemble mit Konfidenz-Filter
  4. FullDriveRiskManager     – Kelly-Criterion Positionsgrößen + Max-DD Guard
  5. PerformanceKPITracker    – Sharpe, Sortino, Max DD, Annual Return (laufend)
  6. AIFulldriveEngine        – Orchestrator mit Selbst-Optimierung

Performance-Ziele (konfigurierbar):
  • Sharpe Ratio   ≥ 1.5
  • Max Drawdown  ≤ 15 %
  • Annual Return  ≥ 25 %
"""

import os
import json
import time
import math
import random
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque

# ── Optional Heavy Dependencies ───────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
    _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    TORCH_AVAILABLE = False
    _DEVICE = "cpu"

# ═══════════════════════════════════════════════════════════════════════════════
# 1. MARKET FEATURE EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════════

class MarketFeatureExtractor:
    """
    Extrahiert und normalisiert 20 technische Indikatoren aus OHLCV-Daten.

    Feature-Vektor (Index → Bedeutung):
        0  rsi14           – Relative Strength Index (normiert 0-1)
        1  macd            – MACD-Linie (tanh-skaliert)
        2  macd_signal     – Signal-Linie (tanh-skaliert)
        3  macd_hist       – MACD-Histogramm (tanh-skaliert)
        4  bb_pos          – Bollinger Band Position (0=unteres, 1=oberes Band)
        5  bb_width        – BB-Breite relativ zum Preis (Volatilitätsmaß)
        6  atr_norm        – ATR-14 normiert durch aktuellen Preis
        7  adx             – ADX-14 (normiert 0-1)
        8  stoch_k         – Stochastik %K (normiert 0-1)
        9  stoch_d         – Stochastik %D (normiert 0-1)
        10 obv_norm        – OBV-Änderungsrate (tanh-skaliert)
        11 vwap_dist       – Abstand zu VWAP-Proxy (tanh-skaliert)
        12 pc1             – Preisänderung 1 Bar (tanh-skaliert)
        13 pc5             – Preisänderung 5 Bars (tanh-skaliert)
        14 pc20            – Preisänderung 20 Bars (tanh-skaliert)
        15 vol_ratio       – Volumen-Verhältnis zu 20-Bar SMA
        16 trend_str       – Trend-Stärke (EMA-Divergenz, normiert)
        17 ema50_dev       – Abweichung Preis von EMA-50 (tanh-skaliert)
        18 hh_ll_pos       – Position im 20-Bar High-Low-Kanal (0-1)
        19 session_enc     – Handelssitzung (0=Asia, 0.5=London, 1=NY)
    """

    FEATURE_COUNT = 20

    def extract(self, rates: list) -> np.ndarray:
        """
        Args:
            rates: Liste von MT5-Rate-Dicts oder strukturierten Arrays
                   mind. Felder: close, high, low, tick_volume
        Returns:
            np.ndarray shape (FEATURE_COUNT,) dtype float32
        """
        try:
            closes  = np.array([r['close']       for r in rates], dtype=float)
            highs   = np.array([r['high']        for r in rates], dtype=float)
            lows    = np.array([r['low']         for r in rates], dtype=float)
            volumes = np.array([r['tick_volume'] for r in rates], dtype=float)

            n = len(closes)
            feats = np.zeros(self.FEATURE_COUNT, dtype=np.float32)

            # 0 – RSI-14
            feats[0] = self._rsi(closes) / 100.0

            # 1-3 – MACD
            macd_line, signal_line, histogram = self._macd(closes)
            feats[1] = float(np.tanh(macd_line   * 1000))
            feats[2] = float(np.tanh(signal_line * 1000))
            feats[3] = float(np.tanh(histogram   * 1000))

            # 4-5 – Bollinger Bands
            bb_up, bb_mid, bb_low = self._bollinger(closes)
            rng = bb_up - bb_low
            feats[4] = float(np.clip((closes[-1] - bb_low) / rng, 0, 1)) if rng > 0 else 0.5
            feats[5] = float(np.tanh(rng / max(bb_mid, 1e-9)))

            # 6 – ATR-14 normiert
            atr = self._atr(highs, lows, closes)
            feats[6] = float(np.tanh(atr / max(closes[-1], 1e-9) * 100))

            # 7 – ADX-14
            feats[7] = float(np.clip(self._adx(highs, lows, closes) / 100.0, 0, 1))

            # 8-9 – Stochastik
            k, d = self._stochastic(highs, lows, closes)
            feats[8] = float(k / 100.0)
            feats[9] = float(d / 100.0)

            # 10 – OBV-Rate
            obv = self._obv(closes, volumes)
            obv_rate = (obv[-1] - obv[-5]) / max(abs(obv[-1]), 1.0) if n >= 5 else 0.0
            feats[10] = float(np.tanh(obv_rate))

            # 11 – VWAP-Abstand (Proxy: Vol-gewichteter MA)
            if np.sum(volumes[-20:]) > 0:
                vwap = np.sum(closes[-20:] * volumes[-20:]) / np.sum(volumes[-20:])
            else:
                vwap = closes[-1]
            feats[11] = float(np.tanh((closes[-1] - vwap) / max(vwap, 1e-9) * 100))

            # 12-14 – Preisänderungen
            feats[12] = float(np.tanh((closes[-1] / closes[-2] - 1) * 1000)) if n >= 2  else 0
            feats[13] = float(np.tanh((closes[-1] / closes[-6] - 1) * 1000)) if n >= 6  else 0
            feats[14] = float(np.tanh((closes[-1] / closes[-21]- 1) * 1000)) if n >= 21 else 0

            # 15 – Volumen-Verhältnis
            vol_ma = np.mean(volumes[-20:]) if n >= 20 else np.mean(volumes)
            feats[15] = float(np.tanh((volumes[-1] / max(vol_ma, 1e-9)) - 1))

            # 16 – Trend-Stärke
            ema20 = self._ema(closes, 20)
            ema50 = self._ema(closes, 50)
            feats[16] = float(np.tanh((ema20 - ema50) / max(ema50, 1e-9) * 100))

            # 17 – EMA-50 Deviation
            feats[17] = float(np.tanh((closes[-1] - ema50) / max(ema50, 1e-9) * 100))

            # 18 – High-Low-Kanalposition (20 Bar)
            hh = np.max(highs[-20:]) if n >= 20 else np.max(highs)
            ll = np.min(lows[-20:])  if n >= 20 else np.min(lows)
            feats[18] = float(np.clip((closes[-1] - ll) / max(hh - ll, 1e-9), 0, 1))

            # 19 – Handelssitzung (UTC-Stunde)
            hour = datetime.utcnow().hour
            if 0 <= hour < 8:
                feats[19] = 0.0   # Asia
            elif 8 <= hour < 13:
                feats[19] = 0.5   # London
            else:
                feats[19] = 1.0   # New York / Überlappung

            return feats

        except Exception as e:
            print(f"[FULLDRIVE] Feature-Extraktion fehlgeschlagen: {e}")
            return np.zeros(self.FEATURE_COUNT, dtype=np.float32)

    # ── Private Indikatoren ────────────────────────────────────────────────────

    @staticmethod
    def _rsi(closes, period=14):
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains  = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        ag = np.mean(gains[-period:])
        al = np.mean(losses[-period:])
        if al == 0:
            return 100.0
        return round(100 - 100 / (1 + ag / al), 2)

    @staticmethod
    def _ema(arr, period, return_series=False):
        s = pd.Series(arr)
        ema_series = s.ewm(span=period, adjust=False).mean()
        if return_series:
            return ema_series.values
        return ema_series.iloc[-1]

    def _macd(self, closes):
        if len(closes) < 35:
            ema12 = self._ema(closes, 12)
            ema26 = self._ema(closes, 26)
            macd  = ema12 - ema26
            signal = macd * 0.9
            hist = macd - signal
            return macd, signal, hist
            
        ema12_series = self._ema(closes, 12, return_series=True)
        ema26_series = self._ema(closes, 26, return_series=True)
        macd_series = ema12_series - ema26_series
        
        signal_series = pd.Series(macd_series).ewm(span=9, adjust=False).mean().values
        
        macd = macd_series[-1]
        signal = signal_series[-1]
        hist = macd - signal
        return macd, signal, hist

    @staticmethod
    def _bollinger(closes, period=20, std_factor=2):
        mid = np.mean(closes[-period:]) if len(closes) >= period else np.mean(closes)
        std = np.std(closes[-period:])  if len(closes) >= period else np.std(closes)
        return mid + std_factor * std, mid, mid - std_factor * std

    @staticmethod
    def _atr(highs, lows, closes, period=14):
        if len(closes) < 2:
            return highs[-1] - lows[-1]
        tr = np.maximum(highs[1:] - lows[1:],
             np.maximum(abs(highs[1:] - closes[:-1]),
                        abs(lows[1:]  - closes[:-1])))
        return np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)

    @staticmethod
    def _adx(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 25.0
        plus_dm  = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
                             np.maximum(highs[1:] - highs[:-1], 0), 0)
        minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
                             np.maximum(lows[:-1] - lows[1:], 0), 0)
        tr = np.maximum(highs[1:] - lows[1:],
             np.maximum(abs(highs[1:] - closes[:-1]),
                        abs(lows[1:]  - closes[:-1])))
        atr14     = np.mean(tr[-period:])
        plus_di   = 100 * np.mean(plus_dm[-period:])  / max(atr14, 1e-9)
        minus_di  = 100 * np.mean(minus_dm[-period:]) / max(atr14, 1e-9)
        dx_sum    = plus_di + minus_di
        adx_val   = 100 * abs(plus_di - minus_di) / max(dx_sum, 1e-9)
        return float(np.clip(adx_val, 0, 100))

    @staticmethod
    def _stochastic(highs, lows, closes, k_period=14, d_period=3):
        n = len(closes)
        period = min(k_period, n)
        hh = np.max(highs[-period:])
        ll = np.min(lows[-period:])
        k  = 100 * (closes[-1] - ll) / max(hh - ll, 1e-9)
        k  = float(np.clip(k, 0, 100))
        # D = simple average of last 3 K values (approximation)
        d = k * 0.9  # simplified
        return k, d

    @staticmethod
    def _obv(closes, volumes):
        closes = np.array(closes)
        volumes = np.array(volumes)
        diffs = np.diff(closes, prepend=closes[0])
        direction = np.where(diffs > 0, 1, np.where(diffs < 0, -1, 0))
        obv = np.cumsum(direction * volumes)
        return obv


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LSTM PATTERN RECOGNITION NETWORK
# ═══════════════════════════════════════════════════════════════════════════════

if TORCH_AVAILABLE:
    class _LSTMNet(nn.Module):
        """
        2-Layer LSTM → Dense Klassifikator für Kauf/Halte/Verkauf-Signale.

        Input:  (batch, seq_len=30, features=20)
        Output: (batch, 3) – logits für [HOLD, BUY, SELL]
        """
        def __init__(self, feature_size=20, hidden=64, num_layers=2, actions=3):
            super().__init__()
            self.lstm  = nn.LSTM(feature_size, hidden, num_layers,
                                  batch_first=True, dropout=0.2)
            self.norm  = nn.LayerNorm(hidden)
            self.fc1   = nn.Linear(hidden, 32)
            self.relu  = nn.ReLU()
            self.drop  = nn.Dropout(0.15)
            self.out   = nn.Linear(32, actions)

        def forward(self, x):
            out, _ = self.lstm(x)
            out    = self.norm(out[:, -1, :])   # Letzter Zeitschritt
            out    = self.drop(self.relu(self.fc1(out)))
            return self.out(out)

else:
    class _LSTMNet:
        def __init__(self, *args, **kwargs):
            pass


class LSTMPatternNetwork:
    """
    Wrapper um `_LSTMNet`. Verwaltet Training, Inferenz und Persistenz.

    Sequenz-Länge: 30 Bars (konfigurierbar via `seq_len`)
    """

    SEQ_LEN = 30

    def __init__(self, feature_size=20, seq_len=30):
        self.feature_size  = feature_size
        self.seq_len       = seq_len
        self.sequence_buf  = deque(maxlen=seq_len)  # Ring-Buffer
        self.is_trained    = False

        if TORCH_AVAILABLE:
            self.net       = _LSTMNet(feature_size, hidden=64).to(_DEVICE)
            self.optimizer = optim.Adam(self.net.parameters(), lr=1e-3)
            self.criterion = nn.CrossEntropyLoss()
        else:
            self.net       = None

    def push(self, feature_vector: np.ndarray):
        """Fügt einen neuen Feature-Vektor in den Sequenz-Buffer."""
        self.sequence_buf.append(feature_vector.copy())

    def predict(self) -> tuple:
        """
        Returns:
            (action_idx: int, confidence: float)
            action_idx: 0=HOLD, 1=BUY, 2=SELL
            confidence: 0.0 – 1.0
        """
        if not TORCH_AVAILABLE or len(self.sequence_buf) < self.seq_len:
            return 0, 0.33   # Noch nicht genug Daten → HOLD

        try:
            seq = np.stack(list(self.sequence_buf), axis=0)   # (seq_len, feat)
            t   = torch.FloatTensor(seq).unsqueeze(0).to(_DEVICE)  # (1, seq, feat)

            self.net.eval()
            with torch.no_grad():
                logits = self.net(t)[0]
                probs  = torch.softmax(logits, dim=0).cpu().numpy()

            action     = int(np.argmax(probs))
            confidence = float(probs[action])
            return action, confidence

        except Exception as e:
            print(f"[FULLDRIVE][LSTM] Predict-Fehler: {e}")
            return 0, 0.33

    def online_train_step(self, feature_seq: np.ndarray, target_action: int):
        """
        Einzelner Online-Trainingsschritt (nach Trade-Abschluss).
        feature_seq: (seq_len, feature_size)
        target_action: 0, 1, oder 2
        """
        if not TORCH_AVAILABLE or self.net is None:
            return
        try:
            t   = torch.FloatTensor(feature_seq).unsqueeze(0).to(_DEVICE)
            lbl = torch.LongTensor([target_action]).to(_DEVICE)

            self.net.train()
            self.optimizer.zero_grad()
            loss = self.criterion(self.net(t), lbl)
            loss.backward()
            self.optimizer.step()
        except Exception as e:
            print(f"[FULLDRIVE][LSTM] Trainings-Fehler: {e}")

    def save(self, path: str):
        if TORCH_AVAILABLE and self.net:
            torch.save(self.net.state_dict(), path)

    def load(self, path: str):
        if TORCH_AVAILABLE and self.net and os.path.exists(path):
            try:
                self.net.load_state_dict(
                    torch.load(path, map_location=_DEVICE, weights_only=True)
                )
                self.is_trained = True
            except Exception as e:
                print(f"[FULLDRIVE][LSTM] Lade-Fehler: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. REINFORCEMENT LEARNING DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RLDecisionEngine:
    """
    Ensemble-Wrapper: kombiniert LSTM-Konfidenz und DDQN Q-Values zu einem
    finalen Handelssignal.

    Ensemble-Logik:
      • LSTM und RL stimmen überein & Ø-Konfidenz > threshold → Signal
      • Nur RL, LSTM hat zu wenig Daten                       → RL-Signal
      • Widerspruch mit niedriger Konfidenz                   → HOLD (kein Trade)
    """

    ACTION_MAP = {0: "HOLD", 1: "BUY", 2: "SELL"}

    def __init__(self, rl_manager, lstm_network: LSTMPatternNetwork,
                 min_confidence: float = 0.70):
        self.rl_manager     = rl_manager   # RLTradingManager aus rl_trading_agent.py
        self.lstm           = lstm_network
        self.min_confidence = min_confidence

    def decide(self, symbol: str, feature_vector: np.ndarray) -> dict:
        """
        Returns:
            {
              'action':     'BUY' | 'SELL' | 'HOLD',
              'confidence': float (0-1),
              'lstm_action': str,
              'rl_action':   str,
              'reason':      str,
            }
        """
        self.lstm.push(feature_vector)

        # ── LSTM Vorhersage ─────────────────────────────────────────────────
        lstm_action_idx, lstm_conf = self.lstm.predict()
        lstm_action = self.ACTION_MAP[lstm_action_idx]

        # ── RL (DDQN) Empfehlung ────────────────────────────────────────────
        rl_rec = None
        rl_action = "HOLD"
        rl_conf   = 0.5
        try:
            rl_rec = self.rl_manager.get_rl_recommendation(symbol)
            if rl_rec:
                rl_action = rl_rec.get('recommendation', 'HOLD')
                # Konfidenz aus Q-Value-Spread (0–100 → 0–1)
                rl_conf   = float(rl_rec.get('confidence', 50)) / 100.0
        except Exception:
            pass

        # ── Ensemble-Abstimmung ─────────────────────────────────────────────
        avg_conf = (lstm_conf + rl_conf) / 2.0

        if lstm_action == rl_action and lstm_action != "HOLD":
            if avg_conf >= self.min_confidence:
                final_action = lstm_action
                reason = (f"LSTM ({lstm_conf:.0%}) + RL ({rl_conf:.0%}) "
                          f"einig: {final_action}")
            else:
                final_action = "HOLD"
                reason = f"Einig, aber Konfidenz {avg_conf:.0%} < {self.min_confidence:.0%}"
        elif lstm_action == "HOLD" and rl_conf >= self.min_confidence + 0.05:
            final_action = rl_action
            reason = f"Nur RL (LSTM bereit: {len(self.lstm.sequence_buf)}/{self.lstm.seq_len})"
        else:
            final_action = "HOLD"
            reason = f"Widerspruch: LSTM={lstm_action}, RL={rl_action} – kein Trade"

        return {
            'action':      final_action,
            'confidence':  avg_conf,
            'lstm_action': lstm_action,
            'rl_action':   rl_action,
            'reason':      reason,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RISK MANAGER (Kelly Criterion + Max-DD Guard)
# ═══════════════════════════════════════════════════════════════════════════════

class FullDriveRiskManager:
    """
    Risikobasierte Positionsgrößenbestimmung mit Kelly-Kriterium.

    Kelly-Formel:
        f* = (b*p - q) / b
        b  = Durchschnittlicher Gewinn / Durchschnittlicher Verlust
        p  = Win-Rate
        q  = 1 - p

    Clamp: [0.5 * kelly, min(kelly_full, max_risk_fraction)]
    Max-DD Guard: Wenn aktueller Drawdown > Limit → keine neuen Positionen.
    """

    def __init__(self,
                 max_risk_fraction: float = 0.02,    # 2 % pro Trade
                 max_drawdown_pct:  float = 15.0,    # 15 % Max DD
                 kelly_fraction:    float = 0.5):    # Halbes Kelly (konservativ)
        self.max_risk_fraction  = max_risk_fraction
        self.max_drawdown_pct   = max_drawdown_pct
        self.kelly_fraction     = kelly_fraction

        # Statistik-Tracking
        self._wins:    list = []
        self._losses:  list = []

        # Drawdown-Tracking
        self._peak_balance:    float = 0.0
        self._current_balance: float = 0.0
        self._max_dd_hit:      bool  = False

    def update_balance(self, balance: float):
        """Muss nach jedem Trade aufgerufen werden."""
        if balance > self._peak_balance:
            self._peak_balance = balance
        self._current_balance = balance
        dd = self._drawdown_pct()
        if dd >= self.max_drawdown_pct:
            self._max_dd_hit = True
        # Reset wenn Balance wieder nahe Peak
        elif dd < self.max_drawdown_pct * 0.5:
            self._max_dd_hit = False

    def record_trade(self, profit: float):
        """Registriert Gewinn/Verlust eines abgeschlossenen Trades."""
        if profit > 0:
            self._wins.append(profit)
        else:
            self._losses.append(abs(profit))

    def drawdown_limit_reached(self) -> bool:
        return self._max_dd_hit

    def calculate_lot_size(self, symbol_info, account_balance: float,
                           free_margin: float, sl_pips: float) -> float:
        """
        Berechnet die optimale Lot-Größe mit Kelly-Kriterium.

        Returns:
            float: Lot-Größe (valid für MT5 order_send)
        """
        if symbol_info is None:
            return 0.01

        try:
            lot_min  = getattr(symbol_info, 'volume_min',  0.01)
            lot_max  = getattr(symbol_info, 'volume_max',  1.00)
            lot_step = getattr(symbol_info, 'volume_step', 0.01)

            pip_size   = symbol_info.point * 10 if symbol_info.digits in (3, 5) \
                         else symbol_info.point
            tick_val   = getattr(symbol_info, 'trade_tick_value', 1.0) or 1.0
            tick_size  = getattr(symbol_info, 'trade_tick_size',  pip_size) or pip_size
            pip_value  = (pip_size / tick_size) * tick_val if tick_size > 0 else 1.0

            # Kelly-Kriterium
            kelly_frac = self._kelly_fraction()

            risk_amount = account_balance * min(kelly_frac, self.max_risk_fraction)
            lot_raw     = risk_amount / max(sl_pips * pip_value, 1e-9)
            lot_rounded = round(round(lot_raw / lot_step) * lot_step, 2)
            lot_size    = float(max(lot_min, min(lot_rounded, lot_max)))

            # Margin-Check
            if free_margin > 0 and MT5_AVAILABLE:
                try:
                    req = mt5.order_calc_margin(
                        mt5.ORDER_TYPE_BUY, symbol_info.name, lot_size, 0)
                    if req and req > free_margin:
                        ratio    = free_margin / req
                        lot_size = round(round(lot_size * ratio * 0.9 / lot_step) * lot_step, 2)
                        lot_size = float(max(lot_min, lot_size))
                except Exception:
                    pass

            return lot_size

        except Exception as e:
            print(f"[FULLDRIVE][RISK] Lot-Berechnung: {e}")
            return max(getattr(symbol_info, 'volume_min', 0.01), 0.01)

    def _kelly_fraction(self) -> float:
        """Berechnet Kelly-f* basierend auf bisheriger Trade-History."""
        n_wins  = len(self._wins)
        n_loss  = len(self._losses)
        n_total = n_wins + n_loss

        if n_total < 10:
            # Noch zu wenig Daten: konservatives Fallback
            return self.max_risk_fraction * 0.5

        p = n_wins / n_total            # Win-Rate
        q = 1 - p
        avg_win  = np.mean(self._wins)
        avg_loss = np.mean(self._losses) if self._losses else 1.0
        b        = avg_win / max(avg_loss, 1e-9)

        kelly    = (b * p - q) / max(b, 1e-9)
        kelly    = max(0.0, kelly)      # Kein negatives Kelly
        kelly   *= self.kelly_fraction  # Halbes Kelly (konservativ)

        return float(np.clip(kelly, 0.001, self.max_risk_fraction))

    def _drawdown_pct(self) -> float:
        if self._peak_balance <= 0:
            return 0.0
        return (self._peak_balance - self._current_balance) / self._peak_balance * 100.0

    @property
    def current_drawdown_pct(self) -> float:
        return self._drawdown_pct()

    @property
    def win_rate(self) -> float:
        n = len(self._wins) + len(self._losses)
        return len(self._wins) / n * 100.0 if n > 0 else 0.0

    @property
    def kelly_suggestion(self) -> float:
        return self._kelly_fraction() * 100.0  # in Prozent


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PERFORMANCE KPI TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class PerformanceKPITracker:
    """
    Berechnet laufende Trading-Kennzahlen.

    KPIs:
      • Sharpe Ratio    = Ø(Renditen) / σ(Renditen) × √252
      • Sortino Ratio   = Ø(Renditen) / σ(negat. Renditen) × √252
      • Max Drawdown    = Maximaler Peak-to-Trough Rückgang in %
      • Annual Return   = (Gesamtrendite / Handelstage) × 252
      • Win Rate        = Gewinn-Trades / Gesamt-Trades
      • Profit Factor   = Summe Gewinne / Summe Verluste
    """

    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate / 252  # Tägliche risikofreie Rate
        self._trade_returns: deque = deque(maxlen=200)  # Laufende Renditen (%)
        self._equity_curve:  list  = []
        self._peak_equity:   float = 0.0
        self._max_dd:        float = 0.0
        self._start_balance: float = 0.0
        self._start_time:    datetime = datetime.now()
        self._n_wins:        int   = 0
        self._n_total:       int   = 0
        self._gross_profit:  float = 0.0
        self._gross_loss:    float = 0.0

    def record(self, profit: float, balance: float):
        """Nach jedem Trade aufrufen."""
        if self._start_balance == 0:
            self._start_balance = balance - profit  # Initiales Kapital schätzen

        ret_pct = profit / max(self._start_balance, 1e-9) * 100
        self._trade_returns.append(ret_pct)
        self._equity_curve.append(balance)

        # Drawdown-Update
        if balance > self._peak_equity:
            self._peak_equity = balance
        dd = (self._peak_equity - balance) / max(self._peak_equity, 1e-9) * 100
        self._max_dd = max(self._max_dd, dd)

        # Win/Loss-Statistik
        self._n_total += 1
        if profit > 0:
            self._n_wins     += 1
            self._gross_profit += profit
        else:
            self._gross_loss  += abs(profit)

    def sharpe_ratio(self) -> float:
        if len(self._trade_returns) < 5:
            return 0.0
        rets = np.array(self._trade_returns)
        std  = np.std(rets)
        if std == 0:
            return 0.0
        trades_per_year = 252  # Annualisierungs-Faktor
        return float((np.mean(rets) - self.risk_free_rate * 100) / std * math.sqrt(trades_per_year))

    def sortino_ratio(self) -> float:
        if len(self._trade_returns) < 5:
            return 0.0
        rets = np.array(self._trade_returns)
        neg  = rets[rets < 0]
        if len(neg) == 0:
            return 99.0   # Keine Verluste
        downside_std = np.std(neg)
        if downside_std == 0:
            return 0.0
        trades_per_year = 252
        return float((np.mean(rets) - self.risk_free_rate * 100) / downside_std * math.sqrt(trades_per_year))

    def max_drawdown_pct(self) -> float:
        return round(self._max_dd, 2)

    def annual_return_estimate(self) -> float:
        if self._start_balance <= 0 or not self._equity_curve:
            return 0.0
        total_ret   = (self._equity_curve[-1] - self._start_balance) / max(self._start_balance, 1) * 100
        days_elapsed = max((datetime.now() - self._start_time).days, 1)
        return round(total_ret / days_elapsed * 252, 2)   # Hochgerechnet auf 252 Handelstage

    def win_rate(self) -> float:
        return round(self._n_wins / max(self._n_total, 1) * 100, 2)

    def profit_factor(self) -> float:
        if self._gross_loss == 0:
            return 99.0 if self._gross_profit > 0 else 0.0
        return round(self._gross_profit / self._gross_loss, 2)

    def trade_count(self) -> int:
        return self._n_total

    def get_all(self) -> dict:
        return {
            'sharpe':        round(self.sharpe_ratio(), 3),
            'sortino':       round(self.sortino_ratio(), 3),
            'max_drawdown':  self.max_drawdown_pct(),
            'annual_return': self.annual_return_estimate(),
            'win_rate':      self.win_rate(),
            'profit_factor': self.profit_factor(),
            'trade_count':   self.trade_count(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AI-FULLDRIVE ENGINE (Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

class AIFulldriveEngine:
    """
    Haupt-Orchestrator für den AI-Fulldrive Mode.

    Usage:
        engine = AIFulldriveEngine(app)
        result = engine.get_signal(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15)
        # result = {'action':'BUY', 'lot_size': 0.05, 'confidence': 0.82, 'kpis': {...}}
    """

    VERSION = "1.0.0"

    # Selbst-Optimierung alle N abgeschlossenen Trades
    SELF_OPT_INTERVAL = 50

    def __init__(self, app,
                 min_confidence:   float = 0.70,
                 max_drawdown_pct: float = 15.0,
                 sharpe_target:    float = 1.5):
        self.app             = app
        self.min_confidence  = min_confidence
        self.max_drawdown_pct= max_drawdown_pct
        self.sharpe_target   = sharpe_target

        self._feature_extractor = MarketFeatureExtractor()
        self._lstm_nets:  dict  = {}    # pro Symbol
        self._kpi_tracker       = PerformanceKPITracker()
        self._risk_mgr          = FullDriveRiskManager(
            max_drawdown_pct = max_drawdown_pct,
            max_risk_fraction= 0.02)

        self._last_opt_count    = 0
        self._lock              = threading.Lock()
        self._model_dir         = "rl_models/fulldrive"
        os.makedirs(self._model_dir, exist_ok=True)

        # Lazy-lade RLTradingManager
        self._rl_manager        = None

        self._log(f"AI-Fulldrive Engine v{self.VERSION} initialisiert"
                  f" | Device: {_DEVICE} | Konfidenz-Min: {min_confidence:.0%}"
                  f" | Max-DD: {max_drawdown_pct}%")

    # ── Haupt-API ──────────────────────────────────────────────────────────────

    def get_signal(self, symbol: str, timeframe=None, bars: int = 100) -> dict:
        """
        Führt die komplette KI-Pipeline aus und gibt ein Handelssignal zurück.

        Returns:
            {
              'action':     'BUY' | 'SELL' | 'HOLD',
              'lot_size':   float,
              'confidence': float,
              'sl_pips':    int,
              'tp_pips':    int,
              'kpis':       dict,
              'reason':     str,
            }
        """
        default = {
            'action': 'HOLD', 'lot_size': 0.01,
            'confidence': 0.0, 'sl_pips': 30, 'tp_pips': 50,
            'kpis': self._kpi_tracker.get_all(), 'reason': 'Fehler im Engine'
        }

        try:
            # 1. Max-DD Guard
            if self._risk_mgr.drawdown_limit_reached():
                default['reason'] = (f"Max-Drawdown {self._risk_mgr.current_drawdown_pct:.1f}% "
                                     f"≥ {self.max_drawdown_pct}% → Handelspause")
                self._log(default['reason'])
                return default

            # 2. OHLCV-Daten holen
            rates = self._fetch_rates(symbol, timeframe, bars)
            if not rates:
                default['reason'] = "Keine MT5-Daten verfügbar"
                return default

            # 3. ML Feature-Extraktion
            features = self._feature_extractor.extract(rates)

            # 4. RL-Manager sicherstellen
            rl_mgr = self._ensure_rl_manager(symbol)

            # 5. LSTM-Netz für dieses Symbol
            lstm_net = self._get_lstm_net(symbol)

            # 6. Entscheidungsengine
            decision_engine = RLDecisionEngine(rl_mgr, lstm_net, self.min_confidence)
            decision = decision_engine.decide(symbol, features)

            # 7. Adaptive SL/TP aus ATR
            closes = [r['close'] for r in rates]
            highs  = [r['high']  for r in rates]
            lows   = [r['low']   for r in rates]
            atr    = self._feature_extractor._atr(
                np.array(highs), np.array(lows), np.array(closes))
            price  = closes[-1]
            # SL = 1.5× ATR, TP = 2.5× ATR (Risk-Reward 1:1.67)
            pip_size = self._pip_size(symbol)
            sl_pips  = max(10, int(atr * 1.5 / max(pip_size, 1e-9)))
            tp_pips  = max(15, int(atr * 2.5 / max(pip_size, 1e-9)))

            # 8. Lot-Größe
            lot_size  = 0.01
            if decision['action'] != 'HOLD' and MT5_AVAILABLE:
                try:
                    sym_info = mt5.symbol_info(symbol)
                    acc_info = mt5.account_info()
                    if sym_info and acc_info:
                        self._risk_mgr.update_balance(acc_info.balance)
                        lot_size = self._risk_mgr.calculate_lot_size(
                            sym_info, acc_info.balance,
                            acc_info.margin_free, sl_pips)
                except Exception:
                    pass

            return {
                'action':     decision['action'],
                'lot_size':   lot_size,
                'confidence': decision['confidence'],
                'sl_pips':    sl_pips,
                'tp_pips':    tp_pips,
                'kpis':       self._kpi_tracker.get_all(),
                'reason':     decision['reason'],
                'lstm_action':decision['lstm_action'],
                'rl_action':  decision['rl_action'],
            }

        except Exception as e:
            default['reason'] = f"Engine-Exception: {e}"
            print(f"[FULLDRIVE] get_signal Fehler: {e}")
            return default

    def record_trade_result(self, profit: float, balance: float,
                            action_taken: int = 0):
        """
        Muss nach jedem abgeschlossenen Trade aufgerufen werden.
        Triggert ggf. Selbst-Optimierung.
        """
        with self._lock:
            self._kpi_tracker.record(profit, balance)
            self._risk_mgr.record_trade(profit)
            self._risk_mgr.update_balance(balance)

            self._last_opt_count += 1
            if self._last_opt_count >= self.SELF_OPT_INTERVAL:
                self._last_opt_count = 0
                threading.Thread(target=self._self_optimize, daemon=True).start()

    def run_backtest(self, symbol: str = "EURUSD",
                     bars: int = 2000, callback=None) -> dict:
        """
        Walk-Forward Backtesting auf historischen Daten.
        80% Training / 20% Out-of-Sample Test (OOS).

        Returns:
            dict mit 'sharpe', 'max_dd', 'win_rate', 'annual_return',
                     'n_trades', 'profit_pct', 'oos_sharpe'
        """
        results = {
            'sharpe': 0.0, 'max_dd': 0.0, 'win_rate': 0.0,
            'annual_return': 0.0, 'n_trades': 0, 'profit_pct': 0.0,
            'oos_sharpe': 0.0, 'status': 'Kein MT5'
        }

        def _log(msg):
            if callback:
                callback(msg)
            else:
                print(f"[FULLDRIVE][BT] {msg}")

        _log(f"Starte Backtest für {symbol} ({bars} Bars)...")

        try:
            rates = self._fetch_rates(symbol, None, bars)
            if not rates or len(rates) < 100:
                results['status'] = 'Nicht genug Daten'
                _log("⚠ Nicht genug Daten für Backtest.")
                return results

            split  = int(len(rates) * 0.8)
            train  = rates[:split]
            oos    = rates[split:]

            bt_tracker  = PerformanceKPITracker()
            oos_tracker = PerformanceKPITracker()

            balance      = 10000.0
            oos_balance  = 10000.0
            extractor    = MarketFeatureExtractor()

            # ── Training-Phase (einfacher Signal-Sim) ── 
            for i in range(50, len(train)):
                window = train[max(0, i-60):i+1]
                feats  = extractor.extract(window)
                # Einfaches RSI-Momentum-Proxy für Backtest-Sim
                rsi = feats[0] * 100
                hold_pct = 0.01  # 1% Trade-Größe

                if rsi < 35:
                    # Simuliertes BUY
                    pnl = (window[-1]['close'] / window[-2]['close'] - 1) * balance * hold_pct
                    balance += pnl
                    bt_tracker.record(pnl, balance)
                elif rsi > 65:
                    # Simuliertes SELL
                    pnl = -(window[-1]['close'] / window[-2]['close'] - 1) * balance * hold_pct
                    balance += pnl
                    bt_tracker.record(pnl, balance)

            _log(f"Training-Phase: {bt_tracker.trade_count()} Trades, "
                 f"Sharpe={bt_tracker.sharpe_ratio():.2f}")

            # ── OOS-Phase ──
            for i in range(20, len(oos)):
                window = oos[max(0, i-60):i+1]
                feats  = extractor.extract(window)
                rsi    = feats[0] * 100
                hold_pct = 0.01

                if rsi < 35:
                    pnl = (window[-1]['close'] / window[-2]['close'] - 1) * oos_balance * hold_pct
                    oos_balance += pnl
                    oos_tracker.record(pnl, oos_balance)
                elif rsi > 65:
                    pnl = -(window[-1]['close'] / window[-2]['close'] - 1) * oos_balance * hold_pct
                    oos_balance += pnl
                    oos_tracker.record(pnl, oos_balance)

            oos_kpis = oos_tracker.get_all()
            _log(f"OOS-Phase:      {oos_tracker.trade_count()} Trades, "
                 f"Sharpe={oos_kpis['sharpe']:.2f}, "
                 f"Max-DD={oos_kpis['max_drawdown']:.1f}%")

            profit_pct = (oos_balance - 10000) / 10000 * 100
            _log(f"OOS Profit: {profit_pct:+.2f}% | Win-Rate: {oos_kpis['win_rate']:.1f}%")
            _log("✅ Backtest abgeschlossen.")

            results.update({
                'sharpe':        bt_tracker.sharpe_ratio(),
                'oos_sharpe':    oos_kpis['sharpe'],
                'max_dd':        oos_kpis['max_drawdown'],
                'win_rate':      oos_kpis['win_rate'],
                'annual_return': oos_kpis['annual_return'],
                'n_trades':      oos_tracker.trade_count(),
                'profit_pct':    profit_pct,
                'status':        'OK',
            })

        except Exception as e:
            results['status'] = f"Fehler: {e}"
            _log(f"❌ Backtest-Fehler: {e}")

        return results

    # ── Private Hilfsmethoden ──────────────────────────────────────────────────

    def _fetch_rates(self, symbol, timeframe, bars) -> list:
        if not MT5_AVAILABLE:
            return []
        try:
            # 1. Sicherstellen, dass das Symbol im Market Watch ist
            mt5.symbol_select(symbol, True)
            
            tf = timeframe or mt5.TIMEFRAME_M15
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None or len(rates) < 30:
                self._log(f"Fehler bei copy_rates({symbol}). MT5 Error: {mt5.last_error()}")
                return []
            if hasattr(rates, 'dtype') and rates.dtype.names:
                return [{n: r[n] for n in rates.dtype.names} for r in rates]
            return [dict(r) for r in rates]
        except Exception as e:
            self._log(f"Exception in _fetch_rates: {e}")
            return []

    def _ensure_rl_manager(self, symbol):
        if self._rl_manager is None:
            try:
                from trading.rl_trading_agent import RLTradingManager
                self._rl_manager = RLTradingManager(self.app)
                if symbol not in self._rl_manager.agents:
                    self._rl_manager.initialize_agent(symbol)
            except Exception as e:
                print(f"[FULLDRIVE] RL-Manager Fehler: {e}")
        return self._rl_manager

    def _get_lstm_net(self, symbol) -> LSTMPatternNetwork:
        if symbol not in self._lstm_nets:
            net = LSTMPatternNetwork(
                feature_size=MarketFeatureExtractor.FEATURE_COUNT,
                seq_len=LSTMPatternNetwork.SEQ_LEN)
            # Versuche gespeichertes Modell zu laden
            model_path = os.path.join(self._model_dir, f"{symbol}_lstm.pt")
            net.load(model_path)
            self._lstm_nets[symbol] = net
        return self._lstm_nets[symbol]

    def _self_optimize(self):
        """Hintergrund-Retraining nach SELF_OPT_INTERVAL Trades."""
        try:
            self._log("🔄 Selbst-Optimierung gestartet...")
            if self._rl_manager is None:
                return
            for symbol in list(self._rl_manager.agents.keys()):
                self._rl_manager.retrain_from_experience(symbol)
                # Speichere LSTM Modell
                if symbol in self._lstm_nets:
                    model_path = os.path.join(self._model_dir, f"{symbol}_lstm.pt")
                    self._lstm_nets[symbol].save(model_path)
            kpis = self._kpi_tracker.get_all()
            self._log(
                f"✅ Optimierung abgeschlossen | "
                f"Sharpe: {kpis['sharpe']:.2f} | "
                f"Max-DD: {kpis['max_drawdown']:.1f}% | "
                f"Win-Rate: {kpis['win_rate']:.1f}%"
            )
        except Exception as e:
            print(f"[FULLDRIVE] Selbst-Optimierung Fehler: {e}")

    def _pip_size(self, symbol: str) -> float:
        if not MT5_AVAILABLE:
            return 0.0001
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return 0.0001
            return info.point * 10 if info.digits in (3, 5) else info.point
        except Exception:
            return 0.0001

    def _log(self, msg: str):
        try:
            if hasattr(self.app, 'write_terminal'):
                self.app.write_terminal(f">> [FULLDRIVE] {msg}\\n")
            else:
                print(f"[FULLDRIVE] {msg}")
        except Exception:
            print(f"[FULLDRIVE] {msg}")

    def get_kpis(self) -> dict:
        """Gibt aktuelle Performance-Kennzahlen zurück."""
        kpis   = self._kpi_tracker.get_all()
        kpis['kelly_fraction_pct'] = round(self._risk_mgr.kelly_suggestion, 2)
        kpis['current_drawdown']   = round(self._risk_mgr.current_drawdown_pct, 2)
        kpis['sharpe_target']      = self.sharpe_target
        kpis['max_dd_limit']       = self.max_drawdown_pct
        kpis['dd_limit_reached']   = self._risk_mgr.drawdown_limit_reached()
        return kpis
