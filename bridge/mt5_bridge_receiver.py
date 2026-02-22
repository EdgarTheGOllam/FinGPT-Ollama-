#!/usr/bin/env python3
"""
MT5 Bridge Data Receiver
Empfängt und verarbeitet Daten vom MT5 Bridge Indikator
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
import queue
import sqlite3
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

class MT5BridgeReceiver:
    """Empfängt und verarbeitet MT5 Bridge Daten"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Daten-Speicher
        self.data_queue = queue.Queue(maxsize=10000)
        self.latest_data = {}
        self.historical_data = []
        
        # Datenbank
        self.db_connection = None
        self.db_initialized = False
        
        # Callbacks
        self.data_callbacks = []
        
        # Flask App
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'mt5-bridge-secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # WebSocket-Clients
        self.websocket_clients = set()
        
        # Statistiken
        self.stats = {
            'total_received': 0,
            'total_processed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        self._setup_routes()
        self._setup_socketio_events()
        
    def _setup_logging(self) -> logging.Logger:
        """Richtet Logging ein"""
        logger = logging.getLogger('MT5BridgeReceiver')
        logger.setLevel(logging.INFO)
        
        # File Handler
        fh = logging.FileHandler('mt5_bridge_receiver.log')
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
    
    def _setup_routes(self):
        """Richtet Flask-Routes ein"""
        
        @self.app.route('/mt5-data', methods=['POST'])
        def receive_data():
            """Empängt Daten via HTTP POST"""
            try:
                data = request.get_json()
                if data:
                    self._process_data_batch(data)
                    return jsonify({"status": "success", "received": len(data.get('data', []))})
                else:
                    return jsonify({"status": "error", "message": "No data received"}), 400
            except Exception as e:
                self.logger.error(f"Fehler bei HTTP-Datenempfang: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Gibt Receiver-Status zurück"""
            return jsonify(self.get_status())
        
        @self.app.route('/latest-data', methods=['GET'])
        def get_latest_data():
            """Gibt letzte Daten zurück"""
            symbol = request.args.get('symbol')
            timeframe = request.args.get('timeframe')
            
            if symbol and timeframe:
                key = f"{symbol}_{timeframe}"
                data = self.latest_data.get(key)
                return jsonify(data) if data else jsonify({"error": "No data found"})
            else:
                return jsonify(self.latest_data)
        
        @self.app.route('/history', methods=['GET'])
        def get_history():
            """Gibt historische Daten zurück"""
            limit = int(request.args.get('limit', 100))
            symbol = request.args.get('symbol')
            
            if symbol:
                # Aus Datenbank abrufen
                data = self._get_historical_data(symbol, limit)
                return jsonify(data)
            else:
                return jsonify(self.historical_data[-limit:])
    
    def _setup_socketio_events(self):
        """Richtet SocketIO-Events ein"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Neuer Client verbunden"""
            self.websocket_clients.add(request.sid)
            self.logger.info(f"WebSocket Client verbunden: {request.sid}")
            emit('status', {'message': 'Connected to MT5 Bridge Receiver'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Client getrennt"""
            self.websocket_clients.discard(request.sid)
            self.logger.info(f"WebSocket Client getrennt: {request.sid}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Client abonniert Daten"""
            symbol = data.get('symbol')
            timeframe = data.get('timeframe')
            
            # Aktuelle Daten senden
            key = f"{symbol}_{timeframe}"
            latest = self.latest_data.get(key)
            if latest:
                emit('data', latest)
    
    def initialize_database(self, db_path: str = 'mt5_bridge_data.db'):
        """Initialisiert die Datenbank"""
        try:
            self.db_connection = sqlite3.connect(db_path, check_same_thread=False)
            cursor = self.db_connection.cursor()
            
            # Tabelle erstellen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume INTEGER,
                    bid REAL,
                    ask REAL,
                    spread REAL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    bb_upper REAL,
                    bb_lower REAL,
                    bb_middle REAL,
                    ema_20 REAL,
                    ema_50 REAL,
                    indicator_count INTEGER,
                    data_quality_score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Indizes erstellen
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON market_data(symbol, timeframe)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON market_data(timestamp)')
            
            self.db_connection.commit()
            self.db_initialized = True
            
            self.logger.info("Datenbank initialisiert")
            
        except Exception as e:
            self.logger.error(f"Datenbank-Initialisierung fehlgeschlagen: {e}")
    
    def _process_data_batch(self, batch_data: Dict[str, Any]):
        """Verarbeitet Daten-Batch"""
        try:
            data_list = batch_data.get('data', [])
            
            for data_dict in data_list:
                # Daten verarbeiten
                processed_data = self._process_single_data(data_dict)
                
                if processed_data:
                    # In Queue speichern
                    self.data_queue.put(processed_data)
                    
                    # Latest-Data aktualisieren
                    key = f"{processed_data['symbol']}_{processed_data['timeframe']}"
                    self.latest_data[key] = processed_data
                    
                    # In Datenbank speichern
                    if self.db_initialized:
                        self._save_to_database(processed_data)
                    
                    # WebSocket-Clients benachrichtigen
                    self._notify_websocket_clients(processed_data)
                    
                    # Callbacks aufrufen
                    self._call_data_callbacks(processed_data)
            
            self.stats['total_received'] += len(data_list)
            self.stats['total_processed'] += len(data_list)
            
        except Exception as e:
            self.logger.error(f"Fehler bei Batch-Verarbeitung: {e}")
            self.stats['errors'] += 1
    
    def _process_single_data(self, data_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verarbeitet einzelne Daten"""
        try:
            # Timestamp konvertieren
            if isinstance(data_dict.get('timestamp'), str):
                data_dict['timestamp'] = datetime.fromisoformat(data_dict['timestamp'].replace('Z', '+00:00'))
            
            # Daten validieren
            if not self._validate_data(data_dict):
                return None
            
            return data_dict
            
        except Exception as e:
            self.logger.error(f"Fehler bei Datenverarbeitung: {e}")
            return None
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validiert Daten"""
        required_fields = ['symbol', 'timeframe', 'timestamp', 'open_price', 'high_price', 'low_price', 'close_price']
        
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        
        # Preis-Plausibilität prüfen
        prices = [data['open_price'], data['high_price'], data['low_price'], data['close_price']]
        if any(p <= 0 for p in prices):
            return False
        
        # High/Low Konsistenz prüfen
        if data['high_price'] < data['low_price']:
            return False
        
        return True
    
    def _save_to_database(self, data: Dict[str, Any]):
        """Speichert Daten in Datenbank"""
        try:
            cursor = self.db_connection.cursor()
            
            cursor.execute('''
                INSERT INTO market_data (
                    symbol, timeframe, timestamp, open_price, high_price, low_price, close_price,
                    volume, bid, ask, spread, rsi, macd, macd_signal, bb_upper, bb_lower, bb_middle,
                    ema_20, ema_50, indicator_count, data_quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['symbol'], data['timeframe'], data['timestamp'],
                data['open_price'], data['high_price'], data['low_price'], data['close_price'],
                data.get('volume'), data.get('bid'), data.get('ask'), data.get('spread'),
                data.get('rsi'), data.get('macd'), data.get('macd_signal'),
                data.get('bb_upper'), data.get('bb_lower'), data.get('bb_middle'),
                data.get('ema_20'), data.get('ema_50'),
                data.get('indicator_count'), data.get('data_quality_score')
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Fehler bei Datenbank-Speicherung: {e}")
    
    def _notify_websocket_clients(self, data: Dict[str, Any]):
        """Benachrichtigt WebSocket-Clients"""
        try:
            self.socketio.emit('data', data, room='*')
        except Exception as e:
            self.logger.error(f"Fehler bei WebSocket-Benachrichtigung: {e}")
    
    def _call_data_callbacks(self, data: Dict[str, Any]):
        """Ruft registrierte Callbacks auf"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Fehler in Data-Callback: {e}")
    
    def _get_historical_data(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Holt historische Daten aus Datenbank"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                SELECT * FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (symbol, limit))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            data = []
            for row in rows:
                data_dict = dict(zip(columns, row))
                # datetime konvertieren
                if isinstance(data_dict['timestamp'], str):
                    data_dict['timestamp'] = datetime.fromisoformat(data_dict['timestamp'])
                data.append(data_dict)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Fehler beim Abruf historischer Daten: {e}")
            return []
    
    def add_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Fügt Data-Callback hinzu"""
        self.data_callbacks.append(callback)
    
    def get_latest_data(self, symbol: str = None, timeframe: str = None) -> Dict[str, Any]:
        """Holt letzte Daten"""
        if symbol and timeframe:
            key = f"{symbol}_{timeframe}"
            return self.latest_data.get(key)
        return self.latest_data
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt Receiver-Status zurück"""
        uptime = datetime.now() - self.stats['start_time']
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'total_received': self.stats['total_received'],
            'total_processed': self.stats['total_processed'],
            'errors': self.stats['errors'],
            'queue_size': self.data_queue.qsize(),
            'latest_data_count': len(self.latest_data),
            'websocket_clients': len(self.websocket_clients),
            'database_initialized': self.db_initialized
        }
    
    def start(self, host: str = '0.0.0.0', port: int = 8080, debug: bool = False):
        """Startet den Receiver"""
        self.logger.info(f"Starte MT5 Bridge Receiver auf {host}:{port}")
        
        # Datenbank initialisieren
        self.initialize_database()
        
        # Flask-App starten
        self.socketio.run(self.app, host=host, port=port, debug=debug)

class MT5BridgeClient:
    """Client für den Zugriff auf MT5 Bridge Daten"""
    
    def __init__(self, receiver_url: str = 'http://localhost:8080'):
        self.receiver_url = receiver_url
        self.logger = logging.getLogger('MT5BridgeClient')
    
    def get_latest_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Holt letzte Daten für Symbol/Timeframe"""
        try:
            import requests
            
            response = requests.get(
                f"{self.receiver_url}/latest-data",
                params={'symbol': symbol, 'timeframe': timeframe},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Fehler beim Abruf: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Fehler bei Client-Anfrage: {e}")
            return None
    
    def get_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Holt historische Daten"""
        try:
            import requests
            
            response = requests.get(
                f"{self.receiver_url}/history",
                params={'symbol': symbol, 'limit': limit},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Fehler beim History-Abruf: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Fehler bei History-Anfrage: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Holt Receiver-Status"""
        try:
            import requests
            
            response = requests.get(f"{self.receiver_url}/status", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Fehler bei Status-Anfrage: {e}")
            return {}

if __name__ == "__main__":
    # Receiver starten
    receiver = MT5BridgeReceiver()
    
    # Data-Callback Beispiel
    def data_callback(data):
        print(f"Neue Daten: {data['symbol']} {data['timeframe']} @ {data['timestamp']}")
    
    receiver.add_data_callback(data_callback)
    
    # Starten
    receiver.start(host='0.0.0.0', port=8080)