"""
A nice download dialog in OWINP style.
"""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
)

from app.core.downloader import Downloader
from app.core.cache_manager import find_icon
from app.core.translator import t
from app.ui.theme_helper import get_dialog_qss


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


class DownloadDialog(QDialog):
    """
    Download window.
    Shows a progress bar, speed, and size.
    When finished, it offers to open the folder or run the file.
    """

    def __init__(self, app_data: dict, save_path: Path, parent=None) -> None:
        super().__init__(parent)

        self.app_data = app_data
        self.save_path = save_path
        self.downloader: Downloader | None = None

        self.setWindowTitle(
            t("download.title", name=app_data.get("name", ""))
        )
        self.setModal(True)
        self.setFixedSize(480, 260)

        self._build_ui()
        self._apply_styles()
        self._start_download()

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Header: icon + name ---
        header = QHBoxLayout()
        header.setSpacing(16)

        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Look for the icon in the cache (same as in AppCard)
        icon_path = find_icon(self.app_data)

        # If not in the cache, try the built-in one
        if icon_path is None:
            icon_name = self.app_data.get("icon", "")
            if icon_name:
                candidate = ICONS_DIR / icon_name
                if candidate.exists():
                    icon_path = candidate

        if icon_path is not None:
            pixmap = QPixmap(str(icon_path)).scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("?")
            icon_label.setObjectName("DlIconPlaceholder")

        header.addWidget(icon_label)

        text_block = QVBoxLayout()
        text_block.setSpacing(4)

        self.title_label = QLabel(
            t("download.header", name=self.app_data.get("name", ""))
        )
        self.title_label.setObjectName("DlTitle")

        self.status_label = QLabel(t("download.connecting"))
        self.status_label.setObjectName("DlStatus")

        text_block.addWidget(self.title_label)
        text_block.addWidget(self.status_label)

        header.addLayout(text_block, stretch=1)
        layout.addLayout(header)

        # --- Progress bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("DlProgress")
        layout.addWidget(self.progress_bar)

        # --- Details: size, speed, percent ---
        self.details_label = QLabel(t("download.details_init"))
        self.details_label.setObjectName("DlDetails")
        layout.addWidget(self.details_label)

        layout.addStretch(1)

        # --- Buttons (only "Cancel" at first) ---
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(8)
        self.buttons_layout.addStretch(1)

        self.cancel_btn = QPushButton(t("download.cancel"))
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(self.buttons_layout)

    def _apply_styles(self) -> None:
        extra_qss = """
            #DlTitle {
                font-size: 17px;
                font-weight: 700;
                color: __TEXT_PRIMARY__;
            }

            #DlStatus {
                font-size: 13px;
                color: __TEXT_SECONDARY__;
            }

            #DlDetails {
                font-size: 12px;
                color: __ACCENT__;
            }

            #DlIconPlaceholder {
                background-color: __BORDER__;
                border-radius: 8px;
                color: __TEXT_MUTED__;
                font-size: 24px;
                font-weight: 700;
            }

            #DlProgress {
                background-color: __CARD__;
                border: none;
                border-radius: 8px;
                height: 12px;
            }

            #DlProgress::chunk {
                background-color: __ACCENT__;
                border-radius: 8px;
            }
        """
        self.setStyleSheet(get_dialog_qss(extra_qss))

    # ------------------------------------------------------------------
    # Download logic
    # ------------------------------------------------------------------
    def _start_download(self) -> None:
        # URL may come from the button (_clicked_url) or from the old field
        url = self.app_data.get("_clicked_url") or self.app_data.get("download_url", "")
        if not url:
            QMessageBox.warning(
                self,
                t("common.error"),
                t("download.no_url"),
            )
            self.reject()
            return

        self.downloader = Downloader(url, self.save_path)
        self.downloader.progress_changed.connect(self._on_progress)
        self.downloader.finished_ok.connect(self._on_finished)
        self.downloader.cancelled.connect(self._on_cancelled)
        self.downloader.failed.connect(self._on_failed)
        self.downloader.start()

        # Log to console
        print(f"[download] Started downloading: {self.app_data.get('name')}")
        print(f"[download] URL: {url}")
        print(f"[download] To: {self.save_path}")

    def _on_progress(self, downloaded: int, total: int, speed: float) -> None:
        """Updates the progress bar and texts."""
        # Protection: if the dialog is already closing, ignore
        if self.downloader and self.downloader._closing:
            return

        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
        else:
            # If the server did not provide the size — show an "infinite" progress
            self.progress_bar.setRange(0, 0)

        # Format sizes
        dl_text = self._format_size(downloaded)
        total_text = self._format_size(total) if total else "?"
        speed_text = self._format_size(speed) + t("download.per_second")

        self.details_label.setText(f"{dl_text} / {total_text} · {speed_text}")

        # To console — too
        if total:
            percent = int(downloaded * 100 / total)
            print(f"[download] {percent}% ({dl_text}/{total_text}, {speed_text})")

    def _on_finished(self, path: str) -> None:
        """Success. Change the interface to "done"."""
        print(f"[download] Finished: {path}")

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.title_label.setText(f"{self.app_data.get('name', '')}")
        self.status_label.setText(t("download.done_status"))
        self.details_label.setText(t("download.saved_to", path=path))
        self.details_label.setWordWrap(True)

        # Change buttons
        self._swap_buttons_to_done(Path(path))

        # Auto-run, if enabled in the settings
        try:
            from app.core.user_settings import load_user_settings
            settings = load_user_settings()
            if settings.get("auto_run_after_download", False):
                print("[download] Auto-run is enabled — running the file")
                self._run_file(Path(path))
        except Exception as e:
            print(f"[download] Auto-run error: {e}")

    def _on_failed(self, error: str) -> None:
        if self.downloader and self.downloader._closing:
            return
        print(f"[download] Error: {error}")
        QMessageBox.critical(
            self,
            t("download.error_title"),
            t("download.error_text", error=error),
        )
        self.reject()

    def _on_cancel(self) -> None:
        """The "Cancel" button."""
        if self.downloader and self.downloader.isRunning():
            self.downloader.mark_closing()
            self.downloader.cancel()
            self.downloader.wait(3000)
        self.reject()

    def _on_cancelled(self) -> None:
        """The thread reported that the cancellation is done."""
        print("[download] Cancelled by the user")
        self.reject()

    # ------------------------------------------------------------------
    # Swap buttons after completion
    # ------------------------------------------------------------------
    def _swap_buttons_to_done(self, file_path: Path) -> None:
        # Remove old buttons
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.buttons_layout.addStretch(1)

        open_folder_btn = QPushButton(t("download.open_folder"))
        open_folder_btn.setObjectName("SecondaryButton")
        open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_btn.clicked.connect(lambda: self._open_folder(file_path))
        self.buttons_layout.addWidget(open_folder_btn)

        run_btn = QPushButton(t("download.run"))
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.clicked.connect(lambda: self._run_file(file_path))
        self.buttons_layout.addWidget(run_btn)

        close_btn = QPushButton(t("common.ok"))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        self.buttons_layout.addWidget(close_btn)

    def _open_folder(self, file_path: Path) -> None:
        """Opens the file explorer with the file selected."""
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(file_path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(file_path)])
        else:
            subprocess.Popen(["xdg-open", str(file_path.parent)])

    def _run_file(self, file_path: Path) -> None:
        """Runs the downloaded file."""
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(file_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception as e:
            QMessageBox.warning(
                self,
                t("common.error"),
                t("download.run_error", error=str(e)),
            )

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------
    def _format_size(self, size: float) -> str:
        """Converts bytes to a human-readable format."""
        for unit in [
            t("size.b"), t("size.kb"), t("size.mb"), t("size.gb")
        ]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} {t('size.tb')}"

    # ------------------------------------------------------------------
    # Close event (X button)
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        """
        Called when the window is closed (X button, Alt+F4).
        Properly stops the download thread.
        """
        if self.downloader and self.downloader.isRunning():
            print("[download] Dialog is closing — cancelling download")
            self.downloader.mark_closing()
            self.downloader.cancel()
            # Wait for the thread to finish (up to 3 seconds)
            if not self.downloader.wait(3000):
                print("[download] The thread did not finish in 3 sec — forcing")
        event.accept()