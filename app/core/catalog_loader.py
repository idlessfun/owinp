"""
GitHub Program Catalog Downloader.

Downloads the latest JSON program cards from GitHub
and saves them to a local cache so that the app
always displays an up-to-date catalog.

Security:
- HTTPS only
- Only two domains: api.github.com and raw.githubusercontent.com
- Downloaded data is validated as JSON
- No eval/exec on downloaded data
- No shell commands
- Writes only to its own folder in %APPDATA%
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.cache_manager import (
    set_last_update_info,
    should_update_now,
    get_cache_apps_dir,
)
from app.core.user_settings import load_user_settings


# --- Constants ---
GITHUB_USER = "idlessfun"
GITHUB_REPO = "owinp"
GITHUB_BRANCH = "master"
APPS_PATH_IN_REPO = "app/apps"              # where JSON cards are stored in the repo
ICONS_PATH_IN_REPO = "app/resources/icons"  # where icons are stored
SCREENSHOTS_PATH_IN_REPO = "app/resources/screenshots"  # where screenshots are stored

# Base URLs for raw download (JSON and images from GitHub)
RAW_APPS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{APPS_PATH_IN_REPO}/"
)
RAW_ICONS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{ICONS_PATH_IN_REPO}/"
)
RAW_SCREENSHOTS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{SCREENSHOTS_PATH_IN_REPO}/"
)

# Where to save the cache — %APPDATA%\OWINP\cache\
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CACHE_ROOT = APPDATA / "OWINP" / "cache"
CACHE_ICONS = CACHE_ROOT / "icons"              # Icons (flat, shared by all languages)
CACHE_SCREENSHOTS = CACHE_ROOT / "screenshots"  # Screenshots (flat, shared by all languages)


class CatalogLoader(QThread):
    """
    A background process for downloading the latest catalog from GitHub.

    Signals:
        finished_ok — (number of JSON files downloaded) success
        failed      — (error message) Failed
    """

    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(self, force: bool = False) -> None:
        """
        force=True — Ignore throttling—update now.
        force=False — Refresh only if an hour has passed (by default).
        """
        super().__init__()
        self.force = force

    def run(self) -> None:
        """Main thread method."""
        try:
            # Get the current language
            try:
                settings = load_user_settings()
                lang = settings.get("language", "en")
            except Exception:
                lang = "en"

            # Throttling: check time AND language
            if not self.force:
                if not should_update_now(lang):
                    print("[catalog] Catalog update skipped (throttling)")
                    self.finished_ok.emit(0)
                    return

            print(f"[catalog] Checking catalog updates (language: {lang})...")

            # 1. Create cache folders if they don't exist
            get_cache_apps_dir(lang)  # creates cache/apps/<lang>/
            CACHE_ICONS.mkdir(parents=True, exist_ok=True)
            CACHE_SCREENSHOTS.mkdir(parents=True, exist_ok=True)

            # 2. Get file list from app/apps/<lang>/ via GitHub API
            files = self._fetch_language_files(lang)
            if not files:
                print(f"[catalog] No files found for language '{lang}'")
                # Still save the language + time, so we don't retry every minute
                set_last_update_info(lang)
                self.finished_ok.emit(0)
                return

            # 3. Download each .json file + assets
            downloaded = 0
            for filename in files:
                if not filename.endswith(".json"):
                    continue

                data = self._download_json(lang, filename)
                if data is None:
                    continue

                downloaded += 1
                self._download_assets(data)

            # 4. Clean up outdated files (only for current language)
            self._cleanup_stale_files(lang, files)

            # 5. Notify once
            print(f"[catalog] Updated files: {downloaded}")
            set_last_update_info(lang)
            self.finished_ok.emit(downloaded)

        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {e.reason}"
            print(f"[catalog] Error: {msg}")
            self.failed.emit(msg)

        except urllib.error.URLError as e:
            msg = f"No connection: {e.reason}"
            print(f"[catalog] Error: {msg}")
            self.failed.emit(msg)

        except Exception as e:
            msg = f"Unknown error: {e}"
            print(f"[catalog] Error: {msg}")
            self.failed.emit(msg)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------
    def _fetch_language_files(self, lang: str) -> list[str]:
        """
        Requests the list of files in the app/apps/<lang>/ folder via the GitHub API.
        Returns a list of file names (e.g., ["7-zip.json", "notepadpp.json"]).

        If the language folder does not exist on GitHub — returns an empty list.
        """
        api_url = (
            f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
            f"/contents/{APPS_PATH_IN_REPO}/{lang}?ref={GITHUB_BRANCH}"
        )

        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "OWINP/0.1",
                "Accept": "application/vnd.github+json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[catalog] Language folder '{lang}' not found on GitHub")
                return []
            raise

        if not isinstance(data, list):
            return []

        return [
            item.get("name", "")
            for item in data
            if isinstance(item, dict) and item.get("type") == "file"
        ]

    def _download_json(self, lang: str, filename: str) -> dict | None:
        """
        Downloads a single JSON file from app/apps/<lang>/ via raw.githubusercontent.com
        and saves it to cache/apps/<lang>/. Returns a dict with the data on success,
        otherwise None.
        """
        url = RAW_APPS_BASE + f"{lang}/{filename}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OWINP/0.1"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")

            # Validation: is it valid JSON?
            data = json.loads(raw)
            if not isinstance(data, dict):
                print(f"[catalog] {filename} — not a JSON object, skipped")
                return None

            # Check required fields
            if "name" not in data or "id" not in data:
                print(f"[catalog] {filename} — missing id/name, skipped")
                return None

            # Save to cache/<lang>/
            target_dir = get_cache_apps_dir(lang)
            target = target_dir / filename
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())   # ensure data is written to disk

            print(f"[catalog] Downloaded ({lang}): {filename}")
            return data

        except json.JSONDecodeError:
            print(f"[catalog] {filename} — broken JSON, skipped")
            return None
        except Exception as e:
            print(f"[catalog] {filename} — error: {e}")
            return None

    def _download_assets(self, data: dict) -> None:
        """
        Saves the program's icon and screenshots to the cache.

        Logic:
        - If the JSON contains an `icon_url`, use it
        - If only `icon` (file name) is present, construct the URL from our GitHub
        - Similarly for `screenshots` and `screenshots_urls`
        """
        app_id = data.get("id", "unknown")

        # --- Icon ---
        icon_url = data.get("icon_url")
        icon_name = data.get("icon")

        # Security: Blocking Unsafe URLs
        if icon_url and not icon_url.lower().startswith("https://"):
            print(f"[catalog] Insecure icon_url (not HTTPS): {icon_url}")
            icon_url = None

        if icon_url:
            ext = self._extract_extension(icon_url)
            local_name = f"{app_id}{ext}"
            self._download_image(icon_url, CACHE_ICONS / local_name)
        elif icon_name:
            # Security: We only take the filename (without paths)
            safe_name = Path(icon_name).name
            url = RAW_ICONS_BASE + safe_name
            self._download_image(url, CACHE_ICONS / safe_name)

        # --- Screenshots ---
        screenshot_urls = data.get("screenshots_urls", [])
        screenshot_names = data.get("screenshots", [])

        # External URLs
        for i, url in enumerate(screenshot_urls):
            # Security: HTTPS Only
            if not url.lower().startswith("https://"):
                print(f"[catalog] Insecure screenshots_urls (not HTTPS): {url}")
                continue
            ext = self._extract_extension(url)
            local_name = f"{app_id}_{i}{ext}"
            self._download_image(url, CACHE_SCREENSHOTS / local_name)

        # File names from my repo
        for name in screenshot_names:
            # Security: We only accept the filename
            safe_name = Path(name).name
            url = RAW_SCREENSHOTS_BASE + safe_name
            self._download_image(url, CACHE_SCREENSHOTS / safe_name)

    def _download_image(self, url: str, target: Path) -> bool:
        """
        Downloads a single image and saves it to `target`.
        Returns `True` if successful.
        """
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OWINP/0.1"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()

            if not content or len(content) < 20:
                print(f"[catalog] The image is empty: {url}")
                return False

            with open(target, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            print(f"[catalog] Downloaded image: {target.name}")
            return True

        except Exception as e:
            print(f"[catalog] The image has not been downloaded ({url}): {e}")
            return False

    def _cleanup_stale_files(self, lang: str, actual_files: list[str]) -> None:
        """
        Removes cache files that no longer exist on GitHub for the given language.

        Only cleans the <lang> folder. Icons/screenshots cleanup — flat
        (uses all languages to decide which assets are still used).
        """
        # 1. Collect a set of actual names
        actual_names = {name for name in actual_files if name.endswith(".json")}

        # 2. Remove outdated JSON from the language folder
        cache_dir = get_cache_apps_dir(lang)
        removed_json = 0
        for cache_file in cache_dir.glob("*.json"):
            if cache_file.name not in actual_names:
                print(f"[catalog] Removing outdated ({lang}): {cache_file.name}")
                try:
                    cache_file.unlink()
                    removed_json += 1
                except Exception as e:
                    print(f"[catalog] Failed to remove {cache_file.name}: {e}")

        # 3. Collect actual ids from ALL languages (to keep shared assets)
        actual_ids = set()
        cache_apps_root = CACHE_ROOT / "apps"
        if cache_apps_root.exists():
            for lang_dir in cache_apps_root.iterdir():
                if not lang_dir.is_dir():
                    continue
                for cache_file in lang_dir.glob("*.json"):
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if "id" in data:
                            actual_ids.add(data["id"])
                    except Exception:
                        pass

        # 4. Remove icons that are not in any language
        removed_icons = 0
        if CACHE_ICONS.exists():
            for icon_file in CACHE_ICONS.glob("*"):
                if icon_file.stem not in actual_ids:
                    print(f"[catalog] Removing outdated icon: {icon_file.name}")
                    try:
                        icon_file.unlink()
                        removed_icons += 1
                    except Exception:
                        pass

        # 5. Remove screenshots that are not in any language
        removed_shots = 0
        if CACHE_SCREENSHOTS.exists():
            for shot_file in CACHE_SCREENSHOTS.glob("*"):
                stem = shot_file.stem
                if "_" in stem:
                    shot_id = stem.rsplit("_", 1)[0]
                    if shot_id not in actual_ids:
                        print(f"[catalog] Removing outdated screenshot: {shot_file.name}")
                        try:
                            shot_file.unlink()
                            removed_shots += 1
                        except Exception:
                            pass

        if removed_json or removed_icons or removed_shots:
            print(
                f"[catalog] Cache cleanup: "
                f"JSON={removed_json}, icons={removed_icons}, screenshots={removed_shots}"
            )

    @staticmethod
    def _extract_extension(url: str) -> str:
        """
        Retrieves the file extension from a URL.
        For example: ".../vlc.png" -> ".png"
                  ".../file.jpg?x=1" -> ".jpg"
        Returns ".png" by default.
        """
        clean = url.split("?")[0]
        if "." in clean.rsplit("/", 1)[-1]:
            ext = "." + clean.rsplit(".", 1)[-1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
                return ext
        return ".png"