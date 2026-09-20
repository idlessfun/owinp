"""
JSON card loader for programs.

It first attempts to read cached JSON files
from the cache (downloaded from GitHub).
If there is no cache, it reads the built-in JSON files from app/apps/.
"""

import json
from pathlib import Path

from app.core.cache_manager import cache_exists_for_lang, load_cached_apps
from app.core.user_settings import load_user_settings


APPS_DIR = Path(__file__).parent.parent / "apps"


def load_all_apps() -> list[dict]:
    """
    Returns a list of all programs.

    Priority:
    1. Cache for the current language — if available
    2. Cache for English — as a fallback
    3. Built-in (app/apps/<lang>/) — as a last resort
    """
    # Get the current language
    try:
        settings = load_user_settings()
        lang = settings.get("language", "en")
    except Exception:
        lang = "en"

    # Try the cache for the current language
    if cache_exists_for_lang(lang):
        cached = load_cached_apps(lang)
        if cached:
            print(f"[app_loader] Loaded from the cache ({lang}): {len(cached)} items")
            return cached

    # Cache is empty — use the built-in ones
    print("[app_loader] The cache is empty—we'll use the built-in directory")
    return load_builtin_apps()


def load_builtin_apps() -> list[dict]:
    """
    Reads JSON files from the built-in app/apps/<lang>/ folder.

    Priority:
    1. Current UI language folder (app/apps/<lang>/)
    2. English folder (app/apps/en/) as a fallback
    3. Old flat structure (app/apps/*.json) for compatibility

    Returns a list of dictionaries. Ignores corrupted files.
    """
    if not APPS_DIR.exists():
        print(f"[app_loader] Folder not found: {APPS_DIR}")
        return []

    # Get the current language
    try:
        settings = load_user_settings()
        lang = settings.get("language", "en")
    except Exception:
        lang = "en"

    # Try the folder of the current language
    lang_dir = APPS_DIR / lang
    apps = _read_apps_from_dir(lang_dir, label=f"built-in [{lang}]")

    # Fallback to English
    if not apps and lang != "en":
        en_dir = APPS_DIR / "en"
        apps = _read_apps_from_dir(en_dir, label="built-in [en] (fallback)")

    # Fallback to the old flat structure (JSON directly in app/apps/)
    if not apps:
        apps = _read_apps_from_dir(APPS_DIR, label="built-in [legacy]")

    return apps


def _read_apps_from_dir(directory: Path, label: str = "built-in") -> list[dict]:
    """
    Reads all *.json files from the given directory.
    Helper for load_builtin_apps.
    """
    apps: list[dict] = []

    if not directory.exists():
        return apps

    for json_file in sorted(directory.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            apps.append(data)
            print(f"[app_loader] Loaded ({label}): {json_file.name}")
        except json.JSONDecodeError as e:
            print(f"[app_loader] Error in the file {json_file.name}: {e}")
        except Exception as e:
            print(f"[app_loader] Failed to read {json_file.name}: {e}")

    return apps