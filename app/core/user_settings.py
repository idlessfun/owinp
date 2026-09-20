r"""
OWINP Client User Settings.

Stores the selected theme and interface settings.
Saved to %APPDATA%\OWINP\settings.json

Security:
- The file does not contain any secrets
- Stored locally
- If missing, default values are used
"""

import json
import os
from pathlib import Path


APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
SETTINGS_DIR = APPDATA / "OWINP"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


# ---------- Ready-made themes ----------
THEMES = {
    "dark-blue": {
        "name": "🌙  Dark-blue",
        "background": "#1e1f22",
        "sidebar":    "#17181b",
        "card":       "#24262b",
        "border":     "#2f3138",
        "accent":     "#7c9cff",
    },
    "dark-red": {
        "name": "🔴  Dark-red",
        "background": "#1a0d12",
        "sidebar":    "#12080c",
        "card":       "#261218",
        "border":     "#3a1a22",
        "accent":     "#ff5577",
    },
    "dark-green": {
        "name": "🟢  Dark-green",
        "background": "#0f1a14",
        "sidebar":    "#08120d",
        "card":       "#16241d",
        "border":     "#1f362a",
        "accent":     "#5adb8a",
    },
    "dark-purple": {
        "name": "🟣  Dark-purple",
        "background": "#150f1f",
        "sidebar":    "#0d0814",
        "card":       "#1d1429",
        "border":     "#2c1e3d",
        "accent":     "#b388ff",
    },
    "light": {
        "name": "☀️  Light",
        "background": "#f5f5f7",
        "sidebar":    "#e8e8ec",
        "card":       "#ffffff",
        "border":     "#d0d0d5",
        "accent":     "#3b6fd9",
    },
}


DEFAULT_THEME = "dark-blue"
FONT_SIZES = [12, 14, 16, 18]


# All client settings with default values
DEFAULTS = {
    "theme": DEFAULT_THEME,              # Selected theme
    "font_size": 14,                     # font size
    "check_updates_on_start": True,      # Check for updates at startup
    "refresh_catalog_on_start": True,    # Update the catalog on startup
    "auto_run_after_download": False,    # Run the file after downloading it
    "show_update_banner": True,          # Display the “Update Available” banner
    "compact_mode": False,               # Compact mode (fewer cards)
    "animations_enabled": True,          # animations (placeholder—to be added later)
    "show_screenshots": True,            # Display screenshots on the program page
    "language": "en",
}


def load_user_settings() -> dict:
    """Loads the settings. If the file does not exist, the default settings are used."""
    if not SETTINGS_FILE.exists():
        return dict(DEFAULTS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = dict(DEFAULTS)
        result.update(data)
        return result
    except Exception as e:
        print(f"[user_settings] Loading error: {e}")
        return dict(DEFAULTS)


def save_user_settings(settings: dict) -> bool:
    """Saves the settings."""
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print(f"[user_settings] Saved: {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"[user_settings] Save error: {e}")
        return False


def get_user_settings_path() -> Path:
    """Returns the path to the settings file."""
    return SETTINGS_FILE


def get_theme(theme_id: str) -> dict:
    """Returns a dictionary containing the theme colors."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])