---
icon: mortar-board
---

# 🤖 RL Studio

Lerne, wie die künstliche Intelligenz trainiert wird.

### Was bedeutet Reinforcement Learning im Kontext von FinGPT?
FinGPT nutzt eine Deep Q-Network (DQN) Architektur. Das bedeutet: Wenn Sie das System traden lassen, sammelt es jede Entscheidung (State, Action, Reward) in einer lokalen Datenbank (ExperienceDB). Macht der Agent Gewinn, erhält er einen positiven Reward. Macht er Verlust oder läuft in den Stop-Loss, bekommt er eine starke 'Strafe'. Im RL Studio können Sie die KI aus diesen gesammelten Erfahrungen neu trainieren – das System 'merkt' sich also fehlerhafte Marktstrukturen und lernt, diese in Zukunft zu vermeiden.

### Was bewirkt der Algorithmus 'PPO' vs 'DQN'?
Aktuell nutzt das Grundgerüst von FinGPT einen modifizierten DQN (Deep Q-Network) Ansatz mit Erfahrungswiederholung (Replay Buffer). PPO (Proximal Policy Optimization) ist eine fortgeschrittenere Variante, die oft stabilere Trainingsergebnisse bei kontinuierlichen Aktionsräumen liefert. FinGPT fokussiert sich im ersten Schritt stark auf DQN-basierte diskrete Action-Spaces (Kaufen/Verkaufen/Warten), da diese Logiken für das Forex-Trading sehr robust auswertbar sind.

### Wie nutze ich die Performance-Kennzahlen unten links?
Die Checkbox 'Live RL Performance' zeigt das reale Gesamtergebnis der gesammelten Agenten-Erfahrungen seit dem letzten Zurücksetzen der Datenbank. 
- **Erfahrungen** summiert alle getrackten Trades.
- **Win Rate** gibt den Prozentsatz profitabler Trades an.
- **Stop Losses** zählt, wie oft der SL gerissen wurde – diese Information ist extrem wertvoll, da die Algorithmen beim nächtlichen Retraining genau diese SL Trades fünfmal stärker fokussieren (Prioritized Replay), um aus Schmerz zu lernen.

### Wie lange dauert ein RL-Training?
Die Trainingsdauer hängt von der Anzahl der gesammelten Erfahrungen ab. Typischerweise dauert ein Training mit 10.000+ Erfahrungen 5-15 Minuten auf durchschnittlicher Hardware. Sie können das Training auch im Hintergrund laufen lassen, während Sie mit dem Demo-Konto weiterhandeln.

### Was ist der 'Experience Replay Buffer'?
Der Experience Replay Buffer speichert vergangene Entscheidungen des Agents (State, Action, Reward). Anstatt nur aus den neuesten Trades zu lernen, zieht das System während des Trainings zufällige Batches aus der gesamten Historie. Dies verhindert, dass der Agent nur die neuesten Muster 'auswendig lernt'.

### Kann ich das RL-Modell exportieren und woanders verwenden?
Ja, FinGPT speichert trainierte Modelle im Verzeichnis `storage/rl_agents/`. Sie können diese als `.zip`-Dateien exportieren. Die Modelle sind kompatibel mit der FinGPT-Engine und können theoretisch auch in anderen Python-Projekten mit DQN-Implementierung verwendet werden.

### Wie oft sollte ich das RL-Modell neu trainieren?
Wir empfehlen ein Retraining nach mindestens 500-1.000 neuen Trades oder alle 1-2 Wochen, je nach Handelsaktivität. Zu häufiges Retraining mit zu wenigen Daten führt zu Overfitting – der Agent lernt spezifische Muster, die in der Zukunft nicht mehr funktionieren.
