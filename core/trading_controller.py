import time
import re
import json
import os
import sys
import concurrent.futures
import httpx
import MetaTrader5 as mt5
import numpy as np
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from core.market_analyzer import MarketAnalyzer
from core.ai_analyzer import AIAnalyzer

class TradingController:
    def __init__(self, app):
        """
        app: Reference to the ModernFinGPTGUI instance
        """
        self.app = app
        self.is_running = False
        self._trading_thread = None
        self._resolver_thread = None
        
        # Core Components (Safety fallback for GUI vs CLI app instances)
        broker = getattr(app, 'broker', app)
        logger = getattr(app, 'logger', None)
        
        self.market_analyzer = MarketAnalyzer(broker=broker, logger=logger)
        self.ai_analyzer = AIAnalyzer(logger=logger)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._resolver_thread = threading.Thread(target=self._resolve_closed_trades_loop, daemon=True)
        self._resolver_thread.start()
        
        self._trading_thread = threading.Thread(target=self._auto_trading_loop, daemon=True)
        self._trading_thread.start()

    def stop(self):
        self.is_running = False

    def _resolve_closed_trades_loop(self):
        """Background thread to check MT5 for closed trades and update RL Experience DB."""
        while self.is_running and hasattr(self.app, 'is_live_running') and self.app.is_live_running:
            try:
                if not hasattr(self.app, 'experience_db'):
                    time.sleep(10)
                    continue
                    
                unresolved_tickets = self.app.experience_db.get_unresolved_tickets()
                if unresolved_tickets:
                    time_to = datetime.now() + timedelta(days=1)
                    time_from = datetime.now() - timedelta(days=7)
                    
                    history_deals = mt5.history_deals_get(time_from, time_to)
                    if history_deals:
                        deals_by_position = {d.position_id: d for d in history_deals if d.entry == mt5.DEAL_ENTRY_OUT}
                        
                        for ticket in unresolved_tickets:
                            if ticket in deals_by_position:
                                deal = deals_by_position[ticket]
                                profit = deal.profit
                                
                                is_sl = False
                                if deal.comment and "sl" in deal.comment.lower():
                                    is_sl = True
                                elif profit < 0:
                                    is_sl = True
                                    
                                if profit > 0:
                                    reward = profit * 1.5
                                else:
                                    reward = profit * 2.0
                                    if is_sl:
                                        reward -= 50.0
                                        
                                self.app.experience_db.resolve_trade(ticket, profit, is_sl, reward)
                                self.app.write_terminal(f">> [RL] Trade {ticket} bewertet. Profit: {profit:.2f}€, Reward: {reward:.2f}\\n")
            except Exception as e:
                pass
            
            time.sleep(30)

    def _auto_trading_loop(self):
        """
        Real auto-trading engine.
        Reads GUI settings and executes trades via MT5/AI accordingly.
        """
        def _to_float(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return default

        STYLE_MAP = {
            "Scalping":           {"tf": mt5.TIMEFRAME_M5,  "sl": 10, "tp": 15,  "pause": 30},
            "Day Trading":        {"tf": mt5.TIMEFRAME_M15, "sl": 30, "tp": 45,  "pause": 120},
            "Swing Trading":      {"tf": mt5.TIMEFRAME_H1,  "sl": 60, "tp": 90,  "pause": 300},
            "Position Trading":   {"tf": mt5.TIMEFRAME_H4,  "sl":100, "tp":150,  "pause": 300},
            "Price Action":       {"tf": mt5.TIMEFRAME_M15, "sl": 25, "tp": 40,  "pause": 120},
            "Breakout-Trading":   {"tf": mt5.TIMEFRAME_H1,  "sl": 40, "tp": 80,  "pause": 240},
            "Mean Reversion":     {"tf": mt5.TIMEFRAME_M15, "sl": 20, "tp": 30,  "pause": 120},
            "AI-Fulldrive Mode 🤖": {"tf": mt5.TIMEFRAME_M15, "sl": 30, "tp": 50, "pause": 60},
        }

        DAY_ATTRS = ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri"]

        self.app.write_terminal(">> [AUTO] Engine aktiv. Warte auf erste Analyse...\\n")

        # Cache für AI-Fulldrive Engine (einmal pro Session)
        _fulldrive_engine = None

        while self.is_running and self.app.is_live_running:
            try:
                cfg = getattr(self.app, 'app_config', None)
                if not cfg:
                    time.sleep(5)
                    continue

                if not cfg.auto_trading:
                    time.sleep(5)
                    continue

                style       = cfg.trading_style
                strategy    = cfg.signal_strategy
                max_risk_pct= _to_float(cfg.max_risk, 1.0)
                max_daily   = _to_float(cfg.max_daily_loss, 50.0)
                max_pos     = int(_to_float(cfg.max_positions, 3))
                max_spread  = cfg.max_spread
                max_slip    = cfg.max_slippage
                spread_chk  = cfg.spread_check
                time_filt   = cfg.time_filter
                news_filt   = cfg.news_filter
                tf_from     = cfg.trade_time_from
                tf_to       = cfg.trade_time_to

                style_cfg   = STYLE_MAP.get(style, STYLE_MAP["Day Trading"])
                timeframe   = style_cfg["tf"]
                sl_pips     = style_cfg["sl"]
                tp_pips     = style_cfg["tp"]
                pause_secs  = style_cfg["pause"]

                today_idx   = datetime.now().weekday()
                if today_idx < 5:
                    day_is_active = getattr(cfg, DAY_ATTRS[today_idx], True)
                    if not day_is_active:
                        self.app.write_terminal(f">> [AUTO] Handelstag {['Mo','Di','Mi','Do','Fr'][today_idx]} deaktiviert.\\n")
                        time.sleep(pause_secs)
                        continue
                else:
                    self.app.write_terminal(">> [AUTO] Wochenende – kein Trading.\\n")
                    time.sleep(300)
                    continue

                if time_filt:
                    now_utc = datetime.utcnow()
                    now_str = now_utc.strftime("%H:%M")
                    if not (tf_from <= now_str <= tf_to):
                        self.app.write_terminal(f">> [AUTO] Außerhalb Trading-Fenster ({tf_from}–{tf_to} UTC). Jetzt: {now_str}\\n")
                        time.sleep(60)
                        continue

                acc = mt5.account_info()
                if acc is None:
                    time.sleep(10)
                    continue
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                deals_today = mt5.history_deals_get(today_start, datetime.now())
                daily_pnl   = sum(d.profit for d in deals_today) if deals_today else 0.0
                daily_pnl  += acc.profit
                if daily_pnl <= -abs(max_daily):
                    self.app.write_terminal(f">> [AUTO] Tages-Verlustlimit erreicht ({daily_pnl:.2f}€ / -{max_daily:.2f}€). Pause bis Mitternacht.\\n")
                    time.sleep(3600)
                    continue

                # ── AI-FULLDRIVE MODE BRANCH ─────────────────────────────────────
                if style == "AI-Fulldrive Mode 🤖":
                    # Lazy-Initialisierung der Engine
                    if _fulldrive_engine is None:
                        try:
                            from trading.ai_fulldrive_engine import AIFulldriveEngine
                            fd_conf = float(getattr(cfg, 'fulldrive_min_confidence', 70)) / 100.0
                            fd_dd   = float(getattr(cfg, 'fulldrive_max_drawdown',   15))
                            fd_sr   = float(getattr(cfg, 'fulldrive_sharpe_target',  1.5))
                            _fulldrive_engine = AIFulldriveEngine(
                                self.app,
                                min_confidence   = fd_conf,
                                max_drawdown_pct = fd_dd,
                                sharpe_target    = fd_sr,
                            )
                            self.app.fulldrive_engine = _fulldrive_engine
                        except Exception as _fe:
                            self.app.write_terminal(f">> [FULLDRIVE] Init-Fehler: {_fe}\\n")
                            time.sleep(pause_secs)
                            continue

                    fd_syms = [sym for _, sym in getattr(self.app, 'dashboard_symbols', [])]
                    if not fd_syms:
                        fd_syms = ["EURUSD"]

                    # 1. Parallele KI-Auswertung für AI-Fulldrive
                    def fetch_fd_signal(sym):
                        sym_positions = mt5.positions_get(symbol=sym)
                        if sym_positions and len(sym_positions) > 0:
                            return sym, None
                        return sym, _fulldrive_engine.get_signal(sym, timeframe)
                        
                    fd_signals = {}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(fd_syms))) as executor:
                        futures = [executor.submit(fetch_fd_signal, s) for s in fd_syms]
                        for f in concurrent.futures.as_completed(futures):
                            try:
                                sym, sig = f.result()
                                if sig: fd_signals[sym] = sig
                            except Exception as e:
                                self.app.write_terminal(f">> [FULLDRIVE] Signal-Fehler: {e}\\n")

                    # 2. Sequentielle Order-Ausführung
                    for symbol in fd_syms:
                        if not self.is_running or not self.app.is_live_running:
                            break

                        open_pos = mt5.positions_total()
                        if open_pos >= max_pos:
                            break

                        sig = fd_signals.get(symbol)
                        if not sig:
                            continue
                        action    = sig.get('action', 'HOLD')
                        lot_size  = sig.get('lot_size', 0.01)
                        sl_pips   = sig.get('sl_pips', sl_pips)
                        tp_pips   = sig.get('tp_pips', tp_pips)
                        conf      = sig.get('confidence', 0.0)
                        reason    = sig.get('reason', '')
                        kpis      = sig.get('kpis', {})

                        self.app.write_terminal(
                            f">> [FULLDRIVE] {symbol} | Signal: {action} "
                            f"| Konfidenz: {conf:.0%} | {reason}\\n"
                            f"   >> Sharpe: {kpis.get('sharpe',0):.2f} | "
                            f"MaxDD: {kpis.get('max_drawdown',0):.1f}% | "
                            f"WinRate: {kpis.get('win_rate',0):.1f}%\\n"
                        )

                        if action not in ('BUY', 'SELL'):
                            continue

                        tick = mt5.symbol_info_tick(symbol)
                        info = mt5.symbol_info(symbol)
                        if tick is None or info is None:
                            continue

                        point    = info.point
                        pip_size = point * 10 if info.digits in (3, 5) else point
                        spread_pts  = tick.ask - tick.bid
                        spread_pips = spread_pts / pip_size if pip_size > 0 else 99
                        if spread_chk and spread_pips > max_spread:
                            continue

                        pip_dist_sl = sl_pips * pip_size
                        pip_dist_tp = tp_pips * pip_size
                        if action == 'BUY':
                            entry       = tick.ask
                            stop_loss   = round(entry - pip_dist_sl, info.digits)
                            take_profit = round(entry + pip_dist_tp, info.digits)
                            order_type  = mt5.ORDER_TYPE_BUY
                        else:
                            entry       = tick.bid
                            stop_loss   = round(entry + pip_dist_sl, info.digits)
                            take_profit = round(entry - pip_dist_tp, info.digits)
                            order_type  = mt5.ORDER_TYPE_SELL

                        deviation = max(5, max_slip * 10)
                        request = {
                            "action":       mt5.TRADE_ACTION_DEAL,
                            "symbol":       symbol,
                            "volume":       float(lot_size),
                            "type":         order_type,
                            "price":        entry,
                            "sl":           stop_loss,
                            "tp":           take_profit,
                            "deviation":    deviation,
                            "magic":        234002,
                            "comment":      "FinGPT Fulldrive",
                            "type_time":    mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }

                        check = mt5.order_check(request)
                        if check is None or check.retcode != 0:
                            err = f"{check.comment} ({check.retcode})" if check else str(mt5.last_error())
                            self.app.write_terminal(f">> [FULLDRIVE] {symbol} Pre-Check fehlg.: {err}\\n")
                            continue

                        result = mt5.order_send(request)
                        if result.retcode == mt5.TRADE_RETCODE_DONE:
                            self.app.write_terminal(
                                f">> [FULLDRIVE] ✅ {action} {lot_size} {symbol} @ {result.price:.5f} "
                                f"| SL:{stop_loss:.5f} TP:{take_profit:.5f} | Ticket:{result.order}\\n"
                            )
                        else:
                            self.app.write_terminal(
                                f">> [FULLDRIVE] ❌ {symbol} {action} fehlg.: {result.comment} ({result.retcode})\\n"
                            )

                    time.sleep(pause_secs)
                    continue   # Überspringt den Standard-LLM-Loop unten
                # ── ENDE AI-FULLDRIVE BRANCH ─────────────────────────────────

                symbols = [sym for _, sym in getattr(self.app, 'dashboard_symbols', [])]
                if not symbols:
                    symbols = ["EURUSD"]

                # 1. Parallele Analyse und LLM Anfragen
                
                def eval_standard_sym(symbol):
                    sym_positions = mt5.positions_get(symbol=symbol)
                    if sym_positions and len(sym_positions) > 0:
                        return symbol, None
                        
                    tick = mt5.symbol_info_tick(symbol)
                    info = mt5.symbol_info(symbol)
                    if not tick or not info:
                        return symbol, None

                    point     = info.point
                    pip_size  = point * 10 if info.digits in (3, 5) else point
                    spread_pts = tick.ask - tick.bid
                    spread_pips = spread_pts / pip_size if pip_size > 0 else 99
                    
                    if spread_chk and spread_pips > max_spread:
                        return symbol, {"skip_reason": f"Spread {spread_pips:.1f} > {max_spread}"}

                    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 50)
                    if rates is None or len(rates) < 20:
                        return symbol, None
                    closes  = np.array([r['close'] for r in rates], dtype=float)
                    # Indicators from MarketAnalyzer
                    rsi_val = self.market_analyzer.calculate_rsi(symbol, timeframe)
                    macd_data = self.market_analyzer.calculate_macd(symbol, timeframe)
                    macd_sig, _ = self.market_analyzer.get_macd_signal(macd_data)
                    price   = closes[-1]

                    htf_map = {
                        mt5.TIMEFRAME_M5:  mt5.TIMEFRAME_M15,
                        mt5.TIMEFRAME_M15: mt5.TIMEFRAME_H1,
                        mt5.TIMEFRAME_H1:  mt5.TIMEFRAME_H4,
                        mt5.TIMEFRAME_H4:  mt5.TIMEFRAME_D1,
                    }
                    htf_rates = mt5.copy_rates_from_pos(symbol, htf_map.get(timeframe, mt5.TIMEFRAME_H1), 0, 10)
                    if htf_rates is not None and len(htf_rates) >= 5:
                        htf_trend = "BULLISH" if htf_rates[-1]['close'] > htf_rates[0]['close'] else "BEARISH"
                    else:
                        htf_trend = "NEUTRAL"

                    if hasattr(self.app, 'indicator_integration') and self.app.indicator_integration:
                        try:
                            signal_data = self.app.indicator_integration.create_trading_signal(symbol, timeframe=timeframe, use_advanced=True)
                            indicators_str = ""
                            for ind, data in signal_data.get('supporting_signals', []):
                                indicators_str += f"- {data}\\n"
                            for ind, data in signal_data.get('conflicting_signals', []):
                                indicators_str += f"- {data} (Neutral/Widerspruch)\\n"
                            
                            signal_hint = (
                                f"KOMPLETTES INDIKATOREN-BILD FÜR {symbol}:\\n"
                                f"{indicators_str}"
                                f"Zusammenfassung: {signal_data.get('buy_ratio', 0)*100:.0f}% Buy, {signal_data.get('sell_ratio', 0)*100:.0f}% Sell.\\n"
                                f"Übergeordneter Trend: {htf_trend}. Spread: {spread_pips:.1f} Pips."
                            )
                        except Exception as e:
                            signal_data = None
                            signal_hint = f"RSI={rsi_val}, MACD={macd_sig}, Trend={htf_trend}. (Advanced Ind. Error: {e})"
                    else:
                        signal_data = None
                        if "RSI" in strategy:
                            signal_hint = f"RSI={rsi_val}. RSI<30=BUY, RSI>70=SELL."
                        elif "MACD" in strategy:
                            signal_hint = f"MACD-Signal={macd_sig}."
                        else:
                            signal_hint = f"RSI={rsi_val}, MACD={macd_sig}, Übergeordneter Trend={htf_trend}. Spread={spread_pips:.1f}. Preis={price:.5f}."

                    style_instruction = {
                        "Scalping":         "Kurze schnelle Bewegungen, sehr enge SL/TP.",
                        "Day Trading":      "Intraday-Bewegung, klare Trendrichtung bevorzugen.",
                        "Swing Trading":    "Mehrstündige Bewegungen, nur starke Setups.",
                        "Position Trading": "Strategische Trendfolge, viel Geduld.",
                        "Price Action":     "Fokus auf nackte Charts, Widerstände und Kerzenmuster.",
                        "Breakout-Trading": "Handel von Ausbrüchen aus Konsolidierungszonen mit Momentum.",
                        "Mean Reversion":   "Antizyklisches Handeln bei Übertreibungen zurück zum Mittelwert.",
                    }.get(style, "")

                    sys_prompt = "Du bist FinGPT, ein professioneller Forex Bot. Antworte immer auf Deutsch."
                    prompt = (
                        f"Analysiere: {symbol}. "
                        f"Handelsstil: {style}. {style_instruction} "
                        f"Aktuelle Marktdaten: {signal_hint} "
                        f"Gib deine Empfehlung in folgendem Format aus: "
                        f"SIGNAL: [BUY/SELL/WARTEN] | BEGRÜNDUNG: [1-2 Sätze warum]"
                    )

                    ai_signal = "WARTEN"
                    ai_reasoning = ""
                    try:
                        raw = self.app._call_llm_api(system_prompt=sys_prompt, user_prompt=prompt, max_tokens=150).strip()
                        ai_reasoning = raw
                        raw_upper = raw.upper()
                        if re.search(r'\bBUY\b|\bKAUF\b|\bLONG\b', raw_upper):
                            ai_signal = "BUY"
                        elif re.search(r'\bSELL\b|\bVERKAUF\b|\bSHORT\b', raw_upper):
                            ai_signal = "SELL"
                    except Exception as e:
                        return symbol, {"skip_reason": f"KI API Fehler: {e}"}
                        
                    return symbol, {
                        "action": ai_signal,
                        "reasoning": ai_reasoning,
                        "rsi": rsi_val,
                        "macd": macd_sig,
                        "trend": htf_trend,
                        "spread": spread_pips,
                        "signal_data": signal_data,
                        "tick": tick,
                        "info": info,
                        "pip_size": pip_size
                    }

                std_signals = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(symbols))) as executor:
                    futures = [executor.submit(eval_standard_sym, s) for s in symbols]
                    for f in concurrent.futures.as_completed(futures):
                        try:
                            sym, result = f.result()
                            if result: std_signals[sym] = result
                        except Exception as e:
                            self.app.write_terminal(f">> [AUTO] Fehler bei Symbol-Auswertung: {e}\\n")

                # 2. Sequentielle Order-Ausführung
                for symbol in symbols:
                    if not self.is_running or not self.app.is_live_running:
                        break

                    open_pos = mt5.positions_total()
                    if open_pos >= max_pos:
                        self.app.write_terminal(f">> [AUTO] Max. Positionen ({open_pos}/{max_pos}) erreicht. Stoppe Setups.\\n")
                        break

                    res = std_signals.get(symbol)
                    if not res:
                        continue
                        
                    if "skip_reason" in res:
                        self.app.write_terminal(f">> [AUTO] {symbol}: {res['skip_reason']} Übersprungen.\\n")
                        continue
                        
                    ai_signal = res["action"]
                    
                    tick = res.get("tick")
                    info = res.get("info")
                    pip_size = res.get("pip_size")
                    ai_reasoning = res.get("reasoning", "")
                    rsi_val = res.get("rsi")
                    macd_sig = res.get("macd")
                    htf_trend = res.get("trend")
                    spread_pips = res.get("spread")
                    
                    if res["signal_data"]:
                        buy_pct = res["signal_data"].get('buy_ratio', 0) * 100
                        sell_pct = res["signal_data"].get('sell_ratio', 0) * 100
                        self.app.write_terminal(
                            f">> [AUTO] {symbol} | Konsens: {buy_pct:.0f}% Buy / {sell_pct:.0f}% Sell\\n"
                            f"   >> RSI:{res['rsi']} | MACD:{res['macd']} | Trend:{res['trend']} | Spread:{res['spread']:.1f}p\\n"
                            f"   >> KI-SIGNAL: {ai_signal}\\n"
                        )
                    else:
                        self.app.write_terminal(f">> [AUTO] {symbol} | RSI:{res['rsi']} | MACD:{res['macd']} | Trend:{res['trend']} | Spread:{res['spread']:.1f}p | Signal: {ai_signal}\\n")

                    if ai_signal == "WARTEN":
                        continue

                    try:
                        from trading.rl_trading_agent import RLTradingManager
                        if not hasattr(self.app, 'rl_manager'):
                            self.app.rl_manager = RLTradingManager(self.app)
                        
                        rl_rec = self.app.rl_manager.get_rl_recommendation(symbol)
                        if rl_rec and rl_rec['confidence'] > 50:
                            rl_signal = rl_rec['recommendation']
                            
                            if rl_signal == "HOLD" and rl_rec['confidence'] > 70:
                                self.app.write_terminal(f">> [RL ADAPTIV] Veto eingelegt! Hohe SL-Wahrscheinlichkeit. Signal geblockt.\\n")
                                ai_signal = "WARTEN"
                                
                            elif rl_signal != "HOLD" and rl_signal != ai_signal and rl_rec['confidence'] > 80:
                                self.app.write_terminal(f">> [RL ADAPTIV] Signal korrigiert von {ai_signal} auf {rl_signal} (Konfidenz: {rl_rec['confidence']:.1f}%)\\n")
                                ai_signal = rl_signal
                                
                    except Exception as e:
                        self.app.write_terminal(f">> [RL ADAPTIV] Fehler bei Strategie-Evaluation: {e}\\n")

                    if ai_signal == "WARTEN":
                        continue

                    sym_positions = mt5.positions_get(symbol=symbol)
                    if sym_positions and len(sym_positions) > 0:
                        continue

                    pip_dist_sl = sl_pips * pip_size
                    pip_dist_tp = tp_pips * pip_size
                    if ai_signal == "BUY":
                        entry = tick.ask
                        stop_loss   = round(entry - pip_dist_sl, info.digits)
                        take_profit = round(entry + pip_dist_tp, info.digits)
                    else:
                        entry = tick.bid
                        stop_loss   = round(entry + pip_dist_sl, info.digits)
                        take_profit = round(entry - pip_dist_tp, info.digits)

                    try:
                        account_balance = acc.balance
                        free_margin     = acc.margin_free
                        risk_amount     = account_balance * (max_risk_pct / 100.0)
                        tick_value      = info.trade_tick_value or 1.0
                        pip_val         = (pip_size / info.trade_tick_size) * tick_value if info.trade_tick_size > 0 else 1.0
                        
                        lot_raw         = risk_amount / (sl_pips * pip_val) if sl_pips > 0 and pip_val > 0 else 0.01
                        lot_step        = info.volume_step or 0.01
                        lot_min         = info.volume_min or 0.01
                        lot_max         = info.volume_max or 1.0
                        
                        lot_size        = round(round(lot_raw / lot_step) * lot_step, 2)
                        lot_size        = max(lot_min, min(lot_size, lot_max))

                        order_type_calc = mt5.ORDER_TYPE_BUY if ai_signal == "BUY" else mt5.ORDER_TYPE_SELL
                        req_margin = mt5.order_calc_margin(order_type_calc, symbol, lot_size, entry)
                        
                        if req_margin is not None and req_margin > free_margin:
                            max_possible_lot = (free_margin / req_margin) * lot_size
                            lot_size = round(round(max_possible_lot / lot_step) * lot_step, 2)
                            
                            if lot_size < lot_min:
                                self.app.write_terminal(f">> [AUTO] {symbol}: Nicht genug Margin für Minimal-Lot ({lot_min}).\\n")
                                continue
                                
                    except Exception:
                        lot_size = info.volume_min or 0.01

                    deviation = max(5, max_slip * 10)

                    order_type = mt5.ORDER_TYPE_BUY if ai_signal == "BUY" else mt5.ORDER_TYPE_SELL
                    request = {
                        "action":       mt5.TRADE_ACTION_DEAL,
                        "symbol":       symbol,
                        "volume":       float(lot_size),
                        "type":         order_type,
                        "price":        entry,
                        "sl":           stop_loss,
                        "tp":           take_profit,
                        "deviation":    deviation,
                        "magic":        234001,
                        "comment":      f"FinGPT {style}",
                        "type_time":    mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }

                    check = mt5.order_check(request)
                    if check is None or check.retcode != 0:
                        err = f"{check.comment} (code {check.retcode})" if check else str(mt5.last_error())
                        self.app.write_terminal(f">> [AUTO] {symbol} Pre-Check fehlgeschlagen: {err}\\n")
                        continue

                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        self.app.write_terminal(
                            f">> [TRADE] ✅ {ai_signal} {lot_size} {symbol} @ {result.price:.5f} "
                            f"| SL:{stop_loss:.5f} TP:{take_profit:.5f} | Ticket:{result.order}\\n"
                        )
                        try:
                            if getattr(sys, 'frozen', False):
                                _base = os.path.dirname(sys.executable)
                            else:
                                _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                
                            journal_dir = os.path.join(_base, "storage", "trade_journal")
                            os.makedirs(journal_dir, exist_ok=True)
                            _now = datetime.now()
                            ticket_id = result.order or int(_now.timestamp())
                            entry_data = {
                                "ticket":          ticket_id,
                                "symbol":          symbol,
                                "action":          ai_signal,
                                "result":          "Ausgeführt",
                                "open_time":       _now.isoformat(),
                                "close_time":      None,
                                "open_price":      result.price,
                                "close_price":     None,
                                "lot_size":        float(lot_size),
                                "profit":          0.0,
                                "stop_loss":       stop_loss,
                                "take_profit":     take_profit,
                                "ai_reasoning":    ai_reasoning,
                                "ai_confidence":   "",
                                "indicators_used": [f"RSI={rsi_val}", f"MACD={macd_sig}", f"Trend={htf_trend}"],
                                "tags":            [style, strategy],
                            }
                            fname = f"{ticket_id}_{symbol}_{_now.strftime('%Y%m')}.json"
                            fpath = os.path.join(journal_dir, fname)
                            with open(fpath, 'w', encoding='utf-8') as fh:
                                json.dump(entry_data, fh, indent=2, ensure_ascii=False)
                            self.app.write_terminal(f">> [JOURNAL] Trade {ticket_id} gespeichert.\\n")
                            
                            if hasattr(self.app, 'experience_db'):
                                try:
                                    state_features = [
                                        rsi_val if rsi_val is not None else 50.0, 
                                        1.0 if macd_sig == "BUY" else (-1.0 if macd_sig == "SELL" else 0.0),
                                        1.0 if htf_trend == "BULLISH" else (-1.0 if htf_trend == "BEARISH" else 0.0),
                                        spread_pips,
                                        result.price
                                    ]
                                    action_int = 1 if ai_signal == "BUY" else (2 if ai_signal == "SELL" else 0)
                                    self.app.experience_db.insert_pending_trade(
                                        ticket_id, symbol, _now.isoformat(), state_features, action_int
                                    )
                                    self.app.write_terminal(f">> [RL] Status {ticket_id} an Database übergeben.\\n")
                                except Exception as _e:
                                    self.app.write_terminal(f">> [RL] DB Fehler: {_e}\\n")
                                    
                        except Exception as _je:
                            self.app.write_terminal(f">> [JOURNAL] Speicherfehler: {_je}\\n")
                    else:
                        self.app.write_terminal(
                            f">> [TRADE] ❌ {symbol} {ai_signal} fehlgeschlagen: {result.comment} ({result.retcode})\\n"
                        )

            except Exception as e:
                self.app.write_terminal(f">> [AUTO] Loop-Fehler: {e}\\n")

            time.sleep(pause_secs)

        self.app.write_terminal(">> [AUTO] Auto-Trading Engine gestoppt.\\n")
