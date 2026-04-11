import math
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import quantstats as qs
import os
from datetime import datetime

class BacktestEngine:
    """
    Zentrale Backtest-Engine für FinGPT.
    Simuliert Trade-Eintritte (Entry, SL, TP) und generiert QuantStats Reports.
    """
    
    def __init__(self):
        self.last_trades = []
        self.last_equity = []
        self.last_report_path = None
        
    def run(self, symbol: str, timeframe: int, bars: int, strategy: str, 
            start_capital: float, risk_pct: float, rr_ratio: float, 
            atr_mult: float, spread_pips: float):
        
        if not mt5.initialize():
            raise RuntimeError("MT5 nicht verbunden")
            
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) < 50:
            raise RuntimeError(f"Zu wenig Daten für {symbol}")
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
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
            delta = df['close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-9)
            df['rsi'] = 100 - (100 / (1 + rs))
            for i in range(15, len(df) - 1):
                rsi_prev = df['rsi'].iloc[i-1]
                rsi_curr = df['rsi'].iloc[i]
                if rsi_prev < 30 and rsi_curr >= 30:
                    signals.append((i, 1))
                elif rsi_prev > 70 and rsi_curr <= 70:
                    signals.append((i, -1))
                    
        elif strategy == "Bollinger Band Squeeze":
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
                if bw < bwa * 0.7 and c > mid:
                    signals.append((i, 1))
                elif bw < bwa * 0.7 and c < mid:
                    signals.append((i, -1))

        # ── Trade Simulation (ATR-based SL / dynamic TP from RR) ──
        ATR_PERIOD = 14
        df['atr'] = (df['high'] - df['low']).rolling(ATR_PERIOD).mean()
        
        sym_info = mt5.symbol_info(symbol)
        pip_value_per_lot = 10.0
        pip_factor = 0.0001 if sym_info and sym_info.digits >= 4 else 0.01
        
        trades   = []
        balance  = start_capital
        equity   = [balance]
        equity_dates = [df['time'].iloc[0]] # Track dates for QuantStats
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
            
            risk_amount = balance * risk_pct
            
            result_eur = None
            exit_idx   = None
            exit_time  = None
            
            for j in range(sig_idx + 2, min(sig_idx + 100, len(df))):
                bar = df.iloc[j]
                if direction == 1:
                    if bar['low']  <= sl:
                        result_eur = -risk_amount
                        exit_idx = j
                        exit_time = bar['time']
                        break
                    if bar['high'] >= tp:
                        result_eur = risk_amount * rr_ratio
                        exit_idx = j
                        exit_time = bar['time']
                        break
                else:
                    if bar['high'] >= sl:
                        result_eur = -risk_amount
                        exit_idx = j
                        exit_time = bar['time']
                        break
                    if bar['low']  <= tp:
                        result_eur = risk_amount * rr_ratio
                        exit_idx = j
                        exit_time = bar['time']
                        break
                        
            if result_eur is None:
                continue   # trade still open
                
            spread_cost = spread_pips * pip_factor * pip_value_per_lot
            result_eur -= spread_cost
            
            last_exit = exit_idx
            balance  += result_eur
            equity.append(balance)
            equity_dates.append(exit_time)
            
            trades.append({
                "entry_time": str(entry_bar['time'])[:16],
                "exit_time": str(exit_time)[:16],
                "dir":   "BUY" if direction == 1 else "SELL",
                "entry": round(entry, 5),
                "result_eur": round(result_eur, 2),
                "balance": round(balance, 2),
                "win":   result_eur > 0,
            })
            
        self.last_trades = trades
        self.last_equity = equity
        
        if not trades:
            return None
            
        # Metrics Calculation (GUI format)
        total = len(trades)
        wins = sum(1 for t in trades if t['win'])
        winrate = wins / total * 100
        gross_p = sum(t['result_eur'] for t in trades if t['result_eur'] > 0)
        gross_l = abs(sum(t['result_eur'] for t in trades if t['result_eur'] < 0))
        pf = gross_p / gross_l if gross_l > 0 else float('inf')
        pnl = equity[-1] - start_capital
        
        peak, maxdd = start_capital, 0.0
        for e in equity:
            if e > peak: peak = e
            dd = peak - e
            if dd > maxdd: maxdd = dd
            
        if len(equity) > 2:
            rets  = [equity[i] - equity[i-1] for i in range(1, len(equity))]
            mean_r = sum(rets) / len(rets)
            std_r  = (sum((r - mean_r)**2 for r in rets) / len(rets)) ** 0.5
            sharpe = (mean_r / std_r * (252 ** 0.5)) if std_r > 0 else 0.0
        else:
            sharpe = 0.0
            
        # ── QuantStats Report Generation ───────────────────────
        try:
            # Create a pandas Series for returns indexed by date
            eq_series = pd.Series(equity, index=equity_dates)
            
            # Aggregate to daily data (QuantStats prefers daily returns)
            # Take the last equity value of each day
            daily_eq = eq_series.resample('D').last().dropna()
            
            # Calculate daily returns
            returns = daily_eq.pct_change().dropna()
            
            if len(returns) > 2:
                export_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "storage", "backtest_exports"
                )
                os.makedirs(export_dir, exist_ok=True)
                
                ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(export_dir, f"qs_report_{symbol}_{ts_str}.html")
                
                title = f"FinGPT Backtest: {symbol} - {strategy}"
                qs.reports.html(returns, output=report_path, title=title, download_filename=report_path)
                self.last_report_path = report_path
            else:
                self.last_report_path = None
        except Exception as e:
            print(f"QuantStats Report Error: {e}")
            self.last_report_path = None

        return {
            "total": total,
            "winrate": winrate,
            "pf": pf,
            "maxdd": maxdd,
            "pnl": pnl,
            "sharpe": sharpe,
            "equity": equity,
            "trades": trades,
            "report_path": self.last_report_path
        }
