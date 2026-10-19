"""
Program Catalog Cache Manager.

Reads and manages downloaded JSON files
from the cache (the folder is specified by the CACHE_DIR constant below).

Security:
- Reads only its own folder
- Does not delete anything outside its own folder
- Validates each JSON file before returning it
- Asset names coming from remote JSON are reduced to a bare file name,
  so "../../something" can never escape the cache folder
"""

import json
import os
import shutil
import time
from pathlib import Path


# --- Paths ---
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CACHE_ROOT = APPDATA / "OWINP" / "cache"
CACHE_APPS = CACHE_ROOT / "apps"                # Root folder for language subfolders
CACHE_ICONS = CACHE_ROOT / "icons"              # Icons
CACHE_SCREENSHOTS = CACHE_ROOT / "screenshots"  # Screenshots

# --- Throttling ---
LAST_UPDATE_FILE = CACHE_ROOT / "last_update.txt"
THROTTLE_SECONDS = 3600  # 1 hour

LAST_VERSION_CHECK_FILE = CACHE_ROOT / "last_version_check.txt"
VERSION_CHECK_INTERVAL = 3600  # 1 hour


def _safe_component(value: object) -> str:
    """
    Turns an arbitrary value into a single safe path component.

    Returns "" if the value cannot be used as a file/folder name.
    """
    if not isinstance(value, str):
        return ""

    name = value.strip().replace("\\", "/").rsplit("/", 1)[-1].strip()

    # Reject empty names, "." / "..", drive letters and control characters
    if not name or name in (".", "..") or ":" in name:
        return ""
    if any(ord(ch) < 32 for ch in name):
        return ""

    return name


def _safe_asset(base: Path, name: object) -> Path | None:
    """
    Builds a path to an asset inside `base` and verifies that the result
    really stays inside `base`. Returns None for unsafe or missing names.
    """
    safe_name = _safe_component(name)
    if not safe_name:
        return None

    candidate = base / safe_name
    try:
        if candidate.resolve().parent != base.resolve():
            return None
    except OSError:
        return None

    return candidate


def cache_exists() -> bool:
    """Checks if there is at least one JSON file in any language folder."""
    if not CACHE_APPS.exists():
        return False

    try:
        for lang_dir in CACHE_APPS.iterdir():
            if lang_dir.is_dir() and any(lang_dir.glob("*.json")):
                return True
    except OSError as e:
        print(f"[cache] Failed to scan the cache: {e}")

    return False


def cache_exists_for_lang(lang: str) -> bool:
    """Checks if there is at least one JSON file for the specific language."""
    folder = CACHE_APPS / (_safe_component(lang) or "en")
    if not folder.is_dir():
        return False
    return any(folder.glob("*.json"))


def load_cached_apps(lang: str = "") -> list[dict]:
    """
    Reads all JSON files from the cache for the given language.
    If lang is empty — uses the current language from settings.
    Falls back to English if the language folder is empty.

    Returns a list of dictionaries. Ignores corrupted files.
    """
    if not CACHE_APPS.exists():
        return []

    # Determine language
    if not lang:
        try:
            from app.core.user_settings import load_user_settings
            settings = load_user_settings()
            lang = settings.get("language", "en")
        except Exception:
            lang = "en"

    lang = _safe_component(lang) or "en"

    # Try the language folder
    apps = _read_apps_from_cache_dir(CACHE_APPS / lang)

    # Fallback to English
    if not apps and lang != "en":
        apps = _read_apps_from_cache_dir(CACHE_APPS / "en")

    return apps


def _read_apps_from_cache_dir(directory: Path) -> list[dict]:
    """Helper: reads all JSON files from a specific cache folder."""
    if not directory.is_dir():
        return []

    apps: list[dict] = []

    for json_file in sorted(directory.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                print(f"[cache] {json_file.name} — not a JSON object, skipped")
                continue

            if not isinstance(data.get("id"), str) or not data["id"].strip():
                print(f"[cache] {json_file.name} — missing id, skipped")
                continue

            if not isinstance(data.get("name"), str):
                print(f"[cache] {json_file.name} — missing name, skipped")
                continue

            apps.append(data)

        except json.JSONDecodeError as e:
            print(f"[cache] {json_file.name} — broken JSON: {e}")
        except OSError as e:
            print(f"[cache] {json_file.name} — read error: {e}")

    return apps


def clear_cache() -> bool:
    """
    Clears the entire cache folder.

    Also removes the "last update" timestamp: otherwise the application would
    keep an empty catalog for up to an hour before the next automatic refresh.

    Returns True on success.
    """
    ok = True

    if CACHE_APPS.exists():
        try:
            shutil.rmtree(CACHE_APPS)
            print(f"[cache] Cleared: {CACHE_APPS}")
        except OSError as e:
            print(f"[cache] Failed to clear the cache: {e}")
            ok = False

    try:
        CACHE_APPS.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[cache] Failed to recreate the cache folder: {e}")
        ok = False

    # Force the next catalog check to run immediately
    try:
        LAST_UPDATE_FILE.unlink(missing_ok=True)
    except OSError as e:
        print(f"[cache] Failed to reset the update timestamp: {e}")

    return ok


def get_cache_dir() -> Path:
    """Returns the path to the cache root folder (for debugging)."""
    return CACHE_APPS


def get_cache_apps_dir(lang: str) -> Path:
    """
    Returns the path to the cache folder for a specific language.
    Creates the folder if it does not exist.

    Example: get_cache_apps_dir("ru") -> %APPDATA%/OWINP/cache/apps/ru
    """
    folder = CACHE_APPS / (_safe_component(lang) or "en")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# --- Working with the Last Update Time ---

def get_last_update_info() -> tuple[float, str]:
    """
    Returns (last_update_time, last_language) from the file.
    If the file is missing or corrupted — returns (0, "").
    """
    if not LAST_UPDATE_FILE.exists():
        return 0.0, ""

    try:
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()

        if not lines:
            return 0.0, ""

        # Old format: only time
        if len(lines) == 1:
            return float(lines[0].strip()), ""

        # New format: time + language
        return float(lines[0].strip()), lines[1].strip()

    except (OSError, ValueError):
        return 0.0, ""


def set_last_update_info(lang: str) -> None:
    """Writes the current time and language to the file (atomically)."""
    try:
        LAST_UPDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LAST_UPDATE_FILE.with_name(LAST_UPDATE_FILE.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(f"{time.time()}\n{lang}\n")
        os.replace(tmp, LAST_UPDATE_FILE)
    except OSError as e:
        print(f"[cache] Failed to save update time: {e}")


def should_update_now(lang: str = "") -> bool:
    """
    Checks whether the catalog should be updated now.

    Returns True if:
    - Never updated before, OR
    - The cache was cleared, OR
    - Language changed since the last update, OR
    - More than THROTTLE_SECONDS have passed
    """
    if not lang:
        try:
            from app.core.user_settings import load_user_settings
            settings = load_user_settings()
            lang = settings.get("language", "en")
        except Exception:
            lang = "en"

    last_time, last_lang = get_last_update_info()

    if last_time == 0:
        return True

    # Language changed — update immediately.
    # An empty last_lang means the file uses the old format, so update once now.
    if last_lang != lang:
        print(f"[cache] Language changed ({last_lang or '?'} -> {lang}), updating")
        return True

    return (time.time() - last_time) > THROTTLE_SECONDS


# --- Working with Images ---

def find_icon(app_data: dict) -> Path | None:
    """
    Searches for the program icon in the cache.

    Logic:
    1. If there is an “icon_url” field, search for the file <id>.<ext> in CACHE_ICONS
    2. If there is an “icon” field, search for a file with that name in CACHE_ICONS
    3. If nothing is found, return None

    Returns the path to the found file or None.
    """
    if not CACHE_ICONS.is_dir() or not isinstance(app_data, dict):
        return None

    app_id = _safe_component(app_data.get("id", ""))

    # First — icon_url: filename = <id>.<ext>
    if app_data.get("icon_url") and app_id:
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
            candidate = _safe_asset(CACHE_ICONS, f"{app_id}{ext}")
            if candidate is not None and candidate.is_file():
                return candidate

    # Then — icon: the file name as is (basename only)
    icon_name = app_data.get("icon")
    if icon_name:
        candidate = _safe_asset(CACHE_ICONS, icon_name)
        if candidate is not None and candidate.is_file():
            return candidate

    return None


def find_screenshot(app_data: dict, name_or_index) -> Path | None:
    """
    Searches the cache for a screenshot of the program.

    name_or_index — this is:
    - str: the file name from the "screenshots" field (for example, "7zip_1.png")
    - int: index from the field "screenshots_urls" (for example, 0, 1, 2)

    Returns the Path to the file found, or None.
    """
    if not CACHE_SCREENSHOTS.is_dir() or not isinstance(app_data, dict):
        return None

    # By filename (from our repo)
    if isinstance(name_or_index, str):
        candidate = _safe_asset(CACHE_SCREENSHOTS, name_or_index)
        if candidate is not None and candidate.is_file():
            return candidate
        return None

    # By index (from an external URL)
    app_id = _safe_component(app_data.get("id", ""))
    if isinstance(name_or_index, int) and app_id:
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
            candidate = _safe_asset(CACHE_SCREENSHOTS, f"{app_id}_{name_or_index}{ext}")
            if candidate is not None and candidate.is_file():
                return candidate

    return None


def clear_assets_cache() -> bool:
    """
    Cleans up only images (icons and screenshots) without affecting the JSON.
    Returns True if successful.
    """
    success = True
    for folder in (CACHE_ICONS, CACHE_SCREENSHOTS):
        if folder.exists():
            try:
                shutil.rmtree(folder)
                folder.mkdir(parents=True, exist_ok=True)
                print(f"[cache] Cleaned: {folder}")
            except OSError as e:
                print(f"[cache] Failed to clear {folder}: {e}")
                success = False
    return success


# --- Working with the version check time ---

def get_last_version_check() -> float:
    """
    Returns the Unix timestamp of the last version check.
    If the file does not exist or is corrupted, it returns 0 (long ago).
    """
    if not LAST_VERSION_CHECK_FILE.exists():
        return 0.0
    try:
        with open(LAST_VERSION_CHECK_FILE, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return 0.0


def set_last_version_check() -> None:
    """Records the current time as the time of the last version check."""
    try:
        LAST_VERSION_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LAST_VERSION_CHECK_FILE.with_name(LAST_VERSION_CHECK_FILE.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
        os.replace(tmp, LAST_VERSION_CHECK_FILE)
    except OSError as e:
        print(f"[cache] Failed to save the version check time: {e}")


def should_check_version_now() -> bool:
    """
    Checks whether the version needs to be checked right now.

    Returns True if:
    - it has never been checked, or
    - more than VERSION_CHECK_INTERVAL has passed since the last check
    """
    last = get_last_version_check()
    if last == 0:
        return True
    return (time.time() - last) > VERSION_CHECK_INTERVAL


# --- Migration from old flat cache structure ---

def migrate_old_cache() -> None:
    """
    Migrates the old flat cache structure to per-language folders.

    In v0.1.x, all JSON files were stored directly in cache/apps/.
    In v0.2.x, they are stored in cache/apps/<lang>/.

    This function removes old flat *.json files (directly in cache/apps/)
    and leaves the language subfolders untouched.

    Safe to call multiple times — does nothing if there are no old files.
    """
    if not CACHE_APPS.is_dir():
        return

    removed = 0
    for old_file in CACHE_APPS.glob("*.json"):
        # Skip files inside language subfolders (they won't match this glob)
        try:
            print(f"[cache] Migrating: removing old flat file '{old_file.name}'")
            old_file.unlink()
            removed += 1
        except OSError as e:
            print(f"[cache] Failed to remove {old_file.name}: {e}")

    if removed:
        print(f"[cache] Migration complete: removed {removed} old flat JSON files")
