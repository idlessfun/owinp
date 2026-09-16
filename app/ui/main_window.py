"""
Главное окно приложения OWINP.
"""

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
)

from app import __version__
from app.core.updater import UpdateChecker
from app.core.catalog_loader import CatalogLoader
from app.ui.apps_page import AppsPage
from app.ui.update_dialog import UpdateDialog


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()

        # Данные обновления (если найдено)
        self._update_info: dict | None = None
        self._checker: UpdateChecker | None = None
        self._catalog_loader: CatalogLoader | None = None
        self._manual_check = False   # True — проверка была запущена кнопкой

        self.setWindowTitle(f"OWINP — Open Windows Programs v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._build_ui()
        self._apply_styles()

        # Запускаем проверку обновлений через 2 секунды после старта
        # (чтобы окно успело показаться и не «подвисло» при запуске)
        QTimer.singleShot(2000, self._check_for_updates)
        # Запускаем обновление каталога через 3 секунды после старта
        # (чуть позже, чем проверку версии, чтобы не долбить API одновременно)
        QTimer.singleShot(3000, self._refresh_catalog)

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Создаёт и размещает все виджеты."""

        central = QWidget()
        self.setCentralWidget(central)

        # Главный вертикальный layout: [banner сверху] + [основная часть]
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Баннер обновления (сверху, скрыт по умолчанию) ---
        self.update_banner = self._build_update_banner()
        self.update_banner.setVisible(False)
        main_layout.addWidget(self.update_banner)

        # --- Основная часть: [sidebar | content] ---
        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        self.content_area = self._build_content_area()
        root_layout.addWidget(self.content_area, stretch=1)

        main_layout.addWidget(body, stretch=1)

        # Выбираем первый раздел
        self.nav_list.setCurrentRow(0)

    def _build_update_banner(self) -> QFrame:
        """Тонкая полоса сверху — «Доступно обновление»."""

        banner = QFrame()
        banner.setObjectName("UpdateBanner")
        banner.setFixedHeight(44)

        layout = QHBoxLayout(banner)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(12)

        # Текст
        text = QLabel("🎉 Доступна новая версия OWINP")
        text.setObjectName("BannerText")
        layout.addWidget(text)

        layout.addStretch(1)

        # Кнопка «Что нового»
        what_new_btn = QPushButton("Что нового")
        what_new_btn.setObjectName("BannerButton")
        what_new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        what_new_btn.clicked.connect(self._show_update_dialog)
        layout.addWidget(what_new_btn)

        # Кнопка закрытия (×)
        close_btn = QPushButton("×")
        close_btn.setObjectName("BannerClose")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.update_banner.setVisible(False))
        layout.addWidget(close_btn)

        return banner

    def _build_sidebar(self) -> QWidget:
        """Боковая панель с логотипом и списком разделов."""

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

        sections = ["Главная", "Программы"]
        for name in sections:
            QListWidgetItem(name, self.nav_list)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        layout.addWidget(self.nav_list, stretch=1)

        return sidebar

    def _build_content_area(self) -> QWidget:
        """Область контента — стек страниц."""

        stack = QStackedWidget()

        # Страница «Главная»
        # Страница «Главная»
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

        # Кнопка «Проверить обновления»
        check_btn = QPushButton("🔄 Проверить обновления")
        check_btn.setObjectName("PrimaryButton")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.setFixedWidth(240)
        check_btn.clicked.connect(self._manual_check_for_updates)
        home_layout.addWidget(check_btn)

        # Кнопка «Очистить кэш»
        clear_cache_btn = QPushButton("🧹 Очистить кэш")
        clear_cache_btn.setObjectName("SecondaryButton")
        clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_cache_btn.setFixedWidth(240)
        clear_cache_btn.clicked.connect(self._clear_cache_clicked)
        home_layout.addWidget(clear_cache_btn)

        home_layout.addStretch(1)

        home_layout.addStretch(1)

        stack.addWidget(home)

        # Страница «Программы»
        apps_page = AppsPage()
        stack.addWidget(apps_page)

        return stack

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _on_nav_changed(self, index: int) -> None:
        """Переключает страницу при выборе раздела в sidebar."""
        if 0 <= index < self.content_area.count():
            self.content_area.setCurrentIndex(index)

    def _check_for_updates(self) -> None:
        """Автоматическая проверка обновлений (при старте)."""
        self._manual_check = False
        self._checker = UpdateChecker(force=False)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _manual_check_for_updates(self) -> None:
        """Принудительная проверка обновлений (по кнопке)."""
        print("[main] Ручная проверка обновлений")
        self._manual_check = True
        self._checker = UpdateChecker(force=True)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.start()

    def _clear_cache_clicked(self) -> None:
            """Очищает кэш каталога и картинок."""
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

    def _refresh_catalog(self, force: bool = False) -> None:
        """
        Запускает фоновое обновление каталога с GitHub.

        force=True — игнорировать троттлинг (для кнопки «Обновить»).
        force=False — обновлять только если прошёл час (по умолчанию).
        """
        self._catalog_loader = CatalogLoader(force=force)
        self._catalog_loader.finished_ok.connect(self._on_catalog_updated)
        self._catalog_loader.failed.connect(self._on_catalog_failed)
        self._catalog_loader.start()

    def _on_catalog_updated(self, count: int) -> None:
        """Каталог обновлён — тихо логируем."""
        if count > 0:
            print(f"[main] Каталог обновлён: {count} файлов")
        else:
            print("[main] Каталог без изменений")

    def _on_catalog_failed(self, error: str) -> None:
        """Ошибка обновления каталога — тихо логируем, не мешаем пользователю."""
        print(f"[main] Каталог не обновлён: {error}")

    def _on_update_available(self, info: dict) -> None:
        """Есть обновление — показываем баннер."""
        self._update_info = info
        self.update_banner.setVisible(True)
        print(f"[main] Показан баннер обновления: v{info.get('version')}")
        # Если ручная проверка — сразу открываем диалог
        if self._manual_check:
            self._manual_check = False
            self._show_update_dialog()

    def _on_no_update(self) -> None:
        """Обновлений нет."""
        print("[main] Обновлений нет")
        # Если это была ручная проверка — показываем сообщение
        if self._manual_check:
            self._manual_check = False
            QMessageBox.information(
                self,
                "Обновления",
                f"У вас последняя версия OWINP ({__version__}).",
            )

    def _on_check_failed(self, error: str) -> None:
        """Ошибка проверки."""
        print(f"[main] Не удалось проверить обновления: {error}")
        # Если это была ручная проверка — показываем сообщение
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
        """Открывает диалог с описанием обновления."""
        if not self._update_info:
            return
        dialog = UpdateDialog(self._update_info, __version__, parent=self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Стили
    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1f22;
                color: #e6e6e6;
                font-family: "Segoe UI", "Inter", sans-serif;
                font-size: 14px;
            }

            #Sidebar {
                background-color: #17181b;
                border-right: 1px solid #2a2b30;
            }

            #Logo {
                font-size: 22px;
                font-weight: 700;
                color: #7c9cff;
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
                color: #b8b8b8;
            }

            #NavList::item:hover {
                background-color: #24262b;
                color: #ffffff;
            }

            #NavList::item:selected {
                background-color: #2b3557;
                color: #7c9cff;
                font-weight: 600;
            }

            #PageTitle {
                font-size: 28px;
                font-weight: 700;
                color: #ffffff;
            }

            #PageSubtitle {
                font-size: 15px;
                color: #9a9a9a;
                line-height: 1.6;
            }

            /* ---------- Страница «Программы» ---------- */
            #AppsScroll {
                background-color: transparent;
                border: none;
            }

            #AppCard {
                background-color: #24262b;
                border: 1px solid #2f3138;
                border-radius: 12px;
            }

            #AppCard:hover {
                border: 1px solid #3a4a7a;
                background-color: #262830;
            }

            #AppName {
                font-size: 16px;
                font-weight: 600;
                color: #ffffff;
            }

            #AppDescription {
                font-size: 13px;
                color: #a0a0a0;
            }

            #AppMeta {
                font-size: 12px;
                color: #7c9cff;
            }

            #AppIconPlaceholder {
                background-color: #2f3138;
                border-radius: 8px;
                color: #666;
                font-size: 24px;
                font-weight: 700;
            }

            #DownloadButton {
                background-color: #2b3557;
                color: #7c9cff;
                border: 1px solid #3a4a7a;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
            }

            #DownloadButton:hover {
                background-color: #37427a;
                color: #a0b4ff;
            }

            #DownloadButton:pressed {
                background-color: #222a4a;
            }

            /* ---------- Панель поиска и фильтров ---------- */
            #SearchInput {
                background-color: #24262b;
                color: #e6e6e6;
                border: 1px solid #2f3138;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: #2b3557;
            }

            #SearchInput:focus {
                border: 1px solid #7c9cff;
            }

            #SearchInput::placeholder {
                color: #666;
            }

            #CategoryCombo {
                background-color: #24262b;
                color: #e6e6e6;
                border: 1px solid #2f3138;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }

            #CategoryCombo:hover {
                border: 1px solid #3a4a7a;
            }

            #CategoryCombo::drop-down {
                border: none;
                width: 24px;
            }

            #CategoryCombo QAbstractItemView {
                background-color: #24262b;
                color: #e6e6e6;
                border: 1px solid #2f3138;
                border-radius: 8px;
                selection-background-color: #2b3557;
                selection-color: #7c9cff;
                padding: 4px;
                outline: none;
            }

            #CounterLabel {
                color: #7c9cff;
                font-size: 13px;
                font-weight: 600;
            }

            #EmptyMessage {
                color: #666;
                font-size: 15px;
                padding: 60px 20px;
            }

            /* ---------- Страница программы ---------- */
            #DetailsTopBar {
                background-color: #17181b;
                border-bottom: 1px solid #2a2b30;
            }

            #BackButton {
                background-color: transparent;
                color: #7c9cff;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 6px 12px;
            }

            #BackButton:hover {
                color: #a0b4ff;
            }

            #DetailsScroll {
                background-color: transparent;
                border: none;
            }

            #DetailsHeader {
                background-color: #24262b;
                border: 1px solid #2f3138;
                border-radius: 12px;
            }

            #DetailsIconPlaceholder {
                background-color: #2f3138;
                border-radius: 12px;
                color: #666;
                font-size: 36px;
                font-weight: 700;
            }

            #DetailsName {
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
            }

            #DetailsDeveloper {
                font-size: 13px;
                color: #9a9a9a;
            }

            #DetailsShortDesc {
                font-size: 14px;
                color: #b8b8b8;
            }

            #DetailsSection {
                background-color: #24262b;
                border: 1px solid #2f3138;
                border-radius: 12px;
            }

            #SectionTitle {
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
            }

            #SectionText {
                font-size: 14px;
                color: #c8c8c8;
                line-height: 1.6;
            }

            #SectionBullet {
                font-size: 14px;
                color: #c8c8c8;
                line-height: 1.5;
            }

            #SpecKey {
                font-size: 13px;
                color: #9a9a9a;
            }

            #SpecValue {
                font-size: 13px;
                color: #e6e6e6;
                font-weight: 600;
            }

            #PrimaryButton {
                background-color: #2b3557;
                color: #7c9cff;
                border: 1px solid #3a4a7a;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 14px;
            }

            #PrimaryButton:hover {
                background-color: #37427a;
                color: #a0b4ff;
            }

            #PrimaryButton:pressed {
                background-color: #222a4a;
            }

            #SecondaryButton {
                background-color: transparent;
                color: #b8b8b8;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 500;
                font-size: 14px;
            }

            #SecondaryButton:hover {
                background-color: #2a2b30;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }

            #Screenshot {
                border-radius: 8px;
                border: 1px solid #2f3138;
            }

            /* ---------- Баннер обновления ---------- */
            #UpdateBanner {
                background-color: #2b3557;
                border-bottom: 1px solid #3a4a7a;
            }

            #BannerText {
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
            }

            #BannerButton {
                background-color: #7c9cff;
                color: #1e1f22;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }

            #BannerButton:hover {
                background-color: #a0b4ff;
            }

            #BannerClose {
                background-color: transparent;
                color: #7c9cff;
                border: none;
                font-size: 20px;
                font-weight: 700;
                padding: 0;
            }

            #BannerClose:hover {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 20);
                border-radius: 6px;
            }
                        /* ---------- Кнопка «Обновить каталог» ---------- */
            #RefreshButton {
                background-color: #24262b;
                color: #7c9cff;
                border: 1px solid #3a4a7a;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
                font-size: 13px;
            }

            #RefreshButton:hover {
                background-color: #2b3557;
                color: #a0b4ff;
            }

            #RefreshButton:pressed {
                background-color: #222a4a;
            }

            #RefreshButton:disabled {
                color: #666;
                border: 1px solid #2a2b30;
                background-color: #1e1f22;
            }
        """)