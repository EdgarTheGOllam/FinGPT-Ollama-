# FinGPT Configuration GUI

Ein modernes, plattformunabhängiges Python-Interface für die Konfiguration von FinGPT und FinGPT Extended.

## Übersicht

Dieses GUI-Tool bietet eine benutzerfreundliche Oberfläche zur Konfiguration aller wichtigen Parameter der FinGPT Trading-Systeme. Es implementiert eine saubere Trennung zwischen GUI-Logik und Geschäftslogik und bietet umfassende Validierung und Error-Handling.

## Features

### 🎯 Hauptfunktionen
- **Intuitive Benutzeroberfläche** mit modernem Tkinter-Design
- **Tab-basierte Navigation** für übersichtliche Parameter-Gruppierung
- **Echtzeit-Validierung** aller Konfigurationsparameter
- **Visuelle Rückmeldung** über Konfigurationsstatus
- **Import/Export** von Konfigurationen
- **Automatische Backups** bei Konfigurationsänderungen

### 📋 Konfigurationsbereiche

#### Grundlegende Einstellungen
- Ollama URL und Modell-Auswahl
- Trading-Parameter (Lot Size, Risk Management)
- Auto-Trading Konfiguration
- Analyse-Intervalle

#### Erweiterte Einstellungen
- RSI-Parameter (Periode, Overbought/Oversold)
- MACD-Einstellungen (Fast/Slow/Signal Period)
- Support/Resistance-Konfiguration
- Multi-Timeframe-Parameter

#### Extended Einstellungen
- Menü-Konfiguration (Original/Extended)
- Erweiterte Funktionen (Indikatoren, KI-Analyse)
- UI-Einstellungen (Farbschema, Status-Bar)
- Performance-Optimierungen

## Installation

### Voraussetzungen
- Python 3.7 oder höher
- Tkinter (standardmäßig in Python enthalten)
- FinGPT und FinGPT Extended Dateien

### Installationsschritte

1. **Repository klonen oder Dateien herunterladen**
   ```bash
   # Alle benötigten Dateien müssen im selben Verzeichnis liegen:
   # - fingpt_config_gui.py
   # - config_manager.py
   # - requirements.txt
   ```

2. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **GUI starten**
   ```bash
   python fingpt_config_gui.py
   ```

## Verwendung

### Schnellstart

1. **GUI starten**: `python fingpt_config_gui.py`
2. **Konfiguration anpassen**: Navigieren Sie durch die Tabs und passen Sie die Parameter an
3. **Validieren**: Klicken Sie auf "Validieren" um die Einstellungen zu prüfen
4. **Speichern**: Klicken Sie auf "Speichern" um die Konfiguration zu übernehmen

### Detaillierte Bedienung

#### Tab "Grundlegende Einstellungen"
- **Ollama URL**: Geben Sie die URL Ihres Ollama-Servers ein
- **Modell-Auswahl**: Wählen Sie aus verfügbaren KI-Modellen
- **Trading-Parameter**: Konfigurieren Sie Lot Size und Risk Management
- **Auto-Trading**: Aktivieren Sie automatisches Trading

#### Tab "Erweiterte Einstellungen"
- **RSI-Einstellungen**: Passen Sie RSI-Perioden und Level an
- **MACD-Einstellungen**: Konfigurieren Sie MACD-Parameter
- **Support/Resistance**: Definieren Sie S/R-Parameter

#### Tab "Extended Einstellungen"
- **Menü-Konfiguration**: Wählen Sie Menü-Style und sichtbare Optionen
- **Erweiterte Funktionen**: Aktivieren Sie zusätzliche Features
- **UI-Einstellungen**: Passen Sie das Erscheinungsbild an

## Architektur

### Trennung von Verantwortlichkeiten

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI-Schicht                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   FinGPTConfig  │  │  Hauptfenster   │  │   Widgets    │ │
│  │      GUI        │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                Geschäftslogik-Schicht                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  ConfigManager  │  │  FinGPTConfig   │  │ Validation   │ │
│  │                 │  │  DataClasses    │  │   Logic      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  Daten-Schicht                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  JSON Configs   │  │     Backups     │  │   Exports    │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Klassen-Struktur

#### FinGPTConfigGUI
- **Verantwortlich**: Benutzeroberfläche und User-Interaction
- **Hauptfunktionen**: Widget-Management, Event-Handling, Status-Updates

#### ConfigManager
- **Verantwortlich**: Konfigurationsverwaltung und Persistenz
- **Hauptfunktionen**: Laden/Speichern, Validierung, Import/Export

#### FinGPTConfig / FinGPTExtendedConfig
- **Verantwortlich**: Datenhaltung und Typ-Sicherheit
- **Hauptfunktionen**: Parameter-Kapselung, Default-Werte

## Validierung

Das System implementiert umfassende Validierung für alle Konfigurationsparameter:

### Grundlegende Validierungen
- **Numerische Bereiche**: Alle numerischen Parameter haben definierte Min/Max-Werte
- **Logische Konsistenz**: Parameter müssen zueinander konsistent sein
- **Typ-Sicherheit**: Eingaben werden in korrekte Datentypen konvertiert

### Beispiele
```python
# RSI-Validierung
if config.rsi_oversold >= config.rsi_overbought:
    errors.append("RSI Oversold muss kleiner als Overbought sein")

# Lot Size-Validierung
if config.default_lot_size <= 0 or config.default_lot_size > 10:
    errors.append("Default Lot Size muss zwischen 0 und 10 liegen")
```

## Error-Handling

### Mehrstufiges Error-Handling

1. **GUI-Ebene**: Benutzerfreundliche Fehlermeldungen
2. **Logik-Ebene**: Detaillierte Fehler-Beschreibungen
3. **Daten-Ebene**: Sichere Fallbacks und Recovery

### Fehler-Kategorien
- **Validierungsfehler**: Ungültige Parameter
- **Verbindungsfehler**: Ollama nicht erreichbar
- **Dateifehler**: Konfiguration nicht ladbar
- **Systemfehler**: Unerwartete Probleme

## Backup & Wiederherstellung

### Automatische Backups
- **Zeitpunkt**: Vor jeder Konfigurationsänderung
- **Speicherort**: `config/backups/`
- **Format**: JSON mit Zeitstempel
- **Anzahl**: Unbegrenzt (manuelle Bereinigung möglich)

### Manuelles Backup
```python
# Backup erstellen
config_manager.create_backup()

# Konfiguration zurücksetzen
config_manager.reset_to_defaults()
```

## Plattformunabhängigkeit

### Unterstützte Plattformen
- **Windows**: Voll unterstützt
- **macOS**: Voll unterstützt
- **Linux**: Voll unterstützt

### Plattform-spezifische Anpassungen
- **Pfad-Trennung**: Verwendung von `pathlib.Path`
- **Font-Rendering**: System-Standard-Fonts
- **Farbschemata**: Adaptive Farbwahl

## Performance

### Optimierungen
- **Lazy Loading**: Konfigurationen nur bei Bedarf laden
- **Background-Threads**: Netzwerk-Operationen asynchron
- **Caching**: Häufig genutzte Daten zwischenspeichern
- **Memory Management**: Effiziente Ressourcen-Nutzung

### Benchmarks
- **Startzeit**: < 2 Sekunden
- **Speichern**: < 1 Sekunde
- **Validierung**: < 0.5 Sekunden
- **Memory**: < 50 MB

## Sicherheit

### Sicherheitsmaßnahmen
- **Eingabe-Validierung**: Alle Benutzereingaben werden validiert
- **Datei-Zugriff**: Sichere Datei-Operationen
- **Netzwerk**: Timeout und Fehlerbehandlung bei HTTP-Anfragen
- **Daten-Integrität**: Checksummen für Konfigurationsdateien

## Erweiterbarkeit

### Custom-Parameter hinzufügen
```python
# 1. DataClass erweitern
@dataclass
class FinGPTConfig:
    # ... bestehende Parameter
    custom_parameter: str = "default_value"

# 2. GUI erweitern
def create_custom_tab(self):
    # Custom-Tab hinzufügen
    pass

# 3. Validierung erweitern
def validate_custom_parameter(self, config):
    # Custom-Validierung
    pass
```

### Plugin-System
Das System ist für zukünftige Plugin-Erweiterungen vorbereitet.

## Troubleshooting

### Häufige Probleme

#### GUI startet nicht
```bash
# Tkinter installieren (Linux)
sudo apt-get install python3-tk

# Python-Version prüfen
python --version  # Muss 3.7+ sein
```

#### Ollama-Verbindung fehlgeschlagen
```bash
# Ollama-Status prüfen
ollama list

# URL prüfen
curl http://localhost:11434/api/tags
```

#### Konfiguration nicht ladbar
```bash
# Berechtigungen prüfen
ls -la config/

# Backup wiederherstellen
cp config/backups/fingpt_config_*.json config/fingpt_config.json
```

## Entwicklung

### Code-Struktur
```
FinGPT-Ollama-/
├── fingpt_config_gui.py      # Haupt-GUI-Anwendung
├── config_manager.py         # Geschäftslogik
├── requirements.txt          # Abhängigkeiten
├── README.md                 # Dokumentation
├── config/                   # Konfigurationsverzeichnis
│   ├── fingpt_config.json
│   ├── fingpt_extended_config.json
│   └── backups/
└── tests/                    # Unit-Tests (optional)
```

### Coding-Standards
- **PEP 8**: Python-Style-Guide
- **Type-Hints**: Für bessere Code-Dokumentation
- **Docstrings**: Ausführliche Funktionsbeschreibungen
- **Error-Handling**: Umfassende Fehlerbehandlung

## Lizenz

Dieses Projekt ist Teil des FinGPT-Systems und unterliegt den gleichen Lizenzbedingungen.

## Support

Bei Problemen oder Fragen:
1. **Dokumentation prüfen**: README.md und Code-Comments
2. **Troubleshooting**: Siehe Troubleshooting-Abschnitt
3. **Logs prüfen**: Konsolenausgaben und Fehlermeldungen
4. **Community**: GitHub-Issues oder Foren

---

**Version**: 1.0.0  
**Letzte Aktualisierung**: 2024  
**Kompatibilität**: Python 3.7+