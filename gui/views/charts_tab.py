import customtkinter as ctk
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import mplfinance as mpf
import MetaTrader5 as mt5
import pandas as pd
import threading

class ChartsView:
    def __init__(self, tab, app):
        self.tab = tab
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        tab = self.tab
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
    
        # Sub-Navigation for Charts
        self.app.charts_sub_tabs = ctk.CTkTabview(tab, corner_radius=10)
        self.app.charts_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
        self.app.charts_sub_tabs.add("🔲 Multi-View")
        self.app.charts_sub_tabs.add("🔎 Pattern Scanner")
        self.app.charts_sub_tabs.add("🔬 Advanced Analysis")
        self.app.charts_sub_tabs.add("🏦 SMC Scanner")
    
        # --- 1. Sub-Tab: Multi-View (Existing 2x3 Grid) ---
        multi_tab = self.app.charts_sub_tabs.tab("🔲 Multi-View")
        multi_tab.grid_columnconfigure(0, weight=1)
        multi_tab.grid_rowconfigure(1, weight=1)
    
        controls = ctk.CTkFrame(multi_tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
        ctk.CTkButton(controls, text="↻ Charts Aktualisieren", command=self.app.load_forex_charts, fg_color="#2979FF").pack(side="left", padx=(0, 10))
    
        # Timeframe Dropdown Menu
        self.app.chart_timeframe_var = ctk.StringVar(value="D1 (Täglich)")
        self.app.tf_combo = ctk.CTkComboBox(
            controls, 
            values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (Täglich)"], 
            variable=self.app.chart_timeframe_var,
            command=lambda choice: self.app.load_forex_charts()
        )
        self.app.tf_combo.pack(side="left", padx=10)
    
        self.app.charts_container = ctk.CTkScrollableFrame(multi_tab, corner_radius=15, fg_color="#1A1D24")
        self.app.charts_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    
        # Initial message
        self.app.charts_loading_lbl = ctk.CTkLabel(self.app.charts_container, text="Lade interaktive Forex Charts (Major Pairs)... Bitte warten.", 
                           justify="center", font=ctk.CTkFont(family="Inter", size=14), text_color="#8B949E")
        self.app.charts_loading_lbl.pack(pady=50)
    
        # Grid layout for charts_container (2 Columns)
        self.app.charts_container.grid_columnconfigure(0, weight=1)
        self.app.charts_container.grid_columnconfigure(1, weight=1)
    
        # --- 2. Sub-Tab: Pattern Scanner ---
        pattern_tab = self.app.charts_sub_tabs.tab("🔎 Pattern Scanner")
        pattern_tab.grid_columnconfigure(0, weight=1)
        pattern_tab.grid_rowconfigure(1, weight=1)
    
        scan_controls = ctk.CTkFrame(pattern_tab, fg_color="transparent")
        scan_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
        self.app.scan_tf_var = ctk.StringVar(value="D1 (T\u00e4glich)")
        ctk.CTkComboBox(scan_controls, values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (T\u00e4glich)"], variable=self.app.scan_tf_var, width=150).pack(side="left", padx=5)
        ctk.CTkButton(scan_controls, text="\U0001f50d Markt Scannen", command=self.run_pattern_scanner, fg_color="#E67E22", hover_color="#D35400").pack(side="left", padx=5)
        self.app.scan_status_lbl = ctk.CTkLabel(scan_controls, text="Klicke auf Scannen...", text_color="#8B949E")
        self.app.scan_status_lbl.pack(side="left", padx=15)
    
        self.app.pattern_list_frame = ctk.CTkScrollableFrame(pattern_tab, corner_radius=15, fg_color="#1A1D24")
        self.app.pattern_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    
        # Header for the scanner list
        ph_row = ctk.CTkFrame(self.app.pattern_list_frame, fg_color="transparent", height=30)
        ph_row.pack(fill="x", pady=(0, 5))
        ph_row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        for i, col_name in enumerate(["Symbol", "Timeframe", "Gefundenes Pattern", "Relevanz", "Aktion"]):
            ctk.CTkLabel(ph_row, text=col_name, font=ctk.CTkFont(family="Inter", weight="bold", size=12), text_color="#8B949E").grid(row=0, column=i, sticky="w", padx=10)
        ctk.CTkFrame(self.app.pattern_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))
    
        # --- 3. Sub-Tab: Advanced Analysis ---
        adv_tab = self.app.charts_sub_tabs.tab("🔬 Advanced Analysis")
        adv_tab.grid_columnconfigure(0, weight=1)
        adv_tab.grid_rowconfigure(1, weight=1)
    
        adv_controls = ctk.CTkFrame(adv_tab, fg_color="transparent")
        adv_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
        # Details for Advanced Chart
        self.app.adv_symbol_var = ctk.StringVar(value="EURUSD")
        self.app.adv_timeframe_var = ctk.StringVar(value="H1 (1 Std)")
        self.app.adv_indicator_var = ctk.StringVar(value="Keine (Raw Price)")
    
        ctk.CTkComboBox(adv_controls, values=["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"], variable=self.app.adv_symbol_var).pack(side="left", padx=5)
        ctk.CTkComboBox(adv_controls, values=["M1 (1 Min)", "M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (Täglich)"], variable=self.app.adv_timeframe_var).pack(side="left", padx=5)
        ctk.CTkComboBox(adv_controls, values=["Keine (Raw Price)", "SMA 20", "SMA 50", "EMA 200", "Bollinger Bands"], variable=self.app.adv_indicator_var).pack(side="left", padx=5)
    
        ctk.CTkButton(adv_controls, text="📊 Chart Analysieren", command=self.load_advanced_chart, fg_color="#8E44AD", hover_color="#732D91").pack(side="left", padx=10)
    
        self.app.adv_chart_container = ctk.CTkFrame(adv_tab, corner_radius=15, fg_color="#1A1D24")
        self.app.adv_chart_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    
        ctk.CTkLabel(self.app.adv_chart_container, text="Wähle ein Asset und klicke auf 'Chart Analysieren'", text_color="#8B949E", font=ctk.CTkFont(family="Inter", size=14)).pack(expand=True)
    
        # --- 4. Sub-Tab: SMC Scanner ---
        smc_tab = self.app.charts_sub_tabs.tab("🏦 SMC Scanner")
        smc_tab.grid_columnconfigure(0, weight=1)
        smc_tab.grid_rowconfigure(1, weight=1)
    
        smc_controls = ctk.CTkFrame(smc_tab, fg_color="transparent")
        smc_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
        self.app.smc_tf_var = ctk.StringVar(value="H1 (1 Std)")
        ctk.CTkComboBox(smc_controls, values=["M5 (5 Min)", "M15 (15 Min)", "M30 (30 Min)", "H1 (1 Std)", "H4 (4 Std)", "D1 (Täglich)"], variable=self.app.smc_tf_var, width=150).pack(side="left", padx=5)
    
        ctk.CTkButton(smc_controls, text="🏦 SMC Scannen", command=self.run_smc_scanner, fg_color="#3498DB", hover_color="#2980B9").pack(side="left", padx=5)
        self.app.smc_status_lbl = ctk.CTkLabel(smc_controls, text="Klicke auf SMC Scannen...", text_color="#8B949E")
        self.app.smc_status_lbl.pack(side="left", padx=15)
    
        self.app.smc_list_frame = ctk.CTkScrollableFrame(smc_tab, corner_radius=15, fg_color="#1A1D24")
        self.app.smc_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    
        smc_ph_row = ctk.CTkFrame(self.app.smc_list_frame, fg_color="transparent", height=30)
        smc_ph_row.pack(fill="x", pady=(0, 5))
        smc_ph_row.grid_columnconfigure((0,1,2,3), weight=1, uniform="col")
        for i, col_name in enumerate(["Symbol", "Timeframe", "Gefundenes SMC Muster", "Aktion"]):
            ctk.CTkLabel(smc_ph_row, text=col_name, font=ctk.CTkFont(family="Inter", weight="bold", size=12), text_color="#8B949E").grid(row=0, column=i, sticky="w", padx=10)
        ctk.CTkFrame(self.app.smc_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

        # Delay the initial load slightly so the GUI can render first
        self.app.after(1000, self.app.load_forex_charts)

    def load_advanced_chart(self):
        self.app.write_terminal(f">> Lade interaktiven Web-Chart für {self.app.adv_symbol_var.get()}...\n")
    
        symbol = self.app.adv_symbol_var.get()
        tf_str = self.app.adv_timeframe_var.get()
        
        import subprocess
        import sys
        import os
        
        # Launch the interactive pywebview chart in a separate process to avoid blocking Tkinter mainloop
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tv_chart.py")
        subprocess.Popen([sys.executable, script_path, symbol, tf_str])
        
        # Update UI text to let user know it opened in a new window
        for widget in self.app.adv_chart_container.winfo_children():
            widget.destroy()
            
        success_lbl = ctk.CTkLabel(
            self.app.adv_chart_container, 
            text=f"✅ Interaktiver Web-Chart für {symbol} ({tf_str}) geöffnet.", 
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color="#00E676"
        )
        success_lbl.pack(expand=True)
        
        sub_lbl = ctk.CTkLabel(
            self.app.adv_chart_container, 
            text="Siehe externes Web-View Fenster.", 
            font=ctk.CTkFont(family="Inter", size=14),
            text_color="#8B949E"
        )
        sub_lbl.pack()

    def _render_adv_chart(self, fig):
        for widget in self.app.adv_chart_container.winfo_children():
            widget.destroy()
        
        canvas = FigureCanvasTkAgg(fig, master=self.app.adv_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def run_pattern_scanner(self):
        tf_str = self.app.scan_tf_var.get()
        self.app.scan_status_lbl.configure(text=f"Scanne Major Pairs auf {tf_str.split(' ')[0]}...", text_color="#F1C40F")
        self.app.write_terminal(f">> Starte Candlestick Pattern Scanner ({tf_str})...\n")
    
        # Clear old results (keep header)
        children = self.app.pattern_list_frame.winfo_children()
        for widget in children[2:]:
            if hasattr(widget, 'destroy'):
                widget.destroy()
            
        if len(self.app.pattern_list_frame.winfo_children()) < 2:
            ctk.CTkFrame(self.app.pattern_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

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

                self.app.after(0, lambda: self._render_scan_results(found_patterns))
            except Exception as e:
                error_msg = str(e)
                self.app.after(0, lambda msg=error_msg: self.app.scan_status_lbl.configure(text=f"Fehler: {msg}", text_color="#FF1744"))

        threading.Thread(target=scan_logic, daemon=True).start()

    def _render_scan_results(self, patterns):
        if not patterns:
            ctk.CTkLabel(self.app.pattern_list_frame, text="Keine auff\u00e4lligen Candlestick-Patterns gefunden.", text_color="#8B949E").pack(pady=20)
        else:
            for sym, tf, pat, rel, tf_str in patterns:
                row = ctk.CTkFrame(self.app.pattern_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
            
                color = "white"
                if "Bullish" in pat: color = "#00FF66"
                elif "Bearish" in pat: color = "#FF1744"
                elif "Doji" in pat: color = "#F1C40F"
            
                ctk.CTkLabel(row, text=sym, font=ctk.CTkFont(family="Inter", weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
                ctk.CTkLabel(row, text=tf, text_color="#8B949E").grid(row=0, column=1, sticky="w", padx=10)
                ctk.CTkLabel(row, text=pat, text_color=color, font=ctk.CTkFont(family="Inter", weight="bold")).grid(row=0, column=2, sticky="w", padx=10)
                ctk.CTkLabel(row, text=rel, text_color="#F1C40F").grid(row=0, column=3, sticky="w", padx=10)
                ctk.CTkButton(row, text="\U0001f4c8 Chart", width=80, height=26,
                              fg_color="#2979FF", hover_color="#1a5f7a",
                              command=lambda s=sym, t=tf_str, p=pat: self._show_pattern_chart(s, t, p)
                             ).grid(row=0, column=4, sticky="w", padx=10)
            
        self.app.scan_status_lbl.configure(text=f"Scan abgeschlossen. {len(patterns)} Treffer.", text_color="#00FF66")

    def _show_pattern_chart(self, symbol, tf_str, pattern):
        """Open a Toplevel popup with the price chart and the pattern highlighted."""
        popup = ctk.CTkToplevel(self.app)
        popup.title(f"{symbol} - {pattern}")
        popup.geometry("900x550")
        popup.configure(fg_color="#1E1E1E")
        popup.grab_set()
    
        status = ctk.CTkLabel(popup, text=f"Lade Chart f\u00fcr {symbol}...", font=ctk.CTkFont(family="Inter", size=14))
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
                self.app.after(0, lambda: _embed_chart(fig))
            except Exception as e:
                err = str(e)
                self.app.after(0, lambda msg=err: status.configure(text=f"Fehler: {msg}"))
    
        def _embed_chart(fig):
            status.destroy()
            canvas = FigureCanvasTkAgg(fig, master=popup)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
        threading.Thread(target=fetch_chart, daemon=True).start()

    def run_smc_scanner(self):
        tf_str = self.app.smc_tf_var.get()
        self.app.smc_status_lbl.configure(text=f"Scanne Major Pairs auf {tf_str.split(' ')[0]}...", text_color="#F1C40F")
        self.app.write_terminal(f">> Starte SMC Scanner ({tf_str})...\n")
    
        # Clear old results (keep header)
        children = self.app.smc_list_frame.winfo_children()
        for widget in children[2:]:
            if hasattr(widget, 'destroy'):
                widget.destroy()
            
        if len(self.app.smc_list_frame.winfo_children()) < 2:
            ctk.CTkFrame(self.app.smc_list_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

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
                tf_label = tf_str.split(' ')[0]
                
                pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
                found_patterns = []
            
                for symbol in pairs:
                    # Look at the last 25 candles
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 25)
                    if rates is None or len(rates) < 3:
                        continue
                    
                    # Check the most recent 10 candles for FVGs and OBs
                    for i in range(len(rates) - 10, len(rates) - 1):
                        c0, c1, c2 = rates[i-2], rates[i-1], rates[i]
                    
                        # FVG Detection
                        # Bullish FVG: c0 high < c2 low
                        if c0['high'] < c2['low'] and c1['close'] > c1['open']:
                            gap_size = c2['low'] - c0['high']
                            if gap_size > ((c1['high'] - c1['low']) * 0.1) and gap_size > 0.0001: 
                                found_patterns.append((symbol, tf_label, "Bullish FVG", "green", tf_str, int(c1['time'])))
                    
                        # Bearish FVG: c0 low > c2 high
                        if c0['low'] > c2['high'] and c1['close'] < c1['open']:
                            gap_size = c0['low'] - c2['high']
                            if gap_size > ((c1['high'] - c1['low']) * 0.1) and gap_size > 0.0001:
                                found_patterns.append((symbol, tf_label, "Bearish FVG", "red", tf_str, int(c1['time'])))
                            
                        # Order Block Detection
                        # Bullish OB: Last down candle before a strong up move
                        if c0['close'] < c0['open'] and c1['close'] > c1['open'] and c2['close'] > c2['open']:
                            if (c1['close'] - c1['open']) > (c0['open'] - c0['close']) * 1.5:
                                found_patterns.append((symbol, tf_label, "Bullish Order Block", "green", tf_str, int(c0['time']))) 
                    
                        # Bearish OB: Last up candle before a strong down move
                        if c0['close'] > c0['open'] and c1['close'] < c1['open'] and c2['close'] < c2['open']:
                            if (c1['open'] - c1['close']) > (c0['close'] - c0['open']) * 1.5:
                                found_patterns.append((symbol, tf_label, "Bearish Order Block", "red", tf_str, int(c0['time'])))

                # Check for Break of Structure (BOS)
                for symbol in pairs:
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 20)
                    if rates is None or len(rates) < 15: continue
                    past_15 = rates[:-2]
                    current = rates[-2]
                
                    highest_high = max([r['high'] for r in past_15])
                    lowest_low = min([r['low'] for r in past_15])
                
                    if current['close'] > highest_high:
                        found_patterns.append((symbol, tf_label, "Bullish BOS", "green", tf_str, int(current['time'])))
                    elif current['close'] < lowest_low:
                        found_patterns.append((symbol, tf_label, "Bearish BOS", "red", tf_str, int(current['time'])))

                found_patterns.reverse()
                self.app.after(0, lambda: self._render_smc_results(found_patterns[:20])) # Top 20
            except Exception as e:
                error_msg = str(e)
                self.app.after(0, lambda msg=error_msg: self.app.smc_status_lbl.configure(text=f"Fehler: {msg}", text_color="#FF1744"))

        threading.Thread(target=scan_logic, daemon=True).start()

    def _render_smc_results(self, patterns):
        if not patterns:
            ctk.CTkLabel(self.app.smc_list_frame, text="Keine SMC-Muster gefunden.", text_color="#8B949E").pack(pady=20)
        else:
            for sym, tf, pat, color_name, tf_str, timestamp in patterns:
                row = ctk.CTkFrame(self.app.smc_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                row.grid_columnconfigure((0,1,2,3), weight=1, uniform="col")
            
                color = "#00FF66" if color_name == "green" else "#FF1744"
            
                ctk.CTkLabel(row, text=sym, font=ctk.CTkFont(family="Inter", weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
                ctk.CTkLabel(row, text=tf, text_color="#8B949E").grid(row=0, column=1, sticky="w", padx=10)
                ctk.CTkLabel(row, text=pat, text_color=color, font=ctk.CTkFont(family="Inter", weight="bold")).grid(row=0, column=2, sticky="w", padx=10)
                ctk.CTkButton(row, text="🏦 Chart", width=80, height=26,
                              fg_color="#3498DB", hover_color="#2980B9",
                              command=lambda s=sym, t=tf_str, p=pat, ts=timestamp: self._show_smc_chart(s, t, p, ts)
                             ).grid(row=0, column=3, sticky="w", padx=10)
            
        self.app.smc_status_lbl.configure(text=f"Scan abgeschlossen. {len(patterns)} Treffer.", text_color="#00FF66")

    def _show_smc_chart(self, symbol, tf_str, pattern, timestamp):
        """Open a Toplevel popup with the price chart and the SMC pattern highlighted."""
        popup = ctk.CTkToplevel(self.app)
        popup.title(f"{symbol} - {pattern}")
        popup.geometry("900x550")
        popup.configure(fg_color="#1E1E1E")
        popup.grab_set()
    
        status = ctk.CTkLabel(popup, text=f"Lade Chart für {symbol}...", font=ctk.CTkFont(family="Inter", size=14))
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
            
                # Fetch 60 candles hoping the timestamp is within it
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 60)
                if rates is None or len(rates) < 5:
                    raise Exception("Nicht genügend Daten")
                
                df = pd.DataFrame(rates)
                df['time_sec'] = df['time'] # Keep unix time
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
            
                # Find index of timestamp
                idx_matches = df.index[df['time_sec'] == timestamp].tolist()
                target_idx = -1
                if len(idx_matches) > 0:
                    target_idx = df.index.get_loc(idx_matches[0])
            
                fig = Figure(figsize=(9, 4.5), facecolor='#1E1E1E')
                ax = fig.add_subplot(111)
                ax.set_facecolor('#1E1E1E')
                ax.tick_params(colors='white')
                ax.set_title(f"{symbol}  |  {pattern}  |  {tf_str.split(' ')[0]}", color='white', fontsize=12)
                ax.spines['bottom'].set_color('gray')
                ax.spines['left'].set_color('gray')
            
                mpf.plot(df, type='candle', ax=ax, style=s, show_nontrading=False, warn_too_much_data=1000)
            
                if target_idx != -1:
                    color = 'yellow'
                    if "Bullish" in pattern: color = 'green'
                    elif "Bearish" in pattern: color = 'red'
                
                    # Target index relative highlighting
                    ax.axvspan(target_idx - 0.5, target_idx + 0.5, color=color, alpha=0.3, zorder=0)
                    ax.annotate(f"{pattern}", xy=(target_idx, ax.get_ylim()[1]),
                                xycoords=('data', 'data'), ha='center', va='top',
                                color=color, fontsize=10, fontweight='bold')
            
                fig.tight_layout()
                self.app.after(0, lambda: _embed_chart(fig))
            except Exception as e:
                err = str(e)
                self.app.after(0, lambda msg=err: status.configure(text=f"Fehler: {msg}"))
    
        def _embed_chart(fig):
            status.destroy()
            canvas = FigureCanvasTkAgg(fig, master=popup)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
        threading.Thread(target=fetch_chart, daemon=True).start()

    # ══════════════════════════════════════════════════════
    # KI DEBATE TAB
    # ══════════════════════════════════════════════════════
