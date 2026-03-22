---
icon: graph
---

# 📈 Charts

Hochentwickelte Visualisierungswerkzeuge aus dem Charting-Bereich.

### Welche Chart-Typen stehen zur Verfügung und wofür nutze ich sie?

FinGPT bietet vier hochspezialisierte Chart-Ansichten:

1. **Multi-View**: Ein Split-Screen für den ganz schnellen Überblick über bis zu 6 Major-Paare gleichzeitig. Ideal um Markt-Korrelationen (z.B. EURUSD vs. GBPUSD) sofort zu erkennen.
2. **Pattern Scanner**: Ein algorithmisches Tool zur Erkennung von über 15 klassischen Kerzenmustern (wie Engulfing, Doji, Morning Star). Die Muster werden direkt im Chart hervorgehoben.
3. **Advanced Analysis**: Ein ausgewachsenes Charting-Tool für detaillierte Setup-Suchen. Fügen Sie eigene Indikatoren (RSI, Bollinger Bands, Moving Averages) hinzu. Die KI kann auf Knopfdruck eine detaillierte Auswertung exakt dieses Charts vornehmen.
4. **SMC Scanner**: Maßgeschneidert für Smart Money Concepts (SMC). Dieses Tool identifiziert automatisch institutionelle Support/Resistance-Levels (Order Blocks), Breaks of Structure (BoS) und Trendwenden (Change of Character, ChoCH).

### Wie genau funktioniert der Pattern Scanner?

Wählen Sie ein Währungspaar und einen Zeitrahmen (z.B. H1). Wenn Sie auf 'Markt Scannen' klicken, lädt FinGPT die neuesten Bar-Daten aus MetaTrader. Ein Muster-Erkennungs-Algorithmus sucht nach mathematischen Formationen (Candlesticks). Jedes gefundene Muster wird mit einer Stern-Bewertung (Relevanz-Faktor) versehen. Ein 5-Sterne 'Bullish Engulfing' an einem Support-Level ist ein extrem starkes Signal.

### Was ist der 'SMC Scanner' und wie hilft er mir?

SMC (Smart Money Concepts) basiert auf der Annahme, dass große Banken und Institutionen Spuren im Chart hinterlassen. Der Scanner sucht nicht nach klassischen Indikatoren wie dem RSI, sondern nach Marktstruktur: Wo liegen große ungetestete Order-Blöcke? Wo wurde eine alte Struktur gebrochen (Liquidity Sweep)? Der Scanner zeichnet diese kritischen Zonen automatisch rot (Supply/Widerstand) oder grün (Demand/Unterstützung) ein. Es ist ideal, um Trades an genau den Punkten zu platzieren, an denen Banken das Geld drehen.

### Kann ich eigene Indikatoren zu den Charts hinzufügen?
Ja, im Advanced Analysis Modus haben Sie volle Freiheit. Sie können Standard-Indikatoren wie RSI, MACD, Bollinger Bands, Stochastic Oscillator oder gleitende Durchschnitte (SMA, EMA) hinzufügen. Zusätzlich können Sie eigene, benutzerdefinierte Indikatoren über Python-Skripte integrieren, sofern diese mit MetaTrader 5 kompatibel sind.

### Wie aktualisieren sich die Charts in Echtzeit?
Die Charts werden live mit dem MT5-Server synchronisiert. Neue Kerzen erscheinen automatisch, sobald der Broker neue Preisdaten liefert. Bei hoher Volatilität (z.B. während Nachrichten) können Sie die Aktualisierungsfrequenz in den Einstellungen anpassen (von 1 Sekunde bis 1 Minute).

### Welche Zeitrahmen werden unterstützt?
FinGPT unterstützt alle gängigen Zeitrahmen: M1 (1 Minute), M5, M15, M30, H1 (1 Stunde), H4, D1 (Täglich), W1 (Wöchentlich). Für Scalping empfehlen wir M5, für Swing-Trading H1 oder H4.

### Kann ich Chart-Screenshots speichern?
Ja, Sie können jeden Chart als Bilddatei (PNG) exportieren. Dies ist nützlich für Dokumentation, Analysen oder um Setups mit anderen zu teilen. Die Screenshots enthalten alle gezeichneten Indikatoren und Markierungen.
