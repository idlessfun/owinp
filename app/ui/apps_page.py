"""
"Programs" page.

Inside — QStackedWidget with two states:
  0) List of program cards + search and category filter
  1) Details page of the selected program
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
)

from app.core.app_loader import load_all_apps
from app.core.cache_manager import find_icon
from app.core.translator import t
from app.ui.app_details_page import AppDetailsPage
from app.core.catalog_loader import CatalogLoader


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


class AppsPage(QWidget):
    """The "Programs" page — list, search, filter, details."""

    def __init__(self) -> None:
        super().__init__()

        # Load all programs once at startup
        self.all_apps: list[dict] = load_all_apps()
        self.filtered_apps: list[dict] = list(self.all_apps)
        # For the "Refresh" button
        self._reload_loader: CatalogLoader | None = None

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
        self.category_combo.addItem(t("apps.all_categories"))
        # Fill with categories from JSON
        categories = sorted({
            app.get("category", "").strip()
            for app in self.all_apps
            if app.get("category")
        })
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self._apply_filters)
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
        category = self.category_combo.currentText()
        all_categories = t("apps.all_categories")

        # Filter
        result = []
        for app in self.all_apps:
            # --- By category ---
            if category != all_categories:
                if app.get("category", "") != category:
                    continue

            # --- By search ---
            if query:
                haystack_parts = [
                    app.get("name", ""),
                    app.get("description", ""),
                    app.get("developer", ""),
                ]
                # Tags — it's a list, add all
                haystack_parts.extend(app.get("tags", []))
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
                card = AppCard(app_data)
                card.clicked.connect(self._show_details)
                self.cards_layout.addWidget(card)
            self.cards_layout.addStretch(1)

        # Update the counter
        self.counter_label.setText(
            t("apps.found", count=len(self.filtered_apps))
        )

    def _force_refresh(self) -> None:
        """Force-refreshes the catalog from GitHub and rebuilds the list."""
        print("[AppsPage] Forced catalog refresh...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(t("apps.refreshing"))

        self._reload_loader = CatalogLoader(force=True)
        self._reload_loader.finished_ok.connect(self._on_reload_finished)
        self._reload_loader.failed.connect(self._on_reload_failed)
        self._reload_loader.start()

    def _on_reload_finished(self, count: int) -> None:
        """Catalog updated — re-read the cache and rebuild the list."""
        print(f"[AppsPage] Updated files: {count}. Rebuilding list...")

        # Re-read data from the cache
        self.all_apps = load_all_apps()
        self.filtered_apps = list(self.all_apps)

        # Update the category list (new ones may have appeared)
        self._rebuild_categories()

        # Rebuild cards (with current search/filter)
        self._apply_filters()

        # Return the button to its original state
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(t("apps.refresh"))

    def _rebuild_categories(self) -> None:
        """Refills the category dropdown."""
        # Remember the current selection
        current = self.category_combo.currentText()

        # Block signals so we don't trigger filtering during refill
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem(t("apps.all_categories"))

        categories = sorted({
            app.get("category", "").strip()
            for app in self.all_apps
            if app.get("category")
        })
        self.category_combo.addItems(categories)

        # Restore the selection (if the category still exists)
        idx = self.category_combo.findText(current)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        else:
            self.category_combo.setCurrentIndex(0)  # reset to "All categories"

        self.category_combo.blockSignals(False)

    def _on_reload_failed(self, error: str) -> None:
        """Refresh error — report to the console."""
        print(f"[AppsPage] Refresh error: {error}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(t("apps.refresh"))

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
        from PySide6.QtWidgets import QFileDialog
        from app.ui.download_dialog import DownloadDialog

        # URL may come:
        # - from the button (data["_clicked_url"])
        # - from the old download_url field
        url = data.get("_clicked_url") or data.get("download_url", "")

        if not url:
            print("[AppsPage] No download URL for this program")
            return

        default_name = url.split("/")[-1] if url else "download.exe"

        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            t("apps.save_as"),
            default_name,
            "Executable files (*.exe);;All files (*.*)",
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

    def __init__(self, data: dict) -> None:
        super().__init__()

        self._data = data
        self.setObjectName("AppCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # --- Icon (cache first, then built-in) ---
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setObjectName("AppIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Look for the icon in the cache
        cached_icon = find_icon(data)
        icon_path = cached_icon

        # If not in the cache — try the built-in one
        if icon_path is None:
            icon_name = data.get("icon", "")
            if icon_name:
                candidate = ICONS_DIR / icon_name
                if candidate.exists():
                    icon_path = candidate

        if icon_path is not None:
            pixmap = QPixmap(str(icon_path)).scaled(
                64, 64,
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
        text_layout.setSpacing(4)

        name = QLabel(data.get("name", t("details.no_name")))
        name.setObjectName("AppName")

        description = QLabel(data.get("description", ""))
        description.setObjectName("AppDescription")
        description.setWordWrap(True)

        meta_parts = []
        if data.get("version"):
            meta_parts.append(f"v{data['version']}")
        if data.get("category"):
            meta_parts.append(data["category"])
        if data.get("size_mb"):
            meta_parts.append(f"{data['size_mb']} {t('size.mb')}")
        if data.get("license"):
            meta_parts.append(data["license"])

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