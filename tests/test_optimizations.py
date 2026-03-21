import pytest
import asyncio
from unittest.mock import MagicMock, patch
from core.ai_analyzer import AIAnalyzer
from core.market_analyzer import MarketAnalyzer
from core.config_manager import ConfigManager
import os

@pytest.fixture
def config_manager():
    return ConfigManager()

@pytest.fixture
def ai_analyzer():
    return AIAnalyzer()

@pytest.fixture
def market_analyzer():
    mock_broker = MagicMock()
    mock_broker.mt5_connected = True
    return MarketAnalyzer(broker=mock_broker)

def test_config_env_loading(config_manager):
    """Testet, ob .env Werte korrekt geladen werden"""
    with patch.dict(os.environ, {"OLLAMA_URL": "http://test-url:11434", "AI_API_KEY": "test-key"}):
        # Wir müssen load_dotenv manuell triggern oder eine neue Instanz erstellen
        config = ConfigManager()
        assert config.fingpt_config.ollama_url == "http://test-url:11434"
        assert config.fingpt_config.ai_api_key == "test-key"

@pytest.mark.asyncio
async def test_ai_analyzer_async(ai_analyzer):
    """Testet die asynchrone Kommunikation des AIAnalyzer"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"version": "0.1.0"}
        
        status = await ai_analyzer.check_ollama_status()
        assert status is True
        mock_get.assert_called_once_with("/api/version")

def test_market_analyzer_caching(market_analyzer):
    """Testet den Caching-Mechanismus im MarketAnalyzer"""
    symbol = "EURUSD"
    timeframe = 15 # mt5.TIMEFRAME_M15
    
    with patch("MetaTrader5.copy_rates_from_pos") as mock_copy:
        # Mock Daten
        mock_copy.return_value = [
            {'close': 1.1000}, {'close': 1.1010}, {'close': 1.1020},
            {'close': 1.1030}, {'close': 1.1040}, {'close': 1.1050},
            {'close': 1.1060}, {'close': 1.1070}, {'close': 1.1080},
            {'close': 1.1090}, {'close': 1.1100}, {'close': 1.1110},
            {'close': 1.1120}, {'close': 1.1130}, {'close': 1.1140},
            {'close': 1.1150}
        ]
        
        # Erster Aufruf (berechnet)
        val1 = market_analyzer.calculate_rsi(symbol, timeframe, period=10)
        assert val1 is not None
        assert mock_copy.call_count == 1
        
        # Zweiter Aufruf (aus Cache)
        val2 = market_analyzer.calculate_rsi(symbol, timeframe, period=10)
        assert val1 == val2
        assert mock_copy.call_count == 1 # Immer noch 1, da Cache genutzt wurde
