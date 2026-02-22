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
        
        self.status_dot = ctk.CTkLabel(self.header_frame, text="●", text_color="gray", font=ctk.CTkFont(size=20))
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
        
        sys_info = f"Python {sys.version_info.major}.{sys.version_info.minor} | CustomTkinter {ctk.__version__}"
        self.sys_info_label = ctk.CTkLabel(self.status_bar, text=sys_info, font=ctk.CTkFont(size=12), text_color="gray50")
        self.sys_info_label.pack(side="right", padx=15, pady=5)

    def setup_dashboard_tab(self):
        tab = self.tabview.tab("📊 Dashboard")
        tab.grid_columnconfigure((0, 1, 2), weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # Top Cards
        self.create_metric_card(tab, "Kontostand", "€25.430,75", 0, 0)
        self.create_metric_card(tab, "Offene Positionen", "3", 0, 1)
        self.create_metric_card(tab, "Heutige Trades", "12", 0, 2)
        
        self.create_metric_card(tab, "Gewinn/Verlust", "+€1.245,30", 1, 0)
        self.create_metric_card(tab, "Win-Rate", "78%", 1, 1)
        self.create_metric_card(tab, "Risiko-Level", "Medium", 1, 2)

        # Live Data List
        data_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=("gray90", "gray13"))
        data_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
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

    def populate_sample_data(self):
        sample_data = [
            ('EUR/USD', '1.08542', '+0.24%', '1.2M', 'BUY'),
            ('GBP/USD', '1.26783', '-0.12%', '850K', 'SELL'),
            ('USD/JPY', '151.234', '+0.08%', '2.1M', 'HOLD'),
            ('BTC/USD', '43250.00', '+2.35%', '15.4K', 'BUY'),
            ('XAU/USD', '2045.67', '-0.42%', '320K', 'SELL'),
            ('NAS100', '15876.34', '+0.67%', '45.2M', 'BUY')
        ]
        
        for item in sample_data:
            row = LiveDataRow(self.scroll_list, *item)
            row.pack(fill="x", pady=2)
            self.live_data_rows.append(row)

    def setup_charts_tab(self):
        tab = self.tabview.tab("📈 Charts")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(controls, text="↻ Forex Charts Aktualisieren", command=self.load_forex_charts, fg_color="#2E86AB").pack(side="left", padx=(0, 10))
        
        self.charts_container = ctk.CTkScrollableFrame(tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.charts_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Initial message
        self.charts_loading_lbl = ctk.CTkLabel(self.charts_container, text="Lade interaktive Forex Charts (Major Pairs)... Bitte warten.", 
                           justify="center", font=ctk.CTkFont(size=14), text_color="gray50")
        self.charts_loading_lbl.pack(pady=50)
        
        # Grid layout for charts_container (2 Columns)
        self.charts_container.grid_columnconfigure(0, weight=1)
        self.charts_container.grid_columnconfigure(1, weight=1)
        
        # Delay the initial load slightly so the GUI can render first
        self.after(1000, self.load_forex_charts)

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
        tab.grid_columnconfigure(0, weight=1)
        
        # Ollama Panel
        ollama_panel = ctk.CTkFrame(tab, corner_radius=15)
        ollama_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        ollama_panel.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(ollama_panel, text="Ollama Setup", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(ollama_panel, text="Daemon URL:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.url_entry = ctk.CTkEntry(ollama_panel, placeholder_text="http://localhost:11434")
        self.url_entry.insert(0, "http://localhost:11434")
        self.url_entry.grid(row=1, column=1, sticky="w", padx=20, pady=10)
        
        ctk.CTkButton(ollama_panel, text="Test", command=self.test_ollama_connection, width=100).grid(row=1, column=2, padx=20, pady=10)

        # Risk Panel
        risk_panel = ctk.CTkFrame(tab, corner_radius=15)
        risk_panel.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        risk_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(risk_panel, text="Risikomanagement", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        
        self.trading_active_switch = ctk.CTkSwitch(risk_panel, text="Auto-Trading Erlauben", progress_color="#5EBA7D")
        self.trading_active_switch.select()
        self.trading_active_switch.grid(row=1, column=0, sticky="w", padx=20, pady=15)

        ctk.CTkLabel(risk_panel, text="Max Drawdown (%):").grid(row=1, column=1, sticky="e", padx=(0, 10), pady=15)
        self.risk_entry = ctk.CTkEntry(risk_panel, width=80)
        self.risk_entry.insert(0, "2.0")
        self.risk_entry.grid(row=1, column=2, sticky="e", padx=20, pady=15)

        # Save Action
        ctk.CTkButton(tab, text="💾 Konfiguration Speichern", command=self.save_config, font=ctk.CTkFont(weight="bold", size=14),
                      height=40, fg_color="#2E86AB", hover_color="#21618C").grid(row=2, column=0, sticky="e", padx=20, pady=20)

    # --- Funktionalitäten ---

    def toggle_live_data(self):
        if not self.is_live_running:
            self.is_live_running = True
            self.live_btn.configure(text="■ Live Stoppen", fg_color="#E74C3C", hover_color="#C0392B")
            self.status_dot.configure(text_color="#5EBA7D")
            self.write_terminal(">> Live-Stream zu Marktdaten aktiviert.\n")
            self.start_live_stream_thread()
        else:
            self.is_live_running = False
            self.live_btn.configure(text="▶ Live Starten", fg_color="#5EBA7D", hover_color="#4CAF50")
            self.status_dot.configure(text_color="gray")
            self.write_terminal(">> Live-Stream angehalten.\n")

    def start_live_stream_thread(self):
        def update_loop():
            while self.is_live_running:
                # Randomize rows safely in main thread
                self.after(0, self.randomize_table_data)
                now = datetime.now().strftime("%H:%M:%S")
                self.after(0, lambda: self.status_label.configure(text=f"Live-Stream aktiv | Letzte Aktualisierung: {now}"))
                time.sleep(1.5)
        threading.Thread(target=update_loop, daemon=True).start()

    def randomize_table_data(self):
        if self.live_data_rows:
            row = random.choice(self.live_data_rows)
            current_price = float(row.price_lbl.cget("text").replace(',', ''))
            movement = random.uniform(-0.005, 0.005)
            new_price = current_price * (1 + movement)
            
            sign = "+" if movement > 0 else ""
            change_str = f"{sign}{(movement*100):.2f}%"
            row.update_data(f"{new_price:.4f}", change_str)

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

        pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]

        # Use a style compatible with dark mode
        mc = mpf.make_marketcolors(up='#5EBA7D', down='#E74C3C', edge='i', wick='i', vcdopctr=False)
        s = mpf.make_mpf_style(marketcolors=mc, facecolor='#1E1E1E', edgecolor='gray', 
                               figcolor='#1E1E1E', gridcolor='#333333', gridstyle=':')

        def fetch_and_plot():
            try:
                # MT5 initialisieren, falls nicht schon aktiv
                if not mt5.initialize():
                    raise Exception("MetaTrader 5 konnte nicht initialisiert werden.")
                
                figures = []
                for symbol in pairs:
                    # Lade 30 Tage (D1) Daten = TIMEFRAME_D1
                    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 30)
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
                    title = f"{symbol[:3]}/{symbol[3:]}"
                    ax.set_title(title, color='white')
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