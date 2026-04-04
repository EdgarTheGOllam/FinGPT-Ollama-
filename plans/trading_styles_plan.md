# Trading Styles Überarbeitung - Implementierungsplan

## Übersicht

Dieser Plan beschreibt die Implementierung von 4 erweiterten Trading-Styles für die FinGPT Trading Engine:

1. **Orderblock / Supply-Demand-Trading (ICT-Style)**
2. **Market Profile / Volume Profile**
3. **Pattern-Trading ohne Indikator**
4. **Strukturbasierte Trendfolgen**

---

## 1. Orderblock / Supply-Demand-Trading (ICT-Style)

### Konzepte

- **Orderblock**: Zone, von der aus starke impulsive Moves gestartet wurden
- **Fair Value Gap (FVG)**: Bereich mit "leerem" Volumen zwischen zwei Kerzen
- **Liquidity Pool**: Bereich, wo Stop-Losses gesammelt werden
- **Break of Structure (BOS)**: Kurs durchbricht vorheriges Hoch/Tief
- **Return-to-Zone**: Preis kehrt zurück, um in Trendrichtung einzusteigen

### Module

```
trading/
├── ict_trading/
│   ├── __init__.py
│   ├── order_block.py      # Orderblock-Erkennung
│   ├── fvg_analyzer.py     # Fair Value Gap Analyse
│   ├── liquidity.py        # Liquidity Pool Erkennung
│   ├── market_structure.py # BOS, CHOCH Erkennung
│   └── ict_strategy.py    # Hauptstrategie-Klasse
```

### Konfiguration

```python
ICTConfig = {
    # Orderblock-Einstellungen
    "ob_lookback_bars": 100,
    "ob_min_momentum_pips": 20,
    "ob_max_retest_bars": 10,
    "ob_confluence_required": True,
    
    # FVG-Einstellungen
    "fvg_min_gap_pips": 5,
    "fvg_weak_threshold": 3,
    "fvg_strong_threshold": 10,
    
    # Liquidity
    "liquidity_sweep_tolerance": 2,  # Pips
    "equal_highs_window": 5,
    "fibonacci_levels": [0.618, 0.786, 1.0, 1.272],
    
    # Einstiegs-Trigger
    "entry_trigger": "RETURN_TO_ZONE",  # RETURN_TO_ZONE, FVG_BREAK, BOS_CONFIRM
    "confirmation_bars": 1,
    
    # Stop-Loss
    "sl_placement": "BELOW_OB",  # BELOW_OB, BELOW_FVG, BELOW_LIQUIDITY
    "sl_buffer_pips": 5,
    
    # Take-Profit
    "tp_zones": [
        {"target": "NEXT_LIQUIDITY", "rr": 1.0},
        {"target": "PREVIOUS_STRUCTURE", "rr": 1.5},
        {"target": "EXTREME_HIGH_LOW", "rr": 2.0}
    ],
    
    # Risiko
    "min_rr_ratio": 1.5,
    "max_risk_percent": 1.0,
    
    # Marktphasen
    "allowed_market_phases": ["TRENDING", "BOUTS"],
    "range_filter_enabled": True
}
```

### Algorithmen

#### Orderblock-Erkennung
1. Suche nach Kerzen mit starkem Close (body > 70% der Range)
2. Prüfe ob darauf ein starker Impuls-Move folgte (> X Pips)
3. Markiere die Zone als Orderblock wenn Preis zurückkehrt
4. Validierung durch Volumen-Bestätigung

#### Fair Value Gap (FVG)
```
Für jede Kerze i:
    if low[i] > high[i+1]:  # Bullisches FVG
        fvg = low[i] - high[i+1]
    elif high[i] < low[i+1]:  # Bearisches FVG
        fvg = low[i+1] - high[i]
```

#### Return-to-Zone Szenario
1. Identifiziere aktive Orderblöcke
2. Warte auf Preis-Rückkehr zur Zone (< X% Distanz)
3. Bestätige mit FVG oder Liquidity Sweep
4. Entry bei Bullish Confirmation

### Einstiegs-Trigger

| Trigger | Beschreibung | Kondition |
|---------|---------------|-----------|
| RETURN_TO_ZONE | Preis kehrt zum OB zurück | Preis < 5 Pips vom OB, Kerze schließt bullish |
| FVG_BREAK | FVG wird gebrochen | Preis durchbricht FVG-Bereich, Momentum bestätigt |
| BOS_CONFIRM | Break of Structure | Kurs bricht vorheriges Hoch/Tief mit Impuls |

### Marktphasen-Filter

- **TRENDING**: HH/HL Sequenz erkennbar
- **BOUTS**: Impulsive Bewegungen mit Korrekturen
- **RANGE**: Nur seitliche Bewegung, keine Trades

---

## 2. Market Profile / Volume Profile

### Konzepte

- **Value Area (VA)**: Bereich wo X% des Volumens stattfand (typisch 70%)
- **Point of Control (POC)**: Preis mit höchstem Volumen
- **High Volume Node (HVN)**: Volume-Peak = magnetischer Preis
- **Low Volume Node (LVN)**: Volume-Tal = Unterstützungs-/Widerstandszonen
- **Day Types**: Normal Day, Trend Day, Double Distribution, Neutral Day

### Module

```
trading/
├── volume_profile/
│   ├── __init__.py
│   ├── profile_analyzer.py # VP-Berechnung
│   ├── day_type_classifier.py
│   ├── va_zone_detector.py
│   └── vp_strategy.py
```

### Konfiguration

```python
VPConfig = {
    # Volume Profile Einstellungen
    "vp_bars": 20,           # Anzahl Kerzen für VP
    "vp_bins": 20,           # Preis-Bins
    "value_area_pct": 70,    # VA in Prozent
    
    # POC-Einstellungen
    "poc_lookback": 3,       # Anzahl Tage für POC
    "poc_weighted": True,     # Gewichteter POC
    
    # HVN/LVN
    "hvn_threshold": 1.5,    # Multiplikator über Durchschnitt
    "lvn_threshold": 0.5,    # Multiplikator unter Durchschnitt
    
    # Day Type Classification
    "trend_threshold_pct": 0.8,  # % Preisrange für Trend Day
    "normal_range_pct": 0.5,   # Range für Normal Day
    "dd_min_touches": 2,       # Für Double Distribution
    
    # Einstiegs-Trigger
    "entry_on_poc_retest": True,
    "entry_on_hvn_bounce": True,
    "entry_on_va_break": True,
    
    # Stop-Loss
    "sl_outside_va": True,
    "sl_buffer_pips": 5,
    
    # Take-Profit
    "tp_poc": True,
    "tp_opposite_va": True,
    "tp_2r": True,
    
    # Risiko
    "min_rr_ratio": 1.5,
    
    # Marktphasen
    "allowed_phases": ["ALL"]
}
```

### Algorithmen

#### Volume Profile Berechnung
```python
def calculate_vp(rates, bins=20):
    prices = [(r['high'] + r['low']) / 2 for r in rates]
    volumes = [r['tick_volume'] for r in rates]
    
    min_price = min(prices)
    max_price = max(prices)
    bin_size = (max_price - min_price) / bins
    
    # Volume pro Bin
    bin_volumes = [0] * bins
    for price, vol in zip(prices, volumes):
        bin_idx = min(int((price - min_price) / bin_size), bins - 1)
        bin_volumes[bin_idx] += vol
    
    # POC = Bin mit höchstem Volumen
    poc_idx = bin_volumes.index(max(bin_volumes))
    poc = min_price + (poc_idx + 0.5) * bin_size
    
    # Value Area
    total_vol = sum(bin_volumes)
    va_vol = total_vol * (value_area_pct / 100)
    
    sorted_bins = sorted(enumerate(bin_volumes), key=lambda x: -x[1])
    va_vol_acc = 0
    va_bins = []
    for idx, vol in sorted_bins:
        if va_vol_acc >= va_vol:
            break
        va_bins.append(idx)
        va_vol_acc += vol
    
    va_high = min_price + (max(va_bins) + 1) * bin_size
    va_low = min_price + min(va_bins) * bin_size
    
    return {
        "poc": poc,
        "va_high": va_high,
        "va_low": va_low,
        "bin_volumes": bin_volumes,
        "hvns": [i for i, v in enumerate(bin_volumes) if v > avg * hvn_threshold],
        "lvns": [i for i, v in enumerate(bin_volumes) if v < avg * lvn_threshold]
    }
```

#### Day Type Classification

| Day Type | Kriterien |
|----------|-----------|
| **Normal Day** | VA in mittlerem Bereich der Day Range, symmetrische Verteilung |
| **Trend Day** | >80% der Range außerhalb VA, POC am Rand |
| **Double Distribution** | Zwei POC-Levels, beide berührt |
| **Neutral Day** | POC in Mitte, VA füllt gesamte Range |

---

## 3. Pattern-Trading ohne Indikator

### Konzepte

- **Chart Patterns**: Flag, Wedge, Head & Shoulders, Dreiecke, Cup & Handle
- **Candlestick Patterns**: Hammer, Engulfing, Morning/Evening Star, Doji, Piercing
- **S/R Kombination**: Patterns müssen an Unterstützungen/Widerständen liegen

### Module

```
trading/
├── pattern_trading/
│   ├── __init__.py
│   ├── chart_patterns.py   # Flag, Wedge, H&S, Dreiecke
│   ├── candle_patterns.py # Kerzenmuster
│   ├── pattern_validator.py
│   └── pattern_strategy.py
```

### Konfiguration

```python
PatternConfig = {
    # Chart Patterns
    "enable_flags": True,
    "enable_wedges": True,
    "enable_head_shoulders": True,
    "enable_triangles": True,
    "enable_cup_handle": True,
    
    # Candlestick Patterns
    "enable_hammer": True,
    "enable_engulfing": True,
    "enable_morning_star": True,
    "enable_doji": True,
    "enable_piercing": True,
    
    # Pattern-Validierung
    "min_pattern_bars": 5,
    "pattern_tolerance": 0.002,  # Preis-Toleranz
    
    # S/R Bestätigung
    "sr_confirmation_required": True,
    "sr_touch_tolerance_pips": 3,
    
    # Einstiegs-Trigger
    "entry_on_pattern_complete": True,
    "entry_on_sr_retest": True,
    
    # Stop-Loss
    "sl_below_pattern_low": True,
    "sl_buffer_pips": 5,
    
    # Take-Profit
    "tp_pattern_target": True,
    "tp_2r": True,
    "tp_3r": True,
    
    # Risiko
    "min_rr_ratio": 1.5,
    
    # Marktphasen
    "allowed_phases": ["ALL"]
}
```

### Pattern-Erkennungsalgorithmen

#### Flag Pattern
```
1. Identifiziere starke impulsive Bewegung (> 1% in < 10 Bars)
2. Konsolidierung in Channel (parallel lines)
3. Ausbruch in Trendrichtung
4. Entry: Close über/unter Ober-/Unterlinie
```

#### Hammer (Bullish)
```
1. Body im oberen Drittel der Kerze
2. Lower Shadow > 2x Body
3. Kein oder sehr kleiner Upper Shadow
4. Bestätigung: Nächste Kerze schließt über Hammer-Hoch
```

#### Engulfing (Bullish)
```
1. Aktuelle Kerze: bullish, engulf Previous bearish
2. Previous: bearish, vollständig eingetaucht in aktuelle
3. Beide Kerzen mit klaren Bodies (> 50% der Range)
```

---

## 4. Strukturbasierte Trendfolgen (Pure Price Action)

### Konzepte

- **HH/HL**: Higher High / Higher Low = Aufwärtstrend
- **LH/LL**: Lower High / Lower Low = Abwärtstrend
- **Break of Structure (BOS)**: Durchbruch durch vorheriges Hoch/Tief
- **Liquidity Sweep**: Stop-Lock-Bereich wird angesteuert
- **Change of Character (CHOCH)**: Trendwende durch Strukturwechsel

### Module

```
trading/
├── structure_trading/
│   ├── __init__.py
│   ├── structure_analyzer.py  # HH/HL/LH/LL
│   ├── bos_detector.py        # Break of Structure
│   ├── liquidity_sweep.py    # Liquidity Sweeps
│   ├── choch_detector.py     # Change of Character
│   └── structure_strategy.py
```

### Konfiguration

```python
StructureConfig = {
    # Struktur-Einstellungen
    "structure_lookback": 20,
    "swing_detection_window": 5,
    "fractal_period": 5,
    
    # BOS
    "bos_confirmation_bars": 1,
    "bos_min_break_pips": 5,
    "bos_requires_volume": False,
    
    # Liquidity
    "liquidity_sweep_detection": True,
    "stop_hunt_buffer_pips": 2,
    "equal_highs_min_touches": 2,
    "fib_liquidity_levels": [0.618, 0.786, 1.0],
    
    # CHOCH
    "choch_detection": True,
    "choch_require_fvg": True,
    
    # Einstiegs-Trigger
    "entry_on_bos": True,
    "entry_on_liquidity_sweep": True,
    "entry_on_choch": True,
    
    # Stop-Loss
    "sl_below_structure": True,
    "sl_buffer_pips": 5,
    
    # Take-Profit
    "tp_next_structure": True,
    "tp_2r": True,
    "tp_3r": True,
    
    # Risiko
    "min_rr_ratio": 2.0,
    "max_risk_percent": 1.5,
    
    # Marktphasen
    "allowed_phases": ["TRENDING", "BOUTS"]
}
```

### Algorithmen

#### Swing Detection (Fraktale)
```python
def detect_swings(highs, lows, period=5):
    swing_highs = []
    swing_lows = []
    
    for i in range(period, len(highs) - period):
        # Bullisher Swing
        if highs[i] > highs[i-period:i] and highs[i] > highs[i+1:i+period+1]:
            swing_highs.append((i, highs[i]))
        
        # Bearischer Swing
        if lows[i] < lows[i-period:i] and lows[i] < lows[i+1:i+period+1]:
            swing_lows.append((i, lows[i]))
    
    return swing_highs, swing_lows
```

#### HH/HL Sequenz
```python
def analyze_trend_structure(swing_highs, swing_lows):
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "NEUTRAL"
    
    # Prüfe HH/HL
    hh = swing_highs[-1][1] > swing_highs[-2][1]
    hl = swing_lows[-1][1] > swing_lows[-2][1]
    
    # Prüfe LH/LL
    lh = swing_highs[-1][1] < swing_highs[-2][1]
    ll = swing_lows[-1][1] < swing_lows[-2][1]
    
    if hh and hl:
        return "BULLISH"
    elif lh and ll:
        return "BEARISH"
    else:
        return "NEUTRAL"
```

---

## Integration in TradingController

Die neuen Styles werden in `trading_controller.py` integriert:

```python
STYLE_MAP = {
    # ... existing styles ...
    "ICT Orderblock": {
        "module": "trading.ict_trading.ict_strategy",
        "class": "ICTStrategy",
        "tf": mt5.TIMEFRAME_M15,
        "sl": 20,
        "tp": 50,
        "pause": 120,
        "risk_pct": 1.0,
        "max_daily": 250,
    },
    "Market Profile": {
        "module": "trading.volume_profile.vp_strategy",
        "class": "VPStrategy",
        "tf": mt5.TIMEFRAME_M15,
        "sl": 15,
        "tp": 40,
        "pause": 120,
        "risk_pct": 1.0,
        "max_daily": 200,
    },
    "Pattern Trading": {
        "module": "trading.pattern_trading.pattern_strategy",
        "class": "PatternStrategy",
        "tf": mt5.TIMEFRAME_M15,
        "sl": 20,
        "tp": 50,
        "pause": 120,
        "risk_pct": 1.0,
        "max_daily": 250,
    },
    "Structure Trading": {
        "module": "trading.structure_trading.structure_strategy",
        "class": "StructureStrategy",
        "tf": mt5.TIMEFRAME_M15,
        "sl": 25,
        "tp": 75,
        "pause": 180,
        "risk_pct": 1.5,
        "max_daily": 300,
    },
}
```

---

## Gemeinsame Schnittstelle

Jede Strategie implementiert folgende Methoden:

```python
class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, symbol: str, data: dict) -> dict:
        """Analysiere Markt und gebe Signal zurück"""
        pass
    
    @abstractmethod
    def get_signal(self, symbol: str) -> dict:
        """
        Returns:
            dict mit:
            - action: "BUY" | "SELL" | "HOLD"
            - entry_price: float
            - stop_loss: float
            - take_profit: float
            - confidence: float (0-1)
            - reason: str
            - pattern_type: str (optional)
            - rr_ratio: float (optional)
        """
        pass
    
    @abstractmethod
    def validate_entry(self, signal: dict) -> bool:
        """Validiere ob Einstieg valide ist"""
        pass
    
    def get_market_phase(self, symbol: str) -> str:
        """Bestimme Marktphase: TRENDING, RANGE, VOLATILE"""
        pass
```

---

## Implementierungs-Reihenfolge

1. **Base Classes** - Gemeinsame Basis-Klassen und Interfaces
2. **Orderblock/ICT** - Erste Implementierung
3. **Volume Profile** - Zweite Implementierung  
4. **Pattern Trading** - Dritte Implementierung
5. **Structure Trading** - Vierte Implementierung
6. **Integration** - Einbau in TradingController
7. **Tests** - Unit- und Integrationstests
