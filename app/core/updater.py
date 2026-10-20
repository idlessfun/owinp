"""
Checking for OWINP updates via the GitHub API.

Runs in a background thread so as not to block the user interface.
"""

import json
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

from app import __version__

from app.core.cache_manager import (
    should_check_version_now,
    set_last_version_check,
)
from app.core.catalog_loader import _is_allowed_url, _open_url
from app.core.thread_registry import register, unregister

# GitHub repository—this is where we'll go
GITHUB_REPO = "idlessfun/owinp"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_API_HOSTS = frozenset({"api.github.com"})
MAX_API_BYTES = 2 * 1024 * 1024


class UpdateChecker(QThread):
    """
    A background process for checking for updates.

    Signals:
        update_available — (info_dict) There's a new version
        no_update       — No updates
        check_failed    — (error_text) Unable to verify (no internet connection, etc.)
    """

    update_available = Signal(dict)
    no_update = Signal()
    check_failed = Signal(str)

    def __init__(self, force: bool = False) -> None:
        """
        force=True  — Ignore throttling, check right now
                      (for the «Check for Updates» button).
        force=False — Check only if an hour has passed (by default).
        """
        super().__init__()
        self.force = force
        self._cancelled = False

    def cancel(self) -> None:
        """Asks the worker to stop as soon as the current request returns."""
        self._cancelled = True

    def run(self) -> None:
        """Main Flow Method. Runs automatically when .start()."""
        register(self)
        try:
            self._check()
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {e.reason}"
            print(f"[updater] Validation error: {msg}")
            self.check_failed.emit(msg)

        except urllib.error.URLError as e:
            msg = f"No connection: {e.reason}"
            print(f"[updater] Validation error: {msg}")
            self.check_failed.emit(msg)

        except Exception as e:
            msg = f"Unknown error: {e}"
            print(f"[updater] Validation error: {msg}")
            self.check_failed.emit(msg)

        finally:
            unregister(self)

    def _check(self) -> None:
        """Performs the actual request and emits the result signal."""
        if self._cancelled:
            return

        # Throttling: if it's not a “force” request, and it was recently checked, skip it
        if not self.force and not should_check_version_now():
            print("[updater] Update check skipped (throttling)")
            self.no_update.emit()
            return

        print("[updater] Check for Updates...")
        print(f"[updater] Current version: {__version__}")

        # GitHub API Request
        req = urllib.request.Request(
            API_URL,
            headers={
                "User-Agent": f"OWINP/{__version__}",
                "Accept": "application/vnd.github+json",
            },
        )

        with _open_url(req, GITHUB_API_HOSTS, timeout=10) as response:
            if not _is_allowed_url(response.geturl(), GITHUB_API_HOSTS):
                self.check_failed.emit("Unexpected response URL")
                return
            raw = response.read(MAX_API_BYTES + 1)

        if len(raw) > MAX_API_BYTES:
            self.check_failed.emit("The response from GitHub is too large")
            return

        if self._cancelled:
            return

        data = json.loads(raw.decode("utf-8"))

        if not isinstance(data, dict):
            self.check_failed.emit("Unexpected response from GitHub")
            return

        # Retrieving release information
        tag_name = data.get("tag_name")              # for example "v0.2.0"
        release_name = data.get("name")              # for example "OWINP v0.2.0"
        body = data.get("body")                      # Release Notes
        html_url = data.get("html_url")              # link to the release page
        published_at = data.get("published_at")      # publication date

        if not isinstance(tag_name, str) or not tag_name.strip():
            self.check_failed.emit("Unexpected response from GitHub")
            return

        release_name = release_name if isinstance(release_name, str) else ""
        body = body if isinstance(body, str) else ""
        html_url = html_url if isinstance(html_url, str) else ""
        published_at = published_at if isinstance(published_at, str) else ""

        # Record the time of a successful check
        set_last_version_check()

        # Remove the "v" prefix from the tag: "v0.2.0" → "0.2.0"
        latest_version = tag_name.strip().lstrip("vV").strip()

        print(f"[updater] Latest version on GitHub: {latest_version}")

        if self._cancelled:
            return

        # Comparing Versions
        if self._is_newer(latest_version, __version__):
            print(f"[updater] An update is available: {latest_version}")
            self.update_available.emit({
                "version": latest_version,
                "name": release_name,
                "body": body,
                "url": html_url,
                "published_at": published_at,
            })
        else:
            print("[updater] You have the latest version")
            self.no_update.emit()

    @staticmethod
    def _parse_version(version: str) -> tuple[int, ...] | None:
        """
        Converts "v1.2.3", "1.2.3-beta", "1.2.3+build" into (1, 2, 3).
        Returns None for versions without a numeric release part.
        """
        if not isinstance(version, str):
            return None

        # Drop pre-release / build metadata: "1.2.3-beta.1" -> "1.2.3"
        core = version.strip().lstrip("vV").split("-", 1)[0].split("+", 1)[0]
        parts = core.split(".")

        if not parts or not all(part.strip().isdigit() for part in parts):
            return None

        return tuple(int(part) for part in parts)

    @classmethod
    def _is_newer(cls, remote: str, local: str) -> bool:
        """
        Compares two versions of a view "0.1.0" and "0.2.0".
        Returns True if the remote version is newer than the local version.

        Non-numeric versions are treated as "not newer" (the update is never
        forced on the user because of a strange tag).
        """
        remote_parts = cls._parse_version(remote)
        local_parts = cls._parse_version(local)

        if remote_parts is None or local_parts is None:
            return False

        # Pad with zeros to make the lengths equal
        length = max(len(remote_parts), len(local_parts))
        remote_parts = remote_parts + (0,) * (length - len(remote_parts))
        local_parts = local_parts + (0,) * (length - len(local_parts))

        return remote_parts > local_parts
