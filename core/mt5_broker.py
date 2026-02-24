import logging
import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta

class MT5Broker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.mt5_connected = False
        self._reconnect_in_progress = False

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

        # Pre-check
        check_result = mt5.order_check(request)
        if check_result is None or check_result.retcode != mt5.TRADE_RETCODE_DONE:
             err = check_result.retcode if check_result else mt5.last_error()
             return f"Pre-Check fehlgeschlagen (Fehler {err})"

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
