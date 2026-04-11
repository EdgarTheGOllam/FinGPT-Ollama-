import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime
import time

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Fancy console
class C:
    RESET = "\033[0m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    LGRAY = "\033[90m"


def ts():
    return datetime.now().strftime("%H:%M:%S")


class HeatmapView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self._heatmap_running = False
        self._heatmap_thread = None
        self._currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"]

        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(1, weight=1)

        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self.tab, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text="🔥 Währungs-Heatmap (Live)",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#FFEA00",
        ).pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            header, text="Warte auf Daten...", text_color="#8B949E"
        )
        self.status_lbl.pack(side="right", padx=10)

        # ── Main Container (Matplotlib Embed) ───────────────────
        self.main_frame = ctk.CTkFrame(
            self.tab, corner_radius=0, fg_color="transparent"
        )
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        
        # Init Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(9, 5), facecolor='#0B0E14')
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
        
        self.ax.set_facecolor('#0B0E14')
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # Initial empty state (avoids white borders)
        self.ax.text(5, 3.5, "Warte auf Daten-Feed...", color="#4B5563", fontsize=14, ha='center', va='center', fontfamily='sans-serif')
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 7)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ── Footer / Info ────────────────────────────────────────
        info = ctk.CTkLabel(
            self.tab,
            text="Berechnet die relative Stärke anhand von 24h M15 Kerzen über alle Major Pairs.",
            text_color="#8B949E",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=2, column=0, pady=(0, 10))

        # Start background update loop
        self._start_heatmap_loop()

    def _safe_after(self, delay, callback):
        """
        Thread-safe wrapper for app.after() that handles cases where
        the main thread is no longer in the Tkinter event loop.
        """
        if not self._heatmap_running:
            return

        try:
            # Try to get the window info to check if GUI still exists
            if hasattr(self.app, "winfo_exists") and self.app.winfo_exists():
                self.app.after(delay, callback)
            else:
                # GUI window no longer exists, stop the thread
                self._heatmap_running = False
        except RuntimeError as e:
            # Main thread is not in main loop - GUI is closing or closed
            # #region agent log
            import json, time
            with open("debug-0a8f4e.log", "a") as f:
                f.write(json.dumps({"sessionId":"0a8f4e", "runId":"post-fix", "hypothesisId":"H4", "location":"heatmap_tab.py:_safe_after", "message":"RuntimeError in after", "data":{"error": str(e)}, "timestamp":int(time.time()*1000)}) + "\n")
            # #endregion
            if "main thread is not in main loop" in str(e):
                # We started too early. mainloop() hasn't been called yet. 
                # Do NOT stop the thread. Just ignore and it will retry next time.
                pass
            else:
                print(
                    f"{C.LGRAY}[{ts()}]{C.RESET} {C.YELLOW}🧩 [HEATMAP] GUI nicht verfügbar – Thread gestoppt: {e}{C.RESET}"
                )
                self._heatmap_running = False
        except Exception as e:
            print(
                f"{C.LGRAY}[{ts()}]{C.RESET} {C.RED}❌ [HEATMAP] Fehler beim GUI-Update: {e}{C.RESET}"
            )
            self._heatmap_running = False

    def stop(self):
        """
        Stop the heatmap update thread gracefully. Call this when
        the tab or window is being closed/destroyed.
        """
        self._heatmap_running = False
        if self._heatmap_thread and self._heatmap_thread.is_alive():
            print(
                f"{C.LGRAY}[{ts()}]{C.RESET} {C.BLUE}🧩 [HEATMAP] Warte auf Beendigung des Threads...{C.RESET}"
            )
            # Give the thread time to finish current iteration
            time.sleep(1)

    def _start_heatmap_loop(self):
        self._heatmap_running = True

        def loop():
            self._safe_after(
                0,
                lambda: self.status_lbl.configure(
                    text="Initialisiere Heatmap...", text_color="#FFEA00"
                ),
            )

            mt5_available = False
            try:
                import MetaTrader5 as mt5

                mt5_available = True
            except Exception as e:
                print(f"[Heatmap] MT5 Import failed: {e}")

            import random

            while self._heatmap_running:
                try:
                    # Test if we can initialize MT5 safely
                    mt5_initialized = False
                    if mt5_available:
                        try:
                            # Use a short timeout (5 seconds) to prevent infinite blocking
                            # if the MT5 terminal is stuck or prompting for admin rights
                            mt5_initialized = mt5.initialize(timeout=5000)
                        except Exception as e:
                            print(f"[Heatmap] MT5 init error: {e}")

                    if not mt5_available or not mt5_initialized:
                        # MT5 not connected - show demo data
                        self._safe_after(
                            0,
                            lambda: self.status_lbl.configure(
                                text="MT5 nicht verbunden - Demo-Modus",
                                text_color="#FFA500",
                            ),
                        )
                        # Show demo/scatter data when MT5 not connected
                        demo_scores = {
                            "USD": round(random.uniform(-0.5, 0.5), 2),
                            "EUR": round(random.uniform(-0.5, 0.5), 2),
                            "GBP": round(random.uniform(-0.5, 0.5), 2),
                            "JPY": round(random.uniform(-0.5, 0.5), 2),
                            "CHF": round(random.uniform(-0.5, 0.5), 2),
                            "AUD": round(random.uniform(-0.5, 0.5), 2),
                            "CAD": round(random.uniform(-0.5, 0.5), 2),
                        }
                        self._safe_after(
                            0, lambda s=demo_scores: self._update_heatmap(s)
                        )
                        time.sleep(5)
                        continue

                    self._safe_after(
                        0,
                        lambda: self.status_lbl.configure(
                            text="Berechne Stärke...", text_color="#FFEA00"
                        ),
                    )

                    # Calculate relative strength from MT5 data
                    strengths = {c: 0.0 for c in self._currencies}
                    count = {c: 0 for c in self._currencies}

                    # Pairs to analyze to establish strength matrix
                    pairs = [
                        ("EURUSD", "EUR", "USD"),
                        ("GBPUSD", "GBP", "USD"),
                        ("USDJPY", "USD", "JPY"),
                        ("USDCHF", "USD", "CHF"),
                        ("AUDUSD", "AUD", "USD"),
                        ("USDCAD", "USD", "CAD"),
                        ("EURJPY", "EUR", "JPY"),
                        ("GBPJPY", "GBP", "JPY"),
                        ("EURGBP", "EUR", "GBP"),
                    ]

                    valid_data = False
                    for symbol, base, quote in pairs:
                        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 96) # 24h of M15 = 96 candles
                        if rates is not None and len(rates) > 1:
                            valid_data = True
                            open_p = rates[0]["open"]
                            close_p = rates[-1]["close"]
                            change = ((close_p - open_p) / open_p) * 100

                            # Base currency gains strength if price goes up
                            strengths[base] += change
                            count[base] += 1

                            # Quote currency loses strength if price goes up
                            strengths[quote] -= change
                            count[quote] += 1

                    # If no valid data, show message and continue with demo
                    if not valid_data:
                        self._safe_after(
                            0,
                            lambda: self.status_lbl.configure(
                                text="Keine MT5-Daten - Demo-Modus",
                                text_color="#FFA500",
                            ),
                        )
                        demo_scores = {
                            "USD": round(random.uniform(-0.3, 0.3), 2),
                            "EUR": round(random.uniform(-0.3, 0.3), 2),
                            "GBP": round(random.uniform(-0.3, 0.3), 2),
                            "JPY": round(random.uniform(-0.3, 0.3), 2),
                            "CHF": round(random.uniform(-0.3, 0.3), 2),
                            "AUD": round(random.uniform(-0.3, 0.3), 2),
                            "CAD": round(random.uniform(-0.3, 0.3), 2),
                        }
                        self._safe_after(
                            0, lambda s=demo_scores: self._update_heatmap(s)
                        )
                        time.sleep(5)
                        continue

                    # Normalize and update GUI
                    final_scores = {}
                    for c in self._currencies:
                        if count[c] > 0:
                            score = strengths[c] / count[c]
                        else:
                            score = 0.0
                        final_scores[c] = score

                    # Update UI in main thread - using safe wrapper
                    self._safe_after(
                        0,
                        lambda scores=final_scores.copy(): self._update_heatmap(scores),
                    )

                except Exception as e:
                    self._safe_after(
                        0,
                        lambda err=str(e): self.status_lbl.configure(
                            text=f"Fehler: {err}", text_color="#FF1744"
                        ),
                    )

                # Sleep with periodic check for shutdown flag
                for _ in range(60):
                    if not self._heatmap_running:
                        break
                    time.sleep(1)

        self._heatmap_thread = threading.Thread(target=loop, daemon=True)
        self._heatmap_thread.start()

    def _update_heatmap(self, scores):
        """
        Updates the matplotlib canvas with the new scores using the Broadcast-Market-Panel look.
        """
        # Transform scores dict to list of dicts for the render function
        data = [{"symbol": k, "change": v} for k, v in scores.items()]
        
        # Sort by change descending
        data_sorted = sorted(data, key=lambda x: x["change"], reverse=True)
        n_items = len(data_sorted)
        
        # Clear previous plot
        self.ax.clear()
        
        # Plot styling
        bg_color = '#0B0E14'
        text_color = '#E0E0E0'
        up_color = '#089981'   # TradingView Green
        down_color = '#F23645' # TradingView Red
        line_color = '#1A1D24'
        
        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, n_items)
        
        max_val = max(abs(d['change']) for d in data_sorted) if data_sorted else 1
        if max_val == 0:
            max_val = 1
            
        # Layout metrics
        x_symbol = 0.5
        x_change = 2.8
        x_zero_line = 6.0
        max_bar_width = 3.0
        bar_height = 0.4
        
        # Add background highlighting for alternating rows
        for i in range(n_items):
            if i % 2 == 0:
                y = n_items - i - 0.5
                bg_rect = patches.Rectangle((0, y - 0.5), 10, 1, facecolor='#0D1117', edgecolor='none', zorder=0)
                self.ax.add_patch(bg_rect)
        
        # Vertical zero line
        self.ax.plot([x_zero_line, x_zero_line], [0, n_items], color='#1F2937', linewidth=1, zorder=1)
        
        for i, item in enumerate(data_sorted):
            y = n_items - i - 0.5
            
            symbol = item['symbol']
            change = item['change']
            
            is_up = change >= 0
            color = up_color if is_up else down_color
            sign = '+' if is_up else ''
            arrow = '▲' if is_up else '▼'
            
            # 1. Symbol
            self.ax.text(x_symbol, y, symbol, color=text_color, fontsize=15, fontweight='bold', ha='left', va='center', fontfamily='sans-serif')
            
            # 2. Change value (fixed width alignment)
            change_text = f"{sign}{change:.2f}%"
            self.ax.text(x_change, y, change_text, color=color, fontsize=15, fontweight='bold', ha='right', va='center', fontfamily='sans-serif')
            
            # 3. Bar
            bar_len = (abs(change) / max_val) * max_bar_width
            
            # Background track for the bar (adds a professional widget feel)
            bg_track = patches.Rectangle((x_zero_line - max_bar_width, y - bar_height/2), max_bar_width * 2, bar_height, 
                                         facecolor='#161B22', edgecolor='none', zorder=1)
            self.ax.add_patch(bg_track)

            if is_up:
                rect = patches.Rectangle((x_zero_line, y - bar_height/2), bar_len, bar_height, 
                                         facecolor=color, edgecolor='none', zorder=2)
                self.ax.text(x_zero_line + bar_len + 0.15, y, arrow, color=color, fontsize=11, ha='left', va='center')
            else:
                rect = patches.Rectangle((x_zero_line - bar_len, y - bar_height/2), bar_len, bar_height, 
                                         facecolor=color, edgecolor='none', zorder=2)
                self.ax.text(x_zero_line - bar_len - 0.15, y, arrow, color=color, fontsize=11, ha='right', va='center')
                
            self.ax.add_patch(rect)
            
            # 4. Separator line (subtle)
            if i < n_items - 1:
                self.ax.plot([0.1, 9.9], [y - 0.5, y - 0.5], color=line_color, linewidth=0.5, zorder=3)
                
        # Draw canvas
        self.canvas.draw()
        
        # Update status
        now = datetime.now().strftime("%H:%M:%S")
        self.status_lbl.configure(text=f"Live ({now})", text_color=up_color)
