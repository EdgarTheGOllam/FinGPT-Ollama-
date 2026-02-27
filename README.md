# 🤖 FinGPT — Lokales KI-Trading-System für MetaTrader 5

> "Der Markt kann länger irrational bleiben, als du liquide bleiben kannst." — John Maynard Keynes

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
- **Python 3.14+** (Nutzt modernste Syntax-Features).
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
  logs: "C:/Users/edgar/FinGPT/logs"
  data: "C:/Users/edgar/FinGPT/data"
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
3. **Logging:** Überprüfe regelmäßig die Logs unter `C:\Users\edgar\FinGPT\logs`.

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
