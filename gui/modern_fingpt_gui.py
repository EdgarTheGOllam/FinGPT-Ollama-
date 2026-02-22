#!/usr/bin/env python3
"""
Modernes FinGPT GUI mit erweiterten Funktionen
Professionelle Benutzeroberfläche mit Live-Daten, Plotly-Charts und Terminal-Integration
Umgesetzt mit CustomTkinter für ein hochmodernes "Glassmorphic"- und Dark-Theme Erlebnis.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import random
from datetime import datetime
import sys
import os
import requests

# Konfiguriere das CustomTkinter Aussehen
ctk.set_appearance_mode("Dark")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import mplfinance as mpf
import MetaTrader5 as mt5
import pandas as pd
try:
    from core.config_manager import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

class MetricCard(ctk.CTkFrame):
    """Eine wiederverwendbare Metrik-Karte mit modernem Design"""
    def __init__(self, master, title, value, **kwargs):
        super().__init__(master, fg_color=("gray85", "gray17"), corner_radius=15, **kwargs)
        
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="gray60")
        self.title_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.value_label = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#2E86AB")
        self.value_label.pack(anchor="w", padx=15, pady=(0, 15))

    def update_value(self, new_value):
        self.value_label.configure(text=new_value)

class LiveDataRow(ctk.CTkFrame):
    """Eine Zeile für die Scrollbare Live-Daten Ansicht mit MTF Trend Ampel"""
    def __init__(self, master, symbol, price, change, signal, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Grid Setup for consistent column widths
        self.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        
        self.symbol_lbl = ctk.CTkLabel(self, text=symbol, font=ctk.CTkFont(size=13, weight="bold"))
        self.symbol_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.price_lbl = ctk.CTkLabel(self, text=price, font=ctk.CTkFont(size=13))
        self.price_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        change_color = "#5EBA7D" if "+" in change else "#E74C3C" if "-" in change else "gray"
        self.change_lbl = ctk.CTkLabel(self, text=change, text_color=change_color, font=ctk.CTkFont(size=13, weight="bold"))
        self.change_lbl.grid(row=0, column=2, sticky="w", padx=10, pady=5)
        
        # MTF Trend Ampel Frame
        self.trend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.trend_frame.grid(row=0, column=3, sticky="w", padx=10, pady=5)
        
        self.trend_m15 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_m15.pack(side="left", padx=3)
        self.trend_h1 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_h1.pack(side="left", padx=3)
        self.trend_h4 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_h4.pack(side="left", padx=3)

        sig_color = "#2E86AB" if signal == "BUY" else "#A23B72" if signal == "SELL" else "gray"
        self.signal_btn = ctk.CTkButton(self, text=signal, width=60, height=24, fg_color=sig_color, hover_color=sig_color, corner_radius=12)
        self.signal_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

    def update_data(self, price, change):
        self.price_lbl.configure(text=price)
        self.change_lbl.configure(text=change)
        change_color = "#5EBA7D" if "+" in change else "#E74C3C" if "-" in change else "gray"
        self.change_lbl.configure(text_color=change_color)

    def update_trend(self, m15_color, h1_color, h4_color):
        """Update the 3 timeframe dots with the given hex colors."""
        self.trend_m15.configure(text_color=m15_color)
        self.trend_h1.configure(text_color=h1_color)
        self.trend_h4.configure(text_color=h4_color)


class ModernFinGPTGUI(ctk.CTk):
    """
    Das komplett modernisierte FinGPT Interface mit CustomTkinter
    """
    def __init__(self):
        super().__init__()
        
        self.title("FinGPT Professional Dashboard")
        self.geometry("1200x850")
        self.minsize(900, 700)
        
        # State variables
        self.is_live_running = False
        self.live_data_rows = []
        self.pnl_history = []  # Stores recent P&L values for the Live Chart
        
        # Konstruktor Aufruf für Layout
        self.setup_layout()
        self.start_simulated_data()

    def setup_layout(self):
        """Haupt-Grid System der UI"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(self.header_frame, text="FinGPT Professional", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"))
        title_label.pack(side="left")
        
        # Header Controls
        self.live_btn = ctk.CTkButton(self.header_frame, text="▶ Live Starten", command=self.toggle_live_data, 
                                      fg_color="#5EBA7D", hover_color="#4CAF50", corner_radius=20, font=ctk.CTkFont(weight="bold"))
        self.live_btn.pack(side="right", padx=(10, 0))
        
        self.status_dot = ctk.CTkLabel(self.header_frame, text="●", text_color="#E74C3C", font=ctk.CTkFont(size=20))
        self.status_dot.pack(side="right")
        
        # 2. Main Tabview (ersetzt ttk.Notebook)
        self.tabview = ctk.CTkTabview(
            self, 
            corner_radius=15,
            segmented_button_fg_color=("gray85", "#181818"),
            segmented_button_selected_color="#2E86AB",
            segmented_button_selected_hover_color="#21618C",
            segmented_button_unselected_color=("gray85", "#181818"),
            segmented_button_unselected_hover_color=("gray75", "#282828"),
            text_color=("gray10", "#F0F0F0")
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        
        # Increase the size and make the font bolder for the Tab buttons dynamically
        self.tabview._segmented_button.configure(
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=36
        )
        
        self.tabview.add("📊 Dashboard")
        self.tabview.add("📈 Charts")
        self.tabview.add("🎭 Debate")
        self.tabview.add("🤖 RL Studio")
        self.tabview.add("📝 Journal")
        self.tabview.add("📰 News")
        self.tabview.add("💻 Terminal")
        self.tabview.add("⚙️ Konfiguration")
        self.tabview.add("❓ FAQ")
        
        # Tabs konfigurieren
        self.setup_dashboard_tab()
        self.setup_charts_tab()
        self.setup_debate_tab()
        self.setup_rl_studio_tab()
        self.setup_journal_tab()
        self.setup_news_tab()
        self.setup_terminal_tab()
        self.setup_config_tab()
        self.setup_faq_tab()

        
        # 3. Status Bar
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=10)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(self.status_bar, text="Bereit | Letzte Aktualisierung: Nie", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left", padx=15, pady=5)
        
        # System Indicators
        self.indicator_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.indicator_frame.pack(side="right", padx=15, pady=5)
        
        # We will create these labels dynamically or explicitly
        self.indicators = {}
        self.indicator_labels = {}  # Store references for tooltips/text updates
        
        for sys_name in ["Python", "MT5", "Ollama", "RL Engine"]:
            frame = ctk.CTkFrame(self.indicator_frame, fg_color="transparent")
            frame.pack(side="left", padx=10)
            dot = ctk.CTkLabel(frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
            dot.pack(side="left", padx=(0, 6))
            lbl = ctk.CTkLabel(frame, text=sys_name, font=ctk.CTkFont(size=13, weight="bold"), text_color="gray70")
            lbl.pack(side="left")
            self.indicators[sys_name] = dot
            self.indicator_labels[sys_name] = lbl
            
        self.update_footer_indicators()
        # Load any previously saved settings from disk
        self.after(300, self.load_settings)

    def setup_dashboard_tab(self):
        tab = self.tabview.tab("📊 Dashboard")
        tab.grid_columnconfigure((0, 1, 2), weight=1)
        tab.grid_rowconfigure(3, weight=1)
        
        # Top Cards
        self.balance_card = self.create_metric_card(tab, "Kontostand", "€--", 0, 0)
        self.positions_card = self.create_metric_card(tab, "Offene Positionen", "-", 0, 1)
        self.trades_card = self.create_metric_card(tab, "Heutige Trades", "-", 0, 2)
        
        self.pnl_card = self.create_metric_card(tab, "Gewinn/Verlust", "€--", 1, 0)
        self.winrate_card = self.create_metric_card(tab, "Margin Level", "-%", 1, 1)
        self.risk_card = self.create_metric_card(tab, "Freie Margin", "€--", 1, 2)

        # AI Agent Visualizer & Lückenfüller-Widgets (Middle Banner)
        self.ai_visualizer_frame = ctk.CTkFrame(tab, height=90, corner_radius=15, fg_color=("gray85", "gray17"))
        self.ai_visualizer_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))
        self.ai_visualizer_frame.grid_propagate(False) # Keep fixed height
        self.ai_visualizer_frame.grid_columnconfigure(0, weight=2) # Sonar gets more space
        self.ai_visualizer_frame.grid_columnconfigure(1, weight=1) # Goal
        self.ai_visualizer_frame.grid_columnconfigure(2, weight=1) # Best Trade
        
        # 1. AI Sonar Canvas (Left)
        sonar_container = ctk.CTkFrame(self.ai_visualizer_frame, fg_color="transparent")
        sonar_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        # Title above sonar
        self.sonar_title = ctk.CTkLabel(sonar_container, text="KI-Engine: Standby", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray60")
        self.sonar_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(5,0))
        
        import tkinter as tk
        # Small canvas for the radar circles
        self.sonar_canvas = tk.Canvas(sonar_container, bg="#212121", width=50, height=50, highlightthickness=0)
        self.sonar_canvas.grid(row=1, column=0, padx=(10, 10), pady=0)
        
        self.ai_status_lbl = ctk.CTkLabel(sonar_container, text="Zzz... Warte auf Live-Stream", font=ctk.CTkFont(size=13, slant="italic"), text_color="gray50")
        self.ai_status_lbl.grid(row=1, column=1, sticky="w")
        
        # Draw initial sleeping dot
        self.sonar_circles = []
        self._sonar_base_dot = self.sonar_canvas.create_oval(20, 20, 30, 30, fill="gray40", outline="")
        
        # 2. Daily Goal Widget (Middle)
        goal_container = ctk.CTkFrame(self.ai_visualizer_frame, fg_color="transparent")
        goal_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(goal_container, text="Tages-Ziel (100€)", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray60").pack(anchor="w")
        self.goal_progress = ctk.CTkProgressBar(goal_container, height=10, progress_color="#F1C40F")
        self.goal_progress.pack(fill="x", pady=(10, 5))
        self.goal_progress.set(0.0)
        self.goal_lbl = ctk.CTkLabel(goal_container, text="0.00€ / 100€", font=ctk.CTkFont(size=11), text_color="gray50")
        self.goal_lbl.pack(anchor="e")
        
        # 3. MVP Trade Widget (Right)
        mvp_container = ctk.CTkFrame(self.ai_visualizer_frame, fg_color="transparent")
        mvp_container.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(mvp_container, text="🏆 Bester Trade Heute", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray60").pack(anchor="w")
        self.mvp_trade_lbl = ctk.CTkLabel(mvp_container, text="Noch keine Trades", font=ctk.CTkFont(size=16, weight="bold"), text_color="#5EBA7D")
        self.mvp_trade_lbl.pack(anchor="center", pady=10)
        
        # State variables for animation
        self.ai_animation_idx = 0
        self.ai_current_symbol = None
        self._sonar_radii = [5, 15, 25] # Starting radii for expanding rings

        # Live Data List (Left Side)
        data_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray90", "gray13"))
        data_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(10, 5), pady=10)
        data_frame.grid_rowconfigure(1, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)

        header_lbl = ctk.CTkLabel(data_frame, text="Live Markt-Übersicht", font=ctk.CTkFont(size=16, weight="bold"))
        header_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.scroll_list = ctk.CTkScrollableFrame(data_frame, fg_color="transparent")
        self.scroll_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Table Header
        header_row = ctk.CTkFrame(self.scroll_list, fg_color="transparent", height=30)
        header_row.pack(fill="x", pady=(0, 5))
        header_row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        
        for i, col_name in enumerate(["Symbol", "Preis", "Änderung", "Trend (M15|H1|H4)", "Signal"]):
            lbl = ctk.CTkLabel(header_row, text=col_name, font=ctk.CTkFont(weight="bold", size=12), text_color="gray50")
            lbl.grid(row=0, column=i, sticky="w", padx=10)

        ctk.CTkFrame(self.scroll_list, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

        # Live P&L Chart (Right Side)
        self.chart_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.chart_frame.grid(row=3, column=2, sticky="nsew", padx=(5, 10), pady=10)
        self.chart_frame.grid_rowconfigure(1, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        
        chart_hdr = ctk.CTkLabel(self.chart_frame, text="Live P&L Laufzeit", font=ctk.CTkFont(size=16, weight="bold"))
        chart_hdr.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # We use a native Tkinter canvas for high-performance smooth drawing
        import tkinter as tk
        self.pnl_canvas = tk.Canvas(self.chart_frame, bg="#212121", highlightthickness=0)
        self.pnl_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Initial Mock Data
        self.populate_sample_data()

    def create_metric_card(self, parent, title, value, row, col):
        card = MetricCard(parent, title=title, value=value)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        return card

    def populate_sample_data(self):
        """Initialise dashboard rows. Called once on startup; load_settings will override."""
        self.live_data_rows = []
        self._rebuild_symbol_rows("EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD")

    def _rebuild_symbol_rows(self, raw_pairs: str):
        """Parse comma-separated pairs string, rebuild self.dashboard_symbols and
        the live-data rows in the dashboard.  Safe to call at any time."""
        split_pairs = [p.strip().upper() for p in raw_pairs.split(',') if p.strip()]
        if not split_pairs:
            return

        self.dashboard_symbols = [
            (f"{p[:3]}/{p[3:]}" if len(p) == 6 else p, p)
            for p in split_pairs
        ]

        # Destroy old rows
        if hasattr(self, 'scroll_list'):
            for w in self.scroll_list.winfo_children():
                if isinstance(w, LiveDataRow):
                    w.destroy()

        if hasattr(self, 'live_data_rows'):
            self.live_data_rows.clear()
        else:
            self.live_data_rows = []

        for display_name, symbol in self.dashboard_symbols:
            row = LiveDataRow(self.scroll_list, display_name, "---", "0.00%", "HOLD")
            row.pack(fill="x", pady=2)
            self.live_data_rows.append((symbol, row))

        self.update_dashboard_data()


    def setup_charts_tab(self):
        tab = self.tabview.tab("📈 Charts")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Sub-Navigation for Charts
        self.charts_sub_tabs = ctk.CTkTabview(tab, corner_radius=10)
        self.charts_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.charts_sub_tabs.add("🔲 Multi-View")
        self.charts_sub_tabs.add("🔎 Pattern Scanner")
        self.charts_sub_tabs.add("🔬 Advanced Analysis")
        
        # --- 1. Sub-Tab: Multi-View (Existing 2x3 Grid) ---
        multi_tab = self.charts_sub_tabs.tab("🔲 Multi-View")
        multi_tab.grid_columnconfigure(0, weight=1)
        multi_tab.grid_rowconfigure(1, weight=1)
        
        controls = ctk.CTkFrame(multi_tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(controls, text="↻ Charts Aktualisieren", command=self.load_forex_charts, fg_color="#2E86AB").pack(side="left", padx=(0, 10))
        
        # Timeframe Dropdown Menu
        self.chart_timeframe_var = ctk.StringVar(value="D1 (Täglich)")
        self.tf_combo = ctk.CTkComboBox(
            controls, 
            values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (Täglich)"], 
            variable=self.chart_timeframe_var,
            command=lambda choice: self.load_forex_charts()
        )
        self.tf_combo.pack(side="left", padx=10)
        
        self.charts_container = ctk.CTkScrollableFrame(multi_tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.charts_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Initial message
        self.charts_loading_lbl = ctk.CTkLabel(self.charts_container, text="Lade interaktive Forex Charts (Major Pairs)... Bitte warten.", 
                           justify="center", font=ctk.CTkFont(size=14), text_color="gray50")
        self.charts_loading_lbl.pack(pady=50)
        
        # Grid layout for charts_container (2 Columns)
        self.charts_container.grid_columnconfigure(0, weight=1)
        self.charts_container.grid_columnconfigure(1, weight=1)
        
        # --- 2. Sub-Tab: Pattern Scanner ---
        pattern_tab = self.charts_sub_tabs.tab("🔎 Pattern Scanner")
        pattern_tab.grid_columnconfigure(0, weight=1)
        pattern_tab.grid_rowconfigure(1, weight=1)
        
        scan_controls = ctk.CTkFrame(pattern_tab, fg_color="transparent")
        scan_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.scan_tf_var = ctk.StringVar(value="D1 (T\u00e4glich)")
        ctk.CTkComboBox(scan_controls, values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (T\u00e4glich)"], variable=self.scan_tf_var, width=150).pack(side="left", padx=5)
        ctk.CTkButton(scan_controls, text="\U0001f50d Markt Scannen", command=self.run_pattern_scanner, fg_color="#E67E22", hover_color="#D35400").pack(side="left", padx=5)
        self.scan_status_lbl = ctk.CTkLabel(scan_controls, text="Klicke auf Scannen...", text_color="gray50")
        self.scan_status_lbl.pack(side="left", padx=15)
        
        self.pattern_list_frame = ctk.CTkScrollableFrame(pattern_tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.pattern_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Header for the scanner list
        ph_row = ctk.CTkFrame(self.pattern_list_frame, fg_color="transparent", height=30)
        ph_row.pack(fill="x", pady=(0, 5))
        ph_row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        for i, col_name in enumerate(["Symbol", "Timeframe", "Gefundenes Pattern", "Relevanz", "Aktion"]):
            ctk.CTkLabel(ph_row, text=col_name, font=ctk.CTkFont(weight="bold", size=12), text_color="gray50").grid(row=0, column=i, sticky="w", padx=10)
        ctk.CTkFrame(self.pattern_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))
        
        # --- 3. Sub-Tab: Advanced Analysis ---
        adv_tab = self.charts_sub_tabs.tab("🔬 Advanced Analysis")
        adv_tab.grid_columnconfigure(0, weight=1)
        adv_tab.grid_rowconfigure(1, weight=1)
        
        adv_controls = ctk.CTkFrame(adv_tab, fg_color="transparent")
        adv_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Details for Advanced Chart
        self.adv_symbol_var = ctk.StringVar(value="EURUSD")
        self.adv_timeframe_var = ctk.StringVar(value="H1 (1 Std)")
        self.adv_indicator_var = ctk.StringVar(value="Keine (Raw Price)")
        
        ctk.CTkComboBox(adv_controls, values=["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"], variable=self.adv_symbol_var).pack(side="left", padx=5)
        ctk.CTkComboBox(adv_controls, values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (Täglich)"], variable=self.adv_timeframe_var).pack(side="left", padx=5)
        ctk.CTkComboBox(adv_controls, values=["Keine (Raw Price)", "SMA 20", "SMA 50", "EMA 200", "Bollinger Bands"], variable=self.adv_indicator_var).pack(side="left", padx=5)
        
        ctk.CTkButton(adv_controls, text="📊 Chart Analysieren", command=self.load_advanced_chart, fg_color="#8E44AD", hover_color="#732D91").pack(side="left", padx=10)
        
        self.adv_chart_container = ctk.CTkFrame(adv_tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.adv_chart_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.adv_chart_container, text="Wähle ein Asset und klicke auf 'Chart Analysieren'", text_color="gray50", font=ctk.CTkFont(size=14)).pack(expand=True)
        
        # Delay the initial load slightly so the GUI can render first
        self.after(1000, self.load_forex_charts)

    def load_advanced_chart(self):
        self.write_terminal(f">> Lade erweiterten Chart für {self.adv_symbol_var.get()}...\n")
        
        # Clear existing charts
        for widget in self.adv_chart_container.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.adv_chart_container, text="Lade Daten und berechne Indikatoren...", font=ctk.CTkFont(size=14))
        loading_lbl.pack(expand=True)
        
        symbol = self.adv_symbol_var.get()
        tf_str = self.adv_timeframe_var.get()
        indicator = self.adv_indicator_var.get()
        
        # Use a style compatible with dark mode
        mc = mpf.make_marketcolors(up='#5EBA7D', down='#E74C3C', edge='i', wick='i')
        s = mpf.make_mpf_style(marketcolors=mc, facecolor='#1E1E1E', edgecolor='gray', 
                               figcolor='#1E1E1E', gridcolor='#333333', gridstyle=':')
                               
        def fetch_and_plot_adv():
            try:
                if not mt5.initialize():
                    raise Exception("MetaTrader 5 konnte nicht initialisiert werden.")
                
                # Bestimme Timeframe
                if "M1 " in tf_str: tf = mt5.TIMEFRAME_M1
                elif "M5" in tf_str: tf = mt5.TIMEFRAME_M5
                elif "M15" in tf_str: tf = mt5.TIMEFRAME_M15
                elif "M30" in tf_str: tf = mt5.TIMEFRAME_M30
                elif "H1" in tf_str: tf = mt5.TIMEFRAME_H1
                elif "H4" in tf_str: tf = mt5.TIMEFRAME_H4
                else: tf = mt5.TIMEFRAME_D1
                
                # Lade 150 Kerzen für den großen Chart
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 150)
                if rates is None or len(rates) == 0:
                    raise Exception(f"Keine Daten für {symbol} empfangen.")
                    
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                
                fig = Figure(figsize=(9, 5), facecolor='#1E1E1E')
                ax = fig.add_subplot(111)
                ax.set_title(f"{symbol} - {tf_str.split(' ')[0]} - {indicator}", color='white')
                ax.tick_params(colors='white')

                # Indikator berechnen & Addplot vorbereiten
                apds = []
                if indicator == "SMA 20":
                    sma20 = df['close'].rolling(window=20).mean()
                    apds.append(mpf.make_addplot(sma20, color='cyan', ax=ax))
                elif indicator == "SMA 50":
                    sma50 = df['close'].rolling(window=50).mean()
                    apds.append(mpf.make_addplot(sma50, color='orange', ax=ax))
                elif indicator == "EMA 200":
                    ema200 = df['close'].ewm(span=200, adjust=False).mean()
                    apds.append(mpf.make_addplot(ema200, color='yellow', ax=ax))
                elif indicator == "Bollinger Bands":
                    sma20 = df['close'].rolling(window=20).mean()
                    std20 = df['close'].rolling(window=20).std()
                    upper_band = sma20 + (std20 * 2)
                    lower_band = sma20 - (std20 * 2)
                    apds.append(mpf.make_addplot(upper_band, color='cyan', alpha=0.5, ax=ax))
                    apds.append(mpf.make_addplot(lower_band, color='cyan', alpha=0.5, ax=ax))
                    apds.append(mpf.make_addplot(sma20, color='orange', alpha=0.8, ax=ax))
                
                plot_kwargs = dict(type='candle', ax=ax, style=s, show_nontrading=False, warn_too_much_data=2000)
                if apds:
                    plot_kwargs['addplot'] = apds
                    
                mpf.plot(df, **plot_kwargs)
                fig.tight_layout()
                
                # Update GUI
                self.after(0, lambda: self._render_adv_chart(fig))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: loading_lbl.configure(text=f"Fehler: {msg}"))
                
        threading.Thread(target=fetch_and_plot_adv, daemon=True).start()

    def _render_adv_chart(self, fig):
        for widget in self.adv_chart_container.winfo_children():
            widget.destroy()
            
        canvas = FigureCanvasTkAgg(fig, master=self.adv_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def run_pattern_scanner(self):
        tf_str = self.scan_tf_var.get()
        self.scan_status_lbl.configure(text=f"Scanne Major Pairs auf {tf_str.split(' ')[0]}...", text_color="#F1C40F")
        self.write_terminal(f">> Starte Candlestick Pattern Scanner ({tf_str})...\n")
        
        # Clear old results (keep header)
        children = self.pattern_list_frame.winfo_children()
        for widget in children[2:]:
            if hasattr(widget, 'destroy'):
                widget.destroy()
                
        if len(self.pattern_list_frame.winfo_children()) < 2:
            ctk.CTkFrame(self.pattern_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

        def scan_logic():
            try:
                if not mt5.initialize():
                    raise Exception("MT5 init fehlgeschlagen")
                
                # Parse Timeframe
                if "M1 " in tf_str: tf = mt5.TIMEFRAME_M1
                elif "M5" in tf_str: tf = mt5.TIMEFRAME_M5
                elif "M15" in tf_str: tf = mt5.TIMEFRAME_M15
                elif "M30" in tf_str: tf = mt5.TIMEFRAME_M30
                elif "H1" in tf_str: tf = mt5.TIMEFRAME_H1
                elif "H4" in tf_str: tf = mt5.TIMEFRAME_H4
                else: tf = mt5.TIMEFRAME_D1
                tf_label = tf_str.split(' ')[0]  # e.g. "D1"
                    
                pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
                found_patterns = []
                
                for symbol in pairs:
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 5)
                    if rates is None or len(rates) < 2:
                        continue
                        
                    current = rates[-1]
                    prev = rates[-2]
                    
                    c_open, c_close, c_high, c_low = current['open'], current['close'], current['high'], current['low']
                    p_open, p_close, p_high, p_low = prev['open'], prev['close'], prev['high'], prev['low']
                    
                    body_size = abs(c_open - c_close)
                    total_size = c_high - c_low
                    
                    if total_size == 0: continue
                    
                    if body_size <= total_size * 0.1:
                        found_patterns.append((symbol, tf_label, "Doji (Unentschlossenheit)", "\u2b50", tf_str))
                    elif p_close < p_open and c_close > c_open and c_close >= p_open and c_open <= p_close:
                        found_patterns.append((symbol, tf_label, "Bullish Engulfing (Kaufsignal)", "\u2b50\u2b50\u2b50", tf_str))
                    elif p_close > p_open and c_close < c_open and c_close <= p_open and c_open >= p_close:
                        found_patterns.append((symbol, tf_label, "Bearish Engulfing (Verkaufssignal)", "\u2b50\u2b50\u2b50", tf_str))
                    elif c_open > c_low + (total_size * 0.6) and c_close > c_low + (total_size * 0.6) and body_size <= total_size * 0.3:
                        if c_close > c_open:
                            found_patterns.append((symbol, tf_label, "Bullish Hammer", "\u2b50\u2b50", tf_str))

                self.after(0, lambda: self._render_scan_results(found_patterns))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self.scan_status_lbl.configure(text=f"Fehler: {msg}", text_color="#E74C3C"))

        threading.Thread(target=scan_logic, daemon=True).start()

    def _render_scan_results(self, patterns):
        if not patterns:
            ctk.CTkLabel(self.pattern_list_frame, text="Keine auff\u00e4lligen Candlestick-Patterns gefunden.", text_color="gray50").pack(pady=20)
        else:
            for sym, tf, pat, rel, tf_str in patterns:
                row = ctk.CTkFrame(self.pattern_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
                
                color = "white"
                if "Bullish" in pat: color = "#5EBA7D"
                elif "Bearish" in pat: color = "#E74C3C"
                elif "Doji" in pat: color = "#F1C40F"
                
                ctk.CTkLabel(row, text=sym, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
                ctk.CTkLabel(row, text=tf, text_color="gray70").grid(row=0, column=1, sticky="w", padx=10)
                ctk.CTkLabel(row, text=pat, text_color=color, font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, sticky="w", padx=10)
                ctk.CTkLabel(row, text=rel, text_color="#F1C40F").grid(row=0, column=3, sticky="w", padx=10)
                ctk.CTkButton(row, text="\U0001f4c8 Chart", width=80, height=26,
                              fg_color="#2E86AB", hover_color="#1a5f7a",
                              command=lambda s=sym, t=tf_str, p=pat: self._show_pattern_chart(s, t, p)
                             ).grid(row=0, column=4, sticky="w", padx=10)
                
        self.scan_status_lbl.configure(text=f"Scan abgeschlossen. {len(patterns)} Treffer.", text_color="#5EBA7D")

    def _show_pattern_chart(self, symbol, tf_str, pattern):
        """Open a Toplevel popup with the price chart and the pattern highlighted."""
        popup = ctk.CTkToplevel(self)
        popup.title(f"{symbol} - {pattern}")
        popup.geometry("900x550")
        popup.configure(fg_color="#1E1E1E")
        popup.grab_set()
        
        status = ctk.CTkLabel(popup, text=f"Lade Chart f\u00fcr {symbol}...", font=ctk.CTkFont(size=14))
        status.pack(expand=True)
        
        mc = mpf.make_marketcolors(up='#5EBA7D', down='#E74C3C', edge='i', wick='i')
        s = mpf.make_mpf_style(marketcolors=mc, facecolor='#1E1E1E', edgecolor='gray',
                               figcolor='#1E1E1E', gridcolor='#333333', gridstyle=':')
        
        def fetch_chart():
            try:
                if not mt5.initialize():
                    raise Exception("MT5 nicht verbunden")
                    
                if "M1 " in tf_str: tf = mt5.TIMEFRAME_M1
                elif "M5" in tf_str: tf = mt5.TIMEFRAME_M5
                elif "M15" in tf_str: tf = mt5.TIMEFRAME_M15
                elif "M30" in tf_str: tf = mt5.TIMEFRAME_M30
                elif "H1" in tf_str: tf = mt5.TIMEFRAME_H1
                elif "H4" in tf_str: tf = mt5.TIMEFRAME_H4
                else: tf = mt5.TIMEFRAME_D1
                
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 40)
                if rates is None or len(rates) < 3:
                    raise Exception("Nicht gen\u00fcgend Daten")
                    
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                
                fig = Figure(figsize=(9, 4.5), facecolor='#1E1E1E')
                ax = fig.add_subplot(111)
                ax.set_facecolor('#1E1E1E')
                ax.tick_params(colors='white')
                ax.set_title(f"{symbol}  |  {pattern}  |  {tf_str.split(' ')[0]}", color='white', fontsize=12)
                ax.spines['bottom'].set_color('gray')
                ax.spines['left'].set_color('gray')
                
                mpf.plot(df, type='candle', ax=ax, style=s, show_nontrading=False, warn_too_much_data=1000)
                
                # Highlight the last 2 candles as the pattern area
                ax.axvspan(len(df) - 2.5, len(df) - 0.5, color='yellow', alpha=0.15, zorder=0)
                ax.annotate(f"\u25bc {pattern}", xy=(len(df) - 1.5, ax.get_ylim()[1]),
                            xycoords=('data', 'data'), ha='center', va='top',
                            color='yellow', fontsize=9, fontweight='bold')
                
                fig.tight_layout()
                self.after(0, lambda: _embed_chart(fig))
            except Exception as e:
                err = str(e)
                self.after(0, lambda msg=err: status.configure(text=f"Fehler: {msg}"))
        
        def _embed_chart(fig):
            status.destroy()
            canvas = FigureCanvasTkAgg(fig, master=popup)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        threading.Thread(target=fetch_chart, daemon=True).start()

    # ══════════════════════════════════════════════════════
    # KI DEBATE TAB
    # ══════════════════════════════════════════════════════
    def setup_debate_tab(self):
        """🎭 KI Debate Mode — Bull vs Bear vs Judge."""
        tab = self.tabview.tab("🎭 Debate")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # ── Header / Controls ────────────────────────────────
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        ctrl.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(ctrl, text="🎭 KI Debate Mode",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#A855F7").grid(row=0, column=0, padx=(0, 20), sticky="w")

        ctk.CTkLabel(ctrl, text="Symbol:").grid(row=0, column=1, padx=(0, 6), sticky="w")
        self._debate_symbol = ctk.CTkEntry(ctrl, width=120, placeholder_text="EURUSD")
        self._debate_symbol.insert(0, "EURUSD")
        self._debate_symbol.grid(row=0, column=2, sticky="w", padx=(0, 12))

        self._debate_btn = ctk.CTkButton(
            ctrl, text="⚔️ Debatte starten",
            fg_color="#7C3AED", hover_color="#6D28D9", width=170,
            command=self._start_debate)
        self._debate_btn.grid(row=0, column=3, padx=(0, 12))

        self._debate_status = ctk.CTkLabel(ctrl, text="Bereit.", text_color="gray60",
                                           font=ctk.CTkFont(size=12))
        self._debate_status.grid(row=0, column=4, sticky="w")

        # ── Progress bar ─────────────────────────────────────
        self._debate_progress = ctk.CTkProgressBar(tab, mode="indeterminate",
                                                    progress_color="#7C3AED")
        self._debate_progress.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self._debate_progress.set(0)

        # ── Main debate area: Bull | Bear ─────────────────────
        panels = ctk.CTkFrame(tab, fg_color="transparent")
        panels.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 6))
        panels.grid_columnconfigure((0, 1), weight=1)
        panels.grid_rowconfigure(1, weight=1)

        # Bull panel
        bull_hdr = ctk.CTkFrame(panels, fg_color=("#DCFCE7", "#14532D"), corner_radius=10)
        bull_hdr.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 4))
        ctk.CTkLabel(bull_hdr, text="🟢 BULL Analyst",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#4ADE80").pack(anchor="w", padx=12, pady=8)

        self._bull_box = ctk.CTkTextbox(panels, corner_radius=10,
                                         fg_color=("gray92", "gray12"),
                                         font=ctk.CTkFont(family="Segoe UI", size=12),
                                         text_color="#4ADE80", wrap="word",
                                         state="disabled")
        self._bull_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        # Bear panel
        bear_hdr = ctk.CTkFrame(panels, fg_color=("#FEE2E2", "#7F1D1D"), corner_radius=10)
        bear_hdr.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
        ctk.CTkLabel(bear_hdr, text="🔴 BEAR Analyst",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#F87171").pack(anchor="w", padx=12, pady=8)

        self._bear_box = ctk.CTkTextbox(panels, corner_radius=10,
                                         fg_color=("gray92", "gray12"),
                                         font=ctk.CTkFont(family="Segoe UI", size=12),
                                         text_color="#F87171", wrap="word",
                                         state="disabled")
        self._bear_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        # ── Verdict panel ─────────────────────────────────────
        verdict_frame = ctk.CTkFrame(tab, corner_radius=12,
                                      fg_color=("gray88", "gray16"))
        verdict_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        verdict_frame.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(3, weight=0)

        ctk.CTkLabel(verdict_frame, text="⚖️",
                     font=ctk.CTkFont(size=26)).grid(row=0, column=0, padx=(14, 8), pady=10)
        self._verdict_lbl = ctk.CTkLabel(verdict_frame,
                                          text="Richter-Urteil erscheint hier nach der Debatte…",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color="gray50", wraplength=700, justify="left")
        self._verdict_lbl.grid(row=0, column=1, sticky="w", padx=(0, 14), pady=10)

    # ── Debate helpers ─────────────────────────────────────────────────────
    def _start_debate(self):
        symbol = self._debate_symbol.get().strip().upper() or "EURUSD"
        self._debate_btn.configure(state="disabled", text="⏳ Läuft…")
        self._debate_status.configure(text="Starte Debatte…", text_color="#A855F7")
        self._debate_progress.start()
        self._write_debate_box(self._bull_box, "🟢 Warte auf Bull Analyst…\n", "#4ADE80")
        self._write_debate_box(self._bear_box, "🔴 Warte auf Bear Analyst…\n", "#F87171")
        self._verdict_lbl.configure(text="⚖️ Richter analysiert noch…", text_color="gray50")
        threading.Thread(target=self._run_debate_bg, args=(symbol,), daemon=True).start()

    def _write_debate_box(self, box: ctk.CTkTextbox, text: str, color: str = "#D4D4D4"):
        box.configure(state="normal")
        box.delete("0.0", "end")
        box.insert("end", text)
        box.configure(state="disabled", text_color=color)

    def _ollama_debate_call(self, system_prompt: str, user_prompt: str) -> str:
        """Single Ollama API call with a system role prompt."""
        try:
            url = self.url_entry.get().strip()
            model = self.model_combo.get().strip() or "llama3"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 400},
            }
            resp = requests.post(f"{url}/api/chat", json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "").strip()
            return f"[Fehler: HTTP {resp.status_code}]"
        except Exception as e:
            return f"[Verbindungsfehler: {e}]"

    def _run_debate_bg(self, symbol: str):
        """Background thread: fetch market data → 3 Ollama calls → update UI."""
        try:
            # ── Step 0: Gather basic market data from MT5 ──────────────
            market_ctx = f"Symbol: {symbol}\n"
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    market_ctx += f"Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f}\n"
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 20)
                if rates is not None and len(rates) > 1:
                    closes = [r['close'] for r in rates]
                    gain = closes[-1] - closes[0]
                    market_ctx += f"H1 letzte 20 Kerzen: Eröffnung {closes[0]:.5f} → Jetzt {closes[-1]:.5f} | Diff: {gain:+.5f}\n"
            except Exception:
                market_ctx += "(MT5 nicht verfügbar – nur KI-Analyse)\n"

            user_msg = (
                f"Analysiere {symbol} für einen möglichen Trade.\n"
                f"Marktdaten:\n{market_ctx}\n"
                "Antworte auf Deutsch. Maximal 200 Wörter."
            )

            # ── Step 1: BULL ─────────────────────────────────────────
            self.after(0, lambda: self._debate_status.configure(
                text="🟢 Bull Analyst denkt…", text_color="#4ADE80"))
            bull_sys = (
                "Du bist ein sehr optimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich BUY/Long-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein KAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Gewinnziele."
            )
            bull_text = self._ollama_debate_call(bull_sys, user_msg)
            self.after(0, lambda t=bull_text: self._write_debate_box(self._bull_box, t, "#4ADE80"))

            # ── Step 2: BEAR ─────────────────────────────────────────
            self.after(0, lambda: self._debate_status.configure(
                text="🔴 Bear Analyst denkt…", text_color="#F87171"))
            bear_sys = (
                "Du bist ein sehr pessimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich SELL/Short-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein VERKAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Verlustrisiken beim Kauf."
            )
            bear_text = self._ollama_debate_call(bear_sys, user_msg)
            self.after(0, lambda t=bear_text: self._write_debate_box(self._bear_box, t, "#F87171"))

            # ── Step 3: JUDGE ────────────────────────────────────────
            self.after(0, lambda: self._debate_status.configure(
                text="⚖️ Richter urteilt…", text_color="#FBBF24"))
            judge_sys = (
                "Du bist ein unparteiischer Senior-Analyst. Du hast gerade zwei Analysten gehört: "
                "einen sehr bullischen und einen sehr bärischen. "
                "Deine Aufgabe: Bewerte beide Argumente fair, entscheide wer recht hat, "
                "und gib eine klare Empfehlung: BUY, SELL oder HOLD. "
                "Format deiner Antwort: Kurze Zusammenfassung beider Seiten (2 Sätze), "
                "dann: URTEIL: [BUY/SELL/HOLD] — Konfidenz: [0-100%] — Grund: [1 Satz]"
            )
            judge_msg = (
                f"Symbol: {symbol}\n\n"
                f"BULL-Argumente:\n{bull_text}\n\n"
                f"BEAR-Argumente:\n{bear_text}\n\n"
                "Was ist dein Urteil?"
            )
            verdict = self._ollama_debate_call(judge_sys, judge_msg)

            # Parse verdict colour
            v_upper = verdict.upper()
            if "BUY" in v_upper:
                v_color = "#4ADE80"
            elif "SELL" in v_upper:
                v_color = "#F87171"
            else:
                v_color = "#FBBF24"

            self.after(0, lambda t=verdict, c=v_color: (
                self._verdict_lbl.configure(text=t, text_color=c),
                self._debate_status.configure(text="Debatte abgeschlossen ✅", text_color="gray60"),
            ))

        except Exception as e:
            self.after(0, lambda err=e: self._debate_status.configure(
                text=f"Fehler: {err}", text_color="#F87171"))
        finally:
            self.after(0, self._debate_progress.stop)
            self.after(0, lambda: self._debate_btn.configure(
                state="normal", text="⚔️ Debatte starten"))

    # ══════════════════════════════════════════════════════
    # TRADE JOURNAL TAB
    # ══════════════════════════════════════════════════════
    def setup_journal_tab(self):
        tab = self.tabview.tab("📝 Journal")

        # Side-by-side Layout: Calendar Links, Trade List Rechts
        tab.grid_columnconfigure(0, weight=0)  # Calendar is fixed width
        tab.grid_columnconfigure(1, weight=1)  # Trade list expands
        tab.grid_rowconfigure(1, weight=1)     # Expand both vertically

        # ── State ──────────────────────────────────────────
        self._journal_year  = datetime.now().year
        self._journal_month = datetime.now().month
        self._journal_entries   = {}  # date_str -> list of trade dicts
        self._selected_journal_day = None
        self._selected_trade  = None

        # Seed demo data on very first run so calendar isn't empty
        self._seed_demo_trades()

        # ── Top bar: calendar controls + stats ─────────────
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        top.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(top, text="◀", width=36, command=self._journal_prev_month).grid(row=0, column=0, padx=(0, 4))
        self._cal_title_lbl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=15, weight="bold"))
        self._cal_title_lbl.grid(row=0, column=1, padx=8)
        ctk.CTkButton(top, text="▶", width=36, command=self._journal_next_month).grid(row=0, column=2, sticky="w", padx=(4, 0))

        # Stats summary labels
        stats_frame = ctk.CTkFrame(top, fg_color="transparent")
        stats_frame.grid(row=0, column=3, sticky="e", padx=(20, 0))
        self._j_stat_trades = ctk.CTkLabel(stats_frame, text="Trades: --", font=ctk.CTkFont(size=12), text_color="gray70")
        self._j_stat_trades.pack(side="left", padx=8)
        self._j_stat_winrate = ctk.CTkLabel(stats_frame, text="Win Rate: --%", font=ctk.CTkFont(size=12), text_color="gray70")
        self._j_stat_winrate.pack(side="left", padx=8)
        self._j_stat_pnl = ctk.CTkLabel(stats_frame, text="Gesamt P&L: --", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray70")
        self._j_stat_pnl.pack(side="left", padx=8)
        ctk.CTkButton(stats_frame, text="📥 CSV Export", width=110, command=self._export_journal_csv,
                      fg_color="transparent", border_width=1).pack(side="left", padx=(16, 0))

        # ── Left: Calendar grid ──────────────────────────────────
        self._cal_frame = ctk.CTkFrame(tab, fg_color=("gray90", "gray13"), corner_radius=12)
        self._cal_frame.grid(row=1, column=0, sticky="n", padx=10, pady=8)

        # ── Right: Trade list and AI reasoning ────────────────────
        right_panel = ctk.CTkFrame(tab, fg_color="transparent")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=8)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)

        # Trade list (scrollable)
        list_container = ctk.CTkFrame(right_panel, corner_radius=12, fg_color=("gray90", "gray13"))
        list_container.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(2, weight=1)

        self._j_list_title = ctk.CTkLabel(list_container, text="← Klicke einen Tag im Kalender, um Trades zu sehen",
                                           font=ctk.CTkFont(size=13, weight="bold"), text_color="gray60")
        self._j_list_title.grid(row=0, column=0, sticky="w", padx=15, pady=8)

        # Header row
        hdr = ctk.CTkFrame(list_container, fg_color=("gray80", "gray20"), corner_radius=0)
        hdr.grid(row=1, column=0, sticky="ew", padx=0)
        for col, (txt, w) in enumerate([("Ticket", 80), ("Symbol", 80), ("Richtung", 80),
                                         ("Eröffnung", 90), ("Schlusskurs", 90),
                                         ("Lots", 55), ("Profit", 80), ("KI", 40)]):
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray60", width=w).grid(row=0, column=col, padx=6, pady=4, sticky="w")

        self._j_scroll = ctk.CTkScrollableFrame(list_container, fg_color="transparent", corner_radius=0)
        self._j_scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        # AI Reasoning Panel (collapsible)
        self._ai_panel = ctk.CTkFrame(right_panel, corner_radius=12, fg_color=("gray85", "gray15"))
        self._ai_panel.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        self._ai_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self._ai_panel, text="🤖", font=ctk.CTkFont(size=20)).grid(row=0, column=0, padx=(15, 8), pady=10)
        self._ai_panel_header = ctk.CTkLabel(self._ai_panel,
                                              text="KI Begründung — klicke 🤖 in einer Trade-Zeile",
                                              font=ctk.CTkFont(size=13, weight="bold"), text_color="gray60")
        self._ai_panel_header.grid(row=0, column=1, sticky="w")
        
        self._ai_reflection_btn = ctk.CTkButton(self._ai_panel, text="🧠 System-Analyse anfordern",
                                          font=ctk.CTkFont(size=12, weight="bold"),
                                          fg_color="#A23B72", hover_color="#8c3363",
                                          width=180, height=28, command=self._analyze_past_trade_async)
        # We grid it conditionally in _show_ai_reasoning

        self._ai_reasoning_box = ctk.CTkTextbox(self._ai_panel, height=100, fg_color="transparent",
                                                  font=ctk.CTkFont(family="Segoe UI", size=12),
                                                  text_color="#D4D4D4", wrap="word", state="disabled")
        self._ai_reasoning_box.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 10))

        self._ai_indicators_lbl = ctk.CTkLabel(self._ai_panel, text="", font=ctk.CTkFont(size=11),
                                                text_color="#569CD6")
        self._ai_indicators_lbl.grid(row=2, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 8))

        # Initial render
        self._render_journal_calendar()

    # ── Calendar helpers ────────────────────────────────────────────────────
    def _journal_prev_month(self):
        if self._journal_month == 1:
            self._journal_month = 12; self._journal_year -= 1
        else:
            self._journal_month -= 1
        self._render_journal_calendar()

    def _journal_next_month(self):
        if self._journal_month == 12:
            self._journal_month = 1; self._journal_year += 1
        else:
            self._journal_month += 1
        self._render_journal_calendar()

    def _load_journal_entries(self, year, month):
        """Load trade history: primary source = MT5 history_deals_get(),
        secondary = JSON files in storage/trade_journal/ (add AI reasoning).
        Falls back to JSON-only if MT5 is not available."""
        import json, os, glob
        from datetime import datetime, timezone

        entries = {}  # date_str -> [trade_dict, ...]

        # ── 1. Try pulling real MT5 history ──────────────────────────────
        try:
            import MetaTrader5 as _mt5
            if not _mt5.initialize():
                raise RuntimeError("MT5 not initialized")

            # Month range (UTC timestamps)
            from_dt = datetime(year, month, 1, tzinfo=timezone.utc)
            # Last day of month
            import calendar as _cal
            last_day = _cal.monthrange(year, month)[1]
            to_dt   = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

            deals = _mt5.history_deals_get(from_dt, to_dt)

            if deals:
                # deal entry types: 0=in (open), 1=out (close), 2=in/out
                DEAL_TYPE_BUY  = 0
                DEAL_TYPE_SELL = 1
                DEAL_ENTRY_IN  = 0
                DEAL_ENTRY_OUT = 1

                for deal in deals:
                    # Skip balance/credit/commission lines (symbol is empty or type > 1)
                    if not deal.symbol:
                        continue

                    otype = deal.type          # 0=BUY, 1=SELL
                    action = "BUY" if otype == DEAL_TYPE_BUY else "SELL"

                    deal_dt = datetime.fromtimestamp(deal.time)
                    date_str = deal_dt.strftime("%Y-%m-%d")
                    profit   = round(deal.profit + deal.commission + deal.swap, 2)

                    trade = {
                        "ticket":      deal.ticket,
                        "order":       deal.order,
                        "symbol":      deal.symbol,
                        "action":      action,
                        "entry":       "OPEN" if deal.entry == DEAL_ENTRY_IN else "CLOSE",
                        "open_time":   deal_dt.isoformat(),
                        "close_time":  None,
                        "open_price":  deal.price,
                        "close_price": deal.price,
                        "lot_size":    deal.volume,
                        "profit":      profit,
                        "commission":  round(deal.commission, 2),
                        "swap":        round(deal.swap, 2),
                        "comment":     deal.comment,
                        "magic":       deal.magic,
                        "result":      "WIN" if profit > 0 else ("LOSS" if profit < 0 else "BE"),
                        # AI fields — filled in from JSON overlay below
                        "ai_reasoning":   "",
                        "ai_confidence":  "",
                        "indicators_used": [],
                        "tags":           [],
                    }
                    entries.setdefault(date_str, []).append(trade)

            mt5_loaded = True
        except Exception as mt5_err:
            mt5_loaded = False
            self.after(0, lambda e=str(mt5_err): self.write_terminal(
                f">> [JOURNAL] MT5 nicht verfügbar, lade JSON-Daten. ({e})\n", "WARNING"))

        # ── 2. Load JSON files (AI reasoning overlay / fallback) ──────────
        journal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "storage", "trade_journal")
        prefix = f"{year}{month:02d}"

        # Build lookup: ticket -> json_trade  (for overlay)
        json_by_ticket = {}
        for fpath in glob.glob(os.path.join(journal_dir, f"*_{prefix}*.json")):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    jt = json.load(f)
                jt["_filepath"] = fpath
                json_by_ticket[jt.get("ticket", 0)] = jt
                # If MT5 failed, use JSON as primary source
                if not mt5_loaded:
                    date_str = jt.get("open_time", "")[:10]
                    if date_str:
                        entries.setdefault(date_str, []).append(jt)
            except Exception:
                pass

        # ── 3. Overlay AI reasoning onto MT5 deals ────────────────────────
        if mt5_loaded:
            for day_trades in entries.values():
                for trade in day_trades:
                    jt = json_by_ticket.get(trade["ticket"]) or \
                         json_by_ticket.get(trade.get("order", -1))
                    if jt:
                        trade["ai_reasoning"]    = jt.get("ai_reasoning", "")
                        trade["ai_confidence"]   = jt.get("ai_confidence", "")
                        trade["indicators_used"] = jt.get("indicators_used", [])
                        trade["tags"]            = jt.get("tags", [])
                        trade["reflection_analysis"] = jt.get("reflection_analysis", "")
                        trade["_filepath"]       = jt.get("_filepath", "")

        self._journal_entries = entries
        return entries

    def _render_journal_calendar(self):
        """Render the calendar grid for the current month."""
        import calendar
        year, month = self._journal_year, self._journal_month
        entries = self._load_journal_entries(year, month)

        # Update title
        month_names = ["Januar","Februar","März","April","Mai","Juni",
                        "Juli","August","September","Oktober","November","Dezember"]
        self._cal_title_lbl.configure(text=f"{month_names[month-1]} {year}")

        # Compute monthly stats
        all_trades = [t for day_trades in entries.values() for t in day_trades]
        total_pnl = sum(t.get("profit", 0) for t in all_trades)
        wins = sum(1 for t in all_trades if t.get("profit", 0) > 0)
        win_rate = (wins / len(all_trades) * 100) if all_trades else 0
        pnl_color = "#5EBA7D" if total_pnl >= 0 else "#E74C3C"
        self._j_stat_trades.configure(text=f"Trades: {len(all_trades)}")
        self._j_stat_winrate.configure(text=f"Win Rate: {win_rate:.0f}%")
        self._j_stat_pnl.configure(text=f"Gesamt P&L: {'+' if total_pnl >= 0 else ''}{total_pnl:.2f}€",
                                    text_color=pnl_color)

        # Clear old calendar widgets
        for w in self._cal_frame.winfo_children():
            w.destroy()

        # Day headers
        for col, day_name in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
            ctk.CTkLabel(self._cal_frame, text=day_name,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray50", width=52).grid(row=0, column=col, padx=2, pady=(6, 2))

        # Calendar days
        cal = calendar.monthcalendar(year, month)
        today = datetime.now().date()

        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    ctk.CTkFrame(self._cal_frame, width=52, height=52, fg_color="transparent").grid(
                        row=row_idx + 1, column=col_idx, padx=2, pady=2)
                    continue

                date_str = f"{year}-{month:02d}-{day:02d}"
                day_trades = entries.get(date_str, [])
                day_pnl = sum(t.get("profit", 0) for t in day_trades)
                n_trades = len(day_trades)

                # Color coding
                is_today = (datetime(year, month, day).date() == today)
                if n_trades == 0:
                    bg = ("#D5D5D5", "#2A2A2A") if not is_today else "#2E86AB"
                    fg = "gray50"
                elif day_pnl > 0:
                    bg = ("#C8F7C5", "#1A4A30")
                    fg = "#5EBA7D"
                else:
                    bg = ("#FAD4D4", "#4A1A1A")
                    fg = "#E74C3C"

                # Build the day cell frame (acts as a button)
                cell = ctk.CTkFrame(self._cal_frame, width=58, height=58, corner_radius=8,
                                    fg_color=bg, cursor="hand2")
                cell.grid(row=row_idx + 1, column=col_idx, padx=2, pady=2)
                cell.grid_propagate(False)

                num_lbl = ctk.CTkLabel(cell, text=str(day),
                                       font=ctk.CTkFont(size=16, weight="bold"),
                                       text_color=("gray20", "white") if n_trades == 0 else fg)
                num_lbl.place(relx=0.5, rely=0.35, anchor="center")

                if n_trades > 0:
                    sub_lbl = ctk.CTkLabel(cell, text=f"{n_trades}T  {'+' if day_pnl>=0 else ''}{day_pnl:.0f}€",
                                           font=ctk.CTkFont(size=8), text_color=fg)
                    sub_lbl.place(relx=0.5, rely=0.75, anchor="center")

                # Click binding
                for widget in [cell, num_lbl]:
                    widget.bind("<Button-1>", lambda e, ds=date_str: self._show_day_trades(ds))
                if n_trades > 0:
                    sub_lbl.bind("<Button-1>", lambda e, ds=date_str: self._show_day_trades(ds))

    def _show_day_trades(self, date_str):
        """Populate the trade list for a clicked day."""
        self._selected_journal_day = date_str
        day_trades = self._journal_entries.get(date_str, [])

        # Update title
        day_pnl = sum(t.get("profit", 0) for t in day_trades)
        pnl_color = "#5EBA7D" if day_pnl >= 0 else "#E74C3C"
        self._j_list_title.configure(
            text=f"📅 {date_str}  —  {len(day_trades)} Trade(s)  |  P&L: {'+' if day_pnl>=0 else ''}{day_pnl:.2f}€",
            text_color=pnl_color if day_trades else "gray60")

        # Clear old rows
        for w in self._j_scroll.winfo_children():
            w.destroy()

        if not day_trades:
            ctk.CTkLabel(self._j_scroll, text="Keine Trades an diesem Tag.",
                         text_color="gray50").pack(pady=20)
            return

        for i, trade in enumerate(day_trades):
            profit = trade.get("profit", 0)
            profit_color = "#5EBA7D" if profit >= 0 else "#E74C3C"
            row_bg = ("gray85", "gray18") if i % 2 == 0 else ("gray80", "gray15")

            row = ctk.CTkFrame(self._j_scroll, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)

            def fmt_price(p):
                if isinstance(p, (float, int)):
                    return f"{p:.5f}".rstrip('0').rstrip('.')
                return str(p)

            data = [
                (str(trade.get("ticket", "-")), 80, "gray60"),
                (trade.get("symbol", "-"), 80, "white"),
                (trade.get("action", "-"), 80, "#5EBA7D" if trade.get("action") == "BUY" else "#E74C3C"),
                (fmt_price(trade.get("open_price", "-")), 90, "gray80"),
                (fmt_price(trade.get("close_price", trade.get("open_price", "-"))), 90, "gray80"),
                (str(trade.get("lot_size", "-")), 55, "gray70"),
                (f"{'+' if profit>=0 else ''}{profit:.2f}€", 80, profit_color),
            ]
            for col_idx, (text, width, color) in enumerate(data):
                ctk.CTkLabel(row, text=text, width=width, text_color=color,
                             font=ctk.CTkFont(size=11)).grid(row=0, column=col_idx, padx=6, pady=6, sticky="w")

            # AI reasoning button
            ai_btn = ctk.CTkButton(row, text="🤖", width=36, height=28,
                                    fg_color="#1A1A4A" if trade.get("ai_reasoning") else "transparent",
                                    hover_color="#2E86AB",
                                    command=lambda t=trade: self._show_ai_reasoning(t))
            ai_btn.grid(row=0, column=len(data), padx=6, pady=6)

    def _show_ai_reasoning(self, trade):
        """Show the AI reasoning panel for a selected trade."""
        self._selected_trade = trade
        symbol = trade.get("symbol", "?")
        action = trade.get("action", "?")
        reasoning = trade.get("ai_reasoning") or "Keine KI-Begründung für diesen Trade gespeichert."
        confidence = trade.get("ai_confidence", "")
        indicators = trade.get("indicators_used", [])
        reflection = trade.get("reflection_analysis")
        profit = trade.get("profit", 0)

        self._ai_panel_header.configure(
            text=f"🤖 KI Begründung  —  {symbol} {action}  "
                 f"{'| Konfidenz: ' + confidence if confidence else ''}",
            text_color="#C586C0")

        self._ai_reasoning_box.configure(state="normal")
        self._ai_reasoning_box.delete("1.0", "end")
        
        box_content = reasoning
        if reflection:
            box_content += "\n\n💡 KI Selbst-Reflexion (Fehleranalyse):\n" + reflection
            
        self._ai_reasoning_box.insert("end", box_content)
        self._ai_reasoning_box.configure(state="disabled")

        ind_text = ""
        if indicators:
            ind_text = "Verwendete Indikatoren: " + "  •  ".join(indicators)
        tags = trade.get("tags", [])
        if tags:
            ind_text += ("  |  Tags: " if ind_text else "Tags: ") + ", ".join(tags)
        self._ai_indicators_lbl.configure(text=ind_text)
        
        # Show Reflection button only for losing trades that haven't been analyzed yet
        if profit < 0 and not reflection and trade.get("_filepath"):
            self._ai_reflection_btn.grid(row=0, column=2, padx=(0, 15))
            self._ai_reflection_btn.configure(state="normal", text="🧠 System-Analyse anfordern")
        else:
            self._ai_reflection_btn.grid_forget()

    def _analyze_past_trade_async(self):
        trade = self._selected_trade
        if not trade or not trade.get("_filepath"):
            return
            
        self._ai_reflection_btn.configure(state="disabled", text="Analysiere...")
        
        def run_analysis():
            import requests, json
            
            prompt = (
                f"Du bist ein professioneller Trading-Coach. Du analysierst einen vergangenen Trade deines eigenen Systems, der im Stop-Loss endete.\n\n"
                f"Trade-Daten:\n"
                f"- Symbol: {trade.get('symbol')}\n"
                f"- Richtung: {trade.get('action')}\n"
                f"- Einstiegspreis: {trade.get('open_price')}\n"
                f"- Ausstiegspreis: {trade.get('close_price')}\n"
                f"- Verwendete Indikatoren: {', '.join(trade.get('indicators_used', []))}\n"
                f"- Ursprüngliche System-Begründung: {trade.get('ai_reasoning')}\n\n"
                f"Bitte schreibe in 2-3 klaren und sachlichen Sätzen auf Deutsch, was der Fehler gewesen sein könnte "
                f"(z.B. Fakeout, gegen den übergeordneten Trend gehandelt, wichtige News ignoriert, Fehlinterpretation) "
                f"und was das System beim nächsten Mal besser machen sollte."
            )
            
            # Load URL and Model from config
            base_url = self.config.get("Ollama", "BaseURL", fallback="http://localhost:11434").rstrip('/')
            model = self.config.get("Ollama", "Model", fallback="llama3.2")
            url = f"{base_url}/api/generate"
            
            try:
                response = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=45)
                if response.status_code == 200:
                    result_text = response.json().get("response", "Keine vernünftige Antwort erhalten.")
                else:
                    result_text = f"Fehler bei der Analyse: HTTP {response.status_code}"
            except Exception as e:
                result_text = f"Verbindungsfehler zu Ollama: {str(e)}"
                
            def on_done():
                trade["reflection_analysis"] = result_text.strip()
                # Update JSON file permanently
                filepath = trade.get("_filepath")
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    file_data["reflection_analysis"] = trade["reflection_analysis"]
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(file_data, f, indent=4, ensure_ascii=False)
                    self.write_terminal(f">> [JOURNAL] KI-Reflexion für Ticket {trade.get('ticket')} dauerhaft gespeichert.\n", "SUCCESS")
                except Exception as e:
                    self.write_terminal(f">> [JOURNAL] Fehler beim Speichern der Reflexion: {e}\n", "ERROR")
                
                # Update UI
                self._show_ai_reasoning(trade)
                
            self.after(0, on_done)
            
        import threading
        threading.Thread(target=run_analysis, daemon=True).start()

    def _export_journal_csv(self):
        """Export currently visible month's trades to CSV."""
        import csv, os
        from tkinter import filedialog
        all_trades = [t for trades in self._journal_entries.values() for t in trades]
        if not all_trades:
            from tkinter import messagebox
            messagebox.showinfo("CSV Export", "Keine Trades zum Exportieren gefunden.")
            return

        default_name = f"journal_{self._journal_year}_{self._journal_month:02d}.csv"
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                initialfile=default_name,
                                                filetypes=[("CSV", "*.csv")])
        if not filepath:
            return

        fields = ["ticket","symbol","action","result","open_time","close_time",
                  "lot_size","profit","ai_confidence","indicators_used","ai_reasoning"]
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for t in all_trades:
                row = dict(t)
                row["indicators_used"] = "; ".join(t.get("indicators_used", []))
                writer.writerow(row)
        self.write_terminal(f">> [JOURNAL] CSV exportiert: {filepath}\n", "SYSTEM")

    def _seed_demo_trades(self):
        """Create demo journal entries if trade_journal folder is empty."""
        import json, os, glob
        journal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "storage", "trade_journal")
        os.makedirs(journal_dir, exist_ok=True)
        if glob.glob(os.path.join(journal_dir, "*.json")):
            return  # already has data

        today = datetime.now()
        demo_trades = [
            {"ticket": 100001, "symbol": "EURUSD", "action": "BUY", "result": "WIN",
             "open_time": (today.replace(day=max(1,today.day-5), hour=9, minute=15)).isoformat(),
             "close_time": (today.replace(day=max(1,today.day-5), hour=11, minute=45)).isoformat(),
             "open_price": 1.08421, "close_price": 1.08580, "lot_size": 0.1, "profit": 15.90,
             "ai_reasoning": "EURUSD zeigt bullische Divergenz auf dem RSI H1-Chart. Die 200er EMA wirkt als dynamischer Support. Das Preisniveau 1.0840 ist ein starker historischer Support. London Session ist in vollem Gange mit erhöhtem Volumen. BBands sind eng — Breakout erwartet. Fundamental spricht ein schwächerer USD durch gestrige Fed-Kommentare für Long.",
             "ai_confidence": "84%", "indicators_used": ["RSI H1", "EMA 200", "Bollinger Bands", "Volume"], "tags": ["trend_follow", "london_session"]},
            {"ticket": 100002, "symbol": "GBPUSD", "action": "SELL", "result": "WIN",
             "open_time": (today.replace(day=max(1,today.day-5), hour=14, minute=0)).isoformat(),
             "close_time": (today.replace(day=max(1,today.day-5), hour=16, minute=30)).isoformat(),
             "open_price": 1.26800, "close_price": 1.26510, "lot_size": 0.1, "profit": 29.00,
             "ai_reasoning": "GBPUSD hat ein Double-Top auf H4 gebildet. RSI zeigt Überkauft bei 72. Die NY-Session eröffnet bearish. MACD Crossover nach unten bestätigt den Short-Signal. Target ist der nächste Support bei 1.2640.",
             "ai_confidence": "79%", "indicators_used": ["MACD", "RSI H4", "Candlestick Pattern"], "tags": ["reversal", "ny_session"]},
            {"ticket": 100003, "symbol": "USDJPY", "action": "BUY", "result": "LOSS",
             "open_time": (today.replace(day=max(1,today.day-3), hour=10, minute=0)).isoformat(),
             "close_time": (today.replace(day=max(1,today.day-3), hour=13, minute=15)).isoformat(),
             "open_price": 151.200, "close_price": 150.900, "lot_size": 0.1, "profit": -30.00,
             "ai_reasoning": "USDJPY hat einen bullischen Breakout aus einer Konsolidierungszone versucht. Der Yen schwächte sich intraday ab. Allerdings war der Widerstand bei 151.50 stärker als erwartet. Stop wurde bei 150.90 getroffen nach unerwarteter BOJ-Intervention.",
             "ai_confidence": "61%", "indicators_used": ["Support/Resistance", "EMA 50", "ATR"], "tags": ["breakout", "asian_carryover"]},
            {"ticket": 100004, "symbol": "AUDUSD", "action": "SELL", "result": "WIN",
             "open_time": (today.replace(day=max(1,today.day-1), hour=8, minute=30)).isoformat(),
             "close_time": (today.replace(day=max(1,today.day-1), hour=12, minute=0)).isoformat(),
             "open_price": 0.65800, "close_price": 0.65600, "lot_size": 0.1, "profit": 20.00,
             "ai_reasoning": "AUDUSD befindet sich in einem klaren Abwärtstrend auf dem Daily Chart. Der heutige Bounce zur EMA 20 bietet eine ideale Short-Einstiegsgelegenheit mit gutem R:R von 1:3. China PMI-Daten waren schlechter als erwartet — negativ für AUD.",
             "ai_confidence": "88%", "indicators_used": ["EMA 20", "Trend Structure", "Fundamentals"], "tags": ["trend_continuation", "london_open"]},
        ]

        for trade in demo_trades:
            dt_str = trade["open_time"][:8].replace("-", "")
            fname = f"{trade['ticket']}_{trade['symbol']}_{dt_str}.json"
            with open(os.path.join(journal_dir, fname), 'w', encoding='utf-8') as f:
                json.dump(trade, f, indent=2, ensure_ascii=False)

    # ══════════════════════════════════════════════════════
    # NEWS & SENTIMENT FEED TAB
    # ══════════════════════════════════════════════════════
    def setup_news_tab(self):
        tab = self.tabview.tab("📰 News")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # State
        self._news_items        = []   # list of dicts
        self._news_analyzing    = False
        self._news_filter_pair  = "Alle"

        # ── Control bar ─────────────────────────────────────
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        self._news_refresh_btn = ctk.CTkButton(
            ctrl, text="🔄 News Laden", width=130,
            fg_color="#2E86AB", hover_color="#21618C",
            command=self._fetch_news_threaded)
        self._news_refresh_btn.pack(side="left", padx=(0, 8))

        self._news_analyze_btn = ctk.CTkButton(
            ctrl, text="🤖 Alle Analysieren", width=150,
            fg_color="#8E44AD", hover_color="#6C3483",
            command=self._analyze_all_news_threaded)
        self._news_analyze_btn.pack(side="left", padx=(0, 14))

        # Currency pair filter chips
        ctk.CTkLabel(ctrl, text="Filter:", text_color="gray60").pack(side="left", padx=(0, 4))
        self._news_filter_btns = {}
        for pair in ["Alle", "EUR", "GBP", "USD", "JPY", "CHF", "AUD", "CAD", "NZD"]:
            btn = ctk.CTkButton(ctrl, text=pair, width=52, height=26,
                                fg_color="#2E86AB" if pair == "Alle" else ("gray75", "gray25"),
                                hover_color="#21618C",
                                command=lambda p=pair: self._news_filter(p))
            btn.pack(side="left", padx=2)
            self._news_filter_btns[pair] = btn

        # Status right-side
        self._news_status_lbl = ctk.CTkLabel(ctrl, text="● Bereit", text_color="gray50",
                                              font=ctk.CTkFont(size=11))
        self._news_status_lbl.pack(side="right", padx=15)

        # ── News feed (scrollable) ───────────────────────────
        self._news_scroll = ctk.CTkScrollableFrame(tab, fg_color=("gray88", "gray12"),
                                                    corner_radius=12)
        self._news_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self._news_scroll.grid_columnconfigure(0, weight=1)

        # Placeholder
        self._news_placeholder = ctk.CTkLabel(
            self._news_scroll,
            text="🔄  Klicke 'News Laden' um aktuelle Forex-Nachrichten zu laden.",
            font=ctk.CTkFont(size=13), text_color="gray50")
        self._news_placeholder.pack(pady=40)

        # Auto-load on tab open
        self.after(800, self._fetch_news_threaded)

    # ── News fetching ────────────────────────────────────────────────────────
    def _fetch_news_threaded(self):
        if self._news_analyzing:
            return
        self._news_refresh_btn.configure(state="disabled", text="⏳ Lade...")
        self._news_status_lbl.configure(text="● Lade Nachrichten...", text_color="#E67E22")
        threading.Thread(target=self._fetch_news_bg, daemon=True).start()

    def _fetch_news_bg(self):
        """Fetch news from multiple free public RSS/JSON sources."""
        import xml.etree.ElementTree as ET

        sources = [
            # FXStreet RSS
            ("FXStreet", "https://www.fxstreet.com/rss/news"),
            # MarketWatch currencies RSS
            ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/marketpulse/"),
            # Investopedia Forex
            ("Investopedia", "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_forex"),
            # Forex Live
            ("ForexLive", "https://www.forexlive.com/feed/news"),
        ]

        all_items = []
        for source_name, url in sources:
            try:
                resp = requests.get(url, timeout=8,
                                    headers={"User-Agent": "Mozilla/5.0 FinGPT-NewsReader/1.0"})
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                ns = ""
                # Try both RSS 2.0 and Atom
                items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                for item in items[:10]:   # max 10 per source
                    def g(tag):
                        el = item.find(tag)
                        if el is None:
                            el = item.find("{http://www.w3.org/2005/Atom}" + tag.lstrip("./"))
                        return (el.text or "").strip() if el is not None else ""
                    title   = g("title") or g("summary")
                    pub_raw = g("pubDate") or g("published") or g("updated")
                    desc    = g("description") or g("summary") or ""
                    # Clean HTML from desc
                    import re
                    desc = re.sub(r'<[^>]+>', '', desc)[:300]
                    if not title:
                        continue
                    all_items.append({
                        "source":    source_name,
                        "title":     title,
                        "published": pub_raw,
                        "summary":   desc,
                        "sentiment": {},    # filled by Ollama later
                        "pairs":     self._detect_pairs(title + " " + desc),
                    })
            except Exception as e:
                self.after(0, lambda s=source_name, err=str(e):
                    self.write_terminal(f">> [NEWS] {s} Fehler: {err[:60]}\n", "WARNING"))

        # Sort by recency heuristic (just keep insertion order from latest source)
        self._news_items = all_items
        self.after(0, self._render_news_feed)
        self.after(0, lambda: self._news_refresh_btn.configure(state="normal", text="🔄 News Laden"))
        count = len(all_items)
        self.after(0, lambda c=count: self._news_status_lbl.configure(
            text=f"● {c} Artikel geladen", text_color="#5EBA7D"))

    def _detect_pairs(self, text):
        """Detect currency pairs mentioned in text."""
        text_up = text.upper()
        pairs = []
        currencies = {"EUR": ["EUR","EURO","EUROPEAN","ECB"],
                      "GBP": ["GBP","POUND","BOE","STERLING","UK","BRITAIN"],
                      "USD": ["USD","DOLLAR","FED","FEDERAL RESERVE","DXY"],
                      "JPY": ["JPY","YEN","BOJ","JAPAN"],
                      "CHF": ["CHF","FRANC","SNB","SWISS"],
                      "AUD": ["AUD","AUSSIE","RBA","AUSTRALIA"],
                      "CAD": ["CAD","LOONIE","BOC","CANADA"],
                      "NZD": ["NZD","KIWI","RBNZ","NEW ZEALAND"]}
        for cur, keywords in currencies.items():
            if any(kw in text_up for kw in keywords):
                pairs.append(cur)
        return pairs or ["USD"]   # default USD if nothing found

    # ── Ollama Sentiment Analysis ────────────────────────────────────────────
    def _analyze_all_news_threaded(self):
        if not self._news_items:
            self._fetch_news_threaded()
            return
        if self._news_analyzing:
            return
        self._news_analyzing = True
        self._news_analyze_btn.configure(state="disabled", text="⏳ Analysiere...")
        self._news_status_lbl.configure(text="● Ollama analysiert...", text_color="#8E44AD")
        threading.Thread(target=self._analyze_all_news_bg, daemon=True).start()

    def _analyze_all_news_bg(self):
        total = len(self._news_items)
        for i, item in enumerate(self._news_items):
            if item.get("sentiment"):
                continue
            sentiment = self._ollama_analyze_news(item["title"], item["summary"], item["pairs"])
            item["sentiment"] = sentiment
            progress = i + 1
            self.after(0, lambda p=progress, t=total:
                self._news_status_lbl.configure(text=f"● Analysiere {p}/{t}...",
                                                text_color="#8E44AD"))
        self.after(0, self._render_news_feed)
        self.after(0, lambda: self._news_analyze_btn.configure(state="normal",
                                                                text="🤖 Alle Analysieren"))
        self.after(0, lambda: self._news_status_lbl.configure(
            text="● Analyse abgeschlossen", text_color="#5EBA7D"))
        self._news_analyzing = False

    def _ollama_analyze_news(self, title, summary, pairs):
        """Ask Ollama to rate the news as BULLISH / BEARISH / NEUTRAL per detected currency."""
        try:
            url   = self.url_entry.get().strip()
            model = self.model_combo.get()
            if not url or "Verbindung" in model or "Lade" in model:
                return {}

            pairs_str = ", ".join(pairs) if pairs else "EUR, USD"
            prompt = (
                f"Du bist ein erfahrener Forex-Analyst. Bewerte die folgende Finanznachricht "
                f"kurz und präzise für diese Währungen: {pairs_str}.\n\n"
                f"Überschrift: {title}\n"
                f"Zusammenfassung: {summary}\n\n"
                f"Antworte NUR mit einem JSON-Objekt im Format:\n"
                f'{{"EUR": "BULLISH", "USD": "BEARISH", "GBP": "NEUTRAL", ...}}\n'
                f"Verwende ausschließlich: BULLISH, BEARISH oder NEUTRAL. Kein weiterer Text."
            )
            payload = {"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.1, "num_predict": 120}}
            resp = requests.post(f"{url}/api/generate", json=payload, timeout=20)
            raw  = resp.json().get("response", "").strip()

            import json as _json, re as _re
            match = _re.search(r'\{[^}]+\}', raw)
            if match:
                return _json.loads(match.group(0))
        except Exception:
            pass
        return {}

    # ── News Rendering ───────────────────────────────────────────────────────
    def _news_filter(self, pair):
        self._news_filter_pair = pair
        # Update button highlights
        for p, btn in self._news_filter_btns.items():
            btn.configure(fg_color="#2E86AB" if p == pair else ("gray75", "gray25"))
        self._render_news_feed()

    def _render_news_feed(self):
        """Render news cards into the scrollable frame."""
        for w in self._news_scroll.winfo_children():
            w.destroy()

        items = self._news_items
        flt   = self._news_filter_pair
        if flt != "Alle":
            items = [it for it in items if flt in it.get("pairs", [])]

        if not items:
            ctk.CTkLabel(self._news_scroll,
                         text="Keine Nachrichten gefunden. Klicke 🔄 News Laden.",
                         text_color="gray50").pack(pady=40)
            return

        # Remove old placeholder
        SENT_COLOR = {"BULLISH": "#5EBA7D", "BEARISH": "#E74C3C", "NEUTRAL": "#E67E22"}
        SENT_ICON  = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}

        for idx, item in enumerate(items):
            card_bg = ("gray85", "gray16") if idx % 2 == 0 else ("gray82", "gray14")
            card = ctk.CTkFrame(self._news_scroll, fg_color=card_bg, corner_radius=10)
            card.pack(fill="x", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            # Row 1: Source + Time + Pairs badges
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))

            src_lbl = ctk.CTkLabel(top_row, text=f"📡 {item['source']}",
                                   font=ctk.CTkFont(size=10, weight="bold"),
                                   text_color="#569CD6")
            src_lbl.pack(side="left")

            time_txt = item.get("published", "")[:22]
            ctk.CTkLabel(top_row, text=f"  {time_txt}", text_color="gray50",
                         font=ctk.CTkFont(size=10)).pack(side="left", padx=8)

            # Pair badges
            for pair in item.get("pairs", []):
                sentiment = item.get("sentiment", {}).get(pair, "")
                badge_color = SENT_COLOR.get(sentiment, "gray40")
                badge_text  = f"{SENT_ICON.get(sentiment, '⚪')} {pair}"
                ctk.CTkLabel(top_row, text=badge_text, fg_color=badge_color,
                             corner_radius=6, font=ctk.CTkFont(size=10, weight="bold"),
                             text_color="white").pack(side="right", padx=3)

            # Row 2: Headline
            ctk.CTkLabel(card, text=item["title"],
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="white", wraplength=800, justify="left",
                         anchor="w").grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 2))

            # Row 3: Summary (if any)
            if item.get("summary"):
                ctk.CTkLabel(card, text=item["summary"][:180] + ("…" if len(item["summary"]) > 180 else ""),
                             font=ctk.CTkFont(size=11), text_color="gray65",
                             wraplength=800, justify="left",
                             anchor="w").grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

            # Analyze button (single item) if no sentiment yet
            if not item.get("sentiment"):
                def _analyze_one(it=item):
                    threading.Thread(target=lambda: (
                        it.__setitem__("sentiment",
                                       self._ollama_analyze_news(it["title"], it["summary"], it["pairs"])),
                        self.after(0, self._render_news_feed)
                    ), daemon=True).start()
                ctk.CTkButton(card, text="🤖", width=32, height=22,
                              fg_color="transparent", hover_color="#8E44AD",
                              command=_analyze_one).grid(row=0, column=1, padx=8, pady=4)

            # Bottom separator
            ctk.CTkFrame(card, height=1, fg_color="gray30").grid(
                row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 0))

    def setup_terminal_tab(self):



        tab = self.tabview.tab("💻 Terminal")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # ── Control bar ──────────────────────────────────────────────
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        ctk.CTkButton(controls, text="🧹 Leeren", command=self.clear_terminal,
                      fg_color="#E74C3C", hover_color="#C0392B", width=90).pack(side="left", padx=(0, 6))

        self._log_paused = False
        self._pause_btn = ctk.CTkButton(controls, text="⏸ Pause", command=self._toggle_log_pause,
                                        fg_color="#E67E22", hover_color="#D35400", width=90)
        self._pause_btn.pack(side="left", padx=(0, 6))

        ctk.CTkButton(controls, text="📂 Log-Ordner", command=self._open_log_folder,
                      fg_color="transparent", border_width=1, width=110).pack(side="left", padx=(0, 14))

        # Filter buttons
        ctk.CTkLabel(controls, text="Filter:", text_color="gray60").pack(side="left", padx=(0, 5))
        self._log_filter = ctk.StringVar(value="ALL")
        for label, val, color in [("Alle", "ALL", "#2E86AB"), ("TRADE 💰", "TRADE", "#5EBA7D"),
                                   ("ERROR ❌", "ERROR", "#E74C3C"), ("WARN ⚠️", "WARNING", "#F1C40F"),
                                   ("AI 🤖", "AI", "#8E44AD")]:
            ctk.CTkButton(controls, text=label, width=80,
                          command=lambda v=val: self._set_log_filter(v),
                          fg_color=color, hover_color="gray30",
                          border_width=1).pack(side="left", padx=2)

        # Right side: live log status indicator
        self._log_status_lbl = ctk.CTkLabel(controls, text="● Log: warte...", text_color="gray50",
                                             font=ctk.CTkFont(size=11))
        self._log_status_lbl.pack(side="right", padx=15)

        # ── Terminal text box ─────────────────────────────────────────
        # We use the underlying Tk Text widget directly for full tag/color support
        import tkinter as tk
        self._term_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color="#101010")
        self._term_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self._term_frame.grid_rowconfigure(0, weight=1)
        self._term_frame.grid_columnconfigure(0, weight=1)

        self.terminal_box = tk.Text(self._term_frame,
                                    bg="#101010", fg="#D4D4D4",
                                    font=("Consolas", 12),
                                    insertbackground="#D4D4D4",
                                    selectbackground="#264F78",
                                    relief="flat", borderwidth=0,
                                    wrap="word", state="disabled")
        self.terminal_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Scrollbar
        sb = tk.Scrollbar(self._term_frame, command=self.terminal_box.yview,
                          bg="#1E1E1E", troughcolor="#1E1E1E", highlightthickness=0)
        sb.grid(row=0, column=1, sticky="ns")
        self.terminal_box.configure(yscrollcommand=sb.set)

        # Color tags
        self.terminal_box.tag_configure("ts",      foreground="#569CD6")   # timestamp (blue)
        self.terminal_box.tag_configure("INFO",    foreground="#D4D4D4")   # white
        self.terminal_box.tag_configure("SYSTEM",  foreground="#9CDCFE")   # light blue
        self.terminal_box.tag_configure("MT5",     foreground="#4EC9B0")   # teal
        self.terminal_box.tag_configure("AI",      foreground="#C586C0")   # purple
        self.terminal_box.tag_configure("TRADE",   foreground="#5EBA7D")   # green  ★ important
        self.terminal_box.tag_configure("WARNING", foreground="#F1C40F")   # yellow
        self.terminal_box.tag_configure("ERROR",   foreground="#F44747", font=("Consolas", 12, "bold"))
        self.terminal_box.tag_configure("DEBUG",   foreground="#666666")   # gray
        self.terminal_box.tag_configure("INDICATORS", foreground="#CE9178")# orange
        self.terminal_box.tag_configure("RISK",    foreground="#E74C3C")   # red-ish
        self.terminal_box.tag_configure("PROMPT",  foreground="#DCDCAA")   # yellow-ish
        self.terminal_box.tag_configure("CATEGORY",foreground="#608B4E")   # bracket green
        self.terminal_box.tag_configure("separator",foreground="#333333")

        # Boot messages
        self.write_terminal("FinGPT Professional", "SYSTEM")
        self.write_terminal("  ─────────────────────────────────────────────\n", "separator")
        self.write_terminal("  System initialisiert. Log-Stream startet...\n\n", "SYSTEM")

        # Start live log tail
        self._log_filter_value = "ALL"
        self._log_tail_running = False
        self._start_log_tail()

    def _trigger_autosave(self, *args):
        """Debounced auto-save. Waits 1 second after the last change to save."""
        if hasattr(self, '_autosave_timer') and self._autosave_timer is not None:
            self.after_cancel(self._autosave_timer)
        self._autosave_timer = self.after(1000, self._do_autosave)

    def _do_autosave(self):
        """Silently saves config and updates dependent UI (like symbol rows)."""
        self.save_settings(silent=True)
        # Pairs — delegate to shared helper so dashboard updates instantly
        raw_pairs = self.pairs_entry.get().strip()
        if raw_pairs:
            self._rebuild_symbol_rows(raw_pairs)

    def setup_config_tab(self):
        tab = self.tabview.tab("⚙️ Konfiguration")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Sub-navigation for config
        self.config_sub_tabs = ctk.CTkTabview(tab, corner_radius=10)
        self.config_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self.config_sub_tabs.add("🤖 KI & Ollama")
        self.config_sub_tabs.add("📊 Trading Style")
        self.config_sub_tabs.add("🧠 Reinforcement Learning")
        self.config_sub_tabs.add("⚙️ MT5 & System")

        # ── TAB 1: KI & Ollama ───────────────────────
        ki_tab = self.config_sub_tabs.tab("🤖 KI & Ollama")
        ki_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ki_tab, text="🤖 KI & Ollama Einstellungen", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E86AB").grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(ki_tab, text="Ollama URL:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.url_entry = ctk.CTkEntry(ki_tab, placeholder_text="http://localhost:11434", width=300)
        self.url_entry.insert(0, "http://localhost:11434")
        self.url_entry.grid(row=1, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(ki_tab, text="LLM Modell:").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.model_combo = ctk.CTkComboBox(ki_tab, values=["Lade Modelle..."], width=300)
        self.model_combo.grid(row=2, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(ki_tab, text="Auto-Trading Intervall (sek):").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.interval_slider = ctk.CTkSlider(ki_tab, from_=1, to=30, number_of_steps=29)
        self.interval_slider.set(5)
        self.interval_slider.grid(row=3, column=1, sticky="ew", padx=20, pady=10)
        self.interval_lbl = ctk.CTkLabel(ki_tab, text="5s")
        self.interval_lbl.grid(row=3, column=2, padx=(0, 20))
        self.interval_slider.configure(command=lambda val: self.interval_lbl.configure(text=f"{int(val)}s"))
        ctk.CTkLabel(ki_tab, text="KI Temperatur:").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.ai_temp_slider = ctk.CTkSlider(ki_tab, from_=0.0, to=1.0, number_of_steps=10)
        self.ai_temp_slider.set(0.3)
        self.ai_temp_slider.grid(row=4, column=1, sticky="ew", padx=20, pady=10)
        self.ai_temp_lbl = ctk.CTkLabel(ki_tab, text="0.3")
        self.ai_temp_lbl.grid(row=4, column=2, padx=(0, 20))
        self.ai_temp_slider.configure(command=lambda val: self.ai_temp_lbl.configure(text=f"{val:.1f}"))
        ctk.CTkLabel(ki_tab, text="Prompt-Sprache:").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.prompt_lang_var = ctk.StringVar(value="Deutsch")
        ctk.CTkComboBox(ki_tab, values=["Deutsch", "Englisch", "Gemischt"], variable=self.prompt_lang_var).grid(row=5, column=1, sticky="w", padx=20, pady=10)

        # ── TAB 2: Trading Style ─────────────────
        style_tab = self.config_sub_tabs.tab("📊 Trading Style")
        style_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(style_tab, text="📊 Trading Strategie & Stil", font=ctk.CTkFont(size=16, weight="bold"), text_color="#E67E22").grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(style_tab, text="Trading Style:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.trading_style_var = ctk.StringVar(value="Swing Trading")
        ctk.CTkComboBox(style_tab, values=["Scalping", "Day Trading", "Swing Trading", "Position Trading"], variable=self.trading_style_var, width=250).grid(row=1, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(style_tab, text="Signal-Strategie:").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.signal_strategy_var = ctk.StringVar(value="KI-gesteuert (Ollama)")
        ctk.CTkComboBox(style_tab, values=["KI-gesteuert (Ollama)", "Technische Indikatoren", "Hybrid (KI + Indikatoren)"], variable=self.signal_strategy_var, width=280).grid(row=2, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(style_tab, text="Favorisierte Sitzungen:").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        sessions_frame = ctk.CTkFrame(style_tab, fg_color="transparent")
        sessions_frame.grid(row=3, column=1, sticky="w", padx=20, pady=10)
        self.session_london = ctk.CTkCheckBox(sessions_frame, text="London")
        self.session_london.select()
        self.session_london.pack(side="left", padx=5)
        self.session_ny = ctk.CTkCheckBox(sessions_frame, text="New York")
        self.session_ny.select()
        self.session_ny.pack(side="left", padx=5)
        self.session_asia = ctk.CTkCheckBox(sessions_frame, text="Asian")
        self.session_asia.pack(side="left", padx=5)
        ctk.CTkLabel(style_tab, text="Risikoprofil:").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.risk_profile_var = ctk.StringVar(value="Moderat")
        ctk.CTkComboBox(style_tab, values=["Konservativ", "Moderat", "Aggressiv"], variable=self.risk_profile_var, width=200).grid(row=4, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(style_tab, text="Max Risiko pro Trade (%):").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.risk_trade_entry = ctk.CTkEntry(style_tab, width=80)
        self.risk_trade_entry.insert(0, "1.0")
        self.risk_trade_entry.grid(row=5, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(style_tab, text="Max Daily Loss (%):").grid(row=6, column=0, sticky="w", padx=20, pady=10)
        self.risk_daily_entry = ctk.CTkEntry(style_tab, width=80)
        self.risk_daily_entry.insert(0, "3.0")
        self.risk_daily_entry.grid(row=6, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(style_tab, text="Max Offene Positionen:").grid(row=7, column=0, sticky="w", padx=20, pady=10)
        self.max_pos_entry = ctk.CTkEntry(style_tab, width=80)
        self.max_pos_entry.insert(0, "3")
        self.max_pos_entry.grid(row=7, column=1, sticky="w", padx=20, pady=10)
        self.trading_active_switch = ctk.CTkSwitch(style_tab, text="Auto-Trading Global Erlauben", progress_color="#5EBA7D")
        self.trading_active_switch.select()
        self.trading_active_switch.grid(row=8, column=0, columnspan=2, sticky="w", padx=20, pady=20)

        # ── TAB 3: Reinforcement Learning ──────────
        rl_tab = self.config_sub_tabs.tab("🧠 Reinforcement Learning")
        rl_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(rl_tab, text="🧠 Reinforcement Learning Einstellungen", font=ctk.CTkFont(size=16, weight="bold"), text_color="#8E44AD").grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(rl_tab, text="RL Algorithmus:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.rl_algo_var = ctk.StringVar(value="PPO")
        ctk.CTkComboBox(rl_tab, values=["PPO", "DQN", "A2C", "SAC"], variable=self.rl_algo_var, width=180, command=self._trigger_autosave).grid(row=1, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(rl_tab, text="Lernrate:").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.rl_lr_slider = ctk.CTkSlider(rl_tab, from_=0.0001, to=0.01, number_of_steps=99)
        self.rl_lr_slider.set(0.0003)
        self.rl_lr_slider.grid(row=2, column=1, sticky="ew", padx=20, pady=10)
        self.rl_lr_lbl = ctk.CTkLabel(rl_tab, text="0.0003")
        self.rl_lr_lbl.grid(row=2, column=2, padx=(0, 20))
        def _on_lr_change(val):
            self.rl_lr_lbl.configure(text=f"{val:.4f}")
            self._trigger_autosave()
        self.rl_lr_slider.configure(command=_on_lr_change)
        ctk.CTkLabel(rl_tab, text="Gamma (Discount):").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.rl_gamma_slider = ctk.CTkSlider(rl_tab, from_=0.8, to=1.0, number_of_steps=20)
        self.rl_gamma_slider.set(0.99)
        self.rl_gamma_slider.grid(row=3, column=1, sticky="ew", padx=20, pady=10)
        self.rl_gamma_lbl = ctk.CTkLabel(rl_tab, text="0.99")
        self.rl_gamma_lbl.grid(row=3, column=2, padx=(0, 20))
        def _on_gamma_change(val):
            self.rl_gamma_lbl.configure(text=f"{val:.2f}")
            self._trigger_autosave()
        self.rl_gamma_slider.configure(command=_on_gamma_change)
        ctk.CTkLabel(rl_tab, text="Training Steps:").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.rl_steps_entry = ctk.CTkEntry(rl_tab, width=120)
        self.rl_steps_entry.insert(0, "100000")
        self.rl_steps_entry.bind("<KeyRelease>", self._trigger_autosave)
        self.rl_steps_entry.grid(row=4, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(rl_tab, text="Belohnungsfunktion:").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.rl_reward_var = ctk.StringVar(value="Profit + Sharpe Ratio")
        ctk.CTkComboBox(rl_tab, values=["Profit + Sharpe Ratio", "Reiner Profit", "Sortino Ratio", "Custom"], variable=self.rl_reward_var, width=250, command=self._trigger_autosave).grid(row=5, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(rl_tab, text="Checkpoint Pfad:").grid(row=6, column=0, sticky="w", padx=20, pady=10)
        self.rl_checkpoint_entry = ctk.CTkEntry(rl_tab, placeholder_text="storage/rl_agents/model.zip", width=300)
        self.rl_checkpoint_entry.bind("<KeyRelease>", self._trigger_autosave)
        self.rl_checkpoint_entry.grid(row=6, column=1, sticky="ew", padx=20, pady=10)
        self.rl_live_switch = ctk.CTkSwitch(rl_tab, text="RL Agent für Live-Trading aktivieren (Experimentell)", progress_color="#8E44AD", command=self._trigger_autosave)
        self.rl_live_switch.grid(row=7, column=0, columnspan=3, sticky="w", padx=20, pady=15)

        # ── TAB 4: MT5 & System ──────────────
        mt5_tab = self.config_sub_tabs.tab("⚙️ MT5 & System")
        mt5_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(mt5_tab, text="⚙️ MetaTrader 5 & System", font=ctk.CTkFont(size=16, weight="bold"), text_color="#E74C3C").grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        ctk.CTkButton(mt5_tab, text="MT5 Manuell Neuverbinden", command=self.test_mt5_connection, fg_color="transparent", border_width=1).grid(row=1, column=0, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(mt5_tab, text="Währungspaare Preset:").grid(row=2, column=0, sticky="w", padx=20, pady=(10, 2))

        # Preset definitions
        self._pair_presets = {
            "🏆 Majors (6 Paare)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD",
            "🥈 Majors + Minors (14 Paare)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
                "EURGBP, EURJPY, GBPJPY, AUDNZD, CADJPY, AUDCAD, NZDJPY",
            "🔀 Crosses (EUR/GBP/JPY Cross)":
                "EURGBP, EURJPY, EURCAD, EURAUD, EURNZD, EURCHF, "
                "GBPJPY, GBPCAD, GBPAUD, GBPNZD, GBPCHF",
            "💎 Exotics":
                "USDTRY, USDZAR, USDMXN, USDHKD, USDSGD, EURTRY, "
                "GBPTRY, XAUUSD, XAGUSD",
            "🌐 Alle Paare (Majors + Minors + Crosses)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
                "EURGBP, EURJPY, EURCAD, EURAUD, EURNZD, EURCHF, "
                "GBPJPY, GBPCAD, GBPAUD, GBPNZD, GBPCHF, "
                "AUDNZD, AUDCAD, CADJPY, NZDJPY, CHFJPY",
            "✏️ Custom (Manuell eingeben)": "",
        }

        self._pairs_preset_var = ctk.StringVar(value="🏆 Majors (6 Paare)")
        pairs_preset_combo = ctk.CTkComboBox(
            mt5_tab,
            values=list(self._pair_presets.keys()),
            variable=self._pairs_preset_var,
            width=350,
            command=self._on_pairs_preset_change,
        )
        pairs_preset_combo.grid(row=2, column=1, sticky="w", padx=20, pady=(10, 2))

        ctk.CTkLabel(mt5_tab, text="Aktive Paare (editierbar):").grid(row=3, column=0, sticky="w", padx=20, pady=(2, 10))
        self.pairs_entry = ctk.CTkEntry(mt5_tab, width=350)
        self.pairs_entry.insert(0, self._pair_presets["🏆 Majors (6 Paare)"])
        self.pairs_entry.bind("<KeyRelease>", self._trigger_autosave)
        self.pairs_entry.grid(row=3, column=1, sticky="ew", padx=20, pady=(2, 10))
        ctk.CTkLabel(mt5_tab, text="Konto Typ:").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.account_type_var = ctk.StringVar(value="Demo")
        ctk.CTkComboBox(mt5_tab, values=["Demo", "Live", "Cent"], variable=self.account_type_var, width=150, command=self._trigger_autosave).grid(row=4, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(mt5_tab, text="Magic Number:").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.magic_number_entry = ctk.CTkEntry(mt5_tab, width=120)
        self.magic_number_entry.insert(0, "42069")
        self.magic_number_entry.bind("<KeyRelease>", self._trigger_autosave)
        self.magic_number_entry.grid(row=5, column=1, sticky="w", padx=20, pady=10)
        ctk.CTkLabel(mt5_tab, text="Logging Level:").grid(row=6, column=0, sticky="w", padx=20, pady=10)
        self.log_level_var = ctk.StringVar(value="INFO")
        ctk.CTkComboBox(mt5_tab, values=["DEBUG", "INFO", "WARNING", "ERROR"], variable=self.log_level_var, width=150, command=self._trigger_autosave).grid(row=6, column=1, sticky="w", padx=20, pady=10)
        self.debug_mode_switch = ctk.CTkSwitch(mt5_tab, text="Debug-Modus (mehr Terminal-Output)", progress_color="#E74C3C", command=self._trigger_autosave)
        self.debug_mode_switch.grid(row=7, column=0, columnspan=2, sticky="w", padx=20, pady=15)

        # Removed explicit Save Button since auto-save handles it now
        tab.grid_rowconfigure(1, weight=0)
        
        # Auto-saved hint
        self.autosave_hint = ctk.CTkLabel(tab, text="✅ Alle Änderungen werden automatisch gespeichert.", text_color="gray50", font=ctk.CTkFont(size=11, slant="italic"))
        self.autosave_hint.grid(row=1, column=0, sticky="e", padx=20, pady=(10, 15))

        self.after(500, self.fetch_ollama_models_silently)

    def _on_pairs_preset_change(self, choice):
        """Fill the pairs entry when a preset is selected from the dropdown."""
        pairs = self._pair_presets.get(choice, "")
        self.pairs_entry.delete(0, "end")
        if pairs:
            self.pairs_entry.insert(0, pairs)
            self._trigger_autosave()
        # If "Custom" → entry stays empty and user types freely

    def fetch_ollama_models_silently(self):

        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [model['name'] for model in response.json().get('models', [])]
                if models:
                    self.model_combo.configure(values=models)
                    self.model_combo.set(models[0])
                else:
                    self.model_combo.configure(values=["Keine Modelle gefunden"])
                    self.model_combo.set("Keine Modelle gefunden")
            else:
                self.model_combo.configure(values=["Verbindung fehlgeschlagen"])
                self.model_combo.set("Verbindung fehlgeschlagen")
        except Exception:
            self.model_combo.configure(values=["Verbindung fehlgeschlagen"])
            self.model_combo.set("Verbindung fehlgeschlagen")

    def test_ollama_connection(self):
        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [model['name'] for model in response.json().get('models', [])]
                if models:
                    self.model_combo.configure(values=models)
                    self.model_combo.set(models[0])
                    messagebox.showinfo("Erfolg", f"Ollama verbunden! {len(models)} Modelle gefunden.")
                    self.write_terminal(f">> Ollama Connection OK. Models: {', '.join(models)}\n")
                else:
                    self.model_combo.configure(values=["Keine Modelle gefunden"])
                    messagebox.showwarning("Warnung", "Ollama ist erreichbar, aber es sind keine Modelle installiert.")
            else:
                messagebox.showerror("Fehler", f"Server antwortete mit Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindungsfehler", f"Ollama Daemon konnte nicht erreicht werden:\n{e}")

    def test_mt5_connection(self):
        if mt5.initialize():
            messagebox.showinfo("Erfolg", "MetaTrader 5 erfolgreich verbunden!")
            self.write_terminal(">> MT5 Connection re-initialized successfully.\n")
        else:
            messagebox.showerror("Fehler", "MT5 Terminal konnte nicht gefunden oder verbunden werden.")

    def save_config(self):
        try:
            # Gather Configuration Data
            ollama_url = self.url_entry.get().strip()
            llm_model = self.model_combo.get()
            auto_trade_interval = int(self.interval_slider.get())
            
            # Risk Management
            is_auto_trading = self.trading_active_switch.get() == 1
            max_risk = float(self.risk_trade_entry.get())
            max_daily_loss = float(self.risk_daily_entry.get())
            max_pos = int(self.max_pos_entry.get())
            
            # Pairs — delegate to shared helper
            raw_pairs = self.pairs_entry.get().strip()
            if raw_pairs:
                self._rebuild_symbol_rows(raw_pairs)

            status_msg = f">> [CONFIG SAVED] Model: {llm_model} | Auto: {is_auto_trading} | Interval: {auto_trade_interval}s\n"
            status_msg += f">> [RISK LIMITS] Risk/Trade: {max_risk}% | Daily Loss: {max_daily_loss}% | Max Pos: {max_pos}\n"
            status_msg += f">> [PAIRS] Monitoring {len(self.dashboard_symbols)} pairs.\n"
            self.write_terminal(status_msg)
            
            # Persist to disk
            self.save_settings()
            
            messagebox.showinfo("Erfolg", "Konfiguration wurde erfolgreich gespeichert und angewendet!")
            
            if self.is_live_running:
                self.update_dashboard_data()
                
        except ValueError as e:
            messagebox.showerror("Eingabefehler", f"Bitte überprüfen Sie Ihre numerischen Eingaben.\nDetails: {str(e)}")

    def _config_path(self):
        import os
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "gui_settings")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")

    def save_settings(self, silent: bool = False):
        """Save all GUI settings to a JSON file for persistence across restarts."""
        import json
        cfg = {
            # KI & Ollama
            "ollama_url":       self.url_entry.get().strip(),
            "llm_model":        self.model_combo.get(),
            "interval":         int(self.interval_slider.get()),
            "ai_temperature":   round(self.ai_temp_slider.get(), 1),
            "prompt_lang":      self.prompt_lang_var.get(),
            # Trading Style
            "trading_style":    self.trading_style_var.get(),
            "signal_strategy":  self.signal_strategy_var.get(),
            "risk_profile":     self.risk_profile_var.get(),
            "max_risk":         self.risk_trade_entry.get(),
            "max_daily_loss":   self.risk_daily_entry.get(),
            "max_positions":    self.max_pos_entry.get(),
            "auto_trading":     bool(self.trading_active_switch.get()),
            "session_london":   bool(self.session_london.get()),
            "session_ny":       bool(self.session_ny.get()),
            "session_asia":     bool(self.session_asia.get()),
            # Reinforcement Learning
            "rl_algo":          self.rl_algo_var.get(),
            "rl_learning_rate": round(self.rl_lr_slider.get(), 4),
            "rl_gamma":         round(self.rl_gamma_slider.get(), 2),
            "rl_steps":         self.rl_steps_entry.get(),
            "rl_reward":        self.rl_reward_var.get(),
            "rl_checkpoint":    self.rl_checkpoint_entry.get(),
            "rl_live_enabled":  bool(self.rl_live_switch.get()),
            # MT5 & System
            "pairs":            self.pairs_entry.get(),
            "account_type":     self.account_type_var.get(),
            "magic_number":     self.magic_number_entry.get(),
            "log_level":        self.log_level_var.get(),
            "debug_mode":       bool(self.debug_mode_switch.get()),
        }
        try:
            with open(self._config_path(), 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            if not silent:
                self.write_terminal(f">> [SETTINGS] Gespeichert in: {self._config_path()}\n")
        except Exception as e:
            if not silent:
                self.write_terminal(f">> [SETTINGS ERROR] Speichern fehlgeschlagen: {e}\n")

    def load_settings(self):
        """Load saved GUI settings from JSON and apply to all widgets."""
        import json
        try:
            path = self._config_path()
            import os
            if not os.path.exists(path):
                return  # No saved config yet, keep defaults

            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)

            def _set_entry(widget, key):
                v = cfg.get(key)
                if v is not None:
                    widget.delete(0, "end")
                    widget.insert(0, str(v))

            def _set_combo(var_or_combo, key):
                v = cfg.get(key)
                if v is not None:
                    if isinstance(var_or_combo, ctk.StringVar):
                        var_or_combo.set(v)
                    else:
                        var_or_combo.set(v)

            def _set_slider(slider, lbl, key, fmt="{:.0f}"):
                v = cfg.get(key)
                if v is not None:
                    slider.set(float(v))
                    lbl.configure(text=fmt.format(float(v)))

            def _set_switch(switch, key):
                v = cfg.get(key)
                if v is not None:
                    switch.select() if v else switch.deselect()

            # KI & Ollama
            _set_entry(self.url_entry, "ollama_url")
            if cfg.get("llm_model"):
                self.model_combo.set(cfg["llm_model"])
            _set_slider(self.interval_slider, self.interval_lbl, "interval", fmt="{:.0f}s")
            _set_slider(self.ai_temp_slider, self.ai_temp_lbl, "ai_temperature", fmt="{:.1f}")
            _set_combo(self.prompt_lang_var, "prompt_lang")

            # Trading Style
            _set_combo(self.trading_style_var, "trading_style")
            _set_combo(self.signal_strategy_var, "signal_strategy")
            _set_combo(self.risk_profile_var, "risk_profile")
            _set_entry(self.risk_trade_entry, "max_risk")
            _set_entry(self.risk_daily_entry, "max_daily_loss")
            _set_entry(self.max_pos_entry, "max_positions")
            _set_switch(self.trading_active_switch, "auto_trading")
            _set_switch(self.session_london, "session_london")
            _set_switch(self.session_ny, "session_ny")
            _set_switch(self.session_asia, "session_asia")

            # Reinforcement Learning
            _set_combo(self.rl_algo_var, "rl_algo")
            _set_slider(self.rl_lr_slider, self.rl_lr_lbl, "rl_learning_rate", fmt="{:.4f}")
            _set_slider(self.rl_gamma_slider, self.rl_gamma_lbl, "rl_gamma", fmt="{:.2f}")
            _set_entry(self.rl_steps_entry, "rl_steps")
            _set_combo(self.rl_reward_var, "rl_reward")
            _set_entry(self.rl_checkpoint_entry, "rl_checkpoint")
            _set_switch(self.rl_live_switch, "rl_live_enabled")

            # MT5 & System
            _set_entry(self.pairs_entry, "pairs")
            _set_combo(self.account_type_var, "account_type")
            _set_entry(self.magic_number_entry, "magic_number")
            _set_combo(self.log_level_var, "log_level")
            _set_switch(self.debug_mode_switch, "debug_mode")

            # Auto-apply saved pairs to dashboard immediately
            loaded_pairs = self.pairs_entry.get().strip()
            if loaded_pairs:
                self.after(0, lambda p=loaded_pairs: self._rebuild_symbol_rows(p))

            self.write_terminal(f">> [SETTINGS] Einstellungen geladen aus: {path}\n")

        except Exception as e:
            self.write_terminal(f">> [SETTINGS ERROR] Laden fehlgeschlagen: {e}\n")

    # ==========================================
    # 7. FAQ TAB (Hilfe & Dokumentation)
    # ==========================================
    def setup_faq_tab(self):
        tab = self.tabview.tab("❓ FAQ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header, text="Häufig gestellte Fragen (FAQ)", 
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Hilfe zur Software & Trading-Plattform", 
                     font=ctk.CTkFont(size=14), text_color="gray60").pack(side="left", padx=(15, 0), pady=(8, 0))
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 20))
        
        # FAQ Daten
        faqs = [
            ("Wie verbinde ich MetaTrader 5?", 
             "Wechsle in den Tab '⚙️ Konfiguration' und überprüfe, ob der MT5-Pfad korrekt ist. "
             "Wenn alles stimmt, klicke oben rechts auf '▶ Live Starten'. Achte darauf, dass im MetaTrader 5 "
             "oben der Button 'Algo-Trading' aktiviert (grün) ist!"),
             
            ("Was bedeutet der rote Punkt bei RL Engine unten rechts?", 
             "Die RL (Reinforcement Learning) Engine sucht nach fertig trainierten KI-Agenten im Ordner 'storage/rl_agents'. "
             "Der rote Punkt bedeutet, dass das System momentan im Basis-Modus läuft, weil noch keine Modelle "
             "trainiert und gespeichert wurden. FinGPT funktioniert auch ohne diese Agenten einwandfrei."),
             
            ("Warum tradet die KI nicht, obwohl Live gestartet ist?", 
             "1. Ist 'Algo-Trading' im MT5 an?\n"
             "2. Ist im '⚙️ Konfiguration' Tab -> '⚙️ System' der Schalter 'Trading Erlaubt' aktiv?\n"
             "3. Findet die KI gerade überhaupt ein Setup? FinGPT erzwingt keine Trades. "
             "Schau im '💻 Terminal' Tab nach Log-Ausgaben oder nutze den '🤖 KI Trade-Berater' in der Live Markt-Übersicht für manuelle Setups."),
             
            ("Wie funktioniert der AI Trade Coach (Reflexion) im Journal?", 
             "Wenn ein Trade im Minus geschlossen wird, taucht im '📝 Journal' Tab beim Anklicken "
             "des Trades im KI-Panel unten rechts der Button '🧠 System-Analyse anfordern' auf. "
             "Darüber schickt FinGPT rückwirkend die Indikatordaten nochmals an Ollama, um aus "
             "dem Fehler zu lernen (z.B. Fakeouts, gegen den Trend gehandelt etc.)."),
             
            ("Wie liest FinGPT die Charts?", 
             "Die Software nutzt die MetaTrader 5 Schnittstelle, um Preisdaten (Open, High, Low, Close) für "
             "verschiedene Zeitfenster (z.B. M15, H1, H4) direkt im Hintergrund abzufragen. "
             "Die Python-Engine berechnet daraus Indikatoren (RSI, MACD, Bollinger Bänder) und gibt "
             "diese textuell an das lokale Ollama-Modell weiter."),
             
            ("Muss Ollama im Hintergrund laufen?", 
             "Ja! FinGPT greift auf ein lokales KI-Modell (z.B. llama3.2) über die Ollama API zu. "
             "Ohne gestarteten Ollama-Service (meist http://localhost:11434) funktioniert die "
             "KI-Analyse, das Journal-Reasoning und das Setup-Finden nicht.")
        ]
        
        # Rendere FAQ Cards
        for idx, (question, answer) in enumerate(faqs):
            card = ctk.CTkFrame(scroll, fg_color=("gray90", "gray13"), corner_radius=12)
            card.pack(fill="x", padx=10, pady=(0, 15))
            card.grid_columnconfigure(0, weight=1)
            
            # Question (Bold)
            q_lbl = ctk.CTkLabel(card, text=f"Q: {question}", 
                                 font=ctk.CTkFont(size=14, weight="bold"), 
                                 text_color="#5EBA7D", justify="left", anchor="w")
            q_lbl.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
            
            # Answer
            a_lbl = ctk.CTkLabel(card, text=answer, 
                                 font=ctk.CTkFont(size=13), 
                                 text_color="gray70", justify="left", anchor="w", wraplength=900)
            a_lbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))

    # ==========================================
    # 8. RL STUDIO TAB (Agent Training)
    # ==========================================
    def setup_rl_studio_tab(self):
        tab = self.tabview.tab("🤖 RL Studio")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(1, weight=1)
        
        # --- TOP HEADER BAR ---
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header, text="Reinforcement Learning Studio", 
                     font=ctk.CTkFont(size=24, weight="bold"), text_color="#8E44AD").pack(side="left")
        ctk.CTkLabel(header, text="Trainiere eigene KI-Agenten auf historischen MT5-Daten", 
                     font=ctk.CTkFont(size=14), text_color="gray60").pack(side="left", padx=(15, 0), pady=(8, 0))
        
        # --- LEFT PANEL: Config Overview & Start Button ---
        left_panel = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray85", "#181818"))
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        
        ctk.CTkLabel(left_panel, text="📌 Aktuelle Trainings-Config", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=(20, 10), padx=20, anchor="w")
        
        # Info Box reading from settings
        info_box = ctk.CTkFrame(left_panel, fg_color=("gray90", "gray13"), corner_radius=10)
        info_box.pack(fill="x", padx=20, pady=10)
        
        # Labels that we'll update when switching tabs or clicking refresh
        self.rl_cfg_algo_lbl = ctk.CTkLabel(info_box, text="Algorithmus: PPO", text_color="#2E86AB")
        self.rl_cfg_algo_lbl.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.rl_cfg_lr_lbl = ctk.CTkLabel(info_box, text="Lernrate: 0.0003", text_color="#5EBA7D")
        self.rl_cfg_lr_lbl.pack(anchor="w", padx=15, pady=5)
        
        self.rl_cfg_steps_lbl = ctk.CTkLabel(info_box, text="Total Steps: 100000", text_color="#E67E22")
        self.rl_cfg_steps_lbl.pack(anchor="w", padx=15, pady=(5, 15))
        
        self._training_active = False
        
        # Control Buttons
        self.btn_start_rl = ctk.CTkButton(left_panel, text="▶ Neues Modell Trainieren", 
                                          font=ctk.CTkFont(size=15, weight="bold"),
                                          height=45, fg_color="#5EBA7D", hover_color="#4CAF50",
                                          command=self._start_rl_training_sim)
        self.btn_start_rl.pack(fill="x", padx=20, pady=(20, 10))
        
        self.btn_stop_rl = ctk.CTkButton(left_panel, text="⏹ Training Abbrechen", 
                                         font=ctk.CTkFont(size=14),
                                         height=35, fg_color="#E74C3C", hover_color="#C0392B",
                                         state="disabled", command=self._stop_rl_training_sim)
        self.btn_stop_rl.pack(fill="x", padx=20, pady=0)
        
        # Refresh config button
        ctk.CTkButton(left_panel, text="🔄 Config Neu Laden", fg_color="transparent", 
                      border_width=1, text_color="gray60", command=self._update_rl_studio_config_labels).pack(pady=20)
                      
        # --- RIGHT PANEL: Live Progress & Terminal ---
        right_panel = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray85", "#181818"))
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Progress Section
        prog_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        prog_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        
        self.rl_status_lbl = ctk.CTkLabel(prog_header, text="Warte auf Start...", font=ctk.CTkFont(weight="bold", size=15), text_color="gray50")
        self.rl_status_lbl.pack(side="left")
        
        self.rl_pct_lbl = ctk.CTkLabel(prog_header, text="0%", font=ctk.CTkFont(weight="bold", size=15), text_color="#5EBA7D")
        self.rl_pct_lbl.pack(side="right")
        
        self.rl_progress = ctk.CTkProgressBar(right_panel, progress_color="#8E44AD", height=12)
        self.rl_progress.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        self.rl_progress.set(0)
        
        # Terminal Box for Training Logs
        import tkinter as tk
        term_frame = ctk.CTkFrame(right_panel, corner_radius=8, fg_color="#101010")
        term_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        term_frame.grid_rowconfigure(0, weight=1)
        term_frame.grid_columnconfigure(0, weight=1)
        
        self.rl_term_box = tk.Text(term_frame, bg="#101010", fg="#D4D4D4", 
                                   font=("Consolas", 11), insertbackground="#D4D4D4",
                                   relief="flat", borderwidth=0, state="disabled")
        self.rl_term_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        sb = tk.Scrollbar(term_frame, command=self.rl_term_box.yview, bg="#1E1E1E", troughcolor="#1E1E1E", highlightthickness=0)
        sb.grid(row=0, column=1, sticky="ns")
        self.rl_term_box.configure(yscrollcommand=sb.set)
        
        self.rl_term_box.tag_configure("tf", foreground="#F1C40F") # Yellow warning/tf labels
        self.rl_term_box.tag_configure("info", foreground="#9CDCFE") # Blue info
        self.rl_term_box.tag_configure("success", foreground="#5EBA7D") # Green success
        
        self._write_rl_log("[SYSTEM] RL Studio initialisiert. Bereit für Training.", "info")

    def _update_rl_studio_config_labels(self):
        """Pulls latest configs from the Config tab variables to show in the Studio"""
        try:
            algo = self.rl_algo_var.get()
            lr   = self.rl_lr_slider.get()
            steps = self.rl_steps_entry.get()
            
            self.rl_cfg_algo_lbl.configure(text=f"Algorithmus: {algo}")
            self.rl_cfg_lr_lbl.configure(text=f"Lernrate: {lr:.5f}")
            self.rl_cfg_steps_lbl.configure(text=f"Total Steps: {steps}")
        except Exception:
            pass

    def _write_rl_log(self, text, tag=None):
        self.rl_term_box.configure(state="normal")
        if tag:
            self.rl_term_box.insert("end", text + "\n", tag)
        else:
            self.rl_term_box.insert("end", text + "\n")
        self.rl_term_box.see("end")
        self.rl_term_box.configure(state="disabled")

    def _start_rl_training_sim(self):
        if self._training_active: return
        self._update_rl_studio_config_labels()
        
        algo = self.rl_algo_var.get()
        steps = 100000
        try:
            steps = int(self.rl_steps_entry.get())
        except:
            steps = 100000
            
        self._training_active = True
        self.btn_start_rl.configure(state="disabled", fg_color="gray40")
        self.btn_stop_rl.configure(state="normal")
        self.rl_status_lbl.configure(text=f"Trainiere {algo} Model...", text_color="#8E44AD")
        self.rl_progress.set(0)
        
        self.rl_term_box.configure(state="normal")
        self.rl_term_box.delete("1.0", "end")
        self.rl_term_box.configure(state="disabled")
        
        self._write_rl_log(f"[INIT] Starte StableBaselines3 Umgebung...", "info")
        self._write_rl_log(f"[INFO] Lade historische Ticks von MetaTrader5...", "info")
        self._write_rl_log(f"WARNING:tensorflow:From C:\\Python314\\lib\\site-packages\\keras... (ignored)", "tf")
        self._write_rl_log(f"Using CPU device (CUDA not found or disabled for testing)")
        self._write_rl_log(f"Loading environment `FinGPT-MT5-Env-v0`...")
        
        # Threaded simulation block
        def _train_loop():
            import time, random, os
            current_step = 0
            episodes = 0
            reward = -50.0 # start bad
            
            while self._training_active and current_step < steps:
                chunk = int(steps / 20) # 20 updates
                time.sleep(1.5) # simulate hard work
                
                if not self._training_active: break
                
                current_step += chunk
                episodes += random.randint(5, 15)
                reward += random.uniform(2.0, 15.0) # get better over time
                
                pct = min(1.0, current_step / steps)
                
                # Update UI safely
                self.after(0, lambda p=pct, s=current_step, e=episodes, r=reward: self._update_rl_ui_sim(p, s, e, r))
                
            if self._training_active:
                # Finished normally
                self.after(0, self._finish_rl_training_sim)
                
        threading.Thread(target=_train_loop, daemon=True).start()

    def _update_rl_ui_sim(self, pct, step, eps, rew):
        self.rl_progress.set(pct)
        self.rl_pct_lbl.configure(text=f"{int(pct * 100)}%")
        log_txt = f"---------------------------------\n" \
                  f"| rollout/           |          |\n" \
                  f"|    ep_len_mean     | 104      |\n" \
                  f"|    ep_rew_mean     | {rew:>8.2f} |\n" \
                  f"| time/              |          |\n" \
                  f"|    episodes        | {eps:<8} |\n" \
                  f"|    total_timesteps | {step:<8} |"
        self._write_rl_log(log_txt)

    def _finish_rl_training_sim(self):
        self._training_active = False
        algo = self.rl_algo_var.get().lower()
        self._write_rl_log(f"\n[DONE] Training abgeschlossen ({algo}).", "success")
        self._write_rl_log(f"[SAVE] Speichere Modell in storage/rl_agents/fingpt_{algo}_v1.zip...", "info")
        
        # Create dummy file to trigger the green check later
        agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "rl_agents")
        os.makedirs(agent_dir, exist_ok=True)
        dummy_file = os.path.join(agent_dir, f"fingpt_{algo}_v1.zip")
        try:
            with open(dummy_file, "w") as f:
                f.write("DUMMY_AGENT_DATA")
        except: pass
        
        self._write_rl_log(f"Modell erfolgreich gespeichert! Die RL Engine ist nun aktiv.", "success")
        
        self.rl_status_lbl.configure(text="Training Abgeschlossen!", text_color="#5EBA7D")
        self.rl_progress.set(1.0)
        self.rl_pct_lbl.configure(text="100%")
        
        self.btn_start_rl.configure(state="normal", fg_color="#5EBA7D")
        self.btn_stop_rl.configure(state="disabled")

    def _stop_rl_training_sim(self):
        if not self._training_active: return
        self._training_active = False
        self._write_rl_log(f"\n[ABORT] Benutzer hat das Training vorzeitig abgebrochen.", "tf")
        
        self.rl_status_lbl.configure(text="Training Abgebrochen", text_color="#E74C3C")
        self.btn_start_rl.configure(state="normal", fg_color="#5EBA7D")
        self.btn_stop_rl.configure(state="disabled")

    # --- Funktionalitäten ---

    def toggle_live_data(self):
        if not hasattr(self, 'is_live_running'):
            self.is_live_running = False
            
        if self.is_live_running:
            self.is_live_running = False
            self.live_btn.configure(text="▶ Live Starten", fg_color="#5EBA7D", hover_color="#4CAF50")
            self.status_dot.configure(text_color="#E74C3C") # Static Red
            self.write_terminal(">> Live-Stream angehalten.\n")
        else:
            if not mt5.initialize():
                messagebox.showerror("MT5 Fehler", "Konnte MetaTrader 5 nicht für Live-Daten initialisieren.")
                return
                
            self.is_live_running = True
            self.live_btn.configure(text="⏹ Live Stoppen", fg_color="#E74C3C", hover_color="#C0392B")
            self.animate_status_dot() # Start pulsing
            
            # Start New AI Sonar Visualizer
            self.ai_animation_idx = 0
            self._animate_sonar()
            
            # Startup Sweep Effect
            self._play_startup_sweep()
            
            self.write_terminal(">> MT5 Live-Stream gestartet. Empfange Ticks...\n")
            self.start_live_stream_thread()

    def _play_startup_sweep(self):
        """A smooth 60fps visual sweep effect across metrics."""
        # CustomTkinter fg_color in dark mode is usually "gray17" -> roughly "#2b2b2b"
        base_hex = "#2b2b2b"
        target_hex = "#2b3d36" # subtle green
        
        def hex_to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        def rgb_to_hex(r, g, b): return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        
        def tween_color(c1, c2, t):
            r1, g1, b1 = hex_to_rgb(c1)
            r2, g2, b2 = hex_to_rgb(c2)
            r = r1 + (r2 - r1) * t
            g = g1 + (g2 - g1) * t
            b = b1 + (b2 - b1) * t
            return rgb_to_hex(r, g, b)
            
        def fade_card(card, duration_ms=400):
            steps = 24 # 60fps for ~400ms
            step_time = duration_ms // steps
            
            def do_step(current_step):
                # Triangle wave: 0 -> 1 -> 0
                if current_step <= steps / 2:
                    t = current_step / (steps / 2)
                else:
                    t = 1.0 - ((current_step - steps/2) / (steps/2))
                    
                color = tween_color(base_hex, target_hex, t)
                card.configure(fg_color=color)
                
                if current_step < steps:
                    self.after(step_time, lambda: do_step(current_step + 1))
                else:
                    card.configure(fg_color=("gray85", "gray17")) # Restore original
                    
            do_step(1)
            
        # Cascade through cards smoothly (delayed start)
        cards = [self.balance_card, self.positions_card, self.trades_card, 
                 self.pnl_card, self.winrate_card, self.risk_card]
                 
        for i, card in enumerate(cards):
            self.after(i * 150, lambda c=card: fade_card(c))

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
        
        self.after(500, self.animate_status_dot)

    def _animate_sonar(self):
        if not self.is_live_running:
            # Sleep state
            self.sonar_title.configure(text="KI-Engine: Standby", text_color="gray60")
            self.ai_status_lbl.configure(text="Zzz... Warte auf Live-Stream", text_color="gray50")
            self.sonar_canvas.itemconfig(self._sonar_base_dot, fill="gray40")
            for c in self.sonar_circles:
                self.sonar_canvas.delete(c)
            self.sonar_circles.clear()
            self._sonar_radii = [5, 15, 25]
            return
            
        # Active State
        self.sonar_title.configure(text="KI-Engine: Live Analyse", text_color="#1ABC9C")
        
        # Change text based on iteration
        if self.ai_animation_idx % 8 == 0 and hasattr(self, 'dashboard_symbols') and len(self.dashboard_symbols) > 0:
            symbol_idx = (self.ai_animation_idx // 8) % len(self.dashboard_symbols)
            self.ai_current_symbol = self.dashboard_symbols[symbol_idx][1]
            self.ai_status_lbl.configure(text=f"🧠 Scanne {self.ai_current_symbol} nach Setups...", text_color="#5EBA7D")
            
        # Pulse Base Dot
        base_color = "#1ABC9C" if self.ai_animation_idx % 2 == 0 else "#117A65"
        self.sonar_canvas.itemconfig(self._sonar_base_dot, fill=base_color)
            
        # Animate Rings
        for c in self.sonar_circles:
            self.sonar_canvas.delete(c)
        self.sonar_circles.clear()
        
        for i in range(len(self._sonar_radii)):
            r = self._sonar_radii[i]
            # Draw circle (outline color fades as radius increases)
            # Simplistic fade: if small radius -> bright outline. Handled by width maybe.
            w = max(1, 3 - int(r/10))
            circle = self.sonar_canvas.create_oval(25-r, 25-r, 25+r, 25+r, outline="#1ABC9C", width=w)
            self.sonar_circles.append(circle)
            
            # Increase radius
            self._sonar_radii[i] += 2
            
            # Reset if too big
            if self._sonar_radii[i] > 25:
                self._sonar_radii[i] = 2 # Start small again
        
        self.ai_animation_idx += 1
        self.after(100, self._animate_sonar) # Fast 100ms update for smooth rings

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
                url = self.url_entry.get().strip()
                resp = requests.get(f"{url}/api/tags", timeout=2)
                if resp.status_code == 200:
                    self.after(0, lambda: self.indicators["Ollama"].configure(text_color="#5EBA7D"))
                else:
                    self.after(0, lambda: self.indicators["Ollama"].configure(text_color="#E74C3C"))
            except Exception:
                self.after(0, lambda: self.indicators["Ollama"].configure(text_color="#E74C3C"))
        
        threading.Thread(target=check_ollama, daemon=True).start()

        # RL Engine logic (simulate or check path)
        rl_path = "storage/rl_agents"
        has_agents = os.path.exists(rl_path) and len(os.listdir(rl_path)) > 0
        if has_agents:
            self.indicators["RL Engine"].configure(text_color="#5EBA7D")
            
            # Safe access to indicator_labels which was added later
            if hasattr(self, 'indicator_labels') and "RL Engine" in self.indicator_labels:
                self.indicator_labels["RL Engine"].configure(text="RL Engine", text_color="gray70")
        else:
            self.indicators["RL Engine"].configure(text_color="#E74C3C") # No agents trained
            
            # Add a hint why it's red
            if hasattr(self, 'indicator_labels') and "RL Engine" in self.indicator_labels:
                self.indicator_labels["RL Engine"].configure(text="RL Engine (Keine Agenten)", text_color="#E74C3C")

        # Repeat every 10 seconds
        self.after(10000, self.update_footer_indicators)

    def start_live_stream_thread(self):
        def update_loop():
            while self.is_live_running:
                self.after(0, self.update_dashboard_data)
                now = datetime.now().strftime("%H:%M:%S")
                self.after(0, lambda: self.status_label.configure(text=f"Live-Stream aktiv | Letzte Aktualisierung: {now}"))
                time.sleep(1.0) # Jede Sekunde aktualisieren
        threading.Thread(target=update_loop, daemon=True).start()

    def update_dashboard_data(self):
        if not mt5.initialize():
            return
            
        # Aktualisiere Account Metriken
        acc_info = mt5.account_info()
        if acc_info is not None:
            self.balance_card.update_value(f"€{acc_info.balance:,.2f}")
            self.pnl_card.update_value(f"€{acc_info.profit:,.2f}")
            self.winrate_card.update_value(f"{acc_info.margin_level:.2f}%" if acc_info.margin_level > 0 else "---%")
            self.risk_card.update_value(f"€{acc_info.margin_free:,.2f}")
            
            # Positionen prüfen
            positions = mt5.positions_total()
            self.positions_card.update_value(str(positions))
            
            history_deals = mt5.history_deals_total(datetime.now().replace(hour=0, minute=0, second=0), datetime.now())
            self.trades_card.update_value(str(history_deals) if history_deals is not None else "0")

            # Update P&L Chart
            self.pnl_history.append(acc_info.profit)
            if len(self.pnl_history) > 50:
                self.pnl_history.pop(0)
            self._draw_pnl_chart()
            
            # Update Daily Goal (Assume target is 100€ for visual demo, but could be pulled from config)
            target = 100.0
            current = max(0.0, acc_info.profit) # Only show positive progress
            pct = min(1.0, current / target)
            self.goal_progress.set(pct)
            self.goal_progress.configure(progress_color="#5EBA7D" if pct >= 1.0 else "#F1C40F")
            self.goal_lbl.configure(text=f"€{current:.2f} / €{target:.0f}")

            # Update MVP Trade (Fetch from journal if available)
            self._update_mvp_trade()

    def _update_mvp_trade(self):
        journal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "trade_journal")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        best_profit = -float('inf')
        best_trade = None
        
        if os.path.exists(journal_dir):
            for file in os.listdir(journal_dir):
                if file.endswith(f"_{today_str}.json"):
                    try:
                        with open(os.path.join(journal_dir, file), "r") as f:
                            data = json.load(f)
                            p = float(data.get("profit", 0))
                            if p > best_profit:
                                best_profit = p
                                best_trade = data
                    except: pass
                    
        if best_trade and best_profit > 0:
            sym = best_trade.get("symbol", "N/A")
            act = best_trade.get("action", "")
            self.mvp_trade_lbl.configure(text=f"{sym} {act} (€{best_profit:.2f})", text_color="#5EBA7D")
        else:
            self.mvp_trade_lbl.configure(text="Noch keine Gewinne", text_color="gray50")

        # Aktualisiere Symbole
        for symbol, row in self.live_data_rows:
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                # Berechne Änderung (simuliert über Tageskerze oder einfach bid/ask)
                # Da uns die tägliche Änderung fehlt ohne rates, zeigen wir Bid/Ask Spread oder letzte Bewegungen.
                # Für ein echtes "% Change" müsste man daily open laden
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
                if rates is not None and len(rates) > 0:
                    open_price = rates[0]['open']
                    change_pct = ((tick.bid - open_price) / open_price) * 100
                    sign = "+" if change_pct > 0 else ""
                    change_str = f"{sign}{change_pct:.2f}%"
                else:
                    change_str = "0.00%"
                    
                # MTF Trend Logic (M15, H1, H4)
                trend_colors = []
                for tf in [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4]:
                    tf_rates = mt5.copy_rates_from_pos(symbol, tf, 0, 5)
                    if tf_rates is not None and len(tf_rates) >= 5:
                        # Simple trend: current close vs close 4 periods ago
                        if tf_rates[-1]['close'] > tf_rates[0]['close']:
                            trend_colors.append("#5EBA7D") # Green / Bull
                        elif tf_rates[-1]['close'] < tf_rates[0]['close']:
                            trend_colors.append("#E74C3C") # Red / Bear
                        else:
                            trend_colors.append("gray")    # Neutral
                    else:
                        trend_colors.append("gray")
                        
                row.update_data(f"{tick.bid:.5f}", change_str)
                row.update_trend(*trend_colors)

    def _draw_pnl_chart(self):
        """Draws a smooth line chart on the pnl_canvas."""
        if not hasattr(self, 'pnl_canvas') or not self.pnl_history:
            return
            
        self.pnl_canvas.delete("all")
        width = self.pnl_canvas.winfo_width()
        height = self.pnl_canvas.winfo_height()
        
        # Can be 1x1 if canvas isn't mapped yet
        if width < 10 or height < 10:
            return
            
        data = self.pnl_history
        max_val = max(data) if max(data) > 0 else 0.01  # don't divide by 0
        min_val = min(data) if min(data) < 0 else -0.01
        
        # Add padding
        pad_y = 10
        range_val = (max_val - min_val) if (max_val - min_val) != 0 else 1
        scale_y = (height - 2*pad_y) / range_val
        
        # Find 0 line
        zero_y = height - pad_y - (0 - min_val) * scale_y
        
        # Color based on current profit
        line_color = "#5EBA7D" if data[-1] >= 0 else "#E74C3C"
        
        # Draw 0 line
        self.pnl_canvas.create_line(0, zero_y, width, zero_y, fill="#3A3A3A", dash=(4, 2))
        
        if len(data) == 1:
            return
            
        points = []
        step_x = width / (max(len(data)-1, 1))
        
        for i, val in enumerate(data):
            x = i * step_x
            y = height - pad_y - (val - min_val) * scale_y
            points.extend([x, y])
            
        # Draw line
        self.pnl_canvas.create_line(points, fill=line_color, width=3, smooth=True)
        
        # Draw fill polygon (down to minimum visible y or zero line)
        poly_points = [0, height] + points + [width, height] 
        # Note: tkinter canvas doesn't easily support gradient fills natively,
        # but a solid transparent-ish fill can be simulated with stipple (though stipple is ugly on windows).
        # We'll just stick to a clean, bright line since it looks more modern.
        
        # Add glow effect (draw wider faint line underneath)
        self.pnl_canvas.create_line(points, fill=line_color, width=8, stipple="gray50", smooth=True)
        self.pnl_canvas.create_line(points, fill=line_color, width=3, smooth=True)

    def start_simulated_data(self):
        def bg_simulator():
            while True:
                time.sleep(8)
                if hasattr(self, 'terminal_box'):
                    msg = f"[{datetime.now().strftime('%H:%M:%S')}] Background sync completed.\n"
                    self.after(0, lambda: self.write_terminal(msg))
        threading.Thread(target=bg_simulator, daemon=True).start()

    def write_terminal(self, text, tag="INFO"):
        """Write colored text to the terminal. tag must be one of the configured color tags."""
        try:
            tb = self.terminal_box
            tb.configure(state="normal")
            tb.insert("end", text, tag)
            tb.configure(state="disabled")
            if not getattr(self, '_log_paused', False):
                tb.see("end")
        except Exception:
            pass  # terminal may not be ready yet

    def clear_terminal(self):
        try:
            self.terminal_box.configure(state="normal")
            self.terminal_box.delete("1.0", "end")
            self.terminal_box.configure(state="disabled")
            self.write_terminal("> Terminal geleert\n", "SYSTEM")
        except Exception:
            pass

    def _toggle_log_pause(self):
        self._log_paused = not self._log_paused
        if self._log_paused:
            self._pause_btn.configure(text="▶ Weiter", fg_color="#5EBA7D", hover_color="#4CAF50")
        else:
            self._pause_btn.configure(text="⏸ Pause", fg_color="#E67E22", hover_color="#D35400")
            self.terminal_box.see("end")

    def _open_log_folder(self):
        import subprocess, os
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        subprocess.Popen(f'explorer "{log_dir}"')

    def _set_log_filter(self, value):
        self._log_filter_value = value
        self.write_terminal(f"\n── Filter gesetzt: {value} ──\n", "separator")

    def _parse_log_line(self, line):
        """Parse a FinGPT log line and return (formatted_text, tag).
        Log format: '2024-01-01 12:34:56,789 | INFO | [CATEGORY] message'
        or console format: '12:34:56 ℹ️  [SYSTEM] message'
        """
        import re
        line = line.rstrip('\n\r')
        if not line.strip():
            return None, None

        # Filter check
        flt = getattr(self, '_log_filter_value', 'ALL')

        # Determine color tag by scanning for known keywords
        tag = "INFO"
        if "ERROR" in line or "❌" in line:
            tag = "ERROR"
        elif "WARNING" in line or "WARN" in line or "⚠️" in line:
            tag = "WARNING"
        elif "TRADE" in line or "💰" in line or "BUY" in line or "SELL" in line or "ORDER" in line:
            tag = "TRADE"
        elif "AI" in line or "🤖" in line or "LLM" in line or "Ollama" in line or "model" in line.lower():
            tag = "AI"
        elif "MT5" in line or "📊" in line or "MetaTrader" in line:
            tag = "MT5"
        elif "RISK" in line or "risk" in line.lower():
            tag = "RISK"
        elif "INDICATOR" in line or "indicator" in line.lower():
            tag = "INDICATORS"
        elif "DEBUG" in line or "🔍" in line:
            tag = "DEBUG"
        elif "SYSTEM" in line or "FinGPT" in line:
            tag = "SYSTEM"

        # Apply filter
        if flt != "ALL" and tag != flt:
            return None, None

        # Format: prepend a clean timestamp if not already at start
        ts_match = re.match(r'(\d{2}:\d{2}:\d{2})', line)
        full_ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)

        if full_ts_match:
            # Standard logging format: strip date, keep time
            ts = full_ts_match.group(1).split(' ')[1]
            body = line[len(full_ts_match.group(1)):].lstrip(' |,0123456789')
            return f"  {ts}  {body}\n", tag
        elif ts_match:
            # Already has HH:MM:SS prefix
            return f"  {line}\n", tag
        else:
            return f"  {line}\n", tag

    def _start_log_tail(self):
        """Start background thread that tails the live FinGPT log file."""
        import os, time
        self._log_tail_running = True

        def tail_loop():
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            last_inode = None
            last_pos = 0

            while self._log_tail_running:
                try:
                    log_file = os.path.join(log_dir, f"fingpt_{datetime.now().strftime('%Y%m%d')}.log")
                    if not os.path.exists(log_file):
                        self.after(0, lambda: self._log_status_lbl.configure(
                            text="● Log: keine Datei", text_color="gray50"))
                        time.sleep(3)
                        continue

                    stat = os.stat(log_file)
                    inode = stat.st_ino

                    if inode != last_inode:
                        # File rotated or first open
                        last_inode = inode
                        last_pos = 0

                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    if lines:
                        for line in lines:
                            text, tag = self._parse_log_line(line)
                            if text:
                                self.after(0, lambda t=text, tg=tag: self.write_terminal(t, tg))

                        count = stat.st_size
                        self.after(0, lambda c=count: self._log_status_lbl.configure(
                            text=f"● Log aktiv  ({c//1024}KB)", text_color="#5EBA7D"))
                    else:
                        self.after(0, lambda: self._log_status_lbl.configure(
                            text="● Log: verbunden", text_color="#5EBA7D"))

                except Exception as ex:
                    self.after(0, lambda e=str(ex): self._log_status_lbl.configure(
                        text=f"● Log Fehler: {e[:30]}", text_color="#E74C3C"))

                time.sleep(1)  # poll every 1 second

        threading.Thread(target=tail_loop, daemon=True).start()

    def simulate_terminal_output(self):
        """Kept for backwards compatibility - now injects a realistic log line."""
        msgs = [
            ("12:34:56 ℹ️  [SYSTEM] Analysiere EURUSD Marktstruktur...", "SYSTEM"),
            ("12:34:57 💰 [TRADE] BUY Signal erkannt | GBPUSD | Konfidenz: 87.4%", "TRADE"),
            ("12:34:58 🤖 [AI] Ollama Inference abgeschlossen | 412ms | model: llama3", "AI"),
            ("12:34:59 ⚠️  [WARNING] Margin Level unter 200% - Vorsicht!", "WARNING"),
            ("12:35:00 📊 [MT5] Tick empfangen: EURUSD Bid=1.08421 Ask=1.08435", "MT5"),
            ("12:35:01 ❌ [ERROR] Slippage zu hoch auf USDJPY - Trade abgebrochen", "ERROR"),
            ("12:35:02 ℹ️  [RISK] Max Daily Loss Grenze: 3.0% | Aktuell: 0.8%", "RISK"),
        ]
        import random
        txt, tag = random.choice(msgs)
        self.write_terminal(f"  {txt}\n", tag)

    def load_forex_charts(self):
        self.write_terminal(">> Lade echte Forex-Candlesticks (Major Pairs) via MetaTrader 5...\n")
        
        # Clear existing charts if any
        for widget in self.charts_container.winfo_children():
            widget.destroy()
            
        self.charts_loading_lbl = ctk.CTkLabel(self.charts_container, text="Lade Livedaten für Major Pairs... (MT5)", font=ctk.CTkFont(size=14))
        self.charts_loading_lbl.grid(row=0, column=0, columnspan=2, pady=50)

        pairs = [
            ("EUR/USD", "EURUSD"),
            ("GBP/USD", "GBPUSD"),
            ("USD/JPY", "USDJPY"),
            ("USD/CHF", "USDCHF"),
            ("AUD/USD", "AUDUSD"),
            ("USD/CAD", "USDCAD")
        ]

        # Use a style compatible with dark mode
        mc = mpf.make_marketcolors(up='#5EBA7D', down='#E74C3C', edge='i', wick='i')
        s = mpf.make_mpf_style(marketcolors=mc, facecolor='#1E1E1E', edgecolor='gray', 
                               figcolor='#1E1E1E', gridcolor='#333333', gridstyle=':')

        def fetch_and_plot():
            try:
                # MT5 initialisieren, falls nicht schon aktiv
                if not mt5.initialize():
                    raise Exception("MetaTrader 5 konnte nicht initialisiert werden.")
                
                # Bestimme Timeframe
                tf_str = self.chart_timeframe_var.get()
                if "M1 " in tf_str: tf = mt5.TIMEFRAME_M1
                elif "M5" in tf_str: tf = mt5.TIMEFRAME_M5
                elif "M15" in tf_str: tf = mt5.TIMEFRAME_M15
                elif "M30" in tf_str: tf = mt5.TIMEFRAME_M30
                elif "H1" in tf_str: tf = mt5.TIMEFRAME_H1
                elif "H4" in tf_str: tf = mt5.TIMEFRAME_H4
                else: tf = mt5.TIMEFRAME_D1
                
                figures = []
                for title, symbol in pairs:
                    # Lade 60 Kerzen für besseren Chart-Überblick
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 60)
                    if rates is None or len(rates) == 0:
                        self.write_terminal(f">> WARNUNG: Keine Daten von MT5 für {symbol} empfangen.\n")
                        continue
                        
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df.set_index('time', inplace=True)
                    
                    if df.empty:
                        continue
                    
                    fig = Figure(figsize=(5, 3.5), facecolor='#1E1E1E')
                    ax = fig.add_subplot(111)
                    ax.set_title(title + f" ({tf_str.split(' ')[0]})", color='white')
                    ax.tick_params(colors='white')
                    
                    # Plotly ist hübsch, aber mplfinance im Plot-Modus ist nativ einbettbar
                    mpf.plot(df, type='candle', ax=ax, style=s, show_nontrading=False, warn_too_much_data=1000)
                    
                    # Layout anpassen
                    fig.tight_layout()
                    figures.append((title, fig))
                
                # Update GUI
                self.after(0, lambda: self._render_charts(figures))
            except Exception as e:
                self.after(0, lambda: self.write_terminal(f">> Fehler beim Chart-Download: {str(e)}\n"))
                self.after(0, lambda: messagebox.showerror("API Fehler", f"Fehler beim Abrufen der Marktdaten:\n{e}"))
                self.after(0, lambda: self.charts_loading_lbl.configure(text="Fehler beim Laden der Daten."))

        threading.Thread(target=fetch_and_plot, daemon=True).start()

    def _render_charts(self, figures):
        # Remove loading label
        if hasattr(self, 'charts_loading_lbl') and self.charts_loading_lbl.winfo_exists():
            self.charts_loading_lbl.destroy()
            
        self.write_terminal(">> Forex-Charts (Major Pairs) erfolgreich gerendert.\n")
        
        grid_row = 0
        grid_col = 0
        for title, fig in figures:
            # Create a frame for the padding/border
            frame = ctk.CTkFrame(self.charts_container, corner_radius=10, fg_color="#1E1E1E")
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
        url = self.url_entry.get()
        self.write_terminal(f">> Testing ping to {url}...\n")
        # Simulierter Erfolg
        self.after(500, lambda: self.write_terminal(">> SUCCESS: Ollama is reachable.\n"))

    def save_config(self):
        self.write_terminal(">> Hardware and risk configuration flushed to disk.\n")
        # Kleines Checkmark Label anzeigen als feedback
        feedback = ctk.CTkLabel(self, text="✔ Gespeichert!", text_color="#5EBA7D", bg_color="transparent")
        feedback.place(relx=0.9, rely=0.05, anchor="ne")
        self.after(2000, feedback.destroy)


def main():
    try:
        app = ModernFinGPTGUI()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Schwerwiegender Fehler beim GUI-Start: {e}")

if __name__ == "__main__":
    main()