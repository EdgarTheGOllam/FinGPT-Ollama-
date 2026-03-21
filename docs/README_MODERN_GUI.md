# FinGPT Modern Professional GUI

Eine vollständig überarbeitete, moderne und professionelle Benutzeroberfläche für das FinGPT Trading-System mit erweiterten Funktionen.

## Übersicht

Diese moderne GUI bietet eine ansprechende, farbenfrohe und intuitive Benutzeroberfläche mit folgenden Hauptfunktionen:

### 🎨 Design-Verbesserungen
- Modernes Farbschema mit ansprechenden Farbverläufen
- Professionelle Icons und Schatteneffekte
- Responsive Gestaltung für verschiedene Bildschirmgrößen
- Klare visuelle Hierarchie und intuitive Navigation

### 🚀 Erweiterte Funktionen
- **Dashboard** mit Live-Daten-Anzeige
- **Interaktive Plotly-Charts** für technische Analysen
- **Terminal-Output-Bereich** für Systemmeldungen
- **Konfigurationspanel** für Einstellungen
- **Statusleiste** mit Systeminformationen

## Funktionen im Detail

### 📊 Dashboard
Das Dashboard bietet einen Überblick über wichtige Trading-Metriken:
- Kontostand und Performance-Kennzahlen
- Offene Positionen und aktuelle Trades
- Gewinn-/Verlust-Anzeigen und Win-Rate
- Live Markt-Daten-Tabelle mit Echtzeit-Updates

### 📈 Charts & Visualisierungen
Mit Plotly-Integration können interaktive Finanzcharts angezeigt werden:
- Preis-Charts mit technischen Indikatoren
- Volumen-Analysen und Markt-Trends
- Interaktive Zoom- und Pan-Funktionen
- Exportmöglichkeiten für Analysen

### 💻 Terminal
Der integrierte Terminal-Bereich zeigt Systemmeldungen und Logs:
- Echtzeit-Output von Trading-Aktivitäten
- Fehlermeldungen und Diagnoseinformationen
- Simulationsmodus für Entwicklungsphase
- Farbcodierte Meldungen für bessere Lesbarkeit

### ⚙️ Konfiguration
Das Konfigurationspanel ermöglicht die Anpassung aller Systemeinstellungen:
- Ollama-URL und Modell-Auswahl
- Trading-Parameter und Risikomanagement
- Technische Indikatoren und deren Einstellungen
- UI-Anpassungen und Personalisierung

## Technische Umsetzung

### Architektur
```
┌─────────────────────────────────────────────────────────────┐
│                    GUI-Schicht                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  ModernFinGPTGUI│  │   Widgets       │  │   Styling    │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                Geschäftslogik-Schicht                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  ConfigManager  │  │  DataProcessor  │  │  ChartEngine │ │
│  │  (optional)     │  │  (simuliert)    │  │  (Plotly)    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  Daten-Schicht                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Live-Markt-    │  │  Historische    │  │  Nutzer-     │ │
│  │  daten (sim)    │  │  Konfiguration  │  │  einstellungen│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Abhängigkeiten
- **tkinter**: Standard-GUI-Bibliothek (in Python enthalten)
- **plotly** (optional): Für interaktive Charts (`pip install plotly`)
- **requests**: Für HTTP-Anfragen (bereits in requirements.txt)

## Installation

### Voraussetzungen
- Python 3.7 oder höher
- Tkinter (standardmäßig in Python enthalten)
- FinGPT-Systemdateien

### Empfohlene Optionen
```bash
# Für volle Funktionalität:
pip install plotly
```

### Starten der GUI
```bash
# Startet die moderne GUI mit Fallback auf klassische GUI
python launch_gui.py
```

## Verwendung

### Schnellstart
1. **GUI starten**: `python launch_gui.py`
2. **Live-Daten aktivieren**: Klicken Sie auf "Live Daten anzeigen"
3. **Terminal simulieren**: Im Terminal-Tab "Simulate Output" klicken
4. **Konfiguration anpassen**: Im Konfigurations-Tab Einstellungen ändern

### Navigation
- **Dashboard-Tab**: Übersicht über alle wichtigen Kennzahlen
- **Charts-Tab**: Interaktive Finanz-Charts (bei installiertem Plotly)
- **Terminal-Tab**: Systemmeldungen und Logs
- **Konfiguration-Tab**: Alle Systemeinstellungen anpassen

## Design-Features

### Farbpalette
- **Primärblau**: `#2E86AB` (Hauptfarbe für wichtige Elemente)
- **Akzentrot**: `#A23B72` (Warnungen und wichtige Hinweise)
- **Erfolgsgrün**: `#5EBA7D` (Positive Meldungen und Buttons)
- **Hintergrund**: `#F8F9FA` ( Heller Hintergrund für bessere Lesbarkeit)
- **Kartenhintergrund**: `#FFFFFF` (Weiße Karten für Kontrast)

### Typografie
- **Überschriften**: Segoe UI, fett, 16px (Header) bzw. 12px (Subheader)
- **Normaler Text**: Segoe UI, 10px
- **Terminal**: Consolas, 10px (für Code-ähnliche Darstellung)

### Responsives Design
- Flexible Grid-Layouts die sich an Bildschirmgröße anpassen
- Scrollbare Bereiche für große Datenmengen
- Adaptive Spaltenbreiten für verschiedene Auflösungen

## Entwicklung

### Code-Struktur
```
FinGPT-Ollama-/
├── modern_fingpt_gui.py      # Moderne Haupt-GUI
├── launch_gui.py             # Launcher mit Fallback
├── fingpt_config_gui.py      # Klassische GUI (Fallback)
├── README_MODERN_GUI.md      # Diese Dokumentation
└── requirements.txt          # Abhängigkeiten
```

### Erweiterungsmöglichkeiten
1. **Echte Datenintegration**: Verbindung zu MetaTrader 5 API
2. **Erweiterte Charts**: Mehr technische Indikatoren
3. **Benachrichtigungssystem**: Push-Nachrichten bei wichtigen Ereignissen
4. **Berichtsfunktionen**: PDF-Export von Analysen und Performance

## Fehlerbehandlung

### Bekannte Probleme
- Ohne Plotly sind Charts nicht verfügbar (Funktionalität bleibt aber erhalten)
- Live-Daten sind in der Demo-Version simuliert

### Fallback-Mechanismus
Wenn die moderne GUI nicht startet, wird automatisch auf die klassische GUI zurückgegriffen.

## Lizenz

Dieses Projekt ist Teil des FinGPT-Systems und unterliegt den gleichen Lizenzbedingungen wie das Hauptprojekt.

---

**Version**: 1.0.0  
**Letzte Aktualisierung**: 2024  
**Kompatibilität**: Python 3.7+