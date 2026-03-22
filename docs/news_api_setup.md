# 📰 FinGPT News API Setup Anleitung

## Übersicht

Der Streamlit News-Tab verwendet mehrere News-Quellen für Echtzeit-Trading-Nachrichten:

1. **NewsAPI.org** - Hauptquelle für Finanznachrichten
2. **Finnhub** - Forex und Krypto News
3. **Alpha Vantage** - Wirtschaftskalender und News
4. **RSS Feeds** - FXStreet, Investing.com, ForexFactory

---

## 🔑 API Key Registration

### 1. NewsAPI.org (Empfohlen)

**URL:** https://newsapi.org/register

**Kostenlos:** 100 Anfragen/Tag (für Entwicklung ausreichend)

```bash
# In .env Datei eintragen:
NEWSAPI_KEY=your_api_key_here
```

**Features:**
- Echtzeit Finanznachrichten
- Sortierung nach Datum
- Mehrsprachig

---

### 2. Finnhub.io (Empfohlen)

**URL:** https://finnhub.io/

**Kostenlos:** 60 API-Anfragen/min

```bash
# In .env Datei eintragen:
FINNHUB_API_KEY=your_api_key_here
```

**Features:**
- Forex News
- Krypto News
- Wirtschaftskalender

---

### 3. Alpha Vantage

**URL:** https://www.alphavantage.co/

**Kostenlos:** 25 Anfragen/Tag

```bash
# In .env Datei eintragen:
ALPHA_VANTAGE_KEY=your_api_key_here
```

**Features:**
- Wirtschaftskalender
- FX Daily Rates
- Krypto Daten

---

## ⚙️ Setup Schritt-für-Schritt

### Schritt 1: .env Datei erstellen

Erstelle eine `.env` Datei im Hauptverzeichnis:

```bash
# FinGPT Environment Variables
NEWSAPI_KEY=your_newsapi_key
FINNHUB_API_KEY=your_finnhub_key
ALPHA_VANTAGE_KEY=your_alphavantage_key
OLLAMA_URL=http://localhost:11434
```

### Schritt 2: Dependencies installieren

```bash
pip install streamlit plotly feedparser requests pandas
```

### Schritt 3: Streamlit App starten

```bash
cd gui/views
streamlit run news_tab_streamlit.py --server.port 8501
```

---

## 🔧 Konfiguration

### Cache Einstellungen

Der News-Tab verwendet einen 5-Minuten Cache:

```python
@st.cache_data(ttl=300, show_spinner=False)
def fetch_and_cache_news(...):
    ...
```

### Auto-Refresh

Aktiviere Auto-Refresh in der UI:

```python
auto_refresh = st.checkbox("🔄 Auto-Refresh (60s)", value=True)
```

---

## 🧪 Test ohne API Keys

Der News-Tab zeigt automatisch Demo-Daten, wenn keine API Keys konfiguriert sind:

```
⚠️ Keine Nachrichten gefunden. Bitte API-Keys konfigurieren.
Erstelle eine .env Datei mit NEWSAPI_KEY, FINNHUB_API_KEY
```

---

## 📊 Ollama Integration (Optional)

Für FinGPT Sentiment Analysis:

1. Ollama installieren: https://ollama.ai/
2. Model herunterladen:
   ```bash
   ollama pull qwen3
   ```
3. Ollama starten:
   ```bash
   ollama serve
   ```

Das Sentiment wird dann mit echter KI analysiert statt nur mit Keywords.

---

## ❓ Fehlerbehebung

### "429 Too Many Requests"
→ API Limit erreicht. Warte oder nutze andere API

### "401 Unauthorized"
→ API Key falsch oder abgelaufen. Prüfe .env

### "Connection Timeout"
→ Keine Internetverbindung oder API nicht erreichbar

### Ollama Fehler
→ Stelle sicher, dass Ollama läuft: `ollama list`

---

## 📝累[Todo: Update .env.example]

Die API Keys sollten in der .env.example dokumentiert werden.
