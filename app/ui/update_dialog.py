"""
A dialog box with information about the update.
It displays the version, release notes, and action buttons.
"""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
)

from app.core.translator import t
from app.ui.theme_helper import get_dialog_qss

class UpdateDialog(QDialog):
    """
    A window displaying information about an available update.

    Shows: the title, the current and new versions, the release notes
    (in GitHub Markdown format), and the «Download» and «Later» buttons.
    """

    def __init__(self, info: dict, current_version: str, parent=None) -> None:
        super().__init__(parent)

        self.info = info
        self.current_version = current_version

        self.setWindowTitle(t("dialog.update.title"))
        self.setModal(True)
        self.resize(640, 560)
        self.setMinimumSize(500, 400)

        self._build_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # Building the Interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Title ---
        title = QLabel(t("dialog.update.header"))
        title.setObjectName("UpdateTitle")
        layout.addWidget(title)

        # --- Version ---
        versions_layout = QHBoxLayout()
        versions_layout.setSpacing(8)

        current_label = QLabel(t("dialog.update.current", version=self.current_version))
        current_label.setObjectName("VersionCurrent")

        arrow = QLabel("→")
        arrow.setObjectName("VersionArrow")

        new_label = QLabel(t("dialog.update.new", version=self.info.get('version', '?')))
        new_label.setObjectName("VersionNew")

        versions_layout.addWidget(current_label)
        versions_layout.addWidget(arrow)
        versions_layout.addWidget(new_label)
        versions_layout.addStretch(1)

        layout.addLayout(versions_layout)

        # --- What's New (Markdown from GitHub) ---
        what_new_title = QLabel(t("dialog.update.whats_new"))
        what_new_title.setObjectName("SectionLabel")
        layout.addWidget(what_new_title)

        # QTextBrowser can render Markdown
        self.body_browser = QTextBrowser()
        self.body_browser.setObjectName("ReleaseBody")
        self.body_browser.setOpenExternalLinks(True)

        body_text = self.info.get("body", "").strip()
        if not body_text:
            body_text = t("dialog.update.no_description")

        # setMarkdown — converts ## and ** into nice formatting
        try:
            self.body_browser.setMarkdown(body_text)
        except AttributeError:
            # Older versions of PySide6 may not include setMarkdown
            self.body_browser.setPlainText(body_text)

        layout.addWidget(self.body_browser, stretch=1)

        # --- Publication Date ---
        published = self.info.get("published_at", "")
        if published:
            date_label = QLabel(t("dialog.update.date", date=published[:10]))
            date_label.setObjectName("DateLabel")
            layout.addWidget(date_label)

        # --- Buttons ---
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addStretch(1)

        later_btn = QPushButton(t("dialog.update.later"))
        later_btn.setObjectName("SecondaryButton")
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(later_btn)

        download_btn = QPushButton(t("dialog.update.download"))
        download_btn.setObjectName("PrimaryButton")
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.clicked.connect(self._open_release_page)
        buttons_layout.addWidget(download_btn)

        layout.addLayout(buttons_layout)

    # ------------------------------------------------------------------
    # Processors
    # ------------------------------------------------------------------
    def _open_release_page(self) -> None:
        """Opens the release page in the browser."""
        url = self.info.get("url", "")
        if url:
            print(f"[updater] Open in a browser: {url}")
            webbrowser.open(url)
        self.accept()

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        extra_qss = """
            #UpdateTitle {
                font-size: 20px;
                font-weight: 700;
                color: __TEXT_PRIMARY__;
            }

            #VersionCurrent {
                font-size: 14px;
                color: __TEXT_SECONDARY__;
            }

            #VersionArrow {
                font-size: 14px;
                color: __ACCENT__;
            }

            #VersionNew {
                font-size: 14px;
                color: __ACCENT__;
                font-weight: 700;
            }

            #SectionLabel {
                font-size: 13px;
                color: __TEXT_SECONDARY__;
                margin-top: 8px;
            }

            #ReleaseBody {
                background-color: __CARD__;
                color: __TEXT_NORMAL__;
                border: 1px solid __BORDER__;
                border-radius: 10px;
                padding: 14px;
                font-size: 13px;
                selection-background-color: __ACCENT_SOFT__;
            }

            #DateLabel {
                font-size: 12px;
                color: __ACCENT__;
            }
        """
        self.setStyleSheet(get_dialog_qss(extra_qss))