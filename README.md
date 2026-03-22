# 🤖 FinGPT — Lokales KI-Trading-System für MetaTrader 5

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![MetaTrader 5](https://img.shields.io/badge/MetaTrader-5-green.svg)](https://www.metatrader5.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-orange.svg)](https://ollama.ai/)

> "Der Markt kann länger irrational bleiben, als du liquide bleiben kannst." — John Maynard Keynes

FinGPT ist ein professionelles, modulares Trading-Framework, das die Präzision klassischer technischer Indikatoren mit der kognitiven Analyse moderner **Large Language Models (LLMs)** verbindet. Das System agiert als intelligente Brücke zwischen lokalen KI-Instanzen (Ollama) oder Cloud-APIs und der MetaTrader 5 Handelsplattform.

---

## 🌟 Kern-Philosophie
- **100% Local-First:** Kein Datentransfer in die Cloud. Deine Strategien und Trades bleiben dein Geheimnis.
- **Privacy-by-Design:** Volle Kontrolle über deine Finanzdaten.
- **Hybrid-Analyse:** Symbiose aus harten mathematischen Indikatoren und KI-basierter Marktstimmungs-Auswertung.

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
**FinGPT-Ollama** ist ein vollkommen lokales, Privacy-First Trading-System. Es kombiniert klassische technische Analyse mit der Power moderner Large Language Models (LLMs) via **Ollama**, um datengestützte Handelsentscheidungen direkt in **MetaTrader 5** auszuführen.

---

## 🌟 Kern-Philosophie
- **100% Local-First:** Kein Datentransfer in die Cloud. Deine Strategien und Trades bleiben dein Geheimnis.
- **Privacy-by-Design:** Volle Kontrolle über deine Finanzdaten.
- **Hybrid-Analyse:** Symbiose aus harten mathematischen Indikatoren und KI-basierter Marktstimmungs-Auswertung.

---

## 🚀 Hauptmerkmale

| Feature | Beschreibung |
| :--- | :--- |
| **💡 KI-Integration** | Nutzt lokale Modelle (z.B. `fingpt`, `qwen2.5-coder`) via Ollama für Marktprognosen. |
| **📊 Chart-Analyse** | Echtzeit-Auswertung von RSI, MACD, Moving Averages und dynamischen S/R-Zonen. |
| **🛡️ Risk Management** | Automatische Lot-Berechnung basierend auf Risk-Percentage, Trailing-Stops & Break-Even. |
| **🖥️ Modern GUI / CLI** | Flexibilität zwischen einem mächtigen Terminal-Menü und einer modernen Benutzeroberfläche. |
| **🌙 Asynchrone Engine** | Optimiert für stabile Ausführung, auch bei nächtlichen Workflows. |
| **📝 Audit Logging** | Detaillierte Historie mit Kategorisierung (TRADE, AI, SYSTEM, ERROR). |

---

## 🛠️ Installation

### 1. Voraussetzungen
- **Windows 11** (empfohlen für volle MT5-Kompatibilität).
- **Python 3.9+** (empfohlen: 3.10-3.12 für beste Kompatibilität).
- **Ollama:** Installiert und konfiguriert (`OLLAMA_ORIGINS=*`).
- **NVIDIA GPU:** Empfohlen (RTX 4080 Kapazitäten werden optimal genutzt).

### 2. Repository klonen
```bash
git clone https://github.com/EdgarTheGOllam/FinGPT-Ollama-.git
cd FinGPT-Ollama-
```

### 3. Umgebung einrichten
Wir empfehlen die manuelle Pfad-Konfiguration für maximale Kontrolle:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Modelle laden
Stelle sicher, dass deine lokalen Modelle bereit sind:
```bash
ollama pull fingpt
ollama pull qwen2.5-coder:32b # Oder dein bevorzugtes Model
```

---

## ⚙️ Konfiguration (`config.yaml`)

Passe das System an deine Infrastruktur an. **Hinweis:** Nutze manuelle Pfade für volle Transparenz.

```yaml
mt5:
  login: 12345678
  password: "dein_sicheres_passwort"
  server: "Dein-Broker-Server"

ollama:
  model: "fingpt"
  host: "http://localhost:11434"

trading:
  risk_percent: 1.0
  symbols: ["EURUSD", "BTCUSD", "XAUUSD"]
  timeframes: ["M15", "H1"]

paths:
  logs: "logs/"
  data: "storage/"
```

---

## 📈 Nutzung

### Start der Haupt-Engine
```bash
python FinGPT.py
```

### Start der Modernen GUI
```bash
python launch_gui.py
```

### Workflow-Empfehlung
1. **Demo-Testing:** Nutze das System zuerst im Demo-Modus deines MT5-Kontos.
2. **KI-Check:** Vergleiche die KI-Vorschläge mit deinem eigenen Chart-Audit.
3. **Logging:** Überprüfe regelmäßig die Logs im `logs/` Verzeichnis.

---

## 🗺️ Roadmap / Geplante Features
- [ ] **Docker-Support:** Containerisierung für noch einfacheres Deployment.
- [ ] **ComfyUI Integration:** Generierung von visuellen Chart-Reports via Stable Diffusion.
- [ ] **Backtesting-Modul:** Simulation historischer Daten mit KI-Logik.
- [ ] **3D-Druck-Alerts:** Integration von Status-Meldungen auf deinem Flashforge Adventurer 5M.

---

## 🤝 Mitwirken
Beiträge sind willkommen! 
1. Fork das Projekt.
2. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`).
3. Commit deine Änderungen (`git commit -m 'Add some AmazingFeature'`).
4. Push den Branch (`git push origin feature/AmazingFeature`).
5. Öffne einen Pull Request.

---

## ⚠️ Disclaimer (Haftungsausschluss)
**Der Handel mit Finanzinstrumenten ist mit erheblichen Risiken verbunden.** Dieses System ist ein experimentelles Tool. Es übernimmt keine Garantie für Gewinne. Der Autor übernimmt keine Haftung für finanzielle Verluste. Die Nutzung erfolgt auf eigene Gefahr. Teste das System **immer** zuerst in einer sicheren Umgebung (Demo-Konto).

---

## 📄 Lizenz
Dieses Projekt ist unter der **MIT-Lizenz** lizenziert. Siehe die `LICENSE` Datei für Details.

---
*Entwickelt mit ❤️ für lokale KI und finanzielle Freiheit.*
