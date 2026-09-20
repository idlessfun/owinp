"""
Program details page.

Opens when a card is clicked in the list.
Shows: icon, name, developer, description,
specs, requirements, features, and action buttons.
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
)

from app.core.cache_manager import find_icon, find_screenshot
from app.core.translator import t


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "resources" / "screenshots"


class AppDetailsPage(QWidget):
    """
    Program details page.

    Signals:
        back_requested — emitted on "← Back" click.
                         AppsPage catches it and returns to the list.
        download_requested — emitted on "Download" click.
                             Passes app_data as argument.
    """

    back_requested = Signal()
    download_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()

        self._current_data: dict = {}

        # Outer vertical layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Top bar with "Back" button ----
        top_bar = QFrame()
        top_bar.setObjectName("DetailsTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 12, 20, 12)

        back_btn = QPushButton(t("details.back"))
        back_btn.setObjectName("BackButton")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        top_layout.addWidget(back_btn)

        top_layout.addStretch(1)

        outer.addWidget(top_bar)

        # ---- Scrollable content area ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("DetailsScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(40, 20, 40, 40)
        self.content_layout.setSpacing(24)

        scroll.setWidget(self.content)
        outer.addWidget(scroll, stretch=1)

    # ------------------------------------------------------------------
    # Filling the page with data
    # ------------------------------------------------------------------
    def set_app_data(self, data: dict) -> None:
        """Fills the page with the program data. Clears previous content."""
        self._current_data = data

        # Remove all widgets from the old content
        self._clear_layout(self.content_layout)

        # ---- Header: icon + name + developer + buttons ----
        self.content_layout.addWidget(self._build_header(data))

        # ---- Description ----
        long_desc = data.get("long_description") or data.get("description")
        if long_desc:
            self.content_layout.addWidget(
                self._build_section(t("details.section.description"), long_desc)
            )

        # ---- Specs (table) ----
        specs = self._build_specs(data)
        if specs:
            self.content_layout.addWidget(specs)

        # ---- Features ----
        features = data.get("features", [])
        if features:
            self.content_layout.addWidget(
                self._build_section(t("details.section.features"), None, features)
            )

        # ---- System requirements ----
        requirements = data.get("requirements", [])
        if requirements:
            self.content_layout.addWidget(
                self._build_section(t("details.section.requirements"), None, requirements)
            )

        # ---- Screenshots ----
        try:
            from app.core.user_settings import load_user_settings
            settings = load_user_settings()
            show_screenshots = settings.get("show_screenshots", True)
        except Exception:
            show_screenshots = True

        screenshots = data.get("screenshots", [])
        if screenshots and show_screenshots:
            self.content_layout.addWidget(
                self._build_screenshots(screenshots)
            )

        # Stretch at the end
        self.content_layout.addStretch(1)

    def _clear_layout(self, layout) -> None:
        """Removes all widgets and sub-layouts from the layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    # ------------------------------------------------------------------
    # Building page blocks
    # ------------------------------------------------------------------
    def _build_header(self, data: dict) -> QWidget:
        """Header: large icon, name, developer, action buttons."""

        header = QFrame()
        header.setObjectName("DetailsHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- Icon 96x96 (cache first, then built-in) ---
        icon_label = QLabel()
        icon_label.setFixedSize(96, 96)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("DetailsIcon")

        # Look for the icon in the cache
        icon_path = find_icon(data)

        # If not in cache — try the built-in one
        if icon_path is None:
            icon_name = data.get("icon", "")
            if icon_name:
                candidate = ICONS_DIR / icon_name
                if candidate.exists():
                    icon_path = candidate

        if icon_path is not None:
            pixmap = QPixmap(str(icon_path)).scaled(
                96, 96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("?")
            icon_label.setObjectName("DetailsIconPlaceholder")

        layout.addWidget(icon_label)

        # --- Text block ---
        text_block = QVBoxLayout()
        text_block.setSpacing(6)

        name = QLabel(data.get("name", t("details.no_name")))
        name.setObjectName("DetailsName")

        developer = data.get("developer", "")
        if developer:
            dev_label = QLabel(t("details.developer", name=developer))
            dev_label.setObjectName("DetailsDeveloper")
            text_block.addWidget(name)
            text_block.addWidget(dev_label)
        else:
            text_block.addWidget(name)

        short_desc = data.get("description", "")
        if short_desc:
            desc = QLabel(short_desc)
            desc.setObjectName("DetailsShortDesc")
            desc.setWordWrap(True)
            text_block.addWidget(desc)

        layout.addLayout(text_block, stretch=1)

        # --- Action buttons (right) ---
        actions = QVBoxLayout()
        actions.setSpacing(8)

        # Get the list of download buttons
        download_buttons = self._get_download_buttons(data)

        for btn_info in download_buttons:
            label = btn_info.get("label", t("details.download"))
            url = btn_info.get("url", "")
            is_primary = btn_info.get("primary", False)
            btn_type = btn_info.get("type", "download")

            if not url:
                continue

            btn = QPushButton(label)
            btn.setObjectName("PrimaryButton" if is_primary else "SecondaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedWidth(180)
            # Pass data, URL, and button type to the signal
            btn.clicked.connect(
                lambda _, u=url, d=data, bt=btn_type: self._on_download_clicked(u, d, bt)
            )
            actions.addWidget(btn)

        # "Open website" button — separately
        website = data.get("website", "")
        if website:
            site_btn = QPushButton(t("details.open_website"))
            site_btn.setObjectName("SecondaryButton")
            site_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            site_btn.setFixedWidth(180)
            site_btn.clicked.connect(lambda: self._open_website(website))
            actions.addWidget(site_btn)

        actions.addStretch(1)
        layout.addLayout(actions)

        return header

    def _build_section(
        self, title: str, text: str | None, items: list | None = None
    ) -> QWidget:
        """
        Universal section block.
        If text is given — shows a paragraph.
        If items are given — shows a bulleted list.
        """

        section = QFrame()
        section.setObjectName("DetailsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(title)
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        if text:
            body = QLabel(text)
            body.setObjectName("SectionText")
            body.setWordWrap(True)
            layout.addWidget(body)

        if items:
            for item in items:
                bullet = QLabel(f"•  {item}")
                bullet.setObjectName("SectionBullet")
                bullet.setWordWrap(True)
                layout.addWidget(bullet)

        return section

    def _build_specs(self, data: dict) -> QWidget | None:
        """Block with specs: version, size, license, category, etc."""

        rows = []
        if data.get("version"):
            rows.append((t("details.spec.version"), data["version"]))
        if data.get("release_date"):
            rows.append((t("details.spec.release_date"), data["release_date"]))
        if data.get("category"):
            rows.append((t("details.spec.category"), data["category"]))
        if data.get("size_mb"):
            rows.append((t("details.spec.size"), f"{data['size_mb']} {t('size.mb')}"))
        if data.get("license"):
            rows.append((t("details.spec.license"), data["license"]))

        if not rows:
            return None

        section = QFrame()
        section.setObjectName("DetailsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(t("details.section.specs"))
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        for label, value in rows:
            row = QHBoxLayout()
            key = QLabel(label)
            key.setObjectName("SpecKey")
            key.setFixedWidth(140)

            val = QLabel(str(value))
            val.setObjectName("SpecValue")

            row.addWidget(key)
            row.addWidget(val, stretch=1)
            layout.addLayout(row)

        return section

    def _build_screenshots(self, screenshots: list) -> QWidget:
        """Block with screenshots."""

        section = QFrame()
        section.setObjectName("DetailsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(t("details.section.screenshots"))
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        # Try two sources: "screenshots" (names) and "screenshots_urls" (URLs)
        names = self._current_data.get("screenshots", [])
        urls = self._current_data.get("screenshots_urls", [])

        # First — by names (our screenshots)
        for name in names:
            shot_path = find_screenshot(self._current_data, name)
            if shot_path is None:
                # Fallback: built-in screenshot
                builtin = SCREENSHOTS_DIR / name
                if builtin.exists():
                    shot_path = builtin

            if shot_path is None:
                continue

            self._add_screenshot_to_layout(shot_path, layout)

        # Then — by external URLs (indices)
        for idx in range(len(urls)):
            shot_path = find_screenshot(self._current_data, idx)
            if shot_path is None:
                continue

            self._add_screenshot_to_layout(shot_path, layout)

        return section

    def _add_screenshot_to_layout(self, shot_path: Path, layout) -> None:
        """Loads an image, scales to 600px wide, adds it to the layout."""
        if not shot_path.exists():
            return

        pixmap = QPixmap(str(shot_path))
        if pixmap.isNull():
            print(f"[details] Broken screenshot: {shot_path.name}")
            return

        scaled = pixmap.scaledToWidth(
            600,
            Qt.TransformationMode.SmoothTransformation,
        )

        img_label = QLabel()
        img_label.setPixmap(scaled)
        img_label.setObjectName("Screenshot")
        layout.addWidget(img_label)

    def _get_download_buttons(self, data: dict) -> list[dict]:
        """
        Returns a list of download buttons.

        Supports two formats:
        1. New: "downloads" field — list of dicts with label/url/primary
        2. Old: "download_url" field — converted to a single button

        Returns a list of dicts:
        [{"label": str, "url": str, "primary": bool}, ...]
        """
        # Priority — new format
        downloads = data.get("downloads", [])
        if isinstance(downloads, list) and downloads:
            result = []
            for item in downloads:
                if not isinstance(item, dict):
                    continue
                result.append({
                    "label": item.get("label", t("details.download")),
                    "url": item.get("url", ""),
                    "primary": bool(item.get("primary", False)),
                    "type": item.get("type", "download"),
                })
            if result:
                return result

        # Fallback — old format
        old_url = data.get("download_url", "")
        if old_url:
            return [{
                "label": t("details.download"),
                "url": old_url,
                "primary": True,
            }]

        return []

    def _on_download_clicked(
        self, url: str, data: dict, btn_type: str = "download"
    ) -> None:
        """
        One of the buttons is clicked.

        btn_type = "download" — download the file (emit signal)
        btn_type = "link"     — open the link in the browser
        """
        if btn_type == "link":
            # Open the link in the browser
            print(f"[details] Opening link: {url}")
            self._open_website(url)
            return

        # By default — download
        payload = dict(data)          # copy
        payload["_clicked_url"] = url  # add the URL that was clicked
        self.download_requested.emit(payload)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _open_website(self, url: str) -> None:
        """Opens the website in the system browser."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))