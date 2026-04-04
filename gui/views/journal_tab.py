import customtkinter as ctk
import threading
import json
import os
import glob
from datetime import datetime, timezone
import calendar
import pandas as pd

class JournalView:
    def __init__(self, tab, app):
        """
        tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = tab
        self.app = app
        
        # ── State ──────────────────────────────────────────
        self._journal_year  = datetime.now().year
        self._journal_month = datetime.now().month
        self._journal_entries   = {}  # date_str -> list of trade dicts
        self._selected_journal_day = None
        self._selected_trade  = None

        self.setup_ui()
        
    def setup_ui(self):
        """📝 Journal Component UI setup"""
        self.tab.grid_columnconfigure(0, weight=0)  # Calendar is fixed width
        self.tab.grid_columnconfigure(1, weight=1)  # Trade list expands
        self.tab.grid_rowconfigure(1, weight=1)     # Expand both vertically

        # Seed demo data on very first run so calendar isn't empty
        self._seed_demo_trades()

        # ── Top bar: calendar controls + stats ─────────────
        top = ctk.CTkFrame(self.tab, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        top.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(top, text="◀", width=36, command=self._journal_prev_month).grid(row=0, column=0, padx=(0, 4))
        self._cal_title_lbl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(family="Inter", size=15, weight="bold"))
        self._cal_title_lbl.grid(row=0, column=1, padx=8)
        ctk.CTkButton(top, text="▶", width=36, command=self._journal_next_month).grid(row=0, column=2, sticky="w", padx=(4, 0))

        # Stats summary labels
        stats_frame = ctk.CTkFrame(top, fg_color="transparent")
        stats_frame.grid(row=0, column=3, sticky="e", padx=(20, 0))
        self._j_stat_trades = ctk.CTkLabel(stats_frame, text="Trades: --", font=ctk.CTkFont(family="Inter", size=12), text_color="#8B949E")
        self._j_stat_trades.pack(side="left", padx=8)
        self._j_stat_winrate = ctk.CTkLabel(stats_frame, text="Win Rate: --%", font=ctk.CTkFont(family="Inter", size=12), text_color="#8B949E")
        self._j_stat_winrate.pack(side="left", padx=8)
        self._j_stat_pnl = ctk.CTkLabel(stats_frame, text="Gesamt P&L: --", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#8B949E")
        self._j_stat_pnl.pack(side="left", padx=8)
        ctk.CTkButton(stats_frame, text="📥 CSV Export", width=110, command=self._export_journal_csv,
                      fg_color="transparent", border_width=1).pack(side="left", padx=(16, 0))

        # ── Left container (Calendar + Report) ───────────────────
        self._left_panel = ctk.CTkFrame(self.tab, fg_color="transparent")
        self._left_panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        self._left_panel.grid_rowconfigure(1, weight=1)
        self._left_panel.grid_columnconfigure(0, weight=1)

        # ── Left Top: Calendar grid ──────────────────────────────────
        self._cal_frame = ctk.CTkFrame(self._left_panel, fg_color="#1A1D24", corner_radius=12)
        self._cal_frame.grid(row=0, column=0, sticky="n", pady=(0, 10))

        # ── Left Bottom: Monthly Report ──────────────────────────────
        self._report_frame = ctk.CTkFrame(self._left_panel, fg_color="#1A1D24", corner_radius=12)
        self._report_frame.grid(row=1, column=0, sticky="nsew")
        self._report_frame.grid_rowconfigure(2, weight=1)
        self._report_frame.grid_columnconfigure(0, weight=1)
        
        rep_hdr = ctk.CTkLabel(self._report_frame, text="📊 Monatsbericht", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#C586C0")
        rep_hdr.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        
        self._report_stats_lbl = ctk.CTkLabel(self._report_frame, text="Lade Daten...", font=ctk.CTkFont(family="Inter", size=11), text_color="#8B949E", justify="left")
        self._report_stats_lbl.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))
        
        self._report_chart_container = ctk.CTkFrame(self._report_frame, fg_color="transparent")
        self._report_chart_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))


        # ── Right: Trade list and AI reasoning ────────────────────
        right_panel = ctk.CTkFrame(self.tab, fg_color="transparent")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=8)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)

        # Trade list (scrollable)
        list_container = ctk.CTkFrame(right_panel, corner_radius=12, fg_color="#1A1D24")
        list_container.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(2, weight=1)

        self._j_list_title = ctk.CTkLabel(list_container, text="← Klicke einen Tag im Kalender, um Trades zu sehen",
                                           font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#8B949E")
        self._j_list_title.grid(row=0, column=0, sticky="w", padx=15, pady=8)

        # Header row
        hdr = ctk.CTkFrame(list_container, fg_color="#1A1D24", corner_radius=0)
        hdr.grid(row=1, column=0, sticky="ew", padx=0)
        for col, (txt, w) in enumerate([("Ticket", 80), ("Symbol", 80), ("Richtung", 80),
                                         ("Eröffnung", 90), ("Schlusskurs", 90),
                                         ("Lots", 55), ("Profit", 80), ("KI", 40)]):
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                         text_color="#8B949E", width=w).grid(row=0, column=col, padx=6, pady=4, sticky="w")

        self._j_scroll = ctk.CTkScrollableFrame(list_container, fg_color="transparent", corner_radius=0)
        self._j_scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        # AI Reasoning Panel (collapsible)
        self._ai_panel = ctk.CTkFrame(right_panel, corner_radius=12, fg_color="#1A1D24")
        self._ai_panel.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        self._ai_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self._ai_panel, text="🤖", font=ctk.CTkFont(family="Inter", size=20)).grid(row=0, column=0, padx=(15, 8), pady=10)
        self._ai_panel_header = ctk.CTkLabel(self._ai_panel,
                                              text="KI Begründung — klicke 🤖 in einer Trade-Zeile",
                                              font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#8B949E")
        self._ai_panel_header.grid(row=0, column=1, sticky="w")
        
        self._ai_reflection_btn = ctk.CTkButton(self._ai_panel, text="🧠 System-Analyse anfordern",
                                          font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                                          fg_color="#9C27B0", hover_color="#8c3363",
                                          width=180, height=28, command=self._analyze_past_trade_async)
        # We grid it conditionally in _show_ai_reasoning

        self._ai_visualizer_btn = ctk.CTkButton(self._ai_panel, text="📈 Trade Visualizer",
                                          font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                                          fg_color="#2979FF", hover_color="#1a5f7a",
                                          width=150, height=28, command=self._show_trade_visualizer)
        # We grid it conditionally in _show_ai_reasoning

        self._ai_reasoning_box = ctk.CTkTextbox(self._ai_panel, height=100, fg_color="transparent",
                                                  font=ctk.CTkFont(family="Inter", size=12),
                                                  text_color="#D4D4D4", wrap="word", state="disabled")
        self._ai_reasoning_box.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 10))

        self._ai_indicators_lbl = ctk.CTkLabel(self._ai_panel, text="", font=ctk.CTkFont(family="Inter", size=11),
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
        entries = {}  # date_str -> [trade_dict, ...]

        # ── 1. Try pulling real MT5 history ──────────────────────────────
        try:
            import MetaTrader5 as _mt5
            if not _mt5.initialize():
                raise RuntimeError("MT5 not initialized")

            # Month range (UTC timestamps)
            from_dt = datetime(year, month, 1, tzinfo=timezone.utc)
            # Last day of month
            last_day = calendar.monthrange(year, month)[1]
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
            if hasattr(self.app, 'write_terminal'):
                self.app.after(0, lambda e=str(mt5_err): self.app.write_terminal(
                    f">> [JOURNAL] MT5 nicht verfügbar, lade JSON-Daten. ({e})\n", "WARNING"))

        # ── 2. Load JSON files (AI reasoning overlay / fallback) ──────────
        # Check if sys.path context or __file__ has right directory structure. We use the desktop app root.
        # Check if sys.path context or __file__ has right directory structure. We use the desktop app root.
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        journal_dir = os.path.join(base_dir, "storage", "trade_journal")
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
        pnl_color = "#00FF66" if total_pnl >= 0 else "#FF1744"
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
                         font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                         text_color="#8B949E", width=52).grid(row=0, column=col, padx=2, pady=(6, 2))

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
                    bg = ("#D5D5D5", "#2A2A2A") if not is_today else "#2979FF"
                    fg = "gray50"
                elif day_pnl > 0:
                    bg = ("#C8F7C5", "#1A4A30")
                    fg = "#00FF66"
                else:
                    bg = ("#FAD4D4", "#4A1A1A")
                    fg = "#FF1744"

                # Build the day cell frame (acts as a button)
                cell = ctk.CTkFrame(self._cal_frame, width=58, height=58, corner_radius=8,
                                    fg_color=bg, cursor="hand2")
                cell.grid(row=row_idx + 1, column=col_idx, padx=2, pady=2)
                cell.grid_propagate(False)

                num_lbl = ctk.CTkLabel(cell, text=str(day),
                                       font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
                                       text_color=("gray20", "white") if n_trades == 0 else fg)
                num_lbl.place(relx=0.5, rely=0.35, anchor="center")

                if n_trades > 0:
                    sub_lbl = ctk.CTkLabel(cell, text=f"{n_trades}T  {'+' if day_pnl>=0 else ''}{day_pnl:.0f}€",
                                           font=ctk.CTkFont(family="Inter", size=8), text_color=fg)
                    sub_lbl.place(relx=0.5, rely=0.75, anchor="center")

                # Click binding
                for widget in [cell, num_lbl]:
                    widget.bind("<Button-1>", lambda e, ds=date_str: self._show_day_trades(ds))
                if n_trades > 0:
                    sub_lbl.bind("<Button-1>", lambda e, ds=date_str: self._show_day_trades(ds))

        # Render Monthly Report
        self._render_monthly_report(entries)

    def _render_monthly_report(self, entries):
        # Clear old chart
        for w in self._report_chart_container.winfo_children():
            w.destroy()

        all_trades = [t for day_trades in entries.values() for t in day_trades]
        if not all_trades:
            self._report_stats_lbl.configure(text="Keine Trades in diesem Monat.")
            return

        gross_profit = sum(t.get("profit", 0) for t in all_trades if t.get("profit", 0) > 0)
        gross_loss = abs(sum(t.get("profit", 0) for t in all_trades if t.get("profit", 0) < 0))
        net_profit = gross_profit - gross_loss
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        wins = sum(1 for t in all_trades if t.get("profit", 0) > 0)
        win_rate = (wins / len(all_trades) * 100)
        best_trade = max((t.get("profit", 0) for t in all_trades), default=0)
        worst_trade = min((t.get("profit", 0) for t in all_trades), default=0)

        stats_text = (
            f"Netto P&L: {net_profit:+.2f}€    Profit Faktor: {profit_factor:.2f}\n"
            f"Win Rate: {win_rate:.1f}% ({wins}/{len(all_trades)})    Bester Trade: {best_trade:.2f}€\n"
            f"Brutto Gewinn: +{gross_profit:.2f}€    Brutto Verlust: -{gross_loss:.2f}€"
        )
        self._report_stats_lbl.configure(text=stats_text)

        # Build Daily Cumulative PnL
        daily_pnl = {}
        for date_str, trades in entries.items():
            daily_pnl[date_str] = sum(t.get("profit", 0) for t in trades)
            
        # Ensure all days of the month are in the chart (up to today or end of month)
        import calendar
        year, month = self._journal_year, self._journal_month
        last_day = calendar.monthrange(year, month)[1]
        
        x_days = []
        y_pnl = []
        cum_pnl = 0
        
        for d in range(1, last_day + 1):
            date_str = f"{year}-{month:02d}-{d:02d}"
            cum_pnl += daily_pnl.get(date_str, 0)
            x_days.append(d)
            y_pnl.append(cum_pnl)

        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        fig = Figure(figsize=(4, 2.5), facecolor='#1A1D24')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#1A1D24')
        ax.tick_params(colors='#8B949E', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#333333')
            
        # Plot area
        line_color = '#00FF66' if cum_pnl >= 0 else '#FF1744'
        ax.plot(x_days, y_pnl, color=line_color, linewidth=2)
        ax.fill_between(x_days, y_pnl, 0, color=line_color, alpha=0.1)
        ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        ax.set_title("Kumulierter P&L (Monat)", color='#8B949E', fontsize=10, pad=10)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self._report_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _show_day_trades(self, date_str):
        """Populate the trade list for a clicked day."""
        self._selected_journal_day = date_str
        day_trades = self._journal_entries.get(date_str, [])

        # Update title
        day_pnl = sum(t.get("profit", 0) for t in day_trades)
        pnl_color = "#00FF66" if day_pnl >= 0 else "#FF1744"
        self._j_list_title.configure(
            text=f"📅 {date_str}  —  {len(day_trades)} Trade(s)  |  P&L: {'+' if day_pnl>=0 else ''}{day_pnl:.2f}€",
            text_color=pnl_color if day_trades else "gray60")

        # Clear old rows
        for w in self._j_scroll.winfo_children():
            w.destroy()

        if not day_trades:
            ctk.CTkLabel(self._j_scroll, text="Keine Trades an diesem Tag.",
                         text_color="#8B949E").pack(pady=20)
            return

        for i, trade in enumerate(day_trades):
            profit = trade.get("profit", 0)
            profit_color = "#00FF66" if profit >= 0 else "#FF1744"
            row_bg = "#1A1D24" if i % 2 == 0 else "#1A1D24"

            row = ctk.CTkFrame(self._j_scroll, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)
            
            # Make the row flexible so it pushes the button to the right but keeps it visible
            row.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)
            row.grid_columnconfigure(7, weight=0, minsize=45) # AI Button Column

            def fmt_price(p):
                if isinstance(p, (float, int)):
                    return f"{p:.5f}".rstrip('0').rstrip('.')
                return str(p)

            data = [
                (str(trade.get("ticket", "-")), 60, "gray60"),
                (trade.get("symbol", "-"), 70, "white"),
                (trade.get("action", "-"), 60, "#00FF66" if trade.get("action") == "BUY" else "#FF1744"),
                (fmt_price(trade.get("open_price", "-")), 80, "gray80"),
                (fmt_price(trade.get("close_price", trade.get("open_price", "-"))), 80, "gray80"),
                (str(trade.get("lot_size", "-")), 50, "gray70"),
                (f"{'+' if profit>=0 else ''}{profit:.2f}€", 75, profit_color),
            ]
            for col_idx, (text, width, color) in enumerate(data):
                ctk.CTkLabel(row, text=text, width=width, text_color=color,
                             font=ctk.CTkFont(family="Inter", size=11), anchor="w").grid(row=0, column=col_idx, padx=4, pady=6, sticky="w")

            # AI reasoning button
            ai_btn = ctk.CTkButton(row, text="🤖", width=36, height=28,
                                    fg_color="#1A1A4A" if trade.get("ai_reasoning") else "transparent",
                                    hover_color="#2979FF",
                                    command=lambda t=trade: self._show_ai_reasoning(t))
            ai_btn.grid(row=0, column=len(data), padx=(0, 6), pady=6, sticky="e")

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
            self._ai_visualizer_btn.grid(row=0, column=3, padx=(0, 15))
        else:
            self._ai_reflection_btn.grid_forget()
            self._ai_visualizer_btn.grid(row=0, column=2, padx=(0, 15))

    def _show_trade_visualizer(self):
        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        import mplfinance as mpf
        import MetaTrader5 as mt5

        trade = getattr(self, "_selected_trade", None)
        if not trade: 
            return
            
        symbol = trade.get("symbol")
        if not symbol:
            if hasattr(self.app, 'write_terminal'):
                self.app.write_terminal(">> [JOURNAL] Kann Trade nicht visualisieren: Kein Symbol vorhanden.\n", "ERROR")
            return
            
        action = trade.get("action", "BUY")
        open_time = trade.get("open_time")
        close_time = trade.get("close_time")
        
        entry_price = float(trade.get("open_price", 0)) if trade.get("open_price") else None
        sl_price = float(trade.get("stop_loss", 0)) if trade.get("stop_loss") else None
        tp_price = float(trade.get("take_profit", 0)) if trade.get("take_profit") else None
        ai_reasoning = trade.get("ai_reasoning", "Keine KI-Begründung für diesen Trade gespeichert.")
        
        if not open_time:
            if hasattr(self.app, 'write_terminal'):
                self.app.write_terminal(">> [JOURNAL] Kann Trade nicht visualisieren: Keine Open-Zeit vorhanden.\n", "ERROR")
            return

        popup = ctk.CTkToplevel(self.app)
        popup.title(f"Trade Visualizer  —  {symbol} {action} Ticket {trade.get('ticket', '')}")
        popup.geometry("900x550")
        popup.configure(fg_color="#0F111A")
        popup.grab_set()

        status = ctk.CTkLabel(popup, text=f"Lade historische MT5-Daten für {symbol}...", font=ctk.CTkFont(family="Inter", size=14))
        status.pack(expand=True)

        # Modern vibrant colors (TradingView dark mode inspired)
        mc = mpf.make_marketcolors(
            up='#26A69A', down='#EF5350',
            edge={'up': '#26A69A', 'down': '#EF5350'},
            wick={'up': '#26A69A', 'down': '#EF5350'},
            ohlc='i'
        )
        s = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor='#0F111A',
            edgecolor='#2A2E39',
            figcolor='#0F111A',
            gridcolor='#1E222D',
            gridstyle='--',
            rc={'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10, 'text.color': '#D1D4DC'}
        )

        def fetch_chart():
            try:
                if not mt5.initialize():
                    raise Exception("MT5 nicht verbunden")
                
                # Convert ISO string times to pandas datetime
                import dateutil.parser
                t_open = dateutil.parser.parse(open_time).replace(tzinfo=None) # naive
                
                if close_time:
                    t_close = dateutil.parser.parse(close_time).replace(tzinfo=None)
                else:
                    t_close = datetime.now()
                    
                tf = mt5.TIMEFRAME_M15
                import pytz
                
                time_from = t_open - pd.Timedelta(hours=10)
                time_to = t_close + pd.Timedelta(hours=5)
                
                rates = mt5.copy_rates_range(symbol, tf, time_from, time_to)
                if rates is None or len(rates) < 5:
                    raise Exception("Nicht genügend MT5 Daten für diesen Zeitraum gefunden.")
                
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                
                # Locate indices for annotations
                df['dist_o'] = abs(df.index - t_open)
                open_idx = df.index.get_loc(df['dist_o'].idxmin())
                
                close_idx = None
                if close_time:
                    df['dist_c'] = abs(df.index - t_close)
                    close_idx = df.index.get_loc(df['dist_c'].idxmin())

                fig = Figure(figsize=(9, 4), facecolor='#0F111A') 
                ax = fig.add_subplot(111)
                ax.set_facecolor('#0F111A')
                ax.tick_params(colors='#787B86')
                
                pnl_str = f"Profit: {trade.get('profit', 0):.2f}€"
                ax.set_title(f"{action} {symbol}  |  {pnl_str}", color='#D1D4DC', fontsize=13, pad=15, fontweight='bold')
                
                # Clean up borders
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_color('#2A2E39')
                ax.spines['left'].set_color('#2A2E39')

                mpf.plot(df, type='candle', ax=ax, style=s, show_nontrading=False, warn_too_much_data=2000)

                bbox_props = dict(boxstyle="round,pad=0.4", fc="#1E222D", ec="#3B404E", lw=1)
                open_color = '#2962FF'
                arrow = '▲' if action == 'BUY' else '▼'
                
                y_pos_open = df.iloc[open_idx]['low'] * 0.999 if action == 'BUY' else df.iloc[open_idx]['high'] * 1.001
                
                ax.annotate(f"{arrow} OPEN", xy=(open_idx, y_pos_open),
                            xycoords=('data', 'data'), ha='center', va='top' if action == 'BUY' else 'bottom',
                            color=open_color, fontsize=9, fontweight='bold', bbox=bbox_props)
                            
                if close_idx is not None:
                    close_arrow = '▼' if action == 'BUY' else '▲'
                    y_pos_close = df.iloc[close_idx]['high'] * 1.001 if action == 'BUY' else df.iloc[close_idx]['low'] * 0.999
                    
                    is_profit = trade.get('profit', 0) > 0
                    c_color = '#26A69A' if is_profit else '#EF5350'

                    ax.annotate(f"{close_arrow} CLOSE", xy=(close_idx, y_pos_close),
                                xycoords=('data', 'data'), ha='center', va='bottom' if action == 'BUY' else 'top',
                                color=c_color, fontsize=9, fontweight='bold', bbox=bbox_props)
                                
                    ax.plot([open_idx, close_idx], [df.iloc[open_idx]['close'], df.iloc[close_idx]['close']], 
                           color='#787B86', linestyle=':', linewidth=1.5, alpha=0.8)
                           
                x_max = len(df) - 1
                line_text_bg = dict(boxstyle="round,pad=0.2", fc="#0F111A", ec="none")

                if entry_price and entry_price > 0:
                    ax.axhline(entry_price, color='#2962FF', linestyle='-', linewidth=1, alpha=0.6)
                    ax.text(x_max, entry_price, " ENTRY", color='#2962FF', va='center', ha='left', fontsize=8, fontweight='bold', bbox=line_text_bg)
                
                if sl_price and sl_price > 0:
                    ax.axhline(sl_price, color='#EF5350', linestyle='--', linewidth=1, alpha=0.6)
                    ax.text(x_max, sl_price, " SL", color='#EF5350', va='center', ha='left', fontsize=8, fontweight='bold', bbox=line_text_bg)
                    
                if tp_price and tp_price > 0:
                    ax.axhline(tp_price, color='#26A69A', linestyle='--', linewidth=1, alpha=0.6)
                    ax.text(x_max, tp_price, " TP", color='#26A69A', va='center', ha='left', fontsize=8, fontweight='bold', bbox=line_text_bg)

                fig.tight_layout()
                self.app.after(0, lambda: _embed_chart(fig))
            except Exception as e:
                err = str(e)
                self.app.after(0, lambda msg=err: status.configure(text=f"Fehler beim Laden des Charts:\n{msg}", text_color="#FF1744"))

        def _embed_chart(fig):
            status.destroy()
            canvas = FigureCanvasTkAgg(fig, master=popup)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(10, 0))
            
            info_frame = ctk.CTkFrame(popup, fg_color="#14151B", corner_radius=10, border_width=1, border_color="#2A2E39")
            info_frame.pack(fill="x", side="bottom", padx=10, pady=10)
            
            header = ctk.CTkLabel(info_frame, text="🤖 KI Begründung & Trade-Setup", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#A9B1D6")
            header.pack(anchor="w", padx=15, pady=(10, 5))
            
            details = f"Einstieg: {entry_price if entry_price else '-'}      SL: {sl_price if sl_price else '-'}      TP: {tp_price if tp_price else '-'}"
            details_lbl = ctk.CTkLabel(info_frame, text=details, font=ctk.CTkFont(family="Inter", size=12), text_color="#8B949E")
            details_lbl.pack(anchor="w", padx=15, pady=(0, 5))
            
            reason_box = ctk.CTkTextbox(info_frame, height=80, fg_color="transparent", text_color="#D1D4DC", wrap="word")
            reason_box.pack(fill="x", padx=10, pady=(0, 10))
            reason_box.insert("1.0", str(ai_reasoning).strip())
            reason_box.configure(state="disabled")

        threading.Thread(target=fetch_chart, daemon=True).start()

    def _analyze_past_trade_async(self):
        trade = self._selected_trade
        if not trade or not trade.get("_filepath"):
            return
            
        self._ai_reflection_btn.configure(state="disabled", text="Analysiere...")
        
        def run_analysis():
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
            
            try:
                sys_prompt = "Du bist ein professioneller Trading-Coach."
                if hasattr(self.app, '_call_llm_api'):
                    result = self.app._call_llm_api(system_prompt=sys_prompt, user_prompt=prompt, max_tokens=300)
                else:
                    result = "KI API auf Ebene MainWindow nicht gefunden."
                if result and not result.startswith("[Fehler") and not result.startswith("[API Fehler"):
                    result_text = result
                else:
                    result_text = result if result else "Keine vernünftige Antwort erhalten."
            except Exception as e:
                result_text = f"KI Fehler: {str(e)}"
                
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
                    if hasattr(self.app, 'write_terminal'):
                        self.app.write_terminal(f">> [JOURNAL] KI-Reflexion für Ticket {trade.get('ticket')} dauerhaft gespeichert.\n", "SUCCESS")
                except Exception as e:
                    if hasattr(self.app, 'write_terminal'):
                        self.app.write_terminal(f">> [JOURNAL] Fehler beim Speichern der Reflexion: {e}\n", "ERROR")
                
                # Update UI
                self._show_ai_reasoning(trade)
                
            self.app.after(0, on_done)
            
        threading.Thread(target=run_analysis, daemon=True).start()

    def _export_journal_csv(self):
        """Export currently visible month's trades to CSV."""
        import csv
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
        if hasattr(self.app, 'write_terminal'):
            self.app.write_terminal(f">> [JOURNAL] CSV exportiert: {filepath}\n", "SYSTEM")

    def _seed_demo_trades(self):
        """Create demo journal entries if trade_journal folder is empty."""
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        journal_dir = os.path.join(base_dir, "storage", "trade_journal")
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
