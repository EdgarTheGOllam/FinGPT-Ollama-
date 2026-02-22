# 🤖 FinGPT – KI‑gestütztes Trading‑System für MetaTrader 5

> "Der Markt kann länger irrational bleiben, als du liquide bleiben kannst." – John Maynard Keynes

Ein vollständig lokales, Python‑basiertes Trading‑System, das klassische technische Indikatoren mit großen Sprachmodellen (LLMs) über **Ollama** kombiniert und über die MetaTrader 5‑API (MQL5‑Bridge) ausführt.

## 📌 Überblick

| Feature | Kurzbeschreibung |
| ------- | ----------------- |
| **Technische Indikatoren** | RSI, MACD, dynamische Support/Resistance, Multi‑Timeframe‑Analyse |
| **Risikomanagement** | Lot‑Berechnung nach Risiko‑% → automatischer Lot‑Scaler, Trailing‑Stops, Partial‑Close, Magic‑Number |
| **KI‑Integration (Ollama)** | Modelle: `fingpt`, `llama3`, `mistral` (Fallback). Analyse von Indikatoren + Chart‑Struktur, Ausgabe in Deutsch inkl. Confidence‑Score |
| **Auto‑Trading Engine** | Pipeline: Trend → RSI → MACD → S/R → KI → Order‑Platzierung, Symbol‑Rotation, Fehlertoleranz |
| **CLI‑Menü** | 16‑Punkte‑Menu für Daten, KI‑Analyse, Auto‑Trading, Indikatoren‑Einstellungen, Logging, … |
| **Logging** | Strukturierte Logs (`SYSTEM`, `TRADE`, `AI`, `ERROR` …) mit Emojis, tägliche Log‑Dateien |
| **Offline‑First** | Alles läuft **lokal** – keine Cloud‑Abhängigkeiten, nur Ollama & MetaTrader 5. |

## 🚀 Installation

### 1. System‑Voraussetzungen
- **Python** ≥ 3.9 (empfohlen 3.11)
- **MetaTrader 5** (Demo‑ oder Live‑Konto)
- **Ollama** – Modelle `fingpt`, `llama3`, `mistral` lokal installiert
- **Git** für das Klonen des Repos

### 2. Repository klonen
```bash
git clone https://github.com/EdgarTomas2001/FinGPT-Ollama-.git
cd FinGPT-Ollama-
```

### 3. Python‑Abhängigkeiten installieren
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```
> **Hinweis:** Alle Pakete sind bereits vorkonfiguriert – keine zusätzlichen Installationen nötig.

### 4. Ollama‑Umgebung konfigurieren
```bash
ollama pull fingpt
ollama pull llama3
ollama pull mistral
```
Falls du die Ollama‑API von einem anderen Prozess nutzt, setze:
```bash
export OLLAMA_ORIGINS=*   # Linux/macOS
set OLLAMA_ORIGINS=*      # Windows CMD
```

### 5. MetaTrader 5‑Verbindung prüfen
```python
import MetaTrader5 as mt5
if not mt5.initialize():
    print("MT5‑Initialisierung fehlgeschlagen")
else:
    print("MT5 erfolgreich verbunden")
    mt5.shutdown()
```

### 6. Konfigurationsdatei anlegen (`config.yaml`)
```yaml
mt5:
  login: 12345678
  password: "dein_passwort"
  server: "Demo-Server"

ollama:
  model: "fingpt"
  endpoint: "http://127.0.0.1:11434/api/generate"

risk:
  risk_percent: 1.0
  trailing_stop:
    start: 20
    step: 5

paths:
  logs: "./logs"
  data: "./data"
```
> Passe die Werte nach deinen Bedürfnissen an.

## 📚 Nutzung
```bash
python main.py
```
Im interaktiven Menü kannst du Daten laden, KI‑Analysen starten, Auto‑Trading aktivieren und Einstellungen ändern. Vor dem Live‑Handel immer im Demo‑Modus testen – das Menü fragt explizit nach einer Bestätigung.

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
