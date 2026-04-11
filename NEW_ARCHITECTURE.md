# FinGPT - Neue Architektur (Tauri + React + FastAPI)

Dieses Projekt wurde auf eine moderne Desktop-Architektur migriert, um eine hochwertige UI/UX zu bieten, während der bestehende Python-Core erhalten bleibt.

## Architektur-Überblick

Die neue Architektur besteht aus zwei Hauptkomponenten, die lokal auf deinem PC laufen:

1. **Python Core (Backend):** Ein FastAPI-Server, der als API-Brücke zwischen dem React-Frontend und der bestehenden Python-Business-Logik (`core/`, `trading/`, etc.) dient.
2. **Frontend (UI):** Eine moderne React-App (TypeScript, Vite, Tailwind CSS), die entweder im Browser oder idealerweise verpackt in **Tauri** als natives Desktop-Fenster läuft.

### Ordnerstruktur

- `frontend/`: Enthält den gesamten React UI Code.
  - `src/features/`: Modulare React-Features wie das Dashboard.
  - `src/components/`: Wiederverwendbare UI-Elemente (Sidebar, Cards, etc.).
  - `src-tauri/`: Konfiguration für die Tauri Desktop-App.
- `python_core/`: Die neue Heimat für saubere Python-Schnittstellen.
  - `api/main.py`: Der FastAPI Entrypoint.
- `run_backend.py`: Helper-Skript zum Starten des Python-APIs.
- `gui/`: *Alte GUI-Dateien (werden schrittweise durch das Frontend ersetzt).*

---

## Wie starte ich das neue Projekt?

Du benötigst zwei laufende Prozesse (Terminal-Fenster):

### 1. Python Backend starten

Stelle sicher, dass du in deiner virtuellen Umgebung bist und die neuen Abhängigkeiten installiert hast:
```bash
pip install -r requirements.txt
```

Starte den API-Server:
```bash
python run_backend.py
```
*(Der Server läuft nun auf `http://localhost:8000`)*

### 2. Frontend starten

Öffne ein zweites Terminal:
```bash
cd frontend
npm install
```

**Für die Entwicklung im Browser (Vite Dev-Server):**
```bash
npm run dev
```
*(Das Dashboard öffnet sich unter `http://localhost:5173`)*

**Für die native Desktop-App (Tauri):**
*(Hinweis: Erfordert [Rust](https://www.rust-lang.org/tools/install) auf deinem System)*
```bash
npm run tauri dev
```

---

## Nächste Schritte zur Migration
1. **Echte Daten anbinden:** In `python_core/api/main.py` die Mock-Daten durch echte Aufrufe an `core.mt5_broker` oder `core.trading_controller` ersetzen.
2. **Weitere Tabs portieren:** Nach dem Dashboard können "Journal", "Settings" und "Markets" als React-Komponenten in `frontend/src/features/` gebaut werden.
3. **Alte GUI entfernen:** Sobald alle Features abgedeckt sind, kann der `gui/` Ordner gelöscht werden.