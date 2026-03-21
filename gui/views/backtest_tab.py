import customtkinter as ctk
import tkinter as tk
import threading
import math
import os
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class BacktestView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self._last_trades = []
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(2, weight=1)

        # ── Control Bar (Row 0) ──────────────────────────────────────
        ctrl = ctk.CTkScrollableFrame(self.tab, orientation="horizontal", fg_color="transparent", height=80)
        ctrl.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkLabel(ctrl, text="Symbol:").pack(side="left", padx=(0, 4))
        self.symbol_combo = ctk.CTkComboBox(ctrl, values=["EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","XAUUSD"], width=110)
        self.symbol_combo.set("EURUSD")
        self.symbol_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(ctrl, text="Timeframe:").pack(side="left", padx=(0, 4))
        self.tf_combo = ctk.CTkComboBox(ctrl, values=["M15 (15 Min)","M30 (30 Min)","H1 (1 Std)","H4 (4 Std)","D1 (Täglich)"], width=130)
        self.tf_combo.set("H1 (1 Std)")
        self.tf_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(ctrl, text="Bars:").pack(side="left", padx=(0, 4))
        self.bars_combo = ctk.CTkComboBox(ctrl, values=["200","500","1000","2000","5000"], width=80)
        self.bars_combo.set("500")
        self.bars_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(ctrl, text="Strategie:").pack(side="left", padx=(0, 4))
        self.strategy_combo = ctk.CTkComboBox(ctrl, values=[
            "SMC Fair Value Gap", "SMC Order Block",
            "Bullish Engulfing", "EMA 20/50 Crossover",
            "RSI Überkauft/Überverkauft", "Bollinger Band Squeeze"], width=210)
        self.strategy_combo.set("SMC Fair Value Gap")
        self.strategy_combo.pack(side="left", padx=(0, 10))

        # ── New: Startkapital ──
        ctk.CTkLabel(ctrl, text="Kapital (€):").pack(side="left", padx=(0, 4))
        self.capital_entry = ctk.CTkEntry(ctrl, width=80, placeholder_text="10000")
        self.capital_entry.insert(0, "10000")
        self.capital_entry.pack(side="left", padx=(0, 10))

        # ── New: Risk per Trade ──
        ctk.CTkLabel(ctrl, text="Risiko/Trade (%):").pack(side="left", padx=(0, 4))
        self.risk_entry = ctk.CTkEntry(ctrl, width=60, placeholder_text="1.0")
        self.risk_entry.insert(0, "1.0")
        self.risk_entry.pack(side="left", padx=(0, 10))

        # ── New: R:R Slider ──
        ctk.CTkLabel(ctrl, text="R:R:").pack(side="left", padx=(0, 4))
        rr_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        rr_frame.pack(side="left", padx=(0, 10))
        self.rr_lbl = ctk.CTkLabel(rr_frame, text="1.5", width=30, font=ctk.CTkFont(size=11))
        self.rr_lbl.pack(side="right")
        self.rr_slider = ctk.CTkSlider(rr_frame, from_=1.0, to=3.0, number_of_steps=20, width=100,
                                        command=lambda v: self.rr_lbl.configure(text=f"{v:.1f}"))
        self.rr_slider.set(1.5)
        self.rr_slider.pack(side="left")

        # ── New: ATR Multiplier ──
        ctk.CTkLabel(ctrl, text="ATR×SL:").pack(side="left", padx=(0, 4))
        atr_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        atr_frame.pack(side="left", padx=(0, 10))
        self.atr_lbl = ctk.CTkLabel(atr_frame, text="1.0", width=30, font=ctk.CTkFont(size=11))
        self.atr_lbl.pack(side="right")
        self.atr_slider = ctk.CTkSlider(atr_frame, from_=0.5, to=3.0, number_of_steps=25, width=100,
                                         command=lambda v: self.atr_lbl.configure(text=f"{v:.1f}"))
        self.atr_slider.set(1.0)
        self.atr_slider.pack(side="left")

        # ── New: Spread ──
        ctk.CTkLabel(ctrl, text="Spread (Pips):").pack(side="left", padx=(0, 4))
        self.spread_entry = ctk.CTkEntry(ctrl, width=55, placeholder_text="1.0")
        self.spread_entry.insert(0, "1.0")
        self.spread_entry.pack(side="left", padx=(0, 10))

        self.run_btn = ctk.CTkButton(ctrl, text="▶ Backtest Starten",
                                          fg_color="#00FF66", hover_color="#4CAF50", width=160,
                                          command=self._run_backtest_threaded)
        self.run_btn.pack(side="left", padx=(6, 4))

        # ── New: CSV Export ──
        self.export_btn = ctk.CTkButton(ctrl, text="📥 CSV Export",
                                         fg_color="transparent", border_width=1,
                                         text_color="#8B949E", width=110,
                                         state="disabled",
                                         command=self._export_csv)
        self.export_btn.pack(side="left", padx=(0, 10))

        self.status_lbl = ctk.CTkLabel(ctrl, text="Bereit.", text_color="#8B949E",
                                        font=ctk.CTkFont(family="Inter", size=12))
        self.status_lbl.pack(side="left", padx=10)

        # ── Progress bar ──────────────────────────────────────────
        self.progress_bar = ctk.CTkProgressBar(self.tab, mode="indeterminate", progress_color="#00FF66")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        self.progress_bar.set(0)

        # ── Main Area: Stats + Chart + Trade List ─────────────────
        main = ctk.CTkFrame(self.tab, fg_color="transparent")
        main.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        main.grid_columnconfigure(0, weight=2)  # chart
        main.grid_columnconfigure(1, weight=1)  # stats + trades
        main.grid_rowconfigure(0, weight=1)

        # Left: Equity Curve canvas
        chart_frame = ctk.CTkFrame(main, corner_radius=12, fg_color="#1A1D24")
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        chart_frame.grid_rowconfigure(1, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chart_frame, text="📈 Equity-Kurve (€)",
                     font=ctk.CTkFont(family="Inter", size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        self.eq_canvas_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        self.eq_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))
        self.eq_canvas_frame.grid_columnconfigure(0, weight=1)
        self.eq_canvas_frame.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(self.eq_canvas_frame,
                     text="Starte einen Backtest um die Equity-Kurve zu sehen.",
                     text_color="#8B949E", font=ctk.CTkFont(family="Inter", size=13)).grid(row=0, column=0)

        # Right panel: stats + trade list
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Stats cards (3x2 grid)
        stats_frame = ctk.CTkFrame(right, corner_radius=12, fg_color="#1A1D24")
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        stats_frame.grid_columnconfigure((0,1), weight=1)

        self.stats = {}
        for i, (lbl, key) in enumerate([
            ("Trades Gesamt", "total"), ("Winrate", "winrate"),
            ("Profit Factor", "pf"),    ("Max Drawdown (€)", "maxdd"),
            ("Netto P&L (€)", "pnl"),   ("Sharpe Ratio", "sharpe")
        ]):
            r, c = divmod(i, 2)
            card = ctk.CTkFrame(stats_frame, fg_color="#1A1D24", corner_radius=10)
            card.grid(row=r, column=c, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=lbl, font=ctk.CTkFont(family="Inter", size=10), text_color="#8B949E").pack(anchor="w", padx=8, pady=(6,0))
            val_lbl = ctk.CTkLabel(card, text="–", font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color="#2979FF")
            val_lbl.pack(anchor="w", padx=8, pady=(0,6))
            self.stats[key] = val_lbl

        # Trade list
        trades_frame = ctk.CTkFrame(right, corner_radius=12, fg_color="#1A1D24")
        trades_frame.grid(row=1, column=0, sticky="nsew")
        trades_frame.grid_rowconfigure(1, weight=1)
        trades_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(trades_frame, text="📋 Trade-Liste",
                     font=ctk.CTkFont(family="Inter", size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=8)
        self.trade_scroll = ctk.CTkScrollableFrame(trades_frame, fg_color="transparent")
        self.trade_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0,6))
        self.trade_scroll.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="tc")

        # Load initial settings from config if available
        self._load_from_config()

    def _load_from_config(self):
        """Pre-fill controls from saved config."""
        try:
            cfg = self.app.app_config
            self.capital_entry.delete(0, "end")
            self.capital_entry.insert(0, str(cfg.bt_start_capital))
            self.rr_slider.set(cfg.bt_rr_ratio)
            self.rr_lbl.configure(text=f"{cfg.bt_rr_ratio:.1f}")
            self.atr_slider.set(cfg.bt_atr_mult)
            self.atr_lbl.configure(text=f"{cfg.bt_atr_mult:.1f}")
            self.spread_entry.delete(0, "end")
            self.spread_entry.insert(0, str(cfg.bt_spread_pips))
        except Exception:
            pass

    def _run_backtest_threaded(self):
        self.run_btn.configure(state="disabled", text="⏳ Läuft…")
        self.export_btn.configure(state="disabled")
        self.status_lbl.configure(text="Lade Daten…", text_color="#E67E22")
        self.progress_bar.start()
        threading.Thread(target=self._run_backtest_bg, daemon=True).start()

    def _run_backtest_bg(self):
        """Core backtesting engine – runs in a background thread."""
        symbol   = self.symbol_combo.get()
        tf_str   = self.tf_combo.get()
        bars     = int(self.bars_combo.get())
        strategy = self.strategy_combo.get()

        # Parse new parameters
        try:
            start_capital = float(self.capital_entry.get())
        except ValueError:
            start_capital = 10000.0
        try:
            risk_pct = float(self.risk_entry.get()) / 100.0
        except ValueError:
            risk_pct = 0.01
        rr_ratio  = self.rr_slider.get()
        atr_mult  = self.atr_slider.get()
        try:
            spread_pips = float(self.spread_entry.get())
        except ValueError:
            spread_pips = 1.0

        # Map timeframe string → MT5 constant
        if "M15" in tf_str:   tf = mt5.TIMEFRAME_M15
        elif "M30" in tf_str: tf = mt5.TIMEFRAME_M30
        elif "H4"  in tf_str: tf = mt5.TIMEFRAME_H4
        elif "D1"  in tf_str: tf = mt5.TIMEFRAME_D1
        else:                 tf = mt5.TIMEFRAME_H1

        try:
            if not mt5.initialize():
                raise RuntimeError("MT5 nicht verbunden")

            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None or len(rates) < 50:
                raise RuntimeError(f"Zu wenig Daten für {symbol}")

            df = pd.DataFrame(rates)

            # ── Signal Generation ──────────────────────────────────
            signals = []   # list of (index, direction) where direction = 1 (buy) / -1 (sell)

            if strategy == "SMC Fair Value Gap":
                for i in range(2, len(df) - 1):
                    c0, c1, c2 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
                    if c0['high'] < c2['low'] and c1['close'] > c1['open']:
                        gap = c2['low'] - c0['high']
                        if gap > (c1['high'] - c1['low']) * 0.1:
                            signals.append((i, 1))
                    if c0['low'] > c2['high'] and c1['close'] < c1['open']:
                        gap = c0['low'] - c2['high']
                        if gap > (c1['high'] - c1['low']) * 0.1:
                            signals.append((i, -1))

            elif strategy == "SMC Order Block":
                for i in range(2, len(df) - 1):
                    c0, c1, c2 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
                    if c0['close'] < c0['open'] and c1['close'] > c1['open'] and c2['close'] > c2['open']:
                        if (c1['close']-c1['open']) > (c0['open']-c0['close']) * 1.5:
                            signals.append((i, 1))
                    if c0['close'] > c0['open'] and c1['close'] < c1['open'] and c2['close'] < c2['open']:
                        if (c1['open']-c1['close']) > (c0['close']-c0['open']) * 1.5:
                            signals.append((i, -1))

            elif strategy == "Bullish Engulfing":
                for i in range(1, len(df) - 1):
                    prev, curr = df.iloc[i-1], df.iloc[i]
                    if prev['close'] < prev['open'] and curr['close'] > curr['open']:
                        if curr['close'] >= prev['open'] and curr['open'] <= prev['close']:
                            signals.append((i, 1))
                    if prev['close'] > prev['open'] and curr['close'] < curr['open']:
                        if curr['close'] <= prev['open'] and curr['open'] >= prev['close']:
                            signals.append((i, -1))

            elif strategy == "EMA 20/50 Crossover":
                df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
                df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
                for i in range(51, len(df) - 1):
                    prev_cross = df['ema20'].iloc[i-1] - df['ema50'].iloc[i-1]
                    curr_cross = df['ema20'].iloc[i]   - df['ema50'].iloc[i]
                    if prev_cross <= 0 < curr_cross:
                        signals.append((i, 1))
                    elif prev_cross >= 0 > curr_cross:
                        signals.append((i, -1))

            elif strategy == "RSI Überkauft/Überverkauft":
                # RSI-based reversal signals
                delta = df['close'].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss.replace(0, 1e-9)
                df['rsi'] = 100 - (100 / (1 + rs))
                for i in range(15, len(df) - 1):
                    rsi_prev = df['rsi'].iloc[i-1]
                    rsi_curr = df['rsi'].iloc[i]
                    # Cross from oversold → buy
                    if rsi_prev < 30 and rsi_curr >= 30:
                        signals.append((i, 1))
                    # Cross from overbought → sell
                    elif rsi_prev > 70 and rsi_curr <= 70:
                        signals.append((i, -1))

            elif strategy == "Bollinger Band Squeeze":
                # Volatility squeeze breakout
                df['bb_mid']  = df['close'].rolling(20).mean()
                bb_std        = df['close'].rolling(20).std()
                df['bb_up']   = df['bb_mid'] + 2 * bb_std
                df['bb_low']  = df['bb_mid'] - 2 * bb_std
                df['bb_width'] = df['bb_up'] - df['bb_low']
                df['bw_avg']  = df['bb_width'].rolling(50).mean()
                for i in range(51, len(df) - 1):
                    bw  = df['bb_width'].iloc[i]
                    bwa = df['bw_avg'].iloc[i]
                    c   = df['close'].iloc[i]
                    mid = df['bb_mid'].iloc[i]
                    # Squeeze detected (low volatility), then candle closes above mid → buy breakout
                    if bw < bwa * 0.7 and c > mid:
                        signals.append((i, 1))
                    elif bw < bwa * 0.7 and c < mid:
                        signals.append((i, -1))

            # ── Trade Simulation (ATR-based SL / dynamic TP from RR) ──
            ATR_PERIOD = 14
            df['atr'] = (df['high'] - df['low']).rolling(ATR_PERIOD).mean()

            # Pip size for the symbol (simplified)
            sym_info = mt5.symbol_info(symbol)
            pip_value_per_lot = 10.0  # approximate €/pip for standard lot, ~1€ for micro
            pip_factor = 0.0001 if sym_info and sym_info.digits >= 4 else 0.01

            trades   = []
            balance  = start_capital
            equity   = [balance]
            last_exit = -1

            for sig_idx, direction in signals:
                if sig_idx <= last_exit:
                    continue   # skip overlapping trades
                if sig_idx + 1 >= len(df):
                    continue

                entry_bar = df.iloc[sig_idx + 1]
                entry     = entry_bar['open']
                atr       = df['atr'].iloc[sig_idx]
                if atr == 0 or math.isnan(atr):
                    continue

                sl_dist_price = atr * atr_mult
                tp_dist_price = sl_dist_price * rr_ratio
                sl = entry - direction * sl_dist_price
                tp = entry + direction * tp_dist_price

                # Risk amount in euros
                risk_amount = balance * risk_pct

                # Scan forward for TP/SL hit
                result_eur = None
                exit_idx   = None
                for j in range(sig_idx + 2, min(sig_idx + 100, len(df))):
                    bar = df.iloc[j]
                    if direction == 1:
                        if bar['low']  <= sl:
                            result_eur = -risk_amount
                            exit_idx   = j; break
                        if bar['high'] >= tp:
                            result_eur = risk_amount * rr_ratio
                            exit_idx   = j; break
                    else:
                        if bar['high'] >= sl:
                            result_eur = -risk_amount
                            exit_idx   = j; break
                        if bar['low']  <= tp:
                            result_eur = risk_amount * rr_ratio
                            exit_idx   = j; break

                if result_eur is None:
                    continue   # trade still open at end of data

                # Deduct spread cost (approximate)
                spread_cost = spread_pips * pip_factor * pip_value_per_lot
                result_eur -= spread_cost

                last_exit = exit_idx
                balance  += result_eur
                equity.append(balance)

                trades.append({
                    "entry_time": str(pd.to_datetime(entry_bar['time'], unit='s'))[:16],
                    "dir":   "BUY" if direction == 1 else "SELL",
                    "entry": round(entry, 5),
                    "result_eur": round(result_eur, 2),
                    "balance": round(balance, 2),
                    "win":   result_eur > 0,
                })

            # ── Calculate Stats ────────────────────────────────────
            if not trades:
                self.app.after(0, lambda: (
                    self.status_lbl.configure(text="Keine Trades gefunden.", text_color="#E67E22"),
                    self.progress_bar.stop(),
                    self.run_btn.configure(state="normal", text="▶ Backtest Starten")
                ))
                return

            total   = len(trades)
            wins    = sum(1 for t in trades if t['win'])
            winrate = wins / total * 100
            gross_p = sum(t['result_eur'] for t in trades if t['result_eur'] > 0)
            gross_l = abs(sum(t['result_eur'] for t in trades if t['result_eur'] < 0))
            pf      = gross_p / gross_l if gross_l > 0 else float('inf')
            pnl     = equity[-1] - start_capital

            # Max drawdown in euros
            peak, maxdd = start_capital, 0.0
            for e in equity:
                if e > peak: peak = e
                dd = peak - e
                if dd > maxdd: maxdd = dd

            # Sharpe (simplified)
            if len(equity) > 2:
                rets  = [equity[i] - equity[i-1] for i in range(1, len(equity))]
                mean_r = sum(rets) / len(rets)
                std_r  = (sum((r - mean_r)**2 for r in rets) / len(rets)) ** 0.5
                sharpe = (mean_r / std_r * (252 ** 0.5)) if std_r > 0 else 0.0
            else:
                sharpe = 0.0

            self._last_trades = trades
            self.app.after(0, lambda: self._bt_show_results(
                trades, equity, total, winrate, pf, maxdd, pnl, sharpe, start_capital))

        except Exception as e:
            err = str(e)
            self.app.after(0, lambda msg=err: (
                self.status_lbl.configure(text=f"Fehler: {msg[:70]}", text_color="#FF1744"),
                self.progress_bar.stop(),
                self.run_btn.configure(state="normal", text="▶ Backtest Starten")
            ))

    def _bt_show_results(self, trades, equity, total, winrate, pf, maxdd, pnl, sharpe, start_capital):
        """Render results on the main thread."""
        self.progress_bar.stop()
        self.run_btn.configure(state="normal", text="▶ Backtest Starten")
        self.export_btn.configure(state="normal")
        self.status_lbl.configure(text=f"✅ Fertig – {total} Trades simuliert", text_color="#00FF66")

        # Update stat cards
        wr_color  = "#00FF66" if winrate >= 50 else "#FF1744"
        pnl_color = "#00FF66" if pnl >= 0    else "#FF1744"
        self.stats["total"].configure(text=str(total))
        self.stats["winrate"].configure(text=f"{winrate:.1f}%", text_color=wr_color)
        self.stats["pf"].configure(text=f"{min(pf,99):.2f}")
        self.stats["maxdd"].configure(text=f"-{maxdd:.2f}€", text_color="#FF1744")
        self.stats["pnl"].configure(text=f"{pnl:+.2f}€", text_color=pnl_color)
        self.stats["sharpe"].configure(text=f"{sharpe:.2f}")

        # ── Equity Curve (in €) ──────────────────────────────────
        for w in self.eq_canvas_frame.winfo_children():
            w.destroy()

        fig = Figure(figsize=(6, 3), facecolor="#1a1a1a")
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#1a1a1a")
        ax.tick_params(colors="gray")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333")

        color = "#00FF66" if equity[-1] >= start_capital else "#FF1744"
        ax.plot(equity, color=color, linewidth=1.5)
        ax.fill_between(range(len(equity)), equity, alpha=0.15, color=color)
        ax.axhline(start_capital, color="gray", linewidth=0.5, linestyle="--")
        ax.set_xlabel("Trades", color="gray", fontsize=9)
        ax.set_ylabel("Kapital (€)", color="gray", fontsize=9)
        ax.set_title(f"{self.symbol_combo.get()} – {self.strategy_combo.get()}", color="white", fontsize=10)
        fig.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=self.eq_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # ── Trade List ───────────────────────────────────────────
        for w in self.trade_scroll.winfo_children():
            w.destroy()

        # Header
        hdr = ctk.CTkFrame(self.trade_scroll, fg_color="#1A1D24", corner_radius=6)
        hdr.pack(fill="x", pady=(0, 4))
        hdr.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="tc")
        for ci, h in enumerate(["Zeit", "Dir", "Entry", "Ergebnis (€)", "Kontostand"]):
            ctk.CTkLabel(hdr, text=h, font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                         text_color="#8B949E").grid(row=0, column=ci, padx=6, pady=4, sticky="w")

        for t in trades[-50:]:  # show last 50
            row_bg = "#1A1D24" if t['win'] else "#1A1D24"
            rc = ctk.CTkFrame(self.trade_scroll, fg_color=row_bg, corner_radius=6)
            rc.pack(fill="x", pady=2)
            rc.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="tc")
            pip_color = "#00FF66" if t['win'] else "#FF1744"
            dir_color = "#2979FF" if t['dir'] == "BUY" else "#9C27B0"
            ctk.CTkLabel(rc, text=t['entry_time'], font=ctk.CTkFont(family="Inter", size=9), text_color="#8B949E").grid(row=0, column=0, padx=6, pady=3, sticky="w")
            ctk.CTkLabel(rc, text=t['dir'],  font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color=dir_color).grid(row=0, column=1, padx=6, sticky="w")
            ctk.CTkLabel(rc, text=str(t['entry']), font=ctk.CTkFont(family="Inter", size=9), text_color="#8B949E").grid(row=0, column=2, padx=6, sticky="w")
            ctk.CTkLabel(rc, text=f"{t['result_eur']:+.2f}€", font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color=pip_color).grid(row=0, column=3, padx=6, sticky="w")
            ctk.CTkLabel(rc, text=f"{t['balance']:.2f}€", font=ctk.CTkFont(family="Inter", size=9), text_color="#8B949E").grid(row=0, column=4, padx=6, sticky="w")

    def _export_csv(self):
        """Export last backtest trades to CSV."""
        if not self._last_trades:
            return
        try:
            export_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage", "backtest_exports"
            )
            os.makedirs(export_dir, exist_ok=True)
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            sym = self.symbol_combo.get()
            strat = self.strategy_combo.get().replace(" ", "_").replace("/", "-")
            path = os.path.join(export_dir, f"{sym}_{strat}_{ts}.csv")
            pd.DataFrame(self._last_trades).to_csv(path, index=False, encoding="utf-8-sig")
            self.status_lbl.configure(text=f"✅ CSV gespeichert: {os.path.basename(path)}", text_color="#00FF66")
            self.app.write_terminal(f">> [BACKTEST] CSV Export: {path}\n")
        except Exception as e:
            self.status_lbl.configure(text=f"❌ Export Fehler: {e}", text_color="#FF1744")
