"""
Downloading files in a background thread.

Uses qthread to prevent the UI from freezing.
Progress is communicated via Qt signals.
"""

import hashlib
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app import __version__
from app.core.thread_registry import register, unregister


MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024


class _Cancelled(Exception):
    """Raised internally when the user cancels the download."""


class _Failed(Exception):
    """Raised internally for validation errors (for example, a non-HTTPS URL)."""


def _is_https_url(url: object) -> bool:
    """True for an absolute HTTPS URL with a host and no embedded credentials."""
    if not isinstance(url, str):
        return False
    try:
        parts = urllib.parse.urlsplit(url.strip())
        parts.port
    except ValueError:
        return False
    return (
        parts.scheme.lower() == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
    )


class _HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Blocks redirects that drop HTTPS or hide embedded credentials."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_https_url(newurl):
            raise urllib.error.URLError(f"Blocked insecure redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Downloader(QThread):
    """
    Background download stream for the file.

    Signals:
        progress_changed — (bytes_downloaded, total_bytes, speed_bytes/s)
        finished_ok      — (path_to_file)
        canceled — cancellation by the user (without an error)
        failed           — (error_text)
    """

    progress_changed = Signal("qint64", "qint64", float)   # Downloaded, Total, Speed
    finished_ok = Signal(str)                    # path to the file
    cancelled = Signal()                         # cancellation without error
    failed = Signal(str)                         # error message

    def __init__(self, url: str, save_path: Path, expected_sha256: str = "") -> None:
        super().__init__()
        self.url = url
        self.save_path = Path(save_path)
        self.expected_sha256 = (
            expected_sha256 if isinstance(expected_sha256, str) else ""
        )
        self._cancel_requested = False
        self._closing = False   # True, if the dialog box is closed
        self._created_file = False  # True once we started writing the target

    @property
    def is_closing(self) -> bool:
        """True if the dialog is closing and signals must not be emitted."""
        return self._closing

    def cancel(self) -> None:
        """Request cancellation. The stream will be interrupted on the next iteration."""
        self._cancel_requested = True

    def mark_closing(self) -> None:
        """
        Mark the stream as “dialog closed.”
        After that, signals will NOT be emitted (the receiver object may have already been removed).
        """
        self._closing = True

    def run(self) -> None:
        """
        The main method of the stream. It is called automatically when .start() is called.
        This is where the download takes place.
        """
        register(self)
        try:
            self._download()
        except _Cancelled:
            self._discard_partial()
            print("[download] Cancelled by the user")
            if not self._closing:
                self.cancelled.emit()
        except _Failed as e:
            self._discard_partial()
            print(f"[download] {e}")
            if not self._closing:
                self.failed.emit(str(e))
        except urllib.error.HTTPError as e:
            self._discard_partial()
            if not self._closing:
                self.failed.emit(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            self._discard_partial()
            if not self._closing:
                self.failed.emit(f"No connection: {e.reason}")
        except Exception as e:
            self._discard_partial()
            if not self._closing:
                self.failed.emit(f"Unknown error: {e}")
        finally:
            unregister(self)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _download(self) -> None:
        # Security Check: HTTPS Only
        if not _is_https_url(self.url):
            raise _Failed(f"Insecure URL (HTTPS required): {self.url}")

        expected = self.expected_sha256.strip().lower()
        if expected and (
            len(expected) != 64
            or any(ch not in "0123456789abcdef" for ch in expected)
        ):
            raise _Failed("Invalid SHA-256 checksum in the catalog")

        hasher = hashlib.sha256() if expected else None

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": f"OWINP/{__version__} (+https://github.com/idlessfun/owinp)"
            },
        )
        opener = urllib.request.build_opener(_HttpsRedirectHandler())

        with opener.open(req, timeout=30) as response:
            if not _is_https_url(response.geturl()):
                raise _Failed("The server redirected to an insecure URL")

            # File size (maybe None if the server does not return a Content-Length header)
            raw_total = response.headers.get("Content-Length", 0) or 0
            try:
                total = int(raw_total)
            except (TypeError, ValueError):
                total = 0

            if total > MAX_DOWNLOAD_BYTES:
                raise _Failed("The file is larger than the allowed limit")

            # Create a folder if it doesn't exist
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            # Download in 64-KB blocks
            chunk_size = 64 * 1024
            downloaded = 0
            last_emit = 0.0
            start_time = time.monotonic()

            with open(self.save_path, "wb") as f:
                self._created_file = True
                while True:
                    if self._cancel_requested:
                        raise _Cancelled

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    downloaded += len(chunk)
                    if downloaded > MAX_DOWNLOAD_BYTES:
                        raise _Failed("The file is larger than the allowed limit")

                    f.write(chunk)
                    if hasher is not None:
                        hasher.update(chunk)

                    # Calculating Speed
                    elapsed = time.monotonic() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0

                    # We emit a progress signal no more than 10 times per second
                    now = time.monotonic()
                    if now - last_emit >= 0.1 and not self._closing:
                        self.progress_changed.emit(downloaded, total, speed)
                        last_emit = now

                # Make sure the file is really on disk before reporting success
                f.flush()
                os.fsync(f.fileno())

        if self._cancel_requested:
            raise _Cancelled

        if total > 0 and downloaded != total:
            raise _Failed("Incomplete download: the connection was interrupted")

        if hasher is not None and hasher.hexdigest() != expected:
            raise _Failed("SHA-256 checksum mismatch")

        # Final progress indicator — 100%
        if not self._closing:
            self.progress_changed.emit(downloaded, total, 0)

        if not self._closing:
            self.finished_ok.emit(str(self.save_path))

    def _discard_partial(self) -> None:
        """Deletes a partially downloaded file, if this worker created it."""
        if not self._created_file:
            return

        try:
            if self.save_path.exists():
                self.save_path.unlink()
                print(f"[download] Partial file removed: {self.save_path}")
        except OSError as e:
            print(f"[download] Failed to remove the partial file: {e}")
