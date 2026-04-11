import json
import os

def migrate_user_config(config_path="storage/gui_settings/config.json"):
    """
    Migration-Skript zur Bereinigung der User-Configs:
    1. Entfernt obsoleten "Mica-Effekt" (falls vorhanden).
    2. Fügt "appearance_mode" und "color_theme" als Standards hinzu.
    """
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}. No migration needed.")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        changes_made = False

        # Remove old keys
        keys_to_remove = ["mica_switch", "mica_effect", "glassmorphism"]
        for key in keys_to_remove:
            if key in data:
                del data[key]
                changes_made = True

        # Add new default theme settings if missing
        if "appearance_mode" not in data:
            data["appearance_mode"] = "Dark"
            changes_made = True
            
        if "color_theme" not in data:
            data["color_theme"] = "green"
            changes_made = True

        if changes_made:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Migration erfolgreich: Config wurde aktualisiert.")
            print("Release Notes: 'Windows 11 Mica-Effekt' wurde entfernt, neues Theme-Management hinzugefügt.")
        else:
            print("Migration abgeschlossen: Keine Änderungen erforderlich.")

    except Exception as e:
        print(f"Fehler bei der Migration: {e}")

if __name__ == "__main__":
    migrate_user_config()
