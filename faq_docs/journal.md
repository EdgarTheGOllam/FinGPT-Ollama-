---
icon: book
---

# 📝 Journal

Das Trade Journal speichert Ihre Trading-Historie.

### Welche Details werden im Trade Journal festgehalten?
Das Journal speichert jeden abgeschlossenen Trade samt Ticket-Nummer, Währungspaar, Datum und dem realisierten Profit in Euro. Exklusiv in FinGPT wird zudem der **'AI Context'** gespeichert: Dies ist die exakte Begründung, warum die KI an diesem Tag eingestiegen ist (z.B. 'RSI überverkauft + Bullish Engulfing erkannt').

### Warum ist das Journaling für meinen Erfolg so wichtig?
Ein detailliertes Journal trennt professionelle Trader von Spielern. Ohne Aufzeichnung können Sie Fehler nicht reproduzieren. Durch das Mitprotokollieren der KI-Begründung können Sie später analysieren: 'Immer wenn die KI wegen RSI tradet, mache ich Gewinn, aber wenn sie wegen MACD tradet, verliere ich.' So können Sie Ihr System feintunen.

### Wo liegen diese Daten physisch?
Die Daten werden als saubere, strukturierte JSON-Dateien lokal auf Ihrer Festplatte im Verzeichnis `storage/trade_journal/` abgelegt. Es findet kein Cloud-Upload statt. Ihre Handelsdaten bleiben zu 100% anonym und auf Ihrem Rechner.

### Kann ich das Journal nach bestimmten Kriterien filtern?
Ja, das Journal bietet vielfältige Filteroptionen:
- Nach Datum (bestimmter Zeitraum)
- Nach Symbol (EURUSD, GBPJPY, etc.)
- Nach Gewinn/Verlust
- Nach Trading-Stil
- Nach KI-Reasoning (warum die KI den Trade eingegangen ist)

### Wie exportiere ich meine Handelshistorie?
Sie können das gesamte Journal als CSV-Datei exportieren, die Sie dann in Excel oder anderen Programmen weiterverarbeiten können. Dies ist nützlich für Steuerzwecke oder detaillierte Performance-Analysen.

### Was bedeutet der 'AI Confidence' Wert im Journal?
Der AI Confidence-Wert zeigt, wie sicher sich die KI bei diesem spezifischen Trade war (0-100%). Ein Wert über 70% bedeutet, dass die KI sehr überzeugt vom Setup war. Interessanterweise korreliert ein hoher Confidence-Wert nicht immer mit Profit – es ist dennoch ein wertvoller Lernindikator.

### Kann ich Notizen zu Trades hinzufügen?
Ja, Sie können jedem Trade manuelle Notizen hinzufügen. Dies ist besonders nützlich, wenn Sie z.B. manuell in einen Trade eingegriffen haben oder besondere Umstände bemerkt haben, die die KI nicht berücksichtigen konnte.
