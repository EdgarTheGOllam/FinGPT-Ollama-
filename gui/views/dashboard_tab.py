import customtkinter as ctk
import tkinter as tk
from gui.components.metric_card import MetricCard
from gui.components.interactive_frame import HoverFadeFrame
from gui.components.live_data_row import LiveDataRow
from gui.design_system import DesignSystem
from gui.config.dashboard_config import (
    get_dashboard_config,
    get_metric_config,
    get_symbols,
    get_update_interval,
)
from gui.components.sonar_animation import SonarAnimation
from gui.components.spotlight_overlay import SpotlightOverlay


class DashboardView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self._window_width = 1400  # Default, wird bei Größenänderung aktualisiert
        self.setup_ui()
        self.populate_sample_data()

        # Responsive Event-Bindung
        self.tab.bind("<Configure>", self._on_tab_configure)
        self.tab.bind("<<ResponsiveLayoutChanged>>", self._on_responsive_change)

    def _on_tab_configure(self, event):
        """Wird aufgerufen, wenn sich die Tab-Größe ändert."""
        if hasattr(self.tab, "winfo_width"):
            new_width = self.tab.winfo_width()
            if new_width > 100 and abs(new_width - self._window_width) > 50:
                self._window_width = new_width
                self.tab.event_generate("<<ResponsiveLayoutChanged>>", when="tail")

    def _on_responsive_change(self, event):
        """Reagiert auf Größenänderungen und passt das Layout an."""
        self._adjust_layout()

    def _adjust_layout(self):
        """Passt das Layout basierend auf der Fenstergröße an."""
        ds = DesignSystem
        breakpoint = ds.get_current_breakpoint(self._window_width)

        # Passe Spacing basierend auf Breakpoint an
        if breakpoint in ["xs", "sm"]:
            # Sehr schmal: Reduziere Spacing
            metric_spacing = ds.get_responsive_spacing("md", self._window_width)
            container_spacing = ds.get_responsive_spacing("sm", self._window_width)
        elif breakpoint == "md":
            metric_spacing = ds.get_spacing("md")
            container_spacing = ds.get_spacing("sm")
        else:
            metric_spacing = ds.get_spacing("md")
            container_spacing = ds.get_spacing("md")

        # Update Metric Card Spacing
        if hasattr(self.app, "balance_card"):
            cards = [
                getattr(self.app, "balance_card", None),
                getattr(self.app, "equity_card", None),
                getattr(self.app, "margin_card", None),
                getattr(self.app, "risk_card", None),
                getattr(self.app, "pnl_card", None),
                getattr(self.app, "margin_level_card", None),
                getattr(self.app, "positions_card", None),
                getattr(self.app, "trades_card", None),
            ]
            for card in [(c) for c in cards if c is not None]:
                if card.winfo_exists():
                    card.grid_configure(
                        padx=metric_spacing // 2, pady=metric_spacing // 2
                    )

        # Update AI Visualizer padding to match metric cards alignment
        if (
            hasattr(self.app, "ai_visualizer_frame")
            and self.app.ai_visualizer_frame.winfo_exists()
        ):
            self.app.ai_visualizer_frame.grid_configure(padx=metric_spacing // 2)
        # Passe AI Visualizer Canvas-Größe an
        if hasattr(self.app, "sonar_anim"):
            new_sonar_width = max(250, min(400, self._window_width // 4))
            self.app.sonar_anim.resize(
                width=new_sonar_width, height=self.app.sonar_anim.height
            )
            self.app.sonar_width = new_sonar_width

    def setup_ui(self):
        ds = DesignSystem

        # Lade Konfiguration
        config = get_dashboard_config()

        # Responsive Grid-Konfiguration
        # Für kleine Bildschirme: Weniger Spalten
        num_columns = ds.calculate_grid_columns(self._window_width)

        # Grid-Spalten: metric cards (4 spalten), dann unten 2:1 aufteilung
        for col in range(4):
            self.tab.grid_columnconfigure(col, weight=1, uniform="metric_col")

        # Row-Konfiguration:
        # Row 0-1: Metric Cards
        # Row 2: AI Visualizer (flexible Höhe)
        # Row 3: Content Area (weight=1 für flexible Höhe)
        self.tab.grid_rowconfigure(2, weight=0)  # AI Visualizer
        self.tab.grid_rowconfigure(3, weight=1)  # Content Area

        # Top Cards - Konsistente Padding-Werte aus Design-System
        # Verwende minimum width um Abschneiden zu verhindern
        min_card_width = ds.get_min_width_for_breakpoint("metric_card")

        # Lade Metriken aus Konfiguration
        metric_configs = {m.key: m for m in config.metrics}
        
        mode = ctk.get_appearance_mode()
        # Neue harmonische Farbtokens
        card_bg     = DesignSystem.BG['card']       # '#13151A'
        border_idle = DesignSystem.BORDERS['subtle'] # '#1E2128'

        # Erstelle Metric Cards mit Konfigurationswerten
        balance_cfg = metric_configs.get("balance")
        self.app.balance_card = self.create_metric_card(
            self.tab,
            balance_cfg.title if balance_cfg else "Kontostand",
            balance_cfg.default_value if balance_cfg else "€--",
            0,
            0,
            min_width=min_card_width,
            icon_type="balance",
        )

        equity_cfg = metric_configs.get("equity")
        self.app.equity_card = self.create_metric_card(
            self.tab,
            equity_cfg.title if equity_cfg else "Kapital",
            equity_cfg.default_value if equity_cfg else "€--",
            0,
            1,
            min_width=min_card_width,
            icon_type="balance",
        )

        margin_cfg = metric_configs.get("margin")
        self.app.margin_card = self.create_metric_card(
            self.tab,
            margin_cfg.title if margin_cfg else "Marge",
            margin_cfg.default_value if margin_cfg else "€--",
            0,
            2,
            min_width=min_card_width,
            icon_type="risk",
        )

        risk_cfg = metric_configs.get("risk")
        self.app.risk_card = self.create_metric_card(
            self.tab,
            risk_cfg.title if risk_cfg else "Freie Margin",
            risk_cfg.default_value if risk_cfg else "€--",
            0,
            3,
            min_width=min_card_width,
            icon_type="risk",
        )

        pnl_cfg = metric_configs.get("pnl")
        self.app.pnl_card = self.create_metric_card(
            self.tab,
            pnl_cfg.title if pnl_cfg else "Gewinn/Verlust",
            pnl_cfg.default_value if pnl_cfg else "€--",
            1,
            0,
            min_width=min_card_width,
            icon_type="pnl",
        )

        margin_level_cfg = metric_configs.get("margin_level")
        self.app.margin_level_card = self.create_metric_card(
            self.tab,
            margin_level_cfg.title if margin_level_cfg else "Margin Stand",
            margin_level_cfg.default_value if margin_level_cfg else "-%",
            1,
            1,
            min_width=min_card_width,
            icon_type="winrate",
        )

        positions_cfg = metric_configs.get("positions")
        self.app.positions_card = self.create_metric_card(
            self.tab,
            positions_cfg.title if positions_cfg else "Offene Positionen",
            positions_cfg.default_value if positions_cfg else "-",
            1,
            2,
            min_width=min_card_width,
            icon_type="positions",
        )

        trades_cfg = metric_configs.get("trades")
        self.app.trades_card = self.create_metric_card(
            self.tab,
            trades_cfg.title if trades_cfg else "Heutige Trades",
            trades_cfg.default_value if trades_cfg else "-",
            1,
            3,
            min_width=min_card_width,
            icon_type="trades",
        )

        # AI Agent Visualizer & Lückenfüller-Widgets (Middle Banner)
        # Responsive Höhe: Auf kleinen Bildschirmen reduzieren, um Platz für Listen/Charts zu machen
        ai_height = 120 if self._window_width < ds.BREAKPOINTS["md"] else 160
        self.app.ai_visualizer_frame = HoverFadeFrame(
            self.tab,
            height=ai_height,
            corner_radius=ds.get_radius("lg"),
            fg_color=card_bg,            # Einheitlicher bg_card Hintergrund
            active_bg_color=card_bg,
            border_width=1,
            idle_border_color=border_idle,  # Sehr subtiler Rahmen
        )
        self.app.ai_visualizer_frame.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=ds.get_spacing("md"),
            pady=(ds.get_spacing("sm"), ds.get_spacing("md")),
        )
        self.app.ai_visualizer_frame.grid_propagate(False)
        self.app.ai_visualizer_frame.grid_columnconfigure(0, weight=1)
        self.app.ai_visualizer_frame.grid_columnconfigure(1, weight=2)
        self.app.ai_visualizer_frame.grid_columnconfigure(2, weight=1)

        # Spotlight-Effekt für AI Visualizer Frame (temporär deaktiviert wegen Tkinter-Kompatibilität)
        # self.app.ai_spotlight = SpotlightOverlay(
        #     self.app.ai_visualizer_frame,
        #     spotlight_color="#60A5FA",
        #     spotlight_radius=150,
        #     intensity=0.15,
        #     border_glow_color="#00FF66",
        #     border_glow_intensity=0.35,
        # )

        # Responsive padding für AI Visualizer reduzieren für mehr Space
        ai_padding = ds.get_responsive_spacing("sm", self._window_width)

        # 1. Daily Goal Widget (Left)
        goal_container = ctk.CTkFrame(
            self.app.ai_visualizer_frame, fg_color="transparent"
        )
        goal_container.grid(
            row=0, column=0, sticky="nsew", padx=ai_padding, pady=ai_padding
        )

        ctk.CTkLabel(
            goal_container,
            text="🎯 Tages-Ziel (100€)",
            font=ds.get_font("sm", "medium"),
            text_color=ds.get_semantic_color("neutral"),
        ).pack(anchor="w")
        self.app.goal_progress = ctk.CTkProgressBar(
            goal_container, height=10, progress_color=ds.get_color("warning")
        )
        self.app.goal_progress.pack(fill="x", pady=(ds.get_spacing("sm"), 4))
        self.app.goal_progress.set(0.0)
        self.app.goal_lbl = ctk.CTkLabel(
            goal_container,
            text="0.00€ / 100€",
            font=ds.get_font("sm", "normal", mono=True),
            text_color=ds.get_color("neutral", "medium"),
        )
        self.app.goal_lbl.pack(anchor="e")

        # 2. AI Sonar Animation (Center — GSAP-inspiriert, 60 fps)
        # Hintergrund explizit auf bg_card setzen: nahtlose Einbettung im Panel
        sonar_bg = DesignSystem.BG['card']  # '#13151A'
        sonar_container = ctk.CTkFrame(
            self.app.ai_visualizer_frame, fg_color=sonar_bg
        )
        sonar_container.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=ds.get_spacing("md"),
            pady=ds.get_spacing("sm"),
        )
        sonar_container.grid_columnconfigure(0, weight=1)
        sonar_container.grid_rowconfigure(0, weight=1)

        sonar_width = max(200, min(320, self._window_width // 4))
        sonar_height = 110 if self._window_width < ds.BREAKPOINTS["md"] else 145

        self.app.sonar_anim = SonarAnimation(
            sonar_container, width=sonar_width, height=sonar_height, fps=60,
            bg_color=sonar_bg,  # BG-Sync: Animation passt zur Panel-Farbe
        )
        self.app.sonar_anim.canvas.grid(row=0, column=0)

        # Compat-Shims: Damit bestehender Code nicht bricht
        self.app.sonar_canvas = self.app.sonar_anim.canvas
        self.app.sonar_circles = []  # Nicht mehr genutzt, aber Referenz bleibt
        self.app.sonar_width = sonar_width
        self.app.sonar_height = sonar_height
        self.app.ai_status_lbl = None  # Status ist jetzt in der Animation eingebaut

        # 3. MVP Trade Widget (Right)
        mvp_container = ctk.CTkFrame(
            self.app.ai_visualizer_frame, fg_color="transparent"
        )
        mvp_container.grid(
            row=0, column=2, sticky="nsew", padx=ai_padding, pady=ai_padding
        )

        ctk.CTkLabel(
            mvp_container,
            text="🏆 Bester Trade Heute",
            font=ds.get_font("sm", "medium"),
            text_color=ds.get_semantic_color("neutral"),
        ).pack(anchor="e")
        self.app.mvp_trade_lbl = ctk.CTkLabel(
            mvp_container,
            text="Noch keine Trades",
            font=ds.get_font("xl", "bold", mono=True),
            text_color=ds.get_semantic_color("profit"),
        )
        self.app.mvp_trade_lbl.pack(anchor="e", pady=ds.get_spacing("md"))

        # State variables (Compat für bestehende Code-Stellen)
        self.app.ai_animation_idx = 0
        self.app.ai_current_symbol = None
        self.app._sonar_radii = [5, 15, 25]

        # Live Data List & P&L Chart - Responsive Aufteilung
        # Berechne Spaltenaufteilung basierend auf Fensterbreite
        if self._window_width < ds.BREAKPOINTS["sm"]:
            # Sehr schmal: untereinander
            live_data_colspan = 4
            chart_column = 0
            chart_colspan = 4
            chart_row = 4
        elif self._window_width < ds.BREAKPOINTS["md"]:
            # Schmal: Live Data bekommt mehr Platz (~3/4)
            live_data_colspan = 3
            chart_column = 3
            chart_colspan = 1
            chart_row = 3
        else:
            # Normal: 3:1 Aufteilung
            live_data_colspan = 3
            chart_column = 3
            chart_colspan = 1
            chart_row = 3

        # Responsive Spacing
        content_spacing = ds.get_responsive_spacing("sm", self._window_width)

        # Live Data List (Left Side)
        data_frame = HoverFadeFrame(
            self.tab,
            corner_radius=ds.get_radius("lg"),
            fg_color=card_bg,          # Einheitlicher bg_card Hintergrund
            active_bg_color=card_bg,
            border_width=1,
            idle_border_color=border_idle,
        )
        data_frame.grid(
            row=chart_row,
            column=0,
            columnspan=live_data_colspan,
            sticky="nsew",
            padx=content_spacing,
            pady=content_spacing,
        )
        data_frame.grid_rowconfigure(1, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)

        # Spotlight-Effekt für Live Data Frame (temporär deaktiviert)
        # self.app.data_spotlight = SpotlightOverlay(
        #     data_frame,
        #     spotlight_color="#60A5FA",
        #     spotlight_radius=120,
        #     intensity=0.12,
        #     border_glow_color="#FF1744",
        #     border_glow_intensity=0.25,
        # )

        header_lbl = ctk.CTkLabel(
            data_frame,
            text="Live Markt-Übersicht",
            font=ds.get_font("lg", "bold"),
            text_color=ds.get_semantic_color("neutral"),
        )
        header_lbl.grid(
            row=0,
            column=0,
            sticky="w",
            padx=ds.get_spacing("lg"),
            pady=ds.get_spacing("lg"),
        )

        self.app.scroll_list = ctk.CTkScrollableFrame(
            data_frame, fg_color="transparent"
        )
        self.app.scroll_list.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=ds.get_spacing("md"),
            pady=(0, ds.get_spacing("md")),
        )

        # Table Header - Lade Spalten aus Konfiguration
        header_row = ctk.CTkFrame(
            self.app.scroll_list, fg_color="transparent", height=30
        )
        header_row.pack(fill="x", pady=(0, ds.get_spacing("sm")))
        header_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="col")

        # Verwende konfigurierte Spaltennamen
        live_data_cols = config.live_data_columns
        col_names = [col.get("title", col.get("key", "")) for col in live_data_cols]

        for i, col_name in enumerate(col_names):
            lbl = ctk.CTkLabel(
                header_row,
                text=col_name,
                font=ds.get_font("xs", "medium"),
                text_color=ds.get_color("neutral", "medium"),
            )
            lbl.grid(row=0, column=i, sticky="w", padx=ds.get_spacing("md"))

        # Subtile Trennlinie — passend zum neuen Designsystem
        ctk.CTkFrame(
            self.app.scroll_list, height=1, fg_color=border_idle  # '#1E2128'
        ).pack(fill="x", pady=(0, ds.get_spacing("sm")))

        # Live P&L Chart (Right Side) - nur wenn genug Platz
        if chart_colspan > 0:
            self.app.chart_frame = HoverFadeFrame(
                self.tab,
                corner_radius=ds.get_radius("lg"),
                fg_color=card_bg,
                active_bg_color=card_bg,
                border_width=1,
                idle_border_color=border_idle,
            )
            self.app.chart_frame.grid(
                row=chart_row,
                column=chart_column,
                columnspan=chart_colspan,
                sticky="nsew",
                padx=(ds.get_spacing("md"), content_spacing),
                pady=content_spacing,
            )
            self.app.chart_frame.grid_rowconfigure(1, weight=1)
            self.app.chart_frame.grid_columnconfigure(0, weight=1)

            # Spotlight-Effekt für Chart Frame (temporär deaktiviert)
            # self.app.chart_spotlight = SpotlightOverlay(
            #     self.app.chart_frame,
            #     spotlight_color="#60A5FA",
            #     spotlight_radius=100,
            #     intensity=0.1,
            #     border_glow_color="#FFEA00",
            #     border_glow_intensity=0.2,
            # )

            chart_hdr = ctk.CTkLabel(
                self.app.chart_frame,
                text="Live P&L Laufzeit",
                font=ds.get_font("lg", "bold"),
                text_color=ds.get_semantic_color("neutral"),
            )
            chart_hdr.grid(
                row=0,
                column=0,
                sticky="w",
                padx=ds.get_spacing("lg"),
                pady=ds.get_spacing("lg"),
            )

            self.app.pnl_canvas = tk.Canvas(
                self.app.chart_frame,
                bg=DesignSystem.BG['card'],  # Einheitlich mit allen anderen Panels
                highlightthickness=0,
            )
            self.app.pnl_canvas.grid(
                row=1,
                column=0,
                sticky="nsew",
                padx=ds.get_spacing("md"),
                pady=(0, ds.get_spacing("md")),
            )

    def create_metric_card(
        self, parent, title, value, row, col, min_width=None, **kwargs
    ):
        card = MetricCard(
            parent, title=title, value=value, min_width=min_width, **kwargs
        )
        card.grid(
            row=row,
            column=col,
            padx=DesignSystem.get_spacing("md"),
            pady=DesignSystem.get_spacing("md"),
            sticky="nsew",
        )
        return card

    def populate_sample_data(self):
        """Initialise dashboard rows. Called once on startup; load_settings will override."""
        # Lade Symbole aus Konfiguration
        config_symbols = get_symbols()
        symbols_str = ", ".join(config_symbols)

        self.app.live_data_rows = []
        self._rebuild_symbol_rows(symbols_str)

    def _rebuild_symbol_rows(self, raw_pairs: str):
        """Parse comma-separated pairs string, rebuild app.dashboard_symbols and
        the live-data rows in the dashboard.  Safe to call at any time."""
        split_pairs = [p.strip().upper() for p in raw_pairs.split(",") if p.strip()]
        if not split_pairs:
            # Fallback to display dummy symbols if empty
            split_pairs = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]

        self.app.dashboard_symbols = [
            (f"{p[:3]}/{p[3:]}" if len(p) == 6 else p, p) for p in split_pairs
        ]

        # Destroy old rows
        if hasattr(self.app, "scroll_list"):
            for w in self.app.scroll_list.winfo_children():
                if isinstance(w, LiveDataRow):
                    w.destroy()

        if hasattr(self.app, "live_data_rows"):
            self.app.live_data_rows.clear()
        else:
            self.app.live_data_rows = []

        for display_name, symbol in self.app.dashboard_symbols:
            row = LiveDataRow(
                self.app.scroll_list, display_name, "---", "0.00%", "HOLD"
            )
            row.pack(fill="x", pady=2)
            row.update_data(
                "---", "0.00%", history=[1.0, 1.05, 1.02, 1.08, 1.07]
            )  # Dummy chart until live data arrives
            self.app.live_data_rows.append((symbol, row))

        if hasattr(self.app, "update_dashboard_data"):
            self.app.update_dashboard_data()
