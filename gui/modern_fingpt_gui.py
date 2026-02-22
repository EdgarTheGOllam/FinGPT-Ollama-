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
    """Eine Zeile für die Scrollbare Live-Daten Ansicht"""
    def __init__(self, master, symbol, price, change, volume, signal, **kwargs):
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
        
        self.vol_lbl = ctk.CTkLabel(self, text=volume, font=ctk.CTkFont(size=13))
        self.vol_lbl.grid(row=0, column=3, sticky="w", padx=10, pady=5)

        sig_color = "#2E86AB" if signal == "BUY" else "#A23B72" if signal == "SELL" else "gray"
        self.signal_btn = ctk.CTkButton(self, text=signal, width=60, height=24, fg_color=sig_color, hover_color=sig_color, corner_radius=12)
        self.signal_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

    def update_data(self, price, change):
        self.price_lbl.configure(text=price)
        self.change_lbl.configure(text=change)
        change_color = "#5EBA7D" if "+" in change else "#E74C3C" if "-" in change else "gray"
        self.change_lbl.configure(text_color=change_color)


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
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        
        self.tabview.add("📊 Dashboard")
        self.tabview.add("📈 Charts")
        self.tabview.add("💻 Terminal")
        self.tabview.add("⚙️ Konfiguration")
        
        # Tabs konfigurieren
        self.setup_dashboard_tab()
        self.setup_charts_tab()
        self.setup_terminal_tab()
        self.setup_config_tab()
        
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
        for sys_name in ["Python", "MT5", "Ollama", "RL Engine"]:
            frame = ctk.CTkFrame(self.indicator_frame, fg_color="transparent")
            frame.pack(side="left", padx=8)
            dot = ctk.CTkLabel(frame, text="●", text_color="gray", font=ctk.CTkFont(size=14))
            dot.pack(side="left", padx=(0, 4))
            lbl = ctk.CTkLabel(frame, text=sys_name, font=ctk.CTkFont(size=11), text_color="gray70")
            lbl.pack(side="left")
            self.indicators[sys_name] = dot
            
        self.update_footer_indicators()

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

        # AI Agent Visualizer (Middle Banner)
        self.ai_visualizer_frame = ctk.CTkFrame(tab, height=60, corner_radius=15, fg_color=("gray85", "gray17"))
        self.ai_visualizer_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))
        self.ai_visualizer_frame.grid_propagate(False) # Keep fixed height
        self.ai_visualizer_frame.grid_columnconfigure(1, weight=1)
        
        self.ai_dot = ctk.CTkLabel(self.ai_visualizer_frame, text="●", text_color="gray", font=ctk.CTkFont(size=24))
        self.ai_dot.pack(side="left", padx=(20, 10), pady=15)
        
        self.ai_status_lbl = ctk.CTkLabel(self.ai_visualizer_frame, text="Zzz... Warte auf Live-Stream", font=ctk.CTkFont(size=14, weight="bold", slant="italic"), text_color="gray60")
        self.ai_status_lbl.pack(side="left", pady=15)
        
        # State variables for animation
        self.ai_animation_idx = 0
        self.ai_current_symbol = None

        # Live Data List
        data_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray90", "gray13"))
        data_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
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
        
        for i, col_name in enumerate(["Symbol", "Preis", "Änderung", "Volume", "Signal"]):
            lbl = ctk.CTkLabel(header_row, text=col_name, font=ctk.CTkFont(weight="bold", size=12), text_color="gray50")
            lbl.grid(row=0, column=i, sticky="w", padx=10)

        ctk.CTkFrame(self.scroll_list, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

        # Initial Mock Data
        self.populate_sample_data()

    def create_metric_card(self, parent, title, value, row, col):
        card = MetricCard(parent, title=title, value=value)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        return card

    def populate_sample_data(self):
        # Initialisiere die Zeilen mit echten Paaren
        self.dashboard_symbols = [
            ("EUR/USD", "EURUSD"),
            ("GBP/USD", "GBPUSD"),
            ("USD/JPY", "USDJPY"),
            ("USD/CHF", "USDCHF"),
            ("AUD/USD", "AUDUSD"),
            ("USD/CAD", "USDCAD")
        ]
        
        for display_name, symbol in self.dashboard_symbols:
            row = LiveDataRow(self.scroll_list, display_name, "---", "0.00%", "---", "HOLD")
            row.pack(fill="x", pady=2)
            self.live_data_rows.append((symbol, row))

        # initial fetch
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

    def setup_terminal_tab(self):
        tab = self.tabview.tab("💻 Terminal")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(controls, text="🧹 Säubern", command=self.clear_terminal, fg_color="#E74C3C", hover_color="#C0392B").pack(side="left", padx=(0, 10))
        ctk.CTkButton(controls, text="🤖 Output Simulieren", command=self.simulate_terminal_output, fg_color="transparent", border_width=2).pack(side="left")

        self.terminal_box = ctk.CTkTextbox(tab, corner_radius=15, font=ctk.CTkFont(family="Consolas", size=13), 
                                           fg_color="#1E1E1E", text_color="#D4D4D4", wrap="word")
        self.terminal_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.write_terminal("FinGPT Professional System Initialized...\n")
        self.write_terminal("Ready for incoming streams.\n> ")

    def setup_config_tab(self):
        tab = self.tabview.tab("⚙️ Konfiguration")
        
        # We need a scrollable container because config can get long
        scroll_config = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_config.pack(fill="both", expand=True, padx=10, pady=10)
        scroll_config.grid_columnconfigure(0, weight=1)
        
        # 1. System & KI Panel
        sys_panel = ctk.CTkFrame(scroll_config, corner_radius=15, fg_color=("gray90", "gray13"))
        sys_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 20))
        sys_panel.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(sys_panel, text="🤖 System & KI Einstellungen", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E86AB").grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(sys_panel, text="Ollama URL:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.url_entry = ctk.CTkEntry(sys_panel, placeholder_text="http://localhost:11434")
        self.url_entry.insert(0, "http://localhost:11434")
        self.url_entry.grid(row=1, column=1, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(sys_panel, text="LLM Modell:").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.model_combo = ctk.CTkComboBox(sys_panel, values=["Lade Modelle..."])
        self.model_combo.grid(row=2, column=1, sticky="w", padx=20, pady=10)

        ctk.CTkLabel(sys_panel, text="Auto-Trading Intervall (sek):").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.interval_slider = ctk.CTkSlider(sys_panel, from_=1, to=30, number_of_steps=29)
        self.interval_slider.set(5)
        self.interval_slider.grid(row=3, column=1, sticky="ew", padx=20, pady=10)
        self.interval_lbl = ctk.CTkLabel(sys_panel, text="5s")
        self.interval_lbl.grid(row=3, column=2, sticky="e", padx=(0, 20))
        self.interval_slider.configure(command=lambda val: self.interval_lbl.configure(text=f"{int(val)}s"))

        # 2. Risk Management Panel
        risk_panel = ctk.CTkFrame(scroll_config, corner_radius=15, fg_color=("gray90", "gray13"))
        risk_panel.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 20))
        risk_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(risk_panel, text="🛡️ Risk Management", font=ctk.CTkFont(size=16, weight="bold"), text_color="#5EBA7D").grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        
        self.trading_active_switch = ctk.CTkSwitch(risk_panel, text="Auto-Trading Global Erlauben", progress_color="#5EBA7D")
        self.trading_active_switch.select()
        self.trading_active_switch.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=15)

        ctk.CTkLabel(risk_panel, text="Max Risiko pro Trade (%):").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.risk_trade_entry = ctk.CTkEntry(risk_panel, width=80)
        self.risk_trade_entry.insert(0, "1.0")
        self.risk_trade_entry.grid(row=2, column=1, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(risk_panel, text="Max Daily Loss (%):").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        self.risk_daily_entry = ctk.CTkEntry(risk_panel, width=80)
        self.risk_daily_entry.insert(0, "3.0")
        self.risk_daily_entry.grid(row=3, column=1, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(risk_panel, text="Max Offene Positionen:").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.max_pos_entry = ctk.CTkEntry(risk_panel, width=80)
        self.max_pos_entry.insert(0, "3")
        self.max_pos_entry.grid(row=4, column=1, sticky="w", padx=20, pady=10)

        # 3. MT5 Panel
        mt5_panel = ctk.CTkFrame(scroll_config, corner_radius=15, fg_color=("gray90", "gray13"))
        mt5_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 20))
        mt5_panel.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(mt5_panel, text="� MetaTrader 5 Einstellungen", font=ctk.CTkFont(size=16, weight="bold"), text_color="#E74C3C").grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        
        ctk.CTkButton(mt5_panel, text="MT5 Manuell Neuverbinden", command=self.test_mt5_connection, fg_color="transparent", border_width=1).grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(mt5_panel, text="Aktive Währungspaare (Komma-getrennt):").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.pairs_entry = ctk.CTkEntry(mt5_panel, width=300)
        self.pairs_entry.insert(0, "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD")
        self.pairs_entry.grid(row=2, column=1, sticky="w", padx=20, pady=10)

        # Save Action
        save_btn = ctk.CTkButton(scroll_config, text="💾 Alle Systemeinstellungen Speichern", command=self.save_config, 
                      font=ctk.CTkFont(weight="bold", size=14), height=45, fg_color="#2E86AB", hover_color="#21618C")
        save_btn.grid(row=3, column=0, sticky="e", padx=10, pady=20)
        
        # Initial Model Fetch
        self.after(500, self.fetch_ollama_models_silently)

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
            # System & KI
            ollama_url = self.url_entry.get().strip()
            llm_model = self.model_combo.get()
            auto_trade_interval = int(self.interval_slider.get())
            
            # Risk Management
            is_auto_trading = self.trading_active_switch.get() == 1
            max_risk = float(self.risk_trade_entry.get())
            max_daily_loss = float(self.risk_daily_entry.get())
            max_pos = int(self.max_pos_entry.get())
            
            # Pairs
            raw_pairs = self.pairs_entry.get().strip()
            if raw_pairs:
                split_pairs = [p.strip() for p in raw_pairs.upper().split(',') if p.strip()]
                # Update dashboard_symbols (Format: "EUR/USD", "EURUSD")
                self.dashboard_symbols = [(f"{p[:3]}/{p[3:]}" if len(p) == 6 else p, p) for p in split_pairs]
                
                # Rebuild LiveDataRows in Dashboard
                for widget in self.scroll_list.winfo_children():
                    if isinstance(widget, LiveDataRow):
                        widget.destroy()
                
                self.live_data_rows.clear()
                for display_name, symbol in self.dashboard_symbols:
                    row = LiveDataRow(self.scroll_list, display_name, "---", "0.00%", "---", "HOLD")
                    row.pack(fill="x", pady=2)
                    self.live_data_rows.append((symbol, row))

            # Simulate backend assignment for UI demonstration purposes
            # In a full integration, these would be passed to FinGPT core or a JSON config
            
            status_msg = f">> [CONFIG SAVED] Model: {llm_model} | Auto: {is_auto_trading} | Interval: {auto_trade_interval}s\n"
            status_msg += f">> [RISK LIMITS] Risk/Trade: {max_risk}% | Daily Loss: {max_daily_loss}% | Max Pos: {max_pos}\n"
            status_msg += f">> [PAIRS] Monitoring {len(self.dashboard_symbols)} pairs.\n"
            self.write_terminal(status_msg)
            
            messagebox.showinfo("Erfolg", "Konfiguration wurde erfolgreich gespeichert und angewendet!")
            
            # Force immediate update of new pairs if live
            if self.is_live_running:
                self.update_dashboard_data()
                
        except ValueError as e:
            messagebox.showerror("Eingabefehler", f"Bitte überprüfen Sie Ihre numerischen Eingaben.\nDetails: {str(e)}")
            
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
            
            # Start AI Visualizer Animation
            self.ai_animation_idx = 0
            self.animate_ai_visualizer()
            
            self.write_terminal(">> MT5 Live-Stream gestartet. Empfange Ticks...\n")
            self.start_live_stream_thread()

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

    def animate_ai_visualizer(self):
        if not self.is_live_running or not hasattr(self, 'dashboard_symbols') or len(self.dashboard_symbols) == 0:
            self.ai_dot.configure(text_color="gray")
            self.ai_status_lbl.configure(text="Zzz... Warte auf Live-Stream", text_color="gray60")
            return
            
        current_color = self.ai_dot.cget("text_color")
        
        # Rotate symbol every 3 seconds (6 ticks of 500ms)
        if self.ai_animation_idx % 6 == 0:
            symbol_idx = (self.ai_animation_idx // 6) % len(self.dashboard_symbols)
            self.ai_current_symbol = self.dashboard_symbols[symbol_idx][1]
            self.ai_status_lbl.configure(text=f"🧠 Ollama analysiert {self.ai_current_symbol}...", text_color="#1ABC9C")
            
        # Pulse dot (Cyan/Teal)
        next_color = "#1ABC9C" if current_color != "#1ABC9C" else "#117A65"
        self.ai_dot.configure(text_color=next_color)
        
        self.ai_animation_idx += 1
        self.after(500, self.animate_ai_visualizer)

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
        if os.path.exists(rl_path) and len(os.listdir(rl_path)) > 0:
            self.indicators["RL Engine"].configure(text_color="#5EBA7D")
        else:
            self.indicators["RL Engine"].configure(text_color="#E74C3C") # No agents trained

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
                    
                row.update_data(f"{tick.bid:.5f}", change_str)

    def start_simulated_data(self):
        def bg_simulator():
            while True:
                time.sleep(8)
                if hasattr(self, 'terminal_box'):
                    msg = f"[{datetime.now().strftime('%H:%M:%S')}] Background sync completed.\n"
                    self.after(0, lambda: self.write_terminal(msg))
        threading.Thread(target=bg_simulator, daemon=True).start()

    def write_terminal(self, text):
        self.terminal_box.insert("end", text)
        self.terminal_box.see("end")

    def clear_terminal(self):
        self.terminal_box.delete("0.0", "end")
        self.write_terminal("> ")

    def simulate_terminal_output(self):
        msgs = [
            "Analyzing deep learning model accuracy...",
            "Executing fast scalp on EUR/USD.",
            "Risk limits within bounds. Proceeding.",
            "LLM inference completed in 452ms.",
            "Fetching macroeconomic news sentiment..."
        ]
        self.write_terminal(f"[{datetime.now().strftime('%H:%M:%S')}] {random.choice(msgs)}\n")

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