# 🤖 FinGPT – KI‑gestütztes Trading‑System für MetaTrader 5

> "Der Markt kann länger irrational bleiben, als du liquide bleiben kannst." – John Maynard Keynes

Ein professionelles, vollständig lokales Python‑basiertes Trading‑System, das klassische technische Indikatoren mit großen Sprachmodellen (LLMs) über **Ollama** kombiniert und über die MetaTrader 5‑API (MQL5‑Bridge) ausführt.

## 📌 Features

| Feature | Kurzbeschreibung |
| ------- | ----------------- |
| **Modernes GUI** | Hochwertiges Dashboard mit Dark Mode, Echtzeit-Metriken und Splash-Screen Animation. |
| **KI‑Integration** | Nutzt **Ollama** (fingpt, llama3) für Marktanalysen mit Reasoning & Confidence-Score. |
| **Auto‑Trading Engine** | Vollautomatische Pipeline: Trend-Analyse → Indikatoren → KI-Validierung → Order-Platzierung. |
| **Risikomanagement** | Dynamische Lot-Berechnung (% Risiko), Trailing-Stops, Partial-Close und Schutzmechanismen. |
| **Echtzeit-Charts** | Integration von Plotly für interaktive Markt-Visualisierungen direkt in der GUI. |
| **Modularer Aufbau** | Saubere Trennung von Broker-Logik, Markt-Analyse, KI-Engine und UI-Komponenten. |
| **Offline‑First** | Höchster Datenschutz: Alles läuft lokal – keine Cloud‑Abhängigkeiten notwendig. |

## � Projektstruktur

Das System ist modular aufgebaut, um Wartbarkeit und Erweiterbarkeit zu gewährleisten:

- `core/`: Das Herzstück – Enthält den `AIAnalyzer`, `MT5Broker` und Markt-Analyse-Logik.
- `gui/`: Beinhaltet die moderne CustomTkinter-Oberfläche sowie klassische CLI-Menüs.
- `trading/`: Logik für Indikatoren, Risikomanagement und Trading-Strategien.
- `bridge/`: Die technische Schnittstelle (Receiver/Indicator) zu MetaTrader 5.
- `config/`: Zentrale Verwaltung aller Parameter (KI-Modelle, Risiko, Pfade).
- `storage/`: Persistente Speicherung von Trade-Logs, KI-Reasoning und Journalen.

## �🚀 Installation

### 1. System‑Voraussetzungen
- **Python** ≥ 3.9 (empfohlen 3.11)
- **MetaTrader 5** (Demo‑ oder Live‑Konto mit aktiviertem Algo-Handel)
- **Ollama** – Modelle `fingpt`, `llama3` lokal installiert

### 2. Setup
```bash
# Repository klonen
git clone https://github.com/EdgarTomas2001/FinGPT-Ollama-.git
cd FinGPT-Ollama-

# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### 3. Ollama Modells laden
```bash
ollama pull fingpt
ollama pull llama3
```

## 📚 Nutzung

Das System wird über den zentralen Launcher gestartet:

```bash
python launch_gui.py
```

### GUI Funktionen:
- **Dashboard**: Live-Überblick über offene Positionen und Markt-Trends.
- **AI Analysis**: Manuelle oder automatische Analyse von Symbolen durch das LLM.
- **Settings**: Konfiguration von Risiko-Parametern, Trading-Zeiten und KI-Modellen direkt in der App.
- **Log Viewer**: Echtzeit-Überwachung aller System- und Handelsaktivitäten.

## 🛠️ Weiterentwicklung
- Modell‑Feintuning mit eigenen Finanz‑Datensätzen
- Docker‑Support für schnelles Setup
- Web‑UI (lokal, offline) via Flask + React
- Back‑Testing‑Modul für historische Simulationen
- CI/CD mit GitHub‑Actions (nur Lint & Tests, kein automatisches Deploy)

## 🤝 Mitwirken
1. Fork das Repository
2. Feature‑Branch erstellen (`git checkout -b feature/mein‑feature`)
3. Änderungen committen & Pushen
4. Pull‑Request öffnen – bitte einen kurzen Überblick im PR‑Body geben

*Bitte keine automatischen Pfad‑Ersetzungen im Code einbringen – verwende stattdessen Konfigurations‑Variablen.*

## ⚠️ Disclaimer
*FinGPT ist ein rein experimentelles, privates Projekt. Das System nutzt automatisierte Handelsentscheidungen und kann zu finanziellen Verlusten führen. Der Autor übernimmt keinerlei Haftung für Verluste, Schäden oder rechtliche Konsequenzen, die aus der Nutzung dieses Codes entstehen. Nutzer sind verpflichtet, das System zunächst in einer sicheren Umgebung (z. B. Demo‑Konto) zu testen und sämtliche regulatorischen Vorgaben sowie Risikomanagement‑Prinzipien eigenständig zu berücksichtigen.*

## 📜 Lizenz
MIT – du darfst das Projekt frei nutzen, modifizieren und kommerziell einsetzen, solange der Lizenz‑Hinweis erhalten bleibt.

---
> **Tipp für nächtliche Arbeit:** Starte das Skript in einer `tmux`‑Session, damit du bei Verbindungsabbrüchen das Log weiter verfolgen kannst.
