import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime
import time

class HeatmapView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self._heatmap_running = False
        self._currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"]
        self._currency_labels = {}
        self._strength_bars = {}
        
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(1, weight=1)

        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self.tab, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(header, text="🔥 Währungs-Heatmap (Live)", 
                     font=ctk.CTkFont(family="Inter", size=20, weight="bold"), 
                     text_color="#FFEA00").pack(side="left")
                     
        self.status_lbl = ctk.CTkLabel(header, text="Warte auf Daten...", text_color="#8B949E")
        self.status_lbl.pack(side="right", padx=10)

        # ── Main Container ───────────────────────────────────────
        main_frame = ctk.CTkFrame(self.tab, corner_radius=15, fg_color=("#F5F5F5", "#151515"))
        main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Create rows for each currency
        for i, curr in enumerate(self._currencies):
            main_frame.grid_rowconfigure(i, weight=1)
            
            # Currency Label (Left)
            lbl = ctk.CTkLabel(main_frame, text=curr, font=ctk.CTkFont(family="Inter", size=16, weight="bold"))
            lbl.grid(row=i, column=0, sticky="e", padx=(20, 10), pady=10)
            self._currency_labels[curr] = lbl
            
            # Bar Container (Middle)
            bar_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=30)
            bar_frame.grid(row=i, column=1, sticky="ew", padx=10, pady=10)
            bar_frame.grid_propagate(False)
            
            # Progress Bar
            progress = ctk.CTkProgressBar(bar_frame, height=20, corner_radius=10, progress_color="gray30")
            progress.pack(fill="both", expand=True)
            progress.set(0.0)
            self._strength_bars[curr] = progress
            
            # Value Label (Right)
            val_lbl = ctk.CTkLabel(main_frame, text="0.0", font=ctk.CTkFont(family="Consolas", size=14))
            val_lbl.grid(row=i, column=2, sticky="w", padx=(10, 20), pady=10)
            
            # Store references
            self._strength_bars[curr] = {'bar': progress, 'lbl': val_lbl}

        # ── Footer / Info ────────────────────────────────────────
        info = ctk.CTkLabel(self.tab, text="Berechnet die relative Stärke anhand von 24h M15 Kerzen über alle Major Pairs.", 
                            text_color="#8B949E", font=ctk.CTkFont(size=11))
        info.grid(row=2, column=0, pady=(0, 10))
        
        # Start background update loop
        self._start_heatmap_loop()

    def _start_heatmap_loop(self):
        self._heatmap_running = True
        
        def loop():
            import MetaTrader5 as mt5
            while self._heatmap_running:
                try:
                    if not mt5.initialize():
                        self.app.after(0, lambda: self.status_lbl.configure(text="Fehler: MT5 nicht verbunden", text_color="#FF1744"))
                        time.sleep(5)
                        continue
                        
                    self.app.after(0, lambda: self.status_lbl.configure(text="Berechne Stärke...", text_color="#FFEA00"))
                        
                    # Calculate dummy or real relative strength
                    # For a real heatmap, we'd need to compare e.g EURUSD, GBPUSD, USDJPY, EURJPY etc.
                    # This is a simplified calculation algorithm gathering changes.
                    strengths = {c: 0.0 for c in self._currencies}
                    count = {c: 0 for c in self._currencies}
                    
                    # Pairs to analyze to establish strength matrix
                    pairs = [
                        ("EURUSD", "EUR", "USD"), ("GBPUSD", "GBP", "USD"), ("USDJPY", "USD", "JPY"),
                        ("USDCHF", "USD", "CHF"), ("AUDUSD", "AUD", "USD"), ("USDCAD", "USD", "CAD"),
                        ("EURJPY", "EUR", "JPY"), ("GBPJPY", "GBP", "JPY"), ("EURGBP", "EUR", "GBP")
                    ]
                    
                    for symbol, base, quote in pairs:
                        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 24)
                        if rates is not None and len(rates) > 1:
                            open_p = rates[0]['open']
                            close_p = rates[-1]['close']
                            change = ((close_p - open_p) / open_p) * 100
                            
                            # Base currency gains strength if price goes up
                            strengths[base] += change
                            count[base] += 1
                            
                            # Quote currency loses strength if price goes up
                            strengths[quote] -= change
                            count[quote] += 1
                            
                    # Normalize and update GUI
                    max_abs = 0.001
                    final_scores = {}
                    
                    for c in self._currencies:
                        if count[c] > 0:
                            score = strengths[c] / count[c]
                        else:
                            score = 0.0
                        final_scores[c] = score
                        if abs(score) > max_abs:
                            max_abs = abs(score)
                            
                    # Update UI in main thread
                    self.app.after(0, lambda scores=final_scores, m=max_abs: self._update_bars(scores, m))
                    
                except Exception as e:
                    self.app.after(0, lambda err=e: self.status_lbl.configure(text=f"Fehler: {err}", text_color="#FF1744"))
                    
                time.sleep(60) # Update every minute

        threading.Thread(target=loop, daemon=True).start()
        
    def _update_bars(self, scores, max_abs):
        for c, score in scores.items():
            # Flatten to 0.0 - 1.0 (0.5 is neutral)
            normalized = (score / max_abs) / 2.0 + 0.5
            normalized = max(0.0, min(1.0, normalized))
            
            color = "#00FF66" if score > 0 else "#FF1744" if score < 0 else "gray50"
            
            bar_dict = self._strength_bars[c]
            bar_dict['bar'].set(normalized)
            bar_dict['bar'].configure(progress_color=color)
            
            sign = "+" if score > 0 else ""
            bar_dict['lbl'].configure(text=f"{sign}{score:.2f}", text_color=color)
            
        now = datetime.now().strftime("%H:%M:%S")
        self.status_lbl.configure(text=f"Live ({now})", text_color="#00FF66")
