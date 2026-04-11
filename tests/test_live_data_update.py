import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
import customtkinter as ctk
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Mock MetaTrader5 before importing our modules
mock_mt5 = MagicMock()
sys.modules['MetaTrader5'] = mock_mt5

from gui.components.live_data_row import LiveDataRow

class TestLiveDataRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a root window but don't show it
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.row = LiveDataRow(
            master=self.root,
            symbol="EUR/USD",
            price="1.1000",
            change="+0.1%",
            signal="WAIT"
        )
        # Mock the configure method of the signal_btn to track calls
        self.row.signal_btn.configure = MagicMock()
        
    def test_update_trend_all_green_returns_buy(self):
        # All green dots should result in BUY signal
        self.row.update_trend("#10B981", "#10B981", "#10B981")
        self.row.signal_btn.configure.assert_called_with(
            text="BUY",
            fg_color="#10B981",
            hover_color="#00E676",
            text_color="#09090B",
        )

    def test_update_trend_all_red_returns_sell(self):
        # All red dots should result in SELL signal
        self.row.update_trend("#EF4444", "#EF4444", "#EF4444")
        self.row.signal_btn.configure.assert_called_with(
            text="SELL",
            fg_color="#EF4444",
            hover_color="#D50000",
            text_color="#09090B",
        )

    def test_update_trend_mixed_colors_returns_wait(self):
        # Mixed colors should result in WAIT signal
        self.row.update_trend("#10B981", "gray", "#EF4444")
        self.row.signal_btn.configure.assert_called_with(
            text="WAIT",
            fg_color="#FFEA00",
            hover_color="#FFD600",
            text_color="#09090B",
        )

class TestDashboardDataUpdate(unittest.TestCase):
    @patch('gui.modern_fingpt_gui.mt5')
    def test_network_timeout_tick_none(self, mock_mt5_module):
        """Test API timeout where symbol_info_tick returns None"""
        app = MagicMock()
        app.live_data_rows = [("EURUSD", MagicMock())]
        app._last_dashboard_history_update = 0
        
        mock_acc_info = MagicMock()
        mock_acc_info.balance = 10000.0
        mock_acc_info.equity = 10000.0
        mock_acc_info.margin = 0.0
        mock_acc_info.margin_free = 10000.0
        mock_acc_info.margin_level = 0.0
        mock_acc_info.profit = 0.0
        mock_mt5_module.account_info.return_value = mock_acc_info
        
        # Simulate network timeout
        mock_mt5_module.symbol_info_tick.return_value = None
        
        try:
            from gui.modern_fingpt_gui import ModernFinGPTGUI
            ModernFinGPTGUI._update_mvp_trade(app)
            
            # Ensure update_data was never called since tick is None
            app.live_data_rows[0][1].update_data.assert_not_called()
        except Exception as e:
            self.fail(f"_update_mvp_trade raised exception on network timeout: {e}")

    @patch('gui.modern_fingpt_gui.mt5')
    def test_api_delay_copy_rates_fails(self, mock_mt5_module):
        """Test API delay/failure where history data fetching fails but tick succeeds"""
        app = MagicMock()
        app.live_data_rows = [("EURUSD", MagicMock())]
        app._last_dashboard_history_update = 0
        app._dashboard_history_cache = {}
        app._last_dashboard_history_update = 0
        
        mock_acc_info = MagicMock()
        mock_acc_info.balance = 10000.0
        mock_acc_info.equity = 10000.0
        mock_acc_info.margin = 0.0
        mock_acc_info.margin_free = 10000.0
        mock_acc_info.margin_level = 0.0
        mock_acc_info.profit = 0.0
        mock_mt5_module.account_info.return_value = mock_acc_info

        mock_tick = MagicMock()
        mock_tick.bid = 1.1050
        mock_mt5_module.symbol_info_tick.return_value = mock_tick
        
        # Simulate API delay/error on historical data
        mock_mt5_module.copy_rates_from_pos.return_value = None
        
        try:
            from gui.modern_fingpt_gui import ModernFinGPTGUI
            ModernFinGPTGUI._update_mvp_trade(app)
            
            row_mock = app.live_data_rows[0][1]
            row_mock.update_data.assert_called_with("1.10500", "0.00%", history=[])
            row_mock.update_trend.assert_called_with("gray", "gray", "gray")
        except Exception as e:
            self.fail(f"_update_mvp_trade raised exception on API delay: {e}")

    @patch('gui.modern_fingpt_gui.mt5')
    def test_successful_data_transmission(self, mock_mt5_module):
        """Test successful data update yielding correct trend colors"""
        app = MagicMock()
        app.live_data_rows = [("EURUSD", MagicMock())]
        app._last_dashboard_history_update = 0
        app._dashboard_history_cache = {}
        app._last_dashboard_history_update = 0
        
        mock_acc_info = MagicMock()
        mock_acc_info.balance = 10000.0
        mock_acc_info.equity = 10000.0
        mock_acc_info.margin = 0.0
        mock_acc_info.margin_free = 10000.0
        mock_acc_info.margin_level = 0.0
        mock_acc_info.profit = 0.0
        mock_mt5_module.account_info.return_value = mock_acc_info

        mock_tick = MagicMock()
        mock_tick.bid = 1.1050
        mock_mt5_module.symbol_info_tick.return_value = mock_tick
        
        def mock_copy_rates(sym, tf, start, count):
            if tf == mock_mt5_module.TIMEFRAME_D1:
                return [{"open": 1.1000}]
            elif tf == mock_mt5_module.TIMEFRAME_M15:
                return [{"close": 1.1000}, {"close": 1.1050}]
            elif tf == mock_mt5_module.TIMEFRAME_H1:
                return [{"close": 1.1050}, {"close": 1.1000}]
            elif tf == mock_mt5_module.TIMEFRAME_H4:
                return [{"close": 1.1000}, {"close": 1.1000}]
            elif tf == mock_mt5_module.TIMEFRAME_M1:
                return [{"close": 1.1000}, {"close": 1.1050}]
            return None

        mock_mt5_module.copy_rates_from_pos.side_effect = mock_copy_rates
        
        try:
            from gui.modern_fingpt_gui import ModernFinGPTGUI
            ModernFinGPTGUI._update_mvp_trade(app)
            
            row_mock = app.live_data_rows[0][1]
            
            # Price changed from 1.1000 to 1.1050 -> +0.45%
            change_pct = ((1.1050 - 1.1000) / 1.1000) * 100
            expected_change = f"+{change_pct:.2f}%"
            
            row_mock.update_data.assert_called_with("1.10500", expected_change, history=[1.1000, 1.1050])
            row_mock.update_trend.assert_called_with("#10B981", "#EF4444", "gray")
        except Exception as e:
            self.fail(f"_update_mvp_trade raised exception on successful transmission: {e}")

if __name__ == '__main__':
    unittest.main()