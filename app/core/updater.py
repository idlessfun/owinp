"""
Checking for OWINP updates via the GitHub API.

Runs in a background thread so as not to block the user interface.
"""

import json
import urllib.request
import urllib.error

from PySide6.QtCore import QThread, Signal

from app import __version__

from app.core.cache_manager import (
    should_check_version_now,
    set_last_version_check,
)

# GitHub repository—this is where we'll go
GITHUB_REPO = "idlessfun/owinp"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


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

    def run(self) -> None:
        """Main Flow Method. Runs automatically when .start()."""
        try:
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

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Retrieving release information
            tag_name = data.get("tag_name", "")          # for example "v0.2.0"
            release_name = data.get("name", "")          # for example "OWINP v0.2.0"
            body = data.get("body", "")                  # Release Notes
            html_url = data.get("html_url", "")          # link to the release page
            published_at = data.get("published_at", "")  # publication date

            # Record the time of a successful check
            set_last_version_check()
            # Remove the "v" prefix from the tag: "v0.2.0" → "0.2.0"
            latest_version = tag_name.lstrip("v").strip()

            print(f"[updater] Latest version on GitHub: {latest_version}")

            # Comparing Versions
            if self._is_newer(latest_version, __version__):
                print(f"[updater] ✅ An update is available: {latest_version}")
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

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        """
        Compares two versions of a view "0.1.0" and "0.2.0".
        Returns True if the remote version is newer than the local version.
        """
        try:
            remote_parts = [int(x) for x in remote.split(".")]
            local_parts = [int(x) for x in local.split(".")]
        except ValueError:
            # If the version is non-standard (for example, "0.2.0-beta"), we consider it "not newer"
            return False

        # Pad with zeros to make the lengths equal
        while len(remote_parts) < len(local_parts):
            remote_parts.append(0)
        while len(local_parts) < len(remote_parts):
            local_parts.append(0)

        return remote_parts > local_parts