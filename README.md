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
├── core/           # Herzstück: Broker-Anbindung, AI-Logik & Datenverarbeitung
├── trading/        # Strategien: RL-Agents, Risiko-Management & Indikatoren
├── gui/            # Frontend: Modernes Dashboard & CLI-Komponenten
├── bridge/         # Technische Schnittstellen (MQL5-Python Bridge)
├── config/         # Konfiguration: Backups, API-Keys & Trade-Parameter
└── storage/        # Datenbanken: Trade-History, Logs & RL-Modelle
```

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
  Trage deinen **OpenAI API Key** oder andere Provider in der `config/fingpt_config.json` ein, um High-End-Modelle wie GPT-4o für tiefergehende Marktanalysen zu nutzen.

### 3. System starten
```bash
python launch_gui.py
```

---

## 🛠️ Erweiterbarkeit & APIs
Das System ist "API-Ready" entwickelt. Dank der modularen `AIAnalyzer`-Klasse können verschiedene Endpunkte (Localhost, OpenAI, Anthropic) einfach parallel geschaltet werden, um Analysen zu vergleichen ("AI Debate Mode").

---

## ⚠️ Disclaimer
*FinGPT ist ein experimentelles System. Automatisierter Handel birgt hohe finanzielle Risiken. Der Autor übernimmt keine Haftung für Verluste. Teste das System IMMER zuerst auf einem Demo-Konto.*

---
Managed by **EdgarTheGOllam** | Optimized for Privacy & Performance.
