import customtkinter as ctk
import tkinter as tk
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class LiveDataRow(ctk.CTkFrame):
    """Eine Zeile für die Scrollbare Live-Daten Ansicht mit MTF Trend Ampel, Hover-Interaktion und Mini-Chart (Sparkline)"""

    # Minimale Breiten für verschiedene Spalten
    MIN_WIDTHS = {
        "symbol": 60,
        "chart": 50,
        "price": 80,
        "change": 60,
        "trend": 70,
        "signal": 50,
    }

    def __init__(
        self,
        master,
        symbol,
        price,
        change,
        signal,
        min_height=None,
        compact_mode=False,
        **kwargs,
    ):
        self.default_color = "transparent"
        self.hover_color = "transparent"  # Professionell: Kein Hover-Effekt

        # Responsive Höhe
        from gui.design_system import DesignSystem

        ds = DesignSystem
        self._min_height = min_height or ds.COMPONENTS["live_data_row"]["height"]
        self._compact_mode = compact_mode

        super().__init__(
            master,
            fg_color=self.default_color,
            corner_radius=8,
            height=self._min_height,
            **kwargs,
        )

        # Grid Setup for consistent column widths
        # Verwende weight für flexible Aufteilung, aber mit Mindestbreiten
        self.grid_columnconfigure(
            0, weight=0, minsize=self.MIN_WIDTHS["symbol"]
        )  # Symbol
        self.grid_columnconfigure(
            1, weight=0, minsize=self.MIN_WIDTHS["chart"]
        )  # Chart
        self.grid_columnconfigure(
            2, weight=1, minsize=self.MIN_WIDTHS["price"]
        )  # Price
        self.grid_columnconfigure(
            3, weight=1, minsize=self.MIN_WIDTHS["change"]
        )  # Change
        self.grid_columnconfigure(
            4, weight=0, minsize=self.MIN_WIDTHS["trend"]
        )  # Trend
        self.grid_columnconfigure(
            5, weight=0, minsize=self.MIN_WIDTHS["signal"]
        )  # Signal

        # Berechne Padding basierend auf Kompakt-Modus
        padx = 6 if compact_mode else 10
        pady = 6 if compact_mode else 10

        # Font-Größen responsiv
        font_size = 11 if compact_mode else 13

        self.symbol_lbl = ctk.CTkLabel(
            self,
            text=symbol,
            font=ctk.CTkFont(family="Inter", size=font_size, weight="bold"),
        )
        self.symbol_lbl.grid(row=0, column=0, sticky="w", padx=padx, pady=pady)

        # --- Mini-Chart (Sparkline) - Responsive Breite ---
        chart_width = 50 if compact_mode else 80
        chart_height = 25 if compact_mode else 30
        self.chart_frame = ctk.CTkFrame(
            self, fg_color="transparent", width=chart_width, height=chart_height
        )
        self.chart_frame.grid(row=0, column=1, sticky="w", padx=2, pady=pady)
        self.chart_frame.grid_propagate(False)

        # Fig-Größe ebenfalls responsive
        fig_width = 0.8 if compact_mode else 1.0
        fig_height = 0.35 if compact_mode else 0.4
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=100, facecolor="#0B0E14")
        self.ax = self.fig.add_subplot(111)
        self.ax.axis("off")
        self.ax.margins(x=0, y=0.1)

        (self.line,) = self.ax.plot([], [], color="gray", linewidth=1.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)
        # ------------------------------

        self.price_lbl = ctk.CTkLabel(
            self,
            text=price,
            font=ctk.CTkFont(family="Consolas", size=font_size),
            text_color="#FFFFFF",
        )
        self.price_lbl.grid(row=0, column=2, sticky="w", padx=padx, pady=pady)

        change_color = (
            "#00FF66" if "+" in change else "#FF1744" if "-" in change else "#8B949E"
        )
        self.change_lbl = ctk.CTkLabel(
            self,
            text=change,
            text_color=change_color,
            font=ctk.CTkFont(family="Consolas", size=font_size, weight="bold"),
        )
        self.change_lbl.grid(row=0, column=3, sticky="w", padx=padx, pady=pady)

        # MTF Trend Ampel Frame - responsive Größe
        trend_dot_size = 14 if compact_mode else 16
        trend_padx = 2 if compact_mode else 3
        self.trend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.trend_frame.grid(row=0, column=4, sticky="w", padx=padx, pady=pady)

        self.trend_m15 = ctk.CTkLabel(
            self.trend_frame,
            text="●",
            text_color="gray",
            font=ctk.CTkFont(family="Inter", size=trend_dot_size),
        )
        self.trend_m15.pack(side="left", padx=trend_padx)
        self.trend_h1 = ctk.CTkLabel(
            self.trend_frame,
            text="●",
            text_color="gray",
            font=ctk.CTkFont(family="Inter", size=trend_dot_size),
        )
        self.trend_h1.pack(side="left", padx=trend_padx)
        self.trend_h4 = ctk.CTkLabel(
            self.trend_frame,
            text="●",
            text_color="gray",
            font=ctk.CTkFont(family="Inter", size=trend_dot_size),
        )
        self.trend_h4.pack(side="left", padx=trend_padx)

        # Signal Button - responsive Größe
        sig_width = 45 if compact_mode else 60
        sig_height = 20 if compact_mode else 24
        sig_font_size = 9 if compact_mode else 10
        sig_color = (
            "#00FF66"
            if signal == "BUY"
            else "#FF1744"
            if signal == "SELL"
            else "#8B949E"
        )
        self.signal_btn = ctk.CTkButton(
            self,
            text=signal,
            width=sig_width,
            height=sig_height,
            fg_color=sig_color,
            hover_color=sig_color,
            text_color="#0B0E14",
            corner_radius=10,
            font=ctk.CTkFont(family="Inter", size=sig_font_size, weight="bold"),
        )
        self.signal_btn.grid(row=0, column=5, sticky="w", padx=padx, pady=pady)

        # Event-Bindings für die Hover-Animation
        self._bind_hover(self)
        self._bind_hover(self.symbol_lbl)
        self._bind_hover(self.price_lbl)
        self._bind_hover(self.change_lbl)
        self._bind_hover(self.trend_frame)
        self._bind_hover(self.trend_m15)
        self._bind_hover(self.trend_h1)
        self._bind_hover(self.trend_h4)

        # Bind hover to chart canvas too
        self.canvas_widget.bind("<Enter>", self._on_enter)
        self.canvas_widget.bind("<Leave>", self._on_leave)

    def _bind_hover(self, widget):
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        self.configure(fg_color=self.hover_color)
        self.fig.set_facecolor("#1A1D24")
        self.canvas.draw_idle()

    def _on_leave(self, event):
        self.configure(fg_color=self.default_color)
        self.fig.set_facecolor("#0B0E14")  # Reset to default
        self.canvas.draw_idle()

    def update_data(self, price, change, history=None):
        self.price_lbl.configure(text=price)
        self.change_lbl.configure(text=change)
        change_color = (
            "#00FF66" if "+" in change else "#FF1744" if "-" in change else "#8B949E"
        )
        self.change_lbl.configure(text_color=change_color)

        # Update Sparkline Chart
        if history is not None and len(history) > 1:
            y = np.array(history)
            x = np.arange(len(y))
            self.line.set_data(x, y)
            self.ax.set_xlim(0, len(y) - 1)
            self.ax.set_ylim(
                min(y) - (max(y) - min(y)) * 0.1, max(y) + (max(y) - min(y)) * 0.1
            )

            # Color code the line
            if y[-1] >= y[0]:
                self.line.set_color("#00FF66")  # Green
            else:
                self.line.set_color("#FF1744")  # Red

            self.canvas.draw_idle()

    def update_trend(self, m15_color, h1_color, h4_color):
        """Update the 3 timeframe dots with the given hex colors."""
        self.trend_m15.configure(text_color=m15_color)
        self.trend_h1.configure(text_color=h1_color)
        self.trend_h4.configure(text_color=h4_color)

        # Calculate dynamic signal based on the three trend dots
        green = "#00FF66"
        red = "#FF1744"

        colors = [m15_color, h1_color, h4_color]
        if all(c == green for c in colors):
            self.signal_btn.configure(
                text="BUY",
                fg_color="#00FF66",
                hover_color="#00E676",
                text_color="#0B0E14",
            )
        elif all(c == red for c in colors):
            self.signal_btn.configure(
                text="SELL",
                fg_color="#FF1744",
                hover_color="#D50000",
                text_color="#0B0E14",
            )
        else:
            self.signal_btn.configure(
                text="WAIT",
                fg_color="#FFEA00",
                hover_color="#FFD600",
                text_color="#0B0E14",
            )
