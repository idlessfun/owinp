"""
Главное окно приложения OWINP.
"""

from PySide6.QtCore import Qt
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
)

from app.ui.apps_page import AppsPage


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OWINP — Open Windows Programs")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._build_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Создаёт и размещает все виджеты."""

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Левая панель (sidebar)
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        # 2. Правая область (контент) — создаём ДО выбора раздела,
        #    иначе _on_nav_changed упадёт с AttributeError
        self.content_area = self._build_content_area()
        root_layout.addWidget(self.content_area, stretch=1)

        # 3. Теперь обе части готовы — можно выбрать первый раздел.
        #    Это вызовет _on_nav_changed и переключит страницу.
        self.nav_list.setCurrentRow(0)

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

        # Подключаем обработчик, но НЕ выбираем строку здесь —
        # это делается в _build_ui, когда content_area уже создан.
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        layout.addWidget(self.nav_list, stretch=1)

        return sidebar

    def _build_content_area(self) -> QWidget:
        """Область контента (сейчас одна страница — 'Главная')."""

        stack = QStackedWidget()

        home = QWidget()
        home_layout = QVBoxLayout(home)
        home_layout.setContentsMargins(40, 40, 40, 40)
        home_layout.setSpacing(16)

        title = QLabel("Добро пожаловать в OWINP")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Здесь будет каталог open-source программ для Windows.\n"
            "Скоро добавим карточки приложений и кнопку «Скачать»."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        home_layout.addWidget(title)
        home_layout.addWidget(subtitle)
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
        """)
