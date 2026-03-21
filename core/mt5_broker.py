import logging
import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from core.interfaces import IBroker

# MT5 error code mapping
MT5_ERROR_CODES = {
    10004: "Requote",
    10006: "Request rejected",
    10007: "Request canceled by trader",
    10008: "Order placed",
    10009: "Request completed",
    10010: "Only part of the request was completed",
    10011: "Error in processing a request",
    10012: "Request canceled by timeout",
    10013: "Invalid request",
    10014: "Invalid volume in the request",
    10015: "Invalid price in the request",
    10016: "Invalid stops in the request",
    10017: "Trade is disabled",
    10018: "Insufficient margin",
    10019: "No money",
    10020: "Price changed",
    10021: "Off quotes",
    10022: "Broker is busy",
    10023: "Invalid price or volume in the request",
    10024: "Invalid order",
    10025: "Position is closed",
    10026: "Invalid order expiration in the request",
    10027: "Number of open and pending orders limit has been reached",
    10028: "No history data",
    10029: "No history data for calculation",
    10030: "Maximal allowed price of the market order has been reached",
    10031: "Maximal allowed price of the limit order has been reached",
    10032: "Maximal allowed price of the stop order has been reached",
    10033: "No money for bank operations",
    10034: "Server error",
    10035: "Module is busy",
    10036: "Invalid order volume in the request",
    10037: "Invalid order stop price in the request",
    10038: "Invalid order stop price limit in the request",
    10039: "Invalid order expiration time in the request",
    10040: "Too many requests",
    10041: "No changes in the request",
    10042: "Autotrading disabled",
    10043: "Invalid expert properties in the request",
    10044: "Invalid signal properties in the request",
}

class MT5Broker(IBroker):
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.mt5_connected = False
        self._reconnect_in_progress = False

    def connect(self) -> bool:
        """Stellt eine Verbindung zu MetaTrader 5 her"""
        return self.connect_mt5()

    def disconnect(self) -> None:
        """Trennt die Verbindung zu MetaTrader 5"""
        self.disconnect_mt5()

    def is_connected(self) -> bool:
        """Prüft, ob die MT5 Verbindung noch aktiv ist"""
        return self.mt5_connected and self.is_mt5_alive()

    def get_live_data(self, symbol: str) -> Dict[str, Any]:
        """Holt die aktuellen Live-Daten aus MT5"""
        data_str = self.get_mt5_live_data(symbol)
        # Return as dict for interface consistency
        return {"raw_data": data_str, "symbol": symbol, "timestamp": datetime.now()}

    def log(self, level, message, category="MT5"):
        # Helper to maintain consistent logging format
        if self.logger:
            formatted_message = f"[{category}] {message}"
            if level == "INFO": self.logger.info(formatted_message)
            elif level == "WARNING": self.logger.warning(formatted_message)
            elif level == "ERROR": self.logger.error(formatted_message)
            elif level == "DEBUG": self.logger.debug(formatted_message)

    def connect_mt5(self):
        """Stellt eine Verbindung zu MetaTrader 5 her"""
        if self._reconnect_in_progress:
            return False

        if not mt5.initialize():
            self.log("ERROR", f"MT5 Initialisierung fehlgeschlagen: {mt5.last_error()}")
            self.mt5_connected = False
            return False

        account_info = mt5.account_info()
        if account_info:
            self.log("INFO", f"Erfolgreich mit MT5 verbunden. Konto: {account_info.login}, Server: {account_info.server}")
            self.log("INFO", f"Balance: {account_info.balance:.2f} {account_info.currency}, Equity: {account_info.equity:.2f}")
            self.mt5_connected = True
            return True
        else:
            self.log("ERROR", f"Konnte Kontoinformationen nicht abrufen: {mt5.last_error()}")
            self.mt5_connected = False
            return False

    def disconnect_mt5(self):
        """Trennt die Verbindung zu MetaTrader 5"""
        if mt5.terminal_info() is not None:
            mt5.shutdown()
        self.mt5_connected = False
        self.log("INFO", "MT5 Verbindung getrennt")

    def is_mt5_alive(self):
        """Prüft, ob die MT5 Verbindung noch aktiv ist"""
        term_info = mt5.terminal_info()
        return term_info is not None

    def reconnect_mt5(self, max_retries: int = 10, base_delay: float = 5.0):
        """Versucht die MT5 Verbindung wiederherzustellen"""
        if self._reconnect_in_progress:
            self.log("DEBUG", "Ein Reconnect-Versuch läuft bereits.")
            return False

        self._reconnect_in_progress = True
        self.log("WARNING", "MT5-Verbindung verloren. Starte Reconnect-Schleife...")
        
        try:
            mt5.shutdown()  # clean state
        except Exception:
            pass

        attempt = 1
        current_delay = base_delay

        try:
            while attempt <= max_retries:
                self.log("INFO", f"Reconnect Versuch {attempt}/{max_retries}...")
                
                if mt5.initialize():
                    acc_info = mt5.account_info()
                    if acc_info is not None:
                        self.log("INFO", f"✔️ Reconnect erfolgreich. Verbunden als: {acc_info.login}")
                        self.mt5_connected = True
                        return True
                
                self.log("WARNING", f"Versuch {attempt} fehlgeschlagen (Error: {mt5.last_error()}). Warte {current_delay}s...")
                time.sleep(current_delay)
                attempt += 1
                current_delay = min(current_delay * 2, 300)  # max 5 mins delay

            self.log("ERROR", "❌ Reconnect endgültig fehlgeschlagen nach allen Versuchen.")
            self.mt5_connected = False
            return False
            
        finally:
            self._reconnect_in_progress = False

    def get_mt5_live_data(self, symbol):
        """Holt die aktuellen Live-Daten aus MT5"""
        if not self.mt5_connected:
            self.reconnect_mt5()
            if not self.mt5_connected:
                 return "Fehler: Keine Verbindung zu MT5"

        tick = mt5.symbol_info_tick(symbol)
        
        # Ensure symbol is available
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return f"Fehler: Symbol {symbol} nicht gefunden"
            
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return f"Fehler: Konnte Symbol {symbol} nicht abonnieren"

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1)
        
        if tick and rates is not None and len(rates) > 0:
            current_close = rates[0]['close']
            
            data_str = (
                f"Aktuelle Daten für {symbol}:\n"
                f"Datum/Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Bid: {tick.bid:.5f}\n"
                f"Ask: {tick.ask:.5f}\n"
                f"Letzter Close (M15): {current_close:.5f}\n"
                f"Spread: {(tick.ask - tick.bid)*10000:.1f} Pips"
            )
            return data_str
        else:
            return f"Fehler: Keine Daten für {symbol} empfangen. Error={mt5.last_error()}"

    def execute_trade(self, symbol, action, lot_size, stop_loss=None, take_profit=None, comment="FinGPT Trade"):
        """Führt einen Trade aus"""
        if not self.mt5_connected:
            self.reconnect_mt5()
            if not self.mt5_connected:
                return "Trade fehlgeschlagen: Keine MT5 Verbindung"

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return f"Trade fehlgeschlagen: Symbol {symbol} nicht gefunden"

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return f"Trade fehlgeschlagen: Symbol {symbol} kann nicht aktiviert werden"

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return "Trade fehlgeschlagen: Keine Tick-Daten verfügbar"

        order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if action == "BUY" else tick.bid

        # MARGIN VALIDATION - Adjust lot_size if insufficient margin
        try:
            account_info = mt5.account_info()
            if account_info:
                free_margin = account_info.margin_free
                # Calculate required margin for the requested lot size
                req_margin = mt5.order_calc_margin(order_type, symbol, float(lot_size), price)
                if req_margin is not None and req_margin > free_margin * 0.8:
                    # Not enough margin - calculate maximum feasible lot size
                    lot_step = symbol_info.volume_step
                    lot_min = symbol_info.volume_min
                    lot_max = symbol_info.volume_max
                    
                    # Calculate max lot size that fits in margin (with 10% safety buffer)
                    max_lot_by_margin = (free_margin * 0.9) / req_margin * float(lot_size)
                    adjusted_lot = round(round(max_lot_by_margin / lot_step) * lot_step, 2)
                    adjusted_lot = max(lot_min, min(adjusted_lot, lot_max))
                    
                    if adjusted_lot < float(lot_size):
                        self.log("WARNING",
                            f"Margin insufficient for {lot_size} lots (req: {req_margin:.2f}, free: {free_margin:.2f}). "
                            f"Adjusting to {adjusted_lot} lots.",
                            "MT5")
                        lot_size = adjusted_lot
                        if lot_size < lot_min:
                            return f"Trade fehlgeschlagen: Nicht genug Margin für Minimal-Lot ({lot_min})"
        except Exception as e:
            self.log("WARNING", f"Margin validation error: {e}", "MT5")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if stop_loss is not None:
             request["sl"] = float(stop_loss)
        if take_profit is not None:
             request["tp"] = float(take_profit)

        # Pre-check with logging
        self.log("INFO", f"Pre-Check request: {request}", "MT5")
        account_info = mt5.account_info()
        if account_info:
            self.log("INFO", f"Account balance: {account_info.balance}, Free margin: {account_info.margin_free}", "MT5")
        else:
            self.log("WARNING", "Could not get account info for logging", "MT5")
        
        # DEBUG: Log MT5 constants
        self.log("DEBUG", f"TRADE_RETCODE_DONE value: {mt5.TRADE_RETCODE_DONE}", "MT5")
        
        check_result = mt5.order_check(request)
        
        # DEBUG: Log full check_result details
        if check_result is None:
            self.log("DEBUG", "check_result is None - checking last_error()", "MT5")
            last_err = mt5.last_error()
            self.log("DEBUG", f"mt5.last_error(): {last_err}", "MT5")
        else:
            self.log("DEBUG", f"check_result type: {type(check_result)}", "MT5")
            self.log("DEBUG", f"check_result.retcode: {check_result.retcode}", "MT5")
            self.log("DEBUG", f"check_result.comment: {check_result.comment}", "MT5")
            # Use getattr with defaults for safety
            self.log("DEBUG", f"check_result.balance: {getattr(check_result, 'balance', 'N/A')}", "MT5")
            self.log("DEBUG", f"check_result.equity: {getattr(check_result, 'equity', 'N/A')}", "MT5")
            self.log("DEBUG", f"check_result.margin: {getattr(check_result, 'margin', 'N/A')}", "MT5")
            self.log("DEBUG", f"check_result.margin_free: {getattr(check_result, 'margin_free', 'N/A')}", "MT5")
            self.log("DEBUG", f"check_result.order: {getattr(check_result, 'order', 'N/A')}", "MT5")
        
        if check_result is None or check_result.retcode != mt5.TRADE_RETCODE_DONE:
             err = check_result.retcode if check_result else mt5.last_error()
             # Improved error handling: handle retcode=0 specifically
             if err == 0:
                 # retcode 0 often means success or no error - let's check the comment
                 comment = check_result.comment if check_result else ""
                 if comment and "done" in comment.lower():
                     self.log("INFO", f"Pre-Check returned retcode=0 but comment suggests success: {comment}", "MT5")
                     # Treat as success - continue to order_send
                     pass
                 else:
                     error_description = f"Retcode 0 (possibly success) - Comment: {check_result.comment if check_result else 'N/A'}"
                     self.log("ERROR", f"Pre-Check with retcode=0: {error_description}", "MT5")
                     return f"Pre-Check fehlgeschlagen (Fehler {err}: {error_description})"
             else:
                 error_description = MT5_ERROR_CODES.get(err, f"Unknown error code {err}")
                 self.log("ERROR", f"Pre-Check failed with error: {err} - {error_description}", "MT5")
                 return f"Pre-Check fehlgeschlagen (Fehler {err}: {error_description})"

        # Send order
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
             return f"Order Error: {result.comment} ({result.retcode})"
             
        # Berechne SL / TP Abstand in Pips
        point = symbol_info.point
        sl_pips = abs(price - stop_loss) / point if stop_loss else 0
        tp_pips = abs(take_profit - price) / point if take_profit else 0

        msg = (f"✅ Erfolgreich! Position eröffnet:\n"
               f"Ticket: {result.order}\n"
               f"Volumen: {result.volume}\n"
               f"Preis: {result.price}")
               
        if stop_loss: msg += f"\nSL: {stop_loss} ({int(sl_pips)} Punkte)"
        if take_profit: msg += f"\nTP: {take_profit} ({int(tp_pips)} Punkte)"
        
        return msg

    def manage_open_positions(self):
         """Verwaltet offene Positionen interactive"""
         positions = mt5.positions_get()
         if not positions:
             print("ℹ️ Keine offenen Positionen.")
             return

         print("\n📌 OFFENE POSITIONEN:")
         print(f"{'Ticket':<10} {'Symbol':<10} {'Typ':<6} {'Lot':<6} {'Open':<10} {'Current':<10} {'Profit':<10}")
         print("-" * 65)
         
         for p in positions:
             type_str = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
             profit_str = f"€{p.profit:.2f}" if p.profit >= 0 else f"-€{abs(p.profit):.2f}"
             print(f"{p.ticket:<10} {p.symbol:<10} {type_str:<6} {p.volume:<6.2f} {p.price_open:<10.5f} {p.price_current:<10.5f} {profit_str:<10}")

         choice = input("\nAktion: [T]icket schließen, [A]lle schließen, [E]xit: ").upper()
         if choice == "A":
             for p in positions:
                 self.close_position(p.ticket, "Manual Close All")
             print("✅ Alle Positionen geschlossen.")
         elif choice.isdigit() or choice.startswith("T"):
             opt = choice[1:].strip() if choice.startswith("T") else choice.strip()
             if opt.isdigit():
                 res = self.close_position(int(opt), "Manual Close")
                 print(res)

    def get_open_positions(self, symbol=None):
         """Gibt offene Positionen zurück (optional gefiltert)"""
         if not self.mt5_connected:
             return []
         
         positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
         if positions is None:
             return []
         return positions

    def close_position(self, ticket, comment="FinGPT Close"):
         """Schließt eine spezifische Position"""
         if not self.mt5_connected:
              return "Fehler: MT5 nicht verbunden"

         position = mt5.positions_get(ticket=ticket)
         if position is None or len(position) == 0:
              return f"Fehler: Position {ticket} nicht gefunden"
              
         position = position[0]
         
         tick = mt5.symbol_info_tick(position.symbol)
         if not tick: return "Fehler: Keine Preisdaten"
             
         action = mt5.TRADE_ACTION_DEAL
         order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
         price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

         request = {
             "action": action,
             "symbol": position.symbol,
             "volume": position.volume,
             "type": order_type,
             "position": position.ticket,
             "price": price,
             "deviation": 20,
             "magic": 234000,
             "comment": comment,
             "type_time": mt5.ORDER_TIME_GTC,
             "type_filling": mt5.ORDER_FILLING_IOC,
         }

         result = mt5.order_send(request)
         if result.retcode != mt5.TRADE_RETCODE_DONE:
              return f"Schließen fehlgeschlagen für {ticket}: {result.comment} ({result.retcode})"
              
         return f"✅ Position {ticket} geschlossen. Profit: {position.profit:.2f}"

    def partial_close_position(self, position, close_percentage):
        """Schließt einen Teil der Position basierend auf dem Prozentsatz"""
        if not self.mt5_connected:
             return False, "Fehler: MT5 nicht verbunden"

        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info:
             return False, "Fehler: Symbol-Info nicht gefunden"

        # Berechne close-Volumen
        close_volume = position.volume * (close_percentage / 100.0)
        
        # Runde auf Step-Size
        vol_step = symbol_info.volume_step
        close_volume = round(close_volume / vol_step) * vol_step
        
        # Kontrolliere Minimum
        if close_volume < symbol_info.volume_min:
             return False, f"Volumen zu klein für Partial Close ({close_volume} < {symbol_info.volume_min})"
             
        # Verhindere Über-Schließen
        if close_volume > position.volume:
             close_volume = position.volume

        tick = mt5.symbol_info_tick(position.symbol)
        if not tick:
             return False, "Fehler: Keine Preisdaten"
             
        deal_action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": deal_action,
            "symbol": position.symbol,
             "volume": close_volume,
             "type": order_type,
             "position": position.ticket,
             "price": price,
             "deviation": 20,
             "magic": 234000,
             "comment": f"FinGPT Partial Close ({close_percentage}%)",
             "type_time": mt5.ORDER_TIME_GTC,
             "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"Partial-Close fehlgeschlagen: {result.comment}"
             
        return True, f"✅ Partial Close ({close_volume} Lots) ausgeführt."
