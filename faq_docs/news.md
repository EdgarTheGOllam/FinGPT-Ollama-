---
icon: note
---

# 📰 News

Echtzeit-Meldungen, die die Finanzmärkte bewegen.

### Woher bezieht FinGPT die Echtzeit-Finanznews?
Das System nutzt RSS-Aggregatoren (XML-Schnittstellen) von Top-Finanzportalen wie FXStreet, MarketWatch, Bloomberg-Feeds und LiveSquawk. Es werden hunderte Nachrichten pro Stunde gefiltert und nach Relevanz sortiert.

### Warum ist der 'News-Filter' Schalter in den Optionen so wichtig?
Makroökonomische Nachrichten (wie US-Zinsentscheide (FOMC) oder Arbeitsmarktdaten (NFP)) verursachen massive, unvorhersehbare Kurssprünge innerhalb von Millisekunden. Solche Volatilitäts-Spikes reißen selbst die besten technischen Setups und Stop-Losses ein. Wenn der News-Filter aktiv ist, stoppt FinGPT das automatische Eingehen neuer Trades in den Minuten rund um solche wichtigen Meldungen.

### Welche Nachrichtenquellen werden verwendet?
FinGPT aggregiert Nachrichten aus folgenden Quellen:
- FXStreet
- Investing.com
- MarketWatch
- Bloomberg (via RSS)
- Reuters
- ForexFactory

### Kann ich bestimmte Nachrichtenarten filtern?
Ja, Sie können einstellen, welche Nachrichtentypen relevant sind:
- Zinsentscheidungen
- BIP-Daten
- Arbeitsmarktberichte
- Inflationsdaten (CPI, PPI)
- Geopolitische Ereignisse

### Wie weit im Voraus warnt das System vor wichtigen Nachrichten?
Das System zeigt einen Kalender mit den wichtigsten anstehenden Ereignissen. Sie können einstellen, wie viele Minuten vor einer Nachricht der Trading-Stopp beginnen soll (typischerweise 15-30 Minuten).

### Was passiert, wenn eine Nachricht während eines offenen Trades veröffentlicht wird?
Falls Sie bereits eine offene Position haben und eine wichtige Nachricht erscheint, trifft FinGPT eine Entscheidung basierend auf Ihren Risikoeinstellungen:
- Sofortiger Schluss der Position
- Verengung des Stop-Loss
- oder keine Aktion (wenn Sie manuell eingestiegen sind)
