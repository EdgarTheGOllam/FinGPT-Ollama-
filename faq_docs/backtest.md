---
icon: history
---

# 📉 Backtest

Testen Sie Ihre Setups mithilfe von Chart-Historie

### Wie funktioniert die Backtest-Engine von MT5 in FinGPT?
FinGPT simuliert Ihre in den Optionen gewählten Parameter (Trading Style, SL/TP Vorgaben, Risikoprofil) auf historischen Kursdaten. Wenn Sie z.B. 6 Monate wählen, geht die Engine Kerze für Kerze durch die MT5-Historie, feuert Kauf-/Verkaufssignale ab (basierend auf der gewählten Strategie) und berechnet das fiktive Kontowachstum mit realen Spreads.

### Auf welche drei Kennzahlen muss ich beim Backtesten primär achten?
1. **Profit Factor**: Beschreibt das Verhältnis von Bruttogewinn zu Bruttoverlust. Alles über 1.5 ist exzellent.
2. **Max Drawdown**: Der größte prozentuale Einbruch Ihres Kontos von einem Hoch zu einem Tief. Er zeigt das wahre Risiko. Ein System mit 50% Rendite aber 40% Drawdown ist hochgefährlich.
3. **Win Rate**: Die Trefferquote. Interessanterweise muss eine Win Rate nicht bei 90% liegen. Gute Trendfolger-Systeme (Breakout-Trading) haben oft nur 40% Winrate, aber sie gewinnen 3x mehr bei einem profitablen Trade als sie bei einem Verlust verlieren (Risk-Reward-Ratio > 1:3).

### Kann ich verschiedene Zeitrahmen im Backtest vergleichen?
Ja, FinGPT ermöglicht Ihnen, denselben Strategie-Set auf verschiedenen Zeitrahmen (M5, M15, H1, H4, D1) zu testen. Oft verhält sich eine Strategie auf dem M15 perfekt, auf dem H1 jedoch katastrophal. Der Vergleich zeigt Ihnen, welcher Zeitrahmen am besten zu Ihrer Risikotoleranz passt.

### Wie realistisch sind die Backtest-Ergebnisse?
Die Engine verwendet reale Spreads vom MT5-Server und simuliert Slippage bei schnellen Marktbewegungen. Allerdings können Backtests niemals zu 100% die Realität abbilden: Extreme Nachrichtenereignisse (Flash Crashes) oder Liquidity Gaps sind oft nur eingeschränkt simulierbar. Nutzen Sie Backtests als Orientierung, nicht als Garantie.

### Welche Datenqualität wird für Backtests benötigt?
FinGPT zieht die Daten direkt von MT5. Stellen Sie sicher, dass Ihr Broker vollständige Tick-Daten oder zumindest-Minute-Bars (M1) für den gewählten Zeitraum archiviert hat. Lücken in der Historie führen zu ungenauen Ergebnissen.
