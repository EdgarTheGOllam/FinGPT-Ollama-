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

### Kann ich das Terminal-Log in eine Datei speichern?
Ja, Sie können den gesamten Terminal-Output als Textdatei exportieren. Dies ist nützlich für Fehleranalyse oder um das Verhalten in bestimmten Marktsituationen später zu untersuchen. Die Funktion finden Sie im Kontextmenü (Rechtsklick auf das Terminal).

### Was bedeuten die verschiedenen Farben im Terminal?
- **Blau**: Informative Meldungen, Debug-Informationen
- **Grün**: Erfolgreiche Operationen (Verbindung hergestellt, Trade ausgeführt)
- **Gelb**: Warnungen (z.B. hoher Spread, Trade übersprungen)
- **Rot**: Fehler (Verbindungsprobleme, nicht genug Margin)
- **Weiß/Grau**: Normale Statusmeldungen

### Wie detailliert kann ich die Logging-Stufe einstellen?
In den Einstellungen können Sie zwischen verschiedenen Log-Leveln wählen:
- **Minimal**: Nur kritische Fehler
- **Normal**: Warnungen und wichtige Events
- **Verbose**: Detaillierte Debug-Informationen
- **Entwickler**: Alle Nachrichten inkl. technischer Details

### Kann ich die Terminal-Schriftgröße ändern?
Ja, über die GUI-Einstellungen können Sie die Schriftgröße des Terminals anpassen (klein, mittel, groß). Dies ist besonders nützlich bei hochauflösenden Bildschirmen.
