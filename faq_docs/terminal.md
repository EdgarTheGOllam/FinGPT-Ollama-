---
icon: terminal
---

# 💻 Terminal

Das Entwickler-Terminal von FinGPT

### Warum blitzt das Terminal so extrem schnell und was sagen die Codes aus?

Das Terminal gewährt Ihnen Entwickler-Einsicht (Debug Level). 

- Code `[DEBUG]` oder blauer Text bedeutet Informationsfluss (z.B. 'Verbindungscheck erfolgreich').
- Ein gelbes `[WARN]` bedeutet, dass etwas vermieden wurde (z.B. 'Trade abgebrochen, da Spread > 1.5 Pips').
- Ein rotes `[ERROR]` erfordert Aufmerksamkeit (z.B. 'Lot-Größe überschreitet Margin' oder 'Verbindung zu Ollama verloren').
- `[RL ADAPTIV]` ist besonders wichtig: Das bedeutet, dass der Machine Learning Agent eingegriffen und ein klassisches Indikatoren-Signal basierend auf seinen Fehler-Erfahrungen annulliert hat.

### Löscht sich das Terminal selbst?

Ja, um Arbeitsspeicher (RAM) zu sparen und die Performance der GUI nicht zu gefährden, kürzt das Terminal seinen Inhalt gelegentlich automatisch. Wichtige strategische Meilensteine (Trade Entries) sind aber dauerhaft im Journal und in der ExperienceDB gespeichert.
