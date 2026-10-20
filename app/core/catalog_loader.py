"""
GitHub Program Catalog Downloader.

Downloads the latest JSON program cards from GitHub
and saves them to a local cache so that the app
always displays an up-to-date catalog.

Security:
- HTTPS only
- Only two domains: api.github.com and raw.githubusercontent.com
- Redirects are validated against the same allowlist
- JSON and image responses are size-capped
- Asset names are reduced to safe Windows file names and must stay in the cache
- Downloaded data is validated as JSON
- No eval/exec on downloaded data
- No shell commands
- Writes only to its own data folder (%APPDATA%\OWINP or portable OWINP-data)
"""

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from email.utils import formatdate
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app import __version__
from app.core.cache_manager import (
    CACHE_APPS,
    CACHE_ICONS,
    CACHE_SCREENSHOTS,
    _safe_asset,
    _safe_component,
    get_cache_apps_dir,
    set_last_update_info,
    should_update_now,
)
from app.core.thread_registry import register, unregister
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

# Refuse unexpectedly huge "images" (the biggest real icon is ~5 MB)
MAX_ASSET_BYTES = 25 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024

GITHUB_HOSTS = frozenset({"api.github.com", "raw.githubusercontent.com"})
ASSET_HOSTS = frozenset({"raw.githubusercontent.com"})

USER_AGENT = f"OWINP/{__version__} (+https://github.com/idlessfun/owinp)"


def _is_allowed_url(url: object, allowed_hosts: frozenset[str]) -> bool:
    """True for a plain HTTPS URL on one of the allowed hosts."""
    if not isinstance(url, str):
        return False

    try:
        parts = urllib.parse.urlsplit(url.strip())
        port = parts.port
    except ValueError:
        return False

    if parts.scheme.lower() != "https":
        return False
    if parts.username or parts.password:
        return False
    if port not in (None, 443):
        return False
    if not parts.hostname:
        return False

    return parts.hostname.lower() in allowed_hosts


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Blocks redirects that leave the GitHub allowlist or drop HTTPS."""

    def __init__(self, allowed_hosts: frozenset[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_allowed_url(newurl, self._allowed_hosts):
            raise urllib.error.URLError(f"Blocked redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_url(req: urllib.request.Request, allowed_hosts: frozenset[str], timeout: int = 10):
    """Opens an HTTP request with an allowlisted redirect policy."""
    opener = urllib.request.build_opener(_SafeRedirectHandler(allowed_hosts))
    return opener.open(req, timeout=timeout)


def _read_limited(response, limit: int) -> bytes:
    """Reads at most `limit` bytes and fails if the body is larger."""
    content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f"Response is larger than {limit} bytes")
    return content


def _atomic_write_bytes(target: Path, content: bytes) -> None:
    """
    Writes bytes to `target` atomically.

    A temporary file is written first, then renamed over the target, so an
    interrupted download can never leave a truncated JSON card or image.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(
        f"{target.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )

    try:
        with open(tmp, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


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
        self._cancelled = False

    def cancel(self) -> None:
        """Asks the worker to stop after the current file."""
        self._cancelled = True

    def run(self) -> None:
        """Main thread method."""
        register(self)
        try:
            self._run()
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

        finally:
            unregister(self)

    def _run(self) -> None:
        """Actual work, separated so that run() can wrap it with error handling."""
        # Get the current language
        try:
            settings = load_user_settings()
            lang = _safe_component(settings.get("language", "en")) or "en"
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
            if self._cancelled:
                print("[catalog] Cancelled by the user")
                self.finished_ok.emit(downloaded)
                return

            if not filename.endswith(".json"):
                continue

            data = self._download_json(lang, filename)
            if data is None:
                continue

            downloaded += 1
            self._download_assets(data)

        if self._cancelled:
            print("[catalog] Cancelled by the user")
            self.finished_ok.emit(downloaded)
            return

        # 4. Clean up outdated files (only for the current language)
        self._cleanup_stale_files(lang, files)

        # 5. Notify once
        print(f"[catalog] Updated files: {downloaded}")
        set_last_update_info(lang)
        self.finished_ok.emit(downloaded)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------
    def _fetch_language_files(self, lang: str) -> list[str]:
        """
        Requests the list of files in the app/apps/<lang>/ folder via the GitHub API.
        Returns a list of file names (e.g., ["7-zip.json", "notepadpp.json"]).

        If the language folder does not exist on GitHub — returns an empty list.
        """
        safe_lang = _safe_component(lang) or "en"
        api_url = (
            f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
            f"/contents/{APPS_PATH_IN_REPO}/{urllib.parse.quote(safe_lang)}"
            f"?ref={GITHUB_BRANCH}"
        )

        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )

        try:
            with _open_url(req, GITHUB_HOSTS) as response:
                if not _is_allowed_url(response.geturl(), GITHUB_HOSTS):
                    raise urllib.error.URLError("Unexpected response URL")
                raw = _read_limited(response, MAX_JSON_BYTES)
                data = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[catalog] Language folder '{safe_lang}' not found on GitHub")
                return []
            raise

        if not isinstance(data, list):
            return []

        files = []
        for item in data:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            name = _safe_component(item.get("name"))
            if name:
                files.append(name)
        return files

    def _download_json(self, lang: str, filename: str) -> dict | None:
        """
        Downloads a single JSON file from app/apps/<lang>/ via raw.githubusercontent.com
        and saves it to cache/apps/<lang>/. Returns a dict with the data on success,
        otherwise None.
        """
        safe_lang = _safe_component(lang) or "en"
        safe_name = _safe_component(filename)
        if not safe_name.endswith(".json"):
            return None

        url = (
            RAW_APPS_BASE
            + f"{urllib.parse.quote(safe_lang)}/{urllib.parse.quote(safe_name)}"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            with _open_url(req, GITHUB_HOSTS) as response:
                if not _is_allowed_url(response.geturl(), GITHUB_HOSTS):
                    raise urllib.error.URLError("Unexpected response URL")
                raw = _read_limited(response, MAX_JSON_BYTES).decode("utf-8-sig")

            # Validation: is it valid JSON?
            data = json.loads(raw)
            if not isinstance(data, dict):
                print(f"[catalog] {safe_name} — not a JSON object, skipped")
                return None

            # Check required fields
            if not isinstance(data.get("id"), str) or not data["id"].strip():
                print(f"[catalog] {safe_name} — missing id, skipped")
                return None
            if not _safe_component(data["id"]):
                print(f"[catalog] {safe_name} — unsafe id, skipped")
                return None
            if not isinstance(data.get("name"), str) or not data["name"].strip():
                print(f"[catalog] {safe_name} — missing name, skipped")
                return None

            # Save to cache/<lang>/ atomically
            target = get_cache_apps_dir(safe_lang) / safe_name
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            _atomic_write_bytes(target, payload)

            print(f"[catalog] Downloaded ({safe_lang}): {safe_name}")
            return data

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            print(f"[catalog] {safe_name} — broken or oversized JSON, skipped")
            return None
        except (urllib.error.URLError, OSError) as e:
            print(f"[catalog] {safe_name} — error: {e}")
            return None

    def _download_assets(self, data: dict) -> None:
        """
        Saves the program's icon and screenshots to the cache.

        Logic:
        - If the JSON contains an `icon_url`, use it
        - If only `icon` (file name) is present, construct the URL from our GitHub
        - Similarly for `screenshots` and `screenshots_urls`
        """
        app_id = _safe_component(data.get("id"))
        if not app_id:
            return

        # --- Icon ---
        icon_url = data.get("icon_url")
        icon_name = data.get("icon")

        # Security: assets may only come from raw.githubusercontent.com
        if isinstance(icon_url, str) and icon_url.strip():
            if not _is_allowed_url(icon_url, ASSET_HOSTS):
                print(f"[catalog] Blocked icon_url host or scheme: {icon_url}")
                icon_url = None

        if self._cancelled:
            return

        if isinstance(icon_url, str) and icon_url:
            ext = self._extract_extension(icon_url)
            target = _safe_asset(CACHE_ICONS, f"{app_id}{ext}")
            if target is not None:
                self._download_image(str(icon_url), target)
        elif isinstance(icon_name, str) and icon_name:
            # Security: we only take a safe file name (without paths)
            safe_name = _safe_component(icon_name)
            target = _safe_asset(CACHE_ICONS, safe_name)
            if safe_name and target is not None:
                url = RAW_ICONS_BASE + urllib.parse.quote(safe_name)
                self._download_image(url, target)

        # --- Screenshots ---
        screenshot_urls = data.get("screenshots_urls") or []
        screenshot_names = data.get("screenshots") or []

        if not isinstance(screenshot_urls, list):
            screenshot_urls = []
        if not isinstance(screenshot_names, list):
            screenshot_names = []

        # External URLs
        for i, url in enumerate(screenshot_urls):
            if self._cancelled:
                return
            if not _is_allowed_url(url, ASSET_HOSTS):
                print(f"[catalog] Blocked screenshots_urls entry: {url}")
                continue
            ext = self._extract_extension(url)
            target = _safe_asset(CACHE_SCREENSHOTS, f"{app_id}_{i}{ext}")
            if target is not None:
                self._download_image(url, target)

        # File names from our repo
        for name in screenshot_names:
            if self._cancelled:
                return
            safe_name = _safe_component(name)
            target = _safe_asset(CACHE_SCREENSHOTS, safe_name)
            if not safe_name or target is None:
                continue
            url = RAW_SCREENSHOTS_BASE + urllib.parse.quote(safe_name)
            self._download_image(url, target)

    def _download_image(self, url: str, target: Path) -> bool:
        """
        Downloads a single image and saves it to `target`.
        Returns `True` if successful.

        Sends If-Modified-Since for files that are already cached, so an
        unchanged image costs a tiny 304 response instead of a full download.
        """
        if not _is_allowed_url(url, ASSET_HOSTS):
            print(f"[catalog] Refused an unsafe image URL: {url}")
            return False

        if not self._is_cache_image(target):
            print(f"[catalog] Refused an unsafe image path: {target}")
            return False

        try:
            headers = {"User-Agent": USER_AGENT}

            try:
                stat = target.stat()
                if stat.st_size > 0:
                    headers["If-Modified-Since"] = formatdate(
                        stat.st_mtime, usegmt=True
                    )
            except OSError:
                pass

            req = urllib.request.Request(url, headers=headers)
            try:
                with _open_url(req, ASSET_HOSTS) as response:
                    if not _is_allowed_url(response.geturl(), ASSET_HOSTS):
                        return False
                    content = response.read(MAX_ASSET_BYTES + 1)
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    return True
                raise

            if not content or len(content) < 20:
                print(f"[catalog] The image is empty: {url}")
                return False

            if len(content) > MAX_ASSET_BYTES:
                print(f"[catalog] The image is too large, skipped: {url}")
                return False

            _atomic_write_bytes(target, content)
            print(f"[catalog] Downloaded image: {target.name}")
            return True

        except Exception as e:
            print(f"[catalog] The image has not been downloaded ({url}): {e}")
            return False

    @staticmethod
    def _is_cache_image(target: Path) -> bool:
        """True only for a direct child of the icon or screenshot cache."""
        try:
            parent = target.resolve().parent
            return parent in (CACHE_ICONS.resolve(), CACHE_SCREENSHOTS.resolve())
        except OSError:
            return False

    def _cleanup_stale_files(self, lang: str, actual_files: list[str]) -> None:
        """
        Removes cache files that no longer exist on GitHub for the given language.

        Only cleans the <lang> folder. Icons/screenshots are shared between
        languages, so they are kept when any cached card references them.
        """
        safe_lang = _safe_component(lang) or "en"

        # 1. Collect a set of actual names
        actual_names = {
            _safe_component(name)
            for name in actual_files
            if isinstance(name, str) and name.endswith(".json")
        }
        actual_names.discard("")

        # 2. Remove outdated JSON from the language folder
        cache_dir = get_cache_apps_dir(safe_lang)
        removed_json = 0
        for cache_file in cache_dir.glob("*.json"):
            if cache_file.name not in actual_names:
                print(f"[catalog] Removing outdated ({safe_lang}): {cache_file.name}")
                try:
                    cache_file.unlink()
                    removed_json += 1
                except OSError as e:
                    print(f"[catalog] Failed to remove {cache_file.name}: {e}")

        # 3. Remove temporary files left behind by an interrupted write
        for tmp_file in cache_dir.glob("*.tmp"):
            try:
                tmp_file.unlink()
            except OSError:
                pass

        # 4. Collect all asset names that any cached card still references
        referenced_icons, referenced_shots = self._collect_referenced_assets()

        # 4. Remove icons that are not referenced by any language
        removed_icons = self._remove_unreferenced(CACHE_ICONS, referenced_icons)

        # 5. Remove screenshots that are not referenced by any language
        removed_shots = self._remove_unreferenced(
            CACHE_SCREENSHOTS, referenced_shots
        )

        if removed_json or removed_icons or removed_shots:
            print(
                f"[catalog] Cache cleanup: "
                f"JSON={removed_json}, icons={removed_icons}, screenshots={removed_shots}"
            )

    @staticmethod
    def _remove_unreferenced(folder: Path, referenced: set[str]) -> int:
        """Deletes regular files in `folder` that are not in `referenced`."""
        removed = 0
        if not folder.is_dir():
            return removed

        for asset in folder.iterdir():
            if not asset.is_file():
                continue
            # Temporary files from an interrupted write are always removed
            if asset.name.endswith(".tmp"):
                try:
                    asset.unlink()
                except OSError:
                    pass
                continue

            if asset.name in referenced:
                continue

            print(f"[catalog] Removing outdated asset: {asset.name}")
            try:
                asset.unlink()
                removed += 1
            except OSError:
                pass

        return removed

    def _collect_referenced_assets(self) -> tuple[set[str], set[str]]:
        """
        Scans every cached JSON card (all languages) and returns
        (referenced icon names, referenced screenshot names).
        """
        icons: set[str] = set()
        shots: set[str] = set()

        if not CACHE_APPS.is_dir():
            return icons, shots

        for lang_dir in CACHE_APPS.iterdir():
            if not lang_dir.is_dir():
                continue

            for card in lang_dir.glob("*.json"):
                try:
                    with open(card, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue

                if not isinstance(data, dict):
                    continue

                app_id = _safe_component(data.get("id"))

                icon_url = data.get("icon_url")
                icon_name = data.get("icon")

                if isinstance(icon_url, str) and icon_url and app_id:
                    icons.add(f"{app_id}{self._extract_extension(icon_url)}")
                if isinstance(icon_name, str) and icon_name:
                    safe_name = _safe_component(icon_name)
                    if safe_name:
                        icons.add(safe_name)

                screenshots = data.get("screenshots") or []
                if isinstance(screenshots, list):
                    for name in screenshots:
                        safe_name = _safe_component(name)
                        if safe_name:
                            shots.add(safe_name)

                screenshots_urls = data.get("screenshots_urls") or []
                if isinstance(screenshots_urls, list) and app_id:
                    for i, url in enumerate(screenshots_urls):
                        if isinstance(url, str) and url:
                            shots.add(
                                f"{app_id}_{i}{self._extract_extension(url)}"
                            )

        return icons, shots

    @staticmethod
    def _extract_extension(url: str) -> str:
        """
        Retrieves the file extension from a URL.
        For example: ".../vlc.png" -> ".png"
                  ".../file.jpg?x=1" -> ".jpg"
        Returns ".png" by default.
        """
        try:
            path = urllib.parse.urlsplit(url).path
        except ValueError:
            return ".png"

        name = path.rsplit("/", 1)[-1]
        if "." in name:
            ext = "." + name.rsplit(".", 1)[-1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
                return ext
        return ".png"
