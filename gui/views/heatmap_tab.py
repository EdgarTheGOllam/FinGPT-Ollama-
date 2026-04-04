import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime
import time
from datetime import datetime


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
        self._currency_labels = {}
        self._strength_bars = {}

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

        # ── Main Container ───────────────────────────────────────
        main_frame = ctk.CTkFrame(
            self.tab, corner_radius=15, fg_color=("#F5F5F5", "#151515")
        )
        main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create rows for each currency
        for i, curr in enumerate(self._currencies):
            main_frame.grid_rowconfigure(i, weight=1)

            # Currency Label (Left)
            lbl = ctk.CTkLabel(
                main_frame,
                text=curr,
                font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            )
            lbl.grid(row=i, column=0, sticky="e", padx=(20, 10), pady=10)
            self._currency_labels[curr] = lbl

            # Bar Container (Middle)
            bar_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=30)
            bar_frame.grid(row=i, column=1, sticky="ew", padx=10, pady=10)
            bar_frame.grid_propagate(False)

            # Progress Bar
            progress = ctk.CTkProgressBar(
                bar_frame, height=20, corner_radius=10, progress_color="gray30"
            )
            progress.pack(fill="both", expand=True)
            progress.set(0.5)  # Start at neutral (0.5)

            # Value Label (Right)
            val_lbl = ctk.CTkLabel(
                main_frame, text="0.0", font=ctk.CTkFont(family="Consolas", size=14)
            )
            val_lbl.grid(row=i, column=2, sticky="w", padx=(10, 20), pady=10)

            # Store references - single dictionary assignment
            self._strength_bars[curr] = {"bar": progress, "lbl": val_lbl}

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
                        max_abs = 0.5
                        self._safe_after(
                            0, lambda s=demo_scores, m=max_abs: self._update_bars(s, m)
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
                        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 24)
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
                            0, lambda s=demo_scores: self._update_bars(s, 0.3)
                        )
                        time.sleep(5)
                        continue

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

                    # Ensure we have a non-zero max_abs for normalization
                    if max_abs < 0.001:
                        max_abs = 0.001

                    # Update UI in main thread - using safe wrapper
                    self._safe_after(
                        0,
                        lambda scores=final_scores.copy(), m=max_abs: self._update_bars(
                            scores, m
                        ),
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

    def _update_bars(self, scores, max_abs):
        for c, score in scores.items():
            # Flatten to 0.0 - 1.0 (0.5 is neutral)
            normalized = (score / max_abs) / 2.0 + 0.5
            normalized = max(0.0, min(1.0, normalized))

            color = "#00FF66" if score > 0 else "#FF1744" if score < 0 else "gray50"

            bar_dict = self._strength_bars[c]
            bar_dict["bar"].set(normalized)
            bar_dict["bar"].configure(progress_color=color)

            sign = "+" if score > 0 else ""
            bar_dict["lbl"].configure(text=f"{sign}{score:.2f}", text_color=color)

        now = datetime.now().strftime("%H:%M:%S")
        self.status_lbl.configure(text=f"Live ({now})", text_color="#00FF66")
