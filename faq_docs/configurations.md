---
icon: gear
---

# ⚙️ Konfigurationen

Wie Sie den Bot auf Ihre Vorlieben einstellen.

### Wie beeinflussen die verschiedenen 'Trading Styles' das System konkret?

Wir haben 7 unterschiedliche Stile implementiert, die drastische Auswirkungen auf die Engine haben:

**Scalping:** Arbeitet extrem kurzfristig. Das System liest nur den 5-Minuten-Chart (M5). Es setzt extrem enge Stop-Losses (z.B. 10 Pips) und Take-Profits. Ideal für Phasen hoher Liquidität (London Open), aber riskant bei hohem Spread.  
**Day Trading:** Der Allrounder. Nutzt den M15-Chart. Trades zielen darauf ab, den übergeordneten Tagestrend mitzunehmen und werden idealerweise noch vor Mitternacht geschlossen.  
**Swing Trading:** Analysiert den H1-Chart. Sucht nach mehrtägigen Bewegungen und Schwüngen. Ein einzelner Trade kann enorme Gewinne erzielen, erfordert aber viel Geduld und weitaus größere Stop-Loss Abstände, um nicht durch Rauschen ausgestoppt zu werden.  
**Position Trading:** Betrachtet H4 oder gar D1 Charts. Das absolute Langfrist-System, reagiert kaum auf tägliche Nachrichten, sondern auf makroökonomische Trends über Wochen.  
**Price Action:** Ignoriert laggy (nachhinkende) Indikatoren wie den MACD stark und konzentriert sich auf das nackte Chart, Kerzenkörper, Dochte und Widerstandslinien auf dem M15.  
**Breakout-Trading:** Sucht gezielt nach langen Phasen enger Range (Konsolidierung) auf dem H1-Chart und platziert Trades genau dann, wenn der Kurs explosiv aus diesem Block ausbricht.  
**Mean Reversion:** Das antizyklische Modell. Die Engine sucht nach extrem starken Übertreibungen (Preis viel zu weit entfernt vom glättenden EMA) auf dem M15-Chart und wettet mit engen Stops darauf, dass der Markt wie ein Gummiband zur Mitte (Mean) zurückschnellt.

### Inwiefern unterscheiden sich die Signal-Strategien (KI vs. Hybrid vs. Technical)?

- Wenn Sie **Technische Indikatoren** wählen, feuert die Engine Trades stur nach Mathe-Regeln ab (z.B. RSI < 30 = BUY). Dies ist sehr schnell, aber fehleranfällig in Seitwärtsphasen. 
- **KI-gesteuert** nutzt primär Ollama LLaMa-Modelle, um das Gesamtbild prosahaft auszuwerten. 
- **Hybrid (KI + Indikatoren)** filtert zuerst mathematisch strikt vor und lässt nur Setups zu, die auch von der KI als logisch bewertet und per Prompt abgesegnet werden.
