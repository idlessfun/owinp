"""
Downloading files in a background thread.

Uses qthread to prevent the UI from freezing.
Progress is communicated via Qt signals.
"""

import urllib.request
import urllib.error
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class Downloader(QThread):
    """
    Background download stream for the file.

    Signals:
        progress_changed — (bytes_downloaded, total_bytes, speed_bytes/s)
        finished_ok      — (path_to_file)
        canceled — cancellation by the user (without an error)
        failed           — (error_text)
    """

    progress_changed = Signal(int, int, float)   # Downloaded, Total, Speed
    finished_ok = Signal(str)                    # path to the file
    cancelled = Signal()                         # cancellation without error
    failed = Signal(str)                         # error message

    def __init__(self, url: str, save_path: Path) -> None:
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._cancelled = False
        self._closing = False   # True, if the dialog box is closed

    def cancel(self) -> None:
        """Request cancellation. The stream will be interrupted on the next iteration."""
        self._cancelled = True

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
        try:
            # Security Check: HTTPS Only
            if not self.url.lower().startswith("https://"):
                self.failed.emit(
                    f"Insecure URL (HTTPS required): {self.url}"
                )
                return

            # Open a connection
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "OWINP/0.1 (+https://github.com/idlessfun/owinp)"},
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                # File size (maybe None if the server does not return a Content-Length header)
                total = int(response.headers.get("Content-Length", 0))

                # Create a folder if it doesn't exist
                self.save_path.parent.mkdir(parents=True, exist_ok=True)

                # Download in 64-KB blocks
                chunk_size = 64 * 1024
                downloaded = 0
                last_emit = 0

                import time
                start_time = time.time()

                with open(self.save_path, "wb") as f:
                    while True:
                        if self._cancelled:
                            f.close()
                            self.save_path.unlink(missing_ok=True)
                            # If the dialog is already closing, do not emit
                            if not self._closing:
                                self.cancelled.emit()
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calculating Speed
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        # We emit a progress signal no more than 10 times per second
                        now = time.time()
                        if now - last_emit >= 0.1 and not self._closing:
                            self.progress_changed.emit(downloaded, total, speed)
                            last_emit = now

                    # Final progress indicator — 100%
                    if not self._closing:
                        self.progress_changed.emit(downloaded, total, 0)

                # Success
                if not self._closing:
                    self.finished_ok.emit(str(self.save_path))

        except urllib.error.HTTPError as e:
            if not self._closing:
                self.failed.emit(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            if not self._closing:
                self.failed.emit(f"No connection: {e.reason}")
        except Exception as e:
            if not self._closing:
                self.failed.emit(f"Unknown error: {e}")