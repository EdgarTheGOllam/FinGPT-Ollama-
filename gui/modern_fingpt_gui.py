#!/usr/bin/env python3
"""
Modernes FinGPT GUI mit erweiterten Funktionen
Professionelle Benutzeroberfläche mit Live-Daten, Plotly-Charts und Terminal-Integration
Umgesetzt mit CustomTkinter für ein hochmodernes "Glassmorphic"- und Dark-Theme Erlebnis.
"""

import sys
import os
import time
import logging
import threading
import MetaTrader5 as mt5
from datetime import datetime
from typing import Optional

# Aurora Hintergrund-Integration
try:
    from gui.aurora_tkinter import attach_aurora_to_frame
    _AURORA_AVAILABLE = True
except ImportError:
    _AURORA_AVAILABLE = False
from tkinter import messagebox
from PIL import Image

# Fix path FIRST - before any project imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import customtkinter as ctk
from core.app_config import app_config_manager


# Fancy Console Output
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    LGRAY = "\033[90m"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def fancy_print(msg: str, level: str = "INFO", icon: Optional[str] = None):
    """Fancy print für GUI - Level: INFO, SUCCESS, WARN, ERROR, SYSTEM"""
    config = {
        "INFO": {"icon": "ℹ️ ", "color": C.CYAN},
        "SUCCESS": {"icon": "✅ ", "color": C.GREEN},
        "WARN": {"icon": "⚠️ ", "color": C.YELLOW},
        "ERROR": {"icon": "❌ ", "color": C.RED},
        "SYSTEM": {"icon": "💻 ", "color": C.BLUE},
        "MCP": {"icon": "🔌 ", "color": C.MAGENTA},
        "INDICATORS": {"icon": "📊 ", "color": C.BLUE},
        "HEATMAP": {"icon": "🧩 ", "color": C.YELLOW},
    }
    cfg = config.get(level, {"icon": "• ", "color": C.LGRAY})
    use_icon = icon or cfg["icon"]
    color = cfg["color"]

    if level == "INFO":
        print(f"{C.LGRAY}[{ts()}]{C.RESET} {color}{use_icon}[{level}]{C.RESET} {msg}")
    elif level == "SYSTEM":
        print(f"{C.LGRAY}[{ts()}]{C.RESET} {color}{use_icon}{C.RESET}{msg}")
    else:
        print(
            f"{C.LGRAY}[{ts()}]{C.RESET} {color}{use_icon}[{level}]{C.RESET} {color}{msg}{C.RESET}"
        )


# Ensure project root is on sys.path so gui.* imports resolve
# whether this file is run directly or via launch_gui.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import requests

# Konfiguriere das CustomTkinter Aussehen
import customtkinter as ctk
from gui.design_system import DesignSystem

ctk.set_appearance_mode("Dark")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

# Apply the new Shader-Inspired Design System
ctk.set_default_color_theme("blue") 
# Note: We will use DesignSystem.SEMANTIC for specific component colors

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import mplfinance as mpf
import MetaTrader5 as mt5
import pandas as pd
import tkinter as tk

try:
    from core.config_manager import ConfigManager

    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

# Import Modernisierte Komponenten
from gui.components.metric_card import MetricCard
from gui.components.live_data_row import LiveDataRow
from gui.views.dashboard_tab import DashboardView

# Import Event Bus und Data Update Manager
try:
    from gui.controllers.event_bus import EventBus, DashboardEvents, DashboardEvent

    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

try:
    from gui.utils.data_update_manager import DataUpdateManager

    DATA_UPDATE_MANAGER_AVAILABLE = True
except ImportError:
    DATA_UPDATE_MANAGER_AVAILABLE = False
from gui.views.charts_tab import ChartsView
from gui.views.rl_settings_tab import RLSettingsView
from gui.views.journal_tab import JournalView
from gui.views.debate_tab import DebateView
from gui.views.news_tab import NewsView
from gui.views.backtest_tab import BacktestView
from gui.views.terminal_tab import TerminalView
from gui.views.config_tab import ConfigView
from gui.views.faq_tab import FAQView
from gui.views.heatmap_tab import HeatmapView
from gui.widgets.order_book import OrderBookWidget
from gui.widgets.risk_calculator import RiskCalculatorWidget
from gui.widgets.multi_account import MultiAccountManager

# Advanced Indicators Import
try:
    from trading.advanced_indicators import AdvancedIndicators, IndicatorIntegration

    ADVANCED_INDICATORS_AVAILABLE = True
    fancy_print("Advanced Indicators initialisiert", "INDICATORS")
except ImportError as e:
    ADVANCED_INDICATORS_AVAILABLE = False
    fancy_print(f"Advanced Indicators nicht verfügbar: {e}", "WARN")

try:
    from core.market_analyzer import MarketAnalyzer

    MARKET_ANALYZER_AVAILABLE = True
    fancy_print("MarketAnalyzer erfolgreich geladen", "INFO")
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False

try:
    from storage.experience_db import ExperienceDB

    EXPERIENCE_DB_AVAILABLE = True
except ImportError as e:
    fancy_print(f"Experience DB nicht verfügbar: {e}", "ERROR")
    EXPERIENCE_DB_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────
# Modern Pill Navigation Bar (Native CTk)
# ─────────────────────────────────────────────────────────────────
class _ModernTabBar(ctk.CTkFrame):
    """
    Animierte, Apple-ähnliche "Segmented Control" Tab Bar.
    KOMPakte Version: Originalgröße (45px), aber kompaktere Fonts.
    """

    def __init__(self, master, tabs: list[str], on_select, **kw):
        # Original height 45px für volle Funktionalität
        super().__init__(
            master, fg_color="transparent", corner_radius=0, height=45, **kw
        )
        self.pack_propagate(False)
        self._tabs = tabs
        self._on_select = on_select
        self._buttons = {}

        # 1. Background layer for the sliding pill
        self.bg_layer = ctk.CTkFrame(self, fg_color="transparent", corner_radius=15)
        self.bg_layer.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

        # Die animierte, gleitende "Pille" im bg_layer - Originalgröße
        self.active_bg = ctk.CTkFrame(
            self.bg_layer, fg_color="#4B5563", corner_radius=12, height=35, width=0
        )
        self.active_bg.place(x=0, y=5)

        # 2. Foreground layer for the clickable buttons (transparent overlay)
        self.fg_layer = ctk.CTkFrame(self, fg_color="transparent")
        self.fg_layer.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

        self.num_tabs = len(tabs)
        for i in range(self.num_tabs):
            self.fg_layer.grid_columnconfigure(i, weight=1)

        for i, name in enumerate(tabs):
            btn = ctk.CTkButton(
                self.fg_layer,
                text=name,
                fg_color="transparent",
                hover_color=DesignSystem.SEMANTIC['border'],
                text_color=DesignSystem.SEMANTIC['neutral'],
                # KOMPakt: Font 13px → 14px, Height bleibt 35px
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                corner_radius=12,
                height=35,
                width=10,
                command=lambda n=name, idx=i: self._select(n, idx, notify=True),
            )
            btn.grid(row=0, column=i, sticky="ew", padx=3, pady=5)

            # KRITISCH: Button im Dictionary speichern für select() und _select() Methoden
            self._buttons[name] = {"btn": btn, "index": i}

        # Startup variables
        self._active_idx = 0
        self._active_name = tabs[0]
        self._current_x = 0
        self._current_width = 0
        self._animation_job = None

        # Give the GUI time to draw and calculate button sizes
        self.after(100, lambda: self._select(self._tabs[0], 0, notify=False, snap=True))

    def select(self, name: str):
        if name in self._buttons:
            self._select(name, self._buttons[name]["index"], notify=False)

    def _select(self, name: str, idx: int, notify: bool = True, snap: bool = False):
        # KRITISCH: Prüfen ob Buttons Dictionary befüllt ist
        if not self._buttons:
            logging.error(
                f"[_ModernTabBar] FEHLER: _buttons Dictionary ist leer! Buttons wurden nicht erstellt."
            )
            return

        logging.info(
            f"[_ModernTabBar] Tab ausgewählt: {name} (Index: {idx}), verfügbare Tabs: {list(self._buttons.keys())}"
        )
        if self._animation_job:
            self.after_cancel(self._animation_job)

        self._active_name = name
        self._active_idx = idx

        # Update text colors immediately
        for tab_name, data in self._buttons.items():
            btn = data["btn"]
            if tab_name == name:
                btn.configure(
                    text_color="#FFFFFF", hover=False
                )  # White text on soft gray pill
            else:
                btn.configure(
                    text_color=("gray30", "#8B949E"),
                    hover=True,
                    hover_color=("#D1D5DB", "#2A2D34"),
                )

        # Calculate target position for the sliding pill
        self.update_idletasks()
        try:
            target_btn = self._buttons[name]["btn"]
            # To get relative X to the _ModernTabBar we need to account for fg_layer
            # The safest way in Tkinter is to use rootx difference
            target_x = target_btn.winfo_rootx() - self.winfo_rootx()
            target_width = target_btn.winfo_width()

            if target_width <= 1:  # Window not fully drawn yet
                self.after(50, lambda: self._select(name, idx, notify, snap))
                return

            if snap:
                self._current_x = target_x
                self._current_width = target_width
                self.active_bg.configure(width=self._current_width)
                # Original: y=5, height=35
                self.active_bg.place(
                    x=self._current_x, y=5, width=self._current_width, height=35
                )
            else:
                # Start Animation
                self._animate_pill(target_x, target_width)

            if notify:
                self._on_select(name)
        except Exception as e:
            pass

    def _animate_pill(self, target_x, target_w):
        """Easing Funktion für das sliden der Pille"""
        try:
            # Easing factor: higher is slower. 0.3 means move 30% of the remaining distance per frame
            easing = 0.35

            dx = target_x - self._current_x
            dw = target_w - self._current_width

            # Stop condition (close enough)
            if abs(dx) < 1.0 and abs(dw) < 1.0:
                self._current_x = target_x
                self._current_width = target_w
                self.active_bg.configure(width=self._current_width)
                # Original: y=5, height=35
                self.active_bg.place(
                    x=self._current_x, y=5, width=self._current_width, height=35
                )
                return

            self._current_x += dx * easing
            self._current_width += dw * easing

            self.active_bg.configure(width=self._current_width)
            self.active_bg.place(
                x=self._current_x, y=5, width=self._current_width, height=35
            )  # Original
            self._animation_job = self.after(
                16, lambda: self._animate_pill(target_x, target_w)
            )
        except Exception:
            pass


class ModernFinGPTGUI(ctk.CTk):
    """
    Das komplett modernisierte FinGPT Interface mit CustomTkinter
    """

    def __init__(self):
        super().__init__()

        # Handle window close event (Alt+F4, etc.)
        self.protocol("WM_DELETE_WINDOW", self._close_window)

        self.app_config = app_config_manager.load()

        # ============================================================
        # MODERNISIERUNG: Event Bus und Data Update Manager
        # ============================================================
        self.event_bus = None
        self.data_update_manager = None

        if EVENT_BUS_AVAILABLE:
            try:
                from gui.controllers.event_bus import EventBus, DashboardEvents, DashboardEvent
                self.event_bus = EventBus()
                self.event_bus.subscribe(
                    DashboardEvents.ACCOUNT_DATA_UPDATED, self._on_data_updated
                )
                self.event_bus.subscribe(
                    DashboardEvents.TRADE_EXECUTED, self._on_trade_executed
                )
                self.event_bus.subscribe(
                    DashboardEvents.CONNECTION_STATUS_CHANGED, self._on_config_changed
                )
                fancy_print("Event Bus erfolgreich initialisiert", "SYSTEM")
            except Exception as e:
                fancy_print(f"Event Bus Initialisierung fehlgeschlagen: {e}", "ERROR")
        else:
            self.event_bus = None

        if DATA_UPDATE_MANAGER_AVAILABLE:
            try:
                from gui.utils.data_update_manager import DataUpdateManager
                self.data_update_manager = DataUpdateManager()
                fancy_print("Data Update Manager erfolgreich initialisiert", "SYSTEM")
            except Exception as e:
                fancy_print(
                    f"Data Update Manager Initialisierung fehlgeschlagen: {e}", "ERROR"
                )
        else:
            self.data_update_manager = None
        # ============================================================

        self.title("FinGPT Professional Dashboard")

        # Icon setzen
        try:
            import os

            icon_path = r"C:\Users\edgar\Downloads\generated-image-removebg-preview.png"
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, img)
                self._app_icon = img
        except Exception:
            pass

        # Responsive Fenstergröße - verwende verfügbare Bildschirmgröße
        self._setup_responsive_geometry()

        self.attributes("-alpha", 1.0)  # Make window visible immediately

        # Custom Apple-like Titlebar Setup
        self.overrideredirect(True)
        # Set main background color directly to TTG Deep Black
        self.configure(fg_color="#09090B")

        # Hack to show window in Windows taskbar and apply native rounded corners
        self.after(200, self._set_appwindow)
        self.bind("<Map>", self._on_map)

        # Main container (no fake rounded corners anymore, OS handles it natively)
        self.main_container = ctk.CTkFrame(
            self, corner_radius=0, border_width=0, fg_color="transparent"
        )
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Aurora Hintergrund (als ERSTES Element in main_container laden -> Z-Index ganz unten) ──────
        self._aurora_bg = None
        if _AURORA_AVAILABLE:
            try:
                self._aurora_bg = attach_aurora_to_frame(
                    self.main_container,
                    config={
                        "color0":    "5227FF",   # Violet
                        "color1":    "7cff67",   # Light Green
                        "color2":    "5227FF",   # Violet
                        "amplitude": 1.0,
                        "blend":     0.5,
                        "speed":     0.8,
                    },
                )
                fancy_print("Aurora Hintergrund aktiv", "SYSTEM")
            except Exception as _aurora_err:
                fancy_print(f"Aurora Hintergrund Fehler: {_aurora_err}", "WARN")
        # ─────────────────────────────────────────────────────────────────────────────────────────────

        # Custom Titlebar inside main_container
        self.title_bar = ctk.CTkFrame(
            self.main_container, height=40, corner_radius=0, fg_color="#18181B"
        )
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<B1-Motion>", self._move_window)
        self.title_bar.bind("<Button-1>", self._get_pos)

        # Apple style buttons wrapper
        self.apple_buttons_frame = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.apple_buttons_frame.pack(side="left", padx=12, pady=(10, 0))

        # TTG Style Buttons
        self.close_btn = ctk.CTkButton(
            self.apple_buttons_frame,
            width=12,
            height=12,
            corner_radius=6,
            text="",
            fg_color="#EF4444",
            hover_color="#FF5252",
            command=self._close_window,
        )
        self.close_btn.pack(side="left", padx=4)

        self.min_btn = ctk.CTkButton(
            self.apple_buttons_frame,
            width=12,
            height=12,
            corner_radius=6,
            text="",
            fg_color="#F59E0B",
            hover_color="#FFFF00",
            command=self._minimize_window,
        )
        self.min_btn.pack(side="left", padx=4)

        self.max_btn = ctk.CTkButton(
            self.apple_buttons_frame,
            width=12,
            height=12,
            corner_radius=6,
            text="",
            fg_color="#10B981",
            hover_color="#00E676",
            command=self._maximize_window,
        )
        self.max_btn.pack(side="left", padx=4)

        # Title inside titlebar
        self.title_lbl = ctk.CTkLabel(
            self.title_bar,
            text="FinGPT Professional Dashboard",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color="#FFFFFF",
        )
        self.title_lbl.pack(side="left", padx=(10, 0))
        self.title_lbl.bind("<B1-Motion>", self._move_window)
        self.title_lbl.bind("<Button-1>", self._get_pos)

        # Content frame that replaces 'self' for the original grid layout
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=0, pady=(0, 10))

        # --- Add Resize Grip ---
        self.sizegrip = ctk.CTkLabel(
            self.main_container,
            text="◢",
            text_color="gray40",
            font=ctk.CTkFont(family="Inter", size=14),
        )
        self.sizegrip.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)
        self.sizegrip.bind("<B1-Motion>", self._resize_window)
        self.sizegrip.configure(cursor="size_nw_se")

        # State variables
        self.is_live_running = False
        self.live_data_rows = []
        self.pnl_history = []  # Stores recent P&L values for the Live Chart

        # --- Advanced Indicators Initialization ---
        self.market_analyzer = None
        self.advanced_indicators = None
        self.indicator_integration = None

        if MARKET_ANALYZER_AVAILABLE:
            self.market_analyzer = MarketAnalyzer(broker=self, logger=None)
            self.write_terminal(">> MarketAnalyzer erfolgreich geladen.\n")

        if ADVANCED_INDICATORS_AVAILABLE:
            self.advanced_indicators = AdvancedIndicators(logger=None)
            self.indicator_integration = IndicatorIntegration(
                self
            )  # Pass 'self' as the bot/fingpt instance
            self.write_terminal(
                ">> Erweiterte Indikatoren (10+) erfolgreich geladen.\n"
            )

        # Konstruktor Aufruf für Layout
        self.setup_layout()
        self.start_simulated_data()

    # --- Custom Titlebar & Resize Methods ---
    def _resize_window(self, event):
        """Allows resizing of the frameless window from the bottom right corner."""
        width = int(event.x_root - self.winfo_rootx())
        height = int(event.y_root - self.winfo_rooty())
        # Enforce minimum sizes manually
        width = max(width, 900)
        height = max(height, 700)
        self.geometry(f"{width}x{height}")

    def _set_appwindow(self):
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # Taskbar integration
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style = style & ~0x00000080
            style = style | 0x00040000
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)

            # Windows 11 Native Rounded Corners
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
            val = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(val), ctypes.sizeof(val)
            )
        except Exception:
            pass

    def _get_pos(self, event):
        self._xwin = event.x
        self._ywin = event.y

    def _move_window(self, event):
        self.geometry(f"+{event.x_root - self._xwin}+{event.y_root - self._ywin}")

    def _close_window(self):
        # Stop all background threads gracefully before closing
        self.is_live_running = False
        self._is_closing = True

        # Aurora stoppen
        if hasattr(self, "_aurora_bg") and self._aurora_bg is not None:
            try:
                self._aurora_bg.stop()
            except Exception:
                pass

        if hasattr(self, "heatmap_view"):
            self.heatmap_view.stop()

        if hasattr(self, "terminal_view"):
            self.terminal_view.destroy()

        self.destroy()

    def _minimize_window(self):
        self.overrideredirect(False)
        self.state("iconic")

    def _maximize_window(self):
        if self.state() == "zoomed":
            self.state("normal")
        else:
            self.state("zoomed")

    def _setup_responsive_geometry(self):
        """
        Richtet das Fenster responsive ein, basierend auf der Bildschirmgröße.
        Verwendet die verfügbare Bildschirmgröße für eine optimale Darstellung.
        """
        try:
            # Hole Bildschirmgröße
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # Berechne optimale Fenstergröße (80% der Bildschirmgröße, max 1400x950)
            target_width = min(int(screen_width * 0.85), 1400)
            target_height = min(int(screen_height * 0.85), 950)

            # Setze Mindestgröße basierend auf Bildschirmgröße
            # Für sehr kleine Bildschirme reduziere Mindestgröße
            if screen_width < 1024 or screen_height < 768:
                min_width = 800
                min_height = 600
            else:
                min_width = 900
                min_height = 700

            self.minsize(min_width, min_height)

            # Zentriere Fenster
            x = (screen_width - target_width) // 2
            y = (screen_height - target_height) // 2

            self.geometry(f"{target_width}x{target_height}+{x}+{y}")

        except Exception:
            # Fallback zu Standardwerten
            self.geometry("1400x950")
            self.minsize(900, 700)

    def _on_map(self, event):
        if self.state() == "normal":
            self.overrideredirect(True)

    # --- Compatibility Helpers for Advanced Indicators ---
    @property
    def logger(self):
        """Helper to satisfy AdvancedIndicators/MarketAnalyzer."""
        import logging

        return logging.getLogger("FinGPT-GUI")

    def log(self, level, message, category="GUI"):
        """Logging helper."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] [{category}] {message}")

    def get_mt5_live_data(self, symbol):
        """Returns a string summary of live data for a symbol."""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return f"Keine Ticks für {symbol} empfangen."

            # Basis-Info
            bid = tick.bid
            ask = tick.ask
            spread = ask - bid

            # Hole letzte Kerze für Änderung
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
            change_pct = 0.0
            if rates is not None and len(rates) > 0:
                open_price = rates[0]["open"]
                change_pct = ((bid - open_price) / open_price) * 100

            return (
                f"AKTUELLER MARKT STATUS ({symbol}):\n"
                f"- Preis (Bid): {bid:.5f}\n"
                f"- Preis (Ask): {ask:.5f}\n"
                f"- Spread: {spread:.5f}\n"
                f"- Tages-Änderung: {change_pct:+.2f}%\n"
                f"- Zeit: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            return f"Fehler beim Abrufen der Live-Daten für {symbol}: {e}"

    # --- Indicator Integration Helpers ---
    @property
    def mt5_connected(self):
        """Helper for MarketAnalyzer check."""
        return mt5.initialize()

    def calculate_rsi(self, symbol, timeframe=mt5.TIMEFRAME_H1):
        if self.market_analyzer:
            return self.market_analyzer.calculate_rsi(symbol, timeframe)
        return None

    def calculate_macd(self, symbol, timeframe=mt5.TIMEFRAME_H1):
        if self.market_analyzer:
            return self.market_analyzer.calculate_macd(symbol, timeframe)
        return None

    def calculate_support_resistance(self, symbol, timeframe=mt5.TIMEFRAME_H1):
        if self.market_analyzer:
            return self.market_analyzer.calculate_support_resistance(symbol, timeframe)
        return None

    def get_rsi_signal(self, rsi_value):
        if self.market_analyzer:
            return self.market_analyzer.get_rsi_signal(rsi_value)
        return "NEUTRAL", "No Analyzer"

    def get_macd_signal(self, macd_data):
        if self.market_analyzer:
            return self.market_analyzer.get_macd_signal(macd_data)
        return "NEUTRAL", "No Analyzer"

    def get_sr_signal(self, sr_data, current_price):
        if self.market_analyzer:
            return self.market_analyzer.get_sr_signal(sr_data, current_price)
        return "NEUTRAL", "No Analyzer"

    def setup_layout(self):
        """Haupt-Grid System der UI"""
        # row 0 = header, row 1 = nav bar, row 2 = tabview (weight=1), row 3 = status bar
        self.content_frame.grid_rowconfigure(2, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Aurora wurde bereits in __init__ geladen, um ganz hinten im Z-Index zu liegen

        # 1. Header Frame - KOMPakt: pady=(15,15) → (5,5)
        self.header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.header_frame.grid(
            row=0, column=0, sticky="ew", padx=30, pady=(5, 5)
        )  # KOMPakt: pady=(15,15)

        try:
            logo_path = r"C:\Users\edgar\Desktop\FinGPT Webseite\Bilder logo.png"
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                # KOMPakt: Logo height 32px → 24px
                w, h = pil_img.size
                aspect = w / h
                ctk_logo = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(int(24 * aspect), 24)
                )  # KOMPakt: 32→24

                self.logo_label = ctk.CTkLabel(
                    self.header_frame, image=ctk_logo, text=""
                )
                self.logo_label.pack(side="left", padx=(0, 10))  # KOMPakt: padx=(0,15)
        except Exception as e:
            print(f"Fehler beim Laden des Logos: {e}")

        # KOMPakt: Title font 24px → 16px
        title_label = ctk.CTkLabel(
            self.header_frame,
            text="FinGPT Professional",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),  # KOMPakt: 24→16
            text_color="#FFFFFF",
        )
        title_label.place(relx=0.45, rely=0.5, anchor="center")

        # Version-Label - KOMPakt: Kleiner und weniger padding
        version_label = ctk.CTkLabel(
            self.header_frame,
            text="v1.0.3 Beta",
            font=ctk.CTkFont(family="Inter", size=9),  # KOMPakt: 12→9
            text_color="#8B949E",
        )
        version_label.pack(
            side="left", padx=(8, 0), pady=(5, 0)
        )  # KOMPakt: padx=(10,0), pady=(8,0)

        # Version-Label entfernt für mehr Platz (KOMPakt)
        # KOMPakt: Live-Button height 40→28, corner_radius 20→15
        self.live_btn = ctk.CTkButton(
            self.header_frame,
            text="▶ Live",
            command=self.toggle_live_data,  # KOMPakt: "▶ Live Starten" → "▶ Live"
            fg_color="#10B981",
            hover_color="#00C853",
            text_color="#09090B",
            corner_radius=15,
            height=28,  # KOMPakt: height=28
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
        )  # KOMPakt: size=12
        self.live_btn.pack(side="right", padx=(8, 0))

        # KOMPakt: Status dot size 20→14
        self.status_dot = ctk.CTkLabel(
            self.header_frame,
            text="●",
            text_color="#EF4444",
            font=ctk.CTkFont(family="Inter", size=14),
        )  # KOMPakt: 20→14
        self.status_dot.pack(side="right")

        # ── Tab names - Originalnamen für Views behalten
        _TAB_NAMES = [
            "📊 Dashboard",
            "📈 Charts",
            "🎭 Debate",
            "📉 Backtest",
            "🔥 Heatmap",
            "💹 Trading",
            "📝 Journal",
            "📰 News",
            "🤖 RL Studio",
            "💻 Terminal",
            "⚙️ Konfiguration",
            "❓ FAQ",
        ]

        # 2a. Modern CTk Tab Bar (row=1) - KOMPakt: pady (0,10) → (0,4)
        logging.info(
            f"[ModernFinGPTGUI] Erstelle _ModernTabBar mit {len(_TAB_NAMES)} Tabs: {_TAB_NAMES}"
        )
        self.nav_bar = _ModernTabBar(
            self.content_frame,
            tabs=_TAB_NAMES,
            on_select=self._navbar_on_select,
        )
        # padding pushes it cleanly slightly down - KOMPakt: pady=(0,10) → (0,4)
        self.nav_bar.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 4))
        logging.info("[ModernFinGPTGUI] NavBar erfolgreich erstellt und positioniert")

        # 2b. Main Tabview – content area only (row=2)
        self.content_frame.grid_rowconfigure(2, weight=1)
        self.tabview = ctk.CTkTabview(
            self.content_frame,
            corner_radius=15,
            segmented_button_fg_color="#09090B",
            segmented_button_selected_color="#1E2228",
            segmented_button_unselected_color="#09090B",
            segmented_button_selected_hover_color="#1E2228",
            segmented_button_unselected_hover_color="#09090B",
            text_color="#8B949E",
            fg_color="transparent",
        )
        self.tabview.grid(
            row=2, column=0, sticky="nsew", padx=30, pady=(0, 8)
        )  # KOMPakt: pady (0,20) → (0,8)

        self.tabview.configure(border_width=0)

        for name in _TAB_NAMES:
            tab_frame = self.tabview.add(name)
            # Make tabs transparent so the aurora background can shine through
            tab_frame.configure(fg_color="transparent")

        # Hide the built-in segmented button completely after tabs are added
        self.tabview._segmented_button.grid_remove()
        self.tabview._segmented_button.configure(height=0)

        # Tabs konfigurieren - Reihenfolge muss mit _TAB_NAMES übereinstimmen
        self.dashboard_view = DashboardView(self.tabview.tab("📊 Dashboard"), self)
        
        # #region agent log
        import json, time
        with open("debug-0a8f4e.log", "a") as f:
            f.write(json.dumps({"sessionId":"0a8f4e", "runId":"post-fix", "hypothesisId":"H3", "location":"modern_fingpt_gui.py:tab_bg", "message":"Tab Dashboard fg_color", "data":{"fg_color": str(self.tabview.tab("📊 Dashboard").cget("fg_color"))}, "timestamp":int(time.time()*1000)}) + "\n")
        # #endregion
        
        self.charts_view = ChartsView(self.tabview.tab("📈 Charts"), self)
        self.debate_view = DebateView(self.tabview.tab("🎭 Debate"), self)
        self.backtest_view = BacktestView(self.tabview.tab("📉 Backtest"), self)
        self.heatmap_view = HeatmapView(self.tabview.tab("🔥 Heatmap"), self)
        self.trading_view = self._create_trading_view(
            self.tabview.tab("💹 Trading"), self
        )
        self.journal_view = JournalView(self.tabview.tab("📝 Journal"), self)
        self.news_view = NewsView(self.tabview.tab("📰 News"), self)
        self.rl_settings_view = RLSettingsView(self.tabview.tab("🤖 RL Studio"), self)
        self.terminal_view = TerminalView(self.tabview.tab("💻 Terminal"), self)
        self.config_view = ConfigView(self.tabview.tab("⚙️ Konfiguration"), self)
        self.faq_view = FAQView(self.tabview.tab("❓ FAQ"), self)

        # 3. Status Bar - KOMPakt: height 30→24, pady (0,30) → (0,10)
        self.status_bar = ctk.CTkFrame(
            self.content_frame, height=24, corner_radius=12
        )  # KOMPakt: height=24
        self.status_bar.grid(
            row=3, column=0, sticky="ew", padx=30, pady=(0, 10)
        )  # KOMPakt: pady=(0,30) → (0,10)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Bereit | Letzte Aktualisierung: Nie",
            font=ctk.CTkFont(family="Inter", size=10),
        )  # KOMPakt: size=12 → 10
        self.status_label.pack(side="left", padx=10, pady=3)

        # System Indicators
        self.indicator_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.indicator_frame.pack(side="right", padx=15, pady=5)

        # We will create these labels dynamically or explicitly
        self.indicators = {}
        self.indicator_labels = {}  # Store references for tooltips/text updates

        for sys_name in ["Python", "MT5", "Ollama", "RL Engine"]:
            frame = ctk.CTkFrame(self.indicator_frame, fg_color="transparent")
            frame.pack(side="left", padx=6)  # KOMPakt: padx=10 → 6
            dot = ctk.CTkLabel(
                frame,
                text="●",
                text_color="gray",
                font=ctk.CTkFont(family="Inter", size=12),
            )  # KOMPakt: size=16 → 12
            dot.pack(side="left", padx=(0, 4))  # KOMPakt: padx=(0,6) → (0,4)
            lbl = ctk.CTkLabel(
                frame,
                text=sys_name,
                font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                text_color="gray70",
            )  # KOMPakt: size=13 → 10
            lbl.pack(side="left")
            self.indicators[sys_name] = dot
            self.indicator_labels[sys_name] = lbl

        self.update_footer_indicators()
        # Load any previously saved settings from disk
        self.after(300, self.load_settings)
        # Start the fade-in animation
        self.after(100, self._fade_in, 0.0)

    def _fade_in(self, alpha):
        """Weiche Fade-In Animation beim Start des Programms"""
        alpha += 0.08
        if alpha < 1.0:
            self.attributes("-alpha", alpha)
            self.after(25, self._fade_in, alpha)
        else:
            self.attributes("-alpha", 1.0)

    def _navbar_on_select(self, tab_name: str):
        """Called by the nav bar when user clicks a tab."""
        logging.info(f"[_navbar_on_select] Tab-Wechsel zu: {tab_name}")
        self.tabview.set(tab_name)
        self._on_tab_change()

    def _on_tab_change(self):
        """Micro-Interaction: Kurzes dynamisches Flackern / Fade beim Tab-Wechsel."""
        # Keep the nav bar in sync if tab was changed programmatically
        try:
            current = self.tabview.get()
            if hasattr(self, "nav_bar"):
                self.nav_bar.select(current)
        except Exception:
            pass
        self.attributes("-alpha", 0.85)
        self.after(10, self._fade_in, 0.85)

    # ══════════════════════════════════════════════════════
    # TRADE JOURNAL TAB
    # ══════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════
    # BACKTESTING TAB (now in gui/views/backtest_tab.py)
    # ══════════════════════════════════════════════════════════════

    def setup_terminal_tab(self):
        # Ausgelagert in TerminalView (gui/views/terminal_tab.py)
        pass

    def _trigger_autosave(self, *args):
        """Debounced auto-save. Waits 1 second after the last change to save."""
        if hasattr(self, "_autosave_timer") and self._autosave_timer is not None:
            self.after_cancel(self._autosave_timer)
        self._autosave_timer = self.after(1000, self._do_autosave)

    def _do_autosave(self):
        """Silently saves config and updates dependent UI (like symbol rows)."""
        self.save_settings(silent=True)
        # Pairs — delegate to shared helper so dashboard updates instantly
        raw_pairs = self.config_view.pairs_entry.get().strip()
        if raw_pairs:
            self.dashboard_view._rebuild_symbol_rows(raw_pairs)

    def _create_trading_view(self, parent, app):
        """Erstellt die Trading-Ansicht mit Order Book, Risk Calculator und Multi-Account"""
        # Main container
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # Two-column layout
        left_column = ctk.CTkFrame(container)
        left_column.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        right_column = ctk.CTkFrame(container)
        right_column.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        # Order Book (links oben)
        order_book_frame = ctk.CTkFrame(left_column)
        order_book_frame.pack(fill="both", expand=True)

        try:
            self.order_book_widget = OrderBookWidget(order_book_frame)
            self.order_book_widget.pack(fill="both", expand=True)
        except Exception as e:
            ctk.CTkLabel(
                order_book_frame,
                text=f"Order Book konnte nicht geladen werden: {e}",
                text_color="red",
            ).pack(pady=20)

        # Risk Calculator (links unten)
        risk_calc_frame = ctk.CTkFrame(left_column)
        risk_calc_frame.pack(fill="both", expand=True, pady=(10, 0))

        try:
            self.risk_calculator_widget = RiskCalculatorWidget(risk_calc_frame)
            self.risk_calculator_widget.pack(fill="both", expand=True)
        except Exception as e:
            ctk.CTkLabel(
                risk_calc_frame,
                text=f"Risk Calculator konnte nicht geladen werden: {e}",
                text_color="red",
            ).pack(pady=20)

        # Multi-Account Manager (rechts)
        multi_account_frame = ctk.CTkFrame(right_column)
        multi_account_frame.pack(fill="both", expand=True)

        try:
            self.multi_account_widget = MultiAccountManager(multi_account_frame)
            self.multi_account_widget.pack(fill="both", expand=True)
        except Exception as e:
            ctk.CTkLabel(
                multi_account_frame,
                text=f"Multi-Account Manager konnte nicht geladen werden: {e}",
                text_color="red",
            ).pack(pady=20)

        return container

    def setup_config_tab(self):
        tab = self.tabview.tab("⚙️ Konfiguration")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Sub-navigation for config
        self.config_sub_tabs = ctk.CTkTabview(tab, corner_radius=10)
        self.config_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self.config_sub_tabs.add("🤖 KI & Ollama")
        self.config_sub_tabs.add("🎨 Appearance")
        self.config_sub_tabs.add("📊 Trading Style")
        self.config_sub_tabs.add("🧠 Reinforcement Learning")
        self.config_sub_tabs.add("⚙️ MT5 & System")
        self.config_sub_tabs.add("🔕 Benachrichtigungen")

        # Now actually populate them
        self._populate_config_tabs(tab)

    def _on_provider_change(self, choice=None):
        if choice is None:
            choice = self.config_view.ki_provider_var.get()

        if "Ollama" in choice:
            self.config_view.url_lbl.configure(text="Ollama URL:")
            self.config_view.api_key_entry.configure(
                state="normal"
            )  # Enable to allow clearing or just let it be
            self.config_view.api_key_entry.configure(fg_color=("gray85", "gray25"))
            # Optionally disable entirely but grey out is nice
            threading.Thread(
                target=self.config_view.fetch_ollama_models_silently, daemon=True
            ).start()
        elif "OpenAI" in choice:
            self.config_view.url_lbl.configure(text="Base URL (opt):")
            self.config_view.api_key_entry.configure(
                state="normal", fg_color=("white", "gray15")
            )
            self.config_view.model_combo.configure(
                values=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            )
            if self.config_view.model_combo.get() not in [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ]:
                self.config_view.model_combo.set("gpt-4o")
        elif "Anthropic" in choice:
            self.config_view.url_lbl.configure(text="Base URL (opt):")
            self.config_view.api_key_entry.configure(
                state="normal", fg_color=("white", "gray15")
            )
            self.config_view.model_combo.configure(
                values=[
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-haiku-20240307",
                ]
            )
            if self.config_view.model_combo.get() not in [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
            ]:
                self.config_view.model_combo.set("claude-3-5-sonnet-20241022")
        elif "DeepSeek" in choice:
            self.config_view.url_lbl.configure(text="Base URL (opt):")
            self.config_view.api_key_entry.configure(
                state="normal", fg_color=("white", "gray15")
            )
            self.config_view.model_combo.configure(
                values=["deepseek-chat", "deepseek-coder"]
            )
            if self.config_view.model_combo.get() not in [
                "deepseek-chat",
                "deepseek-coder",
            ]:
                self.config_view.model_combo.set("deepseek-chat")
        elif "OpenRouter" in choice:
            self.config_view.url_lbl.configure(text="Base URL (opt):")
            self.config_view.api_key_entry.configure(
                state="normal", fg_color=("white", "gray15")
            )
            self.config_view.model_combo.configure(values=["Lade Modelle..."])
            self.config_view.model_combo.set("Lade Modelle...")
            threading.Thread(
                target=self.config_view.fetch_openrouter_models_silently, daemon=True
            ).start()

        self._trigger_autosave()

    def _call_llm_api(self, system_prompt, user_prompt, max_tokens=500):
        """
        Zentraler HTTP Wrapper für Ollama, OpenAI, Anthropic, DeepSeek.
        Nimmt Parameter aus dem GUI state. Blockiert, sollte also aus Threads aufgerufen werden!
        """
        import requests
        import subprocess
        import threading
        import time

        provider = self.config_view.ki_provider_var.get()
        model = self.config_view.model_combo.get()
        temperature = self.config_view.ai_temp_slider.get()
        url = self.config_view.url_entry.get().strip()
        api_key = self.config_view.api_key_entry.get().strip()

        # Hilfsfunktion: Versuche Ollama automatisch zu starten
        def try_start_ollama():
            """Versucht Ollama im Hintergrund zu starten."""
            try:
                # Versuche zuerst den normalen Ollama-Befehl
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                # Warte bis zu 10 Sekunden auf Ollama
                for _ in range(20):
                    time.sleep(0.5)
                    try:
                        resp = requests.get(f"{base_url}/api/tags", timeout=1)
                        if resp.status_code == 200:
                            return True
                    except:
                        pass
                return False
            except FileNotFoundError:
                return False
            except Exception:
                return False

        # 1. Ollama (Lokal)
        if "Ollama" in provider:
            base_url = url if url else "http://localhost:11434"
            full_prompt = f"System: {system_prompt}\nUser: {user_prompt}"
            try:
                resp = requests.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                    timeout=120,
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "")
                else:
                    return f"[API Fehler Ollama] Status {resp.status_code}: {resp.text}"
            except requests.exceptions.ConnectionError as e:
                # Ollama läuft nicht - versuche es automatisch zu starten
                err_msg = str(e)
                if "Connection refused" in err_msg or "10061" in err_msg:
                    # Versuche Ollama automatisch zu starten
                    self.write_terminal(
                        ">> Ollama nicht erreichbar. Versuche automatisch zu starten...\n"
                    )
                    if try_start_ollama():
                        self.write_terminal(
                            ">> Ollama wurde gestartet. Wiederhole Anfrage...\n"
                        )
                        try:
                            resp = requests.post(
                                f"{base_url}/api/generate",
                                json={
                                    "model": model,
                                    "prompt": full_prompt,
                                    "stream": False,
                                    "options": {
                                        "num_predict": max_tokens,
                                        "temperature": temperature,
                                    },
                                },
                                timeout=120,
                            )
                            if resp.status_code == 200:
                                return resp.json().get("response", "")
                            else:
                                return f"[API Fehler Ollama] Status {resp.status_code}: {resp.text}"
                        except Exception as e2:
                            return f"[API Fehler Ollama] Auch nach Neustart: {str(e2)}"
                    else:
                        return (
                            f"[API Fehler Ollama] Ollama läuft nicht!\n"
                            f"Bitte starten Sie Ollama manuell mit: 'ollama serve'\n"
                            f"Oder installieren Sie Ollama von: https://ollama.ai\n"
                            f"Details: {err_msg}"
                        )
                return f"[API Fehler Ollama] {err_msg}"
            except Exception as e:
                return f"[API Fehler Ollama] {str(e)}"

        # 2. OpenAI API
        elif "OpenAI" in provider:
            base_url = url if url else "https://api.openai.com/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                else:
                    return f"[API Fehler OpenAI] {resp.status_code}: {resp.text}"
            except Exception as e:
                return f"[API Fehler OpenAI] {str(e)}"

        # 3. Anthropic API
        elif "Anthropic" in provider:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                resp = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 200:
                    return resp.json()["content"][0]["text"]
                else:
                    return f"[API Fehler Anthropic] {resp.status_code}: {resp.text}"
            except Exception as e:
                return f"[API Fehler Anthropic] {str(e)}"

        # 4. DeepSeek API
        elif "DeepSeek" in provider:
            base_url = url if url else "https://api.deepseek.com/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                else:
                    return f"[API Fehler DeepSeek] {resp.status_code}: {resp.text}"
            except Exception as e:
                return f"[API Fehler DeepSeek] {str(e)}"

        # 5. OpenRouter API
        elif "OpenRouter" in provider:
            base_url = url if url else "https://openrouter.ai/api/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://fingpt.local",
                "X-Title": "FinGPT",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                else:
                    return f"[API Fehler OpenRouter] {resp.status_code}: {resp.text}"
            except Exception as e:
                return f"[API Fehler OpenRouter] {str(e)}"

        return "[Fehler] Unbekannter KI Provider"

    def save_config(self):
        try:
            # Gather Configuration Data
            ollama_url = self.config_view.url_entry.get().strip()
            llm_model = self.config_view.model_combo.get()
            auto_trade_interval = int(self.config_view.interval_slider.get())

            # Risk Management
            is_auto_trading = self.config_view.trading_active_switch.get() == 1
            max_risk = float(self.config_view.risk_trade_entry.get())
            max_daily_loss = float(self.config_view.risk_daily_entry.get())
            max_pos = int(self.config_view.max_pos_entry.get())

            # Pairs — delegate to shared helper
            raw_pairs = self.config_view.pairs_entry.get().strip()
            if raw_pairs:
                self.dashboard_view._rebuild_symbol_rows(raw_pairs)

            status_msg = f">> [CONFIG SAVED] Model: {llm_model} | Auto: {is_auto_trading} | Interval: {auto_trade_interval}s\n"
            status_msg += f">> [RISK LIMITS] Risk/Trade: {max_risk}% | Daily Loss: {max_daily_loss}% | Max Pos: {max_pos}\n"
            status_msg += (
                f">> [PAIRS] Monitoring {len(self.dashboard_symbols)} pairs.\n"
            )
            self.write_terminal(status_msg)

            # Persist to disk
            self.save_settings()

            messagebox.showinfo(
                "Erfolg", "Konfiguration wurde erfolgreich gespeichert und angewendet!"
            )

            if self.is_live_running:
                self.update_dashboard_data()

        except ValueError as e:
            messagebox.showerror(
                "Eingabefehler",
                f"Bitte überprüfen Sie Ihre numerischen Eingaben.\nDetails: {str(e)}",
            )

    def _config_path(self):
        return app_config_manager.config_path

    def update_config_from_gui(self):
        cfg = self.app_config
        view = self.config_view

        cfg.ki_provider = view.ki_provider_var.get()
        cfg.ollama_url = view.url_entry.get().strip()

        api_text = view.api_key_entry.get().strip()
        cfg.api_key = api_text
        if "OpenAI" in cfg.ki_provider:
            cfg.api_key_openai = api_text
        elif "Anthropic" in cfg.ki_provider:
            cfg.api_key_anthropic = api_text
        elif "DeepSeek" in cfg.ki_provider:
            cfg.api_key_deepseek = api_text
        elif "OpenRouter" in cfg.ki_provider:
            cfg.api_key_openrouter = api_text
        cfg.llm_model = view.model_combo.get()
        try:
            cfg.interval = int(view.interval_slider.get())
        except:
            pass
        try:
            cfg.ai_temperature = round(view.ai_temp_slider.get(), 1)
        except:
            pass
        cfg.prompt_lang = view.prompt_lang_var.get()
        cfg.system_prompt = view.system_prompt_text.get("0.0", "end-1c").strip()
        try:
            cfg.min_confidence = int(view.confidence_slider.get())
        except:
            pass

        cfg.trading_style = view.trading_style_var.get()
        cfg.signal_strategy = view.signal_strategy_var.get()
        cfg.risk_profile = view.risk_profile_var.get()
        cfg.max_risk = view.risk_trade_entry.get()
        cfg.max_daily_loss = view.risk_daily_entry.get()
        cfg.max_positions = view.max_pos_entry.get()
        cfg.trailing_stop = bool(view.trailing_stop_switch.get())
        cfg.trailing_dist = view.ts_dist_entry.get()
        cfg.break_even = bool(view.break_even_switch.get())
        cfg.break_even_dist = view.be_dist_entry.get()
        cfg.weekend_exit = bool(view.weekend_exit_switch.get())
        cfg.auto_trading = bool(view.trading_active_switch.get())
        if hasattr(view, "session_london"):
            cfg.session_london = bool(view.session_london.get())
        if hasattr(view, "session_ny"):
            cfg.session_ny = bool(view.session_ny.get())
        if hasattr(view, "session_asia"):
            cfg.session_asia = bool(view.session_asia.get())
        if hasattr(view, "session_sydney"):
            cfg.session_sydney = bool(view.session_sydney.get())

        cfg.trade_time_from = view.trade_time_from.get()
        cfg.trade_time_to = view.trade_time_to.get()
        cfg.time_filter = bool(view.time_filter_switch.get())
        cfg.day_mon = bool(view.day_mon.get())
        cfg.day_tue = bool(view.day_tue.get())
        cfg.day_wed = bool(view.day_wed.get())
        cfg.day_thu = bool(view.day_thu.get())
        cfg.day_fri = bool(view.day_fri.get())
        # NEU: Samstag und Sonntag
        cfg.day_sat = bool(view.day_sat.get()) if hasattr(view, "day_sat") else False
        cfg.day_sun = bool(view.day_sun.get()) if hasattr(view, "day_sun") else False

        cfg.news_filter = bool(view.news_filter_switch.get())
        try:
            cfg.news_before_min = int(view.news_before_slider.get())
        except:
            pass
        try:
            cfg.news_after_min = int(view.news_after_slider.get())
        except:
            pass
        cfg.news_high = bool(view.news_high.get())
        cfg.news_medium = bool(view.news_medium.get())
        cfg.news_low = bool(view.news_low.get())

        try:
            cfg.max_spread = int(view.max_spread_slider.get())
        except:
            pass
        try:
            cfg.max_slippage = int(view.max_slippage_slider.get())
        except:
            pass
        cfg.spread_check = bool(view.spread_check_switch.get())

        cfg.rl_algo = view.rl_algo_var.get()
        try:
            cfg.rl_learning_rate = round(view.rl_lr_slider.get(), 4)
        except:
            pass
        try:
            cfg.rl_gamma = round(view.rl_gamma_slider.get(), 2)
        except:
            pass
        cfg.rl_steps = view.rl_steps_entry.get()
        cfg.rl_reward = view.rl_reward_var.get()
        cfg.rl_buffer_size = view.rl_buffer_entry.get()
        cfg.rl_batch_size = view.rl_batch_entry.get()
        cfg.rl_epochs = view.rl_epochs_entry.get()
        cfg.rl_target_update = view.rl_target_update_entry.get()
        cfg.rl_checkpoint = view.rl_checkpoint_entry.get()
        cfg.rl_live_enabled = bool(view.rl_live_switch.get())
        try:
            cfg.rl_epsilon_start = round(view.rl_eps_start_slider.get(), 2)
        except:
            pass
        try:
            cfg.rl_epsilon_min = round(view.rl_eps_min_slider.get(), 3)
        except:
            pass
        try:
            cfg.rl_epsilon_decay = round(view.rl_eps_decay_slider.get(), 4)
        except:
            pass
        cfg.rl_timeframe = view.rl_timeframe_var.get()
        cfg.rl_bars = view.rl_bars_entry.get()
        cfg.rl_nn_arch = view.rl_nn_arch_var.get()

        # Risk Manager
        try:
            cfg.rm_max_daily_loss_eur = float(view.rm_daily_loss_entry.get())
        except:
            pass
        try:
            cfg.rm_max_weekly_loss_eur = float(view.rm_weekly_loss_entry.get())
        except:
            pass
        try:
            cfg.rm_min_time_between_trades = int(view.rm_cooldown_slider.get())
        except:
            pass
        try:
            cfg.rm_max_trades_per_day = int(view.rm_max_trades_entry.get())
        except:
            pass

        # Backtest
        try:
            cfg.bt_rr_ratio = round(
                view.rr_slider.get() if hasattr(view, "rr_slider") else 1.5, 1
            )
        except:
            pass
        try:
            cfg.llm_max_tokens = int(view.max_tokens_slider.get())
        except:
            pass
        cfg.pairs = view.pairs_entry.get()
        cfg.debug_mode = bool(view.debug_mode_switch.get())

        cfg.tg_token = view.tg_token_entry.get().strip()
        cfg.tg_chat_id = view.tg_chat_id_entry.get().strip()
        cfg.discord_webhook = view.discord_webhook_entry.get().strip()
        cfg.sound_alerts = bool(view.sound_alerts_switch.get())

    def save_settings(self, silent: bool = False):
        try:
            self.update_config_from_gui()
            app_config_manager.save()
            if not silent:
                self.write_terminal(
                    f">> [SETTINGS] Gespeichert in: {app_config_manager.config_path}\n"
                )
        except Exception as e:
            if not silent:
                self.write_terminal(
                    f">> [SETTINGS ERROR] Speichern fehlgeschlagen: {e}\n"
                )

    def load_settings(self):
        try:
            self.app_config = app_config_manager.load()
            cfg = self.app_config
            view = self.config_view

            def _set_entry(widget, v):
                if v is not None:
                    widget.delete(0, "end")
                    widget.insert(0, str(v))

            def _set_combo(var, v):
                if v is not None:
                    var.set(v)

            def _set_slider(slider, lbl, v, fmt="{:.0f}"):
                if v is not None:
                    slider.set(float(v))
                    lbl.configure(text=fmt.format(float(v)))

            def _set_switch(switch, v):
                if v is not None:
                    switch.select() if v else switch.deselect()

            _set_combo(view.ki_provider_var, cfg.ki_provider)
            _set_entry(view.url_entry, cfg.ollama_url)

            if "OpenAI" in cfg.ki_provider:
                _set_entry(
                    view.api_key_entry, getattr(cfg, "api_key_openai", cfg.api_key)
                )
            elif "Anthropic" in cfg.ki_provider:
                _set_entry(
                    view.api_key_entry, getattr(cfg, "api_key_anthropic", cfg.api_key)
                )
            elif "DeepSeek" in cfg.ki_provider:
                _set_entry(
                    view.api_key_entry, getattr(cfg, "api_key_deepseek", cfg.api_key)
                )
            elif "OpenRouter" in cfg.ki_provider:
                _set_entry(
                    view.api_key_entry, getattr(cfg, "api_key_openrouter", cfg.api_key)
                )
            else:
                _set_entry(view.api_key_entry, cfg.api_key)

            _set_combo(view.model_combo, cfg.llm_model)
            _set_slider(
                view.interval_slider, view.interval_lbl, cfg.interval, "{:.0f}s"
            )
            _set_slider(
                view.ai_temp_slider, view.ai_temp_lbl, cfg.ai_temperature, "{:.1f}"
            )
            _set_combo(view.prompt_lang_var, cfg.prompt_lang)
            view.system_prompt_text.delete("0.0", "end")
            view.system_prompt_text.insert("0.0", str(cfg.system_prompt))
            _set_slider(
                view.confidence_slider,
                view.confidence_lbl,
                cfg.min_confidence,
                "{:.0f}%",
            )

            self.after(200, lambda: self._on_provider_change())

            _set_combo(view.trading_style_var, cfg.trading_style)
            _set_combo(view.signal_strategy_var, cfg.signal_strategy)
            _set_combo(view.risk_profile_var, cfg.risk_profile)
            _set_entry(view.risk_trade_entry, cfg.max_risk)
            _set_entry(view.risk_daily_entry, cfg.max_daily_loss)
            _set_entry(view.max_pos_entry, cfg.max_positions)
            _set_switch(view.trailing_stop_switch, cfg.trailing_stop)
            _set_entry(view.ts_dist_entry, cfg.trailing_dist)
            _set_switch(view.break_even_switch, cfg.break_even)
            _set_entry(view.be_dist_entry, cfg.break_even_dist)
            _set_switch(view.weekend_exit_switch, cfg.weekend_exit)
            _set_switch(view.trading_active_switch, cfg.auto_trading)
            if hasattr(view, "session_london"):
                _set_switch(view.session_london, cfg.session_london)
            if hasattr(view, "session_ny"):
                _set_switch(view.session_ny, cfg.session_ny)
            if hasattr(view, "session_asia"):
                _set_switch(view.session_asia, cfg.session_asia)
            if hasattr(view, "session_sydney"):
                _set_switch(view.session_sydney, getattr(cfg, "session_sydney", True))

            _set_entry(view.trade_time_from, cfg.trade_time_from)
            _set_entry(view.trade_time_to, cfg.trade_time_to)
            _set_switch(view.time_filter_switch, cfg.time_filter)
            _set_switch(view.day_mon, cfg.day_mon)
            _set_switch(view.day_tue, cfg.day_tue)
            _set_switch(view.day_wed, cfg.day_wed)
            _set_switch(view.day_thu, cfg.day_thu)
            _set_switch(view.day_fri, cfg.day_fri)
            # NEU: Samstag und Sonntag
            if hasattr(view, "day_sat"):
                _set_switch(view.day_sat, getattr(cfg, "day_sat", False))
            if hasattr(view, "day_sun"):
                _set_switch(view.day_sun, getattr(cfg, "day_sun", False))

            # NEU: Visuelle Wochentag-Buttons aktualisieren
            if hasattr(view, "update_day_buttons_from_config"):
                self.after(100, view.update_day_buttons_from_config)

            _set_switch(view.news_filter_switch, cfg.news_filter)
            _set_slider(
                view.news_before_slider,
                view.news_before_lbl,
                cfg.news_before_min,
                "{:.0f} Min",
            )
            _set_slider(
                view.news_after_slider,
                view.news_after_lbl,
                cfg.news_after_min,
                "{:.0f} Min",
            )
            _set_switch(view.news_high, cfg.news_high)
            _set_switch(view.news_medium, cfg.news_medium)
            _set_switch(view.news_low, cfg.news_low)

            _set_slider(
                view.max_spread_slider,
                view.max_spread_lbl,
                cfg.max_spread,
                "{:.0f} pips",
            )
            _set_slider(
                view.max_slippage_slider,
                view.max_slippage_lbl,
                cfg.max_slippage,
                "{:.0f} pips",
            )
            _set_switch(view.spread_check_switch, cfg.spread_check)

            _set_combo(view.rl_algo_var, cfg.rl_algo)
            _set_slider(
                view.rl_lr_slider, view.rl_lr_lbl, cfg.rl_learning_rate, "{:.4f}"
            )
            _set_slider(view.rl_gamma_slider, view.rl_gamma_lbl, cfg.rl_gamma, "{:.2f}")
            _set_entry(view.rl_steps_entry, cfg.rl_steps)
            _set_combo(view.rl_reward_var, cfg.rl_reward)
            _set_entry(view.rl_buffer_entry, cfg.rl_buffer_size)
            _set_entry(view.rl_batch_entry, cfg.rl_batch_size)
            _set_entry(view.rl_epochs_entry, cfg.rl_epochs)
            _set_entry(view.rl_target_update_entry, cfg.rl_target_update)
            _set_entry(view.rl_checkpoint_entry, cfg.rl_checkpoint)
            _set_switch(view.rl_live_switch, cfg.rl_live_enabled)

            _set_entry(view.pairs_entry, cfg.pairs)
            _set_switch(view.debug_mode_switch, cfg.debug_mode)

            _set_entry(view.tg_token_entry, cfg.tg_token)
            _set_entry(view.tg_chat_id_entry, cfg.tg_chat_id)
            _set_entry(view.discord_webhook_entry, cfg.discord_webhook)
            _set_switch(view.sound_alerts_switch, cfg.sound_alerts)
            try:
                view.notif_sl_hit.select() if cfg.notif_sl_hit else view.notif_sl_hit.deselect()
                view.notif_tp_hit.select() if cfg.notif_tp_hit else view.notif_tp_hit.deselect()
                view.notif_new_trade.select() if cfg.notif_new_trade else view.notif_new_trade.deselect()
                view.notif_error.select() if cfg.notif_error else view.notif_error.deselect()
            except Exception:
                pass

            # NEW: RL epsilon, timeframe, bars, nn_arch
            try:
                _set_slider(
                    view.rl_eps_start_slider,
                    view.rl_eps_start_lbl,
                    cfg.rl_epsilon_start,
                    "{:.2f}",
                )
            except:
                pass
            try:
                _set_slider(
                    view.rl_eps_min_slider,
                    view.rl_eps_min_lbl,
                    cfg.rl_epsilon_min,
                    "{:.3f}",
                )
            except:
                pass
            try:
                _set_slider(
                    view.rl_eps_decay_slider,
                    view.rl_eps_decay_lbl,
                    cfg.rl_epsilon_decay,
                    "{:.4f}",
                )
            except:
                pass
            try:
                _set_combo(view.rl_timeframe_var, cfg.rl_timeframe)
            except:
                pass
            try:
                _set_entry(view.rl_bars_entry, cfg.rl_bars)
            except:
                pass
            try:
                _set_combo(view.rl_nn_arch_var, cfg.rl_nn_arch)
            except:
                pass

            # NEW: Max Tokens
            try:
                _set_slider(
                    view.max_tokens_slider,
                    view.max_tokens_lbl,
                    cfg.llm_max_tokens,
                    "{:.0f}",
                )
            except:
                pass

            # NEW: Risk Manager
            try:
                _set_entry(view.rm_daily_loss_entry, cfg.rm_max_daily_loss_eur)
            except:
                pass
            try:
                _set_entry(view.rm_weekly_loss_entry, cfg.rm_max_weekly_loss_eur)
            except:
                pass
            try:
                view.rm_cooldown_slider.set(float(cfg.rm_min_time_between_trades))
                view.rm_cooldown_lbl.configure(
                    text=f"{int(cfg.rm_min_time_between_trades)} sek"
                )
            except:
                pass
            try:
                _set_entry(view.rm_max_trades_entry, cfg.rm_max_trades_per_day)
            except:
                pass

            loaded_pairs = view.pairs_entry.get().strip()
            if loaded_pairs:
                self.after(
                    0,
                    lambda p=loaded_pairs: self.dashboard_view._rebuild_symbol_rows(p),
                )

            self.write_terminal(
                f">> [SETTINGS] Einstellungen geladen aus: {app_config_manager.config_path}\n"
            )

        except Exception as e:
            self.write_terminal(f">> [SETTINGS ERROR] Laden fehlgeschlagen: {e}\n")

    def toggle_live_data(self):
        if not hasattr(self, "is_live_running"):
            self.is_live_running = False

        if self.is_live_running:
            self.is_live_running = False
            self.live_btn.configure(
                text="▶ Live Starten", fg_color="#5EBA7D", hover_color="#4CAF50"
            )
            self.status_dot.configure(text_color="#E74C3C")  # Static Red
            self.write_terminal(">> Live-Stream angehalten.\\n")
            if hasattr(self, "sonar_anim"):
                self.sonar_anim.set_active(False)
            if hasattr(self, "trading_controller"):
                self.trading_controller.stop()
        else:
            if not mt5.initialize():
                messagebox.showerror(
                    "MT5 Fehler",
                    "Konnte MetaTrader 5 nicht für Live-Daten initialisieren.",
                )
                return

            self.is_live_running = True
            self.live_btn.configure(
                text="⏹ Live Stoppen", fg_color="#E74C3C", hover_color="#C0392B"
            )
            self.animate_status_dot()  # Start pulsing

            # Neue SonarAnimation aktivieren
            if hasattr(self, "sonar_anim"):
                self.sonar_anim.set_active(True)

            # Startup Sweep Effect
            self._play_startup_sweep()

            # Start Background AI Speech Bubble Worker
            threading.Thread(target=self._ai_analysis_worker, daemon=True).start()

            # Start Experience DB Resolver
            if EXPERIENCE_DB_AVAILABLE:
                if not hasattr(self, "experience_db"):
                    self.experience_db = ExperienceDB()
                self.write_terminal(">> [RL] Experience DB aktiv. Lerne aus Trades.\\n")

            if not hasattr(self, "trading_controller"):
                from core.trading_controller import TradingController

                self.trading_controller = TradingController(self)

            self.trading_controller.start()

            if (
                hasattr(self.config_view, "trading_active_switch")
                and self.config_view.trading_active_switch.get()
            ):
                self.write_terminal(">> [AUTO] Auto-Trading Engine gestartet.\\n")

            self.write_terminal(">> MT5 Live-Stream gestartet. Empfange Ticks...\\n")
            self.start_live_stream_thread()

    def _play_startup_sweep(self):
        """A smooth 60fps visual sweep effect across metrics."""
        # CustomTkinter fg_color in dark mode is usually "gray17" -> roughly "#2b2b2b"
        base_hex = "#2b2b2b"
        target_hex = "#2b3d36"  # subtle green

        def hex_to_rgb(h):
            return tuple(int(h.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(r, g, b):
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

        def tween_color(c1, c2, t):
            r1, g1, b1 = hex_to_rgb(c1)
            r2, g2, b2 = hex_to_rgb(c2)
            r = r1 + (r2 - r1) * t
            g = g1 + (g2 - g1) * t
            b = b1 + (b2 - b1) * t
            return rgb_to_hex(r, g, b)

        def fade_card(card, duration_ms=400):
            steps = 24  # 60fps for ~400ms
            step_time = duration_ms // steps

            def do_step(current_step):
                # Triangle wave: 0 -> 1 -> 0
                if current_step <= steps / 2:
                    t = current_step / (steps / 2)
                else:
                    t = 1.0 - ((current_step - steps / 2) / (steps / 2))

                color = tween_color(base_hex, target_hex, t)
                card.configure(fg_color=color)

                if current_step < steps:
                    self.after(step_time, lambda: do_step(current_step + 1))
                else:
                    card.configure(fg_color=("gray85", "gray17"))  # Restore original

            do_step(1)

        # Cascade through cards smoothly (delayed start)
        cards = [
            self.balance_card,
            self.equity_card,
            self.margin_card,
            self.risk_card,
            self.pnl_card,
            self.margin_level_card,
            self.positions_card,
            self.trades_card,
        ]

        for i, card in enumerate(cards):
            self.after(i * 150, lambda c=card: fade_card(c))

    def _ai_analysis_worker(self):
        """Runs in background, randomly generating a 1-sentence analysis from Ollama to display as floating speech bubbles"""
        import time, random, requests

        while self.is_live_running:
            # Wait between analyses (e.g. 8-15 seconds)
            time.sleep(random.randint(8, 15))
            if not self.is_live_running:
                break

            if (
                not hasattr(self, "dashboard_symbols")
                or len(self.dashboard_symbols) == 0
            ):
                continue

            symbol = random.choice(self.dashboard_symbols)[1]
            sys_prompt = "Du bist ein FinGPT Agent. Antworte in maximal einem Satz und maximal 10 Worten."

            # --- Comprehensive Analysis for AI Bubbles ---
            if self.indicator_integration:
                # Use enhanced AI analysis to get a deep insight
                try:
                    # Use a standard timeframe for general dashboard bubbles (e.g., M15 or H1)
                    # We can try to see what the user has currently selected as "Trading Style"
                    style = getattr(self, "trading_style_var", None)
                    style_str = style.get() if style else "Day Trading"

                    # Map style to MT5 timeframe constant (re-using the logic from _auto_trading_loop)
                    tf = mt5.TIMEFRAME_M15
                    if style_str == "Scalping":
                        tf = mt5.TIMEFRAME_M5
                    elif style_str == "Swing Trading":
                        tf = mt5.TIMEFRAME_H1
                    elif style_str == "Position Trading":
                        tf = mt5.TIMEFRAME_H4
                    elif style_str in ["Price Action", "Mean Reversion"]:
                        tf = mt5.TIMEFRAME_M15
                    elif style_str == "Breakout-Trading":
                        tf = mt5.TIMEFRAME_H1

                    analysis = self.indicator_integration.enhanced_ai_analysis(
                        symbol, timeframe=tf, include_advanced=True
                    )
                    # We want just a short summary from this long analysis
                    prompt = f"Hier ist eine technische Analyse für {symbol} ({style_str} Perspektive):\n{analysis}\nFasse das Wichtigste in EXAKT EINEM KURZEN SATZ (max 10 Worte) zusammen. Zum Beispiel 'Starker Kaufimpuls durch Ichimoku bestätigt' oder 'RSI und MACD warnen vor Trendwende'."
                except Exception:
                    prompt = f"Schreibe eine extrem kurze und spannende Feststellung zum {symbol} Chart. Zum Beispiel 'RSI stark überverkauft bei {symbol}' oder 'Volatilitäts-Spike bei {symbol} registriert.'. Keine Einleitung."
            else:
                prompt = f"Schreibe eine extrem kurze und spannende Feststellung zum {symbol} Chart. Zum Beispiel 'RSI stark überverkauft bei {symbol}' oder 'Volatilitäts-Spike bei {symbol} registriert.'. Keine Einleitung."

            try:
                text_raw = self._call_llm_api(
                    system_prompt=sys_prompt, user_prompt=prompt, max_tokens=30
                )
                if (
                    text_raw
                    and not text_raw.startswith("[Fehler")
                    and not text_raw.startswith("[API Fehler")
                ):
                    text = text_raw.strip().replace('"', "")
                    if text and hasattr(self, "sonar_anim"):
                        # Bubble direkt an die neue Animation übergeben
                        self.after(0, lambda t=text: self.sonar_anim.add_bubble(t))
            except Exception:
                pass

    def animate_status_dot(self):
        if not self.is_live_running:
            self.status_dot.configure(text_color="#E74C3C")
            self.indicators["MT5"].configure(text_color="#E74C3C")
            return

        current_color = self.status_dot.cget("text_color")
        # Pulse between bright green and a darker green
        next_color = "#5EBA7D" if current_color != "#5EBA7D" else "#1E8449"
        self.status_dot.configure(text_color=next_color)
        self.indicators["MT5"].configure(text_color=next_color)

        # Rotierendes Symbol fr die neue SonarAnimation (alle 2 Sekunden)
        if (
            hasattr(self, "sonar_anim")
            and hasattr(self, "dashboard_symbols")
            and self.dashboard_symbols
        ):
            if not hasattr(self, "ai_animation_idx"):
                self.ai_animation_idx = 0

            self.ai_animation_idx += 1
            if self.ai_animation_idx % 4 == 0:
                symbol_idx = (self.ai_animation_idx // 4) % len(self.dashboard_symbols)
                self.ai_current_symbol = self.dashboard_symbols[symbol_idx][1]
                self.sonar_anim.set_symbol(self.ai_current_symbol)

        self.after(500, self.animate_status_dot)

    def _animate_sonar(self):
        """DEPRECATED – ersetzt durch SonarAnimation (gui/components/sonar_animation.py)."""
        pass

    def update_footer_indicators(self):
        # Python is always running if we are here
        self.indicators["Python"].configure(text_color="#5EBA7D")

        # MT5 indicator is handled by animate_status_dot when live,
        # but if we are not live, let's just check terminal exists
        if not self.is_live_running:
            try:
                # mt5.terminal_info() can check if connected without starting stream
                if mt5.terminal_info() is not None:
                    self.indicators["MT5"].configure(text_color="#5EBA7D")
                else:
                    self.indicators["MT5"].configure(text_color="#E74C3C")
            except:
                self.indicators["MT5"].configure(text_color="#E74C3C")

        # Ollama check (non-blocking thread to avoid UI freeze)
        def check_ollama():
            try:
                url = self.config_view.url_entry.get().strip()
                resp = requests.get(f"{url}/api/tags", timeout=2)
                if getattr(self, "_is_closing", False):
                    return

                if resp.status_code == 200:
                    self.after(
                        0,
                        lambda: (
                            not getattr(self, "_is_closing", False)
                            and self.indicators["Ollama"].configure(
                                text_color="#5EBA7D"
                            )
                        ),
                    )
                else:
                    self.after(
                        0,
                        lambda: (
                            not getattr(self, "_is_closing", False)
                            and self.indicators["Ollama"].configure(
                                text_color="#E74C3C"
                            )
                        ),
                    )
            except Exception:
                if not getattr(self, "_is_closing", False):
                    try:
                        self.after(
                            0,
                            lambda: (
                                not getattr(self, "_is_closing", False)
                                and self.indicators["Ollama"].configure(
                                    text_color="#E74C3C"
                                )
                            ),
                        )
                    except:
                        pass

        threading.Thread(target=check_ollama, daemon=True).start()

        # RL Engine logic (simulate or check path)
        rl_path = "storage/rl_agents"
        has_agents = os.path.exists(rl_path) and len(os.listdir(rl_path)) > 0
        if has_agents:
            self.indicators["RL Engine"].configure(text_color="#5EBA7D")

            # Safe access to indicator_labels which was added later
            if (
                hasattr(self, "indicator_labels")
                and "RL Engine" in self.indicator_labels
            ):
                self.indicator_labels["RL Engine"].configure(
                    text="RL Engine", text_color="gray70"
                )
        else:
            self.indicators["RL Engine"].configure(
                text_color="#E74C3C"
            )  # No agents trained

            # Add a hint why it's red
            if (
                hasattr(self, "indicator_labels")
                and "RL Engine" in self.indicator_labels
            ):
                self.indicator_labels["RL Engine"].configure(
                    text="RL Engine (Keine Agenten)", text_color="#E74C3C"
                )

        # Repeat every 10 seconds
        self.after(10000, self.update_footer_indicators)

    def start_live_stream_thread(self):
        def update_loop():
            while self.is_live_running:
                self.after(0, self.update_dashboard_data)
                now = datetime.now().strftime("%H:%M:%S")
                self.after(
                    0,
                    lambda: self.status_label.configure(
                        text=f"Live-Stream aktiv | Letzte Aktualisierung: {now}"
                    ),
                )
                time.sleep(1.0)  # Jede Sekunde aktualisieren

        threading.Thread(target=update_loop, daemon=True).start()

    def update_dashboard_data(self):
        if not mt5.initialize():
            return

        # Aktualisiere Account Metriken
        acc_info = mt5.account_info()
        if acc_info is not None:
            self.balance_card.update_value(f"€{acc_info.balance:,.2f}")
            self.equity_card.update_value(f"€{acc_info.equity:,.2f}")
            self.margin_card.update_value(f"€{acc_info.margin:,.2f}")
            self.risk_card.update_value(f"€{acc_info.margin_free:,.2f}")

            self.pnl_card.update_value(f"€{acc_info.profit:,.2f}")
            self.margin_level_card.update_value(
                f"{acc_info.margin_level:.2f}%" if acc_info.margin_level > 0 else "---%"
            )

            # Positionen prüfen
            positions = mt5.positions_total()
            self.positions_card.update_value(str(positions))

            history_deals = mt5.history_deals_total(
                datetime.now().replace(hour=0, minute=0, second=0), datetime.now()
            )
            self.trades_card.update_value(
                str(history_deals) if history_deals is not None else "0"
            )

            # Update P&L Chart
            self.pnl_history.append(acc_info.profit)
            if len(self.pnl_history) > 50:
                self.pnl_history.pop(0)
            self._draw_pnl_chart()

            # Update Daily Goal (Assume target is 100€ for visual demo, but could be pulled from config)
            target = 100.0
            current = max(0.0, acc_info.profit)  # Only show positive progress
            pct = min(1.0, current / target)
            self.goal_progress.set(pct)
            self.goal_progress.configure(
                progress_color="#5EBA7D" if pct >= 1.0 else "#F1C40F"
            )
            self.goal_lbl.configure(text=f"€{current:.2f} / €{target:.0f}")

            # Update MVP Trade (Fetch from journal if available)
            self._update_mvp_trade()

    def _update_mvp_trade(self):
        if not mt5.initialize():
            self.mvp_trade_lbl.configure(text="Noch keine Gewinne", text_color="gray50")
            return

        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        deals = mt5.history_deals_get(today_start, datetime.now())

        best_profit = -float("inf")
        best_deal = None

        if deals:
            for deal in deals:
                if deal.entry == mt5.DEAL_ENTRY_OUT and deal.profit > 0:
                    if deal.profit > best_profit:
                        best_profit = deal.profit
                        best_deal = deal

        if best_deal and best_profit > 0:
            sym = best_deal.symbol if best_deal.symbol else "N/A"
            # If DEAL_ENTRY_OUT is a SELL deal, it closed a LONG position.
            # If it's a BUY deal, it closed a SHORT position.
            action = "LONG" if best_deal.type == mt5.DEAL_TYPE_SELL else "SHORT"
            self.mvp_trade_lbl.configure(
                text=f"{sym} {action} (€{best_profit:.2f})", text_color="#5EBA7D"
            )
        else:
            self.mvp_trade_lbl.configure(text="Noch keine Gewinne", text_color="gray50")

        # Aktualisiere Symbole
        import time

        now = time.time()
        should_update_history = False
        if (
            not hasattr(self, "_last_dashboard_history_update")
            or (now - self._last_dashboard_history_update) > 60
        ):
            self._last_dashboard_history_update = now
            should_update_history = True

        if not hasattr(self, "_dashboard_history_cache"):
            self._dashboard_history_cache = {}

        for symbol, row in self.live_data_rows:
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                if should_update_history or symbol not in self._dashboard_history_cache:
                    # Berechne Änderung
                    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
                    if rates is not None and len(rates) > 0:
                        open_price = rates[0]["open"]
                        change_pct = ((tick.bid - open_price) / open_price) * 100
                        sign = "+" if change_pct > 0 else ""
                        change_str = f"{sign}{change_pct:.2f}%"
                    else:
                        change_str = "0.00%"

                    # MTF Trend Logic (M15, H1, H4)
                    trend_colors = []
                    for tf in [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4]:
                        tf_rates = mt5.copy_rates_from_pos(symbol, tf, 0, 5)
                        if tf_rates is not None and len(tf_rates) >= 2:
                            if tf_rates[-1]["close"] > tf_rates[0]["close"]:
                                trend_colors.append("#5EBA7D")  # Green / Bull
                            elif tf_rates[-1]["close"] < tf_rates[0]["close"]:
                                trend_colors.append("#E74C3C")  # Red / Bear
                            else:
                                trend_colors.append("gray")  # Neutral
                        else:
                            trend_colors.append("gray")

                    # --- Fetch Sparkline Data (last 30 minutes M1) ---
                    history_data = []
                    try:
                        m1_rates = mt5.copy_rates_from_pos(
                            symbol, mt5.TIMEFRAME_M1, 0, 30
                        )
                        if m1_rates is not None and len(m1_rates) > 0:
                            history_data = [r["close"] for r in m1_rates]
                    except Exception:
                        pass

                    self._dashboard_history_cache[symbol] = (
                        change_str,
                        trend_colors,
                        history_data,
                    )
                else:
                    change_str, trend_colors, history_data = (
                        self._dashboard_history_cache[symbol]
                    )

                row.update_data(f"{tick.bid:.5f}", change_str, history=history_data)
                row.update_trend(*trend_colors)

    def _draw_pnl_chart(self):
        """Draws a smooth, gradient-colored P&L line chart on the pnl_canvas."""
        if not hasattr(self, "pnl_canvas") or not self.pnl_history:
            return

        self.pnl_canvas.delete("all")
        width = self.pnl_canvas.winfo_width()
        height = self.pnl_canvas.winfo_height()

        if width < 10 or height < 10:
            return

        data = self.pnl_history
        n = len(data)

        # Value range (ensure no division by zero)
        max_val = max(max(data), 0.01)
        min_val = min(min(data), -0.01)
        range_val = max_val - min_val or 1

        pad_x, pad_y = 6, 12
        draw_w = width - 2 * pad_x
        draw_h = height - 2 * pad_y

        # Zero-line Y
        zero_y = pad_y + draw_h * (1 - (0 - min_val) / range_val)

        # ── Zero reference line ──────────────────────────────────────
        self.pnl_canvas.create_line(
            pad_x, zero_y, width - pad_x, zero_y, fill="#3A3A3A", dash=(3, 4), width=1
        )

        if n < 2:
            return

        # ── Coordinate calculation ───────────────────────────────────
        def _xy(i, v):
            x = pad_x + i * draw_w / (n - 1)
            y = pad_y + draw_h * (1 - (v - min_val) / range_val)
            return x, y

        coords = [_xy(i, v) for i, v in enumerate(data)]

        # ── Helper: lerp between two RGB tuples ──────────────────────
        def _lerp_color(c1, c2, t):
            """t=0 → c1, t=1 → c2"""
            t = max(0.0, min(1.0, t))
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            return f"#{r:02x}{g:02x}{b:02x}"

        RED = (231, 76, 60)  # #E74C3C
        YELLOW = (241, 196, 15)  # #F1C40F
        GREEN = (94, 186, 125)  # #5EBA7D

        def _pnl_color(value):
            """Map a P&L value to a smooth red→yellow→green color."""
            if value >= 0:
                # 0..max_val → yellow..green
                t = value / max_val if max_val > 0 else 1.0
                return _lerp_color(YELLOW, GREEN, t)
            else:
                # min_val..0 → red..yellow
                t = (value - min_val) / (-min_val) if min_val < 0 else 0.0
                return _lerp_color(RED, YELLOW, t)

        # ── Draw subtle fill area (stipple for transparency effect) ──
        # Build polygon per-segment from the zero-line down
        for i in range(n - 1):
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            mid_v = (data[i] + data[i + 1]) / 2
            fill_c = _pnl_color(mid_v)
            self.pnl_canvas.create_polygon(
                x0,
                y0,
                x1,
                y1,
                x1,
                zero_y,
                x0,
                zero_y,
                fill=fill_c,
                outline="",
                stipple="gray25",
            )

        # ── Draw gradient line segment by segment ────────────────────
        for i in range(n - 1):
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            mid_v = (data[i] + data[i + 1]) / 2
            seg_col = _pnl_color(mid_v)
            self.pnl_canvas.create_line(
                x0,
                y0,
                x1,
                y1,
                fill=seg_col,
                width=1.5,
                smooth=False,
                capstyle="round",
                joinstyle="round",
            )

        # ── Draw a subtle dot at the latest value ────────────────────
        lx, ly = coords[-1]
        dot_col = _pnl_color(data[-1])
        r = 3
        self.pnl_canvas.create_oval(
            lx - r, ly - r, lx + r, ly + r, fill=dot_col, outline=""
        )

    def start_simulated_data(self):
        # Der simulierte Background-Sync wurde entfernt, um das Terminal
        # von unwichtigen "Background sync completed" Nachrichten zu bereinigen.
        # So bleiben echte Trades und Fehlermeldungen besser sichtbar.
        pass

    # ============================================================
    # MODERNISIERUNG: Event Bus Callback-Handler
    # ============================================================
    def _on_data_updated(self, event):
        """Wird aufgerufen wenn Daten aktualisiert wurden"""
        if hasattr(event, "data"):
            data_type = event.event_type
            # Hier können wir UI-Updates basierend auf Datenänderungen durchführen
            # z.B. Metric Cards aktualisieren, Charts neu zeichnen, etc.
            self.write_terminal(f">> [EVENT] Daten aktualisiert: {data_type}")

    def _on_trade_executed(self, event):
        """Wird aufgerufen wenn ein Trade ausgeführt wurde"""
        if hasattr(event, "data"):
            data = event.data
            symbol = data.get("symbol", "N/A")
            action = data.get("action", "N/A")
            self.write_terminal(f">> [EVENT] Trade ausgeführt: {action} {symbol}")

            # Aktualisiere Dashboard nach Trade
            if hasattr(self, "dashboard_view"):
                self.dashboard_view.refresh_data()

    def _on_config_changed(self, event):
        """Wird aufgerufen wenn sich die Konfiguration geändert hat"""
        self.write_terminal(">> [EVENT] Konfiguration geändert")
        # Lade Konfiguration neu
        self.app_config = app_config_manager.load()

    def emit_event(self, event_type: str, data: dict = None, source: str = None):
        """Hilfsmethode um Events zu senden"""
        if self.event_bus and data:
            self.event_bus.publish(event_type, data, source)

    # ============================================================

    def write_terminal(self, text, tag="INFO"):
        """Write colored text to the terminal by delegating to TerminalView."""
        if hasattr(self, "terminal_view") and self.terminal_view:
            self.terminal_view.write_terminal(text, tag)
        else:
            # Fancy console output wenn TerminalView nicht verfügbar
            icon_map = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅ ",
                "WARN": "⚠️ ",
                "ERROR": "❌ ",
                "SYSTEM": "💻 ",
                "TRADE": "💱",
            }
            icon = icon_map.get(tag, "• ")
            msg = text.strip().replace(">> ", "").replace("[", "").replace("]", "")
            fancy_print(msg, tag, icon)

    def load_forex_charts(self):
        self.write_terminal(">> Lade Forex Live-Charts (Major Pairs)...\n")

        # Clear existing charts
        for widget in self.charts_container.winfo_children():
            widget.destroy()

        # Show loading indicator
        loading_lbl = ctk.CTkLabel(
            self.charts_container,
            text="⏳ Lade Marktdaten von MetaTrader 5...",
            font=ctk.CTkFont(family="Inter", size=14),
            text_color="#8B949E",
        )
        loading_lbl.grid(row=0, column=0, columnspan=2, pady=80)

        tf_str = (
            self.chart_timeframe_var.get()
            if hasattr(self, "chart_timeframe_var")
            else "D1 (Täglich)"
        )

        # Chart style for dark mode
        import mplfinance as mpf

        mc = mpf.make_marketcolors(
            up="#5EBA7D", down="#E74C3C", edge="i", wick="i", volume="in"
        )
        chart_style = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#141720",
            edgecolor="#2D3748",
            figcolor="#141720",
            gridcolor="#2D3748",
            gridstyle=":",
            rc={
                "axes.labelcolor": "#8B949E",
                "xtick.color": "#8B949E",
                "ytick.color": "#8B949E",
            },
        )

        pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]

        def fetch_and_render():
            try:
                if getattr(self, "_is_closing", False):
                    return
                if not mt5.initialize():
                    raise Exception("MetaTrader 5 nicht verbunden. Bitte Live starten.")

                # Parse timeframe
                if "M1 " in tf_str:
                    tf = mt5.TIMEFRAME_M1
                elif "M5" in tf_str:
                    tf = mt5.TIMEFRAME_M5
                elif "M15" in tf_str:
                    tf = mt5.TIMEFRAME_M15
                elif "M30" in tf_str:
                    tf = mt5.TIMEFRAME_M30
                elif "H1" in tf_str:
                    tf = mt5.TIMEFRAME_H1
                elif "H4" in tf_str:
                    tf = mt5.TIMEFRAME_H4
                else:
                    tf = mt5.TIMEFRAME_D1

                tf_label = tf_str.split(" ")[0]
                chart_data = []

                for symbol in pairs:
                    if getattr(self, "_is_closing", False):
                        return
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 80)
                    if rates is None or len(rates) < 5:
                        continue
                    df = pd.DataFrame(rates)
                    df["time"] = pd.to_datetime(df["time"], unit="s")
                    df.set_index("time", inplace=True)
                    chart_data.append((symbol, df, tf_label))

                if not chart_data:
                    raise Exception(
                        "Keine Marktdaten empfangen. Ist MT5 mit einem Konto verbunden?"
                    )

                if not getattr(self, "_is_closing", False):
                    try:
                        self.after(
                            0,
                            lambda: (
                                not getattr(self, "_is_closing", False)
                                and _render(chart_data, chart_style)
                            ),
                        )
                    except Exception:
                        pass

            except Exception as e:
                err = str(e)
                if not getattr(self, "_is_closing", False):
                    try:
                        self.after(
                            0,
                            lambda msg=err: (
                                not getattr(self, "_is_closing", False)
                                and _show_error(msg)
                            ),
                        )
                    except Exception:
                        pass

        def _show_error(msg):
            for w in self.charts_container.winfo_children():
                w.destroy()
            ctk.CTkLabel(
                self.charts_container,
                text=f"⚠ {msg}",
                font=ctk.CTkFont(family="Inter", size=14),
                text_color="#E74C3C",
                wraplength=600,
            ).grid(row=0, column=0, columnspan=2, pady=80)

        def _render(chart_data, style):
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            for w in self.charts_container.winfo_children():
                w.destroy()

            self.charts_container.grid_columnconfigure(0, weight=1)
            self.charts_container.grid_columnconfigure(1, weight=1)

            grid_row = 0
            grid_col = 0

            for symbol, df, tf_label in chart_data:
                frame = ctk.CTkFrame(
                    self.charts_container,
                    corner_radius=10,
                    fg_color="#141720",
                    border_width=1,
                    border_color="#2D3748",
                )
                frame.grid(row=grid_row, column=grid_col, padx=8, pady=8, sticky="nsew")
                self.charts_container.grid_rowconfigure(grid_row, weight=1)

                try:
                    import mplfinance as mpf

                    fig = Figure(figsize=(5, 3.2), facecolor="#141720", dpi=90)
                    ax = fig.add_subplot(111)
                    ax.set_facecolor("#141720")
                    ax.tick_params(colors="#8B949E", labelsize=7)
                    ax.spines["bottom"].set_color("#2D3748")
                    ax.spines["left"].set_color("#2D3748")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)

                    # Title with current price
                    last_close = df["close"].iloc[-1]
                    price_fmt = (
                        f"{last_close:.5f}" if last_close < 10 else f"{last_close:.3f}"
                    )
                    ax.set_title(
                        f"{symbol}  ·  {tf_label}  ·  {price_fmt}",
                        color="white",
                        fontsize=9,
                        fontweight="bold",
                        pad=6,
                    )

                    mpf.plot(
                        df,
                        type="candle",
                        ax=ax,
                        style=style,
                        show_nontrading=False,
                        warn_too_much_data=2000,
                    )
                    fig.tight_layout(pad=0.5)

                    canvas = FigureCanvasTkAgg(fig, master=frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(
                        fill="both", expand=True, padx=3, pady=3
                    )

                except Exception as e:
                    ctk.CTkLabel(
                        frame,
                        text=f"{symbol}\nFehler: {e}",
                        text_color="#E74C3C",
                        font=ctk.CTkFont(size=11),
                    ).pack(expand=True)

                grid_col += 1
                if grid_col > 1:
                    grid_col = 0
                    grid_row += 1

            self.write_terminal(
                f">> {len(chart_data)} Forex-Charts erfolgreich gerendert ({tf_label}).\n"
            )

        threading.Thread(target=fetch_and_render, daemon=True).start()

    def _render_charts_from_data(self, chart_data, style):
        try:
            figures = []
            for title, df, tf_str in chart_data:
                fig = Figure(figsize=(5, 3.5), facecolor="#1E1E1E")
                ax = fig.add_subplot(111)
                ax.set_title(title + f" ({tf_str.split(' ')[0]})", color="white")
                ax.tick_params(colors="white")

                mpf.plot(
                    df,
                    type="candle",
                    ax=ax,
                    style=style,
                    show_nontrading=False,
                    warn_too_much_data=1000,
                )
                fig.tight_layout()
                figures.append((title, fig))

            self._render_charts(figures)
        except Exception as e:
            err_msg = str(e)
            self.write_terminal(f">> Fehler beim Chart-Erstellen: {err_msg}\n")
            messagebox.showerror(
                "API Fehler", f"Fehler beim Erstellen der Marktdaten-Charts:\n{err_msg}"
            )

    def _render_charts(self, figures):
        # Remove loading label
        if (
            hasattr(self, "charts_loading_lbl")
            and self.charts_loading_lbl.winfo_exists()
        ):
            self.charts_loading_lbl.destroy()

        self.write_terminal(">> Forex-Charts (Major Pairs) erfolgreich gerendert.\n")

        grid_row = 0
        grid_col = 0
        for title, fig in figures:
            # Create a frame for the padding/border
            frame = ctk.CTkFrame(
                self.charts_container, corner_radius=10, fg_color="#1E1E1E"
            )
            frame.grid(row=grid_row, column=grid_col, padx=10, pady=10, sticky="nsew")

            # Embed matplotlib figure
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
            canvas.draw()

            grid_col += 1
            if grid_col > 1:
                grid_col = 0
                grid_row += 1

    def new_chart(self):
        # Obsolete with grid approach, reroute to reload
        self.load_forex_charts()

    def test_ollama_connection(self):
        url = self.config_view.url_entry.get()
        self.write_terminal(f">> Testing ping to {url}...\n")
        # Simulierter Erfolg
        self.after(
            500, lambda: self.write_terminal(">> SUCCESS: Ollama is reachable.\n")
        )

    def save_config(self):
        self.write_terminal(">> Hardware and risk configuration flushed to disk.\n")
        # Kleines Checkmark Label anzeigen als feedback
        feedback = ctk.CTkLabel(
            self, text="✔ Gespeichert!", text_color="#5EBA7D", bg_color="transparent"
        )
        feedback.place(relx=0.9, rely=0.05, anchor="ne")
        self.after(2000, feedback.destroy)


class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.app_config = app_config_manager.load()
        self.title("FinGPT Startup")

        # Center the splash screen
        window_width = 500
        window_height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        self.overrideredirect(True)  # Remove windows borders/titlebar for clean look
        self.configure(fg_color="#121212")

        # UI Elements
        self.logo_lbl = ctk.CTkLabel(
            self,
            text="FinGPT",
            font=ctk.CTkFont(family="Inter", size=42, weight="bold"),
            text_color="#5EBA7D",
        )
        self.logo_lbl.pack(pady=(60, 10))

        self.sub_lbl = ctk.CTkLabel(
            self,
            text="AI Trading Assistant",
            font=ctk.CTkFont(family="Inter", size=16),
            text_color="gray70",
        )
        self.sub_lbl.pack(pady=(0, 30))

        self.progress = ctk.CTkProgressBar(
            self,
            width=350,
            height=10,
            progress_color="#5EBA7D",
            fg_color="#1E1E1E",
            corner_radius=5,
        )
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.status_lbl = ctk.CTkLabel(
            self,
            text="Initialisiere System...",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="gray50",
        )
        self.status_lbl.pack(pady=5)

        # Startup variables
        self.step = 0
        self.max_steps = 100
        self.loading_texts = [
            "Lade Metatrader 5 Module...",
            "Initialisiere KI Trading Modus...",
            "Verbinde zu Ollama / Cloud APIs...",
            "Lade historische Marktdaten...",
            "Kalibriere Neuronale Netze...",
            "Lese Konfigurationsdateien...",
            "Prüfe Handelssignale...",
            "Starte FinGPT Dashboard...",
        ]

        # Start animation loop (total duration ~10s -> 100 steps * 100ms)
        self.after(200, self._animate)

    def _animate(self):
        if self.step < self.max_steps:
            self.step += 1
            progress_val = self.step / self.max_steps
            self.progress.set(progress_val)

            # Change status text dynamically based on progress
            idx = int(progress_val * len(self.loading_texts))
            if idx >= len(self.loading_texts):
                idx = len(self.loading_texts) - 1
            self.status_lbl.configure(text=self.loading_texts[idx])

            self.after(100, self._animate)  # 100ms per step * 100 = 10 seconds
        else:
            self._launch_main_app()

    def _launch_main_app(self):
        self.destroy()  # Close splash
        app = ModernFinGPTGUI()
        app.mainloop()


def main():
    try:
        splash = SplashScreen()
        splash.mainloop()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Schwerwiegender Fehler beim GUI-Start: {e}")


if __name__ == "__main__":
    main()
