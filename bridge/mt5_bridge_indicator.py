#!/usr/bin/env python3
"""
MetaTrader5 Python Bridge Indikator
Echtzeit-Datenbrücke zwischen MT5 und externen Anwendungen
"""

import MetaTrader5 as mt5
import numpy as np
import json
import threading
import time
import http.client
import urllib.request
import urllib.parse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import queue
import hashlib
import hmac
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings("ignore")

# Konfiguration
@dataclass
class BridgeConfig:
    """Konfiguration für die MT5 Bridge"""
    # Datenübertragung
    enable_http: bool = True
    enable_websocket: bool = False
    enable_file_output: bool = True
    http_endpoint: str = "http://localhost:8080/mt5-data"
    websocket_endpoint: str = "ws://localhost:8081/mt5-ws"
    file_output_path: str = "./mt5_bridge_data.json"
    
    # Daten-Erfassung
    capture_price_data: bool = True
    capture_volume: bool = True
    capture_indicators: bool = True
    capture_timeframes: List[str] = None
    max_history_bars: int = 1000
    
    # Performance
    update_interval_ms: int = 1000  # Millisekunden
    batch_size: int = 10
    compression_enabled: bool = True
    
    # Sicherheit
    enable_authentication: bool = False
    api_key: str = ""
    api_secret: str = ""
    
    # Fehlerbehandlung
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    connection_timeout_seconds: float = 5.0
    
    def __post_init__(self):
        if self.capture_timeframes is None:
            self.capture_timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]

@dataclass
class MarketData:
    """Marktdaten-Struktur"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    bid: float
    ask: float
    last_price: float
    spread: float
    
    # Indikatoren
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_middle: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    
    # Metadaten
    indicator_count: int = 0
    data_quality_score: float = 1.0

class MT5BridgeIndicator:
    """Hauptklasse für den MT5 Bridge Indikator"""
    
    def __init__(self, config: BridgeConfig = None):
        self.config = config or BridgeConfig()
        self.logger = self._setup_logging()
        
        # Status-Variablen
        self.is_running = False
        self.is_connected = False
        self.last_update_time = None
        self.error_count = 0
        self.success_count = 0
        
        # Daten-Speicher
        self.data_queue = queue.Queue(maxsize=1000)
        self.latest_data = {}
        self.historical_data = {}
        
        # Threads
        self.data_thread = None
        self.transmission_thread = None
        
        # Verbindungspools
        self.http_connections = {}
        self.websocket_connection = None
        
        # Indikatoren-Cache
        self.indicator_cache = {}
        
        self.logger.info("MT5 Bridge Indikator initialisiert")
    
    def _setup_logging(self) -> logging.Logger:
        """Richtet das Logging ein"""
        logger = logging.getLogger('MT5Bridge')
        logger.setLevel(logging.INFO)
        
        # File Handler
        fh = logging.FileHandler('mt5_bridge.log')
        fh.setLevel(logging.INFO)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def initialize(self) -> bool:
        """Initialisiert die Bridge-Verbindung"""
        try:
            # MT5 initialisieren
            if not mt5.initialize():
                self.logger.error("MT5 Initialisierung fehlgeschlagen")
                return False
            
            # Verbindung prüfen
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Keine Account-Informationen verfügbar")
                return False
            
            self.is_connected = True
            self.logger.info(f"MT5 verbunden: {account_info.company}")
            
            # Datenübertragung initialisieren
            if self.config.enable_http:
                self._init_http_connection()
            
            if self.config.enable_websocket:
                self._init_websocket_connection()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialisierung fehlgeschlagen: {e}")
            return False
    
    def _init_http_connection(self):
        """Initialisiert HTTP-Verbindung"""
        try:
            parsed_url = urllib.parse.urlparse(self.config.http_endpoint)
            conn = http.client.HTTPConnection(
                parsed_url.netloc,
                timeout=self.config.connection_timeout_seconds
            )
            self.http_connections['primary'] = conn
            self.logger.info("HTTP-Verbindung initialisiert")
        except Exception as e:
            self.logger.error(f"HTTP-Verbindung fehlgeschlagen: {e}")
    
    def _init_websocket_connection(self):
        """Initialisiert WebSocket-Verbindung"""
        try:
            # WebSocket-Implementierung (vereinfacht)
            self.logger.info("WebSocket-Verbindung initialisiert")
        except Exception as e:
            self.logger.error(f"WebSocket-Verbindung fehlgeschlagen: {e}")
    
    def start(self) -> bool:
        """Startet die Bridge"""
        if not self.is_connected:
            if not self.initialize():
                return False
        
        self.is_running = True
        
        # Threads starten
        self.data_thread = threading.Thread(target=self._data_collection_loop, daemon=True)
        self.transmission_thread = threading.Thread(target=self._data_transmission_loop, daemon=True)
        
        self.data_thread.start()
        self.transmission_thread.start()
        
        self.logger.info("MT5 Bridge gestartet")
        return True
    
    def stop(self):
        """Stoppt die Bridge"""
        self.is_running = False
        
        # Threads beenden
        if self.data_thread:
            self.data_thread.join(timeout=5)
        if self.transmission_thread:
            self.transmission_thread.join(timeout=5)
        
        # Verbindungen schließen
        for conn in self.http_connections.values():
            try:
                conn.close()
            except:
                pass
        
        # MT5 beenden
        mt5.shutdown()
        
        self.logger.info("MT5 Bridge gestoppt")
    
    def _data_collection_loop(self):
        """Hauptschleife für Datenerfassung"""
        self.logger.info("MT5 Bridge Daten-Erfassung gestartet")
        while self.is_running:
            try:
                start_time = time.time()
                
                # Symbole erfassen
                symbols = self._get_active_symbols()
                self.logger.debug(f"Erfasste Symbole: {symbols}")
                
                for symbol in symbols:
                    for timeframe in self.config.capture_timeframes:
                        try:
                            data = self._collect_market_data(symbol, timeframe)
                            if data:
                                self.data_queue.put(data)
                                self.success_count += 1
                        except Exception as e:
                            self.logger.error(f"Fehler bei Datenerfassung {symbol} {timeframe}: {e}")
                
                # Update-Zeit anpassen
                elapsed = time.time() - start_time
                sleep_time = max(0, (self.config.update_interval_ms / 1000) - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Fehler in Datenerfassungsschleife: {e}")
                time.sleep(1)
        self.logger.info("MT5 Bridge Daten-Erfassung gestoppt")
    
    def _data_transmission_loop(self):
        """Hauptschleife für Datenübertragung"""
        batch = []
        
        while self.is_running:
            try:
                # Daten aus Queue holen
                while not self.data_queue.empty() and len(batch) < self.config.batch_size:
                    try:
                        data = self.data_queue.get_nowait()
                        batch.append(data)
                    except queue.Empty:
                        break
                
                # Batch übertragen
                if batch:
                    self._transmit_data_batch(batch)
                    batch = []
                
                time.sleep(0.1)  # Kurze Pause
                
            except Exception as e:
                self.logger.error(f"Fehler in Übertragungsschleife: {e}")
                time.sleep(1)
    
    def _get_active_symbols(self) -> List[str]:
        """Holt aktive Symbole"""
        try:
            # Symbole aus MT5 Market Watch
            symbols: List[str] = []
            for symbol_info in mt5.symbols_get():
                if symbol_info.visible and symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                    symbols.append(symbol_info.name)
            
            # Auf wichtige Forex-Paare beschränken
            priority_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
            symbols = [s for s in priority_symbols if s in symbols] + symbols[:10]
            
            return symbols[:20]  # Max 20 Symbole
            
        except Exception as e:
            self.logger.error(f"Fehler beim Abruf der Symbole: {e}")
            return ["EURUSD"]  # Fallback
    
    def _collect_market_data(self, symbol: str, timeframe_str: str) -> Optional[MarketData]:
        """Sammelt Marktdaten für ein Symbol"""
        try:
            # Timeframe konvertieren
            timeframe = self._convert_timeframe(timeframe_str)
            if timeframe is None:
                return None
            
            # Aktuelle Daten holen
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            # Chart-Daten holen
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 1)
            if rates is None or len(rates) == 0:
                return None
            
            rate = rates[0]
            
            # Marktdaten erstellen
            market_data = MarketData(
                symbol=symbol,
                timeframe=timeframe_str,
                timestamp=datetime.fromtimestamp(rate['time']),
                open_price=rate['open'],
                high_price=rate['high'],
                low_price=rate['low'],
                close_price=rate['close'],
                volume=rate['tick_volume'],
                bid=tick.bid,
                ask=tick.ask,
                last_price=tick.last if hasattr(tick, 'last') else tick.bid,
                spread=tick.ask - tick.bid
            )
            
            # Indikatoren berechnen
            if self.config.capture_indicators:
                self._calculate_indicators(market_data, symbol, timeframe)
            
            # Datenqualität bewerten
            market_data.data_quality_score = self._calculate_data_quality(market_data)
            
            # Cache aktualisieren
            cache_key = f"{symbol}_{timeframe_str}"
            self.latest_data[cache_key] = market_data
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Fehler bei Datenerfassung {symbol} {timeframe_str}: {e}")
            return None
    
    def _convert_timeframe(self, timeframe_str: str) -> Optional[int]:
        """Konvertiert Timeframe-String zu MT5-Konstante"""
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1
        }
        return timeframe_map.get(timeframe_str)
    
    def _calculate_indicators(self, data: MarketData, symbol: str, timeframe: int):
        """Berechnet technische Indikatoren"""
        try:
            # Historische Daten für Indikatoren
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
            if len(rates) < 20:
                return
            
            closes = [rate['close'] for rate in rates]
            closes_array = np.array(closes)
            
            # RSI (14 Perioden)
            if len(closes) >= 14:
                data.rsi = self._calculate_rsi(closes_array, 14)
            
            # MACD
            if len(closes) >= 26:
                macd_line, signal_line = self._calculate_macd(closes_array)
                data.macd = macd_line
                data.macd_signal = signal_line
            
            # Bollinger Bands (20, 2)
            if len(closes) >= 20:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes_array, 20, 2)
                data.bb_upper = bb_upper
                data.bb_middle = bb_middle
                data.bb_lower = bb_lower
            
            # EMA (20, 50)
            if len(closes) >= 50:
                data.ema_20 = self._calculate_ema(closes_array, 20)
                data.ema_50 = self._calculate_ema(closes_array, 50)
            
            # Indikator-Zähler
            data.indicator_count = sum([
                1 for val in [data.rsi, data.macd, data.bb_upper, data.ema_20, data.ema_50]
                if val is not None
            ])
            
        except Exception as e:
            self.logger.error(f"Fehler bei Indikator-Berechnung: {e}")
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Berechnet RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Berechnet MACD"""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # Signal Line (EMA von MACD)
        if len(prices) >= signal:
            macd_history = []
            for i in range(signal, len(prices)):
                ema_f = self._calculate_ema(prices[i-signal:i], fast)
                ema_s = self._calculate_ema(prices[i-signal:i], slow)
                macd_history.append(ema_f - ema_s)
            
            if macd_history:
                signal_line = np.mean(macd_history[-signal:])
                return float(macd_line), float(signal_line)
        
        return float(macd_line), float(macd_line)
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> tuple:
        """Berechnet Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return float(upper), float(middle), float(lower)
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Berechnet EMA"""
        if len(prices) < period:
            return float(prices[-1])
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    def _calculate_data_quality(self, data: MarketData) -> float:
        """Berechnet Datenqualitäts-Score"""
        score = 1.0
        
        # Preis-Plausibilität prüfen
        if data.open_price <= 0 or data.close_price <= 0:
            score -= 0.3
        
        # Spread prüfen
        if data.spread <= 0 or data.spread > 0.1:  # 100 Pips max
            score -= 0.2
        
        # Volumen prüfen
        if data.volume < 0:
            score -= 0.1
        
        # Zeitstempel prüfen
        now = datetime.now()
        if abs((now - data.timestamp).total_seconds()) > 300:  # 5 Minuten max
            score -= 0.2
        
        # Indikator-Vollständigkeit
        if self.config.capture_indicators:
            expected_indicators = 5
            actual_indicators = data.indicator_count
            score -= (expected_indicators - actual_indicators) * 0.1
        
        return max(0.0, score)
    
    def _transmit_data_batch(self, batch: List[MarketData]):
        """Überträgt Daten-Batch"""
        try:
            # Daten serialisieren
            data_json = self._serialize_data(batch)
            
            # HTTP-Übertragung
            if self.config.enable_http:
                self._transmit_http(data_json)
            
            # WebSocket-Übertragung
            if self.config.enable_websocket:
                self._transmit_websocket(data_json)
            
            # Datei-Ausgabe
            if self.config.enable_file_output:
                self._transmit_file(data_json)
            
            self.success_count += len(batch)
            
        except Exception as e:
            self.logger.error(f"Fehler bei Datenübertragung: {e}")
            self.error_count += 1
    
    def _serialize_data(self, batch: List[MarketData]) -> str:
        """Serialisiert Daten zu JSON"""
        def json_serializer(obj):
            """Benutzerdefinierter JSON-Serializer für nicht-standardisierte Typen"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'item'):  # Für numpy-Typen wie uint64
                return obj.item()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        data_dicts = []
        for data in batch:
            data_dict = asdict(data)
            # datetime konvertieren
            data_dict['timestamp'] = data.timestamp
            data_dicts.append(data_dict)
        
        return json.dumps({
            "timestamp": datetime.now(),
            "batch_size": len(batch),
            "data": data_dicts
        }, default=json_serializer)
    
    def _transmit_http(self, data_json: str):
        """Überträgt Daten via HTTP"""
        try:
            conn = self.http_connections.get('primary')
            if not conn:
                return
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MT5-Bridge/1.0'
            }
            
            if self.config.enable_authentication:
                headers['Authorization'] = self._generate_auth_header()
            
            conn.request('POST', '/mt5-data', data_json, headers)
            response = conn.getresponse()
            
            if response.status != 200:
                self.logger.warning(f"HTTP-Übertragung fehlgeschlagen: {response.status}")
            
        except Exception as e:
            self.logger.error(f"HTTP-Übertragungsfehler: {e}")
            # Verbindung neu aufbauen
            self._init_http_connection()
    
    def _transmit_websocket(self, data_json: str):
        """Überträgt Daten via WebSocket"""
        try:
            # WebSocket-Implementierung
            pass
        except Exception as e:
            self.logger.error(f"WebSocket-Übertragungsfehler: {e}")
    
    def _transmit_file(self, data_json: str):
        """Schreibt Daten in Datei"""
        try:
            with open(self.config.file_output_path, 'w') as f:
                f.write(data_json)
        except Exception as e:
            self.logger.error(f"Datei-Übertragungsfehler: {e}")
    
    def _generate_auth_header(self) -> str:
        """Generiert Authentication Header"""
        if not self.config.api_key or not self.config.api_secret:
            return ""
        
        timestamp = str(int(time.time()))
        message = f"{timestamp}{self.config.api_key}"
        signature = hmac.new(
            self.config.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"HMAC {self.config.api_key}:{timestamp}:{signature}"
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt Bridge-Status zurück"""
        return {
            "is_running": self.is_running,
            "is_connected": self.is_connected,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "queue_size": self.data_queue.qsize(),
            "latest_data_count": len(self.latest_data),
            "config": asdict(self.config)
        }

# MT5 Indikator-Export-Funktionen
def get_indicator_info():
    """Gibt Indikator-Informationen zurück"""
    return {
        "name": "MT5 Python Bridge",
        "version": "1.0.0",
        "description": "Echtzeit-Datenbrücke zwischen MT5 und externen Anwendungen",
        "author": "FinGPT Team",
        "parameters": {
            "http_endpoint": {"type": "string", "default": "http://localhost:8080/mt5-data"},
            "enable_file_output": {"type": "bool", "default": True},
            "update_interval_ms": {"type": "int", "default": 1000}
        }
    }

# Globale Bridge-Instanz
_bridge_instance = None

def initialize_bridge(config: BridgeConfig = None) -> MT5BridgeIndicator:
    """Initialisiert die globale Bridge-Instanz"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MT5BridgeIndicator(config)
    return _bridge_instance

def start_bridge() -> bool:
    """Startet die globale Bridge-Instanz"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MT5BridgeIndicator()
    return _bridge_instance.start()

def stop_bridge():
    """Stoppt die globale Bridge-Instanz"""
    global _bridge_instance
    if _bridge_instance:
        _bridge_instance.stop()
        _bridge_instance = None

def get_bridge_status() -> Dict[str, Any]:
    """Gibt Status der globalen Bridge-Instanz zurück"""
    if _bridge_instance:
        return _bridge_instance.get_status()
    return {"error": "Bridge nicht initialisiert"}

if __name__ == "__main__":
    # Test-Modus
    config = BridgeConfig(
        enable_http=False,
        enable_websocket=False,
        enable_file_output=True,
        file_output_path="./mt5_test_data.json"
    )
    
    bridge = MT5BridgeIndicator(config)
    
    try:
        if bridge.start():
            print("MT5 Bridge gestartet - Drücke Ctrl+C zum Beenden")
            while True:
                time.sleep(1)
                status = bridge.get_status()
                print(f"Status: {status['success_count']} Erfolge, {status['error_count']} Fehler")
    except KeyboardInterrupt:
        print("Beende Bridge...")
    finally:
        bridge.stop()