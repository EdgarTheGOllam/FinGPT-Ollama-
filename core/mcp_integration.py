"""
MCP Integration für FinGPT
Verbindet TradingView-MCP und Hive Intelligence MCP mit dem Auto-Trading System
"""

import json
import subprocess
import sys
import threading
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("FinGPT MCP")


def _build_npx_cmd(*args) -> list:
    """
    Erstellt den korrekten npx-Befehl abhängig vom Betriebssystem.
    
    Warum nötig: Auf Windows blockiert die PowerShell Execution Policy
    die Ausführung von .ps1-Skripten (npx.ps1, npm.ps1). Durch Verwendung
    von cmd.exe als Wrapper wird npx via npx.cmd aufgerufen, das keine
    Execution-Policy-Prüfung unterläuft.
    """
    if sys.platform == "win32":
        return ["cmd", "/c", "npx"] + list(args)
    return ["npx"] + list(args)


# Fancy console colors
class C:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    LGRAY = "\033[90m"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def mcp_print(msg: str, level: str = "INFO"):
    config = {
        "INFO": {"icon": "🔌 ", "color": C.MAGENTA},
        "SUCCESS": {"icon": "✅ ", "color": C.GREEN},
        "WARN": {"icon": "⚠️ ", "color": C.YELLOW},
        "ERROR": {"icon": "❌ ", "color": C.RED},
    }
    cfg = config.get(level, {"icon": "🔌 ", "color": C.LGRAY})
    print(
        f"{C.LGRAY}[{ts()}]{C.RESET} {cfg['color']}{cfg['icon']}[MCP]{C.RESET} {cfg['color']}{msg}{C.RESET}"
    )


# Mapping von String-Level-Namen zu logging-Integer-Werten.
# Warum nötig: logging.Logger.log() lehnt Strings als Level-Parameter ab
# ("level must be an integer"). Eigene String-Konvention 'SUCCESS' hat kein
# Standard-Äquivalent – wird auf INFO gemappt.
_LOG_LEVEL_MAP: dict = {
    "DEBUG":   logging.DEBUG,
    "INFO":    logging.INFO,
    "SUCCESS": logging.INFO,
    "WARN":    logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR":   logging.ERROR,
    "CRITICAL":logging.CRITICAL,
}


def _resolve_log_level(level) -> int:
    """Konvertiert String-Level-Namen sicher in logging-Integer-Werte."""
    if isinstance(level, int):
        return level
    return _LOG_LEVEL_MAP.get(str(level).upper(), logging.INFO)


class MCPIntegration:
    """Integration für TradingView und Hive Intelligence MCP Server"""

    def __init__(self, logger=None):
        self.logger = logger
        self.tradingview_process = None
        self.hive_process = None
        self.tradingview_ready = False
        self.hive_ready = False
        self._lock = threading.Lock()

    def log(self, level, message):
        # Nutze fancy print statt logging
        mcp_print(message, level)

    def start_tradingview(self):
        """Startet TradingView MCP Server.
        
        Warum subprocess.Popen statt subprocess.run:
        MCP Server sind langlebige Prozesse die dauerhaft im Hintergrund
        laufen müssen – .run() würde blockieren bis der Prozess endet.
        """
        try:
            self.log("INFO", "Starte TradingView MCP Server...")
            self.tradingview_process = subprocess.Popen(
                _build_npx_cmd("-y", "tradingview-mcp-server"),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            # Kurz warten und dann prüfen ob der Prozess noch läuft
            time.sleep(2)
            if self.tradingview_process.poll() is not None:
                # Prozess ist bereits beendet = Fehler beim Start
                stderr_out = self.tradingview_process.stderr.read()
                mcp_print(f"TradingView sofort beendet: {stderr_out[:200]}", "ERROR")
                return False
            self.tradingview_ready = True
            self.log("SUCCESS", "TradingView MCP Server gestartet")
            return True
        except FileNotFoundError:
            mcp_print("npx nicht gefunden. Bitte Node.js/npm installieren.", "ERROR")
            return False
        except Exception as e:
            mcp_print(f"TradingView Start fehlgeschlagen: {e}", "ERROR")
            return False

    def start_hive(self):
        """Startet Hive Intelligence MCP Server.
        
        Warum eigenständiger Prozess: Hive Intelligence ist ein separater MCP-Server
        mit eigenem JSON-RPC-Kanal – beide Server müssen unabhängig voneinander
        laufen damit ein Ausfall nicht den anderen blockiert.
        """
        try:
            self.log("INFO", "Starte Hive Intelligence MCP Server...")
            self.hive_process = subprocess.Popen(
                _build_npx_cmd("-y", "hive-intelligence"),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            time.sleep(2)
            if self.hive_process.poll() is not None:
                stderr_out = self.hive_process.stderr.read()
                mcp_print(f"Hive sofort beendet: {stderr_out[:200]}", "ERROR")
                return False
            self.hive_ready = True
            self.log("SUCCESS", "Hive Intelligence MCP Server gestartet")
            return True
        except FileNotFoundError:
            mcp_print("npx nicht gefunden. Bitte Node.js/npm installieren.", "ERROR")
            return False
        except Exception as e:
            self.log("ERROR", f"Hive Start fehlgeschlagen: {e}")
            return False

    def start_all(self):
        """Startet beide MCP Server"""
        self.start_tradingview()
        self.start_hive()

    def stop_all(self):
        """Stoppt beide MCP Server"""
        if self.tradingview_process:
            self.tradingview_process.terminate()
            self.tradingview_ready = False
        if self.hive_process:
            self.hive_process.terminate()
            self.hive_ready = False
        self.log("INFO", "MCP Server gestoppt")

    def call_tradingview(self, method: str, params: Dict = None) -> Optional[Any]:
        """Ruft TradingView MCP Methode auf"""
        if not self.tradingview_ready:
            return None

        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or {},
            }

            self.tradingview_process.stdin.write(json.dumps(request) + "\n")
            self.tradingview_process.stdin.flush()

            response_line = self.tradingview_process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                return response.get("result")
            return None
        except Exception as e:
            self.log("ERROR", f"TradingView Aufruf fehlgeschlagen: {e}")
            return None

    def call_hive(self, method: str, params: Dict = None) -> Optional[Any]:
        """Ruft Hive Intelligence MCP Methode auf"""
        if not self.hive_ready:
            return None

        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or {},
            }

            self.hive_process.stdin.write(json.dumps(request) + "\n")
            self.hive_process.stdin.flush()

            response_line = self.hive_process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                return response.get("result")
            return None
        except Exception as e:
            self.log("ERROR", f"Hive Aufruf fehlgeschlagen: {e}")
            return None


class TradingViewAnalyzer:
    """TradingView MCP Integration für technische Analyse"""

    def __init__(self, mcp_integration: MCPIntegration, logger=None):
        self.mcp = mcp_integration
        self.logger = logger

    def log(self, level, message):
        if self.logger:
            # logging.Logger.log() erwartet einen Integer-Level, keinen String
            self.logger.log(_resolve_log_level(level), "[TV] %s", message)
        else:
            mcp_print(message, level)

    def screen_stocks(
        self,
        filters: List[Dict] = None,
        sort_by: str = "market_cap_basic",
        sort_order: str = "desc",
        limit: int = 20,
    ) -> List[Dict]:
        """Stock Screening mit TradingView"""
        params = {
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "markets": ["america"],
        }
        if filters:
            params["filters"] = filters

        result = self.mcp.call_tradingview("tradingview_screen_stocks", params)
        if result:
            return result if isinstance(result, list) else []
        return []

    def screen_crypto(
        self,
        filters: List[Dict] = None,
        sort_by: str = "market_cap_basic",
        sort_order: str = "desc",
        limit: int = 20,
    ) -> List[Dict]:
        """Crypto Screening mit TradingView"""
        params = {"sort_by": sort_by, "sort_order": sort_order, "limit": limit}
        if filters:
            params["filters"] = filters

        result = self.mcp.call_tradingview("tradingview_screen_crypto", params)
        if result:
            return result if isinstance(result, list) else []
        return []

    def screen_forex(
        self,
        filters: List[Dict] = None,
        sort_by: str = "volume",
        sort_order: str = "desc",
        limit: int = 20,
    ) -> List[Dict]:
        """Forex Screening mit TradingView"""
        params = {"sort_by": sort_by, "sort_order": sort_order, "limit": limit}
        if filters:
            params["filters"] = filters

        result = self.mcp.call_tradingview("tradingview_screen_forex", params)
        if result:
            return result if isinstance(result, list) else []
        return []

    def get_preset(self, preset_name: str) -> Dict:
        """TradingView Preset abrufen"""
        return self.mcp.call_tradingview(
            "tradingview_get_preset", {"preset_name": preset_name}
        )

    def list_presets(self) -> List[Dict]:
        """Verfügbare Presets auflisten"""
        return self.mcp.call_tradingview("tradingview_list_presets", {})

    def lookup_symbols(self, symbols: List[str]) -> List[Dict]:
        """Symbol-Daten abrufen"""
        return self.mcp.call_tradingview(
            "tradingview_lookup_symbols", {"symbols": symbols}
        )

    def list_fields(
        self, asset_type: str = "stock", category: str = None
    ) -> List[Dict]:
        """Verfügbare Filter-Felder abrufen"""
        params = {"asset_type": asset_type}
        if category:
            params["category"] = category
        return self.mcp.call_tradingview("tradingview_list_fields", params)

    def get_trading_signals(self, symbol: str) -> Dict:
        """Technische Trading-Signale für Symbol"""
        signals = []

        rsi_filter = [{"field": "RSI", "operator": "in_range", "value": [30, 70]}]
        stocks = self.screen_stocks(filters=rsi_filter, limit=50)

        for stock in stocks:
            if symbol.upper() in str(stock.get("symbol", "")).upper():
                return stock

        return {}


class HiveIntelligenceAnalyzer:
    """Hive Intelligence MCP Integration für Marktdaten"""

    def __init__(self, mcp_integration: MCPIntegration, logger=None):
        self.mcp = mcp_integration
        self.logger = logger

    def log(self, level, message):
        if self.logger:
            # logging.Logger.log() erwartet einen Integer-Level, keinen String
            self.logger.log(_resolve_log_level(level), "[HIVE] %s", message)
        else:
            mcp_print(message, level)

    def get_crypto_price(self, symbol: str) -> Optional[Dict]:
        """Aktueller Crypto-Preis"""
        params = {"symbol": symbol.upper()}
        return self.mcp.call_hive("crypto_price", params)

    def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """Aktienkurs abrufen"""
        params = {"symbol": symbol.upper()}
        return self.mcp.call_hive("stock_quote", params)

    def get_forex_rate(self, pair: str) -> Optional[Dict]:
        """Forex-Kurs abrufen"""
        params = {"symbol": pair.upper()}
        return self.mcp.call_hive("forex_rate", params)

    def get_market_summary(self) -> Dict:
        """Markt-Zusammenfassung"""
        return self.mcp.call_hive("market_summary", {}) or {}

    def get_crypto_sentiment(self, symbol: str) -> Optional[Dict]:
        """Crypto Sentiment-Analyse"""
        params = {"symbol": symbol.upper()}
        return self.mcp.call_hive("crypto_sentiment", params)

    def get_news(
        self, symbol: str = None, category: str = None, limit: int = 10
    ) -> List[Dict]:
        """Nachrichten abrufen"""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol.upper()
        if category:
            params["category"] = category

        result = self.mcp.call_hive("news", params)
        if result:
            return result if isinstance(result, list) else []
        return []

    def get_defi_tvl(self, protocol: str = None) -> Dict:
        """DeFi TVL Daten"""
        params = {}
        if protocol:
            params["protocol"] = protocol
        return self.mcp.call_hive("defi_tvl", params) or {}

    def get_network_gas(self, chain: str = "ethereum") -> Dict:
        """Gas-Preise abrufen"""
        params = {"chain": chain}
        return self.mcp.call_hive("network_gas", params) or {}

    def get_portfolio(self, address: str) -> Dict:
        """Wallet-Portfolio abrufen"""
        params = {"address": address}
        return self.mcp.call_hive("portfolio", params) or {}


class MCPTradingEngine:
    """
    Erweiterter Trading-Engine der MCP-Daten in Trading-Entscheidungen integriert
    """

    def __init__(self, app, logger=None):
        self.app = app
        self.logger = logger
        self.mcp = MCPIntegration(logger=logger)
        self.tv = TradingViewAnalyzer(self.mcp, logger=logger)
        self.hive = HiveIntelligenceAnalyzer(self.mcp, logger=logger)
        self.enabled = False

    def log(self, level, message):
        if self.logger:
            # logging.Logger.log() erwartet einen Integer-Level, keinen String
            self.logger.log(_resolve_log_level(level), "[MCP-ENGINE] %s", message)
        else:
            mcp_print(message, level)

    def start(self):
        """MCP Server starten"""
        if not self.enabled:
            self.log("INFO", "Starte MCP Server...")
            self.mcp.start_all()
            self.enabled = True
            self.log("INFO", "MCP Server aktiv")

    def stop(self):
        """MCP Server stoppen"""
        if self.enabled:
            self.mcp.stop_all()
            self.enabled = False

    def get_market_data(self, symbol: str, market_type: str = "forex") -> Dict:
        """
        Sammelt Marktdaten aus allen MCP-Quellen für ein Symbol
        """
        data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "sources": [],
        }

        if market_type == "crypto":
            price_data = self.hive.get_crypto_price(symbol)
            if price_data:
                data["price"] = price_data
                data["sources"].append("hive_crypto")

            sentiment = self.hive.get_crypto_sentiment(symbol)
            if sentiment:
                data["sentiment"] = sentiment
                data["sources"].append("hive_sentiment")

        elif market_type == "stock":
            quote = self.hive.get_stock_quote(symbol)
            if quote:
                data["quote"] = quote
                data["sources"].append("hive_stock")

        elif market_type == "forex":
            rate = self.hive.get_forex_rate(symbol)
            if rate:
                data["rate"] = rate
                data["sources"].append("hive_forex")

        return data

    def get_trading_signals(self, symbol: str, market_type: str = "forex") -> Dict:
        """
        Generiert Trading-Signale basierend auf MCP-Daten
        """
        signals = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "signals": [],
            "action": "WARTEN",
            "confidence": 0,
        }

        try:
            if market_type == "forex":
                forex_signals = self.tv.screen_forex(limit=10)
                for pair in forex_signals:
                    if symbol.upper() in str(pair.get("symbol", "")).upper():
                        signals["signals"].append(
                            {"source": "tradingview", "data": pair}
                        )

                        rsi = pair.get("RSI", 50)
                        if rsi < 30:
                            signals["signals"].append(
                                {
                                    "source": "rsi",
                                    "type": "BUY",
                                    "value": rsi,
                                    "reason": f"RSI überverkauft ({rsi})",
                                }
                            )
                        elif rsi > 70:
                            signals["signals"].append(
                                {
                                    "source": "rsi",
                                    "type": "SELL",
                                    "value": rsi,
                                    "reason": f"RSI überkauft ({rsi})",
                                }
                            )

                        change = pair.get("change", 0)
                        if change > 1:
                            signals["signals"].append(
                                {
                                    "source": "momentum",
                                    "type": "BUY",
                                    "value": change,
                                    "reason": f"Starke Aufwärtsbewegung ({change}%)",
                                }
                            )
                        elif change < -1:
                            signals["signals"].append(
                                {
                                    "source": "momentum",
                                    "type": "SELL",
                                    "value": change,
                                    "reason": f"Starke Abwärtsbewegung ({change}%)",
                                }
                            )

            elif market_type == "crypto":
                crypto_signals = self.tv.screen_crypto(limit=20)
                for coin in crypto_signals:
                    if symbol.upper() in str(coin.get("symbol", "")).upper():
                        signals["signals"].append(
                            {"source": "tradingview", "data": coin}
                        )

                        sentiment = self.hive.get_crypto_sentiment(symbol)
                        if sentiment:
                            signals["signals"].append(
                                {"source": "hive_sentiment", "data": sentiment}
                            )

            buy_votes = sum(1 for s in signals["signals"] if s.get("type") == "BUY")
            sell_votes = sum(1 for s in signals["signals"] if s.get("type") == "SELL")

            if buy_votes > sell_votes:
                signals["action"] = "BUY"
                signals["confidence"] = min(
                    buy_votes / (buy_votes + sell_votes + 1) * 100, 100
                )
            elif sell_votes > buy_votes:
                signals["action"] = "SELL"
                signals["confidence"] = min(
                    sell_votes / (buy_votes + sell_votes + 1) * 100, 100
                )

        except Exception as e:
            self.log("ERROR", f"Signal-Generierung fehlgeschlagen: {e}")

        return signals

    def enhance_trading_decision(
        self, symbol: str, current_signal: Dict, market_type: str = "forex"
    ) -> Dict:
        """
        Verbessert eine Trading-Entscheidung mit MCP-Daten

        Args:
            symbol: Handelssymbol
            current_signal: Aktuelles Signal vom Trading-Engine
            market_type: Markt-Typ (forex, crypto, stock)

        Returns:
            Verbessertes Signal mit MCP-Daten
        """
        enhanced = current_signal.copy()
        enhanced["mcp_data"] = self.get_market_data(symbol, market_type)
        enhanced["mcp_signals"] = self.get_trading_signals(symbol, market_type)

        mcp_action = enhanced["mcp_signals"].get("action", "WARTEN")
        mcp_confidence = enhanced["mcp_signals"].get("confidence", 0)

        if mcp_confidence > 50:
            if mcp_action == "BUY" and enhanced.get("action") != "BUY":
                enhanced["mcp_override"] = (
                    f"MCP empfiehlt BUY (Konfidenz: {mcp_confidence}%)"
                )
            elif mcp_action == "SELL" and enhanced.get("action") != "SELL":
                enhanced["mcp_override"] = (
                    f"MCP empfiehlt SELL (Konfidenz: {mcp_confidence}%)"
                )

        return enhanced

    def get_market_sentiment(self, symbol: str = None) -> Dict:
        """Gesamt-Marktstimmung abrufen"""
        sentiment = {"timestamp": datetime.now().isoformat(), "markets": {}}

        try:
            summary = self.hive.get_market_summary()
            sentiment["markets"]["overall"] = summary

            if symbol:
                if "USD" in symbol:
                    forex = self.hive.get_forex_rate(symbol)
                    if forex:
                        sentiment["markets"]["forex"] = forex

                crypto_sent = self.hive.get_crypto_sentiment(symbol)
                if crypto_sent:
                    sentiment["symbol"] = crypto_sent

        except Exception as e:
            self.log("ERROR", f"Sentiment-Abruf fehlgeschlagen: {e}")

        return sentiment


def create_mcp_integration(app, logger=None) -> MCPTradingEngine:
    """Factory-Funktion zur Erstellung der MCP-Integration"""
    return MCPTradingEngine(app, logger)
