import os
import time
import threading

class TerminalColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class CLIMenu:
    def __init__(self, main_app, logger=None):
        """
        Initializes the CLI Menu.
        main_app is an instance of the orchestrator class (e.g., MT5FinGPT)
        that provides access to broker, ai, risk_manager, etc.
        """
        self.app = main_app
        self.logger = logger
        self.ui_lock = threading.Lock()
        
        # Enable ANSI colors for Windows cmd
        if os.name == 'nt':
            os.system("")

    def print_header(self, title, width=80):
        """Beautiful header output with ANSI colors"""
        print(f"\n{TerminalColors.OKCYAN}{TerminalColors.BOLD}╔" + "═" * (width - 2) + "╗")
        print(f"║{title:^{width-2}}║")
        print("╚" + "═" * (width - 2) + f"╝{TerminalColors.ENDC}")

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_error(self, message):
        print(f"{TerminalColors.FAIL}❌ FEHLER:{TerminalColors.ENDC} {message}")

    def print_success(self, message):
        print(f"{TerminalColors.OKGREEN}✅ ERFOLG:{TerminalColors.ENDC} {message}")

    def print_warning(self, message):
        print(f"{TerminalColors.WARNING}⚠️ WARNUNG:{TerminalColors.ENDC} {message}")

    def print_status_bar(self):
        """Dynamic status bar showing all components"""
        try:
            with self.ui_lock:
                risk_status = "❌"
                if hasattr(self.app, 'risk_manager') and self.app.risk_manager:
                    try:
                        summary = self.app.risk_manager.get_risk_summary()
                        if summary is not None:
                            risk_status = "✅"
                            daily_pnl = summary.get('daily_pnl', 0)
                            if hasattr(self.app.risk_manager, 'max_daily_loss'):
                                if daily_pnl <= self.app.risk_manager.max_daily_loss * 0.8:
                                    risk_status = "🟡"
                                elif daily_pnl <= self.app.risk_manager.max_daily_loss:
                                    risk_status = "🔴"
                    except Exception:
                        risk_status = "⚠️"

                status_items = [
                    f"📱 MT5: {'✅' if getattr(self.app, 'broker', None) and getattr(self.app.broker, 'mt5_connected', False) else '❌'}",
                    f"🤖 KI: {'✅' if getattr(self.app, 'ai', None) and hasattr(self.app.ai, 'selected_model') and self.app.ai.selected_model else '❌'}",
                    f"💰 Trading: {'✅' if getattr(self.app, 'trading_enabled', False) else '❌'}",
                    f"🔄 Auto: {'✅' if getattr(self.app, 'auto_trading', False) else '❌'}",
                    f"🛡️ Risk: {risk_status}",
                ]

                if getattr(self.app, 'has_extended_indicators', False):
                    indicators_count = "7+"
                    indicators_status = "✅"
                else:
                    indicators_count = "3"
                    indicators_status = "📊"
        
                status_items.append(f"📊 Ind.: {indicators_status}({indicators_count})")

                if hasattr(self.app, 'rl_enabled'):
                    rl_status = "✅" if self.app.rl_enabled else "❌"
                    status_items.append(f"🤖 RL: {rl_status}")

                status_items.append(f"🔧 Comp.: {'✅' if getattr(self.app, 'companion_enabled', False) else '❌'}")

                total_width = max(80, len(' ┃ '.join(status_items)) + 4)
        
                print(f"{TerminalColors.OKBLUE}┏" + "━" * (total_width - 2) + f"┓{TerminalColors.ENDC}")
                print(f"{TerminalColors.OKBLUE}┃ {TerminalColors.ENDC}{(' ┃ '.join(status_items)):<{total_width-4}}{TerminalColors.OKBLUE} ┃{TerminalColors.ENDC}")
                print(f"{TerminalColors.OKBLUE}┗" + "━" * (total_width - 2) + f"┛{TerminalColors.ENDC}")
            
        except Exception as e:
            self.print_error(f"Status-Bar Fehler: {str(e)[:50]}")

    def interactive_menu(self):
        """Overhauled modern interactive menu"""
        if getattr(self.app, 'auto_start_companion', False) and not getattr(self.app, 'companion_enabled', False):
            self.app.companion_silent_mode = True
            print(f"{TerminalColors.OKCYAN}🔧 Starte Trading Companion...{TerminalColors.ENDC}")
            try:
                self.app.start_trading_companion()
            except Exception as e:
                self.print_error(f"Konnte Companion nicht starten: {e}")
            self.app.companion_silent_mode = False
    
        while True:
            # Let the companion print anything it needs before we repaint the menu
            companion_was_active = getattr(self.app, 'companion_enabled', False)
            if companion_was_active:
                time.sleep(0.1)
    
            header_title = "FinGPT TRADING SYSTEM"
            if getattr(self.app, 'has_extended_indicators', False):
                header_title += " (ERWEITERT)"
            if getattr(self.app, 'rl_enabled', False):
                header_title += " + RL"
        
            print("\n")
            self.print_header(header_title)
            self.print_status_bar()
    
            print(f"\n{TerminalColors.BOLD}📋 HAUPTMENÜ:{TerminalColors.ENDC}")
            print(f"{TerminalColors.HEADER}────────────────────────────────────────────────────────────────────────────────{TerminalColors.ENDC}")
            
            # Group 1
            print(f"{TerminalColors.OKGREEN}🟢 TRADING & POSITIONEN{TerminalColors.ENDC}")
            print("  1. 💰 Trade ausführen")
            print("  2. 📈 Offene Positionen verwalten")
            print(f"  3. 🔄 Auto-Trading {TerminalColors.OKCYAN}[Umschalten]{TerminalColors.ENDC}")
            print(f"  4. 🔓 Trading global {TerminalColors.WARNING}[Aktivieren/Deaktivieren]{TerminalColors.ENDC}")
            
            # Group 2
            print(f"\n{TerminalColors.OKBLUE}🔵 ANALYSE & DATEN{TerminalColors.ENDC}")
            print("  5. 📊 Live-Daten (Quotes)")
            print("  6. 🤖 KI-Analyse (inkl. Indikatoren)")
            print("  7. 🎯 Signal-Generator (Multi-Indikator)")
            print("  8. 📉 Indikator-Scanner & Vergleich")
            
            # Group 3
            print(f"\n{TerminalColors.WARNING}⚙️ EINSTELLUNGEN & SYSTEM{TerminalColors.ENDC}")
            print("  9. 🛡️ Risk Management (Stop-Loss, Limits)")
            print(" 10. 🎯 Partial Close & Trailing Stop")
            print(" 11. 📈 Indikator- & Timeframe-Settings")
            print(" 12. 🔗 MT5 Verbindung / Währungspaare")
            print(" 13. 🔧 Trading Companion")
            print(" 14. 🤖 Reinforcement Learning")

            # Group 4
            print(f"\n{TerminalColors.HEADER}🌐 GLOBALE KONFIGURATION (GUI-Vollparität){TerminalColors.ENDC}")
            print(" 15. 🤖 KI & Ollama Einstellungen")
            print(" 16. 📊 Trading Stil & Ausführung (inkl. AI-Fulldrive)")
            print(" 17. 🔕 Benachrichtigungen (Telegram / Discord)")

            print(f"\n{TerminalColors.FAIL} 18. ❌ Beenden{TerminalColors.ENDC}")
            print(f"{TerminalColors.HEADER}────────────────────────────────────────────────────────────────────────────────{TerminalColors.ENDC}")

            try:
                print(f"{TerminalColors.BOLD}🎯 Ihre Wahl (1-18): {TerminalColors.ENDC}", end="", flush=True)
                choice = input().strip()
            except KeyboardInterrupt:
                choice = "18"
            
            if not choice:
                continue
    
            if not self.handle_menu_choice(choice):
                break

    def handle_menu_choice(self, choice):
        """Robust menu selection handling"""
        with open("menu_debug.log", "a", encoding="utf-8") as debug_file:
            debug_file.write(f"[{time.strftime('%H:%M:%S')}] Received choice: '{choice}'\n")
        
        try:
            if choice == "1":
                with open("menu_debug.log", "a", encoding="utf-8") as debug_file:
                    debug_file.write(f"[{time.strftime('%H:%M:%S')}] Processing choice 1\n")
                if not getattr(self.app, 'trading_enabled', False):
                    self.print_warning("TRADING IST AKTUELL DEAKTIVIERT!")
                    print("Möchten Sie Trading jetzt AKTIVIEREN? (j/n): ", end="", flush=True)
                    confirm = input().lower().strip()
                    if confirm == 'j':
                        self.app.trading_enabled = True
                        self.print_success("Trading wurde AKTIVIERT.")
                    else:
                        self.print_error("Trade abgebrochen (Trading deaktiviert).")
                        self.pause_menu()
                        return True

                if getattr(self.app, 'trading_enabled', False):
                    print(f"{TerminalColors.OKCYAN}Symbol (z.B. EURUSD): {TerminalColors.ENDC}", end="", flush=True)
                    symbol = input().upper().strip()
                    if symbol:
                        print(f"{TerminalColors.OKCYAN}Aktion (BUY/SELL): {TerminalColors.ENDC}", end="", flush=True)
                        action = input().upper().strip()
                        if action in ["BUY", "SELL"]:
                            lot_size = getattr(self.app, 'default_lot_size', 0.1)
                            if hasattr(self.app, 'execute_trade'):
                                result = self.app.execute_trade(symbol, action, lot_size)
                                print(f"\n{TerminalColors.BOLD}Ergebnis:{TerminalColors.ENDC} {result}")
                            else:
                                self.print_error("execute_trade Methode in Haupt-App nicht gefunden.")
                        else:
                            self.print_error("Ungültige Aktion. Nur BUY oder SELL erlaubt.")
                    else:
                        self.print_error("Kein Symbol eingegeben.")
                
                self.pause_menu()
                return True
        
            elif choice == "2":
                self.print_header("POSITION MANAGEMENT")
                if getattr(self.app, 'broker', None) and hasattr(self.app.broker, 'manage_open_positions'):
                    self.app.broker.manage_open_positions()
                elif hasattr(self.app, 'manage_open_positions'):
                    self.app.manage_open_positions()
                else:
                    self.print_error("Broker oder manage_open_positions nicht verfügbar.")
                self.pause_menu()
                return True
                
            elif choice == "3":
                if not getattr(self.app, 'trading_enabled', False):
                    self.print_error("Erst Trading aktivieren! (Option 4)")
                elif getattr(self.app, 'auto_trading', False):
                    sym_count = len(getattr(self.app, 'auto_trade_symbols', []))
                    print(f"\n{TerminalColors.OKBLUE}🔄 AUTO-TRADING LÄUFT ({sym_count} Symbole){TerminalColors.ENDC}")
                    if input("Auto-Trading stoppen? (ja/nein): ").lower().strip() == "ja":
                        self.app.auto_trading = False
                        self.print_success("Auto-Trading gestoppt")
                else:
                    print(f"\n{TerminalColors.WARNING}🤖 AUTO-TRADING SETUP (Erweitertes Risiko!){TerminalColors.ENDC}")
                    if input("Aktivieren? (ja/nein): ").lower().strip() == "ja":
                        pairs_input = input("Symbole (kommagetrennt, Enter für Majors): ").upper().strip()
                        if pairs_input:
                            self.app.auto_trade_symbols = [p.strip() for p in pairs_input.split(',')]
                        else:
                            self.app.auto_trade_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
                        
                        try:
                            iv = input(f"Intervall (Enter für {getattr(self.app, 'analysis_interval', 300)}s): ").strip()
                            if iv: self.app.analysis_interval = int(iv)
                        except ValueError:
                            pass
                        
                        self.app.auto_trading = True
                        sym_count = len(self.app.auto_trade_symbols)
                        self.print_success(f"Starte Auto-Trading für {sym_count} Paare...")
                        if hasattr(self.app, 'run_auto_trading'):
                            self.app.run_auto_trading()
                        else:
                            self.print_warning("run_auto_trading ist im Hintergrund aktiv.")
                self.pause_menu()
                return True
                
            elif choice == "4":
                self.app.trading_enabled = not getattr(self.app, 'trading_enabled', False)
                status = 'AKTIVIERT' if self.app.trading_enabled else 'DEAKTIVIERT'
                color = TerminalColors.OKGREEN if self.app.trading_enabled else TerminalColors.WARNING
                print(f"{color}Trading ist nun {status}.{TerminalColors.ENDC}")
                self.pause_menu()
                return True

            elif choice == "5":
                symbol = input("Symbol eingeben: ").upper().strip()
                if symbol:
                    if getattr(self.app, 'broker', None) and hasattr(self.app.broker, 'get_mt5_live_data'):
                        print(f"\n{self.app.broker.get_mt5_live_data(symbol)}")
                    elif hasattr(self.app, 'get_mt5_live_data'):
                        print(f"\n{self.app.get_mt5_live_data(symbol)}")
                    else:
                        self.print_error("Live-Daten Funktion nicht verfügbar.")
                self.pause_menu()
                return True
                
            elif choice == "6":
                symbol = input("Symbol für KI Analyse: ").upper().strip()
                if symbol:
                    if getattr(self.app, 'broker', None) and getattr(self.app, 'ai', None):
                        live_data = self.app.broker.get_mt5_live_data(symbol) if hasattr(self.app.broker, 'get_mt5_live_data') else ""
                        if live_data and "Fehler" not in live_data:
                            print(f"\n{TerminalColors.OKCYAN}🤖 Analysiere {symbol}...{TerminalColors.ENDC}")
                            prompt = "Analysiere Daten, bewerte S/R und Indikatoren. Mach es kurz und als BUY/SELL/WARTEN Empfehlung mit Begründung."
                            if hasattr(self.app.ai, 'chat_with_model'):
                                ai_response = getattr(self.app, 'chat_with_model', lambda p, d: "")(prompt, live_data)
                                if hasattr(self.app.ai, 'display_formatted_analysis'):
                                    self.app.ai.display_formatted_analysis(symbol, ai_response, live_data)
                                else:
                                    print(ai_response)
                            else:
                                self.print_error("KI Modul nicht ordnungsgemäß initialisiert.")
                        else:
                            self.print_error("Konnte keine Live-Daten abrufen.")
                    else:
                        self.print_error("Broker oder KI Modul nicht verfügbar.")
                self.pause_menu()
                return True

            elif choice == "7":
                if getattr(self.app, 'has_extended_indicators', False) and hasattr(self.app, 'advanced_signal_generator'):
                    self.app.advanced_signal_generator()
                else:
                    self.print_error("Erweiterte Indikatoren nicht verfügbar")
                self.pause_menu()
                return True

            elif choice == "8":
                if getattr(self.app, 'has_extended_indicators', False):
                    print(f"{TerminalColors.OKCYAN}Optionen:{TerminalColors.ENDC}")
                    print("1. Multi-Scanner")
                    print("2. Indikator Vergleich (Single Symbol)")
                    sub = input("Wahl (1-2): ").strip()
                    if sub == "1" and hasattr(self.app, 'multi_indicator_scanner'): 
                        self.app.multi_indicator_scanner()
                    elif sub == "2" and hasattr(self.app, 'indicator_comparison_analysis'): 
                        self.app.indicator_comparison_analysis()
                    else:
                        self.print_error("Auswahl abgebrochen oder Funktion fehlt.")
                else:
                    self.print_error("Erweiterte Indikatoren nicht verfügbar")
                self.pause_menu()
                return True

            elif choice == "9":
                if hasattr(self.app, 'risk_manager') and self.app.risk_manager and hasattr(self.app, 'risk_management_menu'):
                    self.app.risk_management_menu()
                else:
                    self.print_error("Risk Manager nicht verfügbar")
                self.pause_menu()
                return True

            elif choice == "10":
                print(f"{TerminalColors.OKCYAN}Optionen:{TerminalColors.ENDC}")
                print("1. Partial Close Einstellungen")
                print("2. Trailing Stop Einstellungen")
                sub = input("Wahl (1-2): ").strip()
                if sub == "1":
                    self.print_header("PARTIAL CLOSE")
                    self.app.partial_close_enabled = not getattr(self.app, 'partial_close_enabled', False)
                    self.print_success(f"Partial Close umgeschaltet auf: {self.app.partial_close_enabled}")
                elif sub == "2" and hasattr(self.app, 'trailing_stop_settings_menu'):
                    self.app.trailing_stop_settings_menu()
                self.pause_menu()
                return True

            elif choice == "11":
                self.print_header("INDIKATOR EINSTELLUNGEN")
                print("1. RSI Settings")
                print("2. S/R Settings")
                print("3. MACD Settings")
                print("4. Multi-Timeframe Settings")
                if getattr(self.app, 'has_extended_indicators', False):
                    print("5. Erweiterte Indikatoren Settings")
                sub = input("Wahl: ").strip()
                
                if sub == "1":
                    current_rsi = getattr(self.app, 'rsi_period', 14)
                    new_rsi = input(f"Neue RSI Periode (aktuell {current_rsi}): ").strip()
                    if new_rsi.isdigit(): 
                        self.app.rsi_period = int(new_rsi)
                        self.print_success("RSI Periode aktualisiert.")
                elif sub == "2" and hasattr(self.app, 'sr_settings_menu'): self.app.sr_settings_menu()
                elif sub == "3" and hasattr(self.app, 'macd_settings_menu'): self.app.macd_settings_menu()
                elif sub == "4" and hasattr(self.app, 'mtf_settings_menu'): self.app.mtf_settings_menu()
                elif sub == "5" and getattr(self.app, 'has_extended_indicators', False) and hasattr(self.app, 'advanced_indicator_settings_menu'): 
                    self.app.advanced_indicator_settings_menu()
                self.pause_menu()
                return True

            elif choice == "12":
                self.print_header("MT5 & NETZWERK")
                print("1. Währungspaar Management")
                print("2. MT5 Reconnect")
                sub = input("Wahl (1-2): ").strip()
                if sub == "1" and hasattr(self.app, 'currency_pair_management_menu'): 
                    self.app.currency_pair_management_menu()
                elif sub == "2": 
                    if getattr(self.app, 'broker', None):
                        if getattr(self.app.broker, 'mt5_connected', False) and hasattr(self.app.broker, 'disconnect_mt5'): 
                            self.app.broker.disconnect_mt5()
                        if hasattr(self.app.broker, 'connect_mt5'):
                            self.app.broker.connect_mt5()
                            self.print_success("MT5 Reconnect Versuch ausgeführt.")
                    else:
                        self.print_error("Broker Instanz fehlt.")
                self.pause_menu()
                return True

            elif choice == "13":
                if hasattr(self.app, 'companion_menu'):
                    self.app.companion_menu()
                else:
                    self.print_error("Trading Companion Menü nicht verfügbar")
                return True

            elif choice == "14":
                if getattr(self.app, 'rl_enabled', False) and hasattr(self.app, 'rl_menu_enhanced'):
                    self.app.rl_menu_enhanced()
                else:
                    self.print_error("Reinforcement Learning Modul nicht verfügbar")
                self.pause_menu()
                return True

            elif choice == "15":
                if hasattr(self.app, 'ai_ki_settings_menu'):
                    self.app.ai_ki_settings_menu()
                else:
                    self.print_error("KI & Ollama Einstellungen nicht gefunden")
                return True

            elif choice == "16":
                if hasattr(self.app, 'trading_style_settings_menu'):
                    self.app.trading_style_settings_menu()
                else:
                    self.print_error("Trading Stil Einstellungen nicht gefunden")
                return True

            elif choice == "17":
                if hasattr(self.app, 'notifications_settings_menu'):
                    self.app.notifications_settings_menu()
                else:
                    self.print_error("Benachrichtigungen Einstellungen nicht gefunden")
                return True

            elif choice == "18":
                print(f"\n{TerminalColors.OKCYAN}Fahre FinGPT System herunter...{TerminalColors.ENDC}")
                if hasattr(self.app, 'shutdown_system'):
                    return self.app.shutdown_system()
                return False

            else:
                self.print_error("Ungültige Option gewählt. Bitte eine Zahl (1-18) eingeben.")
                self.pause_menu()
                return True
                
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            with open("menu_debug.log", "a", encoding="utf-8") as debug_file:
                debug_file.write(f"[{time.strftime('%H:%M:%S')}] Exception in menu: {err_msg}\n")
            self.print_error(f"unerwarteter Fehler in der Menü-Aktion: {e}")
            print(err_msg)
            self.pause_menu()
            return True
            
    def pause_menu(self):
        print(f"\n{TerminalColors.BOLD}Drücken Sie Enter zum Fortfahren...{TerminalColors.ENDC}", end="", flush=True)
        input()
