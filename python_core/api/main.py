import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
from typing import List, Dict, Any

app = FastAPI(title="FinGPT Core API", version="1.0.0")

# CORS config to allow React frontend (running on localhost:5173/1420)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für Entwicklung; später einschränken!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class MarketData(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_percent: float

class PortfolioItem(BaseModel):
    symbol: str
    position: float
    value: float
    pnl: float
    pnl_percent: float

# Routes
@app.get("/")
def read_root():
    """Root endpoint zur Statusprüfung."""
    return {"message": "FinGPT Core API is running. Access /docs for the API documentation."}

@app.get("/api/v1/market/summary", response_model=List[MarketData])
def get_market_summary():
    """Gibt eine Liste realistischer Mock-Marktdaten zurück."""
    # Hier später die echten Daten aus core/market_analyzer.py laden!
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD", "US500", "NAS100"]
    data = []
    for sym in symbols:
        base_price = {"EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 150.20, "XAUUSD": 2040.50, 
                      "BTCUSD": 65400.00, "ETHUSD": 3400.00, "US500": 5100.25, "NAS100": 18000.50}.get(sym, 100.0)
        
        change_pct = random.uniform(-2.5, 2.5)
        change_abs = base_price * (change_pct / 100.0)
        
        data.append(MarketData(
            symbol=sym,
            price=round(base_price + change_abs, 4),
            change_24h=round(change_abs, 4),
            change_percent=round(change_pct, 2)
        ))
    return data

@app.get("/api/v1/portfolio", response_model=Dict[str, Any])
def get_portfolio():
    """Gibt Mock-Portfolio-Daten zurück."""
    # Später echte Daten aus core/trading_controller.py oder mt5_broker.py
    positions = [
        PortfolioItem(symbol="EURUSD", position=1.5, value=162750.0, pnl=450.50, pnl_percent=0.28),
        PortfolioItem(symbol="XAUUSD", position=5.0, value=10202.5, pnl=-120.00, pnl_percent=-1.16),
        PortfolioItem(symbol="US500", position=10.0, value=51002.5, pnl=850.75, pnl_percent=1.69)
    ]
    
    total_value = sum(p.value for p in positions) + 25000.0 # Cash
    total_pnl = sum(p.pnl for p in positions)
    
    return {
        "balance": 25000.0,
        "equity": total_value,
        "margin_used": 5000.0,
        "free_margin": 20000.0,
        "total_pnl": total_pnl,
        "total_pnl_percent": round((total_pnl / (total_value - total_pnl)) * 100, 2) if total_value > total_pnl else 0,
        "positions": positions
    }

@app.get("/api/v1/status")
def get_status():
    """Gibt den Systemstatus zurück (MT5, AI, DB)."""
    return {
        "mt5_connected": True,
        "ai_engine_ready": True,
        "database_status": "ok",
        "active_strategies": 2,
        "uptime_seconds": 3600
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
