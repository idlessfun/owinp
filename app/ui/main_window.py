"""
Главное окно приложения OWINP.
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
from app.ui.apps_page import AppsPage
from app.ui.update_dialog import UpdateDialog


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()

        # Обновления / каталог
        self._update_info: dict | None = None
        self._checker: UpdateChecker | None = None
        self._catalog_loader: CatalogLoader | None = None
        self._manual_check = False

        # Пользовательские настройки
        self.user_settings = load_user_settings()

        self.setWindowTitle(f"OWINP — Open Windows Programs v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._build_ui()
        self._apply_styles()

        # Запускаем проверки только если включены в настройках
        if self.user_settings.get("check_updates_on_start", True):
            QTimer.singleShot(2000, self._check_for_updates)
        else:
            print("[main] Проверка обновлений отключена в настройках")

        if self.user_settings.get("refresh_catalog_on_start", True):
            QTimer.singleShot(3000, self._refresh_catalog)
        else:
            print("[main] Обновление каталога отключено в настройках")

    # ------------------------------------------------------------------
    # Построение интерфейса
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

        text = QLabel("🎉 Доступна новая версия OWINP")
        text.setObjectName("BannerText")
        layout.addWidget(text)

        layout.addStretch(1)

        what_new_btn = QPushButton("Что нового")
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

        sections = ["Главная", "Программы", "Настройки"]
        for name in sections:
            QListWidgetItem(name, self.nav_list)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        layout.addWidget(self.nav_list, stretch=1)

        return sidebar

    def _build_content_area(self) -> QWidget:
        stack = QStackedWidget()

        # Главная
        home = QWidget()
        home_layout = QVBoxLayout(home)
        home_layout.setContentsMargins(40, 40, 40, 40)
        home_layout.setSpacing(16)

        title = QLabel("Добро пожаловать в OWINP")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Каталог open-source программ для Windows.\n"
            "Версия: v" + __version__
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        home_layout.addWidget(title)
        home_layout.addWidget(subtitle)
        home_layout.addSpacing(20)

        check_btn = QPushButton("🔄 Проверить обновления")
        check_btn.setObjectName("PrimaryButton")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.setFixedWidth(240)
        check_btn.clicked.connect(self._manual_check_for_updates)
        home_layout.addWidget(check_btn)

        clear_cache_btn = QPushButton("🧹 Очистить кэш")
        clear_cache_btn.setObjectName("SecondaryButton")
        clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_cache_btn.setFixedWidth(240)
        clear_cache_btn.clicked.connect(self._clear_cache_clicked)
        home_layout.addWidget(clear_cache_btn)

        home_layout.addStretch(1)
        stack.addWidget(home)

        # Программы
        apps_page = AppsPage()
        stack.addWidget(apps_page)

        # Настройки
        settings_page = self._build_settings_page()
        stack.addWidget(settings_page)

        return stack

    def _build_settings_page(self) -> QWidget:
        """Страница «Настройки» — тема, шрифт, поведение."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(40, 30, 40, 30)
        outer.setSpacing(16)

        title = QLabel("Настройки")
        title.setObjectName("PageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Настрой внешний вид и поведение приложения. Изменения "
            "применяются сразу и сохраняются между запусками."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("FormScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(16)

        # --- Секция «Интерфейс» ---
        layout.addWidget(self._build_settings_interface())

        # --- Секция «Сеть и обновления» ---
        layout.addWidget(self._build_settings_network())

        # --- Секция «Скачивание» ---
        layout.addWidget(self._build_settings_download())

        # --- Секция «Страница программы» ---
        layout.addWidget(self._build_settings_app_page())

        layout.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # --- Кнопка сброса ---
        buttons = QHBoxLayout()
        reset_btn = QPushButton("🔄  Сбросить все настройки")
        reset_btn.setObjectName("SecondaryButton")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setFixedWidth(280)
        reset_btn.clicked.connect(self._reset_all_settings)
        buttons.addWidget(reset_btn)
        buttons.addStretch(1)
        outer.addLayout(buttons)

        # --- Путь к файлу ---
        path_label = QLabel(f"Файл настроек: {get_user_settings_path()}")
        path_label.setObjectName("SettingsPath")
        path_label.setWordWrap(True)
        outer.addWidget(path_label)

        return page

    def _build_settings_interface(self) -> QGroupBox:
        """Секция «Интерфейс»."""
        group = QGroupBox("Интерфейс")
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        # Тема
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
        form.addRow("Тема:", self.theme_combo)

        # Размер шрифта
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
        form.addRow("Размер шрифта:", self.font_size_combo)

        # Компактный режим
        self.compact_check = QCheckBox("Компактный режим (карточки меньше)")
        self.compact_check.setChecked(self.user_settings.get("compact_mode", False))
        self.compact_check.toggled.connect(
            lambda v: self._on_setting_toggled("compact_mode", v)
        )
        form.addRow("", self.compact_check)

        # Анимации (заглушка на будущее)
        self.animations_check = QCheckBox("Анимации интерфейса")
        self.animations_check.setChecked(self.user_settings.get("animations_enabled", True))
        self.animations_check.toggled.connect(
            lambda v: self._on_setting_toggled("animations_enabled", v)
        )
        form.addRow("", self.animations_check)

        return group

    def _build_settings_network(self) -> QGroupBox:
        """Секция «Сеть и обновления»."""
        group = QGroupBox("Сеть и обновления")
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        # Автопроверка обновлений
        self.check_updates_check = QCheckBox("Проверять обновления при запуске")
        self.check_updates_check.setChecked(
            self.user_settings.get("check_updates_on_start", True)
        )
        self.check_updates_check.toggled.connect(
            lambda v: self._on_setting_toggled("check_updates_on_start", v)
        )
        form.addRow("", self.check_updates_check)

        # Автообновление каталога
        self.refresh_catalog_check = QCheckBox("Обновлять каталог при запуске")
        self.refresh_catalog_check.setChecked(
            self.user_settings.get("refresh_catalog_on_start", True)
        )
        self.refresh_catalog_check.toggled.connect(
            lambda v: self._on_setting_toggled("refresh_catalog_on_start", v)
        )
        form.addRow("", self.refresh_catalog_check)

        # Показывать баннер
        self.show_banner_check = QCheckBox("Показывать баннер «Доступно обновление»")
        self.show_banner_check.setChecked(
            self.user_settings.get("show_update_banner", True)
        )
        self.show_banner_check.toggled.connect(
            lambda v: self._on_setting_toggled("show_update_banner", v)
        )
        form.addRow("", self.show_banner_check)

        return group

    def _build_settings_download(self) -> QGroupBox:
        """Секция «Скачивание»."""
        group = QGroupBox("Скачивание")
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        self.auto_run_check = QCheckBox(
            "Запускать установщик после скачивания (без вопроса)"
        )
        self.auto_run_check.setChecked(
            self.user_settings.get("auto_run_after_download", False)
        )
        self.auto_run_check.toggled.connect(
            lambda v: self._on_setting_toggled("auto_run_after_download", v)
        )
        form.addRow("", self.auto_run_check)

        return group

    def _build_settings_app_page(self) -> QGroupBox:
        """Секция «Страница программы»."""
        group = QGroupBox("Страница программы")
        group.setObjectName("SettingsGroup")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)

        self.show_screenshots_check = QCheckBox("Показывать скриншоты")
        self.show_screenshots_check.setChecked(
            self.user_settings.get("show_screenshots", True)
        )
        self.show_screenshots_check.toggled.connect(
            lambda v: self._on_setting_toggled("show_screenshots", v)
        )
        form.addRow("", self.show_screenshots_check)

        return group
    # ------------------------------------------------------------------
    # Обработчики темы
    # ------------------------------------------------------------------
    def _on_theme_changed(self) -> None:
        """Применяет выбранную тему."""
        theme_id = self.theme_combo.currentData()
        if not theme_id:
            return
        self.user_settings["theme"] = theme_id
        print(f"[main] Новая тема: {theme_id}")
        save_user_settings(self.user_settings)
        self._apply_styles()

    def _on_font_size_changed(self) -> None:
        """Применяет выбранный размер шрифта."""
        size = self.font_size_combo.currentData()
        if not size:
            return
        self.user_settings["font_size"] = size
        print(f"[main] Новый размер шрифта: {size}")
        save_user_settings(self.user_settings)
        self._apply_styles()

    def _on_setting_toggled(self, key: str, value: bool) -> None:
        """Обработчик переключения чекбокса."""
        self.user_settings[key] = value
        print(f"[main] {key} = {value}")
        save_user_settings(self.user_settings)

        # Если изменили что-то, влияющее на запуск — перезапуск нужен позже
        # Если изменили что-то, влияющее на UI — применяем сразу
        if key in ("compact_mode",):
            # В будущем можно перестраивать карточки
            pass

        if key == "show_update_banner" and not value:
            # Скрыть баннер, если он был виден
            self.update_banner.setVisible(False)

    def _reset_all_settings(self) -> None:
        """Сбрасывает все настройки к дефолтным."""
        answer = QMessageBox.question(
            self,
            "Сбросить настройки?",
            "Вернуть все настройки к стандартным значениям?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Сбрасываем в памяти
        self.user_settings = dict(DEFAULTS)
        save_user_settings(self.user_settings)

        # Обновляем UI контролов
        self._sync_settings_ui()

        # Применяем стили
        self._apply_styles()
        print("[main] Все настройки сброшены к дефолтным")

    def _sync_settings_ui(self) -> None:
        """Обновляет значения UI-контролов из self.user_settings."""
        # Тема
        idx = self.theme_combo.findData(self.user_settings.get("theme", DEFAULT_THEME))
        if idx >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)

        # Размер шрифта
        idx = self.font_size_combo.findData(self.user_settings.get("font_size", 14))
        if idx >= 0:
            self.font_size_combo.blockSignals(True)
            self.font_size_combo.setCurrentIndex(idx)
            self.font_size_combo.blockSignals(False)

        # Чекбоксы
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

    def _on_theme_changed(self) -> None:
        """Применяет выбранную тему."""
        theme_id = self.theme_combo.currentData()
        if not theme_id:
            return

        self.user_settings["theme"] = theme_id
        print(f"[main] Новая тема: {theme_id}")
        save_user_settings(self.user_settings)
        self._apply_styles()

    def _reset_theme(self) -> None:
        """Сбрасывает тему к стандартной."""
        answer = QMessageBox.question(
            self,
            "Сбросить тему?",
            "Вернуть стандартную тему OWINP (тёмно-синюю)?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.user_settings["theme"] = DEFAULT_THEME
        save_user_settings(self.user_settings)

        idx = self.theme_combo.findData(DEFAULT_THEME)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        self._apply_styles()
        print("[main] Тема сброшена к стандартной")

        def _on_setting_toggled(self, key: str, value: bool) -> None:
            """Обработчик переключения чекбокса."""
            self.user_settings[key] = value
            print(f"[main] {key} = {value}")
            save_user_settings(self.user_settings)

            # Если изменили что-то, влияющее на UI — применяем сразу
            if key == "show_update_banner" and not value:
                self.update_banner.setVisible(False)

            if key == "compact_mode":
                self._apply_styles()

    # ------------------------------------------------------------------
    # Обработчики навигации
    # ------------------------------------------------------------------
    def _on_nav_changed(self, index: int) -> None:
        if 0 <= index < self.content_area.count():
            self.content_area.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Обновления
    # ------------------------------------------------------------------
    def _check_for_updates(self) -> None:
        self._manual_check = False
        self._checker = UpdateChecker(force=False)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _manual_check_for_updates(self) -> None:
        print("[main] Ручная проверка обновлений")
        self._manual_check = True
        self._checker = UpdateChecker(force=True)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _on_update_available(self, info: dict) -> None:
        """Есть обновление — показываем баннер (если включено в настройках)."""
        self._update_info = info
        show_banner = self.user_settings.get("show_update_banner", True)
        if show_banner:
            self.update_banner.setVisible(True)
            print(f"[main] Показан баннер обновления: v{info.get('version')}")
        else:
            print(f"[main] Баннер отключён, но обновление есть: v{info.get('version')}")

        if self._manual_check:
            self._manual_check = False
            self._show_update_dialog()

    def _on_no_update(self) -> None:
        print("[main] Обновлений нет")
        if self._manual_check:
            self._manual_check = False
            QMessageBox.information(
                self,
                "Обновления",
                f"У вас последняя версия OWINP ({__version__}).",
            )

    def _on_check_failed(self, error: str) -> None:
        print(f"[main] Не удалось проверить обновления: {error}")
        if self._manual_check:
            self._manual_check = False
            QMessageBox.warning(
                self,
                "Ошибка проверки",
                f"Не удалось проверить обновления.\n\n"
                f"Проверьте подключение к интернету.\n\n"
                f"Ошибка: {error}",
            )

    def _show_update_dialog(self) -> None:
        if not self._update_info:
            return
        dialog = UpdateDialog(self._update_info, __version__, parent=self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Каталог
    # ------------------------------------------------------------------
    def _refresh_catalog(self, force: bool = False) -> None:
        self._catalog_loader = CatalogLoader(force=force)
        self._catalog_loader.finished_ok.connect(self._on_catalog_updated)
        self._catalog_loader.failed.connect(self._on_catalog_failed)
        self._catalog_loader.start()

    def _on_catalog_updated(self, count: int) -> None:
        if count > 0:
            print(f"[main] Каталог обновлён: {count} файлов")
        else:
            print("[main] Каталог без изменений")

    def _on_catalog_failed(self, error: str) -> None:
        print(f"[main] Каталог не обновлён: {error}")

    # ------------------------------------------------------------------
    # Кэш
    # ------------------------------------------------------------------
    def _clear_cache_clicked(self) -> None:
        from app.core.cache_manager import clear_cache, clear_assets_cache

        answer = QMessageBox.question(
            self,
            "Очистить кэш?",
            "Будут удалены:\n"
            "• скачанные JSON-карточки программ\n"
            "• иконки и скриншоты\n\n"
            "При следующем запуске каталог скачается заново.\n\n"
            "Продолжить?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        ok_json = clear_cache()
        ok_assets = clear_assets_cache()

        if ok_json and ok_assets:
            QMessageBox.information(
                self,
                "Кэш очищен ✅",
                "Кэш успешно очищен.\n\n"
                "При следующем запуске OWINP загрузит свежий каталог.",
            )
            print("[main] Кэш очищен пользователем")
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось полностью очистить кэш.\n"
                "Проверь консоль на ошибки.",
            )

    # ------------------------------------------------------------------
    # Стили (с подстановкой цветов темы)
    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        # Получаем цвета темы
        theme_id = self.user_settings.get("theme", DEFAULT_THEME)
        theme = get_theme(theme_id)

        accent = theme["accent"]
        background = theme["background"]
        sidebar_bg = theme["sidebar"]
        card_bg = theme["card"]
        border = theme["border"]

        # Подбираем цвет текста: для светлой темы — тёмный, для тёмных — светлый
        is_light = theme_id == "light"
        text_primary = "#1a1a1a" if is_light else "#ffffff"
        text_secondary = "#555555" if is_light else "#9a9a9a"
        text_muted = "#888888" if is_light else "#666666"
        text_normal = "#2a2a2a" if is_light else "#e6e6e6"
        text_dim = "#444444" if is_light else "#b8b8b8"
        text_soft = "#3a3a3a" if is_light else "#c8c8c8"

        # Размер шрифта и компактный режим
        font_size = self.user_settings.get("font_size", 14)
        compact = self.user_settings.get("compact_mode", False)

        # Размеры карточек и отступов: обычные или компактные
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

        # Подставляем цвета темы
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
        Смешивает два hex-цвета: alpha — доля color1.
        Например, _mix("#ffffff", "#000000", 0.5) → "#808080".
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