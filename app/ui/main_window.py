"""
The main window of the OWINP application.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QApplication,
)

from app import __version__
from app.core.updater import UpdateChecker
from app.core.catalog_loader import CatalogLoader
from app.core.user_settings import (
    load_user_settings,
    save_user_settings,
    get_user_settings_path,
    get_theme,
    THEMES,
    DEFAULT_THEME,
    FONT_SIZES,
    DEFAULTS,
)

from app.core.translator import (
    t,
    set_language,
    detect_system_language,
    load_available_languages,
)

from app.ui.apps_page import AppsPage
from app.ui.update_dialog import UpdateDialog


class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self) -> None:
        super().__init__()

        # Updates / Catalog
        self._update_info: dict | None = None
        self._checker: UpdateChecker | None = None
        self._catalog_loader: CatalogLoader | None = None
        self._manual_check = False

        # User settings (theme, font, etc.)
        self.user_settings = load_user_settings()

        # Set the UI language (from settings, or auto-detect if not set)
        lang = self.user_settings.get("language", "")
        if not lang:
            lang = detect_system_language()
            self.user_settings["language"] = lang
            save_user_settings(self.user_settings)
        set_language(lang)
        print(f"[main] UI language: {lang}")

        self.setWindowTitle(f"OWINP — Open Windows Programs v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._build_ui()
        self._apply_styles()

        # Run checks only if they are enabled in the settings
        if self.user_settings.get("check_updates_on_start", True):
            QTimer.singleShot(2000, self._check_for_updates)
        else:
            print("[main] Check for updates is disabled in the settings")

        if self.user_settings.get("refresh_catalog_on_start", True):
            QTimer.singleShot(3000, self._refresh_catalog)
        else:
            print("[main] Catalog updates are disabled in the settings")

    # ------------------------------------------------------------------
    # Building the Interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.update_banner = self._build_update_banner()
        self.update_banner.setVisible(False)
        main_layout.addWidget(self.update_banner)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        self.content_area = self._build_content_area()
        root_layout.addWidget(self.content_area, stretch=1)

        main_layout.addWidget(body, stretch=1)

        self.nav_list.setCurrentRow(0)

    def _build_update_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("UpdateBanner")
        banner.setFixedHeight(44)

        layout = QHBoxLayout(banner)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(12)

        text = QLabel(t("banner.new_version"))
        text.setObjectName("BannerText")
        layout.addWidget(text)

        layout.addStretch(1)

        what_new_btn = QPushButton(t("banner.whats_new"))
        what_new_btn.setObjectName("BannerButton")
        what_new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        what_new_btn.clicked.connect(self._show_update_dialog)
        layout.addWidget(what_new_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("BannerClose")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.update_banner.setVisible(False))
        layout.addWidget(close_btn)

        return banner

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(0)

        logo = QLabel("OWINP")
        logo.setObjectName("Logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        layout.addSpacing(20)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")

        sections = [
            t("nav.home"),
            t("nav.programs"),
            t("nav.settings"),
        ]
        for name in sections:
            QListWidgetItem(name, self.nav_list)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        layout.addWidget(self.nav_list, stretch=1)

        return sidebar

    def _build_content_area(self) -> QWidget:
        stack = QStackedWidget()

        # Home
        home = QWidget()
        home_layout = QVBoxLayout(home)
        home_layout.setContentsMargins(40, 40, 40, 40)
        home_layout.setSpacing(16)

        title = QLabel(t("home.title"))
        title.setObjectName("PageTitle")

        subtitle = QLabel(t("home.subtitle", version=__version__))
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        home_layout.addWidget(title)
        home_layout.addWidget(subtitle)
        home_layout.addSpacing(20)

        check_btn = QPushButton(t("home.check_updates"))
        check_btn.setObjectName("PrimaryButton")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.setFixedWidth(240)
        check_btn.clicked.connect(self._manual_check_for_updates)
        home_layout.addWidget(check_btn)

        clear_cache_btn = QPushButton(t("home.clear_cache"))
        clear_cache_btn.setObjectName("SecondaryButton")
        clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_cache_btn.setFixedWidth(240)
        clear_cache_btn.clicked.connect(self._clear_cache_clicked)
        home_layout.addWidget(clear_cache_btn)

        home_layout.addStretch(1)
        stack.addWidget(home)

        # Programs
        apps_page = AppsPage()
        stack.addWidget(apps_page)

        # Settings
        settings_page = self._build_settings_page()
        stack.addWidget(settings_page)

        return stack

    def _build_settings_page(self) -> QWidget:
        """“Settings” page — theme, font, behavior."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(40, 30, 40, 30)
        outer.setSpacing(16)

        title = QLabel(t("settings.title"))
        title.setObjectName("PageTitle")
        outer.addWidget(title)

        subtitle = QLabel(t("settings.subtitle"))
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # Scrollable Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("FormScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(16)

        # --- “Interface” Section ---
        layout.addWidget(self._build_settings_interface())

        # --- “Network and Updates” Section ---
        layout.addWidget(self._build_settings_network())

        # --- “Downloads” Section ---
        layout.addWidget(self._build_settings_download())

        # --- “Program Page” Section ---
        layout.addWidget(self._build_settings_app_page())

        layout.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # --- Reset Button ---
        buttons = QHBoxLayout()
        reset_btn = QPushButton(t("settings.reset_all"))
        reset_btn.setObjectName("SecondaryButton")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setFixedWidth(280)
        reset_btn.clicked.connect(self._reset_all_settings)
        buttons.addWidget(reset_btn)
        buttons.addStretch(1)
        outer.addLayout(buttons)

        # --- File Path ---
        path_label = QLabel(t("settings.config_file", path=get_user_settings_path()))
        path_label.setObjectName("SettingsPath")
        path_label.setWordWrap(True)
        outer.addWidget(path_label)

        return page

    def _build_settings_interface(self) -> QGroupBox:
        """The ‘Interface’ section."""
        group = QGroupBox(t("settings.section.interface"))
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        # Themes
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("SettingsInput")
        self.theme_combo.setFixedWidth(320)
        for theme_id, theme_data in THEMES.items():
            self.theme_combo.addItem(theme_data["name"], theme_id)
        current_theme = self.user_settings.get("theme", DEFAULT_THEME)
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(t("settings.theme"), self.theme_combo)

        # Font Size
        self.font_size_combo = QComboBox()
        self.font_size_combo.setObjectName("SettingsInput")
        self.font_size_combo.setFixedWidth(320)
        for size in FONT_SIZES:
            self.font_size_combo.addItem(f"{size} px", size)
        current_size = self.user_settings.get("font_size", 14)
        idx = self.font_size_combo.findData(current_size)
        if idx >= 0:
            self.font_size_combo.setCurrentIndex(idx)
        self.font_size_combo.currentIndexChanged.connect(self._on_font_size_changed)
        form.addRow(t("settings.font_size"), self.font_size_combo)

        # Language
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("SettingsInput")
        self.language_combo.setFixedWidth(320)
        available_langs = load_available_languages()
        for lang in available_langs:
            self.language_combo.addItem(lang["name"], lang["code"])
        current_lang = self.user_settings.get("language", "en")
        idx = self.language_combo.findData(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        form.addRow(t("settings.language"), self.language_combo)

        # Compact mode
        self.compact_check = QCheckBox(t("settings.compact_mode"))
        self.compact_check.setChecked(self.user_settings.get("compact_mode", False))
        self.compact_check.toggled.connect(
            lambda v: self._on_setting_toggled("compact_mode", v)
        )
        form.addRow("", self.compact_check)

        # Animations (placeholder for future use)
        self.animations_check = QCheckBox(t("settings.animations"))
        self.animations_check.setChecked(self.user_settings.get("animations_enabled", True))
        self.animations_check.toggled.connect(
            lambda v: self._on_setting_toggled("animations_enabled", v)
        )
        form.addRow("", self.animations_check)

        return group

    def _build_settings_network(self) -> QGroupBox:
        """«Network and Updates» section."""
        group = QGroupBox(t("settings.section.network"))
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        # Check for Updates Automatically
        self.check_updates_check = QCheckBox(t("settings.check_updates_on_start"))
        self.check_updates_check.setChecked(
            self.user_settings.get("check_updates_on_start", True)
        )
        self.check_updates_check.toggled.connect(
            lambda v: self._on_setting_toggled("check_updates_on_start", v)
        )
        form.addRow("", self.check_updates_check)

        # Automatic Catalog Update
        self.refresh_catalog_check = QCheckBox(t("settings.refresh_catalog_on_start"))
        self.refresh_catalog_check.setChecked(
            self.user_settings.get("refresh_catalog_on_start", True)
        )
        self.refresh_catalog_check.toggled.connect(
            lambda v: self._on_setting_toggled("refresh_catalog_on_start", v)
        )
        form.addRow("", self.refresh_catalog_check)

        # Show banner
        self.show_banner_check = QCheckBox(t("settings.show_update_banner"))
        self.show_banner_check.setChecked(
            self.user_settings.get("show_update_banner", True)
        )
        self.show_banner_check.toggled.connect(
            lambda v: self._on_setting_toggled("show_update_banner", v)
        )
        form.addRow("", self.show_banner_check)

        return group

    def _build_settings_download(self) -> QGroupBox:
        """“Downloads» section»."""
        group = QGroupBox(t("settings.section.download"))
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        self.auto_run_check = QCheckBox(t("settings.auto_run"))
        self.auto_run_check.setChecked(
            self.user_settings.get("auto_run_after_download", False)
        )
        self.auto_run_check.toggled.connect(
            lambda v: self._on_setting_toggled("auto_run_after_download", v)
        )
        form.addRow("", self.auto_run_check)

        return group

    def _build_settings_app_page(self) -> QGroupBox:
        """«Program Page» section."""
        group = QGroupBox(t("settings.section.program_page"))
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        self.show_screenshots_check = QCheckBox(t("settings.show_screenshots"))
        self.show_screenshots_check.setChecked(
            self.user_settings.get("show_screenshots", True)
        )
        self.show_screenshots_check.toggled.connect(
            lambda v: self._on_setting_toggled("show_screenshots", v)
        )
        form.addRow("", self.show_screenshots_check)

        return group

    # ------------------------------------------------------------------
    # Settings Handlers
    # ------------------------------------------------------------------
    def _on_theme_changed(self) -> None:
        """Applies the selected theme."""
        theme_id = self.theme_combo.currentData()
        if not theme_id:
            return
        self.user_settings["theme"] = theme_id
        print(f"[main] New theme: {theme_id}")
        save_user_settings(self.user_settings)
        self._apply_styles()

    def _on_font_size_changed(self) -> None:
        """Applies the selected font size."""
        size = self.font_size_combo.currentData()
        if not size:
            return
        self.user_settings["font_size"] = size
        print(f"[main] New font size: {size}")
        save_user_settings(self.user_settings)
        self._apply_styles()

    def _on_language_changed(self) -> None:
        """Asks the user to restart the app manually to apply the new language."""
        lang_code = self.language_combo.currentData()
        if not lang_code:
            return
        if lang_code == self.user_settings.get("language", "en"):
            return

        self.user_settings["language"] = lang_code
        save_user_settings(self.user_settings)
        print(f"[main] New language: {lang_code}")

        QMessageBox.information(
            self,
            t("dialog.restart.title"),
            t("dialog.restart.text"),
        )

    def _on_setting_toggled(self, key: str, value: bool) -> None:
        """Checkbox toggle handler."""
        self.user_settings[key] = value
        print(f"[main] {key} = {value}")
        save_user_settings(self.user_settings)

        # If you've made a change that affects the UI, apply it immediately
        if key == "show_update_banner" and not value:
            self.update_banner.setVisible(False)

        if key == "compact_mode":
            self._apply_styles()

    def _reset_all_settings(self) -> None:
        """Resets all settings to their defaults."""
        answer = QMessageBox.question(
            self,
            t("dialog.reset_settings.title"),
            t("dialog.reset_settings.text"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Clear the memory
        self.user_settings = dict(DEFAULTS)
        save_user_settings(self.user_settings)

        # Updating UI Controls
        self._sync_settings_ui()

        # Applying Styles
        self._apply_styles()
        print("[main] All settings have been reset to their defaults")

    def _sync_settings_ui(self) -> None:
        """Updates the values of UI controls from self.user_settings."""
        # Theme
        idx = self.theme_combo.findData(self.user_settings.get("theme", DEFAULT_THEME))
        if idx >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)

        # Font Size
        idx = self.font_size_combo.findData(self.user_settings.get("font_size", 14))
        if idx >= 0:
            self.font_size_combo.blockSignals(True)
            self.font_size_combo.setCurrentIndex(idx)
            self.font_size_combo.blockSignals(False)

        # Language
        idx = self.language_combo.findData(self.user_settings.get("language", "en"))
        if idx >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(idx)
            self.language_combo.blockSignals(False)

        # Checkboxes
        for key, checkbox in [
            ("compact_mode", self.compact_check),
            ("animations_enabled", self.animations_check),
            ("check_updates_on_start", self.check_updates_check),
            ("refresh_catalog_on_start", self.refresh_catalog_check),
            ("show_update_banner", self.show_banner_check),
            ("auto_run_after_download", self.auto_run_check),
            ("show_screenshots", self.show_screenshots_check),
        ]:
            checkbox.blockSignals(True)
            checkbox.setChecked(self.user_settings.get(key, False))
            checkbox.blockSignals(False)

    # ------------------------------------------------------------------
    # Navigation Handlers
    # ------------------------------------------------------------------
    def _on_nav_changed(self, index: int) -> None:
        if 0 <= index < self.content_area.count():
            self.content_area.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------
    def _check_for_updates(self) -> None:
        self._manual_check = False
        self._checker = UpdateChecker(force=False)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _manual_check_for_updates(self) -> None:
        print("[main] Manually Check for Updates")
        self._manual_check = True
        self._checker = UpdateChecker(force=True)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _on_update_available(self, info: dict) -> None:
        """If there's an update, display a banner (if enabled in the settings)."""
        self._update_info = info
        show_banner = self.user_settings.get("show_update_banner", True)
        if show_banner:
            self.update_banner.setVisible(True)
            print(f"[main] An update banner is displayed: v{info.get('version')}")
        else:
            print(f"[main] The banner is disabled, but there is an update: v{info.get('version')}")

        if self._manual_check:
            self._manual_check = False
            self._show_update_dialog()

    def _on_no_update(self) -> None:
        print("[main] No updates")
        if self._manual_check:
            self._manual_check = False
            QMessageBox.information(
                self,
                t("dialog.updates.title"),
                t("dialog.updates.latest", version=__version__),
            )

    def _on_check_failed(self, error: str) -> None:
        print(f"[main] Failed to check for updates: {error}")
        if self._manual_check:
            self._manual_check = False
            QMessageBox.warning(
                self,
                t("dialog.updates.error_title"),
                t("dialog.updates.error_text", error=error),
            )

    def _show_update_dialog(self) -> None:
        if not self._update_info:
            return
        dialog = UpdateDialog(self._update_info, __version__, parent=self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------
    def _refresh_catalog(self, force: bool = False) -> None:
        self._catalog_loader = CatalogLoader(force=force)
        self._catalog_loader.finished_ok.connect(self._on_catalog_updated)
        self._catalog_loader.failed.connect(self._on_catalog_failed)
        self._catalog_loader.start()

    def _on_catalog_updated(self, count: int) -> None:
        if count > 0:
            print(f"[main] Catalog Updated: {count} files")
        else:
            print("[main] Catalog remains unchanged")

    def _on_catalog_failed(self, error: str) -> None:
        print(f"[main] The catalog has not been updated: {error}")

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------
    def _clear_cache_clicked(self) -> None:
        from app.core.cache_manager import clear_cache, clear_assets_cache

        answer = QMessageBox.question(
            self,
            t("dialog.cache.title"),
            t("dialog.cache.text"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        ok_json = clear_cache()
        ok_assets = clear_assets_cache()

        if ok_json and ok_assets:
            QMessageBox.information(
                self,
                t("dialog.cache.ok_title"),
                t("dialog.cache.ok_text"),
            )
            print("[main] The cache was cleared by the user")
        else:
            QMessageBox.warning(
                self,
                t("dialog.cache.error_title"),
                t("dialog.cache.error_text"),
            )

    # ------------------------------------------------------------------
    # Styles (with theme colors applied)
    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        # Retrieving the theme colors
        theme_id = self.user_settings.get("theme", DEFAULT_THEME)
        theme = get_theme(theme_id)

        accent = theme["accent"]
        background = theme["background"]
        sidebar_bg = theme["sidebar"]
        card_bg = theme["card"]
        border = theme["border"]

        # Choosing a text color: dark for light themes, light for dark themes
        is_light = theme_id == "light"
        text_primary = "#1a1a1a" if is_light else "#ffffff"
        text_secondary = "#555555" if is_light else "#9a9a9a"
        text_muted = "#888888" if is_light else "#666666"
        text_normal = "#2a2a2a" if is_light else "#e6e6e6"
        text_dim = "#444444" if is_light else "#b8b8b8"
        text_soft = "#3a3a3a" if is_light else "#c8c8c8"

        # Font Size and Compact Mode
        font_size = self.user_settings.get("font_size", 14)
        compact = self.user_settings.get("compact_mode", False)

        # Card Sizes and Indents: Standard or Compact
        if compact:
            card_padding = "8px 12px"
            card_spacing = "6px"
            icon_size = "48px"
        else:
            card_padding = "12px 16px"
            card_spacing = "10px"
            icon_size = "64px"

        styles = """
            QMainWindow, QWidget {
                background-color: __BACKGROUND__;
                color: __TEXT_NORMAL__;
                font-family: "Segoe UI", "Inter", sans-serif;
                font-size: __FONT_SIZE__px;
            }

            #Sidebar {
                background-color: __SIDEBAR__;
                border-right: 1px solid __BORDER__;
            }

            #Logo {
                font-size: 22px;
                font-weight: 700;
                color: __ACCENT__;
                letter-spacing: 2px;
            }

            #NavList {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 0 10px;
            }

            #NavList::item {
                padding: 10px 14px;
                border-radius: 8px;
                color: __TEXT_DIM__;
            }

            #NavList::item:hover {
                background-color: __CARD__;
                color: __TEXT_PRIMARY__;
            }

            #NavList::item:selected {
                background-color: __ACCENT_SOFT__;
                color: __ACCENT__;
                font-weight: 600;
            }

            #PageTitle {
                font-size: 28px;
                font-weight: 700;
                color: __TEXT_PRIMARY__;
            }

            #PageSubtitle {
                font-size: 15px;
                color: __TEXT_SECONDARY__;
                line-height: 1.6;
            }

            #AppsScroll {
                background-color: transparent;
                border: none;
            }

            #AppCard {
                background-color: __CARD__;
                border: 1px solid __BORDER__;
                border-radius: 12px;
            }

            #AppCard:hover {
                border: 1px solid __ACCENT__;
            }

            #AppName {
                font-size: 16px;
                font-weight: 600;
                color: __TEXT_PRIMARY__;
            }

            #AppDescription {
                font-size: 13px;
                color: __TEXT_SECONDARY__;
            }

            #AppMeta {
                font-size: 12px;
                color: __ACCENT__;
            }

            #AppIconPlaceholder {
                background-color: __BORDER__;
                border-radius: 8px;
                color: __TEXT_MUTED__;
                font-size: 24px;
                font-weight: 700;
            }

            #DownloadButton {
                background-color: __ACCENT_SOFT__;
                color: __ACCENT__;
                border: 1px solid __ACCENT__;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
            }

            #DownloadButton:hover {
                background-color: __ACCENT__;
                color: __TEXT_PRIMARY__;
            }

            #SearchInput {
                background-color: __CARD__;
                color: __TEXT_NORMAL__;
                border: 1px solid __BORDER__;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }

            #SearchInput:focus {
                border: 1px solid __ACCENT__;
            }

            #CategoryCombo {
                background-color: __CARD__;
                color: __TEXT_NORMAL__;
                border: 1px solid __BORDER__;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }

            #CategoryCombo:hover {
                border: 1px solid __ACCENT__;
            }

            #CounterLabel {
                color: __ACCENT__;
                font-size: 13px;
                font-weight: 600;
            }

            #EmptyMessage {
                color: __TEXT_MUTED__;
                font-size: 15px;
                padding: 60px 20px;
            }

            #DetailsTopBar {
                background-color: __SIDEBAR__;
                border-bottom: 1px solid __BORDER__;
            }

            #BackButton {
                background-color: transparent;
                color: __ACCENT__;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 6px 12px;
            }

            #DetailsScroll {
                background-color: transparent;
                border: none;
            }

            #DetailsHeader {
                background-color: __CARD__;
                border: 1px solid __BORDER__;
                border-radius: 12px;
            }

            #DetailsIconPlaceholder {
                background-color: __BORDER__;
                border-radius: 12px;
                color: __TEXT_MUTED__;
                font-size: 36px;
                font-weight: 700;
            }

            #DetailsName {
                font-size: 24px;
                font-weight: 700;
                color: __TEXT_PRIMARY__;
            }

            #DetailsDeveloper {
                font-size: 13px;
                color: __TEXT_SECONDARY__;
            }

            #DetailsShortDesc {
                font-size: 14px;
                color: __TEXT_DIM__;
            }

            #DetailsSection {
                background-color: __CARD__;
                border: 1px solid __BORDER__;
                border-radius: 12px;
            }

            #SectionTitle {
                font-size: 16px;
                font-weight: 700;
                color: __TEXT_PRIMARY__;
            }

            #SectionText {
                font-size: 14px;
                color: __TEXT_SOFT__;
                line-height: 1.6;
            }

            #SectionBullet {
                font-size: 14px;
                color: __TEXT_SOFT__;
                line-height: 1.5;
            }

            #SpecKey {
                font-size: 13px;
                color: __TEXT_SECONDARY__;
            }

            #SpecValue {
                font-size: 13px;
                color: __TEXT_NORMAL__;
                font-weight: 600;
            }

            #PrimaryButton {
                background-color: __ACCENT_SOFT__;
                color: __ACCENT__;
                border: 1px solid __ACCENT__;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 14px;
            }

            #PrimaryButton:hover {
                background-color: __ACCENT__;
                color: __TEXT_PRIMARY__;
            }

            #SecondaryButton {
                background-color: transparent;
                color: __TEXT_DIM__;
                border: 1px solid __BORDER__;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 500;
                font-size: 14px;
            }

            #SecondaryButton:hover {
                background-color: __CARD__;
                color: __TEXT_PRIMARY__;
                border: 1px solid __ACCENT__;
            }

            #Screenshot {
                border-radius: 8px;
                border: 1px solid __BORDER__;
            }

            #UpdateBanner {
                background-color: __ACCENT_SOFT__;
                border-bottom: 1px solid __ACCENT__;
            }

            #BannerText {
                color: __TEXT_PRIMARY__;
                font-size: 13px;
                font-weight: 600;
            }

            #BannerButton {
                background-color: __ACCENT__;
                color: __BACKGROUND__;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }

            #BannerClose {
                background-color: transparent;
                color: __ACCENT__;
                border: none;
                font-size: 20px;
                font-weight: 700;
                padding: 0;
            }

            #SettingsGroup {
                background-color: __CARD__;
                border: 1px solid __BORDER__;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 12px;
                font-size: 14px;
                font-weight: 600;
                color: __ACCENT__;
            }

            #SettingsGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background-color: __BACKGROUND__;
            }

            #SettingsInput {
                background-color: __BACKGROUND__;
                color: __TEXT_NORMAL__;
                border: 1px solid __BORDER__;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }

            #SettingsInput:focus {
                border: 1px solid __ACCENT__;
            }

            #SettingsPath {
                font-size: 11px;
                color: __TEXT_MUTED__;
                font-family: "Consolas", monospace;
            }

            QComboBox {
                background-color: __BACKGROUND__;
                color: __TEXT_NORMAL__;
                border: 1px solid __BORDER__;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }

            QComboBox QAbstractItemView {
                background-color: __CARD__;
                color: __TEXT_NORMAL__;
                selection-background-color: __ACCENT_SOFT__;
                selection-color: __ACCENT__;
            }
        """

        # Set the theme colors
        replacements = {
            "__ACCENT__": accent,
            "__ACCENT_SOFT__": self._mix(accent, background, 0.75),
            "__BACKGROUND__": background,
            "__SIDEBAR__": sidebar_bg,
            "__CARD__": card_bg,
            "__BORDER__": border,
            "__TEXT_PRIMARY__": text_primary,
            "__TEXT_NORMAL__": text_normal,
            "__TEXT_SECONDARY__": text_secondary,
            "__TEXT_DIM__": text_dim,
            "__TEXT_SOFT__": text_soft,
            "__TEXT_MUTED__": text_muted,
            "__FONT_SIZE__": str(font_size),
        }
        for key, value in replacements.items():
            styles = styles.replace(key, value)

        self.setStyleSheet(styles)

    @staticmethod
    def _mix(color1: str, color2: str, alpha: float) -> str:
        """
        Mixes two hex colors: alpha is the proportion of color1.
        For example, _mix("#ffffff", "#000000", 0.5) → "#808080".
        """
        def hex_to_rgb(h: str) -> tuple[int, int, int]:
            h = h.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        def rgb_to_hex(r: int, g: int, b: int) -> str:
            return f"#{r:02x}{g:02x}{b:02x}"

        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)

        r = int(r1 * (1 - alpha) + r2 * alpha)
        g = int(g1 * (1 - alpha) + g2 * alpha)
        b = int(b1 * (1 - alpha) + b2 * alpha)

        return rgb_to_hex(r, g, b)