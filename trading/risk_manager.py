#!/usr/bin/env python3
"""
RiskManager Klasse für FinGPT Trading System
Erweiterte Risk Management Funktionen
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import logging

class RiskManager:
    def __init__(self, logger=None, max_daily_loss: float = -500.0,
                 max_weekly_loss: float = -1500.0, max_drawdown: float = -2000.0,
                 max_risk_per_trade: float = 2.0, max_total_positions: int = 3):
        """
        Initialisiert den Risk Manager

        Args:
            logger: Logger-Instanz (optional)
            max_daily_loss: Maximaler Tagesverlust (negativ, z.B. -500.0)
            max_weekly_loss: Maximaler Wochenverlust (negativ)
            max_drawdown: Maximaler Drawdown (negativ)
            max_risk_per_trade: Risiko in % des Kontos pro Trade
            max_total_positions: Max Gesamtpositionen
        """
        self.logger = logger or logging.getLogger(__name__)

        # Grundlegende Risk Limits (konfigurierbar)
        self.max_daily_loss = max_daily_loss
        self.max_weekly_loss = max_weekly_loss
        self.max_drawdown = max_drawdown
        self.max_risk_per_trade = max_risk_per_trade

        # Position Limits
        self.max_positions_per_symbol = 1  # Max Positionen pro Symbol
        self.max_total_positions = max_total_positions
        self.max_correlation_exposure = 0.7  # Max Korrelationsexposure

        # Lot Size Limits
        self.min_lot_size = 0.01
        self.max_lot_size = 1.0
        self.default_lot_size = 0.1

        # Time-based Limits
        self.trading_start_hour = 8  # Frühester Trading-Beginn
        self.trading_end_hour = 22   # Spätester Trading-Schluss
        self.max_trades_per_day = 10
        self.min_time_between_trades = 300  # Sekunden zwischen Trades

        # Tracking Variablen
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.total_drawdown = 0.0
        self.trades_today = 0
        self.last_trade_time = None
        self.daily_reset_time = None

        # Korrelationen (wird später erweitert)
        self.symbol_correlations = {}

        self.log("INFO", "RiskManager initialisiert", "RISK")
    
    def log(self, level: str, message: str, category: str = "RISK"):
        """Logging-Funktion — verwendet den echten Logger"""
        formatted_message = f"[{category}] {message}"
        if level == "INFO":
            self.logger.info(formatted_message)
        elif level == "WARNING":
            self.logger.warning(formatted_message)
        elif level == "ERROR":
            self.logger.error(formatted_message)
        elif level == "DEBUG":
            self.logger.debug(formatted_message)
    
    def update_daily_stats(self):
        """Aktualisiert tägliche Statistiken"""
        try:
            current_date = datetime.now().date()
            
            # Reset um Mitternacht
            if self.daily_reset_time != current_date:
                self.daily_pnl = 0.0
                self.trades_today = 0
                self.daily_reset_time = current_date
                self.log("INFO", "Tägliche Statistiken zurückgesetzt")
            
            # Berechne aktuellen P&L
            positions = mt5.positions_get()
            if positions:
                current_pnl = sum(pos.profit for pos in positions)
                
                # Hole geschlossene Trades von heute
                today_start = datetime.combine(current_date, datetime.min.time())
                deals = mt5.history_deals_get(today_start, datetime.now())
                
                if deals:
                    closed_pnl = sum(deal.profit for deal in deals if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL])
                    self.daily_pnl = closed_pnl + current_pnl
                else:
                    self.daily_pnl = current_pnl
            
            return True
            
        except Exception as e:
            self.log("ERROR", f"Fehler bei Daily Stats Update: {e}")
            return False
    
    def calculate_position_size(self, symbol, stop_loss_distance, account_risk_percent=None):
        """
        Berechnet optimale Positionsgröße basierend auf Risiko
        
        Args:
            symbol: Trading Symbol
            stop_loss_distance: Abstand zum Stop Loss in Pips
            account_risk_percent: Risiko in % des Kontos (optional)
            
        Returns:
            float: Berechnete Lot-Größe
        """
        try:
            if account_risk_percent is None:
                account_risk_percent = self.max_risk_per_trade
            
            # Account Info holen
            account_info = mt5.account_info()
            if not account_info:
                self.log("ERROR", "Keine Account-Info verfügbar")
                return self.default_lot_size
            
            # Symbol Info holen
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.log("ERROR", f"Keine Symbol-Info für {symbol}")
                return self.default_lot_size
            
            # Risikokapital berechnen
            account_balance = account_info.balance
            risk_amount = account_balance * (account_risk_percent / 100)
            
            # Pip-Wert berechnen
            pip_size = symbol_info.point
            if symbol_info.digits == 3 or symbol_info.digits == 5:
                pip_size *= 10
            
            # Pip-Wert in Account-Währung
            tick_value = symbol_info.trade_tick_value
            if tick_value == 0:
                tick_value = 1.0
            
            pip_value = (pip_size / symbol_info.trade_tick_size) * tick_value
            
            # Lot-Größe berechnen
            if stop_loss_distance > 0 and pip_value > 0:
                lot_size = risk_amount / (stop_loss_distance * pip_value)
                # Apply safety margin to avoid margin issues
                lot_size = lot_size * 0.95
            else:
                lot_size = self.default_lot_size
            
            # Lot-Größe begrenzen
            lot_size = max(self.min_lot_size, min(lot_size, self.max_lot_size))
            
            # Auf erlaubte Schritte runden
            lot_step = symbol_info.volume_step
            lot_size = round(lot_size / lot_step) * lot_step
            
            self.log("INFO", f"Position Size für {symbol}: {lot_size} Lots (Risiko: {account_risk_percent}%, SL: {stop_loss_distance} Pips)")
            
            return lot_size
            
        except Exception as e:
            self.log("ERROR", f"Position Size Berechnung Fehler: {e}")
            return self.default_lot_size
    
    def can_open_position(self, symbol, action, lot_size):
        """
        Prüft ob eine neue Position eröffnet werden kann
        
        Args:
            symbol: Trading Symbol
            action: BUY oder SELL
            lot_size: Gewünschte Lot-Größe
            
        Returns:
            tuple: (bool, str) - (Erlaubt, Grund)
        """
        try:
            # Update aktuelle Stats
            self.update_daily_stats()
            
            # 1. Täglicher Verlust Check
            if self.daily_pnl <= self.max_daily_loss:
                return False, f"Tägliches Verlustlimit erreicht ({self.daily_pnl:.2f}€ / {self.max_daily_loss:.2f}€)"
            
            # 2. Account Balance Check
            account_info = mt5.account_info()
            if not account_info:
                return False, "Keine Account-Info verfügbar"
            
            if account_info.balance <= 0:
                return False, "Kein verfügbares Kapital"
            
            # 3. Margin Check
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                required_margin = lot_size * symbol_info.trade_contract_size * symbol_info.margin_initial
                free_margin = account_info.margin_free
                
                if required_margin > free_margin * 0.8:  # 80% Sicherheitspuffer
                    return False, f"Nicht genügend Margin (benötigt: {required_margin:.2f}, verfügbar: {free_margin:.2f})"
            
            # 4. Position Limits Check
            existing_positions = mt5.positions_get(symbol=symbol)
            if existing_positions and len(existing_positions) >= self.max_positions_per_symbol:
                return False, f"Max Positionen pro Symbol erreicht ({len(existing_positions)}/{self.max_positions_per_symbol})"
            
            all_positions = mt5.positions_get()
            if all_positions and len(all_positions) >= self.max_total_positions:
                return False, f"Max Gesamtpositionen erreicht ({len(all_positions)}/{self.max_total_positions})"
            
            # 5. Trades pro Tag Check
            if self.trades_today >= self.max_trades_per_day:
                return False, f"Max Trades pro Tag erreicht ({self.trades_today}/{self.max_trades_per_day})"
            
            # 6. Zeit zwischen Trades Check
            if self.last_trade_time:
                time_since_last = (datetime.now() - self.last_trade_time).total_seconds()
                if time_since_last < self.min_time_between_trades:
                    remaining = self.min_time_between_trades - time_since_last
                    return False, f"Warten Sie noch {remaining:.0f}s bis zum nächsten Trade"
            
            # 7. Trading Hours Check
            current_hour = datetime.now().hour
            if not (self.trading_start_hour <= current_hour <= self.trading_end_hour):
                return False, f"Außerhalb der Trading-Zeiten ({self.trading_start_hour}:00 - {self.trading_end_hour}:00)"
            
            # 8. Lot Size Validation
            if not (self.min_lot_size <= lot_size <= self.max_lot_size):
                return False, f"Lot-Größe außerhalb der Limits ({lot_size} nicht in {self.min_lot_size}-{self.max_lot_size})"
            
            # 9. Market Status Check
            if symbol_info and not symbol_info.visible:
                return False, f"Symbol {symbol} nicht handelbar"
            
            # Alle Checks bestanden
            return True, "Trade erlaubt"
            
        except Exception as e:
            self.log("ERROR", f"Position Check Fehler: {e}")
            return False, f"Risk Check Fehler: {e}"
    
    def register_trade(self, symbol, action, lot_size, result):
        """
        Registriert einen ausgeführten Trade
        
        Args:
            symbol: Trading Symbol
            action: BUY oder SELL
            lot_size: Verwendete Lot-Größe
            result: Trade-Ergebnis
        """
        try:
            self.trades_today += 1
            self.last_trade_time = datetime.now()
            
            self.log("INFO", f"Trade registriert: {action} {lot_size} {symbol} - {result}")
            
        except Exception as e:
            self.log("ERROR", f"Trade Registration Fehler: {e}")
    
    def get_risk_summary(self):
        """
        Gibt eine Risiko-Zusammenfassung zurück
        
        Returns:
            dict: Risiko-Statistiken
        """
        try:
            self.update_daily_stats()
            
            # Current Positions
            positions = mt5.positions_get()
            total_exposure = sum(pos.volume for pos in positions) if positions else 0
            
            # Account Info
            account_info = mt5.account_info()
            
            summary = {
                'daily_pnl': self.daily_pnl,
                'daily_limit': self.max_daily_loss,
                'trades_today': self.trades_today,
                'max_trades': self.max_trades_per_day,
                'open_positions': len(positions) if positions else 0,
                'max_positions': self.max_total_positions,
                'total_exposure': total_exposure,
                'account_balance': account_info.balance if account_info else 0,
                'free_margin': account_info.margin_free if account_info else 0,
                'margin_level': account_info.margin_level if account_info else 0
            }
            
            return summary
            
        except Exception as e:
            self.log("ERROR", f"Risk Summary Fehler: {e}")
            return {}
    
    def print_risk_status(self):
        """Druckt aktuellen Risk Status"""
        try:
            summary = self.get_risk_summary()
            
            print("\n🛡️ RISK MANAGEMENT STATUS")
            print("─" * 40)
            print(f"Tages P&L: {summary.get('daily_pnl', 0):.2f}€ / {self.max_daily_loss:.2f}€")
            print(f"Trades heute: {summary.get('trades_today', 0)} / {self.max_trades_per_day}")
            print(f"Offene Positionen: {summary.get('open_positions', 0)} / {self.max_total_positions}")
            print(f"Total Exposure: {summary.get('total_exposure', 0):.2f} Lots")
            print(f"Account Balance: {summary.get('account_balance', 0):.2f}€")
            print(f"Freie Margin: {summary.get('free_margin', 0):.2f}€")
            
            # Status Icons
            pnl_status = "🟢" if summary.get('daily_pnl', 0) > 0 else "🔴" if summary.get('daily_pnl', 0) < self.max_daily_loss * 0.5 else "🟡"
            trades_status = "🟢" if summary.get('trades_today', 0) < self.max_trades_per_day * 0.8 else "🟡"
            positions_status = "🟢" if summary.get('open_positions', 0) < self.max_total_positions else "🟡"
            
            print(f"\nStatus: {pnl_status} P&L | {trades_status} Trades | {positions_status} Positionen")
            print("─" * 40)
            
        except Exception as e:
            self.log("ERROR", f"Risk Status Print Fehler: {e}")
    
    def update_settings(self, **kwargs):
        """
        Aktualisiert Risk Management Einstellungen
        
        Args:
            **kwargs: Einstellungen zum Aktualisieren
        """
        try:
            updated = []
            
            for key, value in kwargs.items():
                if hasattr(self, key):
                    old_value = getattr(self, key)
                    setattr(self, key, value)
                    updated.append(f"{key}: {old_value} -> {value}")
                    
            if updated:
                self.log("INFO", f"Settings aktualisiert: {', '.join(updated)}")
                
        except Exception as e:
            self.log("ERROR", f"Settings Update Fehler: {e}")
