# ==========================================
# 1. IMPORTS & INITIALIZATION
# ==========================================
#!/usr/bin/env python3
"""
FinGPT mit Ollama + MetaTrader 5 Integration
Vollautomatisches Trading mit KI und Partial Close + RSI
"""

# type: ignore[attr-defined, reportPossiblyUnboundVariable, reportOptionalMemberAccess, reportAttributeAccessIssue]
import logging
import requests
import json
import sys
import time
from datetime import datetime
import subprocess
import re
import threading
import os
import signal
import queue
import warnings
warnings.filterwarnings("ignore")

# Set UTF-8 encoding for stdout/stderr (Python 3.7+)
import io
try:
    # Use TextIOWrapper directly to avoid Pylance type issues
    if sys.stdout.encoding != 'utf-8' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass  # Older Python or unsupported environment

try:
    if sys.stderr.encoding != 'utf-8' and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

# MetaTrader 5 Import
try:
    import MetaTrader5 as mt5  # type: ignore[attr-defined, assignment]
    MT5_AVAILABLE = True
    print("MetaTrader5 verfügbar")
except ImportError:
    import typing
    mt5 = typing.cast(typing.Any, None)  # type: ignore[assignment]
    MT5_AVAILABLE = False
    print("MetaTrader5 nicht installiert")

# Import core modules
from trading.risk_manager import RiskManager
from trading.advanced_indicators import AdvancedIndicators, IndicatorIntegration
from trading.rl_trading_agent import RLTradingManager
from core.mt5_broker import MT5Broker
from core.ai_analyzer import AIAnalyzer
from core.market_analyzer import MarketAnalyzer
from core.exception_handler import ErrorHandler
from core.performance_optimizer import PerformanceMetrics, ResourceLimiter
from gui.cli_menu import CLIMenu

class MT5FinGPT:
    # Type annotations for Pylance to recognize instance attributes
    rl_manager: 'RLTradingManager | None' = None
    risk_manager: 'RiskManager | None' = None
    broker: 'MT5Broker'
    ai: 'AIAnalyzer | None' = None
    market: 'MarketAnalyzer | None' = None
    ui_lock: 'threading.Lock'
    
    def __init__(self):
        """Initialisiert das FinGPT System mit korrekter Reihenfolge"""
    
        # GRUNDLEGENDE EINSTELLUNGEN ZUERST
        self.default_lot_size = 0.5
        self.max_risk_percent = 2.0
        self.auto_trading = True
        self.auto_trade_symbols = ["EURUSD"]
        self.analysis_interval = 300
    
        # LOGGING SETUP - MUSS ZUERST KOMMEN!
        self.setup_logging()
        self.log("INFO", "FinGPT System wird initialisiert...")

        # INITIALIZE CORE MODULES
        self.log("DEBUG", "Initialisiere MT5Broker, AIAnalyzer, MarketAnalyzer...", "SYSTEM")
        self.broker = MT5Broker(logger=self.logger)
        self.ai = AIAnalyzer(logger=self.logger)
        self.market = MarketAnalyzer(broker=self.broker, logger=self.logger)
        self.cli = CLIMenu(main_app=self, logger=self.logger)
        
        # Backward compatibility for existing code that checks these flags
        self.mt5_connected = False # Managed by broker mostly now
        self.selected_model = "gpt-oss:120b-cloud" # Default wie gewünscht
        
        # Sync the manual model to AI
        if self.ai:
            self.ai.selected_model = self.selected_model

        # ENHANCED MODE FLAG
        self.enhanced_mode = True  # Enhanced modules are available

        # ERROR HANDLER
        try:
            self.error_handler = ErrorHandler(logger=self.logger)
            self.log("INFO", "✅ Error Handler erfolgreich initialisiert", "SYSTEM")
        except Exception as e:
            self.log("ERROR", f"Error Handler Initialisierung Fehler: {e}", "SYSTEM")
            self.error_handler = None

        # PERFORMANCE METRICS & RESOURCE LIMITER
        try:
            self.performance_metrics = PerformanceMetrics()
            self.resource_limiter = ResourceLimiter()
            self.log("INFO", "✅ Performance Monitoring erfolgreich initialisiert", "SYSTEM")
        except Exception as e:
            self.log("ERROR", f"Performance Monitoring Initialisierung Fehler: {e}", "SYSTEM")
            self.performance_metrics = None
            self.resource_limiter = None

        # TRADING COMPANION INTEGRATION
        self.companion_process = None
        self.companion_enabled = False
        self.auto_start_companion = True  # Companion automatisch beim Start aktivieren

        # TIMEFRAME NAMES
        self.timeframe_names = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5", 
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1"
        } if MT5_AVAILABLE else {}

        # RISK MANAGER - NACH LOGGING!
        try:
            self.risk_manager = RiskManager(logger=self.logger)
            self.log("INFO", "Risk Manager erfolgreich initialisiert", "RISK")
        except Exception as e:
            self.log("ERROR", f"Risk Manager Initialisierung Fehler: {e}", "RISK")
            self.risk_manager = None
    
        # ERWEITERTE INDIKATOREN - NACH LOGGING!
        try:
            self.advanced_indicators = AdvancedIndicators(logger=self.logger)
            self.integration = IndicatorIntegration(self)
            self.log("INFO", "✅ Erweiterte Indikatoren erfolgreich initialisiert", "INDICATORS")
            self.has_extended_indicators = True
        except Exception as e:
            self.log("WARNING", f"Erweiterte Indikatoren nicht verfügbar: {e}", "INDICATORS")
            self.advanced_indicators = None
            self.integration = None
            self.has_extended_indicators = False
    
        # RSI SETTINGS (mapped to market analyzer context)
        self.rsi_period = self.market.rsi_period
        self.rsi_timeframe = mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None
        self.rsi_overbought = self.market.rsi_overbought
        self.rsi_oversold = self.market.rsi_oversold
    
        # SUPPORT/RESISTANCE SETTINGS
        self.sr_lookback_period = self.market.sr_lookback_period
        self.sr_min_touches = 2
        self.sr_tolerance = self.market.sr_tolerance
        self.sr_strength_threshold = self.market.sr_strength_threshold
    

        # MACD SETTINGS
        self.macd_fast_period = 12
        self.macd_slow_period = 26
        self.macd_signal_period = 9
        self.macd_timeframe = mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None
    
        # MULTI-TIMEFRAME SETTINGS
        self.mtf_enabled = True
        self.trend_timeframe = mt5.TIMEFRAME_H1 if MT5_AVAILABLE else None
        self.entry_timeframe = mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None
        self.trend_ema_period = self.market.trend_ema_period
        self.trend_strength_threshold = self.market.trend_strength_threshold
        self.require_trend_confirmation = True
    
        # PARTIAL CLOSE SETTINGS
        self.partial_close_enabled = True
        self.first_target_percent = 50
        self.second_target_percent = 25
        self.profit_target_1 = 1.5
        self.profit_target_2 = 3.0
    
        # UI VERBESSERUNGEN
        self.companion_output_queue = queue.Queue()
        self.ui_lock = threading.Lock()
        self.companion_silent_mode = False
        self.last_menu_display = 0
    
        # TRAILING STOP SETTINGS
        self.trailing_stop_enabled = True
        self.trailing_stop_distance_pips = 20
        self.trailing_stop_step_pips = 5
        self.trailing_stop_start_profit_pips = 15

        self.trading_enabled = True

        # RL INTEGRATION - NACH LOGGING!
        try:
            self.rl_manager = RLTradingManager(self)
            self.rl_enabled = True
            self.log("INFO", "✅ RL Manager erfolgreich initialisiert", "RL")
        except Exception as e:
            self.log("WARNING", f"RL Manager nicht verfügbar: {e}", "RL")
            self.rl_manager = None
            self.rl_enabled = False

        # RL SETTINGS (Basic)
        self.rl_training_mode = False
        self.rl_recommendation_weight = 0.3  # Gewichtung der RL-Empfehlung (30%)

        # RL HYPERPARAMETER (GUI-Parität: config_tab.py → Reinforcement Learning Tab)
        self.rl_algorithm = "PPO"               # PPO | DQN | A2C | SAC
        self.rl_learning_rate = 0.0003
        self.rl_gamma = 0.99                    # Discount-Faktor
        self.rl_training_steps = 100000
        self.rl_reward_function = "Profit + Sharpe Ratio"  # Belohnungsfunktion
        self.rl_buffer_size = 10000             # Replay Buffer Size
        self.rl_batch_size = 64
        self.rl_epochs = 10                     # Epochs (PPO)
        self.rl_target_update = 1000            # Target Update Frequenz (DQN)
        self.rl_epsilon_start = 1.0
        self.rl_epsilon_min = 0.01
        self.rl_epsilon_decay = 0.995
        self.rl_training_timeframe = "M15"      # Training-Zeitrahmen
        self.rl_training_bars = 5000            # Anzahl der Datenpunkte
        self.rl_nn_architecture = "Mittel (128-128)"  # Klein | Mittel | Groß
        self.rl_checkpoint_path = "storage/rl_agents/model.zip"
        self.rl_live_trading_enabled = False    # RL für Live-Trading (Experimentell)
        self.rl_use_gpu = True                  # GPU-Beschleunigung

        # Lade Konfiguration (GUI-Parität)
        from core.app_config import app_config_manager
        self.app_config = app_config_manager.load()
        
        # Backward compatibility for model and intervals
        self.selected_model = self.app_config.llm_model
        self.auto_trade_interval = self.app_config.interval
        
        # ABSCHLUSS UND STATUS
        self.log("INFO", "FinGPT System mit Core Modulen initialisiert")
    
        # STATUS CHECKS
        if self.risk_manager:
            self.log("INFO", "✅ Risk Manager ist verfügbar", "STATUS")
        else:
            self.log("WARNING", "❌ Risk Manager ist NICHT verfügbar", "STATUS")
    
        if self.has_extended_indicators:
            self.log("INFO", "✅ Erweiterte Indikatoren verfügbar", "STATUS")
        else:
            self.log("INFO", "📊 Basis-Indikatoren verfügbar (RSI, MACD, S/R)", "STATUS")
    
        if self.rl_enabled:
            self.log("INFO", "✅ RL Trading Agent verfügbar", "STATUS")
        else:
            self.log("INFO", "📈 Standard Trading Logik aktiv", "STATUS")
       
    # ==========================================
    # 2. LOGGING & UI HELPERS
    # ==========================================
    def calculate_support_resistance(self, symbol, timeframe=None):
        """Berechnet Support und Resistance Level und gibt sie im erwarteten Format zurück.
        
        Args:
            symbol: Das Handelssymbol (z.B. 'EURUSD')
            timeframe: Optionaler Zeitrahmen. Standard ist H1.
            
        Returns:
            Dictionary mit 'nearest_support' und 'nearest_resistance' als Tupel (level, strength)
            oder None wenn keine Daten verfügbar sind.
        """
        if not hasattr(self, 'market') or not self.market:
            return None
            
        try:
            import MetaTrader5 as mt5
            tf = timeframe if timeframe else (mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            
            sr_data = self.market.calculate_support_resistance(symbol, tf)
            
            if not sr_data:
                return None
            
            # Konvertiere zum erwarteten Format
            result = {}
            
            # Nearest Support - nähester Support unter dem aktuellen Preis
            if sr_data.get('support_levels') and len(sr_data['support_levels']) > 0:
                nearest = sr_data['support_levels'][0]
                result['nearest_support'] = (nearest['price'], nearest['strength'])
            else:
                result['nearest_support'] = None
            
            # Nearest Resistance - nähester Resistance über dem aktuellen Preis  
            if sr_data.get('resistance_levels') and len(sr_data['resistance_levels']) > 0:
                nearest = sr_data['resistance_levels'][0]
                result['nearest_resistance'] = (nearest['price'], nearest['strength'])
            else:
                result['nearest_resistance'] = None
            
            # Auch die vollständigen Daten hinzufügen für Kompatibilität
            result['current_price'] = sr_data.get('current_price')
            result['support_levels'] = sr_data.get('support_levels', [])
            result['resistance_levels'] = sr_data.get('resistance_levels', [])
            
            return result
            
        except Exception as e:
            self.log("ERROR", f"calculate_support_resistance Fehler: {e}") if hasattr(self, 'log') else print(f"Fehler: {e}")
            return None
    
    def get_sr_signal(self, sr_data, current_price):
        """Generiert ein Signal basierend auf S/R Levels.
        
        Args:
            sr_data: Dictionary mit S/R Daten von calculate_support_resistance
            current_price: Aktueller Preis
            
        Returns:
            Tuple (signal, description) - signal ist 'BUY', 'SELL' oder 'NEUTRAL'
        """
        if not sr_data or not current_price:
            return "NEUTRAL", "Keine S/R Daten verfügbar"
            
        try:
            # nearest_support und nearest_resistance sind jetzt Tupel (price, strength)
            nearest_resistance = sr_data.get('nearest_resistance')
            nearest_support = sr_data.get('nearest_support')
            
            # DEBUG: Log to validate diagnosis
            self.log("DEBUG", f"nearest_resistance: {nearest_resistance}, nearest_support: {nearest_support}") if hasattr(self, 'log') else None
            
            if nearest_resistance:
                res_price = nearest_resistance[0]
                res_strength = nearest_resistance[1]
                # Distanz in Prozent
                dist_to_res = (res_price - current_price) / current_price * 100
            else:
                dist_to_res = float('inf')
                res_strength = 0
                res_price = current_price  # DEBUG FIX: Initialize to avoid unbound variable
            
            if nearest_support:
                sup_price = nearest_support[0]
                sup_strength = nearest_support[1]
                # Distanz in Prozent
                dist_to_sup = (current_price - sup_price) / current_price * 100
            else:
                dist_to_sup = float('inf')
                sup_strength = 0
                sup_price = current_price  # DEBUG FIX: Initialize to avoid unbound variable
            
            # Signal basierend auf Preisnähe und Stärke
            if dist_to_res < 1.0 and res_strength >= 2:
                return "SELL", f"Preis nahe Resistance ({res_price:.5f}, Stärke: {res_strength})"
            elif dist_to_sup < 1.0 and sup_strength >= 2:
                return "BUY", f"Preis nahe Support ({sup_price:.5f}, Stärke: {sup_strength})"
            elif dist_to_res < 2.0:
                return "NEUTRAL", f"Nahe Resistance ({res_price:.5f})"
            elif dist_to_sup < 2.0:
                return "NEUTRAL", f"Nahe Support ({sup_price:.5f})"
            else:
                return "NEUTRAL", "Kein S/R Signal"
                
        except Exception as e:
            return "NEUTRAL", f"S/R Signal Fehler: {e}"

    def setup_logging(self):
        """Richtet das Logging-System ein"""
        try:
            # Erstelle logs Ordner falls nicht vorhanden
            if not os.path.exists("logs"):
                os.makedirs("logs")
            
            # Log-Datei mit Datum
            log_filename = f"logs/fingpt_{datetime.now().strftime('%Y%m%d')}.log"
            
            # Logging Konfiguration
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s | %(levelname)s | %(message)s',
                handlers=[
                    logging.FileHandler(log_filename, encoding='utf-8'),
                    logging.StreamHandler()  # Auch in Konsole ausgeben
                ]
            )
            
            self.logger = logging.getLogger('FinGPT')
            
        except Exception as e:
            print(f"Logging Setup Fehler: {e}")
            self.logger = None
    
    def log(self, level, message, category="SYSTEM"):
        """
        Universelle Logging-Funktion
        
        Args:
            level: INFO, WARNING, ERROR, DEBUG, TRADE
            message: Log-Nachricht
            category: Kategorie (SYSTEM, TRADE, MT5, AI, etc.)
        """
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{category}] {message}"
            
            # Konsolen-Output mit Icons
            icons = {
                "INFO": "ℹ️",
                "WARNING": "⚠️", 
                "ERROR": "❌",
                "DEBUG": "🔍",
                "TRADE": "💰",
                "MT5": "📊",
                "AI": "🤖",
                "COMPANION": "🔧"
            }
            
            icon = icons.get(level, "📝")
            print(f"{timestamp} {icon} {formatted_message}")
            
            # In Datei loggen
            if self.logger:
                if level == "ERROR":
                    self.logger.error(formatted_message)
                elif level == "WARNING":
                    self.logger.warning(formatted_message)
                elif level == "DEBUG":
                    self.logger.debug(formatted_message)
                else:
                    self.logger.info(formatted_message)
                    
        except Exception as e:
            print(f"Logging Fehler: {e}")
    
    def log_trade(self, symbol, action, result, reasoning="", confidence="", indicators=None, lot_size=0.0, profit=0.0, ticket=0):
        """Spezielle Logging-Funktion für Trades — schreibt auch ins Trade Journal."""
        if ticket == 0 and isinstance(result, str) and "Ticket:" in result:
            import re
            m = re.search(r"Ticket:\s*(\d+)", result)
            if m:
                ticket = int(m.group(1))

        display_result = result.split('\n')[0] if isinstance(result, str) else result
        trade_info = f"{action} {symbol} - {display_result}"
        if reasoning:
            trade_info += f" | Grund: {reasoning}"
        self.log("TRADE", trade_info, "TRADE")
        
        # Write to Trade Journal JSON
        try:
            import json, os
            journal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "trade_journal")
            os.makedirs(journal_dir, exist_ok=True)
            
            now = datetime.now()
            entry = {
                "ticket": ticket or int(now.timestamp()),
                "symbol": symbol,
                "action": action,
                "result": result,
                "open_time": now.isoformat(),
                "close_time": None,
                "lot_size": lot_size,
                "profit": profit,
                "ai_reasoning": reasoning,
                "ai_confidence": confidence,
                "indicators_used": indicators or [],
                "tags": []
            }
            
            fname = f"{entry['ticket']}_{symbol}_{now.strftime('%Y%m%d')}.json"
            fpath = os.path.join(journal_dir, fname)
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
        except Exception as je:
            self.log("DEBUG", f"Journal write error: {je}", "SYSTEM")
    
    def log_error(self, function_name, error, details=""):
        """Spezielle Logging-Funktion für Fehler"""
        error_info = f"Fehler in {function_name}: {error}"
        if details:
            error_info += f" | Details: {details}"
        self.log("ERROR", error_info, "ERROR")
    
    def log_ai_analysis(self, symbol, recommendation, confidence=""):
        """Spezielle Logging-Funktion für AI-Analysen"""
        ai_info = f"AI-Analyse {symbol}: {recommendation}"
        if confidence:
            ai_info += f" | Konfidenz: {confidence}"
        self.log("AI", ai_info, "AI")
    
    def log_debug_menu(self, choice, function_called):
        """Debug-Logging für Menü-Aufrufe"""
        self.log("DEBUG", f"Menü Option '{choice}' -> {function_called}", "MENU")

    def print_header(self, title, width=55):
        """Schöne Header-Darstellung"""
        print("\n" + "═" * width)
        print(f"{title:^{width}}")
        print("═" * width)
    
    def print_status_bar_extended(self):
        """Erweiterte Status-Leiste mit allen Features"""
        with self.ui_lock:
            # Risk Manager Status
            risk_status = "❌"
            if hasattr(self, 'risk_manager') and self.risk_manager:
                try:
                    summary = self.risk_manager.get_risk_summary()
                    if summary is not None:
                        risk_status = "✅"
                        daily_pnl = summary.get('daily_pnl', 0)
                        if hasattr(self.risk_manager, 'max_daily_loss'):
                            if daily_pnl <= self.risk_manager.max_daily_loss * 0.8:
                                risk_status = "🟡"
                            elif daily_pnl <= self.risk_manager.max_daily_loss:
                                risk_status = "🔴"
                except:
                    risk_status = "⚠️"
        
            # Erweiterte Indikatoren Status
            indicators_status = "✅" if getattr(self, 'has_extended_indicators', False) else "❌"
            indicators_count = "7+" if getattr(self, 'has_extended_indicators', False) else "3"
        
            # RL Status
            rl_status = "✅" if getattr(self, 'rl_enabled', False) else "❌"
        
            # Integration Status
            integration_status = "✅" if getattr(self, 'integration', None) else "❌"
    
            status_items = [
                f"📱 MT5: {'✅' if self.mt5_connected else '❌'}",
                f"🤖 KI: {'✅' if self.selected_model else '❌'}",
                f"💰 Trading: {'✅' if self.trading_enabled else '❌'}",
                f"🔄 Auto: {'✅' if self.auto_trading else '❌'}",
                f"🛡️ Risk: {risk_status}",
                f"📊 Indicators: {indicators_status}({indicators_count})",
                f"🤖 RL: {rl_status}",
                f"🔧 Companion: {'✅' if self.companion_enabled else '❌'}"
            ]
    
            print("\n┌" + "─" * 85 + "┐")
            print(f"│ {' | '.join(status_items):<83} │")
            print("└" + "─" * 85 + "┘")
    
    def start_trading_companion(self):
        """Startet das Trading Companion Script mit verbesserter UI"""
        try:
            import os
            companion_script = os.path.join("trading", "trading_companion.py")
            
            if self.companion_enabled or self.companion_process:
                print("🔧 Trading Companion läuft bereits")
                return True
                
            if not os.path.exists(companion_script):
                print(f"❌ Trading Companion Script nicht gefunden: {companion_script}")
                return False
                
            # Starte mit verbessertem Output-Handling und UTF-8 Encoding
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                
                self.companion_process = subprocess.Popen(
                    [sys.executable, companion_script, "--daemon"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    env=env
                )
                
                time.sleep(0.5)
                if self.companion_process.poll() is not None:
                    print("❌ Trading Companion konnte nicht gestartet werden")
                    return False
                    
                print("✅ Trading Companion erfolgreich gestartet")
                self.companion_enabled = True
                
                # Verbesserter Monitor Thread
                def monitor_companion():
                    startup_complete = False
                    while self.companion_process and self.companion_enabled:
                        try:
                            if self.companion_process.poll() is not None:
                                break
                                
                            output = self.companion_process.stdout.readline()  # type: ignore[union-attr]
                            if output:
                                output = output.strip()
                                
                                # Filtere und formatiere Output
                                if not startup_complete:
                                    if "Trading Companion gestartet" in output:
                                        startup_complete = True
                                        with self.ui_lock:
                                            print("🔧 Companion: Bereit für erweiterte Analyse")
                                    elif "Datenverbindung OK" in output:
                                        continue  # Unterdrücke redundante Meldungen
                                else:
                                    # Nach Startup nur wichtige Meldungen zeigen
                                    if not self.companion_silent_mode:
                                        if any(keyword in output for keyword in [
                                            "ANALYSE", "EMPFEHLUNG", "ERROR", "Fehler"
                                        ]):
                                            with self.ui_lock:
                                                print(f"🔧 Companion: {output}")
                                
                        except Exception as e:
                            break
                            
                    with self.ui_lock:
                        print("🔧 Trading Companion Monitor beendet")
                    self.companion_enabled = False
                    self.companion_process = None
                
                companion_thread = threading.Thread(
                    target=monitor_companion,
                    daemon=True,
                    name="CompanionMonitor"
                )
                companion_thread.start()
                
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Starten des Trading Companions: {e}")
                self.companion_process = None
                self.companion_enabled = False
                return False
                
        except Exception as e:
            print(f"❌ Trading Companion Setup Fehler: {e}")
            return False
    
    # ==========================================
    # 3. INTERACTIVE CLI MENU (Moved to gui/cli_menu.py)
    # ==========================================

    # ==========================================
    # 3b. GLOBAL CONFIG MENUS (GUI-Parität)
    # ==========================================

    def ai_ki_settings_menu(self):
        """KI & Ollama Einstellungen — Parität mit GUI config_tab.py → KI & Ollama Tab"""
        from core.app_config import app_config_manager
        while True:
            self.print_header("🤖 KI & OLLAMA EINSTELLUNGEN")

            print("📌 AKTUELLE KONFIGURATION:")
            print("─" * 48)
            print(f"   KI Provider           : {self.app_config.ki_provider}")
            print(f"   Ollama URL            : {self.app_config.ollama_url}")
            
            # Show the key depending on the provider
            if "OpenAI" in self.app_config.ki_provider:
                active_key = self.app_config.api_key_openai or self.app_config.api_key
            elif "Anthropic" in self.app_config.ki_provider:
                active_key = self.app_config.api_key_anthropic or self.app_config.api_key
            elif "DeepSeek" in self.app_config.ki_provider:
                active_key = self.app_config.api_key_deepseek or self.app_config.api_key
            elif "OpenRouter" in self.app_config.ki_provider:
                active_key = self.app_config.api_key_openrouter or self.app_config.api_key
            else:
                active_key = self.app_config.api_key

            print(f"   API Key               : {'*****' if active_key else '(leer)'}")
            print(f"   LLM Modell            : {self.app_config.llm_model}")
            print(f"   Intervall (Auto-Trade): {self.app_config.interval}s")
            print(f"   Temperatur            : {self.app_config.ai_temperature:.1f}")
            print(f"   Max. Tokens           : {self.app_config.llm_max_tokens}")
            print(f"   Prompt-Sprache        : {self.app_config.prompt_lang}")
            print(f"   Min. Confidence       : {self.app_config.min_confidence}%")
            print(f"   System Prompt         : {self.app_config.system_prompt[:60]}...")

            print("\n🛠️  EDITIEROPTIONEN:")
            print("─" * 48)
            print("  1. 🤖 KI Provider (Ollama / OpenAI / Anthropic / DeepSeek / OpenRouter)")
            print("  2. 🌐 Ollama / Base URL")
            print("  3. 🔑 API Key (für aktuellen Provider)")
            print("  4. 🤖 LLM Modell (free text)")
            print("  5. ⏱️  Auto-Trading Intervall (Sekunden)")
            print("  6. 🌡️  KI Temperatur (0.0–1.0)")
            print("  7. 📝 Max. Tokens")
            print("  8. 🌍 Prompt-Sprache")
            print("  9. 🔒 Min. Confidence (%)")
            print(" 10. 📜 System Prompt bearbeiten")
            print(" 11. 🔄 Ollama Modelle abrufen (Test)")
            print("  0. ⬅️  Zurück")

            choice = input("\n🎯 Ihre Wahl (0-11): ").strip()

            if choice == "0":
                break

            elif choice == "1":
                providers = ["Ollama (Lokal)", "OpenAI (ChatGPT)", "Anthropic (Claude)", "DeepSeek", "OpenRouter"]
                for i, p in enumerate(providers, 1):
                    print(f"  {i}. {p}")
                try:
                    idx = int(input(f"Wahl (1-{len(providers)}): ")) - 1
                    if 0 <= idx < len(providers):
                        self.app_config.ki_provider = providers[idx]
                        app_config_manager.save()
                        print(f"✅ KI Provider → {self.app_config.ki_provider}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "2":
                val = input(f"Ollama / Base URL (aktuell: {self.app_config.ollama_url}): ").strip()
                if val:
                    self.app_config.ollama_url = val
                    app_config_manager.save()
                    print(f"✅ URL → {self.app_config.ollama_url}")

            elif choice == "3":
                val = input(f"API Key für {self.app_config.ki_provider} (leer = unverändert): ").strip()
                if val:
                    if "OpenAI" in self.app_config.ki_provider:
                        self.app_config.api_key_openai = val
                    elif "Anthropic" in self.app_config.ki_provider:
                        self.app_config.api_key_anthropic = val
                    elif "DeepSeek" in self.app_config.ki_provider:
                        self.app_config.api_key_deepseek = val
                    elif "OpenRouter" in self.app_config.ki_provider:
                        self.app_config.api_key_openrouter = val
                    else:
                        self.app_config.api_key = val
                    app_config_manager.save()
                    print("✅ API Key gespeichert")

            elif choice == "4":
                val = input(f"LLM Modell (aktuell: {self.app_config.llm_model or '(keins)'}): ").strip()
                if val:
                    self.app_config.llm_model = val
                    self.selected_model = val
                    if hasattr(self, 'ai'):
                        self.ai.selected_model = val
                    app_config_manager.save()
                    print(f"✅ Modell → {self.app_config.llm_model}")

            elif choice == "5":
                try:
                    val = int(input(f"Intervall in Sekunden (aktuell: {self.app_config.interval}, 1–120): "))
                    if 1 <= val <= 120:
                        self.app_config.interval = val
                        self.auto_trade_interval = val
                        self.analysis_interval = val
                        app_config_manager.save()
                        print(f"✅ Intervall → {self.app_config.interval}s")
                    else:
                        print("❌ Bereich: 1–120")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "6":
                try:
                    val = float(input(f"Temperatur (aktuell: {self.app_config.ai_temperature:.1f}, 0.0–1.0): "))
                    if 0.0 <= val <= 1.0:
                        self.app_config.ai_temperature = val
                        app_config_manager.save()
                        print(f"✅ Temperatur → {self.app_config.ai_temperature:.1f}")
                    else:
                        print("❌ Bereich: 0.0–1.0")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "7":
                try:
                    val = int(input(f"Max. Tokens (aktuell: {self.app_config.llm_max_tokens}, 100–4096): "))
                    if 100 <= val <= 4096:
                        self.app_config.llm_max_tokens = val
                        app_config_manager.save()
                        print(f"✅ Max. Tokens → {self.app_config.llm_max_tokens}")
                    else:
                        print("❌ Bereich: 100–4096")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "8":
                langs = ["Deutsch", "Englisch", "Gemischt"]
                print("Optionen:", " | ".join(f"{i+1}. {l}" for i, l in enumerate(langs)))
                try:
                    idx = int(input("Wahl (1-3): ")) - 1
                    if 0 <= idx < len(langs):
                        self.app_config.prompt_lang = langs[idx]
                        app_config_manager.save()
                        print(f"✅ Sprache → {self.app_config.prompt_lang}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "9":
                try:
                    val = int(input(f"Min. Confidence % (aktuell: {self.app_config.min_confidence}, 50–100): "))
                    if 50 <= val <= 100:
                        self.app_config.min_confidence = val
                        app_config_manager.save()
                        print(f"✅ Min. Confidence → {self.app_config.min_confidence}%")
                    else:
                        print("❌ Bereich: 50–100")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "10":
                print(f"\nAktueller System Prompt:\n{self.app_config.system_prompt}\n")
                print("Neuen Prompt eingeben (leer lassen = unverändert):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                if lines:
                    self.app_config.system_prompt = " ".join(lines)
                    app_config_manager.save()
                    print("✅ System Prompt aktualisiert")

            elif choice == "11":
                print(f"🔄 Teste Verbindung zu {self.app_config.ollama_url}...")
                try:
                    import requests
                    resp = requests.get(f"{self.app_config.ollama_url}/api/tags", timeout=5)
                    if resp.status_code == 200:
                        models = [m['name'] for m in resp.json().get('models', [])]
                        print(f"✅ Verbunden! {len(models)} Modell(e) gefunden:")
                        for m in models:
                            print(f"   - {m}")
                    else:
                        print(f"❌ HTTP {resp.status_code}")
                except Exception as e:
                    print(f"❌ Verbindung fehlgeschlagen: {e}")
            else:
                print("❌ Ungültige Auswahl")

            input("\nDrücken Sie Enter zum Fortfahren...")

    def trading_style_settings_menu(self):
        """Trading Stil, AI-Fulldrive, Sessions, Nachrichten-Filter, Ausführungsqualität"""
        from core.app_config import app_config_manager
        while True:
            self.print_header("📊 TRADING STIL & AUSFÜHRUNG")

            print("📌 AKTUELLE KONFIGURATION:")
            print("─" * 48)
            print(f"   Trading Style         : {self.app_config.trading_style}")
            print(f"   Signal-Strategie      : {self.app_config.signal_strategy}")
            print(f"   Risikoprofil          : {self.app_config.risk_profile}")
            print(f"   Max Risiko/Trade      : {self.app_config.max_risk}%")
            print(f"   Max Daily Loss        : {self.app_config.max_daily_loss}%")
            print(f"   Max offene Positionen : {self.app_config.max_positions}")
            print(f"   Trailing Stop         : {'✅' if self.app_config.trailing_stop else '❌'} | {self.app_config.trailing_dist}p Abstand")
            print(f"   Break-Even Stop       : {'✅' if self.app_config.break_even else '❌'} | {self.app_config.break_even_dist}p")
            print(f"   Wochenend-Schutz      : {'✅' if self.app_config.weekend_exit else '❌'}")
            print(f"   RM Max. Tagesverlust  : {self.app_config.rm_max_daily_loss_eur}€")
            print(f"   RM Max. Wochenverlust : {self.app_config.rm_max_weekly_loss_eur}€")
            print(f"   RM Cooldown           : {self.app_config.rm_min_time_between_trades}s")
            print(f"   RM Max Trades/Tag     : {self.app_config.rm_max_trades_per_day}")
            print(f"   Sessions              : {'London ' if self.app_config.session_london else ''}{'NY ' if self.app_config.session_ny else ''}{'Asia' if self.app_config.session_asia else ''}")
            print(f"   Aktive Tage           : {'Mo ' if self.app_config.day_mon else ''}{'Di ' if self.app_config.day_tue else ''}{'Mi ' if self.app_config.day_wed else ''}{'Do ' if self.app_config.day_thu else ''}{'Fr ' if self.app_config.day_fri else ''}{'Sa ' if self.app_config.day_sat else ''}{'So ' if self.app_config.day_sun else ''}")
            print(f"   Handelsfenster        : {self.app_config.trade_time_from}–{self.app_config.trade_time_to} UTC ({'✅' if self.app_config.time_filter else '❌'})")
            print(f"   News-Filter           : {'✅' if self.app_config.news_filter else '❌'}")
            print(f"   Max Spread            : {self.app_config.max_spread}p | Max Slippage: {self.app_config.max_slippage}p")
            print(f"   Debug-Modus           : {'✅' if self.app_config.debug_mode else '❌'}")
            
            if "Fulldrive" in self.app_config.trading_style:
                print(f"\n   🚀 AI-FULLDRIVE (Nur via GUI einstellbar)")

            print("\n🛠️  EDITIEROPTIONEN:")
            print("─" * 48)
            print("  1. 📊 Trading Style")
            print("  2. 🎯 Signal-Strategie")
            print("  3. 🛡️  Risikoprofil")
            print("  4. 💸 Max Risiko/Trade & Max Daily Loss %")
            print("  5. 📦 Max. offene Positionen")
            print("  6. 🎢 Trailing Stop Einstellungen")
            print("  7. ✋ Break-Even Stop Einstellungen")
            print("  8. 📅 Wochenend-Schutz umschalten")
            print("  9. 🛡️  Risk Manager Limits (€)")
            print(" 10. ⏰ Handelssitzungen & Zeitfenster")
            print(" 11. 📰 Nachrichten-Filter")
            print(" 12. ⚡ Spread & Slippage Limits")
            print(" 13. 🗓️  Aktive Handelstage (Mo-So)")
            print(" 14. 🐛 Debug-Modus umschalten")
            print("  0. ⬅️  Zurück")

            choice = input("\n🎯 Ihre Wahl (0-14): ").strip()

            if choice == "0":
                break

            elif choice == "1":
                styles = ["Scalping", "Day Trading", "Swing Trading", "Position Trading",
                          "Price Action", "Breakout-Trading", "Mean Reversion", "AI-Fulldrive Mode 🤖"]
                for i, s in enumerate(styles, 1):
                    print(f"  {i}. {s}")
                try:
                    idx = int(input("Wahl: ")) - 1
                    if 0 <= idx < len(styles):
                        self.app_config.trading_style = styles[idx]
                        app_config_manager.save()
                        print(f"✅ Trading Style → {self.app_config.trading_style}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "2":
                strategies = ["KI-gesteuert (Ollama)", "Technische Indikatoren", "Hybrid (KI + Indikatoren)"]
                for i, s in enumerate(strategies, 1):
                    print(f"  {i}. {s}")
                try:
                    idx = int(input("Wahl: ")) - 1
                    if 0 <= idx < len(strategies):
                        self.app_config.signal_strategy = strategies[idx]
                        app_config_manager.save()
                        print(f"✅ Signal-Strategie → {self.app_config.signal_strategy}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "3":
                profiles = ["Konservativ", "Moderat", "Aggressiv"]
                for i, p in enumerate(profiles, 1):
                    print(f"  {i}. {p}")
                try:
                    idx = int(input("Wahl: ")) - 1
                    if 0 <= idx < len(profiles):
                        self.app_config.risk_profile = profiles[idx]
                        app_config_manager.save()
                        print(f"✅ Risikoprofil → {self.app_config.risk_profile}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "4":
                try:
                    rt = float(input(f"Max Risiko/Trade % (aktuell {self.app_config.max_risk}): ") or self.app_config.max_risk)
                    dl = float(input(f"Max Daily Loss % (aktuell {self.app_config.max_daily_loss}): ") or self.app_config.max_daily_loss)
                    if 0.1 <= rt <= 10 and 0.5 <= dl <= 20:
                        self.app_config.max_risk = str(rt)
                        self.app_config.max_daily_loss = str(dl)
                        app_config_manager.save()
                        print(f"✅ Risiko/Trade={rt}% | Daily Loss={dl}%")
                    else:
                        print("❌ Außerhalb des gültigen Bereichs")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "5":
                try:
                    val = int(input(f"Max. Positionen (aktuell {self.app_config.max_positions}): ") or self.app_config.max_positions)
                    if 1 <= val <= 20:
                        self.app_config.max_positions = str(val)
                        app_config_manager.save()
                        print(f"✅ Max. Positionen → {self.app_config.max_positions}")
                    else:
                        print("❌ Bereich: 1–20")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "6":
                self.app_config.trailing_stop = not self.app_config.trailing_stop
                app_config_manager.save()
                print(f"✅ Trailing Stop → {'aktiviert' if self.app_config.trailing_stop else 'deaktiviert'}")
                if self.app_config.trailing_stop:
                    try:
                        dist = int(input(f"Trailing Abstand Pips (aktuell {self.app_config.trailing_dist}): ") or self.app_config.trailing_dist)
                        self.app_config.trailing_dist = str(max(1, dist))
                        app_config_manager.save()
                        print(f"✅ Trailing Abstand → {self.app_config.trailing_dist}p")
                    except ValueError:
                        pass

            elif choice == "7":
                self.app_config.break_even = not self.app_config.break_even
                app_config_manager.save()
                print(f"✅ Break-Even Stop → {'aktiviert' if self.app_config.break_even else 'deaktiviert'}")
                if self.app_config.break_even:
                    try:
                        dist = int(input(f"Break-Even Abstand Pips (aktuell {self.app_config.break_even_dist}): ") or self.app_config.break_even_dist)
                        self.app_config.break_even_dist = str(max(1, dist))
                        app_config_manager.save()
                        print(f"✅ Break-Even Abstand → {self.app_config.break_even_dist}p")
                    except ValueError:
                        pass

            elif choice == "8":
                self.app_config.weekend_exit = not self.app_config.weekend_exit
                app_config_manager.save()
                print(f"✅ Wochenend-Schutz → {'aktiviert' if self.app_config.weekend_exit else 'deaktiviert'}")

            elif choice == "9":
                try:
                    dl = float(input(f"Max. Tagesverlust € (aktuell {self.app_config.rm_max_daily_loss_eur}): ") or str(self.app_config.rm_max_daily_loss_eur))
                    wl = float(input(f"Max. Wochenverlust € (aktuell {self.app_config.rm_max_weekly_loss_eur}): ") or str(self.app_config.rm_max_weekly_loss_eur))
                    cd = int(input(f"Cooldown Sek. (aktuell {self.app_config.rm_min_time_between_trades}, 60–600): ") or str(self.app_config.rm_min_time_between_trades))
                    mt = int(input(f"Max Trades/Tag (aktuell {self.app_config.rm_max_trades_per_day}): ") or str(self.app_config.rm_max_trades_per_day))
                    self.app_config.rm_max_daily_loss_eur = max(0.0, dl)
                    self.app_config.rm_max_weekly_loss_eur = max(0.0, wl)
                    self.app_config.rm_min_time_between_trades = max(60, min(600, cd))
                    self.app_config.rm_max_trades_per_day = max(1, mt)
                    app_config_manager.save()
                    print(f"✅ RM Limits aktualisiert")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "10":
                print("\n🌍 SESSIONEN:")
                self.app_config.session_london = input(f"London aktiv? (j/n, aktuell {'j' if self.app_config.session_london else 'n'}): ").strip().lower() != "n"
                self.app_config.session_ny = input(f"New York aktiv? (j/n, aktuell {'j' if self.app_config.session_ny else 'n'}): ").strip().lower() != "n"
                self.app_config.session_asia = input(f"Asian aktiv? (j/n, aktuell {'j' if self.app_config.session_asia else 'n'}): ").strip().lower() == "j"
                print("\n⏰ HANDELSFENSTER (UTC):")
                tf = input(f"Von (HH:MM, aktuell {self.app_config.trade_time_from}): ").strip() or self.app_config.trade_time_from
                tt = input(f"Bis (HH:MM, aktuell {self.app_config.trade_time_to}): ").strip() or self.app_config.trade_time_to
                self.app_config.trade_time_from = tf
                self.app_config.trade_time_to = tt
                self.app_config.time_filter = input(f"Zeitfenster-Filter aktiv? (j/n): ").strip().lower() != "n"
                app_config_manager.save()
                print(f"✅ Sessions & Zeiten aktualisiert")

            elif choice == "11":
                self.app_config.news_filter = input(f"News-Filter aktiv? (j/n, aktuell {'j' if self.app_config.news_filter else 'n'}): ").lower() != "n"
                if self.app_config.news_filter:
                    self.app_config.news_high = input(f"🔴 Hoch filtern? (j/n, aktuell {'j' if self.app_config.news_high else 'n'}): ").lower() != "n"
                    self.app_config.news_medium = input(f"🟡 Mittel filtern? (j/n, aktuell {'j' if self.app_config.news_medium else 'n'}): ").lower() == "j"
                    try:
                        self.app_config.news_before_min = int(input(f"Vorab-Sperrzeit Min. (aktuell {self.app_config.news_before_min}): ") or str(self.app_config.news_before_min))
                        self.app_config.news_after_min = int(input(f"Nachher-Sperrzeit Min. (aktuell {self.app_config.news_after_min}): ") or str(self.app_config.news_after_min))
                    except ValueError:
                        pass
                app_config_manager.save()
                print("✅ News-Filter aktualisiert")

            elif choice == "12":
                try:
                    sp = int(input(f"Max Spread Pips (aktuell {self.app_config.max_spread}): ") or str(self.app_config.max_spread))
                    sl = int(input(f"Max Slippage Pips (aktuell {self.app_config.max_slippage}): ") or str(self.app_config.max_slippage))
                    self.app_config.max_spread = max(1, sp)
                    self.app_config.max_slippage = max(1, sl)
                    self.app_config.spread_check = input("Spread-Prüfung aktiviert? (j/n): ").lower() != "n"
                    app_config_manager.save()
                    print(f"✅ Spread/Slippage → {self.app_config.max_spread}p / {self.app_config.max_slippage}p")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "13":
                print("\n🗓️ AKTIVE HANDELSTAGE:")
                self.app_config.day_mon = input(f"Montag aktiv? (j/n, aktuell {'j' if self.app_config.day_mon else 'n'}): ").strip().lower() != "n"
                self.app_config.day_tue = input(f"Dienstag aktiv? (j/n, aktuell {'j' if self.app_config.day_tue else 'n'}): ").strip().lower() != "n"
                self.app_config.day_wed = input(f"Mittwoch aktiv? (j/n, aktuell {'j' if self.app_config.day_wed else 'n'}): ").strip().lower() != "n"
                self.app_config.day_thu = input(f"Donnerstag aktiv? (j/n, aktuell {'j' if self.app_config.day_thu else 'n'}): ").strip().lower() != "n"
                self.app_config.day_fri = input(f"Freitag aktiv? (j/n, aktuell {'j' if self.app_config.day_fri else 'n'}): ").strip().lower() != "n"
                self.app_config.day_sat = input(f"Samstag aktiv? (j/n, aktuell {'j' if self.app_config.day_sat else 'n'}): ").strip().lower() == "j"
                self.app_config.day_sun = input(f"Sonntag aktiv? (j/n, aktuell {'j' if self.app_config.day_sun else 'n'}): ").strip().lower() == "j"
                app_config_manager.save()
                print(f"✅ Handelstage aktualisiert")

            elif choice == "14":
                self.app_config.debug_mode = not self.app_config.debug_mode
                app_config_manager.save()
                print(f"✅ Debug-Modus → {'aktiviert' if self.app_config.debug_mode else 'deaktiviert'}")

            else:
                print("❌ Ungültige Auswahl")

            input("\nDrücken Sie Enter zum Fortfahren...")

    def notifications_settings_menu(self):
        """Benachrichtigungen — Parität mit GUI config_tab.py → Benachrichtigungen Tab"""
        from core.app_config import app_config_manager
        while True:
            self.print_header("🔔 BENACHRICHTIGUNGEN")

            print("📌 AKTUELLE KONFIGURATION:")
            print("─" * 48)
            print(f"   Telegram Token    : {'*****' if self.app_config.tg_token else '(leer)'}")
            print(f"   Telegram Chat ID  : {self.app_config.tg_chat_id or '(leer)'}")
            print(f"   Discord Webhook   : {'konfiguriert' if self.app_config.discord_webhook else '(leer)'}")
            print(f"\n   🔔 FILTER:")
            print(f"   SL Hit            : {'✅' if self.app_config.notif_sl_hit else '❌'}")
            print(f"   TP Hit            : {'✅' if self.app_config.notif_tp_hit else '❌'}")
            print(f"   Neuer Trade       : {'✅' if self.app_config.notif_new_trade else '❌'}")
            print(f"   Fehler/Kritisch   : {'✅' if self.app_config.notif_error else '❌'}")
            print(f"   Sound-Alerts      : {'✅' if self.app_config.sound_alerts else '❌'}")

            print("\n🛠️  EDITIEROPTIONEN:")
            print("─" * 48)
            print("  1. 📱 Telegram Token")
            print("  2. 💬 Telegram Chat ID")
            print("  3. 🎯 Discord Webhook URL")
            print("  4. 📤 Test-Nachricht senden (Telegram)")
            print("  5. 🔔 Benachrichtigungsfilter konfigurieren")
            print("  6. 🔊 Sound-Alerts umschalten")
            print("  0. ⬅️  Zurück")

            choice = input("\n🎯 Ihre Wahl (0-6): ").strip()

            if choice == "0":
                break

            elif choice == "1":
                val = input("Telegram Bot Token (leer = unverändert): ").strip()
                if val:
                    self.app_config.tg_token = val
                    app_config_manager.save()
                    print("✅ Telegram Token gesetzt")

            elif choice == "2":
                val = input(f"Telegram Chat ID (aktuell: {self.app_config.tg_chat_id or '(leer)'}): ").strip()
                if val:
                    self.app_config.tg_chat_id = val
                    app_config_manager.save()
                    print(f"✅ Chat ID → {self.app_config.tg_chat_id}")

            elif choice == "3":
                val = input("Discord Webhook URL (leer = unverändert): ").strip()
                if val:
                    self.app_config.discord_webhook = val
                    app_config_manager.save()
                    print("✅ Discord Webhook gesetzt")

            elif choice == "4":
                if not self.app_config.tg_token or not self.app_config.tg_chat_id:
                    print("❌ Bitte erst Token und Chat ID konfigurieren")
                else:
                    print("📤 Sende Test-Nachricht...")
                    try:
                        import requests
                        url = f"https://api.telegram.org/bot{self.app_config.tg_token}/sendMessage"
                        resp = requests.post(url, json={"chat_id": self.app_config.tg_chat_id, "text": "✅ FinGPT Terminal Test-Nachricht"}, timeout=5)
                        if resp.status_code == 200:
                            print("✅ Test-Nachricht erfolgreich gesendet!")
                        else:
                            print(f"❌ Fehler: {resp.status_code} — {resp.text[:100]}")
                    except Exception as e:
                        print(f"❌ Verbindungsfehler: {e}")

            elif choice == "5":
                print("\n🔔 BENACHRICHTIGUNGSFILTER (j = aktiv, n = inaktiv):")
                self.app_config.notif_sl_hit = input(f"SL Hit ({('✅' if self.app_config.notif_sl_hit else '❌')}): ").strip().lower() != "n"
                self.app_config.notif_tp_hit = input(f"TP Hit ({('✅' if self.app_config.notif_tp_hit else '❌')}): ").strip().lower() != "n"
                self.app_config.notif_new_trade = input(f"Neuer Trade ({('✅' if self.app_config.notif_new_trade else '❌')}): ").strip().lower() != "n"
                self.app_config.notif_error = input(f"Fehler/Kritisch ({('✅' if self.app_config.notif_error else '❌')}): ").strip().lower() != "n"
                app_config_manager.save()
                print("✅ Filter aktualisiert")

            elif choice == "6":
                self.app_config.sound_alerts = not self.app_config.sound_alerts
                app_config_manager.save()
                print(f"✅ Sound-Alerts → {'aktiviert' if self.app_config.sound_alerts else 'deaktiviert'}")

            else:
                print("❌ Ungültige Auswahl")

            input("\nDrücken Sie Enter zum Fortfahren...")

    def mcp_settings_menu(self):
        """MCP Server Konfiguration — Parität mit GUI config_tab.py → MCP Server Tab"""
        from core.app_config import app_config_manager
        while True:
            self.print_header("🔌 MCP SERVER KONFIGURATION")

            print("📌 AKTUELLE KONFIGURATION:")
            print("─" * 48)
            print(f"   MCP Server aktiv      : {'✅' if self.app_config.mcp_enabled else '❌'}")
            
            # Zeige Status falls verfügbar
            tv_status = "❌ Nicht gestartet"
            hive_status = "❌ Nicht gestartet"
            
            if hasattr(self, 'trading_controller') and self.trading_controller and hasattr(self.trading_controller, 'mcp_engine'):
                if getattr(self.trading_controller.mcp_engine, 'mcp_integration', None) and getattr(self.trading_controller.mcp_engine.mcp_integration, 'is_running', False):
                    tv_status = "✅ Aktiv"
                    hive_status = "✅ Aktiv"
            
            print(f"   TradingView MCP       : {tv_status}")
            print(f"   Hive Intelligence MCP : {hive_status}")

            print("\n🛠️  EDITIEROPTIONEN:")
            print("─" * 48)
            print("  1. 🔌 MCP Server umschalten (Aktiv/Inaktiv)")
            print("  2. 🚀 MCP Server manuell starten")
            print("  0. ⬅️  Zurück")

            choice = input("\n🎯 Ihre Wahl (0-2): ").strip()

            if choice == "0":
                break

            elif choice == "1":
                self.app_config.mcp_enabled = not self.app_config.mcp_enabled
                app_config_manager.save()
                
                # Wenn aktiv und Trading Controller vorhanden, starte Engine (oder stoppe sie)
                if hasattr(self, 'trading_controller') and self.trading_controller:
                    if self.app_config.mcp_enabled and getattr(self.trading_controller, 'mcp_engine', None):
                        try:
                            self.trading_controller.mcp_engine.start()
                            print("✅ MCP Server gestartet")
                        except Exception as e:
                            print(f"❌ Fehler beim Starten: {e}")
                    elif not self.app_config.mcp_enabled and getattr(self.trading_controller, 'mcp_engine', None):
                        try:
                            self.trading_controller.mcp_engine.stop()
                            print("✅ MCP Server gestoppt")
                        except Exception:
                            pass
                            
                print(f"✅ MCP Server → {'aktiviert' if self.app_config.mcp_enabled else 'deaktiviert'}")

            elif choice == "2":
                print("🚀 Versuche MCP Server zu starten...")
                if not hasattr(self, 'trading_controller') or not getattr(self, 'trading_controller', None):
                    try:
                        from core.trading_controller import TradingController
                        self.trading_controller = TradingController(self)
                    except Exception as e:
                        print(f"❌ Trading Controller Fehler: {e}")
                        input("\nDrücken Sie Enter zum Fortfahren...")
                        continue

                if getattr(self.trading_controller, 'mcp_engine', None) is None:
                    try:
                        from core.mcp_integration import create_mcp_integration
                        self.trading_controller.mcp_engine = create_mcp_integration(self, None)
                    except Exception as e:
                        print(f"❌ MCP Engine Fehler: {e}")
                        input("\nDrücken Sie Enter zum Fortfahren...")
                        continue

                if self.trading_controller.mcp_engine:
                    try:
                        self.trading_controller.mcp_engine.start()
                        print("✅ MCP Server erfolgreich gestartet!")
                    except Exception as e:
                        print(f"❌ Fehler beim Starten: {e}")
                else:
                    print("❌ MCP Engine konnte nicht erstellt werden.")

            else:
                print("❌ Ungültige Auswahl")

            input("\nDrücken Sie Enter zum Fortfahren...")

    # ==========================================
    # 4. ADVANCED INDICATORS & SIGNALS
    # ==========================================
    def advanced_signal_generator(self):
        """Signal-Generator mit allen verfügbaren Indikatoren"""
        self.print_header("SIGNAL-GENERATOR (ALLE INDIKATOREN)")
    
        if not self.advanced_indicators:
            print("❌ Erweiterte Indikatoren nicht verfügbar")
            return
    
        print("📊 Erstelle Trading-Signale mit allen verfügbaren Indikatoren")
        print("─" * 60)
    
        # Single Symbol oder Multiple
        mode = input("Modus wählen:\n1. Einzelnes Symbol\n2. Multiple Symbole\nWahl (1-2): ").strip()
    
        if mode == "1":
            symbol = input("💱 Symbol eingeben: ").upper()
            if symbol:
                self.generate_single_signal(symbol)
    
        elif mode == "2":
            symbols_input = input("💱 Symbole (kommagetrennt, z.B. EURUSD,GBPUSD): ").upper()
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                self.generate_multiple_signals(symbols)
    
        else:
            print("❌ Ungültige Auswahl")

    def generate_single_signal(self, symbol):
        """Generiert detailliertes Signal für einzelnes Symbol"""
        try:
            print(f"\n🔄 Generiere umfassendes Signal für {symbol}...")
        
            if not self.integration:
                print("❌ Integration nicht verfügbar")
                return
        
            # Erstelle Trading-Signal mit allen Indikatoren
            trading_signal = self.integration.create_trading_signal(symbol, use_advanced=True)
        
            print(f"\n{'='*60}")
            print(f"🎯 TRADING-SIGNAL: {symbol}")
            print(f"{'='*60}")
        
            # Haupt-Signal mit Icon
            signal_icon = "🚀" if trading_signal['signal'] == "STRONG_BUY" else \
                         "🟢" if trading_signal['signal'] == "BUY" else \
                         "💥" if trading_signal['signal'] == "STRONG_SELL" else \
                         "🔴" if trading_signal['signal'] == "SELL" else "🟡"
        
            print(f"{signal_icon} HAUPTSIGNAL: {trading_signal['signal']}")
            print(f"🎯 KONFIDENZ: {trading_signal['confidence']}")
            print(f"📊 ANALYSIERTE INDIKATOREN: {trading_signal['total_indicators']}")
            print(f"⏰ ZEITSTEMPEL: {trading_signal['timestamp']}")
        
            # Signal-Verhältnis
            if trading_signal.get('buy_ratio', 0) > 0 or trading_signal.get('sell_ratio', 0) > 0:
                print(f"\n📈 SIGNAL-VERTEILUNG:")
                print(f"🟢 Bullisch: {trading_signal.get('buy_ratio', 0):.1%}")
                print(f"🔴 Bearisch: {trading_signal.get('sell_ratio', 0):.1%}")
        
            # Unterstützende Signale
            if trading_signal.get('supporting_signals'):
                print(f"\n✅ UNTERSTÜTZENDE SIGNALE:")
                for i, signal in enumerate(trading_signal['supporting_signals'], 1):
                    print(f"{i:2d}. {signal}")
        
            # Neutrale/Konflikt Signale
            if trading_signal.get('conflicting_signals'):
                print(f"\n⚠️ NEUTRALE SIGNALE:")
                for i, signal in enumerate(trading_signal['conflicting_signals'], 1):
                    print(f"{i:2d}. {signal}")
        
            # Trading-Empfehlung
            print(f"\n💡 TRADING-EMPFEHLUNG:")
            if trading_signal['signal'] in ['STRONG_BUY', 'BUY']:
                print(f"📈 Kaufgelegenheit erkannt")
                print(f"🎯 Empfohlene Aktion: Long-Position eröffnen")
            
                # Berechne Einstiegs-Levels
                tick = mt5.symbol_info_tick(symbol)  # type: ignore[attr-defined]
                if tick:
                    current_price = tick.ask
                    print(f"💰 Aktueller Einstiegspreis: {current_price:.5f}")
                
                    # Support/Resistance für Stop-Loss
                    sr_data = self.calculate_support_resistance(symbol)
                    if sr_data and sr_data['nearest_support']:
                        sup_level, _ = sr_data['nearest_support']
                        suggested_sl = sup_level * 0.999  # 0.1% unter Support
                        print(f"🛑 Empfohlener Stop-Loss: {suggested_sl:.5f}")
                
                    if sr_data and sr_data['nearest_resistance']:
                        res_level, _ = sr_data['nearest_resistance']
                        suggested_tp = res_level * 1.001  # 0.1% vor Resistance
                        print(f"🎯 Empfohlenes Take-Profit: {suggested_tp:.5f}")
        
            elif trading_signal['signal'] in ['STRONG_SELL', 'SELL']:
                print(f"📉 Verkaufsgelegenheit erkannt")
                print(f"🎯 Empfohlene Aktion: Short-Position oder bestehende Position schließen")
            
                tick = mt5.symbol_info_tick(symbol)  # type: ignore[attr-defined]
                if tick:
                    current_price = tick.bid
                    print(f"💰 Aktueller Verkaufspreis: {current_price:.5f}")
        
            else:
                print(f"⏸️ Abwarten empfohlen")
                print(f"🎯 Empfohlene Aktion: Weitere Bestätigung abwarten")
                print(f"📊 Grund: Gemischte oder neutrale Signale")
        
            print(f"{'='*60}")
        
        except Exception as e:
            print(f"❌ Signal-Generierung Fehler: {e}")

    def generate_multiple_signals(self, symbols):
        """Generiert Signale für mehrere Symbole"""
        try:
            print(f"\n🔄 Generiere Signale für {len(symbols)} Symbole...")
        
            if not self.integration:
                print("❌ Integration nicht verfügbar")
                return
        
            all_signals = []
        
            for symbol in symbols:
                print(f"📊 Analysiere {symbol}...")
                try:
                    trading_signal = self.integration.create_trading_signal(symbol, use_advanced=True)
                
                    # Bewerte Signal-Qualität
                    score = 0
                    if trading_signal['signal'] in ['STRONG_BUY', 'STRONG_SELL']:
                        score = 5
                    elif trading_signal['signal'] in ['BUY', 'SELL']:
                        score = 3
                    elif trading_signal['signal'] == 'NEUTRAL':
                        score = 1
                
                    # Konfidenz-Bonus
                    if trading_signal['confidence'] == 'HOCH':
                        score += 2
                    elif trading_signal['confidence'] == 'MITTEL':
                        score += 1
                
                    trading_signal['score'] = score
                    all_signals.append(trading_signal)
                
                    time.sleep(0.5)  # Kurze Pause zwischen Analysen
                
                except Exception as e:
                    print(f"⚠️ Fehler bei {symbol}: {e}")
        
            # Sortiere nach Score
            all_signals.sort(key=lambda x: x['score'], reverse=True)
        
            # Zeige Zusammenfassung
            print(f"\n{'='*70}")
            print(f"📊 MULTI-SYMBOL SIGNAL-ÜBERSICHT")
            print(f"{'='*70}")
        
            print(f"{'Symbol':<8} {'Signal':<12} {'Konfidenz':<10} {'Score':<6} {'Indikatoren':<12}")
            print("─" * 70)
        
            for signal in all_signals:
                symbol = signal['symbol']
                main_signal = signal['signal']
                confidence = signal['confidence']
                score = signal['score']
                indicators = signal.get('total_indicators', 0)
            
                signal_icon = "🚀" if main_signal == "STRONG_BUY" else \
                             "🟢" if main_signal == "BUY" else \
                             "💥" if main_signal == "STRONG_SELL" else \
                             "🔴" if main_signal == "SELL" else "🟡"
            
                print(f"{symbol:<8} {signal_icon}{main_signal:<11} {confidence:<10} {score:<6} {indicators:<12}")
        
            # Top-Gelegenheiten hervorheben
            strong_signals = [s for s in all_signals if s['score'] >= 5]
        
            if strong_signals:
                print(f"\n🎯 TOP TRADING-GELEGENHEITEN (Score ≥ 5):")
                print("─" * 50)
            
                for i, signal in enumerate(strong_signals[:5], 1):  # Top 5
                    symbol = signal['symbol']
                    main_signal = signal['signal']
                    buy_ratio = signal.get('buy_ratio', 0)
                    sell_ratio = signal.get('sell_ratio', 0)
                
                    ratio = buy_ratio if main_signal in ['STRONG_BUY', 'BUY'] else sell_ratio
                
                    print(f"🏆 {i}. {symbol}: {main_signal} ({ratio:.1%} Übereinstimmung)")
                
                    # Zeige Top-2 unterstützende Signale
                    if signal.get('supporting_signals'):
                        top_signals = signal['supporting_signals'][:2]
                        for supporting in top_signals:
                            print(f"   ✅ {supporting}")
            else:
                print(f"\n⏸️ Keine starken Trading-Gelegenheiten gefunden")
                print(f"💡 Alle Signale sind neutral oder widersprüchlich")
        
            print(f"{'='*70}")
        
        except Exception as e:
            print(f"❌ Multi-Signal Fehler: {e}")

    def show_individual_advanced_indicators(self):
        """Zeigt einzelne erweiterte Indikatoren zur Auswahl"""
        while True:
            self.print_header("EINZELNE ERWEITERTE INDIKATOREN")
        
            print("📊 Verfügbare Indikatoren:")
            print("─" * 35)
        
            indicator_menu = [
                ("1", "📈", "Williams %R"),
                ("2", "📊", "Commodity Channel Index (CCI)"),
                ("3", "🌊", "Awesome Oscillator"),
                ("4", "☁️", "Ichimoku Cloud"),
                ("5", "📊", "VWAP (Volume Weighted Average Price)"),
                ("6", "💰", "Money Flow Index (MFI)"),
                ("7", "📈", "Average Directional Index (ADX)"),
                ("8", "📊", "Alle Indikatoren anzeigen"),
                ("9", "⬅️", "Zurück")
            ]
        
            for num, icon, desc in indicator_menu:
                print(f" {num}. {icon} {desc}")
        
            print("─" * 35)
        
            choice = input("🎯 Indikator wählen (1-9): ").strip()
        
            if choice == "9":
                break
            elif choice in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                symbol = input("💱 Symbol eingeben: ").upper()
                if symbol:
                    self.display_selected_indicator(choice, symbol)
            else:
                print("❌ Ungültige Auswahl")
        
            if choice != "9":
                input("\nDrücken Sie Enter zum Fortfahren...")

    def display_selected_indicator(self, indicator_choice, symbol):
        """Zeigt einen spezifischen Indikator an"""
        if not self.advanced_indicators:
            print("❌ Erweiterte Indikatoren nicht verfügbar")
            return
    
        try:
            print(f"\n📊 Berechne Indikator für {symbol}...")
        
            if indicator_choice == "1":
                # Williams %R
                wr_data = self.advanced_indicators.calculate_williams_r(symbol)
                if wr_data:
                    print(f"\n📈 WILLIAMS %R ANALYSE:")
                    print(f"Wert: {wr_data['value']}%")
                    print(f"Signal: {wr_data['signal']}")
                    print(f"Beschreibung: {wr_data['description']}")
                    print(f"Überkauft Level: {wr_data['overbought_level']}")
                    print(f"Überverkauft Level: {wr_data['oversold_level']}")
                else:
                    print("❌ Williams %R Daten nicht verfügbar")
        
            elif indicator_choice == "2":
                # CCI
                cci_data = self.advanced_indicators.calculate_cci(symbol)
                if cci_data:
                    print(f"\n📊 COMMODITY CHANNEL INDEX:")
                    print(f"Wert: {cci_data['value']}")
                    print(f"Signal: {cci_data['signal']}")
                    print(f"Beschreibung: {cci_data['description']}")
                    print(f"Überkauft Level: {cci_data['overbought_level']}")
                    print(f"Überverkauft Level: {cci_data['oversold_level']}")
                else:
                    print("❌ CCI Daten nicht verfügbar")
        
            elif indicator_choice == "3":
                # Awesome Oscillator
                ao_data = self.advanced_indicators.calculate_awesome_oscillator(symbol)
                if ao_data:
                    print(f"\n🌊 AWESOME OSCILLATOR:")
                    print(f"Wert: {ao_data['value']}")
                    print(f"Signal: {ao_data['signal']}")
                    print(f"Beschreibung: {ao_data['description']}")
                    print(f"Über Nulllinie: {ao_data['above_zero']}")
                    print(f"Momentum: {ao_data['momentum']}")
                else:
                    print("❌ Awesome Oscillator Daten nicht verfügbar")
        
            elif indicator_choice == "4":
                # Ichimoku
                ichimoku_data = self.advanced_indicators.calculate_ichimoku(symbol)
                if ichimoku_data:
                    print(f"\n☁️ ICHIMOKU CLOUD ANALYSE:")
                    print(f"Tenkan-sen: {ichimoku_data['tenkan_sen']}")
                    print(f"Kijun-sen: {ichimoku_data['kijun_sen']}")
                    print(f"Cloud Top: {ichimoku_data['cloud_top']}")
                    print(f"Cloud Bottom: {ichimoku_data['cloud_bottom']}")
                    print(f"Preis vs Cloud: {ichimoku_data['price_vs_cloud']}")
                    print(f"Cloud Signal: {ichimoku_data['cloud_signal']}")
                    print(f"TK Signal: {ichimoku_data['tk_signal']}")
                    print(f"Gesamtsignal: {ichimoku_data['overall_signal']}")
                    print(f"Beschreibung: {ichimoku_data['description']}")
                else:
                    print("❌ Ichimoku Daten nicht verfügbar")
        
            elif indicator_choice == "5":
                # VWAP
                vwap_data = self.advanced_indicators.calculate_vwap(symbol)
                if vwap_data:
                    print(f"\n📊 VWAP ANALYSE:")
                    print(f"VWAP: {vwap_data['vwap']}")
                    print(f"Aktueller Preis: {vwap_data['current_price']}")
                    print(f"Abstand: {vwap_data['distance_pct']}%")
                    print(f"Signal: {vwap_data['signal']}")
                    print(f"Beschreibung: {vwap_data['description']}")
                    print(f"Preis über VWAP: {vwap_data['above_vwap']}")
                else:
                    print("❌ VWAP Daten nicht verfügbar")
        
            elif indicator_choice == "6":
                # MFI
                mfi_data = self.advanced_indicators.calculate_mfi(symbol)
                if mfi_data:
                    print(f"\n💰 MONEY FLOW INDEX:")
                    print(f"Wert: {mfi_data['value']}")
                    print(f"Signal: {mfi_data['signal']}")
                    print(f"Beschreibung: {mfi_data['description']}")
                    print(f"Überkauft Level: {mfi_data['overbought_level']}")
                    print(f"Überverkauft Level: {mfi_data['oversold_level']}")
                else:
                    print("❌ MFI Daten nicht verfügbar")
        
            elif indicator_choice == "7":
                # ADX
                adx_data = self.advanced_indicators.calculate_adx(symbol)
                if adx_data:
                    print(f"\n📈 AVERAGE DIRECTIONAL INDEX:")
                    print(f"ADX: {adx_data['adx']}")
                    print(f"DI+: {adx_data['di_plus']}")
                    print(f"DI-: {adx_data['di_minus']}")
                    print(f"Trend-Stärke: {adx_data['trend_strength']}")
                    print(f"Trend-Richtung: {adx_data['trend_direction']}")
                    print(f"Signal: {adx_data['signal']}")
                    print(f"Starker Trend: {adx_data['strong_trend']}")
                    print(f"Beschreibung: {adx_data['description']}")
                else:
                    print("❌ ADX Daten nicht verfügbar")
        
            elif indicator_choice == "8":
                # Alle Indikatoren
                analysis = self.advanced_indicators.get_comprehensive_analysis(symbol)
                if analysis:
                    self.advanced_indicators.print_analysis_report(symbol, analysis)
                else:
                    print("❌ Umfassende Analyse nicht verfügbar")
        
        except Exception as e:
            print(f"❌ Fehler bei Indikator-Berechnung: {e}")

    def comprehensive_technical_analysis(self):
        """Vollständige technische Analyse mit allen verfügbaren Indikatoren"""
        self.print_header("VOLLSTÄNDIGE TECHNISCHE ANALYSE")
    
        symbol = input("💱 Symbol für vollständige Analyse: ").upper()
        if not symbol:
            print("❌ Kein Symbol eingegeben")
            return
    
        print(f"\n🔄 Führe vollständige Analyse für {symbol} durch...")
        print("─" * 60)
    
        try:
            # 1. Basis-Indikatoren
            print("📊 BASIS-INDIKATOREN:")
            print("─" * 30)
        
            # RSI
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if rsi_value:
                rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi_value)
                icon = "🟢" if rsi_signal == "BUY" else "🔴" if rsi_signal == "SELL" else "🟡"
                print(f"{icon} RSI: {rsi_value} - {rsi_desc}")
        
            # MACD
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if macd_data:
                macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
                icon = "🟢" if macd_signal == "BUY" else "🔴" if macd_signal == "SELL" else "🟡"
                print(f"{icon} MACD: {macd_desc}")
        
            # Support/Resistance
            sr_data = self.calculate_support_resistance(symbol)
            if sr_data:
                current_price = sr_data['current_price']
                sr_signal, sr_desc = self.get_sr_signal(sr_data, current_price)
                icon = "🟢" if sr_signal == "BUY" else "🔴" if sr_signal == "SELL" else "🟡"
                print(f"{icon} S/R: {sr_desc}")
        
            # 2. Erweiterte Indikatoren
            if self.advanced_indicators:
                print("\n📈 ERWEITERTE INDIKATOREN:")
                print("─" * 30)
            
                advanced_analysis = self.advanced_indicators.get_comprehensive_analysis(symbol)
                if advanced_analysis:
                    self.advanced_indicators.print_analysis_report(symbol, advanced_analysis)
        
            # 3. Gesamtbewertung
            if self.integration:
                print("\n🎯 GESAMTBEWERTUNG:")
                print("─" * 30)
            
                trading_signal = self.integration.create_trading_signal(symbol, use_advanced=True)
            
                signal_icon = "🚀" if trading_signal['signal'] == "STRONG_BUY" else \
                             "🟢" if trading_signal['signal'] == "BUY" else \
                             "💥" if trading_signal['signal'] == "STRONG_SELL" else \
                             "🔴" if trading_signal['signal'] == "SELL" else "🟡"
            
                print(f"{signal_icon} SIGNAL: {trading_signal['signal']}")
                print(f"🎯 KONFIDENZ: {trading_signal['confidence']}")
                print(f"📊 ANALYSIERTE INDIKATOREN: {trading_signal['total_indicators']}")
            
                if trading_signal.get('buy_ratio', 0) > 0 or trading_signal.get('sell_ratio', 0) > 0:
                    print(f"📈 Bullisch: {trading_signal.get('buy_ratio', 0):.1%}")
                    print(f"📉 Bearisch: {trading_signal.get('sell_ratio', 0):.1%}")
            
                # Top-Signale anzeigen
                if trading_signal.get('supporting_signals'):
                    print(f"\n✅ TOP UNTERSTÜTZENDE SIGNALE:")
                    for i, signal in enumerate(trading_signal['supporting_signals'][:5], 1):
                        print(f"{i}. {signal}")
        
            print("─" * 60)
        
        except Exception as e:
            print(f"❌ Vollständige Analyse Fehler: {e}")

    def advanced_indicator_settings_menu(self):
        """Einstellungsmenü für erweiterte Indikatoren"""
        if not self.advanced_indicators:
            print("❌ Erweiterte Indikatoren nicht verfügbar")
            return
    
        while True:
            self.print_header("ERWEITERTE INDIKATOR-EINSTELLUNGEN")
        
            print("📊 Verfügbare Einstellungen:")
            print("─" * 35)
            print(" 1. Williams %R Parameter")
            print(" 2. CCI Parameter") 
            print(" 3. Awesome Oscillator Parameter")
            print(" 4. Ichimoku Parameter")
            print(" 5. VWAP Parameter")
            print(" 6. Money Flow Index Parameter")
            print(" 7. ADX Parameter")
            print(" 8. Alle auf Standard zurücksetzen")
            print(" 9. Zurück")
        
            setting_choice = input("\n🎯 Ihre Wahl (1-9): ").strip()
        
            if setting_choice == "1":
                self.configure_williams_r_settings()
            elif setting_choice == "8":
                confirm = input("Alle auf Standard zurücksetzen? (ja/nein): ")
                if confirm.lower() == "ja":
                    self.reset_advanced_indicator_settings()
                    print("✅ Alle Einstellungen zurückgesetzt")
            elif setting_choice == "9":
                break
            else:
                print("❌ Funktion noch nicht implementiert oder ungültige Auswahl")
        
            if setting_choice != "9":
                input("\nDrücken Sie Enter zum Fortfahren...")

    def configure_williams_r_settings(self):
        """Konfiguration für Williams %R"""
        if not self.advanced_indicators:
            return
    
        print("\n📊 WILLIAMS %R EINSTELLUNGEN")
        print("─" * 30)
        print(f"Aktuelle Periode: {self.advanced_indicators.williams_r_period}")
        print(f"Überkauft Level: {self.advanced_indicators.williams_r_overbought}")
        print(f"Überverkauft Level: {self.advanced_indicators.williams_r_oversold}")
    
        try:
            period = input(f"Neue Periode (5-50, aktuell {self.advanced_indicators.williams_r_period}): ")
            if period:
                period = int(period)
                if 5 <= period <= 50:
                    self.advanced_indicators.williams_r_period = period
                    print(f"✅ Williams %R Periode auf {period} gesetzt")
                else:
                    print("❌ Periode muss zwischen 5 und 50 liegen")
        except ValueError:
            print("❌ Ungültige Eingabe")

    def reset_advanced_indicator_settings(self):
        """Setzt erweiterte Indikator-Einstellungen zurück"""
        if self.advanced_indicators:
            # Standard-Werte setzen
            self.advanced_indicators.williams_r_period = 14
            self.advanced_indicators.williams_r_overbought = -20
            self.advanced_indicators.williams_r_oversold = -80
            self.advanced_indicators.cci_period = 20
            self.advanced_indicators.cci_overbought = 100
            self.advanced_indicators.cci_oversold = -100
            self.advanced_indicators.ao_fast_period = 5
            self.advanced_indicators.ao_slow_period = 34
            # ... weitere Standard-Werte nach Bedarf

    def enhanced_ai_analysis(self):
        """Erweiterte KI-Analyse mit allen Indikatoren"""
        self.print_header("ERWEITERTE KI-ANALYSE")
    
        symbol = input("💱 Symbol für erweiterte KI-Analyse: ").upper()
        if not symbol:
            print("❌ Kein Symbol eingegeben")
            return
    
        if not self.integration:
            print("❌ Integration nicht verfügbar")
            return
    
        print(f"\n🔄 Führe erweiterte KI-Analyse für {symbol} durch...")
    
        try:
            ai_response = self.integration.enhanced_ai_analysis(symbol, include_advanced=True)
            print("\n🤖 ERWEITERTE KI-ANALYSE:")
            print("─" * 40)
            print(ai_response)
        except Exception as e:
            print(f"❌ Erweiterte KI-Analyse Fehler: {e}")

    def multi_indicator_scanner(self):
        """Scanner für multiple Symbole mit allen Indikatoren"""
        self.print_header("MULTI-INDIKATOR SCANNER")
    
        symbols_input = input("💱 Symbole (kommagetrennt, leer für Standard): ").upper()
    
        if symbols_input:
            symbols = [s.strip() for s in symbols_input.split(',')]
        else:
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]
    
        print(f"\n🔄 Scanne {len(symbols)} Symbole...")
    
        if not self.integration:
            print("❌ Integration nicht verfügbar")
            return
    
        try:
            opportunities = []
        
            for symbol in symbols:
                print(f"📊 Scanne {symbol}...")
                try:
                    trading_signal = self.integration.create_trading_signal(symbol, use_advanced=True)
                
                    score = 0
                    if trading_signal['signal'] in ['STRONG_BUY', 'STRONG_SELL']:
                        score = 5
                    elif trading_signal['signal'] in ['BUY', 'SELL']:
                        score = 3
                
                    if trading_signal['confidence'] == 'HOCH':
                        score += 2
                
                    trading_signal['score'] = score
                    opportunities.append(trading_signal)
                
                except Exception as e:
                    print(f"⚠️ {symbol}: {e}")
        
            # Sortiere nach Score
            opportunities.sort(key=lambda x: x['score'], reverse=True)
        
            print(f"\n{'='*60}")
            print("📊 SCANNER ERGEBNISSE")
            print(f"{'='*60}")
        
            for opp in opportunities:
                signal_icon = "🚀" if opp['signal'] == "STRONG_BUY" else \
                             "🟢" if opp['signal'] == "BUY" else \
                             "💥" if opp['signal'] == "STRONG_SELL" else \
                             "🔴" if opp['signal'] == "SELL" else "🟡"
            
                print(f"{signal_icon} {opp['symbol']:8} | {opp['signal']:12} | Score: {opp['score']} | Konfidenz: {opp['confidence']}")
        
        except Exception as e:
            print(f"❌ Scanner Fehler: {e}")
            #

    def indicator_comparison_analysis(self):
        """Vergleicht verschiedene Indikatoren für ein Symbol"""
        self.print_header("INDIKATOR-VERGLEICH")
    
        symbol = input("💱 Symbol für Vergleich: ").upper()
        if not symbol:
            print("❌ Kein Symbol eingegeben")
            return
    
        print(f"\n🔄 Vergleiche Indikatoren für {symbol}...")
    
        try:
            # Basis-Indikatoren sammeln
            indicators_data = {}
        
            # RSI
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if rsi_value:
                rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi_value)
                indicators_data['RSI'] = {
                    'signal': rsi_signal,
                    'value': rsi_value,
                    'description': rsi_desc,
                    'type': 'Momentum'
                }
        
            # MACD
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if macd_data:
                macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
                indicators_data['MACD'] = {
                    'signal': macd_signal,
                    'value': f"{macd_data['macd']:.6f}",
                    'description': macd_desc,
                    'type': 'Trend/Momentum'
                }
        
            # Support/Resistance
            sr_data = self.calculate_support_resistance(symbol)
            if sr_data:
                current_price = sr_data['current_price']
                sr_signal, sr_desc = self.get_sr_signal(sr_data, current_price)
                indicators_data['Support/Resistance'] = {
                    'signal': sr_signal,
                    'value': f"{current_price:.5f}",
                    'description': sr_desc,
                    'type': 'Price Action'
                }
        
            # Erweiterte Indikatoren hinzufügen
            if self.advanced_indicators:
                advanced_analysis = self.advanced_indicators.get_comprehensive_analysis(symbol)
            
                for indicator, data in advanced_analysis.items():
                    if 'signal' in data and 'description' in data:
                        indicator_name = indicator.replace('_', ' ').title()
                    
                        # Typ bestimmen
                        if indicator in ['williams_r', 'cci', 'awesome_oscillator']:
                            ind_type = 'Momentum'
                        elif indicator in ['ichimoku', 'adx']:
                            ind_type = 'Trend'
                        elif indicator in ['vwap', 'mfi']:
                            ind_type = 'Volume'
                        else:
                            ind_type = 'Other'
                    
                        indicators_data[indicator_name] = {
                            'signal': data['signal'],
                            'value': str(data.get('value', 'N/A')),
                            'description': data['description'],
                            'type': ind_type
                        }
        
            # Gruppiere nach Typ
            indicator_types = {}
            for name, data in indicators_data.items():
                indicator_type = data['type']
                if indicator_type not in indicator_types:
                    indicator_types[indicator_type] = []
                indicator_types[indicator_type].append((name, data))
        
            # Zeige Vergleich
            print(f"\n{'='*80}")
            print(f"📊 INDIKATOR-VERGLEICH: {symbol}")
            print(f"{'='*80}")
        
            for indicator_type, indicators in indicator_types.items():
                print(f"\n📈 {indicator_type.upper()}:")
                print("─" * 60)
                print(f"{'Indikator':<20} {'Signal':<12} {'Wert':<15} {'Beschreibung'}")
                print("─" * 60)
            
                for name, data in indicators:
                    signal = data['signal']
                    value = data['value']
                    description = data['description'][:30] + "..." if len(data['description']) > 30 else data['description']
                
                    signal_icon = "🟢" if signal in ['BUY', 'STRONG_BUY'] else \
                                 "🔴" if signal in ['SELL', 'STRONG_SELL'] else "🟡"
                
                    print(f"{name:<20} {signal_icon}{signal:<11} {value:<15} {description}")
        
            # Signal-Konsens Analyse
            print(f"\n🎯 SIGNAL-KONSENS ANALYSE:")
            print("─" * 40)
        
            signal_counts = {}
            for name, data in indicators_data.items():
                signal = data['signal']
                if signal not in signal_counts:
                    signal_counts[signal] = []
                signal_counts[signal].append(name)
        
            for signal, indicators in signal_counts.items():
                count = len(indicators)
                percentage = (count / len(indicators_data)) * 100
            
                signal_icon = "🟢" if signal in ['BUY', 'STRONG_BUY'] else \
                             "🔴" if signal in ['SELL', 'STRONG_SELL'] else "🟡"
            
                print(f"{signal_icon} {signal}: {count} Indikatoren ({percentage:.1f}%)")
                for indicator in indicators[:3]:  # Zeige max 3
                    print(f"   • {indicator}")
                if len(indicators) > 3:
                    print(f"   • ... und {len(indicators) - 3} weitere")
        
            # Konflikt-Analyse
            bullish_signals = signal_counts.get('BUY', []) + signal_counts.get('STRONG_BUY', [])
            bearish_signals = signal_counts.get('SELL', []) + signal_counts.get('STRONG_SELL', [])
            neutral_signals = signal_counts.get('NEUTRAL', [])
        
            print(f"\n⚖️ SIGNAL-VERTEILUNG:")
            print("─" * 30)
            print(f"🟢 Bullisch: {len(bullish_signals)} ({len(bullish_signals)/len(indicators_data)*100:.1f}%)")
            print(f"🔴 Bearisch: {len(bearish_signals)} ({len(bearish_signals)/len(indicators_data)*100:.1f}%)")
            print(f"🟡 Neutral: {len(neutral_signals)} ({len(neutral_signals)/len(indicators_data)*100:.1f}%)")
        
            # Empfehlung
            print(f"\n💡 VERGLEICHS-FAZIT:")
            print("─" * 25)
        
            if len(bullish_signals) >= len(indicators_data) * 0.6:
                print("🚀 STARKER BULLISCHER KONSENS")
                print("   Empfehlung: Kaufgelegenheit prüfen")
            elif len(bearish_signals) >= len(indicators_data) * 0.6:
                print("💥 STARKER BEARISCHER KONSENS")
                print("   Empfehlung: Verkaufsgelegenheit prüfen")
            elif len(bullish_signals) > len(bearish_signals):
                print("🟢 MODERATER BULLISCHER TREND")
                print("   Empfehlung: Vorsichtige Kaufposition möglich")
            elif len(bearish_signals) > len(bullish_signals):
                print("🔴 MODERATER BEARISCHER TREND")
                print("   Empfehlung: Vorsichtige Verkaufsposition möglich")
            else:
                print("🟡 GEMISCHTE SIGNALE")
                print("   Empfehlung: Abwarten oder weitere Bestätigung suchen")
        
            print(f"{'='*80}")
        
        except Exception as e:
            print(f"❌ Indikator-Vergleich Fehler: {e}")

    # ==========================================
    # 5. INDICATOR TESTING & OPTIMIZATION
    # ==========================================
    def indicator_testing_suite(self):
        """Test-Suite für Indikator-Optimierung"""
        self.print_header("INDIKATOR-TEST & OPTIMIERUNG")
    
        print("🧪 Indikator Test-Suite")
        print("─" * 30)
        print("1. Indikator-Performance Test")
        print("2. Parameter-Optimierung")
        print("3. Backtest-Simulation")
        print("4. Korrelations-Analyse")
        print("5. Zurück")
    
        choice = input("\n🎯 Test wählen (1-5): ").strip()
    
        if choice == "1":
            self.indicator_performance_test()
        elif choice == "2":
            self.parameter_optimization()
        elif choice == "3":
            self.backtest_simulation()
        elif choice == "4":
            self.correlation_analysis()
        elif choice == "5":
            return
        else:
            print("❌ Ungültige Auswahl")

    def indicator_performance_test(self):
        """Testet die Performance verschiedener Indikatoren"""
        symbol = input("💱 Symbol für Performance-Test: ").upper()
        if not symbol:
            print("❌ Kein Symbol eingegeben")
            return
    
        print(f"\n🔄 Teste Indikator-Performance für {symbol}...")
    
        try:
            # Teste verschiedene Indikatoren
            indicators_tested = []
        
            # RSI Test
            rsi_start = time.time()
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            rsi_time = time.time() - rsi_start
            if rsi_value:
                indicators_tested.append(('RSI', rsi_time, 'Erfolgreich'))
            else:
                indicators_tested.append(('RSI', rsi_time, 'Fehlgeschlagen'))
        
            # MACD Test
            macd_start = time.time()
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            macd_time = time.time() - macd_start
            if macd_data:
                indicators_tested.append(('MACD', macd_time, 'Erfolgreich'))
            else:
                indicators_tested.append(('MACD', macd_time, 'Fehlgeschlagen'))
        
            # Erweiterte Indikatoren Test
            if self.advanced_indicators:
                adv_start = time.time()
                adv_analysis = self.advanced_indicators.get_comprehensive_analysis(symbol)
                adv_time = time.time() - adv_start
                if adv_analysis:
                    indicators_tested.append(('Erweiterte Indikatoren', adv_time, 'Erfolgreich'))
                else:
                    indicators_tested.append(('Erweiterte Indikatoren', adv_time, 'Fehlgeschlagen'))
        
            # Ergebnisse anzeigen
            print(f"\n📊 PERFORMANCE-TEST ERGEBNISSE:")
            print("─" * 50)
            print(f"{'Indikator':<25} {'Zeit (s)':<10} {'Status'}")
            print("─" * 50)
        
            for name, exec_time, status in indicators_tested:
                status_icon = "✅" if status == 'Erfolgreich' else "❌"
                print(f"{name:<25} {exec_time:<10.3f} {status_icon} {status}")
        
            total_time = sum(t[1] for t in indicators_tested)
            success_rate = len([t for t in indicators_tested if t[2] == 'Erfolgreich']) / len(indicators_tested) * 100
        
            print("─" * 50)
            print(f"Gesamtzeit: {total_time:.3f}s")
            print(f"Erfolgsrate: {success_rate:.1f}%")
        
        except Exception as e:
            print(f"❌ Performance-Test Fehler: {e}")

    def parameter_optimization(self):
        """Optimiert Parameter für Indikatoren"""
        print("\n⚙️ PARAMETER-OPTIMIERUNG")
        print("─" * 30)
        print("Verfügbare Optimierungen:")
        print("1. RSI Periode optimieren")
        print("2. MACD Parameter optimieren")
        print("3. Williams %R optimieren")
        print("4. Zurück")
    
        choice = input("\nOptimierung wählen (1-4): ").strip()
    
        if choice == "1":
            self.optimize_rsi_period()
        elif choice == "2":
            print("MACD Optimierung - In Entwicklung")
        elif choice == "3":
            print("Williams %R Optimierung - In Entwicklung")
        elif choice == "4":
            return
        else:
            print("❌ Ungültige Auswahl")

    def optimize_rsi_period(self):
        """Optimiert RSI-Periode"""
        symbol = input("Symbol für RSI-Optimierung: ").upper()
        if not symbol:
            return
    
        print(f"\n🔄 Optimiere RSI-Periode für {symbol}...")
    
        try:
            periods_to_test = [10, 12, 14, 16, 18, 20]
            results = []
        
            original_period = self.rsi_period
        
            for period in periods_to_test:
                self.market.rsi_period = period
                rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
                if rsi_value:
                    signal, desc = self.market.get_rsi_signal(rsi_value)
                    results.append((period, rsi_value, signal))
                    print(f"Periode {period}: RSI={rsi_value:.1f}, Signal={signal}")
        
            # Setze ursprüngliche Periode zurück
            self.market.rsi_period = original_period
        
            print(f"\n📊 RSI-OPTIMIERUNG ERGEBNISSE:")
            print("─" * 40)
            for period, rsi, signal in results:
                print(f"Periode {period:2d}: RSI={rsi:5.1f} - {signal}")
        
        except Exception as e:
            print(f"❌ RSI-Optimierung Fehler: {e}")

    def backtest_simulation(self):
        """Einfache Backtest-Simulation"""
        print("\n📈 BACKTEST-SIMULATION")
        print("─" * 25)
        print("Diese Funktion ist in Entwicklung.")
        print("Geplante Features:")
        print("• Historische Daten-Analyse")
        print("• Signal-Performance über Zeit")
        print("• Win/Loss Ratio Berechnung")
        print("• Profit Factor Analyse")

    def correlation_analysis(self):
        """Analysiert Korrelationen zwischen Indikatoren"""
        symbol = input("💱 Symbol für Korrelations-Analyse: ").upper()
        if not symbol:
            return
    
        print(f"\n🔄 Analysiere Indikator-Korrelationen für {symbol}...")
    
        try:
            # Sammle alle Indikator-Signale
            signals = {}
        
            # Basis-Indikatoren
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if rsi_value:
                rsi_signal, _ = self.market.get_rsi_signal(rsi_value)
                signals['RSI'] = 1 if rsi_signal == 'BUY' else -1 if rsi_signal == 'SELL' else 0
        
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if macd_data:
                macd_signal, _ = self.market.get_macd_signal(macd_data)
                signals['MACD'] = 1 if macd_signal == 'BUY' else -1 if macd_signal == 'SELL' else 0
        
            # Erweiterte Indikatoren
            if self.advanced_indicators:
                advanced_analysis = self.advanced_indicators.get_comprehensive_analysis(symbol)
                for indicator, data in advanced_analysis.items():
                    if 'signal' in data:
                        signal = data['signal']
                        signals[indicator.upper()] = 1 if signal in ['BUY', 'STRONG_BUY'] else -1 if signal in ['SELL', 'STRONG_SELL'] else 0
        
            # Zeige Korrelation
            print(f"\n📊 INDIKATOR-KORRELATIONS-MATRIX:")
            print("─" * 50)
        
            indicator_names = list(signals.keys())
            for i, ind1 in enumerate(indicator_names):
                for j, ind2 in enumerate(indicator_names):
                    if i <= j:
                        if i == j:
                            correlation = 1.0
                        else:
                            # Einfache Korrelation (gleiche Richtung = positive Korrelation)
                            sig1, sig2 = signals[ind1], signals[ind2]
                            if sig1 == sig2:
                                correlation = 1.0 if sig1 != 0 else 0.0
                            elif sig1 == -sig2:
                                correlation = -1.0
                            else:
                                correlation = 0.0
                    
                        print(f"{ind1} <-> {ind2}: {correlation:+.2f}")
        
            # Konsens-Bewertung
            bullish_count = sum(1 for sig in signals.values() if sig > 0)
            bearish_count = sum(1 for sig in signals.values() if sig < 0)
            neutral_count = sum(1 for sig in signals.values() if sig == 0)
        
            print(f"\n🎯 SIGNAL-KONSENS:")
            print("─" * 20)
            print(f"Bullisch: {bullish_count}")
            print(f"Bearisch: {bearish_count}")
            print(f"Neutral: {neutral_count}")
        
            if bullish_count > bearish_count + neutral_count:
                print("📈 Starker bullischer Konsens")
            elif bearish_count > bullish_count + neutral_count:
                print("📉 Starker bearischer Konsens")
            else:
                print("🟡 Gemischte Signale")
        
        except Exception as e:
            print(f"❌ Korrelations-Analyse Fehler: {e}")

    # ==========================================
    # 6. REINFORCEMENT LEARNING
    # ==========================================
    def rl_menu_enhanced(self):
        """Erweiterte RL Menü mit Smart Training"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
        
        while True:
            self.print_header("REINFORCEMENT LEARNING")
        
            # Auto-Detection
            auto_symbols = self.auto_detect_trading_symbols()
            untrained_count = sum(1 for s in auto_symbols if s not in self.rl_manager.agents or 
                                 getattr(self.rl_manager.agents.get(s, None), 'training_step', 0) < 400)
        
            print("🤖 RL STATUS (DOUBLE DQN AKTIV):")
            print("─" * 35)
            if self.rl_manager:
                print(f"✅ RL Manager aktiv")
                print(f"📊 Trainierte Agents: {len(self.rl_manager.agents)}")
                print(f"🎯 Training Modus: {'✅' if self.rl_training_mode else '❌'}")
                print(f"💱 Auto-Trading Symbole: {', '.join(auto_symbols[:3])}")
                if len(auto_symbols) > 3:
                    print(f"                        + {len(auto_symbols)-3} weitere")
                print(f"🎯 Benötigt Training: {untrained_count}")
            
                # Agent Status Header
                if self.rl_manager.agents:
                    print("\n📋 BEREITSCHAFT:")
                for symbol, agent in self.rl_manager.agents.items():
                    training_steps = getattr(agent, 'training_step', 0)
                    epsilon = getattr(agent, 'epsilon', 1.0)
                    status = "✅ READY" if training_steps >= 400 and epsilon < 0.1 else "🔄 LEARNING"
                    print(f"   {status} | {symbol}: {training_steps} Steps (ε={epsilon:.3f})")
            else:
                print("❌ RL Manager nicht verfügbar")
        
            print(f"\n⚡ QUICK ACTION:")
            print("─" * 35)
            if untrained_count > 0:
                print(f"Drücken Sie 'Q' für schnelles Batch-Training aller {untrained_count} fehlenden Agents!")
            else:
                print(f"✅ Alle Auto-Trading Agents sind ausreichend trainiert.")
        
            print(f"\n🛠️ TRAINING & MANAGEMENT:")
            print("─" * 35)
            print(" 1. 🚀 Single Agent Training (Smart/Manual)")
            print(" 2. 🎯 Batch Training (Alle Symbole)")
            print(" 3. 📊 Training-Statistiken anzeigen")
            print(" 4. 💾 Modelle verwalten (Speichern/Laden)")
            print(" 5. ⚙️ RL-Parameter & Einstellungen")
        
            print(f"\n📈 LIVE TRADING & TESTS:")
            print("─" * 35)
            print(" 6. 🔄 RL Auto-Trading umschalten")
            print(" 7. 🧠 Live RL-Empfehlung testen")
            print(" 8. 📈 Performance-Vergleich (RL vs Klassisch)")
        
            print(f"\n❌ BEENDEN")
            print(" 9. ⬅️ Zurück zum Hauptmenü")
        
            choice = input(f"\n🎯 Ihre Wahl (1-9{', Q' if untrained_count > 0 else ''}): ").strip().upper()
        
            if choice == "Q" and untrained_count > 0:
                untrained_symbols = [s for s in auto_symbols if s not in self.rl_manager.agents or 
                                   getattr(self.rl_manager.agents.get(s, None), 'training_step', 0) < 400]
                print(f"\n⚡ QUICK TRAINING: {', '.join(untrained_symbols)}")
                confirm = input("Alle fehlenden Agents trainieren? (ja/nein): ").lower()
                if confirm == "ja":
                    self.batch_train_sequential(untrained_symbols, 300)
        
            elif choice == "1":
                self.train_rl_agent_enhanced()
            elif choice == "2":
                print(f"\n🔄 BATCH TRAINING FÜR ALLE SYMBOLE")
                print(f"Auto-Trading Symbole: {', '.join(auto_symbols)}")
                episodes = int(input("Episodes pro Symbol (Enter für 250): ") or "250")
                mode = input("Modus (sequential/parallel, Enter für sequential): ").lower() or "sequential"
                if mode == "parallel":
                    self.batch_train_parallel(auto_symbols, episodes)
                else:
                    self.batch_train_sequential(auto_symbols, episodes)
            elif choice == "3":
                self.show_rl_statistics()
            elif choice == "4":
                self.manage_rl_models()
            elif choice == "5":
                self.rl_settings()
            elif choice == "6":
                self.toggle_rl_auto_trading()
            elif choice == "7":
                self.test_rl_recommendation()
            elif choice == "8":
                self.compare_rl_performance()
            elif choice == "9":
                break
            else:
                print("❌ Ungültige Auswahl")
        
            input("\nDrücken Sie Enter zum Fortfahren...")

    def train_rl_agent_enhanced(self):
        """Erweiterte RL Agent Training mit automatischer Symbol-Auswahl"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
        
        print("\n🚀 RL AGENT TRAINING")
        print("─" * 25)
    
        # AUTO-SYMBOL DETECTION
        available_symbols = []
    
        # 1. Nutze aktuelle Auto-Trading Symbole
        if hasattr(self, 'auto_trade_symbols') and self.auto_trade_symbols:
            available_symbols.extend(self.auto_trade_symbols)
            print(f"📊 Auto-Trading Symbole gefunden: {', '.join(self.auto_trade_symbols)}")
    
        # 2. Ergänze um Standard-Majors falls leer
        if not available_symbols:
            available_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]
            print(f"📊 Standard Majors werden verwendet: {', '.join(available_symbols)}")
    
        # 3. Filtere bereits trainierte Agents
        untrained_symbols = []
        trained_symbols = []
    
        for symbol in available_symbols:
            if symbol in self.rl_manager.agents:
                agent = self.rl_manager.agents[symbol]
                training_steps = getattr(agent, 'training_step', 0)
                epsilon = getattr(agent, 'epsilon', 1.0)
            
                if training_steps < 400 or epsilon > 0.1:  # Noch nicht gut trainiert
                    untrained_symbols.append(symbol)
                else:
                    trained_symbols.append(symbol)
            else:
                untrained_symbols.append(symbol)
    
        print(f"\n📈 TRAINING STATUS:")
        if trained_symbols:
            print(f"✅ Gut trainiert: {', '.join(trained_symbols)}")
        if untrained_symbols:
            print(f"🎯 Benötigt Training: {', '.join(untrained_symbols)}")
    
        # AUSWAHL-OPTIONEN
        print(f"\n📋 TRAINING OPTIONEN:")
        print("─" * 25)
        print("1. 🤖 Alle untrainierten Symbole automatisch trainieren")
        print("2. 🎯 Spezifisches Symbol wählen")
        print("3. 📊 Nur die besten 3 Symbole trainieren")
        print("4. 🔄 Alle neu trainieren (überschreiben)")
        print("5. ⬅️ Zurück")
    
        choice = input("\nWählen (1-5): ").strip()
    
        if choice == "1":
            # Automatisches Training aller untrainierten
            if not untrained_symbols:
                print("✅ Alle Symbole sind bereits gut trainiert!")
                return
        
            print(f"\n🚀 BATCH TRAINING")
            print(f"Symbole: {', '.join(untrained_symbols)}")
        
            episodes = int(input("Episodes pro Symbol (Enter für 300): ") or "300")
            parallel = input("Parallel trainieren? (ja/nein): ").lower() == "ja"
        
            if parallel:
                self.batch_train_parallel(untrained_symbols, episodes)
            else:
                self.batch_train_sequential(untrained_symbols, episodes)
    
        elif choice == "2":
            # Manuelle Symbol-Auswahl mit Auto-Complete
            print(f"\n💱 VERFÜGBARE SYMBOLE:")
            for i, symbol in enumerate(available_symbols, 1):
                status = "✅" if symbol in trained_symbols else "🎯"
                agent_info = ""
                if symbol in self.rl_manager.agents:
                    agent = self.rl_manager.agents[symbol]
                    steps = getattr(agent, 'training_step', 0)
                    epsilon = getattr(agent, 'epsilon', 1.0)
                    agent_info = f"(Steps: {steps}, ε: {epsilon:.3f})"
            
                print(f"   {i}. {status} {symbol} {agent_info}")
        
            print("   0. ✍️ Manuell eingeben")
        
            try:
                symbol_choice = input(f"\nSymbol wählen (0-{len(available_symbols)}): ").strip()
            
                if symbol_choice == "0":
                    symbol = input("Symbol eingeben: ").upper().strip()
                else:
                    symbol_idx = int(symbol_choice) - 1
                    if 0 <= symbol_idx < len(available_symbols):
                        symbol = available_symbols[symbol_idx]
                    else:
                        print("❌ Ungültige Auswahl")
                        return
            
                if symbol:
                    episodes = int(input("Anzahl Episodes (Enter für 500): ") or "500")
                    self.train_single_agent(symbol, episodes)
                
            except ValueError:
                print("❌ Ungültige Eingabe")
    
        elif choice == "3":
            # Top 3 Symbole automatisch
            top_symbols = ["EURUSD", "GBPUSD", "USDJPY"]
            top_untrained = [s for s in top_symbols if s in untrained_symbols]
        
            if top_untrained:
                print(f"\n🏆 TOP 3 TRAINING: {', '.join(top_untrained)}")
                episodes = int(input("Episodes pro Symbol (Enter für 400): ") or "400")
                self.batch_train_sequential(top_untrained, episodes)
            else:
                print("✅ Top 3 Symbole sind bereits trainiert!")
    
        elif choice == "4":
            # Alle neu trainieren
            confirm = input(f"\n⚠️ ALLE {len(available_symbols)} Symbole neu trainieren? (JA/nein): ")
            if confirm == "JA":
                episodes = int(input("Episodes pro Symbol (Enter für 200): ") or "200")
                self.batch_train_sequential(available_symbols, episodes)
    
        elif choice == "5":
            return
    
    def batch_train_sequential(self, symbols, episodes):
        """Trainiert mehrere Symbole nacheinander"""
    
        print(f"\n🔄 SEQUENZIELLES BATCH TRAINING")
        print(f"Symbole: {len(symbols)} | Episodes: {episodes} pro Symbol")
        print(f"Geschätzte Gesamtdauer: {len(symbols) * episodes // 50} Minuten")
    
        confirm = input("\nStarten? (ja/nein): ").lower()
        if confirm != "ja":
            return
    
        def batch_worker():
            try:
                for i, symbol in enumerate(symbols, 1):
                    print(f"\n🎯 [{i}/{len(symbols)}] Training {symbol}...")
                    success = self.rl_manager.train_agent(symbol, episodes)
                
                    if success:
                        # Automatisch speichern
                        model_path = f"{self.rl_manager.model_directory}/{symbol}_batch_{episodes}.h5"
                        self.rl_manager.agents[symbol].save_model(model_path)
                        print(f"✅ {symbol} abgeschlossen und gespeichert")
                    else:
                        print(f"❌ {symbol} fehlgeschlagen")
                
                    # Kurze Pause zwischen Trainings
                    if i < len(symbols):
                        print("⏸️ Kurze Pause...")
                        time.sleep(2)
            
                print(f"\n🎉 BATCH TRAINING ABGESCHLOSSEN!")
                print(f"✅ {len(symbols)} Symbole trainiert")
            
            except Exception as e:
                print(f"💥 Batch Training Fehler: {e}")
    
        # Training in separatem Thread
        training_thread = threading.Thread(target=batch_worker, daemon=True)
        training_thread.start()
    
        print("🔄 Batch Training läuft im Hintergrund...")
        print("💡 Sie können andere Menüs verwenden")

    def batch_train_parallel(self, symbols, episodes):
        """Trainiert mehrere Symbole parallel (experimentell)"""
    
        print(f"\n⚡ PARALLELES TRAINING (EXPERIMENTELL)")
        print(f"⚠️ Warnung: Sehr ressourcenintensiv!")
    
        max_parallel = min(3, len(symbols))  # Maximal 3 parallel
        print(f"📊 Parallel: {max_parallel} Symbole gleichzeitig")
    
        confirm = input("Wirklich parallel trainieren? (ja/nein): ").lower()
        if confirm != "ja":
            self.batch_train_sequential(symbols, episodes)
            return
    
        import concurrent.futures
    
        def train_worker(symbol):
            try:
                return self.rl_manager.train_agent(symbol, episodes)
            except Exception as e:
                print(f"❌ {symbol} Parallel-Training Fehler: {e}")
                return False
    
        def parallel_worker():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
                    # Starte alle Trainings
                    futures = {executor.submit(train_worker, symbol): symbol for symbol in symbols}
                
                    # Warte auf Ergebnisse
                    for future in concurrent.futures.as_completed(futures):
                        symbol = futures[future]
                        try:
                            success = future.result()
                            if success:
                                print(f"✅ {symbol} parallel Training abgeschlossen")
                            else:
                                print(f"❌ {symbol} parallel Training fehlgeschlagen")
                        except Exception as e:
                            print(f"❌ {symbol} parallel Fehler: {e}")
            
                print(f"🎉 PARALLEL TRAINING ABGESCHLOSSEN!")
            
            except Exception as e:
                print(f"💥 Parallel Training Fehler: {e}")
    
        # Parallel Training starten
        parallel_thread = threading.Thread(target=parallel_worker, daemon=True)
        parallel_thread.start()
    
        print("⚡ Parallel Training läuft im Hintergrund...")

    def train_single_agent(self, symbol, episodes):
        """Trainiert einen einzelnen Agent mit verbesserter UI"""
    
        print(f"\n🎯 EINZELTRAINING: {symbol}")
        print("─" * 30)
    
        # Status-Check
        if symbol in self.rl_manager.agents:
            agent = self.rl_manager.agents[symbol]
            current_steps = getattr(agent, 'training_step', 0)
            current_epsilon = getattr(agent, 'epsilon', 1.0)
        
            print(f"📊 Aktueller Status:")
            print(f"   Steps: {current_steps}")
            print(f"   Epsilon: {current_epsilon:.3f}")
        
            if current_steps > 400 and current_epsilon < 0.1:
                override = input("⚠️ Agent bereits gut trainiert. Überschreiben? (ja/nein): ").lower()
                if override != "ja":
                    return
    
        print(f"📊 Training Setup:")
        print(f"   Symbol: {symbol}")
        print(f"   Episodes: {episodes}")
        print(f"   Geschätzte Dauer: {episodes//50} Minuten")
    
        confirm = input("\nTraining starten? (ja/nein): ").lower()
        if confirm != "ja":
            return
    
        # Training mit Progress
        def training_worker():
            try:
                print(f"🤖 Starte Training für {symbol}...")
                success = self.rl_manager.train_agent(symbol, episodes)
            
                if success:
                    print(f"✅ Training für {symbol} erfolgreich!")
                
                    # Auto-Save mit Timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    model_path = f"{self.rl_manager.model_directory}/{symbol}_{timestamp}.h5"
                    self.rl_manager.agents[symbol].save_model(model_path)
                    print(f"💾 Modell gespeichert: {model_path}")
                else:
                    print(f"❌ Training für {symbol} fehlgeschlagen")
                
            except Exception as e:
                print(f"💥 Training Fehler: {e}")
    
        # Training starten
        training_thread = threading.Thread(target=training_worker, daemon=True)
        training_thread.start()
    
        print("🔄 Training läuft im Hintergrund...")

    def auto_detect_trading_symbols(self):
        """Automatische Erkennung der zu trainierenden Symbole"""
    
        symbols = set()
    
        # 1. Auto-Trading Symbole
        if hasattr(self, 'auto_trade_symbols') and self.auto_trade_symbols:
            symbols.update(self.auto_trade_symbols)
    
        # 2. Favoriten
        if hasattr(self, 'custom_pairs') and 'user_favorites' in self.custom_pairs:
            symbols.update(self.custom_pairs['user_favorites']['pairs'])
    
        # 3. Aktuelle offene Positionen
        if self.mt5_connected:
            try:
                positions = mt5.positions_get()  # type: ignore[attr-defined]
                if positions:
                    for pos in positions:
                        symbols.add(pos.symbol)
            except:
                pass
    
        # 4. Standard-Fallback
        if not symbols:
            symbols = {"EURUSD", "GBPUSD", "USDJPY"}
    
        return sorted(list(symbols))

    def test_rl_recommendation(self):
        """Testet RL-Empfehlung für Symbol"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
    
        print("\n🧠 RL EMPFEHLUNG TESTEN")
        print("─" * 25)
    
        if not self.rl_manager.agents:
            print("❌ Keine trainierten Agents verfügbar")
            print("💡 Trainieren Sie zuerst einen Agent (Option 1)")
            return
    
        # Verfügbare Agents anzeigen
        print("📊 Verfügbare Agents:")
        for i, symbol in enumerate(self.rl_manager.agents.keys(), 1):
            agent = self.rl_manager.agents[symbol]
            steps = getattr(agent, 'training_step', 0)
            print(f"   {i}. {symbol} ({steps} Trainingssteps)")
    
        # Symbol auswählen
        symbol = input("\nSymbol für Test: ").upper().strip()
        if symbol not in self.rl_manager.agents:
            print(f"❌ Kein trainierter Agent für {symbol}")
            return
    
        try:
            print(f"🔍 Hole RL-Empfehlung für {symbol}...")
        
            # RL Empfehlung
            rl_result = self.rl_manager.get_rl_recommendation(symbol)
        
            if rl_result:
                print(f"\n🤖 RL EMPFEHLUNG:")
                print("─" * 20)
                print(f"📊 Aktion: {rl_result['recommendation']}")
                print(f"🎯 Konfidenz: {rl_result['confidence']:.1f}%")
                print(f"💡 Begründung: {rl_result['reasoning']}")
            
                if rl_result['q_values']:
                    print(f"\n📈 Q-Values:")
                    actions = ['HOLD', 'BUY', 'SELL']
                    for i, (action, q_val) in enumerate(zip(actions, rl_result['q_values'])):
                        print(f"   {action}: {q_val:.4f}")
            
                # Vergleiche mit traditionellen Indikatoren
                print(f"\n📊 VERGLEICH MIT TRADITIONELLEN INDIKATOREN:")
                print("─" * 45)
            
                # RSI
                rsi = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
                rsi_signal = None  # Initialize to avoid unbound variable
                if rsi:
                    rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi)
                    print(f"📈 RSI: {rsi_signal} ({rsi_desc})")
            
                # MACD
                macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
                macd_signal = None  # Initialize to avoid unbound variable
                if macd_data:
                    macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
                    print(f"📊 MACD: {macd_signal} ({macd_desc[:30]}...)")
            
                # Consensus
                signals = []
                if rsi and rsi_signal in ['BUY', 'SELL']:
                    signals.append(rsi_signal)
                if macd_data and macd_signal in ['BUY', 'SELL']:
                    signals.append(macd_signal)
            
                rl_signal = rl_result['recommendation']
                signals.append(rl_signal)
            
                buy_count = signals.count('BUY')
                sell_count = signals.count('SELL')
            
                print(f"\n🎯 CONSENSUS:")
                print(f"   BUY Signale: {buy_count}")
                print(f"   SELL Signale: {sell_count}")
                print(f"   RL Gewichtung: {self.rl_recommendation_weight}")
            
                if buy_count > sell_count:
                    consensus = "BUY"
                elif sell_count > buy_count:
                    consensus = "SELL"
                else:
                    consensus = "NEUTRAL"
            
                print(f"   Consensus: {consensus}")
            
            else:
                print("❌ RL-Empfehlung konnte nicht abgerufen werden")
            
        except Exception as e:
            print(f"❌ Fehler beim Testen: {e}")

    def show_rl_statistics(self):
        """Zeigt RL Training-Statistiken"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
    
        print("\n📊 RL TRAINING-STATISTIKEN")
        print("─" * 30)
    
        if not self.rl_manager.training_stats:
            print("❌ Keine Statistiken verfügbar")
            print("💡 Trainieren Sie zuerst einen Agent")
            return
    
        for symbol, stats in self.rl_manager.training_stats.items():
            print(f"\n🎯 {symbol}:")
            print(f"   Episodes: {stats['episodes']}")
            print(f"   Finaler Reward: {stats['final_reward']:.2f}")
            print(f"   Durchschnitt: {stats['avg_reward']:.2f}")
            print(f"   Bester Reward: {stats['best_reward']:.2f}")
        
            # Agent Info
            if symbol in self.rl_manager.agents:
                agent = self.rl_manager.agents[symbol]
                print(f"   Training Steps: {getattr(agent, 'training_step', 0)}")
                print(f"   Epsilon: {getattr(agent, 'epsilon', 0):.4f}")
                print(f"   Memory Size: {len(getattr(agent, 'memory', []))}")

    def manage_rl_models(self):
        """Verwaltet RL Modelle (Speichern/Laden)"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
    
        print("\n💾 RL MODELL-VERWALTUNG")
        print("─" * 25)
    
        print("1. 💾 Modell speichern")
        print("2. 📁 Modell laden")
        print("3. 📂 Verfügbare Modelle anzeigen")
        print("4. 🗑️ Modell löschen")
    
        choice = input("\nWählen (1-4): ").strip()
    
        if choice == "1":
            # Modell speichern
            if not self.rl_manager.agents:
                print("❌ Keine Agents zum Speichern")
                return
        
            print("\n📊 Verfügbare Agents:")
            for symbol in self.rl_manager.agents.keys():
                print(f"   - {symbol}")
        
            symbol = input("Symbol zum Speichern: ").upper().strip()
            if symbol in self.rl_manager.agents:
                filename = input(f"Dateiname (Enter für {symbol}_manual.h5): ").strip()
                if not filename:
                    filename = f"{symbol}_manual.h5"
            
                if not filename.endswith('.h5'):
                    filename += '.h5'
            
                filepath = f"{self.rl_manager.model_directory}/{filename}"
                self.rl_manager.agents[symbol].save_model(filepath)
                print(f"✅ Modell gespeichert: {filepath}")
            else:
                print(f"❌ Kein Agent für {symbol}")
    
        elif choice == "2":
            # Modell laden
            import os
            models_dir = self.rl_manager.model_directory
        
            if not os.path.exists(models_dir):
                print(f"❌ Model Directory nicht gefunden: {models_dir}")
                return
        
            # Verfügbare Modelle anzeigen
            model_files = [f for f in os.listdir(models_dir) if f.endswith('.h5')]
        
            if not model_files:
                print("❌ Keine gespeicherten Modelle gefunden")
                return
        
            print("\n📁 Verfügbare Modelle:")
            for i, model_file in enumerate(model_files, 1):
                print(f"   {i}. {model_file}")
        
            try:
                model_choice = int(input(f"\nModell wählen (1-{len(model_files)}): ")) - 1
                if 0 <= model_choice < len(model_files):
                    selected_model = model_files[model_choice]
                    filepath = os.path.join(models_dir, selected_model)
                
                    # Symbol extrahieren
                    symbol = selected_model.split('_')[0].upper()
                
                    # Agent erstellen wenn nicht vorhanden
                    if symbol not in self.rl_manager.agents:
                        success = self.rl_manager.initialize_agent(symbol)
                        if not success:
                            print(f"❌ Agent Initialisierung für {symbol} fehlgeschlagen")
                            return
                
                    # Modell laden
                    success = self.rl_manager.agents[symbol].load_model(filepath)
                    if success:
                        print(f"✅ Modell geladen für {symbol}")
                    else:
                        print(f"❌ Fehler beim Laden des Modells")
                else:
                    print("❌ Ungültige Auswahl")
            except ValueError:
                print("❌ Ungültige Eingabe")
    
        elif choice == "3":
            # Verfügbare Modelle anzeigen
            import os
            models_dir = self.rl_manager.model_directory
        
            if os.path.exists(models_dir):
                model_files = [f for f in os.listdir(models_dir) if f.endswith('.h5')]
            
                if model_files:
                    print(f"\n📂 Modelle in {models_dir}:")
                    for model_file in model_files:
                        filepath = os.path.join(models_dir, model_file)
                        size = os.path.getsize(filepath) / 1024  # KB
                        modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                        print(f"   📄 {model_file} ({size:.1f} KB, {modified.strftime('%d.%m.%Y %H:%M')})")
                else:
                    print("❌ Keine Modelle gefunden")
            else:
                print(f"❌ Model Directory nicht gefunden: {models_dir}")

    def rl_settings(self):
        """RL Einstellungen verwalten — vollständige GUI-Parität"""

        while True:
            self.print_header("⚙️ RL EINSTELLUNGEN")

            print("📌 AKTUELLE KONFIGURATION:")
            print("─" * 45)
            print(f"   Algorithmus           : {self.rl_algorithm}")
            print(f"   Lernrate              : {self.rl_learning_rate:.5f}")
            print(f"   Gamma (Discount)      : {self.rl_gamma:.2f}")
            print(f"   Training Steps        : {self.rl_training_steps}")
            print(f"   Belohnungsfunktion    : {self.rl_reward_function}")
            print(f"   Replay Buffer Size    : {self.rl_buffer_size}")
            print(f"   Batch Size            : {self.rl_batch_size}")
            print(f"   Epochs (PPO)          : {self.rl_epochs}")
            print(f"   Target Update (DQN)   : {self.rl_target_update}")
            print(f"   Epsilon Start         : {self.rl_epsilon_start:.2f}")
            print(f"   Epsilon Min           : {self.rl_epsilon_min:.3f}")
            print(f"   Epsilon Decay         : {self.rl_epsilon_decay:.4f}")
            print(f"   Training Timeframe    : {self.rl_training_timeframe}")
            print(f"   Training Bars         : {self.rl_training_bars}")
            print(f"   Netzwerk-Architektur  : {self.rl_nn_architecture}")
            print(f"   Checkpoint Pfad       : {self.rl_checkpoint_path}")
            print(f"   GPU Beschleunigung    : {'✅' if self.rl_use_gpu else '❌'}")
            print(f"   RL Live-Trading       : {'✅ (Experimentell)' if self.rl_live_trading_enabled else '❌'}")
            print(f"   Empfehlungsgewicht    : {self.rl_recommendation_weight}")
            if self.rl_manager:
                print(f"   Manager Episodes      : {self.rl_manager.training_episodes}")
                print(f"   Save Frequency        : {self.rl_manager.model_save_frequency}")

            print("\n🛠️  EDITIEROPTIONEN:")
            print("─" * 45)
            print("  1. 🤖 Algorithmus (PPO/DQN/A2C/SAC)")
            print("  2. 📈 Lernrate")
            print("  3. 🎯 Gamma (Discount-Faktor)")
            print("  4. 📊 Training Steps")
            print("  5. 🏆 Belohnungsfunktion")
            print("  6. 💾 Replay Buffer Size")
            print("  7. 📦 Batch Size")
            print("  8. 🔄 Epochs (PPO) & Target Update (DQN)")
            print("  9. 🎰 Epsilon (Start / Min / Decay)")
            print(" 10. ⏱️  Training Timeframe & Bars")
            print(" 11. 🧠 Netzwerk-Architektur")
            print(" 12. 💾 Checkpoint Pfad")
            print(" 13. 🖥️  GPU Beschleunigung umschalten")
            print(" 14. ⚡ RL Live-Trading umschalten")
            print(" 15. 🎯 RL Empfehlungsgewicht")
            print(" 16. 📊 Manager Training Episodes & Save Freq")
            print("  0. ⬅️  Zurück")

            choice = input("\n🎯 Ihre Wahl (0-16): ").strip()

            if choice == "0":
                break

            elif choice == "1":
                print("\nVerfügbar: PPO | DQN | A2C | SAC")
                val = input(f"Algorithmus (aktuell: {self.rl_algorithm}): ").strip().upper()
                if val in ["PPO", "DQN", "A2C", "SAC"]:
                    self.rl_algorithm = val
                    print(f"✅ Algorithmus → {self.rl_algorithm}")
                else:
                    print("❌ Ungültig — bitte PPO, DQN, A2C oder SAC eingeben")

            elif choice == "2":
                try:
                    val = float(input(f"Lernrate (aktuell: {self.rl_learning_rate:.5f}): ") or str(self.rl_learning_rate))
                    if 0.00001 <= val <= 0.1:
                        self.rl_learning_rate = val
                        print(f"✅ Lernrate → {self.rl_learning_rate:.5f}")
                    else:
                        print("❌ Lernrate muss zwischen 0.00001 und 0.1 liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "3":
                try:
                    val = float(input(f"Gamma (aktuell: {self.rl_gamma:.2f}, 0.8–1.0): ") or str(self.rl_gamma))
                    if 0.8 <= val <= 1.0:
                        self.rl_gamma = val
                        print(f"✅ Gamma → {self.rl_gamma:.2f}")
                    else:
                        print("❌ Gamma muss zwischen 0.8 und 1.0 liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "4":
                try:
                    val = int(input(f"Training Steps (aktuell: {self.rl_training_steps}): ") or str(self.rl_training_steps))
                    if val > 0:
                        self.rl_training_steps = val
                        print(f"✅ Training Steps → {self.rl_training_steps}")
                    else:
                        print("❌ Muss positiv sein")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "5":
                options = ["Profit + Sharpe Ratio", "Reiner Profit", "Sortino Ratio", "Custom"]
                print("Optionen:", " | ".join(f"{i+1}. {o}" for i, o in enumerate(options)))
                try:
                    idx = int(input("Wahl (1-4): ")) - 1
                    if 0 <= idx < len(options):
                        self.rl_reward_function = options[idx]
                        print(f"✅ Belohnungsfunktion → {self.rl_reward_function}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "6":
                try:
                    val = int(input(f"Replay Buffer Size (aktuell: {self.rl_buffer_size}): ") or str(self.rl_buffer_size))
                    if val >= 100:
                        self.rl_buffer_size = val
                        print(f"✅ Buffer Size → {self.rl_buffer_size}")
                    else:
                        print("❌ Mindestens 100")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "7":
                try:
                    val = int(input(f"Batch Size (aktuell: {self.rl_batch_size}): ") or str(self.rl_batch_size))
                    if val >= 8:
                        self.rl_batch_size = val
                        print(f"✅ Batch Size → {self.rl_batch_size}")
                    else:
                        print("❌ Mindestens 8")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "8":
                try:
                    ep = int(input(f"Epochs/PPO (aktuell: {self.rl_epochs}): ") or str(self.rl_epochs))
                    tu = int(input(f"Target Update/DQN (aktuell: {self.rl_target_update}): ") or str(self.rl_target_update))
                    self.rl_epochs = max(1, ep)
                    self.rl_target_update = max(1, tu)
                    print(f"✅ Epochs → {self.rl_epochs} | Target Update → {self.rl_target_update}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "9":
                try:
                    es = float(input(f"Epsilon Start (aktuell: {self.rl_epsilon_start:.2f}, 0.1–1.0): ") or str(self.rl_epsilon_start))
                    em = float(input(f"Epsilon Min (aktuell: {self.rl_epsilon_min:.3f}, 0.001–0.5): ") or str(self.rl_epsilon_min))
                    ed = float(input(f"Epsilon Decay (aktuell: {self.rl_epsilon_decay:.4f}, 0.990–0.9999): ") or str(self.rl_epsilon_decay))
                    if 0.1 <= es <= 1.0 and 0.001 <= em <= 0.5 and 0.99 <= ed <= 0.9999:
                        self.rl_epsilon_start = es
                        self.rl_epsilon_min = em
                        self.rl_epsilon_decay = ed
                        print(f"✅ Epsilon: Start={es:.2f} | Min={em:.3f} | Decay={ed:.4f}")
                    else:
                        print("❌ Werte außerhalb des gültigen Bereichs")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "10":
                tfs = ["M1", "M5", "M15", "M30", "H1", "H4"]
                print("Timeframes:", " | ".join(tfs))
                tf = input(f"Timeframe (aktuell: {self.rl_training_timeframe}): ").strip().upper()
                bars_raw = input(f"Training Bars (aktuell: {self.rl_training_bars}): ").strip()
                if tf in tfs:
                    self.rl_training_timeframe = tf
                    print(f"✅ Timeframe → {self.rl_training_timeframe}")
                elif tf:
                    print("❌ Ungültiger Timeframe")
                if bars_raw.isdigit() and int(bars_raw) >= 100:
                    self.rl_training_bars = int(bars_raw)
                    print(f"✅ Training Bars → {self.rl_training_bars}")

            elif choice == "11":
                archs = ["Klein (64-64)", "Mittel (128-128)", "Groß (256-256)"]
                print("Architekturen:", " | ".join(f"{i+1}. {a}" for i, a in enumerate(archs)))
                try:
                    idx = int(input("Wahl (1-3): ")) - 1
                    if 0 <= idx < len(archs):
                        self.rl_nn_architecture = archs[idx]
                        print(f"✅ Architektur → {self.rl_nn_architecture}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "12":
                path = input(f"Checkpoint Pfad (aktuell: {self.rl_checkpoint_path}): ").strip()
                if path:
                    self.rl_checkpoint_path = path
                    print(f"✅ Checkpoint Pfad → {self.rl_checkpoint_path}")

            elif choice == "13":
                self.rl_use_gpu = not self.rl_use_gpu
                print(f"✅ GPU Beschleunigung → {'aktiviert' if self.rl_use_gpu else 'deaktiviert'}")

            elif choice == "14":
                self.rl_live_trading_enabled = not self.rl_live_trading_enabled
                status = "aktiviert ⚠️ EXPERIMENTELL" if self.rl_live_trading_enabled else "deaktiviert"
                print(f"✅ RL Live-Trading → {status}")

            elif choice == "15":
                try:
                    val = float(input(f"Empfehlungsgewicht (aktuell: {self.rl_recommendation_weight}, 0.0–1.0): "))
                    if 0.0 <= val <= 1.0:
                        self.rl_recommendation_weight = val
                        print(f"✅ Empfehlungsgewicht → {self.rl_recommendation_weight}")
                    else:
                        print("❌ Wert außerhalb 0.0–1.0")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            elif choice == "16" and self.rl_manager:
                try:
                    ep = int(input(f"Manager Episodes (aktuell: {self.rl_manager.training_episodes}): ") or str(self.rl_manager.training_episodes))
                    sf = int(input(f"Save Frequency (aktuell: {self.rl_manager.model_save_frequency}): ") or str(self.rl_manager.model_save_frequency))
                    if 100 <= ep <= 100000:
                        self.rl_manager.training_episodes = ep
                    if 10 <= sf <= 5000:
                        self.rl_manager.model_save_frequency = sf
                    print(f"✅ Episodes → {self.rl_manager.training_episodes} | Save Freq → {self.rl_manager.model_save_frequency}")
                except ValueError:
                    print("❌ Ungültige Eingabe")

            else:
                print("❌ Ungültige Auswahl")

            input("\nDrücken Sie Enter zum Fortfahren...")

    def toggle_rl_auto_trading(self):
        """Aktiviert/Deaktiviert RL Auto-Trading"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
    
        print("\n🔄 RL AUTO-TRADING")
        print("─" * 20)
    
        if not self.rl_manager.agents:
            print("❌ Keine trainierten Agents verfügbar")
            print("💡 Trainieren Sie zuerst einen Agent")
            return
    
        # Status anzeigen
        print(f"Status: {'✅ Aktiviert' if self.rl_training_mode else '❌ Deaktiviert'}")
        print(f"Verfügbare Agents: {list(self.rl_manager.agents.keys())}")
    
        if self.rl_training_mode:
            choice = input("RL Auto-Trading deaktivieren? (ja/nein): ").lower()
            if choice == "ja":
                self.rl_training_mode = False
                print("✅ RL Auto-Trading deaktiviert")
        else:
            choice = input("RL Auto-Trading aktivieren? (ja/nein): ").lower()
            if choice == "ja":
                self.rl_training_mode = True
                print("✅ RL Auto-Trading aktiviert")
                print("💡 RL-Empfehlungen werden nun in Auto-Trading berücksichtigt")

    def compare_rl_performance(self):
        """Vergleicht RL Performance mit traditionellen Methoden"""
        
        # Prüfe ob RL Manager verfügbar ist
        if not self.rl_manager:
            print("\n❌ RL Manager nicht verfügbar")
            return
    
        print("\n📈 PERFORMANCE VERGLEICH")
        print("─" * 30)
    
        if not self.rl_manager.agents:
            print("❌ Keine trainierten Agents für Vergleich")
            return
    
        symbol = input("Symbol für Vergleich: ").upper().strip()
        if symbol not in self.rl_manager.agents:
            print(f"❌ Kein RL Agent für {symbol}")
            return
    
        try:
            print(f"\n🔍 Vergleiche Methoden für {symbol}...")
        
            # RL Empfehlung
            rl_result = self.rl_manager.get_rl_recommendation(symbol)
        
            # Traditionelle Indikatoren
            rsi = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            sr_data = self.market.calculate_support_resistance(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            
            # Initialize current_price to avoid unbound variable
            current_price = None
        
            print(f"\n📊 SIGNALE VERGLEICH:")
            print("─" * 25)
        
            # RL
            if rl_result:
                print(f"🤖 RL Agent: {rl_result['recommendation']} (Konfidenz: {rl_result['confidence']:.1f}%)")
        
            # RSI
            if rsi:
                rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi)
                print(f"📈 RSI: {rsi_signal} ({rsi})")
        
            # MACD
            if macd_data:
                macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
                print(f"📊 MACD: {macd_signal}")
        
            # Support/Resistance
            if sr_data:
                current_price = sr_data['current_price']
                sr_signal, sr_desc = self.market.get_sr_signal(sr_data, current_price)
                print(f"🎯 S/R: {sr_signal}")
        
            # Consensus Berechnung
            signals = []
            if rl_result:
                signals.append(('RL', rl_result['recommendation'], self.rl_recommendation_weight))
            if rsi:
                rsi_signal, _ = self.market.get_rsi_signal(rsi)
                signals.append(('RSI', rsi_signal, 0.2))
            if macd_data:
                macd_signal, _ = self.market.get_macd_signal(macd_data)
                signals.append(('MACD', macd_signal, 0.3))
            if sr_data:
                sr_signal, _ = self.market.get_sr_signal(sr_data, current_price)
                signals.append(('S/R', sr_signal, 0.2))
        
            # Gewichteter Consensus
            buy_weight = sum(weight for method, signal, weight in signals if signal == 'BUY')
            sell_weight = sum(weight for method, signal, weight in signals if signal == 'SELL')
        
            print(f"\n🎯 GEWICHTETER CONSENSUS:")
            print(f"   BUY Gewicht: {buy_weight:.2f}")
            print(f"   SELL Gewicht: {sell_weight:.2f}")
        
            if buy_weight > sell_weight:
                final_recommendation = "BUY"
                confidence = buy_weight / (buy_weight + sell_weight) * 100
            elif sell_weight > buy_weight:
                final_recommendation = "SELL" 
                confidence = sell_weight / (buy_weight + sell_weight) * 100
            else:
                final_recommendation = "NEUTRAL"
                confidence = 50
        
            print(f"   Final: {final_recommendation} (Konfidenz: {confidence:.1f}%)")
        
            # RL Vorteil hervorheben
            print(f"\n🤖 RL VORTEILE:")
            print("   • Lernt aus historischen Mustern")
            print("   • Berücksichtigt komplexe Interaktionen")
            print("   • Passt sich an Marktveränderungen an")
            print("   • Optimiert für maximale Profitabilität")
        
        except Exception as e:
            print(f"❌ Vergleich Fehler: {e}")

    # ==========================================
    # 7. CURRENCY & ACCOUNT MANAGEMENT
    # ==========================================
    def currency_pair_management_menu(self):
        """Vollständiges Währungspaar-Management ohne externe Abhängigkeiten"""
    
        # NOTFALL-INITIALISIERUNG (falls Attribute fehlen)
        if not hasattr(self, 'custom_pairs'):
            self.custom_pairs = {
                "user_favorites": {
                    "name": "Meine Favoriten",
                    "pairs": [],
                    "description": "Ihre persönlichen Lieblings-Paare"
                }
            }
    
        # Vordefinierte Listen direkt hier
        predefined_lists = {
            "major": {
                "name": "Majors (Hauptwährungspaare)",
                "pairs": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"],
                "description": "Die 7 wichtigsten Forex-Paare"
            },
            "eur_cross": {
                "name": "EUR Cross-Paare", 
                "pairs": ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD"],
                "description": "Euro-basierte Währungspaare"
            },
            "gbp_cross": {
                "name": "GBP Cross-Paare",
                "pairs": ["GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD"],
                "description": "Pfund-basierte Währungspaare"
            },
            "conservative": {
                "name": "Konservative Auswahl",
                "pairs": ["EURUSD", "GBPUSD", "USDCHF"],
                "description": "Stabile, gut vorhersagbare Paare"
            },
            "volatile": {
                "name": "Volatile Paare",
                "pairs": ["GBPJPY", "GBPAUD", "EURJPY", "AUDJPY", "GBPNZD"],
                "description": "Hochvolatile Paare für erfahrene Trader"
            },
            "safe_haven": {
                "name": "Safe Haven",
                "pairs": ["USDCHF", "USDJPY", "CHFJPY", "XAUUSD"],
                "description": "Sichere Häfen"
            }
        }
    
        while True:
            self.print_header("WÄHRUNGSPAAR MANAGEMENT")
        
            print("📋 AKTUELLE KONFIGURATION:")
            print("─" * 40)
        
            if hasattr(self, 'auto_trade_symbols') and self.auto_trade_symbols:
                print(f"📊 Auto-Trading Paare: {len(self.auto_trade_symbols)}")
                for i, symbol in enumerate(self.auto_trade_symbols[:5], 1):
                    print(f"   {i}. {symbol}")
                if len(self.auto_trade_symbols) > 5:
                    print(f"   ... und {len(self.auto_trade_symbols) - 5} weitere")
            else:
                print("❌ Keine Auto-Trading Paare konfiguriert")
        
            favorites = self.custom_pairs["user_favorites"]["pairs"]
            if favorites:
                print(f"💾 Favoriten: {len(favorites)} - {', '.join(favorites[:3])}")
                if len(favorites) > 3:
                    print(f"            ... und {len(favorites) - 3} weitere")
        
            print(f"\n📋 OPTIONEN:")
            print("─" * 15)
            print(" 1. 🔧 Vordefinierte Liste wählen")
            print(" 2. ✍️ Manuell eingeben")
            print(" 3. 💾 Favoriten verwalten")
            print(" 4. 📊 Verfügbare Paare anzeigen")
            print(" 5. 🔍 Paar-Verfügbarkeit prüfen")
            print(" 6. 📈 Performance-Analyse")
            print(" 7. ⬅️ Zurück")
        
            choice = input("\n🎯 Ihre Wahl (1-7): ").strip()
        
            if choice == "1":
                # Vordefinierte Listen anzeigen
                print(f"\n📋 VORDEFINIERTE LISTEN:")
                print("─" * 30)
            
                list_options = {}
                counter = 1
            
                for key, config in predefined_lists.items():
                    list_options[str(counter)] = (key, config)
                    print(f" {counter}. {config['name']} ({len(config['pairs'])} Paare)")
                    print(f"    💡 {config['description']}")
                    if len(config['pairs']) <= 7:
                        print(f"    💱 {', '.join(config['pairs'])}")
                    else:
                        print(f"    💱 {', '.join(config['pairs'][:5])}...")
                    print()
                    counter += 1
            
                print(" 0. ⬅️ Zurück")
            
                list_choice = input(f"Wählen Sie eine Liste (0-{counter-1}): ").strip()
            
                if list_choice == "0":
                    continue
                elif list_choice in list_options:
                    key, config = list_options[list_choice]
                
                    # Verfügbarkeits-Check
                    available_pairs = config['pairs'].copy()
                    unavailable_pairs = []
                
                    if self.mt5_connected:
                        print(f"\n🔍 Prüfe Verfügbarkeit...")
                        available_pairs = []
                    
                        for pair in config['pairs']:
                            symbol_info = mt5.symbol_info(pair)
                            if symbol_info and symbol_info.visible:
                                available_pairs.append(pair)
                            else:
                                unavailable_pairs.append(pair)
                    
                        print(f"✅ Verfügbar: {len(available_pairs)}/{len(config['pairs'])}")
                        if unavailable_pairs:
                            print(f"❌ Nicht verfügbar: {', '.join(unavailable_pairs)}")
                
                    if available_pairs:
                        print(f"\n📊 {config['name']}")
                        print(f"💱 Verfügbare Paare: {', '.join(available_pairs)}")
                    
                        confirm = input("\nDiese Auswahl für Auto-Trading verwenden? (ja/nein): ").lower()
                        if confirm == "ja":
                            self.auto_trade_symbols = available_pairs
                            print(f"✅ {len(available_pairs)} Paare für Auto-Trading aktiviert!")
                        
                            # Optional zu Favoriten hinzufügen
                            save_fav = input("Auswahl zu Favoriten hinzufügen? (ja/nein): ").lower()
                            if save_fav == "ja":
                                for pair in available_pairs:
                                    if pair not in favorites:
                                        favorites.append(pair)
                                print("✅ Zu Favoriten hinzugefügt")
                    else:
                        print("❌ Keine verfügbaren Paare in dieser Liste")
                else:
                    print("❌ Ungültige Auswahl")
                
            elif choice == "2":
                # Manuelle Eingabe
                print(f"\n✍️ MANUELLE EINGABE:")
                print("─" * 25)
                print("💡 Formate:")
                print("   • Einzeln: EURUSD")
                print("   • Mehrere: EURUSD,GBPUSD,USDJPY")
                print("   • Mit Leerzeichen: EURUSD GBPUSD USDJPY")
            
                user_input = input("\n💱 Währungspaare eingeben: ").upper().strip()
            
                if user_input:
                    # Parse Input
                    if ',' in user_input:
                        pairs = [p.strip() for p in user_input.split(',')]
                    else:
                        pairs = user_input.split()
                
                    # Validierung
                    valid_pairs = []
                    invalid_pairs = []
                
                    for pair in pairs:
                        if pair:
                            if self.mt5_connected:
                                symbol_info = mt5.symbol_info(pair)
                                if symbol_info and symbol_info.visible:
                                    valid_pairs.append(pair)
                                else:
                                    invalid_pairs.append(pair)
                            else:
                                valid_pairs.append(pair)
                
                    print(f"\n📊 VALIDIERUNG:")
                    if valid_pairs:
                        print(f"✅ Gültig: {len(valid_pairs)} - {', '.join(valid_pairs)}")
                    if invalid_pairs:
                        print(f"❌ Ungültig: {len(invalid_pairs)} - {', '.join(invalid_pairs)}")
                
                    if valid_pairs:
                        confirm = input(f"\n{len(valid_pairs)} gültige Paare verwenden? (ja/nein): ").lower()
                        if confirm == "ja":
                            self.auto_trade_symbols = valid_pairs
                            print(f"✅ {len(valid_pairs)} Paare aktiviert!")
                    else:
                        print("❌ Keine gültigen Paare")
                else:
                    print("❌ Keine Eingabe")
                
            elif choice == "3":
                # Favoriten verwalten
                self.manage_favorite_pairs_simple()
            
            elif choice == "4":
                # Verfügbare Paare anzeigen
                self.show_available_pairs_simple()
            
            elif choice == "5":
                # Verfügbarkeit prüfen
                self.check_pair_availability_simple()
            
            elif choice == "6":
                # Performance-Analyse
                self.analyze_pair_performance_simple()
            
            elif choice == "7":
                break
            
            else:
                print("❌ Ungültige Auswahl")
        
            input("\nDrücken Sie Enter zum Fortfahren...")

    def manage_favorite_pairs_simple(self):
        """Vereinfachte Favoriten-Verwaltung"""
    
        favorites = self.custom_pairs["user_favorites"]["pairs"]
    
        while True:
            print(f"\n💾 FAVORITEN VERWALTEN:")
            print("─" * 25)
        
            if favorites:
                print("📋 Aktuelle Favoriten:")
                for i, pair in enumerate(favorites, 1):
                    print(f"   {i}. {pair}")
            else:
                print("📋 Keine Favoriten gespeichert")
        
            print(f"\nOptionen:")
            print("1. ➕ Favorit hinzufügen")
            print("2. ➖ Favorit entfernen") 
            print("3. 🔄 Favoriten für Auto-Trading verwenden")
            print("4. 🗑️ Alle Favoriten löschen")
            print("5. ⬅️ Zurück")
        
            choice = input("\nWählen (1-5): ").strip()
        
            if choice == "1":
                new_pair = input("Währungspaar eingeben: ").upper().strip()
                if new_pair and new_pair not in favorites:
                    favorites.append(new_pair)
                    print(f"✅ {new_pair} zu Favoriten hinzugefügt")
                else:
                    print("❌ Ungültiges Paar oder bereits vorhanden")
        
            elif choice == "2":
                if favorites:
                    try:
                        index = int(input("Nummer zum Entfernen: ")) - 1
                        if 0 <= index < len(favorites):
                            removed = favorites.pop(index)
                            print(f"✅ {removed} entfernt")
                        else:
                            print("❌ Ungültige Nummer")
                    except ValueError:
                        print("❌ Ungültige Eingabe")
                else:
                    print("❌ Keine Favoriten vorhanden")
        
            elif choice == "3":
                if favorites:
                    self.auto_trade_symbols = favorites.copy()
                    print(f"✅ {len(favorites)} Favoriten für Auto-Trading aktiviert")
                    return
                else:
                    print("❌ Keine Favoriten vorhanden")
        
            elif choice == "4":
                if favorites:
                    confirm = input("Alle Favoriten löschen? (ja/nein): ").lower()
                    if confirm == "ja":
                        favorites.clear()
                        print("✅ Alle Favoriten gelöscht")
                else:
                    print("❌ Keine Favoriten vorhanden")
        
            elif choice == "5":
                break

    def show_available_pairs_simple(self):
        """Vereinfachte Anzeige verfügbarer Paare"""
    
        if not self.mt5_connected:
            print("❌ MT5 nicht verbunden - kann Verfügbarkeit nicht prüfen")
            return
    
        print("\n📊 VERFÜGBARE WÄHRUNGSPAARE:")
        print("─" * 35)
    
        try:
            symbols = mt5.symbols_get()  # type: ignore[attr-defined]
            if not symbols:
                print("❌ Keine Symbole gefunden")
                return
        
            # Nur Forex-Paare (6 Zeichen, nur Buchstaben)
            forex_pairs = [s.name for s in symbols if s.visible and len(s.name) == 6 and s.name.isalpha()]
        
            if forex_pairs:
                print(f"💱 Forex-Paare ({len(forex_pairs)}):")
                # Zeige in 4er-Spalten
                for i in range(0, len(forex_pairs), 4):
                    row = forex_pairs[i:i+4]
                    print("   " + "".join(f"{pair:<12}" for pair in row))
        
            print(f"\n📊 Gesamt verfügbare Forex-Paare: {len(forex_pairs)}")
        
        except Exception as e:
            print(f"❌ Fehler: {e}")

    def check_pair_availability_simple(self):
        """Vereinfachte Verfügbarkeits-Prüfung"""
    
        pairs_input = input("\n💱 Paare prüfen (kommagetrennt): ").upper().strip()
        if not pairs_input:
            return
    
        pairs = [p.strip() for p in pairs_input.split(',')]
    
        print(f"\n🔍 VERFÜGBARKEITS-CHECK:")
        print("─" * 30)
    
        for pair in pairs:
            if self.mt5_connected:
                symbol_info = mt5.symbol_info(pair)
                if symbol_info and symbol_info.visible:
                    tick = mt5.symbol_info_tick(pair)  # type: ignore[attr-defined]
                    if tick:
                        price = (tick.bid + tick.ask) / 2
                        print(f"✅ {pair:<10} Preis: {price:.5f}")
                    else:
                        print(f"⚠️ {pair:<10} Symbol OK, keine Preise")
                else:
                    print(f"❌ {pair:<10} Nicht verfügbar")
            else:
                print(f"❓ {pair:<10} MT5 nicht verbunden")

    def analyze_pair_performance_simple(self):
        """Vereinfachte Performance-Analyse"""
    
        if not hasattr(self, 'auto_trade_symbols') or not self.auto_trade_symbols:
            print("❌ Keine Auto-Trading Paare konfiguriert")
            return
    
        print(f"\n📈 PERFORMANCE-ANALYSE:")
        print("─" * 30)
    
        for symbol in self.auto_trade_symbols[:10]:
            try:
                if self.mt5_connected:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        # RSI berechnen
                        rsi = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1) if self.market and hasattr(self.market, 'calculate_rsi') else None
                        rsi_status = "📈" if rsi and rsi < 30 else "📉" if rsi and rsi > 70 else "📊"
                    
                        # Spread als Volatilitäts-Indikator
                        spread = tick.ask - tick.bid
                        vol_status = "🔥" if spread > 0.0003 else "🟢" if spread < 0.0001 else "🟡"
                    
                        print(f"{rsi_status} {symbol:<10} RSI: {rsi or 'N/A':<5} | Vol: {vol_status}")
                    else:
                        print(f"❌ {symbol:<10} Keine Daten")
                else:
                    print(f"❓ {symbol:<10} MT5 nicht verbunden")
            except Exception as e:
                print(f"⚠️ {symbol:<10} Fehler")
    
        print("\n💡 Legende: 📈 Überverkauft | 📉 Überkauft | 📊 Neutral")
        print("💡 Volatilität: 🔥 Hoch | 🟡 Normal | 🟢 Niedrig")

    def companion_menu(self):
        """Separates Trading Companion Menü"""
        while True:
            self.print_header("TRADING COMPANION")
            
            print(f"📊 Status: {'🟢 Aktiv' if self.companion_enabled else '🔴 Inaktiv'}")
            print(f"🔄 Auto-Start: {'✅ Ein' if self.auto_start_companion else '❌ Aus'}")
            
            if self.companion_enabled:
                print("🔧 Trading Companion ist bereit für erweiterte Analysen")
            else:
                print("❌ Trading Companion ist nicht verfügbar")
            
            print("\n📋 OPTIONEN:")
            print("─" * 25)
            print(" 1. 🔄 Starten/Stoppen")
            print(" 2. ⚙️ Auto-Start ein/aus")
            print(" 3. 📊 Erweiterte Analyse anfordern")
            print(" 4. 🔇 Silent Mode ein/aus")
            print(" 5. ⬅️ Zurück zum Hauptmenü")
            print("─" * 35)
            
            choice = input("🎯 Ihre Wahl (1-5): ").strip()
            
            if not choice:
                continue
            
            if choice == "1":
                if self.companion_enabled:
                    print("🔧 Stoppe Trading Companion...")
                    self.stop_trading_companion()
                else:
                    print("🔧 Starte Trading Companion...")
                    self.start_trading_companion()
                
                input("\n📝 Drücken Sie Enter zum Fortfahren...")
            
            elif choice == "2":
                self.auto_start_companion = not self.auto_start_companion
                status = "✅ Aktiviert" if self.auto_start_companion else "❌ Deaktiviert"
                print(f"🔄 Auto-Start: {status}")
                input("\n📝 Drücken Sie Enter zum Fortfahren...")
            
            elif choice == "3":
                if self.companion_enabled:
                    symbol = input("💱 Symbol für erweiterte Analyse: ").upper()
                    if symbol:
                        print("🔧 Fordere erweiterte Analyse an...")
                        self.request_companion_analysis(symbol)
                else:
                    print("❌ Trading Companion ist nicht aktiv")
                
                input("\n📝 Drücken Sie Enter zum Fortfahren...")
            
            elif choice == "4":
                self.companion_silent_mode = not self.companion_silent_mode
                status = "🔇 Ein" if self.companion_silent_mode else "🔊 Aus"
                print(f"Silent Mode: {status}")
                input("\n📝 Drücken Sie Enter zum Fortfahren...")
            
            elif choice == "5":
                break
            
            else:
                print("❌ Ungültige Auswahl")
                input("\n📝 Drücken Sie Enter zum Fortfahren...")

    # ==========================================
    # 8. TECHNICAL PIPELINE & CORE INDICATORS (Delegated to MarketAnalyzer)
    # ==========================================
    # Old methods removed as they are now in core/market_analyzer.py



    def update_trailing_stops(self):
        """Aktualisiert alle Trailing Stops für offene Positionen"""
        if not self.mt5_connected or not self.trailing_stop_enabled:
            return
    
        try:
            positions = mt5.positions_get()
            if not positions:
                return
        
            updated_count = 0
        
            for position in positions:
                # Nur eigene Positionen (Magic Number)
                if position.magic != 234000:
                    continue
            
                # Aktuelle Marktpreise holen
                tick = mt5.symbol_info_tick(position.symbol)
                if not tick:
                    continue
            
                current_price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
            
                # Berechne neuen Trailing Stop
                new_sl = self.calculate_trailing_stop(position, current_price)
            
                if new_sl and new_sl != position.sl:
                    # Stop Loss modifizieren
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "position": position.ticket,
                        "sl": new_sl,
                        "tp": position.tp
                    }
                
                    result = mt5.order_send(request)
                
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        updated_count += 1
                        self.log("INFO", f"Trailing Stop aktualisiert: {position.symbol} SL: {position.sl:.5f} -> {new_sl:.5f}", "TRAILING")
                        print(f"Trailing Stop {position.symbol}: {new_sl:.5f}")
                    else:
                        self.log("WARNING", f"Trailing Stop Fehler {position.symbol}: {result.comment}", "TRAILING")
        
            if updated_count > 0:
                self.log("INFO", f"{updated_count} Trailing Stops aktualisiert", "TRAILING")
            
        except Exception as e:
            self.log_error("update_trailing_stops", e)

    def calculate_trailing_stop(self, position, current_price):
        """Berechnet neuen Trailing Stop Level für eine Position"""
        try:
            symbol_info = mt5.symbol_info(position.symbol)
            if not symbol_info:
                return None
        
            # Pip-Wert für das Symbol
            pip_size = symbol_info.point
            if symbol_info.digits == 3 or symbol_info.digits == 5:
                pip_size *= 10
        
            # Profit in Pips berechnen
            if position.type == mt5.ORDER_TYPE_BUY:
                profit_pips = (current_price - position.price_open) / pip_size
            
                # Prüfe ob Mindest-Profit erreicht
                if profit_pips < self.trailing_stop_start_profit_pips:
                    return None
            
                # Berechne neuen Stop Loss
                new_sl = current_price - (self.trailing_stop_distance_pips * pip_size)
            
                # Stop Loss darf nur nach oben (günstiger) bewegt werden
                if position.sl == 0 or new_sl > position.sl:
                    # Prüfe Mindestabstand
                    min_distance = symbol_info.trade_stops_level * symbol_info.point
                    if (current_price - new_sl) >= min_distance:
                        return round(new_sl, symbol_info.digits)
                    
            else:  # SELL Position
                profit_pips = (position.price_open - current_price) / pip_size
            
                # Prüfe ob Mindest-Profit erreicht
                if profit_pips < self.trailing_stop_start_profit_pips:
                    return None
            
                # Berechne neuen Stop Loss
                new_sl = current_price + (self.trailing_stop_distance_pips * pip_size)
            
                # Stop Loss darf nur nach unten (günstiger) bewegt werden
                if position.sl == 0 or new_sl < position.sl:
                    # Prüfe Mindestabstand
                    min_distance = symbol_info.trade_stops_level * symbol_info.point
                    if (new_sl - current_price) >= min_distance:
                        return round(new_sl, symbol_info.digits)
        
            return None
        
        except Exception as e:
            self.log_error("calculate_trailing_stop", e, f"Position: {position.ticket}")
            return None
    
    def trailing_stop_settings_menu(self):
        """Trailing Stop Einstellungen Menü"""
        while True:
            print("\n🎯 TRAILING STOP EINSTELLUNGEN")
            print("─" * 40)
            print(f"Status: {'✅ Aktiviert' if self.trailing_stop_enabled else '❌ Deaktiviert'}")
            print(f"Abstand: {self.trailing_stop_distance_pips} Pips")
            print(f"Schritt: {self.trailing_stop_step_pips} Pips")
            print(f"Start ab Profit: {self.trailing_stop_start_profit_pips} Pips")
        
            print("\n1. Ein/Ausschalten")
            print("2. Abstand ändern")
            print("3. Schrittweite ändern")
            print("4. Start-Profit ändern")
            print("5. Sofort aktualisieren")
            print("6. Zurück")
        
            choice = input("\nWählen (1-6): ").strip()
        
            if choice == "1":
                old_status = self.trailing_stop_enabled
                self.trailing_stop_enabled = not self.trailing_stop_enabled
                status = "aktiviert" if self.trailing_stop_enabled else "deaktiviert"
                self.log("INFO", f"Trailing Stop {status}", "SETTINGS")
                print(f"Trailing Stop {status}")
        
            elif choice == "2":
                try:
                    old_distance = self.trailing_stop_distance_pips
                    new_distance = int(input(f"Abstand in Pips (aktuell {self.trailing_stop_distance_pips}): "))
                    if 5 <= new_distance <= 100:
                        self.trailing_stop_distance_pips = new_distance
                        self.log("INFO", f"Trailing Stop Abstand: {old_distance} -> {new_distance} Pips", "SETTINGS")
                        print(f"Abstand auf {new_distance} Pips gesetzt")
                    else:
                        print("Abstand muss zwischen 5 und 100 Pips liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "3":
                try:
                    old_step = self.trailing_stop_step_pips
                    new_step = int(input(f"Schrittweite in Pips (aktuell {self.trailing_stop_step_pips}): "))
                    if 1 <= new_step <= 20:
                        self.trailing_stop_step_pips = new_step
                        self.log("INFO", f"Trailing Stop Schritt: {old_step} -> {new_step} Pips", "SETTINGS")
                        print(f"Schrittweite auf {new_step} Pips gesetzt")
                    else:
                        print("Schrittweite muss zwischen 1 und 20 Pips liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "4":
                try:
                    old_start = self.trailing_stop_start_profit_pips
                    new_start = int(input(f"Start-Profit in Pips (aktuell {self.trailing_stop_start_profit_pips}): "))
                    if 5 <= new_start <= 50:
                        self.trailing_stop_start_profit_pips = new_start
                        self.log("INFO", f"Trailing Stop Start: {old_start} -> {new_start} Pips", "SETTINGS")
                        print(f"Start-Profit auf {new_start} Pips gesetzt")
                    else:
                        print("Start-Profit muss zwischen 5 und 50 Pips liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "5":
                if self.trailing_stop_enabled:
                    print("Aktualisiere Trailing Stops...")
                    self.update_trailing_stops()
                    print("Trailing Stops aktualisiert")
                else:
                    print("Trailing Stop ist deaktiviert")
        
            elif choice == "6":
                break
        
            else:
                print("Ungültige Auswahl")
        
            input("\nDrücken Sie Enter zum Fortfahren...")

    def enhanced_enable_auto_trading(self):
        """Erweiterte Auto-Trading Aktivierung mit verbesserter Benutzerführung"""
    
        if not self.trading_enabled:
            print("❌ Erst Trading aktivieren!")
            return False
    
        print("\n🤖 VOLLAUTOMATISCHES TRADING SETUP")
        print("═" * 50)
        print("⚠️ WARNUNG: Automatisches Trading ist hochriskant!")
        print("💰 Nur mit Geld handeln, das Sie verlieren können!")
    
        # Sicherheitsabfragen
        confirm1 = input("\nAuto-Trading aktivieren? (GEFÄHRLICH/nein): ")
        if confirm1 != "GEFÄHRLICH":
            return False
    
        confirm2 = input("Risiko verstanden? (ICH_VERSTEHE): ")
        if confirm2 != "ICH_VERSTEHE":
            return False
    
        # Währungspaar-Auswahl mit verbesserter UI
        print(f"\n📋 WÄHRUNGSPAAR AUSWAHL")
        print("─" * 30)
        print("1. 🔥 Standard Majors (EURUSD, GBPUSD, USDJPY)")
        print("2. 🌍 Erweiterte Majors (+ USDCHF, AUDUSD, USDCAD)")
        print("3. 🌎 Alle verfügbaren Paare")
        print("4. ✏️ Eigene Auswahl")
        print("5. 📊 Aktuelle Paare beibehalten")
    
        choice = input("Wählen Sie (1-5): ").strip()
    
        if choice == "1":
            self.auto_trade_symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        elif choice == "2":
            self.auto_trade_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
        elif choice == "3":
            # Alle verfügbaren Forex-Paare
            all_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", 
                          "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY", "EURGBP", "EURAUD"]
        
            # Prüfe welche verfügbar sind
            available_symbols = []
            print("📊 Prüfe verfügbare Symbole...")
        
            for symbol in all_symbols:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    available_symbols.append(symbol)
                    print(f"✅ {symbol}")
                else:
                    print(f"❌ {symbol} (nicht verfügbar)")
        
            if available_symbols:
                self.auto_trade_symbols = available_symbols
                print(f"✅ {len(available_symbols)} Paare verfügbar")
            else:
                print("❌ Keine Paare verfügbar - verwende EURUSD")
                self.auto_trade_symbols = ["EURUSD"]
            
        elif choice == "4":
            symbols_input = input("Symbole eingeben (getrennt durch Komma): ").upper()
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                # Validiere Symbole
                valid_symbols = []
                for symbol in symbols:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        valid_symbols.append(symbol)
                        print(f"✅ {symbol}")
                    else:
                        print(f"❌ {symbol} (nicht verfügbar)")
            
                if valid_symbols:
                    self.auto_trade_symbols = valid_symbols
                else:
                    print("❌ Keine gültigen Symbole - verwende EURUSD")
                    self.auto_trade_symbols = ["EURUSD"]
            else:
                return False
            
        elif choice == "5":
            if hasattr(self, 'auto_trade_symbols') and self.auto_trade_symbols:
                print(f"📊 Aktuelle Paare: {', '.join(self.auto_trade_symbols)}")
            else:
                print("❌ Keine aktuellen Paare - verwende EURUSD")
                self.auto_trade_symbols = ["EURUSD"]
        else:
            print("❌ Ungültige Auswahl")
            return False
    
        # Intervall-Einstellung
        print(f"\n⏱️ TRADING INTERVALL")
        print("─" * 25)
        print(f"Aktuell: {self.analysis_interval}s")
        print("💡 Empfohlene Intervalle:")
        print("   • 60-120s:  🔥 Aggressiv (mehr Trades)")
        print("   • 180-300s: 📊 Normal (ausgewogen)")
        print("   • 300-600s: 🛡️ Konservativ (weniger Trades)")
    
        new_interval = input(f"Neues Intervall in Sekunden (Enter für {self.analysis_interval}): ")
        if new_interval:
            try:
                interval_value = int(new_interval)
                if 30 <= interval_value <= 3600:  # 30s bis 1h
                    self.analysis_interval = interval_value
                    print(f"✅ Intervall auf {self.analysis_interval}s gesetzt")
                else:
                    print("⚠️ Intervall außerhalb des empfohlenen Bereichs (30-3600s)")
                    self.analysis_interval = max(30, min(3600, interval_value))
                    print(f"✅ Angepasst auf {self.analysis_interval}s")
            except ValueError:
                print("❌ Ungültiges Intervall - verwende aktuelles")
    
        # Risk Management Check
        print(f"\n🛡️ RISK MANAGEMENT STATUS")
        print("─" * 30)
    
        if hasattr(self, 'risk_manager') and self.risk_manager:
            try:
                summary = self.risk_manager.get_risk_summary()
                print("✅ Risk Management aktiv")
                print(f"💰 Aktueller Tages P&L: {summary.get('daily_pnl', 0):.2f}€")
                print(f"📊 Max Verlust heute: {self.risk_manager.max_daily_loss:.2f}€")
                print(f"🎯 Verbleibende Trades: {self.risk_manager.max_trades_per_day - summary.get('trades_today', 0)}")
                print(f"💼 Offene Positionen: {summary.get('open_positions', 0)}/{self.risk_manager.max_total_positions}")
            
                # Warnung bei kritischen Werten
                if summary.get('daily_pnl', 0) <= self.risk_manager.max_daily_loss * 0.8:
                    print("🔴 WARNUNG: Verlustlimit fast erreicht!")
            
            except Exception as e:
                print(f"⚠️ Risk Manager Status-Fehler: {e}")
        else:
            print("❌ Risk Management nicht verfügbar")
            print("⚠️ Trading ohne Schutz - SEHR RISKANT!")
        
            no_risk_confirm = input("Trotzdem fortfahren? (OHNE_SCHUTZ): ")
            if no_risk_confirm != "OHNE_SCHUTZ":
                return False
    
        # Multi-Timeframe Status
        print(f"\n📈 ANALYSE-FILTER STATUS")
        print("─" * 25)
        print(f"📊 RSI Filter: ✅ (Periode: {self.rsi_period})")
        print(f"📈 MACD Filter: ✅ ({self.macd_fast_period}/{self.macd_slow_period}/{self.macd_signal_period})")
        print(f"🎯 S/R Filter: ✅ (Lookback: {self.sr_lookback_period})")
    
        if self.mtf_enabled:
            tf_name = self.timeframe_names.get(self.trend_timeframe, "H1")
            print(f"⏰ Trend Filter: ✅ ({tf_name} Timeframe)")
        else:
            print(f"⏰ Trend Filter: ❌ (deaktiviert)")
    
        # Final Setup
        self.auto_trading = True
    
        print(f"\n🚀 AUTO-TRADING BEREIT!")
        print("═" * 35)
        print(f"📊 Anzahl Paare: {len(self.auto_trade_symbols)}")
        print(f"💱 Symbole: {', '.join(self.auto_trade_symbols[:5])}")
        if len(self.auto_trade_symbols) > 5:
            print(f"         ... und {len(self.auto_trade_symbols) - 5} weitere")
        print(f"⏱️ Analyse-Intervall: {self.analysis_interval}s")
        print(f"🛡️ Risk Management: {'✅' if hasattr(self, 'risk_manager') and self.risk_manager else '❌'}")
        print(f"📈 Filter aktiv: RSI + MACD + S/R{' + Trend' if self.mtf_enabled else ''}")
        print("═" * 35)
    
        # Letzte Bestätigung
        final_confirm = input("\n🎯 Auto-Trading jetzt starten? (START/abbrechen): ")
        if final_confirm == "START":
            self.log("INFO", f"Auto-Trading aktiviert mit {len(self.auto_trade_symbols)} Paaren", "TRADE")
            print(f"\n🚀 STARTE AUTO-TRADING...")
            print("⏸️ Stopp mit Ctrl+C")
            return True
        else:
            self.auto_trading = False
            print("❌ Auto-Trading abgebrochen")
            return False

    def macd_settings_menu(self):
        """MACD Einstellungen Menü"""
        while True:
            print("\n📊 MACD EINSTELLUNGEN")
            print("─" * 40)
            print(f"Fast EMA: {self.macd_fast_period}")
            print(f"Slow EMA: {self.macd_slow_period}")
            print(f"Signal EMA: {self.macd_signal_period}")
            print(f"Zeitrahmen: {self.macd_timeframe}")
        
            print("\n1. Fast EMA Period ändern")
            print("2. Slow EMA Period ändern")
            print("3. Signal EMA Period ändern")
            print("4. Zeitrahmen ändern")
            print("5. MACD Test")
            print("6. Zurück")
        
            choice = input("\nWählen (1-6): ").strip()
        
            if choice == "1":
                try:
                    old_fast = self.macd_fast_period
                    new_fast = int(input(f"Fast EMA Period (aktuell {self.macd_fast_period}): "))
                    if 5 <= new_fast <= 20 and new_fast < self.macd_slow_period:
                        self.macd_fast_period = new_fast
                        self.log("INFO", f"MACD Fast EMA: {old_fast} -> {new_fast}", "SETTINGS")
                        print(f"Fast EMA auf {new_fast} gesetzt")
                    else:
                        print("Fast EMA muss zwischen 5-20 und kleiner als Slow EMA sein")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "2":
                try:
                    old_slow = self.macd_slow_period
                    new_slow = int(input(f"Slow EMA Period (aktuell {self.macd_slow_period}): "))
                    if 20 <= new_slow <= 50 and new_slow > self.macd_fast_period:
                        self.macd_slow_period = new_slow
                        self.log("INFO", f"MACD Slow EMA: {old_slow} -> {new_slow}", "SETTINGS")
                        print(f"Slow EMA auf {new_slow} gesetzt")
                    else:
                        print("Slow EMA muss zwischen 20-50 und größer als Fast EMA sein")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "3":
                try:
                    old_signal = self.macd_signal_period
                    new_signal = int(input(f"Signal EMA Period (aktuell {self.macd_signal_period}): "))
                    if 5 <= new_signal <= 15:
                        self.macd_signal_period = new_signal
                        self.log("INFO", f"MACD Signal EMA: {old_signal} -> {new_signal}", "SETTINGS")
                        print(f"Signal EMA auf {new_signal} gesetzt")
                    else:
                        print("Signal EMA muss zwischen 5-15 liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "4":
                print("\nZeitrahmen:")
                print("1. M1 (1 Minute)")
                print("2. M5 (5 Minuten)")
                print("3. M15 (15 Minuten)")
                print("4. M30 (30 Minuten)")
                print("5. H1 (1 Stunde)")
            
                tf_choice = input("Wählen (1-5): ").strip()
            
                timeframes = {
                    "1": mt5.TIMEFRAME_M1,
                    "2": mt5.TIMEFRAME_M5,
                    "3": mt5.TIMEFRAME_M15,
                    "4": mt5.TIMEFRAME_M30,
                    "5": mt5.TIMEFRAME_H1
                }
            
                if tf_choice in timeframes:
                    old_tf = self.macd_timeframe
                    self.macd_timeframe = timeframes[tf_choice]
                    tf_names = {"1": "M1", "2": "M5", "3": "M15", "4": "M30", "5": "H1"}
                    self.log("INFO", f"MACD Zeitrahmen geändert zu {tf_names[tf_choice]}", "SETTINGS")
                    print(f"Zeitrahmen auf {tf_names[tf_choice]} gesetzt")
                else:
                    print("Ungültige Auswahl")
        
            elif choice == "5":
                symbol = input("Symbol für MACD Test: ").upper()
                if symbol:
                    self.log("INFO", f"MACD Test gestartet für {symbol}", "ANALYSIS")
                    macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1) if self.market and hasattr(self.market, 'calculate_macd') else None
                    if macd_data:
                        signal, desc = self.market.get_macd_signal(macd_data) if self.market and hasattr(self.market, 'get_macd_signal') else (None, None)
                        print(f"\n{symbol} MACD Test:")
                        print(f"MACD: {macd_data['macd']}")
                        print(f"Signal: {macd_data['signal']}")
                        print(f"Histogram: {macd_data['histogram']}")
                        print(f"Signal: {signal}")
                        print(f"Beschreibung: {desc}")
                    else:
                        print("MACD Berechnung fehlgeschlagen")
        
            elif choice == "6":
                break
        
            else:
                print("Ungültige Auswahl")
        
            input("\nDrücken Sie Enter zum Fortfahren...")

    def stop_trading_companion(self):
        """Stoppt den Trading Companion sicher"""
        try:
            if self.companion_process:
                print("🔧 Beende Trading Companion...")
                self.companion_process.terminate()
                try:
                    self.companion_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.companion_process.kill()
                self.companion_process = None
            self.companion_enabled = False
            print("✅ Trading Companion gestoppt")
        except Exception as e:
            print(f"❌ Fehler beim Stoppen des Companions: {e}")

    # ==========================================
    # 9. RISK MANAGEMENT & POSITION SIZING
    # ==========================================
    def risk_management_menu(self):
        """Neues Risk Management Menü"""
        while True:
            self.print_header("RISK MANAGEMENT")
            
            # Zeige aktuellen Status

            self.risk_manager.print_risk_status()
            
            print("\n📋 OPTIONEN:")
            print("─" * 25)
            print(" 1. 📊 Risk Status anzeigen")
            print(" 2. ⚙️ Limits anpassen")
            print(" 3. 💰 Position Size Rechner")
            print(" 4. 📈 Tagesstatistiken")
            print(" 5. 🔄 Settings zurücksetzen")
            print(" 6. ⬅️ Zurück zum Hauptmenü")
            print("─" * 35)
            
            choice = input("🎯 Ihre Wahl (1-6): ").strip()
            
            if choice == "1":
                self.risk_manager.print_risk_status()
                
            elif choice == "2":
                self.adjust_risk_limits()
                
            elif choice == "3":
                self.position_size_calculator()
                
            elif choice == "4":
                self.show_daily_stats()
                
            elif choice == "6":
                break
                
            elif choice == "5":
                self.reset_risk_settings()
                
            else:
                print("❌ Ungültige Auswahl")
            
            input("\n📝 Drücken Sie Enter zum Fortfahren...")
    
    def adjust_risk_limits(self):
        """Risk Limits anpassen"""
        print("\n⚙️ RISK LIMITS ANPASSEN")
        print("─" * 30)
        
        try:
            print(f"Aktueller Max. Tagesverlust: {self.risk_manager.max_daily_loss}€")
            new_daily_loss = input("Neuer Max. Tagesverlust (Enter für keine Änderung): ")
            
            print(f"Aktuelles Max. Risiko pro Trade: {self.risk_manager.max_risk_per_trade}%")
            new_risk_per_trade = input("Neues Max. Risiko pro Trade (Enter für keine Änderung): ")
            
            print(f"Aktuelle Max. Gesamtpositionen: {self.risk_manager.max_total_positions}")
            new_max_positions = input("Neue Max. Gesamtpositionen (Enter für keine Änderung): ")
            
            # Updates anwenden
            updates = {}
            if new_daily_loss:
                updates['max_daily_loss'] = float(new_daily_loss)
            if new_risk_per_trade:
                updates['max_risk_per_trade'] = float(new_risk_per_trade)
            if new_max_positions:
                updates['max_total_positions'] = int(new_max_positions)
            
            if updates:
                self.risk_manager.update_settings(**updates)
                print("✅ Risk Limits aktualisiert")
            else:
                print("ℹ️ Keine Änderungen vorgenommen")
                
        except ValueError:
            print("❌ Ungültige Eingabe")
        except Exception as e:
            print(f"❌ Fehler: {e}")
    
    def position_size_calculator(self):
        """Position Size Rechner"""
        print("\n💰 POSITION SIZE RECHNER")
        print("─" * 30)
        
        try:
            symbol = input("Symbol: ").upper()
            if not symbol:
                return
            
            stop_loss_pips = float(input("Stop Loss Abstand (Pips): "))
            risk_percent = float(input(f"Risiko % (aktuell {self.risk_manager.max_risk_per_trade}%): ") or self.risk_manager.max_risk_per_trade)
            
            calculated_size = self.risk_manager.calculate_position_size(symbol, stop_loss_pips, risk_percent)
            
            print(f"\n📊 ERGEBNIS:")
            print(f"Symbol: {symbol}")
            print(f"Stop Loss: {stop_loss_pips} Pips")
            print(f"Risiko: {risk_percent}%")
            print(f"Empfohlene Lot Size: {calculated_size}")
            
        except ValueError:
            print("❌ Ungültige Eingabe")
        except Exception as e:
            print(f"❌ Fehler: {e}")
    
    def show_daily_stats(self):
        """Zeigt Tagesstatistiken"""
        print("\n📈 TAGESSTATISTIKEN")
        print("─" * 25)
        
        summary = self.risk_manager.get_risk_summary()
        
        print(f"Tages P&L: {summary.get('daily_pnl', 0):.2f}€")
        print(f"Trades heute: {summary.get('trades_today', 0)}")
        print(f"Offene Positionen: {summary.get('open_positions', 0)}")
        print(f"Account Balance: {summary.get('account_balance', 0):.2f}€")
        print(f"Margin Level: {summary.get('margin_level', 0):.1f}%")
    
    def reset_risk_settings(self):
        """Risk Settings zurücksetzen"""
        confirm = input("Risk Settings auf Standard zurücksetzen? (ja/nein): ")
        if confirm.lower() == "ja":
            self.risk_manager = RiskManager(logger=self.logger)
            print("✅ Risk Settings zurückgesetzt")
        else:
            print("ℹ️ Keine Änderungen vorgenommen")

    def request_companion_analysis(self, symbol):
        """Führt eine erweiterte Analyse mit dem Trading Companion durch"""
        if not self.companion_enabled:
            print("❌ Trading Companion nicht aktiv")
            return
        try:
            if not self.companion_process or self.companion_process.poll() is not None:
                print("❌ Trading Companion nicht verfügbar")
                return
            print(f"🔄 Starte erweiterte Analyse für {symbol}...")
            # Hier könnte die Kommunikation mit dem Companion implementiert werden
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1) if self.market and hasattr(self.market, 'calculate_rsi') else None
            sr_data = self.calculate_support_resistance(symbol)
            print("\n📊 ERWEITERTE ANALYSE:")
            print("─" * 40)
            if rsi_value:
                signal, desc = self.market.get_rsi_signal(rsi_value) if self.market and hasattr(self.market, 'get_rsi_signal') else (None, None)
                print(f"📈 RSI: {rsi_value} - {desc}")
            if sr_data:
                if sr_data['nearest_support']:
                    level, strength = sr_data['nearest_support']
                    print(f"🔵 Support: {level:.5f} (Stärke: {strength})")
                if sr_data['nearest_resistance']:
                    level, strength = sr_data['nearest_resistance']
                    print(f"🔴 Resistance: {level:.5f} (Stärke: {strength})")
            print("─" * 40)
        except Exception as e:
            print(f"❌ Analyse-Fehler: {e}")

    def sr_settings_menu(self):
        """Support/Resistance Einstellungen Menü"""
        while True:
            print("\n📊 SUPPORT/RESISTANCE EINSTELLUNGEN")
            print("─" * 40)
            print(f"Lookback Periode: {self.sr_lookback_period}")
            print(f"Min. Berührungen: {self.sr_min_touches}")
            print(f"Toleranz: {self.sr_tolerance}")
            print(f"Stärke Schwelle: {self.sr_strength_threshold}")
            print("\n1. Lookback Periode ändern")
            print("2. Min. Berührungen ändern")
            print("3. Toleranz ändern")
            print("4. Stärke Schwelle ändern")
            print("5. Zurück")
            choice = input("\nWählen (1-5): ").strip()
            if choice == "1":
                try:
                    new_period = int(input(f"Lookback Periode (aktuell {self.sr_lookback_period}): "))
                    if 20 <= new_period <= 200:
                        self.sr_lookback_period = new_period
                        print("✅ Lookback Periode aktualisiert")
                    else:
                        print("❌ Periode muss zwischen 20 und 200 liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")
            elif choice == "2":
                try:
                    new_touches = int(input(f"Min. Berührungen (aktuell {self.sr_min_touches}): "))
                    if 1 <= new_touches <= 5:
                        self.sr_min_touches = new_touches
                        print("✅ Min. Berührungen aktualisiert")
                    else:
                        print("❌ Wert muss zwischen 1 und 5 liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")
            elif choice == "3":
                try:
                    new_tolerance = float(input(f"Toleranz in Pips (aktuell {self.sr_tolerance*10000:.1f}): ")) / 10000
                    if 0.0001 <= new_tolerance <= 0.001:
                        self.sr_tolerance = new_tolerance
                        print("✅ Toleranz aktualisiert")
                    else:
                        print("❌ Toleranz muss zwischen 1 und 10 Pips liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")
            elif choice == "4":
                try:
                    new_threshold = int(input(f"Stärke Schwelle (aktuell {self.sr_strength_threshold}): "))
                    if 2 <= new_threshold <= 5:
                        self.sr_strength_threshold = new_threshold
                        print("✅ Stärke Schwelle aktualisiert")
                    else:
                        print("❌ Wert muss zwischen 2 und 5 liegen")
                except ValueError:
                    print("❌ Ungültige Eingabe")
            elif choice == "5":
                break

    def print_loading_animation(self, text, duration=2):
        """Zeigt eine schöne Lade-Animation"""
        import time
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        end_time = time.time() + duration
        
        while time.time() < end_time:
            for frame in frames:
                print(f"\r{frame} {text}", end="", flush=True)
                time.sleep(0.1)
                if time.time() >= end_time:
                    break
        
        print(f"\r✅ {text} - Abgeschlossen!    ")
    
    # ==========================================
    # KERN-FUNKTIONEN (Delegated to MT5Broker)
    # ==========================================

    def connect_mt5(self):
        """Stellt eine Verbindung zu MetaTrader 5 her"""
        return self.broker.connect_mt5()

    def disconnect_mt5(self):
        """Trennt die Verbindung zu MetaTrader 5"""
        self.broker.disconnect_mt5()

    def reconnect_mt5(self, max_retries: int = 10, base_delay: float = 5.0):
        """Versucht die MT5 Verbindung wiederherzustellen"""
        return self.broker.reconnect_mt5(max_retries, base_delay)

    def is_mt5_alive(self) -> bool:
        """Prüft ob die MT5 Verbindung noch aktiv ist"""
        return self.broker.is_mt5_alive()

    def get_mt5_live_data(self, symbol):
        if not self.mt5_connected:
            return "MT5 nicht verbunden"
    
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return f"Symbol {symbol} nicht gefunden"
        
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return f"Keine Tick-Daten für {symbol}"
        
            current_price = (tick.bid + tick.ask) / 2
            spread = tick.ask - tick.bid
        
            # RSI berechnen
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi_value)
        
            # MACD berechnen
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
        
            # Support/Resistance berechnen
            sr_data = self.market.calculate_support_resistance(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            sr_signal, sr_desc = self.market.get_sr_signal(sr_data, current_price)
        
            rsi_info = f"RSI: {rsi_desc}" if rsi_value else "RSI: Nicht verfügbar"
            macd_info = f"MACD: {macd_desc}" if macd_data else "MACD: Nicht verfügbar"
            sr_info = f"S/R: {sr_desc}"
        
            # Formatiere S/R Levels für Anzeige
            sr_levels_info = ""
            if sr_data:
                if sr_data['support_levels']:
                    level = sr_data['support_levels'][0]['price']
                    strength = sr_data['support_levels'][0]['strength']
                    distance = abs(current_price - level) / current_price * 10000  # in Pips
                    sr_levels_info += f"\nSupport: {level:.5f} (Stärke: {strength}, {distance:.1f} Pips)"
            
                if sr_data['resistance_levels']:
                    level = sr_data['resistance_levels'][0]['price']
                    strength = sr_data['resistance_levels'][0]['strength']
                    distance = abs(current_price - level) / current_price * 10000  # in Pips
                    sr_levels_info += f"\nResistance: {level:.5f} (Stärke: {strength}, {distance:.1f} Pips)"
        
            # Formatiere MACD Details für Anzeige
            macd_details_info = ""
            if macd_data:
                macd_details_info += f"\nMACD Line: {macd_data['macd']:.6f}"
                macd_details_info += f"\nSignal Line: {macd_data['signal']:.6f}"
                macd_details_info += f"\nHistogram: {macd_data['histogram']:.6f}"
                macd_details_info += f"\nTrend: {macd_data['histogram_trend']}"
        
            return f"""
    MT5 LIVE-DATEN für {symbol}:
    Bid/Ask: {tick.bid:.5f} / {tick.ask:.5f}
    Preis: {current_price:.5f}
    Spread: {spread:.5f}
    {rsi_info}
    RSI-Signal: {rsi_signal}
    {macd_info}
    MACD-Signal: {macd_signal}{macd_details_info}
    {sr_info}
    S/R-Signal: {sr_signal}{sr_levels_info}
    Stand: {datetime.fromtimestamp(tick.time).strftime('%H:%M:%S')}
    """
        
        except Exception as e:
            return f"Daten-Fehler: {e}"
    
    def check_ollama_status(self):
        """Überprüft die Verfügbarkeit des Ollama-Servers via ai module"""
        return self.ai.check_ollama_status_sync()
    
    def get_available_models(self):
        """Holt die Liste der installierten Ollama-Modelle via ai module"""
        return self.ai.get_available_models()
    
    def get_ollama_models(self):
        """Alias für get_available_models - wird von Tests erwartet"""
        return self.get_available_models()
    
    def mtf_settings_menu(self):
        """Multi-Timeframe Einstellungen Menü"""

        # Timeframe-Namen für Anzeige
        def get_timeframe_name(timeframe):
            timeframe_names = {
                mt5.TIMEFRAME_M1: "M1",
                mt5.TIMEFRAME_M5: "M5", 
                mt5.TIMEFRAME_M15: "M15",
                mt5.TIMEFRAME_M30: "M30",
                mt5.TIMEFRAME_H1: "H1",
                mt5.TIMEFRAME_H4: "H4",
                mt5.TIMEFRAME_D1: "D1"
            }

            trend_tf_name = timeframe_names.get(self.trend_timeframe, f"Unbekannt ({self.trend_timeframe})")
            entry_tf_name = timeframe_names.get(self.entry_timeframe, f"Unbekannt ({self.entry_timeframe})")

            return timeframe_names.get(timeframe, f"Unbekannt ({timeframe})")

        while True:
            print("\n📈 MULTI-TIMEFRAME EINSTELLUNGEN")
            print("─" * 40)
            print(f"Status: {'✅ Aktiviert' if self.mtf_enabled else '❌ Deaktiviert'}")
            print(f"Trend-Timeframe: {get_timeframe_name(self.trend_timeframe)}")
            print(f"Entry-Timeframe: {get_timeframe_name(self.entry_timeframe)}")
            print(f"EMA Periode: {self.trend_ema_period}")
            print(f"Trend-Stärke Schwelle: {self.trend_strength_threshold}")
            print(f"Trend-Bestätigung erforderlich: {'✅' if self.require_trend_confirmation else '❌'}")
        
        
            print("\n1. Ein/Ausschalten")
            print("2. Trend-Timeframe ändern")
            print("3. Entry-Timeframe ändern")
            print("4. EMA Periode ändern")
            print("5. Trend-Stärke Schwelle ändern")
            print("6. Trend-Bestätigung ein/aus")
            print("7. Trend-Test")
            print("8. Zurück")
        
            choice = input("\nWählen (1-8): ").strip()
        
            if choice == "1":
                old_status = self.mtf_enabled
                self.mtf_enabled = not self.mtf_enabled
                status = "aktiviert" if self.mtf_enabled else "deaktiviert"
                self.log("INFO", f"Multi-Timeframe {status}", "SETTINGS")
                print(f"Multi-Timeframe {status}")
        
            elif choice == "2":
                print("\nTrend-Timeframe:")
                print("1. M30 (30 Minuten)")
                print("2. H1 (1 Stunde)")
                print("3. H4 (4 Stunden)")
                print("4. D1 (1 Tag)")
            
                tf_choice = input("Wählen (1-4): ").strip()
            
                timeframes = {
                    "1": mt5.TIMEFRAME_M30,
                    "2": mt5.TIMEFRAME_H1,
                    "3": mt5.TIMEFRAME_H4,
                    "4": mt5.TIMEFRAME_D1
                }
            
                if tf_choice in timeframes:
                    old_tf = self.trend_timeframe
                    self.trend_timeframe = timeframes[tf_choice]
                    tf_names = {"1": "M30", "2": "H1", "3": "H4", "4": "D1"}
                    self.log("INFO", f"Trend-Timeframe geändert zu {tf_names[tf_choice]}", "SETTINGS")
                    print(f"Trend-Timeframe auf {tf_names[tf_choice]} gesetzt")
                else:
                    print("Ungültige Auswahl")
        
            elif choice == "3":
                print("\nEntry-Timeframe:")
                print("1. M1 (1 Minute)")
                print("2. M5 (5 Minuten)")
                print("3. M15 (15 Minuten)")
                print("4. M30 (30 Minuten)")
            
                tf_choice = input("Wählen (1-4): ").strip()
            
                timeframes = {
                    "1": mt5.TIMEFRAME_M1,
                    "2": mt5.TIMEFRAME_M5,
                    "3": mt5.TIMEFRAME_M15,
                    "4": mt5.TIMEFRAME_M30
                }
            
                if tf_choice in timeframes:
                    old_tf = self.entry_timeframe
                    self.entry_timeframe = timeframes[tf_choice]
                    tf_names = {"1": "M1", "2": "M5", "3": "M15", "4": "M30"}
                    self.log("INFO", f"Entry-Timeframe geändert zu {tf_names[tf_choice]}", "SETTINGS")
                    print(f"Entry-Timeframe auf {tf_names[tf_choice]} gesetzt")
                else:
                    print("Ungültige Auswahl")
        
            elif choice == "4":
                try:
                    old_period = self.trend_ema_period
                    new_period = int(input(f"EMA Periode (aktuell {self.trend_ema_period}): "))
                    if 20 <= new_period <= 200:
                        self.trend_ema_period = new_period
                        self.log("INFO", f"Trend EMA Periode: {old_period} -> {new_period}", "SETTINGS")
                        print(f"EMA Periode auf {new_period} gesetzt")
                    else:
                        print("EMA Periode muss zwischen 20 und 200 liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "5":
                try:
                    old_threshold = self.trend_strength_threshold
                    new_threshold = float(input(f"Trend-Stärke Schwelle (aktuell {self.trend_strength_threshold}): "))
                    if 0.0001 <= new_threshold <= 0.01:
                        self.trend_strength_threshold = new_threshold
                        self.log("INFO", f"Trend-Stärke Schwelle: {old_threshold} -> {new_threshold}", "SETTINGS")
                        print(f"Trend-Stärke Schwelle auf {new_threshold} gesetzt")
                    else:
                        print("Schwelle muss zwischen 0.0001 und 0.01 liegen")
                except ValueError:
                    print("Ungültige Eingabe")
        
            elif choice == "6":
                old_status = self.require_trend_confirmation
                self.require_trend_confirmation = not self.require_trend_confirmation
                status = "aktiviert" if self.require_trend_confirmation else "deaktiviert"
                self.log("INFO", f"Trend-Bestätigung {status}", "SETTINGS")
                print(f"Trend-Bestätigung {status}")
        
            elif choice == "7":
                if self.mtf_enabled:
                    symbol = input("Symbol für Trend-Test: ").upper()
                    if symbol:
                        self.log("INFO", f"Trend-Test gestartet für {symbol}", "ANALYSIS")
                        trend_data = self.market.get_higher_timeframe_trend(symbol, mt5.TIMEFRAME_H4) if self.market and hasattr(self.market, 'get_higher_timeframe_trend') else None
                        if trend_data:
                            print(f"\n{symbol} Trend-Analyse:")
                            print(f"Richtung: {trend_data['direction']}")
                            print(f"Stärke: {trend_data['strength']:.6f}")
                            print(f"Qualität: {trend_data['quality']}")
                            print(f"EMA Level: {trend_data['ema_level']:.5f}")
                            print(f"Preis über EMA: {trend_data['price_above_ema']}")
                            print(f"EMA steigend: {trend_data['ema_rising']}")
                            print(f"Momentum: {trend_data['momentum_direction']}")
                        else:
                            print("Trend-Analyse fehlgeschlagen")
                else:
                    print("Multi-Timeframe ist deaktiviert")
        
            elif choice == "8":
                break
        
            else:
                print("Ungültige Auswahl")
        
            input("\nDrücken Sie Enter zum Fortfahren...")

    # ==========================================
    # 11. AI INTEGRATION & EXECUTOR
    # ==========================================
    def select_finance_model(self):
        """Wählt automatisch das beste finanzspezifische Modell via ai module"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running(): return False
            return loop.run_until_complete(self.ai.select_finance_model())
        except RuntimeError:
            return asyncio.run(self.ai.select_finance_model())
    
    def chat_with_model(self, message, context=""):
        """Sendet einen Prompt an Ollama und gibt die Antwort zurück via ai module"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running(): return "Aktuell blockiert (Async Loop läuft bereits)"
            return loop.run_until_complete(self.ai.chat_with_model(message, context))
        except RuntimeError:
            return asyncio.run(self.ai.chat_with_model(message, context))
    
    def enable_trading(self):
        print("\nTRADING AKTIVIEREN")
        print("Echte Trades möglich!")
        
        confirm = input("Trading aktivieren? (ja/nein): ")
        if confirm.lower() != "ja":
            return False
        
        account_info = mt5.account_info()
        if account_info and "demo" not in account_info.server.lower():
            print("LIVE-ACCOUNT!")
            confirm2 = input("LIVE-Trading bestätigen (JA): ")
            if confirm2 != "JA":
                return False
        
        self.trading_enabled = True
        print("Trading aktiviert!")
        return True
    
    def execute_trade(self, symbol, action, lot_size=None, stop_loss=None, take_profit=None):
        """Verbesserte execute_trade Methode mit Risk Management"""

    # ==========================================
    # KERN-TRADING LOGIK (Delegated to MT5Broker)
    # ==========================================

    def get_open_positions(self, symbol=None):
        return self.broker.get_open_positions(symbol)

    def execute_trade(self, symbol, action, lot_size=None, stop_loss=None, take_profit=None, comment="FinGPT Trade"):
        return self.broker.execute_trade(symbol, action, lot_size or self.default_lot_size, stop_loss, take_profit, comment)

    def close_position(self, ticket, comment="FinGPT Close"):
        return self.broker.close_position(ticket, comment)

    def partial_close_position(self, position, close_percentage):
        return self.broker.partial_close_position(position, close_percentage)

    def modify_position(self, ticket, stop_loss=None, take_profit=None):
        return self.broker.modify_position(ticket, stop_loss, take_profit)

    def manage_open_positions(self, symbol=None):
        return self.broker.manage_open_positions(symbol)

    def close_all_positions(self, symbol=None):
        return self.broker.close_all_positions(symbol)

    def close_profitable_positions(self, symbol=None, min_profit=0):
        return self.broker.close_profitable_positions(symbol, min_profit)

    def close_losing_positions(self, symbol=None, max_loss=0):
        return self.broker.close_losing_positions(symbol, max_loss)

        print("\nVOLLAUTOMATISCHES TRADING")
        print("EXTREM RISKANT!")
        
        confirm1 = input("Auto-Trading aktivieren? (GEFÄHRLICH/nein): ")
        if confirm1 != "GEFÄHRLICH":
            return False
        
        confirm2 = input("Risiko verstanden? (ICH_VERSTEHE): ")
        if confirm2 != "ICH_VERSTEHE":
            return False
        
        symbols = input("Symbole (z.B. EURUSD,GBPUSD): ")
        if symbols:
            self.auto_trade_symbols = [s.strip().upper() for s in symbols.split(',')]
        
        interval = input(f"Intervall Sekunden ({self.analysis_interval}): ")
        if interval:
            self.analysis_interval = int(interval)
        
        self.auto_trading = True
        print("Auto-Trading aktiviert!")
        return True
    
    def extract_trade_reasoning(self, ai_response):
        """Extrahiert die Begründung aus der KI-Antwort"""
        try:
            # Suche nach Schlüsselwörtern für Begründungen
            response_lower = ai_response.lower()
            
            reasoning_keywords = [
                'weil', 'aufgrund', 'da', 'durch', 'grund', 'indikator', 'signal',
                'trend', 'support', 'resistance', 'breakout', 'momentum', 'rsi',
                'macd', 'bollinger', 'fibonacci', 'chart', 'pattern', 'formation',
                'überkauft', 'überverkauft', 'overbought', 'oversold', 'widerstand',
                'unterstützung', 'durchbruch', 'prallte', 'bounce', 'rejection'
            ]
            
            # Finde Sätze mit Begründungen
            sentences = ai_response.split('.')
            reasoning_parts = []
            
            for sentence in sentences:
                sentence_lower = sentence.strip().lower()
                if any(keyword in sentence_lower for keyword in reasoning_keywords):
                    # Bereinige und kürze den Satz
                    clean_sentence = sentence.strip()
                    if len(clean_sentence) > 100:
                        clean_sentence = clean_sentence[:97] + "..."
                    reasoning_parts.append(clean_sentence)
            
            if reasoning_parts:
                return " | ".join(reasoning_parts[:2])  # Max 2 Begründungen
            
            # Fallback: Versuche generische Begründung zu finden
            if "buy" in response_lower or "kaufen" in response_lower:
                if "support" in response_lower or "unterstützung" in response_lower:
                    return "Support-Level als Kaufgelegenheit"
                elif "rsi" in response_lower:
                    return "RSI-basierte Kaufgelegenheit"
                elif "trend" in response_lower:
                    return "Aufwärtstrend erkannt"
                elif "breakout" in response_lower or "durchbruch" in response_lower:
                    return "Breakout über Resistance"
                elif "signal" in response_lower:
                    return "Bullisches Signal"
                else:
                    return "Positive Marktbewertung"
            
            elif "sell" in response_lower or "verkaufen" in response_lower:
                if "resistance" in response_lower or "widerstand" in response_lower:
                    return "Resistance-Level als Verkaufsgelegenheit"
                elif "rsi" in response_lower:
                    return "RSI-basierte Verkaufsgelegenheit"
                elif "trend" in response_lower:
                    return "Abwärtstrend erkannt"
                elif "breakout" in response_lower or "durchbruch" in response_lower:
                    return "Breakdown unter Support"
                elif "signal" in response_lower:
                    return "Bearisches Signal"
                else:
                    return "Negative Marktbewertung"
            
            return "KI-Empfehlung basiert auf technischer Analyse"
            
        except Exception:
            return "KI-Analyse durchgeführt"
    
    def extract_recommendation_summary(self, ai_response):
        """Extrahiert eine kurze Zusammenfassung der KI-Empfehlung"""
        try:
            lines = ai_response.split('\n')
            for line in lines:
                line_upper = line.upper().strip()
                if any(word in line_upper for word in ['BUY', 'SELL', 'KAUFEN', 'VERKAUFEN', 'WARTEN', 'HOLD']):
                    return line.strip()[:100]  # Erste 100 Zeichen der Empfehlung
            return ai_response[:100]  # Fallback
        except:
            return "KI-Analyse durchgeführt"

    def display_formatted_analysis(self, symbol, ai_response, live_data):
        """Zeigt die KI-Analyse schön formatiert an"""
    
        print("\n" + "═" * 60)
        print(f"🤖 KI-ANALYSE FÜR {symbol}")
        print("═" * 60)
    
        # Aktuelle Marktdaten kurz anzeigen
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                current_price = (tick.bid + tick.ask) / 2
                print(f"💱 Aktueller Preis: {current_price:.5f}")
                print(f"📊 Bid/Ask: {tick.bid:.5f} / {tick.ask:.5f}")
                print("─" * 60)
        except:
            pass
    
        # KI-Antwort strukturiert aufbereiten
        formatted_response = self.format_ai_response(ai_response)
        print(formatted_response)
    
        print("═" * 60)
    
        # Technische Indikatoren Zusammenfassung
        self.display_technical_summary(symbol)

    def format_ai_response(self, response):
        """Formatiert die KI-Antwort schöner"""
        try:
            # Entferne doppelte Leerzeilen und überflüssige Zeichen
            lines = [line.strip() for line in response.split('\n') if line.strip()]
        
            formatted = []
            current_section = ""
        
            for line in lines:
                # Erkenne Überschriften (mit ** oder Doppelpunkt)
                if ('**' in line or 
                    line.endswith(':') or 
                    any(keyword in line.upper() for keyword in ['EMPFEHLUNG', 'ANALYSE', 'BEGRÜNDUNG', 'SIGNAL'])):
                
                    if current_section:
                        formatted.append("")  # Leerzeile vor neuer Sektion
                
                    # Formatiere Überschrift
                    clean_line = line.replace('**', '').strip(':').strip()
                    formatted.append(f"📋 {clean_line.upper()}")
                    formatted.append("─" * 40)
                    current_section = clean_line
                
                else:
                    # Normaler Text mit Icons
                    if any(keyword in line.upper() for keyword in ['BUY', 'KAUFEN']):
                        formatted.append(f"🟢 {line}")
                    elif any(keyword in line.upper() for keyword in ['SELL', 'VERKAUFEN']):
                        formatted.append(f"🔴 {line}")
                    elif any(keyword in line.upper() for keyword in ['WARTEN', 'HOLD', 'NEUTRAL']):
                        formatted.append(f"🟡 {line}")
                    elif any(keyword in line.upper() for keyword in ['STOP', 'SL']):
                        formatted.append(f"🛑 {line}")
                    elif any(keyword in line.upper() for keyword in ['TAKE', 'TP', 'PROFIT']):
                        formatted.append(f"🎯 {line}")
                    elif any(keyword in line.upper() for keyword in ['ENTRY', 'PREIS', 'PRICE']):
                        formatted.append(f"💰 {line}")
                    else:
                        formatted.append(f"   {line}")
        
            return '\n'.join(formatted)
        
        except Exception as e:
            return f"🤖 {response}"  # Fallback bei Formatierungsfehlern

    def display_technical_summary(self, symbol):
        """Zeigt eine kompakte technische Zusammenfassung"""
        try:
            print("\n📊 TECHNISCHE INDIKATOREN ZUSAMMENFASSUNG:")
            print("─" * 50)
        
            # RSI
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if rsi_value:
                rsi_signal, rsi_desc = self.market.get_rsi_signal(rsi_value)
                rsi_icon = "🟢" if rsi_signal == "BUY" else "🔴" if rsi_signal == "SELL" else "🟡"
                print(f"{rsi_icon} RSI ({self.market.rsi_period}): {rsi_value} - {rsi_desc}")
        
            # MACD
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if macd_data:
                macd_signal, macd_desc = self.market.get_macd_signal(macd_data)
                macd_icon = "🟢" if macd_signal == "BUY" else "🔴" if macd_signal == "SELL" else "🟡"
                print(f"{macd_icon} MACD: {macd_data['macd']:.6f} - {macd_desc[:50]}...")
        
            # Support/Resistance
            sr_data = self.market.calculate_support_resistance(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if sr_data:
                current_price = sr_data['current_price']
            
                if sr_data['support_levels']:
                    sup_level = sr_data['support_levels'][0]['price']
                    sup_strength = sr_data['support_levels'][0]['strength']
                    distance = abs(current_price - sup_level) / current_price * 10000
                    print(f"🔵 Nächster Support: {sup_level:.5f} ({distance:.1f} Pips, Stärke: {sup_strength})")
            
                if sr_data['resistance_levels']:
                    res_level = sr_data['resistance_levels'][0]['price']
                    res_strength = sr_data['resistance_levels'][0]['strength']
                    distance = abs(current_price - res_level) / current_price * 10000
                    print(f"🔴 Nächste Resistance: {res_level:.5f} ({distance:.1f} Pips, Stärke: {res_strength})")
        
            # Multi-Timeframe Trend (falls aktiviert)
            if self.mtf_enabled:
                trend_data = self.market.get_higher_timeframe_trend(symbol, self.trend_timeframe)
                if trend_data:
                    trend_icon = "🟢" if "BULLISH" in trend_data['direction'] else "🔴" if "BEARISH" in trend_data['direction'] else "🟡"
                    tf_name = self.timeframe_names.get(self.trend_timeframe, "H1")
                    print(f"{trend_icon} {tf_name} Trend: {trend_data['direction']} ({trend_data['quality']})")
        
            print("─" * 50)
        
        except Exception as e:
            print(f"⚠️ Technische Zusammenfassung Fehler: {e}")

    def parse_ai_recommendation(self, ai_text):
        try:
            import re
            text_upper = ai_text.upper()
            
            action = None
            
            # Suche gezielt nach den isolierten Wörtern am Anfang oder als klare Aussage
            buy_match = re.search(r'\b(BUY|KAUFEN)\b', text_upper)
            sell_match = re.search(r'\b(SELL|VERKAUFEN)\b', text_upper)
            wait_match = re.search(r'\b(WARTEN|HOLD)\b', text_upper)
            
            # Finde die Positionen der ersten Treffer
            pos_buy = buy_match.start() if buy_match else 9999
            pos_sell = sell_match.start() if sell_match else 9999
            pos_wait = wait_match.start() if wait_match else 9999
            
            min_pos = min(pos_buy, pos_sell, pos_wait)
            
            if min_pos == 9999:
                return None
            elif min_pos == pos_wait:
                return None  # WARTEN = False/None
            elif min_pos == pos_buy:
                action = "BUY"
            elif min_pos == pos_sell:
                action = "SELL"
            
            if not action:
                return None
            
            reasoning = self.extract_trade_reasoning(ai_text)
            
            return {
                "action": action,
                "reasoning": reasoning
            }
            
        except Exception:
            return None
    
    # ==========================================
    # 12. AUTO TRADING SYSTEM
    # ==========================================
    def auto_trade_cycle(self, symbol):
        """Verbesserte auto_trade_cycle mit korrigierter Variable-Reihenfolge"""
        try:
            # 1. ERST SYMBOL UND TICK INFO HOLEN - VOR ALLEN ANDEREN CHECKS!
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                print(f"{symbol}: Keine Marktdaten verfügbar")
                return False
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                print(f"{symbol}: Keine Tick-Daten verfügbar")
                return False

            # 2. JETZT ERST BASIS RISK CHECK
            can_trade, reason = self.risk_manager.can_open_position(symbol, "BUY", self.default_lot_size)
            if not can_trade:
                self.log("INFO", f"{symbol}: {reason}", "RISK")
                return False
    
            # 3. MULTI-TIMEFRAME TREND-FILTER
            if self.mtf_enabled and self.require_trend_confirmation:
                trend_data = self.market.get_higher_timeframe_trend(symbol, self.trend_timeframe)
                if not trend_data:
                    print(f"{symbol}: Trend-Analyse fehlgeschlagen")
                    return False
        
                trend_direction = trend_data['direction']
                # trend_strength = trend_data['strength'] # Not available in new impl directly, check return dict
                
                # NUR in Trendrichtung handeln
                if trend_direction == "NEUTRAL":
                     print(f"{symbol}: Kein klarer Trend")
                     return False
    
            # 4. LIVE-DATEN UND KI-ANALYSE
            live_data = self.broker.get_live_data(symbol)
            if not live_data:
                print(f"{symbol}: Fehler beim Laden der Marktdaten")
                return False
            
            # Formuliere den kompletten Prompt inkl. Trading Style
            prompt = (
                f"Analysiere {symbol} für {self.trading_style} mit Risikoprofil '{self.risk_profile}'. "
                f"Berücksichtige die aktuellen M15/H1 Indikatoren und S/R Level. "
                "Gib am Anfang in Großbuchstaben strikt 'BUY', 'SELL' oder 'WARTEN' aus, gefolgt von einer extrem kurzen Begründung (max 1 Satz)."
            )

            # Use sync wrapper to avoid Coroutine errors!
            ai_response = self.chat_with_model(prompt, str(live_data))
            recommendation = self.parse_ai_recommendation(ai_response)
        
            if not recommendation:
                print(f"{symbol}: WARTEN")
                return False
            
            action = recommendation["action"]
            reasoning = recommendation.get("reasoning", "KI-Analyse")
    
            # 5. MULTI-TIMEFRAME BESTÄTIGUNG
            trend_direction = None  # Initialize to avoid unbound variable
            if self.mtf_enabled and self.require_trend_confirmation:
                if action == "BUY" and "BEARISH" in trend_direction:
                    print(f"{symbol}: Trend bearish - BUY abgelehnt")
                    return False
                elif action == "SELL" and "BULLISH" in trend_direction:
                    print(f"{symbol}: Trend bullish - SELL abgelehnt")
                    return False
    
            # 6. PRÜFE OB BEREITS POSITION OFFEN
            positions = mt5.positions_get(symbol=symbol)
            if positions:
                print(f"{symbol}: Position bereits offen")
                return False
            
            # 7. RSI-FILTER
            rsi_value = self.market.calculate_rsi(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if rsi_value:
                if action == "BUY" and rsi_value > self.market.rsi_overbought:
                    print(f"{symbol}: RSI überkauft ({rsi_value}) - BUY abgelehnt")
                    return False
                elif action == "SELL" and rsi_value < self.market.rsi_oversold:
                    print(f"{symbol}: RSI überverkauft ({rsi_value}) - SELL abgelehnt")
                    return False

            # 8. MACD-FILTER
            macd_data = self.market.calculate_macd(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if macd_data:
                macd_signal, _ = self.market.get_macd_signal(macd_data)
                if action == "BUY" and macd_signal == "SELL":
                    print(f"{symbol}: MACD bearisch - BUY abgelehnt")
                    return False
                elif action == "SELL" and macd_signal == "BUY":
                    print(f"{symbol}: MACD bullisch - SELL abgelehnt")
                    return False
        
                # MACD Histogram-Validierung
                if action == "BUY" and macd_data['histogram'] < 0 and macd_data['histogram_trend'] == "FALLEND":
                    print(f"{symbol}: MACD Histogram fallend - BUY abgelehnt")
                    return False
                elif action == "SELL" and macd_data['histogram'] > 0 and macd_data['histogram_trend'] == "STEIGEND":
                    print(f"{symbol}: MACD Histogram steigend - SELL abgelehnt")
                    return False

            # 9. SUPPORT/RESISTANCE FILTER
            sr_data = self.market.calculate_support_resistance(symbol, mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385)
            if sr_data:
                current_price = tick.ask if action == "BUY" else tick.bid
            
                if action == "BUY" and sr_data['resistance_levels']:
                    res_level = sr_data['resistance_levels'][0]['price']
                    distance_to_res = abs(current_price - res_level) / current_price * 10000
                    if distance_to_res < 5:
                        print(f"{symbol}: Zu nah an Resistance ({distance_to_res:.1f} Pips) - BUY abgelehnt")
                        return False
                    
                elif action == "SELL" and sr_data['support_levels']:
                    sup_level = sr_data['support_levels'][0]['price']
                    distance_to_sup = abs(current_price - sup_level) / current_price * 10000
                    if distance_to_sup < 5:
                        print(f"{symbol}: Zu nah an Support ({distance_to_sup:.1f} Pips) - SELL abgelehnt")
                        return False

            # 10. STOP-LOSS UND TAKE-PROFIT BERECHNUNG
            current_price = tick.ask if action == "BUY" else tick.bid
            min_distance = symbol_info.trade_stops_level * symbol_info.point * 2

            stop_loss = 0.0
            take_profit = 0.0

            if sr_data and action == "BUY":
                # Stop-Loss unter nächstem Support
                if sr_data['support_levels']:
                    sup_level = sr_data['support_levels'][0]['price']
                    suggested_sl = sup_level - (symbol_info.point * 10)
                    stop_loss = max(suggested_sl, current_price - 0.0050) # Fallback wenn Support zu tief
                else:
                    stop_loss = current_price - 0.0050
                
                # Take-Profit an nächster Resistance
                if sr_data['resistance_levels']:
                    res_level = sr_data['resistance_levels'][0]['price']
                    suggested_tp = res_level - (symbol_info.point * 10)
                    take_profit = min(suggested_tp, current_price + 0.0100)
                else:
                    take_profit = current_price + 0.0100
                
            elif sr_data and action == "SELL":
                # Stop-Loss über nächster Resistance
                if sr_data['resistance_levels']:
                    res_level = sr_data['resistance_levels'][0]['price']
                    suggested_sl = res_level + (symbol_info.point * 10)
                    stop_loss = min(suggested_sl, current_price + 0.0050)
                else:
                    stop_loss = current_price + 0.0050
                
                # Take-Profit an nächstem Support
                if sr_data['support_levels']:
                    sup_level = sr_data['support_levels'][0]['price']
                    suggested_tp = sup_level + (symbol_info.point * 10)
                    take_profit = max(suggested_tp, current_price - 0.0100)
                else:
                    take_profit = current_price - 0.0100
            else:
                # Fallback zu Standard-Levels
                if action == "BUY":
                    stop_loss = current_price - 0.0050
                    take_profit = current_price + 0.0100
                else:
                    stop_loss = current_price + 0.0050
                    take_profit = current_price - 0.0100

            # 11. TRADE AUSFÜHREN
            print(f"🔄 Analysiere {symbol}...")
            # Ensure SL/TP are within allowed distances
            if action == "BUY":
                 if stop_loss >= current_price - min_distance: stop_loss = current_price - min_distance - symbol_info.point
                 if take_profit <= current_price + min_distance: take_profit = current_price + min_distance + symbol_info.point
            else:
                 if stop_loss <= current_price + min_distance: stop_loss = current_price + min_distance + symbol_info.point
                 if take_profit >= current_price - min_distance: take_profit = current_price - min_distance - symbol_info.point

            result = self.execute_trade(symbol, action, self.default_lot_size, stop_loss=stop_loss, take_profit=take_profit)

            # 12. ERGEBNIS UND BEGRÜNDUNG ANZEIGEN
            if "✅" in str(result): # Convert dict/result to str to be safe
                inds_used = []
                if rsi_value: inds_used.append("RSI")
                if macd_data: inds_used.append("MACD")
                if sr_data: inds_used.append("S/R")
                if self.mtf_enabled: inds_used.append("MTF Trend")
                
                self.log_trade(symbol, action, result, 
                               reasoning=reasoning, 
                               confidence="AutoTrade", 
                               indicators=inds_used,
                               lot_size=self.default_lot_size)
                               
                print(f"📊 Begründung: {reasoning}")
                if self.mtf_enabled and 'trend_data' in locals() and trend_data:
                    print(f"📈 H1-Trend: {trend_data['direction']} (Stärke: {trend_data.get('strength', 0):.5f})")
                if rsi_value:
                    print(f"📈 RSI: {rsi_value}")
                if macd_data:
                    print(f"📊 MACD: {macd_data['macd']:.6f} (Signal: {macd_data['signal']:.6f})")
                    print(f"📊 Histogram: {macd_data['histogram']:.6f} ({macd_data['histogram_trend']})")
                if sr_data and sr_data['support_levels']:
                    sup_level = sr_data['support_levels'][0]['price']
                    sup_strength = sr_data['support_levels'][0]['strength']
                    print(f"🔵 Support: {sup_level:.5f} (Stärke: {sup_strength})")
                if sr_data and sr_data['resistance_levels']:
                    res_level = sr_data['resistance_levels'][0]['price']
                    res_strength = sr_data['resistance_levels'][0]['strength']
                    print(f"🔴 Resistance: {res_level:.5f} (Stärke: {res_strength})")

            print(result)
            return "✅" in str(result)

        except Exception as e:
            print(f"{symbol}: Unerwarteter Fehler - {e}")
            self.log_error("auto_trade_cycle", e, f"Symbol: {symbol}")
            return False
            
    def _stoppable_sleep(self, seconds):
        """Pausiert für 'seconds' Sekunden, bricht ab wenn '0' gedrückt wird."""
        import msvcrt
        iterations = int(seconds * 10)
        for _ in range(iterations):
            if not self.auto_trading: # Falls extern gestoppt
                return False
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'0':
                    self.auto_trading = False
                    self.log("INFO", "Auto-Trading durch Benutzer (Taste 0) gestoppt!", "SYSTEM")
                    return False
            time.sleep(0.1)
        return True
    
    def should_trade_now(self):
        """
        Überprüft, ob der Handel jetzt erlaubt ist basierend auf:
        - Aktueller Wochentag (Handelstage)
        - Aktueller Zeit (Handelszeiten)
        
        Rückgabe: True wenn Handel erlaubt, False wenn nicht
        """
        import datetime
        from core.app_config import app_config_manager
        
        now = datetime.datetime.now()
        current_day = now.weekday()  # 0 = Montag, 6 = Sonntag
        current_time = now.time()
        
        # Lade Konfiguration aus app_config
        try:
            cfg = app_config_manager.load()
            # Wochentag-Mapping aus Konfiguration (Python weekday: 0=Mo, 6=So)
            day_mapping = {
                0: getattr(cfg, 'day_mon', True),   # Montag
                1: getattr(cfg, 'day_tue', True),   # Dienstag
                2: getattr(cfg, 'day_wed', True),   # Mittwoch
                3: getattr(cfg, 'day_thu', True),   # Donnerstag
                4: getattr(cfg, 'day_fri', True),   # Freitag
                5: getattr(cfg, 'day_sat', False),   # Samstag
                6: getattr(cfg, 'day_sun', False),  # Sonntag
            }
            # Handelszeiten aus Konfiguration
            time_filter = getattr(cfg, 'time_filter', True)
            trade_time_from = getattr(cfg, 'trade_time_from', "08:00")
            trade_time_to = getattr(cfg, 'trade_time_to', "20:00")
        except Exception as e:
            # BEISPIEL: Bei Config-Fehler Trading blockieren statt permissive Defaults zu verwenden
            self.log("ERROR", f"Konnte Konfiguration nicht laden: {e} - Trading deaktiviert", "SYSTEM")
            # Sichere Option: Trading blockieren wenn Config nicht verfügbar ist
            return False
        
        # Prüfe ob heute ein Handelstag ist
        is_trading_day = day_mapping.get(current_day, False)
        if not is_trading_day:
            self.log("INFO", f"Kein Handelstag heute ({['Mo','Di','Mi','Do','Fr','Sa','So'][current_day]})", "TRADE")
            return False
        
        # Prüfe Zeitfilter
        if time_filter:
            try:
                # Parse Zeit (unterstütze "08:00" und "8:00" Format)
                start_time = datetime.datetime.strptime(trade_time_from.strip(), "%H:%M").time()
                end_time = datetime.datetime.strptime(trade_time_to.strip(), "%H:%M").time()
                
                # Prüfe Zeitfenster
                if not (start_time <= current_time <= end_time):
                    self.log("INFO", f"Ausserhalb der Handelszeit ({trade_time_from} - {trade_time_to})", "TRADE")
                    return False
            except (ValueError, AttributeError) as e:
                self.log("WARNING", f"Zeitfilter-Fehler: {e} - Trading blockiert", "SYSTEM")
                # Bei Fehler: Handel BLOCKIEREN (Conservative Security)
                return False
        
        return True

    def run_auto_trading(self):
        """Auto-Trading mit MT5 Auto-Reconnect bei Verbindungsverlust."""
        self.log("INFO", "STARTE AUTO-TRADING | STOPP: Taste '0' oder Ctrl+C", "SYSTEM")
        self.log("INFO", f"Symbole: {self.auto_trade_symbols} | Intervall: {self.analysis_interval}s", "SYSTEM")

        cycle = 0
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while self.auto_trading:
                cycle += 1
                self.log("INFO", f"ZYKLUS #{cycle} - {datetime.now().strftime('%H:%M:%S')}", "SYSTEM")
                
                # ── Zeit- und Tagesfilterung ───────────────────────────────────
                if not self.should_trade_now():
                    self.log("INFO", "Ausserhalb der erlaubten Handelszeiten - Warte...", "TRADE")
                    if not self._stoppable_sleep(60):
                        break
                    continue

                # ── MT5 Liveness-Check & Auto-Reconnect ──────────────────
                if not self.is_mt5_alive():
                    self.log("WARNING", "MT5 nicht erreichbar — Auto-Reconnect wird gestartet…", "MT5")
                    if not self.reconnect_mt5(max_retries=10, base_delay=5.0):
                        self.log("ERROR", "MT5 Reconnect endgueltig fehlgeschlagen — Trading beendet", "MT5")
                        self.auto_trading = False
                        break
                    consecutive_errors = 0

                # ── System Health Check alle 10 Zyklen ────────────────────
                if cycle % 10 == 0:
                    if not self.system_health_check():
                        self.log("WARNING", "Health Check fehlgeschlagen - 60s Pause", "SYSTEM")
                        if not self._stoppable_sleep(60): break
                        continue

                # ── Position Management alle 2 Zyklen ─────────────────────
                if cycle % 2 == 0:
                    try:
                        self.log("INFO", "Position Management Check...", "SYSTEM")
                        self.manage_open_positions()
                    except Exception as e:
                        self.log("WARNING", f"Position Management Fehler: {e}", "SYSTEM")
                        self.log_error("position_management", e)

                cycle_errors = 0

                # ── Symbole iterieren ──────────────────────────────────────
                for i, symbol in enumerate(self.auto_trade_symbols):
                    try:
                        self.log("INFO", f"[{i+1}/{len(self.auto_trade_symbols)}] {symbol}", "SYSTEM")
                        success = self.auto_trade_cycle_with_timeout(symbol, timeout=30)
                        if success:
                            consecutive_errors = 0
                        
                        if not self._stoppable_sleep(2): break
                    except Exception as e:
                        consecutive_errors += 1
                        cycle_errors += 1
                        self.log("ERROR", f"{symbol}: Fehler - {e}", "SYSTEM")
                        self.log_error("auto_trade_symbol", e, f"Symbol: {symbol}, Zyklus: {cycle}")
                        if consecutive_errors >= max_consecutive_errors:
                            self.log("WARNING",
                                     f"Zu viele Fehler ({consecutive_errors}) - 5 Min Pause", "SYSTEM")
                            if not self._stoppable_sleep(300): break
                            consecutive_errors = 0

                # ── Zyklus-Zusammenfassung ─────────────────────────────────
                status_text = "OK" if cycle_errors == 0 else "Warnung (Teilfehler)" if cycle_errors < len(self.auto_trade_symbols) else "FEHLER"
                self.log("INFO",
                         f"{status_text} Zyklus #{cycle} abgeschlossen", "SYSTEM")

                if hasattr(self, 'risk_manager') and self.risk_manager and cycle % 5 == 0:
                    try:
                        summary = self.risk_manager.get_risk_summary()
                        self.log("INFO",
                                 f"Tages P&L: {summary.get('daily_pnl', 0):.2f} | "
                                 f"Trades: {summary.get('trades_today', 0)}", "TRADE")
                    except Exception as e:
                        self.log("WARNING", f"Risk Summary Fehler: {e}", "SYSTEM")

                self.log("INFO", f"Warte {self.analysis_interval}s... (Drücke '0' zum Beenden)", "SYSTEM")
                if not self._stoppable_sleep(self.analysis_interval):
                    break

        except KeyboardInterrupt:
            self.log("INFO", "Auto-Trading durch Benutzer gestoppt!", "SYSTEM")
            self.auto_trading = False
        except Exception as e:
            self.log("ERROR", f"Kritischer Auto-Trading Fehler: {e}", "SYSTEM")
            self.log_error("run_auto_trading", e)
            self.auto_trading = False
        finally:
            self.log("INFO", "Auto-Trading beendet", "SYSTEM")


    def system_health_check(self):
        """System Health Check für Auto-Trading"""
        try:
            checks = {
                'mt5_connection': False,
                'ollama_connection': False,
                'risk_manager': False,
                'memory_usage': False
            }
        
            # 1. MT5 Verbindung prüfen
            if self.mt5_connected:
                test_tick = mt5.symbol_info_tick("EURUSD")
                checks['mt5_connection'] = test_tick is not None
        
            # 2. Ollama Verbindung prüfen
            checks['ollama_connection'] = self.ai.check_ollama_status()
        
            # 3. Risk Manager Status prüfen
            if hasattr(self, 'risk_manager') and self.risk_manager:
                try:
                    summary = self.risk_manager.get_risk_summary()
                    checks['risk_manager'] = summary is not None
                except:
                    checks['risk_manager'] = False
        
            # 4. Memory Usage prüfen (vereinfacht)
            import psutil
            memory_percent = psutil.virtual_memory().percent
            checks['memory_usage'] = memory_percent < 90
        
            # Ergebnis bewerten
            health_score = sum(checks.values()) / len(checks)
        
            if health_score < 0.75:  # Weniger als 75% der Checks bestanden
                print(f"⚠️ System Health: {health_score:.0%}")
                for check, status in checks.items():
                    icon = "✅" if status else "❌"
                    print(f"   {icon} {check}")
                return False
        
            return True
        
        except Exception as e:
            print(f"❌ Health Check Fehler: {e}")
            return False

    def auto_trade_cycle_with_timeout(self, symbol, timeout=30):
        """Auto-Trade Cycle mit Timeout-Schutz"""
        import threading
        import time
    
        result = [False]  # Liste für Referenz-Sharing zwischen Threads
        exception = [None]
    
        def target():
            try:
                result[0] = self.auto_trade_cycle(symbol)
            except Exception as e:
                exception[0] = e
    
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
    
        if thread.is_alive():
            print(f"⏰ {symbol}: Timeout nach {timeout}s - wird übersprungen")
            return False
    
        if exception[0]:
            raise exception[0]
    
        return result[0]

    def enhanced_logging_for_auto_trading(self):
        """Erweiterte Logging-Funktionen für Auto-Trading"""
    
        def log_auto_trade_stats(self, cycle, symbol, action, result):
            """Detailliertes Logging für Auto-Trading Statistiken"""
            timestamp = datetime.now().strftime('%H:%M:%S')
        
            # Erstelle strukturierte Log-Nachricht
            log_data = {
                'timestamp': timestamp,
                'cycle': cycle,
                'symbol': symbol,
                'action': action,
                'result': result,
                'daily_trades': getattr(self, 'daily_trade_count', 0),
                'success_rate': self.calculate_success_rate()
            }
        
            # Log in Datei schreiben
            if self.logger:
                self.logger.info(f"AUTO_TRADE: {json.dumps(log_data)}")
        
            # Konsolen-Output
            result_icon = "✅" if "SUCCESS" in result else "❌"
            print(f"{timestamp} {result_icon} #{cycle} {symbol} {action} - {result}")
    
        def calculate_success_rate(self):
            """Berechnet aktuelle Erfolgsrate"""
            try:
                if not hasattr(self, 'trade_history'):
                    self.trade_history = []
            
                if len(self.trade_history) == 0:
                    return 0.0
            
                successful_trades = sum(1 for trade in self.trade_history[-20:] if trade.get('success', False))
                return (successful_trades / min(20, len(self.trade_history))) * 100
            except:
                return 0.0

    def print_callable_methods(self):
        """Druckt alle aufrufbaren Methoden der Klasse (für Debugging)"""
        methods = [method for method in dir(self) if callable(getattr(self, method)) and not method.startswith("__")]
        
        print(f"\nAufrufbare Methoden der {self.__class__.__name__} Klasse:")
        print("=" * 50)
        
        # Gruppiere Methoden nach Funktionalität
        trading_methods = [m for m in methods if any(keyword in m.lower() for keyword in ['trade', 'order', 'position'])]
        analysis_methods = [m for m in methods if any(keyword in m.lower() for keyword in ['rsi', 'calculate', 'analyze', 'signal'])]
        mt5_methods = [m for m in methods if 'mt5' in m.lower() or 'connect' in m.lower()]
        ui_methods = [m for m in methods if any(keyword in m.lower() for keyword in ['menu', 'print', 'interactive'])]
        other_methods = [m for m in methods if m not in trading_methods + analysis_methods + mt5_methods + ui_methods]
        
        categories = [
            ("📊 Trading Methoden", trading_methods),
            ("📈 Analyse Methoden", analysis_methods), 
            ("🔗 MT5 Methoden", mt5_methods),
            ("🖥️ UI Methoden", ui_methods),
            ("⚙️ Sonstige Methoden", other_methods)
        ]
        
        for category_name, method_list in categories:
            if method_list:
                print(f"\n{category_name}:")
                for method in sorted(method_list):
                    print(f"  - {method}")
        
        print("=" * 50)

    def install_dependencies(self):
        """Überprüft und installiert notwendige Abhängigkeiten"""
        try:
            required_packages = ['MetaTrader5', 'numpy', 'requests']
            missing_packages = []
            
            print("Überprüfe Abhängigkeiten...")
            
            for package in required_packages:
                try:
                    __import__(package)
                    print(f"  ✅ {package}")
                except ImportError:
                    print(f"  ❌ {package}")
                    missing_packages.append(package)
            
            if missing_packages:
                print(f"Fehlende Pakete: {missing_packages}")
                print("Installation mit: pip install " + " ".join(missing_packages))
                return False
            
            print("Alle Abhängigkeiten verfügbar")
            return True
            
        except Exception as e:
            print(f"Dependency-Check Fehler: {e}")
            return False

    # ==========================================
    # 13. SYSTEM LIFECYCLE
    # ==========================================
    def shutdown_system(self):
        """Erweiterte System-Shutdown Prozedur"""
        self.log("INFO", "System-Shutdown eingeleitet", "SYSTEM")
        self.print_header("SYSTEM BEENDEN")
        print("Stoppe alle Prozesse...")

        # Companion stoppen
        if self.companion_enabled:
            self.log("INFO", "Trading Companion wird gestoppt", "COMPANION")
            print("Stoppe Trading Companion...")
            self.stop_trading_companion()

        # Auto-Trading stoppen
        if self.auto_trading:
            self.log("INFO", "Auto-Trading wird gestoppt", "TRADE")
            print("Stoppe Auto-Trading...")
            self.auto_trading = False

        # RL System stoppen (falls vorhanden)
        if getattr(self, 'rl_enabled', False) and hasattr(self, 'rl_manager'):
            try:
                print("Speichere RL-Modell...")
                # Hier könnte RL-spezifische Cleanup-Logik stehen
                self.log("INFO", "RL System gestoppt", "RL")
            except Exception as e:
                print(f"⚠️ RL Shutdown Fehler: {e}")

        # Risk Manager Abschlussbericht
        if hasattr(self, 'risk_manager') and self.risk_manager:
            try:
                print("\n🛡️ Session Abschlussbericht:")
                summary = self.risk_manager.get_risk_summary()
                if summary:
                    print(f"📊 Tages P&L: {summary.get('daily_pnl', 0):.2f}€")
                    print(f"💼 Trades heute: {summary.get('trades_today', 0)}")
                    print(f"📈 Offene Positionen: {summary.get('open_positions', 0)}")
                
                    # Erweiterte Statistiken
                    if getattr(self, 'has_extended_indicators', False):
                        print(f"📊 Analysierte Symbole: {getattr(self, 'analyzed_symbols_count', 0)}")
                        print(f"🎯 Generierte Signale: {getattr(self, 'generated_signals_count', 0)}")
            except Exception as e:
                print(f"⚠️ Risk Manager Abschlussbericht Fehler: {e}")

        # MT5 trennen
        if self.mt5_connected:
            self.log("INFO", "MT5 Verbindung wird getrennt", "MT5")
            print("Trenne MT5...")
            self.disconnect_mt5()

        # Final Log
        features_used = []
        if getattr(self, 'has_extended_indicators', False):
            features_used.append("Erweiterte Indikatoren")
        if getattr(self, 'rl_enabled', False):
            features_used.append("RL Trading")
        if hasattr(self, 'risk_manager') and self.risk_manager:
            features_used.append("Risk Management")
    
        if features_used:
            print(f"\n✅ Genutzte erweiterte Features: {', '.join(features_used)}")
    
        self.log("INFO", "System erfolgreich heruntergefahren", "SYSTEM")
        print("Alle Prozesse beendet. Auf Wiedersehen!")
        return False

def signal_handler(sig, frame):
        """Signal Handler für sauberes Beenden"""
        print("\n🛑 Beende alle Prozesse...")
        # Hier können Sie Cleanup-Code hinzufügen
        try:
            # Global bot instance falls verfügbar
            if 'bot' in globals() and bot is not None:
                if hasattr(bot, 'companion_enabled') and bot.companion_enabled:
                    print("🔧 Stoppe Trading Companion...")
                    bot.stop_trading_companion()
            
                if hasattr(bot, 'auto_trading') and bot.auto_trading:
                    print("🔄 Stoppe Auto-Trading...")
                    bot.auto_trading = False
            
                if hasattr(bot, 'mt5_connected') and bot.mt5_connected:
                    print("🔗 Trenne MT5...")
                    bot.disconnect_mt5()
        except Exception as e:
            print(f"⚠️ Cleanup Fehler: {e}")
    
        print("👋 Auf Wiedersehen!")
        sys.exit(0)

def main():
    """Hauptfunktion mit verbesserter Fehlerbehandlung und Risk Management"""
    print("🚀 FinGPT MT5 Setup mit RSI + S/R + Risk Management + Trading Companion")
    print("=" * 65)

    global bot  # Für signal handler
    bot = None

    try:
        bot = MT5FinGPT()
    
        # Abhängigkeiten prüfen
        print("\n📋 SCHRITT 1: Abhängigkeiten")
        if not bot.install_dependencies():
            print("❌ Installieren Sie fehlende Pakete und starten Sie neu")
            return
    
        # Risk Management System Test
        print("\n📋 SCHRITT 2: Risk Management System")
        try:
            if hasattr(bot, 'risk_manager') and bot.risk_manager:
                print("✅ Risk Manager erfolgreich initialisiert")
                
                # Zeige aktuelle Risk Settings
                print(f"   💰 Max Tagesverlust: {bot.risk_manager.max_daily_loss}€")
                print(f"   📊 Max Risiko pro Trade: {bot.risk_manager.max_risk_per_trade}%")
                print(f"   🎯 Max Positionen: {bot.risk_manager.max_total_positions}")
                print(f"   ⏰ Trading Zeiten: {bot.risk_manager.trading_start_hour}:00 - {bot.risk_manager.trading_end_hour}:00")
                
                # Test der Risk Summary
                summary = bot.risk_manager.get_risk_summary()
                if summary:
                    print("✅ Risk Management Funktionen verfügbar")
                else:
                    print("⚠️ Risk Summary Test fehlgeschlagen")
            else:
                print("❌ Risk Manager nicht initialisiert")
                print("💡 Tipp: Prüfen Sie ob risk_manager.py existiert")
        except Exception as e:
            print(f"❌ Risk Management Fehler: {e}")
            print("💡 System läuft weiter, aber ohne Risk Management")

        # Ollama Status prüfen
        print("\n📋 SCHRITT 3: Ollama Server")
        if not bot.ai.check_ollama_status():
            print("❌ Ollama nicht erreichbar. Starten mit: 'ollama serve'")
            print("💡 Tipp: Öffnen Sie ein neues Terminal und führen Sie 'ollama serve' aus")
            print("⚠️ System läuft weiter, aber KI-Analyse ist nicht verfügbar")
        else:
            print("✅ Ollama Server erreichbar")

            # Modelle laden
            print("\n📋 SCHRITT 4: KI-Modelle")
            if not bot.ai.get_available_models():
                print("❌ Keine Ollama-Modelle gefunden")
                print("💡 Tipp: Installieren Sie ein Modell mit 'ollama pull llama3.1:8b'")
            elif not bot.ai.select_finance_model():
                print("❌ Kein passendes Finanz-Modell gefunden")
                print("💡 Tipp: Installieren Sie ein empfohlenes Modell")
            else:
                # Sync selected_model für Status-Anzeige
                bot.selected_model = bot.ai.selected_model

        # MT5 Verbindung
        print("\n📋 SCHRITT 5: MetaTrader 5")
        if bot.broker.connect_mt5():
            # Sync mt5_connected für Status-Anzeige
            bot.mt5_connected = bot.broker.mt5_connected

            # Test der MT5-Daten
            test = bot.broker.get_mt5_live_data("EURUSD")
            if "Fehler" not in test:
                print("✅ MT5-Daten verfügbar!")
                
                # Risk Manager mit MT5 testen (falls verfügbar)
                if hasattr(bot, 'risk_manager') and bot.risk_manager:
                    try:
                        # Test Position Size Berechnung
                        test_lot_size = bot.risk_manager.calculate_position_size("EURUSD", 20.0, 1.0)
                        print(f"✅ Risk Calculator Test: {test_lot_size} Lots für 20 Pips SL")
                        
                        # Test Can Open Position
                        can_trade, reason = bot.risk_manager.can_open_position("EURUSD", "BUY", 0.1)
                        if can_trade:
                            print("✅ Risk Checks: Trading erlaubt")
                        else:
                            print(f"ℹ️ Risk Checks: {reason}")
                            
                    except Exception as e:
                        print(f"⚠️ Risk Calculator Test Fehler: {e}")
            else:
                print(f"⚠️ MT5 verbunden, aber Datentest fehlgeschlagen: {test}")
        else:
            print("⚠️ MT5 nicht verbunden - Trading-Features eingeschränkt")
            print("💡 Risk Management funktioniert trotzdem für Demo-Zwecke")

        # System Status Zusammenfassung
        print("\n📊 SYSTEM STATUS:")
        print("─" * 40)
        
        components = [
            ("🤖 KI-System", "✅" if bot.selected_model else "❌"),
            ("📱 MT5", "✅" if bot.mt5_connected else "❌"), 
            ("🛡️ Risk Manager", "✅" if hasattr(bot, 'risk_manager') and bot.risk_manager else "❌"),
            ("📊 Technische Analyse", "✅"),  # RSI, MACD, S/R sind immer verfügbar
            ("🔧 Trading Companion", "⚠️" if hasattr(bot, 'companion_process') else "❌")
        ]
        
        for component, status in components:
            print(f"{component}: {status}")
        
        print("─" * 40)

        # Zeige Risk Status wenn verfügbar
        if hasattr(bot, 'risk_manager') and bot.risk_manager and bot.mt5_connected:
            try:
                print("\n🛡️ AKTUELLER RISK STATUS:")
                bot.risk_manager.print_risk_status()
            except Exception as e:
                print(f"⚠️ Risk Status Anzeige Fehler: {e}")

        print("\n🎯 SYSTEM BEREIT")
        print("=" * 65)
        


        # Signal Handler registrieren
        signal.signal(signal.SIGINT, signal_handler)

        # Hauptmenü starten (über CLIMenu)
        bot.cli.interactive_menu()

    except KeyboardInterrupt:
        print("\n🛑 Beendet durch Ctrl+C")
        if bot:
            cleanup_bot(bot)
    except ImportError as e:
        print(f"\n❌ Import-Fehler: {e}")
        if "risk_manager" in str(e):
            print("💡 Lösungsvorschlag:")
            print("   1. Erstellen Sie die Datei 'risk_manager.py' im selben Ordner")
            print("   2. Kopieren Sie den RiskManager Code hinein")
            print("   3. Starten Sie das Programm neu")
        else:
            print("💡 Installieren Sie fehlende Pakete mit: pip install <paketname>")
    except Exception as e:
        print(f"\n💥 Unerwarteter Fehler: {e}")
        import traceback
        print("🔍 Fehler-Details:")
        traceback.print_exc()
        if bot:
            cleanup_bot(bot)

def cleanup_bot(bot):
    """Erweiterte Hilfsfunktion für sauberes Beenden mit Risk Manager"""
    try:
        if hasattr(bot, 'companion_enabled') and bot.companion_enabled:
            print("🔧 Stoppe Trading Companion...")
            bot.stop_trading_companion()

        if hasattr(bot, 'auto_trading') and bot.auto_trading:
            print("🔄 Stoppe Auto-Trading...")
            bot.auto_trading = False

        # Risk Manager Abschlussbericht
        if hasattr(bot, 'risk_manager') and bot.risk_manager:
            try:
                print("🛡️ Risk Manager Abschlussbericht:")
                summary = bot.risk_manager.get_risk_summary()
                if summary:
                    print(f"   📊 Tages P&L: {summary.get('daily_pnl', 0):.2f}€")
                    print(f"   💼 Trades heute: {summary.get('trades_today', 0)}")
                    print(f"   📈 Offene Positionen: {summary.get('open_positions', 0)}")
            except Exception as e:
                print(f"⚠️ Risk Manager Abschlussbericht Fehler: {e}")

        if hasattr(bot, 'mt5_connected') and bot.mt5_connected:
            print("🔗 Trenne MT5...")
            bot.disconnect_mt5()
            
    except Exception as e:
        print(f"⚠️ Cleanup Fehler: {e}")


if __name__ == "__main__":
        main()

