"""
"Programs" page.

Inside — QStackedWidget with two states:
  0) List of program cards + search and category filter
  1) Details page of the selected program
"""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QStackedWidget,
    QLineEdit,
    QComboBox,
    QFileDialog,
)

from app.core.app_loader import load_all_apps
from app.core.cache_manager import find_icon
from app.core.translator import t
from app.core.user_settings import load_user_settings
from app.ui.app_details_page import AppDetailsPage


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


class AppsPage(QWidget):
    """The "Programs" page — list, search, filter, details."""

    # Emitted when the user asks for a fresh catalog from GitHub.
    # The main window owns the only CatalogLoader, so two refreshes can
    # never write to the cache at the same time.
    refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        # Load all programs once at startup
        self.all_apps: list[dict] = [
            app for app in load_all_apps() if isinstance(app, dict)
        ]
        self.filtered_apps: list[dict] = list(self.all_apps)

        settings = load_user_settings()
        self.compact_mode: bool = bool(settings.get("compact_mode", False))

        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Stack of pages: 0 — list, 1 — details
        self.stack = QStackedWidget()

        # --- Page 0: list ---
        self.list_page = self._build_list_page()
        self.stack.addWidget(self.list_page)

        # --- Page 1: details ---
        self.details_page = AppDetailsPage()
        self.details_page.back_requested.connect(self._show_list)
        self.details_page.download_requested.connect(self._on_download_clicked)
        self.stack.addWidget(self.details_page)

        outer.addWidget(self.stack)

        # By default — list
        self.stack.setCurrentIndex(0)

        # Initial fill of the list
        self._populate_categories()
        self._apply_filters()

    # ------------------------------------------------------------------
    # Building the list page
    # ------------------------------------------------------------------
    def _build_list_page(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # Title
        title = QLabel(t("apps.title"))
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ---- Toolbar: search + category + counter ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # "Refresh catalog" button
        self.refresh_btn = QPushButton(t("apps.refresh"))
        self.refresh_btn.setObjectName("RefreshButton")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.clicked.connect(self._force_refresh)
        toolbar.addWidget(self.refresh_btn)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText(t("apps.search_placeholder"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_input, stretch=1)

        # Category dropdown
        self.category_combo = QComboBox()
        self.category_combo.setObjectName("CategoryCombo")
        self.category_combo.setFixedWidth(220)
        self.category_combo.addItem(t("apps.all_categories"), None)
        self.category_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.category_combo)

        # Counter
        self.counter_label = QLabel("")
        self.counter_label.setObjectName("CounterLabel")
        self.counter_label.setFixedWidth(120)
        self.counter_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        toolbar.addWidget(self.counter_label)

        layout.addLayout(toolbar)

        # ---- Scrollable area with cards ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("AppsScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, stretch=1)

        return page

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def _apply_filters(self) -> None:
        """Applies search and category filter, then redraws the list."""
        query = self.search_input.text().strip().lower()
        category = self.category_combo.currentData()

        # Filter
        result = []
        for app in self.all_apps:
            if not isinstance(app, dict):
                continue

            # --- By category (stored as item data, not display text) ---
            if category and app.get("category", "") != category:
                continue

            # --- By search ---
            if query:
                haystack_parts = [
                    str(app.get("name", "")),
                    str(app.get("description", "")),
                    str(app.get("developer", "")),
                ]
                # Tags — it's a list, add all
                tags = app.get("tags", [])
                if isinstance(tags, list):
                    haystack_parts.extend(str(tag) for tag in tags)
                haystack = " ".join(haystack_parts).lower()

                if query not in haystack:
                    continue

            result.append(app)

        self.filtered_apps = result
        self._redraw_cards()

    def _redraw_cards(self) -> None:
        """Clears the container and recreates the cards."""
        # Clear old widgets
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # If empty — show a message
        if not self.filtered_apps:
            if not self.all_apps:
                message = t("apps.empty_no_apps")
            else:
                message = t("apps.empty_not_found")

            empty = QLabel(message)
            empty.setObjectName("EmptyMessage")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.cards_layout.addWidget(empty)
            self.cards_layout.addStretch(1)
        else:
            for app_data in self.filtered_apps:
                card = AppCard(app_data, compact=self.compact_mode)
                card.clicked.connect(self._show_details)
                self.cards_layout.addWidget(card)
            self.cards_layout.addStretch(1)

        # Update the counter
        self.counter_label.setText(
            t("apps.found", count=len(self.filtered_apps))
        )

    def _populate_categories(self) -> None:
        """Refills the category dropdown, preserving the current selection."""
        current = self.category_combo.currentData()

        # Block signals so we don't trigger filtering during refill
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem(t("apps.all_categories"), None)

        categories = sorted({
            str(app.get("category", "")).strip()
            for app in self.all_apps
            if isinstance(app, dict) and str(app.get("category", "")).strip()
        })

        for category in categories:
            self.category_combo.addItem(category, category)

        # Restore the selection (if the category still exists)
        idx = self.category_combo.findData(current)
        self.category_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.category_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------
    def _force_refresh(self) -> None:
        """Asks the main window for a fresh catalog."""
        if not self.refresh_btn.isEnabled():
            return

        print("[AppsPage] Forced catalog refresh requested...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(t("apps.refreshing"))
        self.refresh_requested.emit()

    def finish_refresh(self) -> None:
        """Returns the "Refresh" button to its normal state."""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(t("apps.refresh"))

    def reload_from_cache(self) -> None:
        """Re-reads the catalog and rebuilds the list with current filters."""
        print("[AppsPage] Reloading the catalog from the cache...")

        self.all_apps = [
            app for app in load_all_apps() if isinstance(app, dict)
        ]

        # New categories may have appeared
        self._populate_categories()

        # Rebuild cards (with current search/filter)
        self._apply_filters()

    def set_compact_mode(self, enabled: bool) -> None:
        """Switches between normal and compact cards."""
        enabled = bool(enabled)
        if enabled == self.compact_mode:
            return

        self.compact_mode = enabled
        self._redraw_cards()

    # ------------------------------------------------------------------
    # Page switching
    # ------------------------------------------------------------------
    def _show_details(self, data: dict) -> None:
        print(f"[AppsPage] Open page: {data.get('name')}")
        self.details_page.set_app_data(data)
        self.stack.setCurrentIndex(1)

    def _show_list(self) -> None:
        self.stack.setCurrentIndex(0)

    def _on_download_clicked(self, data: dict) -> None:
        """Opens the "Save as" dialog, then starts the download."""
        from app.ui.download_dialog import DownloadDialog

        # URL may come:
        # - from the button (data["_clicked_url"])
        # - from the old download_url field
        url = data.get("_clicked_url") or data.get("download_url", "")

        if not url:
            print("[AppsPage] No download URL for this program")
            return

        # Build a safe default name: strip query strings, keep only the basename
        parsed = urlsplit(str(url))
        default_name = unquote(Path(parsed.path).name) or "download.exe"

        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        initial_path = (
            str(Path(downloads_dir) / default_name)
            if downloads_dir
            else default_name
        )

        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            t("apps.save_as"),
            initial_path,
            "Installers (*.exe *.msi);;All files (*.*)",
        )

        if not save_path_str:
            print("[AppsPage] Download cancelled at the path selection stage")
            return

        save_path = Path(save_path_str)
        dialog = DownloadDialog(data, save_path, parent=self)
        dialog.exec()


class AppCard(QFrame):
    """
    Program card in the list.

    The clicked signal is emitted when the card or the "Details" button is clicked.
    """

    clicked = Signal(dict)

    def __init__(self, data: dict, compact: bool = False) -> None:
        super().__init__()

        self._data = data
        self.setObjectName("AppCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        icon_size = 48 if compact else 64
        margin = 10 if compact else 16

        layout = QHBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(12 if compact else 16)

        # --- Icon (cache first, then built-in) ---
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setObjectName("AppIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Look for the icon in the cache
        icon_path = find_icon(data)

        # If not in the cache — try the built-in one
        if icon_path is None:
            icon_name = data.get("icon", "")
            if isinstance(icon_name, str) and icon_name:
                candidate = ICONS_DIR / Path(icon_name).name
                if candidate.exists():
                    icon_path = candidate

        if icon_path is not None:
            pixmap = QPixmap(str(icon_path)).scaled(
                icon_size, icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("?")
            icon_label.setObjectName("AppIconPlaceholder")

        layout.addWidget(icon_label)

        # --- Text ---
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4 if not compact else 2)

        name = QLabel(str(data.get("name", t("details.no_name"))))
        name.setObjectName("AppName")

        description = QLabel(str(data.get("description", "")))
        description.setObjectName("AppDescription")
        description.setWordWrap(True)

        meta_parts = []
        if data.get("version"):
            meta_parts.append(f"v{data['version']}")
        if data.get("category"):
            meta_parts.append(str(data["category"]))
        if data.get("size_mb"):
            meta_parts.append(f"{data['size_mb']} {t('size.mb')}")
        if data.get("license"):
            meta_parts.append(str(data["license"]))

        meta = QLabel(" · ".join(meta_parts))
        meta.setObjectName("AppMeta")

        text_layout.addWidget(name)
        text_layout.addWidget(description)
        text_layout.addWidget(meta)

        layout.addLayout(text_layout, stretch=1)

        # --- "Details" button ---
        details_btn = QPushButton(t("apps.details_button"))
        details_btn.setObjectName("DownloadButton")
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setFixedWidth(120)
        details_btn.clicked.connect(lambda: self.clicked.emit(self._data))

        layout.addWidget(details_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event) -> None:
        """Click on the card itself (not the button) opens the page."""
        child = self.childAt(event.position().toPoint())
        if isinstance(child, QPushButton):
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._data)
        super().mousePressEvent(event)
