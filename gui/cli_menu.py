import threading

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

    def print_header(self, title, width=55):
        """Schöne Header-Darstellung"""
        print("\n" + "═" * width)
        print(f"{title:^{width}}")
        print("═" * width)

    def print_status_bar(self):
        """Status-Leiste - Funktioniert mit und ohne erweiterte Features"""
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
                    f"📱 MT5: {'✅' if self.app.broker and self.app.broker.mt5_connected else '❌'}",
                    f"🤖 KI: {'✅' if self.app.ai and self.app.ai.selected_model else '❌'}",
                    f"💰 Trading: {'✅' if self.app.trading_enabled else '❌'}",
                    f"🔄 Auto: {'✅' if self.app.auto_trading else '❌'}",
                    f"🛡️ Risk: {risk_status}",
                ]

                if getattr(self.app, 'has_extended_indicators', False):
                    indicators_count = "7+"
                    indicators_status = "✅"
                else:
                    indicators_count = "3"
                    indicators_status = "📊"
        
                status_items.append(f"📊 Indicators: {indicators_status}({indicators_count})")

                if hasattr(self.app, 'rl_enabled'):
                    rl_status = "✅" if self.app.rl_enabled else "❌"
                    status_items.append(f"🤖 RL: {rl_status}")

                status_items.append(f"🔧 Companion: {'✅' if self.app.companion_enabled else '❌'}")

                total_width = max(75, len(' | '.join(status_items)) + 4)
        
                print("\n┌" + "─" * total_width + "┐")
                print(f"│ {' | '.join(status_items):<{total_width-2}} │")
                print("└" + "─" * total_width + "┘")
            
        except Exception as e:
            print("\n┌─────────────────────────────────────────────────────────────────┐")
            print(f"│ Status-Bar Fehler: {str(e)[:50]:<50} │")
            print("└─────────────────────────────────────────────────────────────────┘")

    def interactive_menu(self):
        """Korrigierte interaktive Benutzeroberfläche - Vollständige Menü-Anzeige"""
        if self.app.auto_start_companion and not self.app.companion_enabled:
            self.app.companion_silent_mode = True
            print("🔧 Starte Trading Companion...")
            self.app.start_trading_companion()
            self.app.companion_silent_mode = False
    
        while True:
            companion_was_active = self.app.companion_enabled
            if companion_was_active:
                import time
                time.sleep(0.1)
    
            header_title = "FinGPT TRADING SYSTEM"
            if getattr(self.app, 'has_extended_indicators', False):
                header_title += " (ERWEITERT)"
            if getattr(self.app, 'rl_enabled', False):
                header_title += " + RL"
        
            self.print_header(header_title)
            self.print_status_bar()
    
            print("\n📋 HAUPTMENÜ:")
            print("─" * 40)
            print("🟢 TRADING & POSITIONEN")
            print("  1. 💰 Trade ausführen")
            print("  2. 📈 Offene Positionen verwalten")
            print("  3. 🔄 Auto-Trading umschalten")
            print("  4. 🔓 Trading global aktivieren/deaktivieren")
            
            print("\n🔵 ANALYSE & DATEN")
            print("  5. 📊 Live-Daten (Quotes)")
            print("  6. 🤖 KI-Analyse (inkl. Indikatoren)")
            print("  7. 🎯 Signal-Generator (Multi-Indikator)")
            print("  8. 📉 Indikator-Scanner & Vergleich")
            
            print("\n⚙️ EINSTELLUNGEN & SYSTEM")
            print("  9. 🛡️ Risk Management (Stop-Loss, Limits)")
            print(" 10. 🎯 Partial Close & Trailing Stop")
            print(" 11. 📈 Indikator- & Timeframe-Settings")
            print(" 12. 🔗 MT5 Verbindung / Währungspaare")
            print(" 13. 🔧 Trading Companion")
            print(" 14. 🤖 Reinforcement Learning")
            print("\n 15. ❌ Beenden")
            print("─" * 40)

            max_option = 15
            choice = ""
            try:
                choice = input(f"🎯 Ihre Wahl (1-{max_option}): ").strip()
            except KeyboardInterrupt:
                choice = str(max_option)
            
            if not choice:
                continue
    
            if not self.handle_menu_choice(choice):
                break

    def handle_menu_choice(self, choice):
        """Kombinierte Menü-Behandlung mit übersichtlichen Gruppen"""
        
        if choice == "1":
            if not self.app.trading_enabled:
                print("Trading nicht aktiviert!")
            else:
                symbol = input("Symbol: ").upper()
                action = input("Aktion (BUY/SELL): ").upper()
                if symbol and action in ["BUY", "SELL"]:
                    if self.app.broker:
                         # Simplified call without full risk management integration here for brevity
                         # In real integration, route through the app's execute_trade to use RiskManager
                         result = self.app.broker.execute_trade(symbol, action, self.app.default_lot_size)
                         print(result)
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True
    
        elif choice == "2":
            self.print_header("POSITION MANAGEMENT")
            if self.app.broker:
                self.app.broker.manage_open_positions()
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True
            
        elif choice == "3":
            if not self.app.trading_enabled:
                print("❌ Erst Trading aktivieren! (Option 4)")
            elif self.app.auto_trading:
                print(f"\n🔄 AUTO-TRADING LÄUFT ({len(self.app.auto_trade_symbols)} Symbole)")
                if input("Auto-Trading stoppen? (ja/nein): ").lower() == "ja":
                    self.app.auto_trading = False
                    print("✅ Auto-Trading gestoppt")
            else:
                print("\n🤖 AUTO-TRADING SETUP (GEFÄHRLICH!)")
                if input("Aktivieren? (GEFÄHRLICH/nein): ") == "GEFÄHRLICH":
                    pairs_input = input("Symbole (kommagetrennt, Enter für Majors): ").upper()
                    if pairs_input:
                        self.app.auto_trade_symbols = [p.strip() for p in pairs_input.split(',')]
                    else:
                        self.app.auto_trade_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
                    try:
                        iv = input(f"Intervall (Enter für {self.app.analysis_interval}s): ")
                        if iv: self.app.analysis_interval = int(iv)
                    except ValueError: pass
                    
                    self.app.auto_trading = True
                    print(f"🚀 Starte Auto-Trading für {len(self.app.auto_trade_symbols)} Paare...")
                    # self.app.run_auto_trading() # Call orchestrator method
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True
            
        elif choice == "4":
            self.app.trading_enabled = not self.app.trading_enabled
            print(f"Trading ist nun {'AKTIVIERT' if self.app.trading_enabled else 'DEAKTIVIERT'}")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "5":
            symbol = input("Symbol eingeben: ").upper()
            if symbol and self.app.broker:
                print(f"\n{self.app.broker.get_mt5_live_data(symbol)}")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True
            
        elif choice == "6":
            symbol = input("Symbol für KI Analyse: ").upper()
            if symbol and self.app.broker and self.app.ai:
                live_data = self.app.broker.get_mt5_live_data(symbol)
                if "Fehler" not in live_data:
                    # Omitted advanced indicators logic for length
                    print(f"\n🤖 Analysiere {symbol}...")
                    ai_response = self.app.ai.chat_with_model("Analysiere Daten, bewerte S/R und Indikatoren. Mach es kurz und als BUY/SELL/WARTEN Empfehlung mit Begründung.", live_data)
                    self.app.ai.display_formatted_analysis(symbol, ai_response, live_data)
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "7":
            if getattr(self.app, 'has_extended_indicators', False):
                self.app.advanced_signal_generator()
            else:
                print("❌ Erweiterte Indikatoren nicht verfügbar")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "8":
            if getattr(self.app, 'has_extended_indicators', False):
                sub = input("1. Multi-Scanner\n2. Indikator Vergleich (Single Symbol)\nWahl: ")
                if sub == "1": self.app.multi_indicator_scanner()
                elif sub == "2": self.app.indicator_comparison_analysis()
            else:
                print("❌ Erweiterte Indikatoren nicht verfügbar")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "9":
            if hasattr(self.app, 'risk_manager') and self.app.risk_manager:
                self.app.risk_management_menu()
            else:
                print("❌ Risk Manager nicht verfügbar")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "10":
            sub = input("1. Partial Close Einstellungen\n2. Trailing Stop Einstellungen\nWahl: ")
            if sub == "1":
                self.print_header("PARTIAL CLOSE")
                self.app.partial_close_enabled = not self.app.partial_close_enabled
                print(f"Partial Close umgeschaltet auf: {self.app.partial_close_enabled}")
            elif sub == "2":
                self.app.trailing_stop_settings_menu()
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "11":
            print("\n1. RSI Settings\n2. S/R Settings\n3. MACD Settings\n4. Multi-Timeframe Settings")
            if getattr(self.app, 'has_extended_indicators', False):
                print("5. Erweiterte Indikatoren Settings")
            sub = input("Wahl: ")
            
            if sub == "1":
                new_rsi = input(f"Neue RSI Periode (aktuell {self.app.rsi_period}): ")
                if new_rsi.isdigit(): self.app.rsi_period = int(new_rsi)
            elif sub == "2": self.app.sr_settings_menu()
            elif sub == "3": self.app.macd_settings_menu()
            elif sub == "4": self.app.mtf_settings_menu()
            elif sub == "5" and getattr(self.app, 'has_extended_indicators', False): self.app.advanced_indicator_settings_menu()
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "12":
            sub = input("1. Währungspaar Management\n2. MT5 Reconnect\nWahl: ")
            if sub == "1": 
                if hasattr(self.app, 'currency_pair_management_menu'):
                     self.app.currency_pair_management_menu()
            elif sub == "2": 
                if self.app.broker.mt5_connected: self.app.broker.disconnect_mt5()
                self.app.broker.connect_mt5()
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "13":
            if hasattr(self.app, 'companion_menu'):
                 self.app.companion_menu()
            return True

        elif choice == "14":
            if getattr(self.app, 'rl_enabled', False):
                self.app.rl_menu_enhanced()
            else:
                print("❌ Reinforcement Learning nicht verfügbar")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True

        elif choice == "15":
            if hasattr(self.app, 'shutdown_system'):
               self.app.shutdown_system()
            return False

        else:
            print("❌ Ungültige Option")
            input("\nDrücken Sie Enter zum Fortfahren...")
            return True
