# Heatmap Fix Plan

## Problem
Die Heatmap zeigt keine Daten an. Nach Analyse des Codes in [`heatmap_tab.py`](gui/views/heatmap_tab.py) wurden folgende Probleme identifiziert:

### Identifizierte Probleme

1. **MT5-Verbindung** (Zeile 119): Der Code versucht MT5 zu initialisieren, aber bei fehlender Verbindung wird kein visuelles Feedback gegeben außer dem Status-Label.

2. **Doppelte Dictionary-Zuweisung** (Zeilen 61 und 68):
   ```python
   # Zeile 61 - überschreibt mit progress-Objekt
   self._strength_bars[curr] = progress
   
   # Zeile 68 - überschreibt mit Dictionary (korrekt)
   self._strength_bars[curr] = {'bar': progress, 'lbl': val_lbl}
   ```
   Dies führt zu Verwirrung im Code, obwohl Zeile 68 den korrekten Wert setzt.

3. **Fehlende Symbole**: Wenn MT5-Symbole nicht verfügbar sind, bleiben die Balken auf 0.

4. **Initialisierungsproblem**: Beim ersten Start könnte das GUI-Update fehlschlagen, weil der Thread startet bevor die GUI vollständig bereit ist.

## Lösungsansatz

### Phase 1: Sofortige Visualisierung
- Heatmap mit Demo-Daten anzeigen, falls MT5 nicht verbunden ist
- Visuelles Feedback verbessern

### Phase 2: Code-Refactoring
- Doppelte Dictionary-Zuweisung entfernen
- Fehlerbehandlung verbessern

### Phase 3: Erweiterte Funktionalität
- Manueller Refresh-Button hinzufügen
- Verbindungsstatus deutlicher anzeigen

## Implementierung

Die Lösung wird in [`gui/views/heatmap_tab.py`](gui/views/heatmap_tab.py) implementiert werden.
