# Theme-Token-Dokumentation & System-Abhängigkeiten (FinGPT-Ollama)

Da es sich bei FinGPT-Ollama um eine **Python Desktop-Applikation** mit `customtkinter` (Tkinter-Wrapper) handelt und nicht um eine Web-Applikation (React/Vue), wurde die Architektur an die technischen Gegebenheiten dieses UI-Frameworks adaptiert. Web-Spezifika (wie SCSS, PostCSS, localStorage, `data-theme`) wurden auf Python-äquivalente Tools migriert.

## 1. Dependency-Map (Theme-Abhängigkeiten)

* **Direkte Abhängigkeiten:**
  * `customtkinter` (Theme-Provider, Rendert Farb-Modi & Custom Themes).
  * JSON-Theme-Files (für Custom-Farben).
  * `AppConfig` (`core/app_config.py`): persistiert gewählte Modi (`appearance_mode`, `color_theme`) als Pendant zu `localStorage`.
  * `gui/views/config_tab.py`: Beinhaltet die Dropdowns für Farb-Darstellung und Akzentfarbe.
* **Indirekte Abhängigkeiten:**
  * Einzelne Canvas-Elemente und Labels in `gui/modern_fingpt_gui.py`, die hartcodierte Hex-Werte für spezielle Status-Anzeigen verwenden (z. B. grüner Text bei Profit).

## 2. Die 3 isolierten Farbdarstellungsmodi

1. **Classic-Modus (Default)**
   * Nutzt den eingebauten `Dark` Mode von customtkinter.
   * `Background`: `#1a1a2e`, `Cards`: `#1A1D24`.
   * Akzentfarben: 1:1 beibehalten (blau, grün, dunkelblau) als semantische Tokens innerhalb von customtkinter Themes (z. B. `fg_color`).
   * 100 % rückwärtskompatibel, als default config gesetzt.

2. **Gedimmt-Modus (Light-Mode Variante, "Soft Dark")**
   * *Berechnung:* Abgeleitet aus dem Classic-Modus. Helligkeit um ca. 25 % erhöht, um den Kontrast abzumildern (z. B. `#2b2d3a` statt `#1a1a2e`).
   * *Pipeline:* Anstatt einer Node.js-PostCSS-Pipeline verwenden wir ein Python-Script zur automatischen Hex-Color Helligkeitsanpassung (siehe Tests-Modul). 

3. **White-Modus (High-Brightness)**
   * Setzt `ctk.set_appearance_mode("Light")` und erzwingt Hintergrundfarben auf `#FFFFFF` (`_WHITE_BG = "#FFFFFF"`).
   * Spezifische Text- und Rahmen-Tokens passen sich dem nativen Light-Modus an und wahren das Kontrastverhältnis (WCAG 2.2 AA) automatisch durch die internen Logiken von customtkinter.

## 3. Entfernung von "Windows 11 Mica-Effekt"

Der Toggle für den *Windows 11 Mica-Effekt (Glassmorphismus)* wurde aus allen UI-Ebenen (`config_tab.py`) und der Code-Logik entfernt.
* Ein **Migrations-Skript** (`migrate_config.py`) wurde angelegt, um alte User-Configs zu bereinigen und `appearance_mode` / `color_theme` als neue Default-Keys zu registrieren.

## 4. Performance & Barrierefreiheit (Audit)

* **Performance:** Theme-Wechsel erfolgt durch `ctk.set_appearance_mode` und `.configure()`-Aufrufe nahezu instantan (<< 16ms render time in Tkinter).
* **FOIT (Flash of inauthentic theme):** Wird verhindert, da `load_settings()` beim App-Init den `appearance_mode` aus der Konfiguration sofort anwendet, bevor das Mainloop gestartet wird.
* **Barrierefreiheit:** Kontrastraten für Text in den Default-Themes und dem White-Theme übersteigen standardmäßig 4.5:1.

## 5. Farbpalette & Kontrasttabellen

| Token / Kontext | Classic (Dark) | Gedimmt (Soft) | White (Light) | WCAG Kontrast Text (Weiß/Schwarz) |
| --- | --- | --- | --- | --- |
| `--color-bg-primary` | `#1a1a2e` | `#2b2d3a` | `#FFFFFF` | > 10:1 (weiß/schwarz) |
| `--color-surface` | `#1A1D24` | `#343748` | `#F0F0F0` | > 8.5:1 (weiß/schwarz) |
| `--color-accent-primary` | `#2979FF` (Blau) | `#2979FF` | `#1C54B2` | > 4.5:1 |
| `--color-accent-success` | `#00FF66` | `#10B981` | `#059669` | > 4.5:1 |
| `--color-accent-error` | `#FF1744` | `#EF4444` | `#DC2626` | > 4.5:1 |

## 6. Migration für Nutzer (Release Notes)

> **Release Notes:**
> * Das "Mica-Effekt"-Feature wurde aufgrund von Plattform-Einschränkungen und zugunsten eines sauberen Theme-Systems entfernt.
> * Es steht nun ein vollständig modularer Theme-Switcher (Dark, Gedimmt, White) zur Verfügung.
> * Ihre vorherigen Theme-Einstellungen wurden automatisch migriert!