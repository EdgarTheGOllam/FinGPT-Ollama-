---
---

# 🎭 Debate

Das revolutionäre Multi-Agenten-Diskussionsmodul.

### Wie funktioniert das Debate-Feature (KI-Debatte)?

Der Debate-Mode ist eine der innovativsten Funktionen von FinGPT. Anstatt eine einzige KI nach einer Richtung zu fragen, werden drei separate Instanzen der LLaMa-KI gestartet. 

1. **Bull Analyst**: Erhält die strikte Anweisung, nur Argumente FÜR einen steigenden Kurs zu finden.
2. **Bear Analyst**: MUSS Argumente FÜR einen fallenden Kurs finden.
3. **Judge (Richter)**: Liest beide Plädoyers, wertet die vorliegenden Live-Daten objektiv aus und fällt ein finales, balanciertes Urteil.

### Aus welchem Grund wurde dieses aufwendige Feature entwickelt?

Menschen und oft auch einfache KIs leiden unter dem 'Confirmation Bias' (Bestätigungsfehler): Sobald man eine Meinung hat (z.B. 'Der Euro muss steigen'), übersieht man Warnsignale. Durch das forcierte Gegenüberstellen im Debate-Modus wird die KI gezwungen, auch die Risiken und Gegenargumente (z.B. einen versteckten Widerstand) aufzudecken. Dies senkt Verlusttrades drastisch.

### Kann das System automatisch basierend auf einer Debatte traden?

Im Standard-Auto-Trading nutzt die Engine nur einen Haupt-Analysten zur Geschwindigkeit. Der Debate-Modus ist primär ein manuelles Analysetool für Sie, bevor Sie eine wichtige diskretionäre (manuelle) Handelsentscheidung treffen. Sie können die Empfehlung des Richters manuell im MT5 umsetzen.

### Wie lange dauert eine Debatte?
Eine vollständige Debatte mit drei KI-Instanzen dauert typischerweise 15-30 Sekunden, abhängig von der Ollama-Serverleistung und Ihrer Internetverbindung. Der Bull-Analyst und Bear-Analyst arbeiten parallel, was Zeit spart.

### Kann ich die Debatten-Ergebnisse speichern?
Ja, Sie können jeden Debatten-Report als Textdatei exportieren. Dies ist nützlich für spätere Analyse oder um zu lernen, wie die KI verschiedene Marktsituationen bewertet. Die Berichte enthalten alle Argumente beider Seiten sowie das finale Urteil des Richters.

### Welche Daten werden für die Analyse verwendet?
Die KI-Analysten haben Zugriff auf:
- Aktuelle Kursdaten (Bid/Ask)
- Technische Indikatoren (RSI, MACD, Bollinger Bands)
- Support/Resistance-Levels
- 24-Stunden-Nachrichtenübersicht
- Makroökonomische Kalenderereignisse

### Kann ich die Debatten-Prompts anpassen?
Fortgeschrittene Benutzer können die System-Prompts für Bull, Bear und Judge in den Einstellungen modifizieren. Sie können z.B. festlegen, dass der Bear-Analyst besonders auf Zinsentscheidungen achten soll oder dass der Judge nur bei Übereinstimmung beider Seiten ein starkes Signal geben darf.
