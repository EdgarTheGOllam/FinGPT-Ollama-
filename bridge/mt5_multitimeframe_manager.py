#!/usr/bin/env python3
"""
MT5 Bridge Multi-Timeframe Manager
Verwaltet Multi-Timeframe-Daten und Synchronisation
"""

import MetaTrader5 as mt5
import numpy as np
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict

class Timeframe(Enum):
    """MT5 Timeframes"""
    M1 = ("M1", mt5.TIMEFRAME_M1, 60)
    M5 = ("M5", mt5.TIMEFRAME_M5, 300)
    M15 = ("M15", mt5.TIMEFRAME_M15, 900)
    M30 = ("M30", mt5.TIMEFRAME_M30, 1800)
    H1 = ("H1", mt5.TIMEFRAME_H1, 3600)
    H4 = ("H4", mt5.TIMEFRAME_H4, 14400)
    D1 = ("D1", mt5.TIMEFRAME_D1, 86400)
    W1 = ("W1", mt5.TIMEFRAME_W1, 604800)
    MN1 = ("MN1", mt5.TIMEFRAME_MN1, 2592000)
    
    def __init__(self, name: str, mt5_constant: int, seconds: int):
        self.name = name
        self.mt5_constant = mt5_constant
        self.seconds = seconds

@dataclass
class TimeframeData:
    """Timeframe-spezifische Daten"""
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    bid: float
    ask: float
    spread: float
    
    # Indikatoren für diesen Timeframe
    indicators: Dict[str, float] = None
    
    # Synchronisations-Info
    is_synchronized: bool = False
    sync_timestamp: Optional[datetime] = None
    data_quality: float = 1.0
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}

@dataclass
class SynchronizedData:
    """Synchronisierte Multi-Timeframe-Daten"""
    symbol: str
    master_timestamp: datetime
    timeframes: Dict[str, TimeframeData]
    sync_quality: float
    lag_analysis: Dict[str, float] = None
    
    def __post_init__(self):
        if self.lag_analysis is None:
            self.lag_analysis = {}

class MT5MultiTimeframeManager:
    """Verwaltet Multi-Timeframe-Daten"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Timeframe-Konfiguration
        self.active_timeframes = [
            Timeframe.M1, Timeframe.M5, Timeframe.M15, 
            Timeframe.H1, Timeframe.H4, Timeframe.D1
        ]
        
        # Daten-Speicher
        self.timeframe_data: Dict[str, Dict[str, TimeframeData]] = defaultdict(dict)
        self.synchronized_data: Dict[str, SynchronizedData] = {}
        
        # Synchronisations-Parameter
        self.sync_tolerance_seconds = 30  # Maximal erlaubte Zeitdifferenz
        self.min_sync_quality = 0.7  # Mindest-Sync-Qualität
        
        # Performance-Optimierung
        self.data_cache: Dict[str, Dict[str, List[TimeframeData]]] = defaultdict(lambda: defaultdict(list))
        self.cache_size = 1000
        
        # Threads
        self.sync_thread = None
        self.collection_threads: Dict[str, threading.Thread] = {}
        self.is_running = False
        
        # Statistiken
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'avg_sync_time': 0.0,
            'data_points_collected': 0,
            'last_sync_time': None
        }
        
        # Callbacks
        self.sync_callbacks: List[Callable[[SynchronizedData], None]] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Richtet Logging ein"""
        logger = logging.getLogger('MT5MultiTimeframe')
        logger.setLevel(logging.INFO)
        
        # File Handler
        fh = logging.FileHandler('mt5_multitimeframe.log')
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
    
    def start(self, symbols: List[str]):
        """Startet Multi-Timeframe-Manager"""
        self.is_running = True
        
        # Collection-Threads für jedes Symbol starten
        for symbol in symbols:
            thread = threading.Thread(
                target=self._symbol_collection_loop,
                args=(symbol,),
                daemon=True,
                name=f"MTF_Collector_{symbol}"
            )
            thread.start()
            self.collection_threads[symbol] = thread
        
        # Synchronisations-Thread starten
        self.sync_thread = threading.Thread(
            target=self._synchronization_loop,
            daemon=True,
            name="MTF_Synchronizer"
        )
        self.sync_thread.start()
        
        self.logger.info(f"Multi-Timeframe Manager gestartet für {len(symbols)} Symbole")
    
    def stop(self):
        """Stoppt Multi-Timeframe-Manager"""
        self.is_running = False
        
        # Threads beenden
        for thread in self.collection_threads.values():
            thread.join(timeout=5)
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        self.logger.info("Multi-Timeframe Manager gestoppt")
    
    def _symbol_collection_loop(self, symbol: str):
        """Collection-Schleife für ein Symbol"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Daten für alle Timeframes sammeln
                for timeframe in self.active_timeframes:
                    try:
                        data = self._collect_timeframe_data(symbol, timeframe)
                        if data:
                            self._store_timeframe_data(symbol, timeframe, data)
                            self.stats['data_points_collected'] += 1
                    except Exception as e:
                        self.logger.error(f"Fehler bei Datenerfassung {symbol} {timeframe.name}: {e}")
                
                # Update-Zeit anpassen
                elapsed = time.time() - start_time
                sleep_time = max(0, 1.0 - elapsed)  # Mindestens 1 Sekunde zwischen Updates
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Fehler in Collection-Schleife für {symbol}: {e}")
                time.sleep(5)
    
    def _collect_timeframe_data(self, symbol: str, timeframe: Timeframe) -> Optional[TimeframeData]:
        """Sammelt Daten für einen spezifischen Timeframe"""
        try:
            # Aktuelle Tick-Daten holen
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            # Chart-Daten holen
            rates = mt5.copy_rates_from_pos(symbol, timeframe.mt5_constant, 0, 1)
            if rates is None or len(rates) == 0:
                return None
            
            rate = rates[0]
            
            # Timeframe-Daten erstellen
            data = TimeframeData(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(rate['time']),
                open_price=rate['open'],
                high_price=rate['high'],
                low_price=rate['low'],
                close_price=rate['close'],
                volume=rate['tick_volume'],
                bid=tick.bid,
                ask=tick.ask,
                spread=tick.ask - tick.bid
            )
            
            # Indikatoren berechnen
            data.indicators = self._calculate_timeframe_indicators(symbol, timeframe)
            
            # Datenqualität bewerten
            data.data_quality = self._assess_data_quality(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Fehler bei Datenerfassung {symbol} {timeframe.name}: {e}")
            return None
    
    def _calculate_timeframe_indicators(self, symbol: str, timeframe: Timeframe) -> Dict[str, float]:
        """Berechnet Indikatoren für spezifischen Timeframe"""
        indicators = {}
        
        try:
            # Historische Daten für Indikatoren
            periods = min(200, max(50, timeframe.seconds // 60))  # Dynamische Perioden
            rates = mt5.copy_rates_from_pos(symbol, timeframe.mt5_constant, 0, periods)
            
            if len(rates) < 20:
                return indicators
            
            closes = [rate['close'] for rate in rates]
            closes_array = np.array(closes)
            
            # RSI (angepasste Perioden)
            rsi_period = min(14, len(closes) // 4)
            if rsi_period >= 7:
                indicators['rsi'] = self._calculate_rsi(closes_array, rsi_period)
            
            # EMA (angepasste Perioden)
            ema_short = min(20, len(closes) // 10)
            ema_long = min(50, len(closes) // 4)
            
            if ema_short >= 5:
                indicators['ema_short'] = self._calculate_ema(closes_array, ema_short)
            if ema_long >= 10:
                indicators['ema_long'] = self._calculate_ema(closes_array, ema_long)
            
            # Bollinger Bands
            bb_period = min(20, len(closes) // 5)
            if bb_period >= 10:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes_array, bb_period, 2)
                indicators['bb_upper'] = bb_upper
                indicators['bb_middle'] = bb_middle
                indicators['bb_lower'] = bb_lower
            
            # MACD (für höhere Timeframes)
            if timeframe.seconds >= 300:  # M5 und höher
                if len(closes) >= 26:
                    macd_line, signal_line = self._calculate_macd(closes_array)
                    indicators['macd'] = macd_line
                    indicators['macd_signal'] = signal_line
            
            # Volume Indicators
            if len(rates) >= 20:
                volumes = [rate['tick_volume'] for rate in rates]
                indicators['volume_sma'] = np.mean(volumes[-20:])
            
            # Volatilität
            if len(closes) >= 20:
                returns = np.diff(closes[-20:]) / closes[-20:-1]
                indicators['volatility'] = np.std(returns) * 100
            
        except Exception as e:
            self.logger.error(f"Fehler bei Indikator-Berechnung {symbol} {timeframe.name}: {e}")
        
        return indicators
    
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
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Berechnet EMA"""
        if len(prices) < period:
            return float(prices[-1])
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> Tuple[float, float, float]:
        """Berechnet Bollinger Bands"""
        if len(prices) < period:
            latest = prices[-1]
            return latest, latest, latest
        
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return float(upper), float(middle), float(lower)
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
        """Berechnet MACD"""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # Signal Line (vereinfacht)
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
    
    def _assess_data_quality(self, data: TimeframeData) -> float:
        """Bewertet Datenqualität"""
        quality = 1.0
        
        # Preis-Plausibilität
        if data.open_price <= 0 or data.close_price <= 0:
            quality -= 0.3
        
        # Spread-Plausibilität
        if data.spread <= 0 or data.spread > 0.05:  # 50 Pips max
            quality -= 0.2
        
        # Volumen-Plausibilität
        if data.volume < 0:
            quality -= 0.1
        
        # Zeitstempel-Plausibilität
        now = datetime.now()
        age_seconds = (now - data.timestamp).total_seconds()
        max_age = data.timeframe.seconds * 2  # Max 2 Timeframe-Perioden alt
        
        if age_seconds > max_age:
            quality -= 0.3
        
        # Indikator-Vollständigkeit
        if data.indicators:
            expected_indicators = 5  # Mindestanzahl erwarteter Indikatoren
            actual_indicators = len(data.indicators)
            indicator_quality = min(1.0, actual_indicators / expected_indicators)
            quality = quality * 0.7 + indicator_quality * 0.3
        
        return max(0.0, quality)
    
    def _store_timeframe_data(self, symbol: str, timeframe: Timeframe, data: TimeframeData):
        """Speichert Timeframe-Daten"""
        
        # In aktuellen Speicher
        self.timeframe_data[symbol][timeframe.name] = data
        
        # In Cache
        cache_key = f"{symbol}_{timeframe.name}"
        self.data_cache[cache_key][timeframe.name].append(data)
        
        # Cache-Größe begrenzen
        if len(self.data_cache[cache_key][timeframe.name]) > self.cache_size:
            self.data_cache[cache_key][timeframe.name] = self.data_cache[cache_key][timeframe.name][-self.cache_size:]
    
    def _synchronization_loop(self):
        """Synchronisationsschleife"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Alle Symbole synchronisieren
                for symbol in list(self.timeframe_data.keys()):
                    if self.timeframe_data[symbol]:
                        self._synchronize_symbol_data(symbol)
                
                # Update-Zeit anpassen
                elapsed = time.time() - start_time
                sleep_time = max(0, 5.0 - elapsed)  # Alle 5 Sekunden synchronisieren
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Fehler in Synchronisationsschleife: {e}")
                time.sleep(5)
    
    def _synchronize_symbol_data(self, symbol: str):
        """Synchronisiert Daten für ein Symbol"""
        try:
            symbol_data = self.timeframe_data[symbol]
            if not symbol_data:
                return
            
            # Master-Timeframe auswählen (höchste Auflösung mit gültigen Daten)
            master_timeframe = self._select_master_timeframe(symbol_data)
            if not master_timeframe:
                return
            
            master_data = symbol_data[master_timeframe]
            
            # Synchronisierte Daten erstellen
            synced_data = SynchronizedData(
                symbol=symbol,
                master_timestamp=master_data.timestamp,
                timeframes={},
                sync_quality=0.0
            )
            
            # Alle Timeframes synchronisieren
            total_quality = 0.0
            valid_timeframes = 0
            
            for tf_name, tf_data in symbol_data.items():
                if tf_data and tf_data.data_quality > 0.5:
                    # Zeitdifferenz berechnen
                    time_diff = abs((master_data.timestamp - tf_data.timestamp).total_seconds())
                    
                    # Synchronisations-Qualität berechnen
                    sync_quality = self._calculate_sync_quality(master_data, tf_data, time_diff)
                    
                    if sync_quality >= self.min_sync_quality:
                        tf_data.is_synchronized = True
                        tf_data.sync_timestamp = datetime.now()
                        synced_data.timeframes[tf_name] = tf_data
                        synced_data.lag_analysis[tf_name] = time_diff
                        
                        total_quality += sync_quality
                        valid_timeframes += 1
            
            # Gesamtsync-Qualität berechnen
            if valid_timeframes > 0:
                synced_data.sync_quality = total_quality / valid_timeframes
                
                # Speichern
                self.synchronized_data[symbol] = synced_data
                
                # Statistiken aktualisieren
                self.stats['total_syncs'] += 1
                if synced_data.sync_quality >= self.min_sync_quality:
                    self.stats['successful_syncs'] += 1
                else:
                    self.stats['failed_syncs'] += 1
                
                self.stats['last_sync_time'] = datetime.now()
                
                # Callbacks aufrufen
                self._call_sync_callbacks(synced_data)
                
        except Exception as e:
            self.logger.error(f"Fehler bei Symbol-Synchronisation {symbol}: {e}")
    
    def _select_master_timeframe(self, symbol_data: Dict[str, TimeframeData]) -> Optional[str]:
        """Wählt Master-Timeframe aus"""
        # Bevorzuge M1, falls verfügbar und gut
        priority = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
        
        for tf_name in priority:
            if tf_name in symbol_data:
                tf_data = symbol_data[tf_name]
                if tf_data and tf_data.data_quality > 0.7:
                    return tf_name
        
        # Fallback: beliebiger Timeframe mit guter Qualität
        for tf_name, tf_data in symbol_data.items():
            if tf_data and tf_data.data_quality > 0.5:
                return tf_name
        
        return None
    
    def _calculate_sync_quality(self, master_data: TimeframeData, tf_data: TimeframeData, time_diff: float) -> float:
        """Berechnet Synchronisations-Qualität"""
        quality = 1.0
        
        # Zeitdifferenz berücksichtigen
        max_allowed_diff = self.sync_tolerance_seconds
        if time_diff > max_allowed_diff:
            quality -= (time_diff - max_allowed_diff) / max_allowed_diff
        
        # Datenqualität beider Timeframes
        quality *= (master_data.data_quality + tf_data.data_quality) / 2
        
        # Timeframe-spezifische Toleranzen
        if tf_data.timeframe.seconds > master_data.timeframe.seconds:
            # Höhere Timeframes haben natürliche Verzögerungen
            tolerance_factor = min(2.0, tf_data.timeframe.seconds / master_data.timeframe.seconds)
            quality = min(1.0, quality + (1.0 - quality) * (tolerance_factor - 1.0) / tolerance_factor)
        
        return max(0.0, quality)
    
    def _call_sync_callbacks(self, synced_data: SynchronizedData):
        """Ruft Synchronisations-Callbacks auf"""
        for callback in self.sync_callbacks:
            try:
                callback(synced_data)
            except Exception as e:
                self.logger.error(f"Fehler in Sync-Callback: {e}")
    
    def get_synchronized_data(self, symbol: str) -> Optional[SynchronizedData]:
        """Gibt synchronisierte Daten für Symbol zurück"""
        return self.synchronized_data.get(symbol)
    
    def get_timeframe_data(self, symbol: str, timeframe_name: str) -> Optional[TimeframeData]:
        """Gibt Timeframe-Daten zurück"""
        return self.timeframe_data.get(symbol, {}).get(timeframe_name)
    
    def get_latest_data(self, symbol: str) -> Dict[str, TimeframeData]:
        """Gibt alle neuesten Daten für Symbol zurück"""
        return self.timeframe_data.get(symbol, {})
    
    def add_sync_callback(self, callback: Callable[[SynchronizedData], None]):
        """Fügt Synchronisations-Callback hinzu"""
        self.sync_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt Status zurück"""
        return {
            'is_running': self.is_running,
            'active_timeframes': [tf.name for tf in self.active_timeframes],
            'symbols_tracked': len(self.timeframe_data),
            'synchronized_symbols': len(self.synchronized_data),
            'total_syncs': self.stats['total_syncs'],
            'successful_syncs': self.stats['successful_syncs'],
            'failed_syncs': self.stats['failed_syncs'],
            'success_rate': (self.stats['successful_syncs'] / max(1, self.stats['total_syncs'])) * 100,
            'data_points_collected': self.stats['data_points_collected'],
            'last_sync_time': self.stats['last_sync_time'].isoformat() if self.stats['last_sync_time'] else None
        }

if __name__ == "__main__":
    # Test-Modus
    manager = MT5MultiTimeframeManager()
    
    def sync_callback(synced_data):
        print(f"Sync: {synced_data.symbol} - Quality: {synced_data.sync_quality:.2f} - Timeframes: {list(synced_data.timeframes.keys())}")
    
    manager.add_sync_callback(sync_callback)
    
    try:
        if mt5.initialize():
            print("MT5 verbunden - starte Multi-Timeframe Manager")
            manager.start(["EURUSD", "GBPUSD"])
            
            while True:
                time.sleep(10)
                status = manager.get_status()
                print(f"Status: {status['symbols_tracked']} Symbole, {status['success_rate']:.1f}% Sync-Rate")
                
        else:
            print("MT5 Verbindung fehlgeschlagen")
            
    except KeyboardInterrupt:
        print("Beende Multi-Timeframe Manager...")
    finally:
        manager.stop()
        mt5.shutdown()