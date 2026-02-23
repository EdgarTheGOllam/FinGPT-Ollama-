import customtkinter as ctk
import tkinter as tk
from gui.components.metric_card import MetricCard
from gui.components.live_data_row import LiveDataRow

class DashboardView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self.setup_ui()
        self.populate_sample_data()

    def setup_ui(self):
        self.tab.grid_columnconfigure((0, 1, 2), weight=1)
        self.tab.grid_rowconfigure(3, weight=1)
        
        # Top Cards
        self.app.balance_card = self.create_metric_card(self.tab, "Kontostand", "€--", 0, 0)
        self.app.positions_card = self.create_metric_card(self.tab, "Offene Positionen", "-", 0, 1)
        self.app.trades_card = self.create_metric_card(self.tab, "Heutige Trades", "-", 0, 2)
        
        self.app.pnl_card = self.create_metric_card(self.tab, "Gewinn/Verlust", "€--", 1, 0)
        self.app.winrate_card = self.create_metric_card(self.tab, "Margin Level", "-%", 1, 1)
        self.app.risk_card = self.create_metric_card(self.tab, "Freie Margin", "€--", 1, 2)

        # AI Agent Visualizer & Lückenfüller-Widgets (Middle Banner)
        # We increase height significantly for a more premium, large "Pinterest" feel.
        self.app.ai_visualizer_frame = ctk.CTkFrame(self.tab, height=140, corner_radius=15, fg_color=("gray85", "gray17"))
        self.app.ai_visualizer_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))
        self.app.ai_visualizer_frame.grid_propagate(False) # Keep fixed height
        self.app.ai_visualizer_frame.grid_columnconfigure(0, weight=1) # Goal
        self.app.ai_visualizer_frame.grid_columnconfigure(1, weight=2) # Center Sonar gets more space
        self.app.ai_visualizer_frame.grid_columnconfigure(2, weight=1) # Best Trade
        
        # 1. Daily Goal Widget (Left now)
        goal_container = ctk.CTkFrame(self.app.ai_visualizer_frame, fg_color="transparent")
        goal_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(goal_container, text="🎯 Tages-Ziel (100€)", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray60").pack(anchor="w")
        self.app.goal_progress = ctk.CTkProgressBar(goal_container, height=12, progress_color="#F1C40F")
        self.app.goal_progress.pack(fill="x", pady=(15, 5))
        self.app.goal_progress.set(0.0)
        self.app.goal_lbl = ctk.CTkLabel(goal_container, text="0.00€ / 100€", font=ctk.CTkFont(size=12), text_color="gray50")
        self.app.goal_lbl.pack(anchor="e")
        
        # 2. AI Sonar Canvas (Center - Large & Premium)
        sonar_container = ctk.CTkFrame(self.app.ai_visualizer_frame, fg_color="transparent")
        sonar_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        # Center the canvas within this column
        sonar_container.grid_columnconfigure(0, weight=1)
        sonar_container.grid_rowconfigure(0, weight=1)
        
        # Much larger canvas for a "Pinterest" style floating orb array
        # bg matches gray17 #2b2b2b
        self.app.sonar_width = 300
        self.app.sonar_height = 120
        self.app.sonar_canvas = tk.Canvas(sonar_container, bg="#2b2b2b", width=self.app.sonar_width, height=self.app.sonar_height, highlightthickness=0)
        self.app.sonar_canvas.grid(row=0, column=0, pady=(5, 0)) # Centered
        
        self.app.ai_status_lbl = ctk.CTkLabel(sonar_container, text="Zzz... Warte auf Live-Stream", font=ctk.CTkFont(size=13, slant="italic"), text_color="gray50")
        self.app.ai_status_lbl.grid(row=1, column=0, pady=(5, 5))
        
        # Set up dynamic orb lists
        self.app.sonar_circles = []
        cx, cy = self.app.sonar_width / 2, self.app.sonar_height / 2
        # Center core dot
        self.app._sonar_base_dot = self.app.sonar_canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill="gray40", outline="")
        
        # 3. MVP Trade Widget (Right)
        mvp_container = ctk.CTkFrame(self.app.ai_visualizer_frame, fg_color="transparent")
        mvp_container.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(mvp_container, text="🏆 Bester Trade Heute", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray60").pack(anchor="e")
        self.app.mvp_trade_lbl = ctk.CTkLabel(mvp_container, text="Noch keine Trades", font=ctk.CTkFont(size=18, weight="bold"), text_color="#5EBA7D")
        self.app.mvp_trade_lbl.pack(anchor="e", pady=10)
        
        # State variables for animation
        self.app.ai_animation_idx = 0
        self.app.ai_current_symbol = None
        self.app._sonar_radii = [5, 15, 25] # Starting radii for expanding rings

        # Live Data List (Left Side)
        data_frame = ctk.CTkFrame(self.tab, corner_radius=15, fg_color=("gray90", "gray13"))
        data_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(10, 5), pady=10)
        data_frame.grid_rowconfigure(1, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)

        header_lbl = ctk.CTkLabel(data_frame, text="Live Markt-Übersicht", font=ctk.CTkFont(size=16, weight="bold"))
        header_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.app.scroll_list = ctk.CTkScrollableFrame(data_frame, fg_color="transparent")
        self.app.scroll_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Table Header
        header_row = ctk.CTkFrame(self.app.scroll_list, fg_color="transparent", height=30)
        header_row.pack(fill="x", pady=(0, 5))
        header_row.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        
        for i, col_name in enumerate(["Symbol", "Preis", "Änderung", "Trend (M15|H1|H4)", "Signal"]):
            lbl = ctk.CTkLabel(header_row, text=col_name, font=ctk.CTkFont(weight="bold", size=12), text_color="gray50")
            lbl.grid(row=0, column=i, sticky="w", padx=10)

        ctk.CTkFrame(self.app.scroll_list, height=1, fg_color=("gray70", "gray30")).pack(fill="x", pady=(0, 5))

        # Live P&L Chart (Right Side)
        self.app.chart_frame = ctk.CTkFrame(self.tab, corner_radius=15, fg_color=("gray90", "gray13"))
        self.app.chart_frame.grid(row=3, column=2, sticky="nsew", padx=(5, 10), pady=10)
        self.app.chart_frame.grid_rowconfigure(1, weight=1)
        self.app.chart_frame.grid_columnconfigure(0, weight=1)
        
        chart_hdr = ctk.CTkLabel(self.app.chart_frame, text="Live P&L Laufzeit", font=ctk.CTkFont(size=16, weight="bold"))
        chart_hdr.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # We use a native Tkinter canvas for high-performance smooth drawing
        self.app.pnl_canvas = tk.Canvas(self.app.chart_frame, bg="#212121", highlightthickness=0)
        self.app.pnl_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))


    def create_metric_card(self, parent, title, value, row, col):
        card = MetricCard(parent, title=title, value=value)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        return card

    def populate_sample_data(self):
        """Initialise dashboard rows. Called once on startup; load_settings will override."""
        self.app.live_data_rows = []
        self._rebuild_symbol_rows("EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD")

    def _rebuild_symbol_rows(self, raw_pairs: str):
        """Parse comma-separated pairs string, rebuild app.dashboard_symbols and
        the live-data rows in the dashboard.  Safe to call at any time."""
        split_pairs = [p.strip().upper() for p in raw_pairs.split(',') if p.strip()]
        if not split_pairs:
            return

        self.app.dashboard_symbols = [
            (f"{p[:3]}/{p[3:]}" if len(p) == 6 else p, p)
            for p in split_pairs
        ]

        # Destroy old rows
        if hasattr(self.app, 'scroll_list'):
            for w in self.app.scroll_list.winfo_children():
                if isinstance(w, LiveDataRow):
                    w.destroy()

        if hasattr(self.app, 'live_data_rows'):
            self.app.live_data_rows.clear()
        else:
            self.app.live_data_rows = []

        for display_name, symbol in self.app.dashboard_symbols:
            row = LiveDataRow(self.app.scroll_list, display_name, "---", "0.00%", "HOLD")
            row.pack(fill="x", pady=2)
            self.app.live_data_rows.append((symbol, row))

        if hasattr(self.app, 'update_dashboard_data'):
            self.app.update_dashboard_data()
