#!/usr/bin/env python3
"""
Unit Tests – AI-Fulldrive Engine
=================================
Testet alle Kernkomponenten ohne MT5 oder GPU.
"""

import sys
import os
import math
import unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────
# 1. MarketFeatureExtractor
# ─────────────────────────────────────────────────────────────

class TestMarketFeatureExtractor(unittest.TestCase):

    def _make_rates(self, n=60):
        """Synthetische OHLCV-Bars (leicht ansteigend)."""
        rates = []
        base = 1.1000
        for i in range(n):
            price = base + i * 0.0001 + (np.random.random() - 0.5) * 0.0002
            rates.append({
                'open':        price - 0.0001,
                'high':        price + 0.0003,
                'low':         price - 0.0002,
                'close':       price,
                'tick_volume': int(1000 + np.random.random() * 500),
            })
        return rates

    def test_feature_shape(self):
        from trading.ai_fulldrive_engine import MarketFeatureExtractor
        ext = MarketFeatureExtractor()
        rates = self._make_rates(60)
        feats = ext.extract(rates)
        self.assertEqual(feats.shape, (MarketFeatureExtractor.FEATURE_COUNT,),
                         "Feature-Vektor muss FEATURE_COUNT Elemente haben")

    def test_feature_dtype(self):
        from trading.ai_fulldrive_engine import MarketFeatureExtractor
        ext = MarketFeatureExtractor()
        feats = ext.extract(self._make_rates(60))
        self.assertEqual(feats.dtype, np.float32, "Features müssen float32 sein")

    def test_feature_range(self):
        """Die meisten Features bleiben im Bereich [-3, 3] (tanh-skaliert)."""
        from trading.ai_fulldrive_engine import MarketFeatureExtractor
        ext = MarketFeatureExtractor()
        for _ in range(5):
            feats = ext.extract(self._make_rates(80))
            self.assertFalse(np.any(np.isnan(feats)), "Keine NaN-Werte im Feature-Vektor")

    def test_few_bars_still_returns(self):
        """Auch mit < 30 Bars sollte kein Fehler auftreten."""
        from trading.ai_fulldrive_engine import MarketFeatureExtractor
        ext = MarketFeatureExtractor()
        rates = self._make_rates(15)
        feats = ext.extract(rates)
        self.assertEqual(len(feats), MarketFeatureExtractor.FEATURE_COUNT)


# ─────────────────────────────────────────────────────────────
# 2. FullDriveRiskManager
# ─────────────────────────────────────────────────────────────

class TestFullDriveRiskManager(unittest.TestCase):

    def _mock_symbol_info(self, min_vol=0.01, max_vol=10.0, step=0.01, digits=5):
        class _Info:
            volume_min      = min_vol
            volume_max      = max_vol
            volume_step     = step
            point           = 0.00001
            self_digits     = digits
            trade_tick_value  = 10.0
            trade_tick_size   = 0.00001
            name            = "EURUSD"
        obj = _Info()
        obj.digits = digits        # regular attribute
        return obj

    def test_kelly_fallback_few_trades(self):
        """Mit < 10 Trades gibt es konservatives Fallback."""
        from trading.ai_fulldrive_engine import FullDriveRiskManager
        rm = FullDriveRiskManager(max_risk_fraction=0.02)
        # Nur 5 Trades – Fallback: max_risk * 0.5
        for i in range(5):
            rm.record_trade(10.0 if i % 2 == 0 else -8.0)
        kelly = rm._kelly_fraction()
        self.assertAlmostEqual(kelly, 0.02 * 0.5, places=4,
                               msg="Fallback-Kelly sollte 50% von max_risk sein")

    def test_kelly_clamp_bounds(self):
        """Kelly-Ergebnis bleibt im [0.001, max_risk] Bereich."""
        from trading.ai_fulldrive_engine import FullDriveRiskManager
        rm = FullDriveRiskManager(max_risk_fraction=0.03)
        # 20 Gewinntrades, 10 Verlusttrades → hohe Win-Rate
        for _ in range(20):
            rm.record_trade(50.0)
        for _ in range(10):
            rm.record_trade(-20.0)
        kelly = rm._kelly_fraction()
        self.assertGreaterEqual(kelly, 0.001)
        self.assertLessEqual(kelly, 0.03)

    def test_max_dd_guard(self):
        """Drawdown-Guard triggert wenn Balance 20% unter Peak fällt."""
        from trading.ai_fulldrive_engine import FullDriveRiskManager
        rm = FullDriveRiskManager(max_drawdown_pct=15.0)
        rm.update_balance(10000)
        rm.update_balance(9800)
        self.assertFalse(rm.drawdown_limit_reached())  # nur 2%
        rm.update_balance(8400)
        self.assertTrue(rm.drawdown_limit_reached(),
                        "DD-Guard muss bei 16% Verlust greifen")

    def test_lot_calculation_no_mt5(self):
        """Lot-Berechnung ohne MT5 gibt volume_min zurück."""
        from trading.ai_fulldrive_engine import FullDriveRiskManager
        rm = FullDriveRiskManager()
        sym_info = self._mock_symbol_info()
        lot = rm.calculate_lot_size(sym_info, account_balance=10000,
                                    free_margin=5000, sl_pips=25)
        self.assertGreaterEqual(lot, sym_info.volume_min)
        self.assertLessEqual(lot, sym_info.volume_max)


# ─────────────────────────────────────────────────────────────
# 3. PerformanceKPITracker
# ─────────────────────────────────────────────────────────────

class TestPerformanceKPITracker(unittest.TestCase):

    def _fill_tracker(self, wins=15, losses=5):
        from trading.ai_fulldrive_engine import PerformanceKPITracker
        tracker = PerformanceKPITracker()
        balance = 10000.0
        for _ in range(wins):
            pnl = 50.0
            balance += pnl
            tracker.record(pnl, balance)
        for _ in range(losses):
            pnl = -30.0
            balance += pnl
            tracker.record(pnl, balance)
        return tracker

    def test_sharpe_returns_float(self):
        t = self._fill_tracker()
        sharpe = t.sharpe_ratio()
        self.assertIsInstance(sharpe, float, "Sharpe muss ein float sein")

    def test_win_rate_calculation(self):
        t = self._fill_tracker(wins=15, losses=5)
        self.assertAlmostEqual(t.win_rate(), 75.0, places=1)

    def test_max_dd_non_negative(self):
        t = self._fill_tracker(wins=5, losses=15)   # verlustreich
        self.assertGreaterEqual(t.max_drawdown_pct(), 0.0)

    def test_profit_factor_positive(self):
        t = self._fill_tracker(wins=20, losses=5)
        self.assertGreater(t.profit_factor(), 1.0)

    def test_all_returns_dict(self):
        t = self._fill_tracker()
        result = t.get_all()
        self.assertIsInstance(result, dict)
        required_keys = {'sharpe', 'sortino', 'max_drawdown',
                         'annual_return', 'win_rate', 'profit_factor', 'trade_count'}
        self.assertTrue(required_keys.issubset(set(result.keys())))

    def test_empty_tracker_no_crash(self):
        from trading.ai_fulldrive_engine import PerformanceKPITracker
        t = PerformanceKPITracker()
        kpis = t.get_all()
        self.assertEqual(kpis['trade_count'], 0)
        self.assertEqual(kpis['sharpe'], 0.0)


# ─────────────────────────────────────────────────────────────
# 4. LSTMPatternNetwork (ohne GPU)
# ─────────────────────────────────────────────────────────────

class TestLSTMPatternNetwork(unittest.TestCase):

    def test_predict_returns_tuple(self):
        from trading.ai_fulldrive_engine import LSTMPatternNetwork, MarketFeatureExtractor
        net = LSTMPatternNetwork(feature_size=MarketFeatureExtractor.FEATURE_COUNT)
        # Buffer noch leer → HOLD mit 33% Konfidenz
        action, conf = net.predict()
        self.assertEqual(action, 0)
        self.assertAlmostEqual(conf, 0.33, places=2)

    def test_push_fills_buffer(self):
        from trading.ai_fulldrive_engine import LSTMPatternNetwork, MarketFeatureExtractor
        net = LSTMPatternNetwork(feature_size=MarketFeatureExtractor.FEATURE_COUNT,
                                 seq_len=10)
        for _ in range(10):
            v = np.random.randn(MarketFeatureExtractor.FEATURE_COUNT).astype(np.float32)
            net.push(v)
        self.assertEqual(len(net.sequence_buf), 10)

    def test_full_sequence_gives_valid_action(self):
        from trading.ai_fulldrive_engine import (LSTMPatternNetwork,
                                                   MarketFeatureExtractor,
                                                   TORCH_AVAILABLE)
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch nicht verfügbar – LSTM Test übersprungen")
        net = LSTMPatternNetwork(feature_size=MarketFeatureExtractor.FEATURE_COUNT,
                                 seq_len=10)
        for _ in range(10):
            net.push(np.random.randn(MarketFeatureExtractor.FEATURE_COUNT).astype(np.float32))
        action, conf = net.predict()
        self.assertIn(action, [0, 1, 2], "Action muss 0, 1 oder 2 sein")
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
