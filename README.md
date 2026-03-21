# 🤖 FinGPT – KI‑gestütztes Trading‑System für MetaTrader 5

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![MetaTrader 5](https://img.shields.io/badge/MetaTrader-5-green.svg)](https://www.metatrader5.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-orange.svg)](https://ollama.ai/)

> "Der Markt kann länger irrational bleiben, als du liquide bleiben kannst." – John Maynard Keynes

FinGPT ist ein professionelles, modulares Trading-Framework, das die Präzision klassischer technischer Indikatoren mit der kognitiven Analyse moderner **Large Language Models (LLMs)** verbindet. Das System agiert als intelligente Brücke zwischen lokalen KI-Instanzen (Ollama) oder Cloud-APIs und der MetaTrader 5 Handelsplattform.

---

## 🌟 Key Features

### 🧠 Intelligente KI-Analyse
- **Hybrid-KI-Support:** Nahtlose Integration von **lokalen Modellen** via Ollama (z. B. Llama 3, FinGPT-Specialized) und **Cloud-APIs** (OpenAI ChatGPT, etc.).
- **Deep Reasoning:** Die KI validiert Handelssignale basierend auf RSI, MACD und Preis-Action-Mustern.
- **Confidence Scoring:** Jede Empfehlung enthält einen Vertrauenswert zur Risikominimierung.

### ⚡ Auto-Trading Engine
- **Multi-Timeframe (MTF):** Trend-Bestimmung auf H1, punktgenauer Einstieg auf M15.
- **Advanced Indicators:** Dynamische Support/Resistance-Level, RSI-Erschöpfungssignale und MACD-Crossover.
- **Smarte Ausführung:** Automatisierte Orderplatzierung mit integriertem Fehlermanagement.

### 🛡️ Professionelles Risikomanagement
- **Dynamische Lot-Berechnung:** Automatische Positionsgrößenbestimmung basierend auf dem prozentualen Kontorisiko.
- **Partial Close:** Automatisierte Teilverkäufe (z. B. 50 % bei Target 1, 25 % bei Target 2).
- **Trailing Stop:** Dynamische Gewinnabsicherung durch nachziehende Stopp-Loss-Level.

### 🖥️ Modernes Dashboard
- **Glassmorphic UI:** Hochmoderne Benutzeroberfläche mit CustomTkinter und Dark Mode.
- **Live-Monitoring:** Echtzeit-Metriken, P&L-Kurven und interaktive Plotly-Charts.

---

## 📁 Projektstruktur

```text
FinGPT-Ollama-/
├── FinGPT.py           # CLI-Einstiegspunkt (Terminal-Modus)
├── launch_gui.py       # GUI-Einstiegspunkt (grafisches Dashboard)
├── requirements.txt    # Python-Abhängigkeiten
│
├── bridge/             # MQL5-Python Bridge & MT5-Schnittstellen
├── config/             # Konfigurationsdateien & Backups
├── core/               # Herzstück: Broker, KI-Analyse, Controller
├── docs/               # Vollständige Dokumentation (DE & EN)
├── faq_docs/           # Interaktive FAQ-Website (Retype)
├── gui/                # Frontend: Dashboard, Tabs & CLI-Menü
│   ├── components/     # Wiederverwendbare UI-Komponenten
│   └── views/          # Tab-Ansichten (Config, Charts, RL, etc.)
├── logs/               # Laufzeit-Logs (automatisch generiert)
├── rl_models/          # Gespeicherte RL-Modell-Gewichte (.h5)
├── scripts/            # Windows-Start-Skripte (.bat)
├── storage/            # Datenbanken, Trade-Journal & RL-Experience
├── tests/              # Automatisierte Testsuites (pytest)
└── trading/            # Handelsstrategien: RL-Agent, Risiko, Indikatoren
```

---

## 📚 Dokumentation

Alle Handbücher und Referenzdokumente befinden sich im [`docs/`](docs/) Ordner:

| Dokument | Beschreibung |
|---|---|
| [README_ENHANCED.md](docs/README_ENHANCED.md) | Erweitertes Feature-Handbuch |
| [README_GUI.md](docs/README_GUI.md) | GUI-Benutzerhandbuch |
| [README_MODERN_GUI.md](docs/README_MODERN_GUI.md) | Modernes Dashboard – Übersicht |
| [AI_FULLDRIVE_MODE.md](docs/AI_FULLDRIVE_MODE.md) | Technische Doku des AI-Fulldrive-Modus |
| [DOCUMENTATION_DE.md](docs/DOCUMENTATION_DE.md) | Vollständige Dokumentation (Deutsch) |
| [DOCUMENTATION_EN.md](docs/DOCUMENTATION_EN.md) | Full Documentation (English) |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Beitrag zum Projekt |
| [DISCLAIMER](docs/DISCLAIMER) | Rechtliche Hinweise & Risikohinweis |
| [REVIEWS.md](docs/REVIEWS.md) | Feedback & Reviews |

---

## 🚀 Schnellstart

### 1. Umgebung vorbereiten
```bash
# Repository klonen
git clone https://github.com/EdgarTheGOllam/FinGPT-Ollama-.git
cd FinGPT-Ollama-

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### 2. KI-Schnittstellen konfigurieren
FinGPT unterstützt zwei Arten der KI-Anbindung:

- **Lokal (Ollama):**  
  `ollama pull llama3`
- **Cloud (API):**  
  Trage deinen **OpenAI API Key** in `config/fingpt_config.json` ein.

### 3. System starten

**GUI-Modus (empfohlen):**
```bash
python launch_gui.py
# Alternativ unter Windows:
scripts\run_gui.bat
```

**Terminal / CLI-Modus:**
```bash
python FinGPT.py
# Alternativ unter Windows:
scripts\run_cli.bat
```

---

## 🛠️ Erweiterbarkeit & APIs
Das System ist "API-Ready" entwickelt. Dank der modularen `AIAnalyzer`-Klasse können verschiedene Endpunkte (Localhost, OpenAI, Anthropic) einfach parallel geschaltet werden, um Analysen zu vergleichen ("AI Debate Mode").

---

## ⚠️ Disclaimer
*FinGPT ist ein experimentelles System. Automatisierter Handel birgt hohe finanzielle Risiken. Der Autor übernimmt keine Haftung für Verluste. Teste das System IMMER zuerst auf einem Demo-Konto.*

Vollständiger Risikohinweis: [docs/DISCLAIMER](docs/DISCLAIMER)

---
Managed by **EdgarTheGOllam** | Optimized for Privacy & Performance.
