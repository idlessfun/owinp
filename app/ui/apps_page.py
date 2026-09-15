"""
Страница «Программы».

Внутри — QStackedWidget с двумя состояниями:
  0) Список карточек с программами + поиск и фильтр по категории
  1) Подробная страница выбранной программы
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
from app.ui.app_details_page import AppDetailsPage
from PySide6.QtCore import Qt, Signal, QTimer
from app.core.catalog_loader import CatalogLoader


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"

# Значение для выпадающего списка «Все категории»
ALL_CATEGORIES = "Все категории"


class AppsPage(QWidget):
    """Страница «Программы» — список, поиск, фильтр, подробности."""

    def __init__(self) -> None:
        super().__init__()

        # Загружаем все программы один раз при старте
        self.all_apps: list[dict] = load_all_apps()
        self.filtered_apps: list[dict] = list(self.all_apps)
        # Для кнопки «Обновить»
        self._reload_loader: CatalogLoader | None = None

        # Внешний layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Стопка страниц: 0 — список, 1 — подробности
        self.stack = QStackedWidget()

        # --- Страница 0: список ---
        self.list_page = self._build_list_page()
        self.stack.addWidget(self.list_page)

        # --- Страница 1: подробности ---
        self.details_page = AppDetailsPage()
        self.details_page.back_requested.connect(self._show_list)
        self.details_page.download_requested.connect(self._on_download_clicked)
        self.stack.addWidget(self.details_page)

        outer.addWidget(self.stack)

        # По умолчанию — список
        self.stack.setCurrentIndex(0)

        # Первичное заполнение списка
        self._apply_filters()

    # ------------------------------------------------------------------
    # Построение страницы со списком
    # ------------------------------------------------------------------
    def _build_list_page(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("Программы")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ---- Панель инструментов: поиск + категория + счётчик ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        # Кнопка «Обновить каталог»
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setObjectName("RefreshButton")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.clicked.connect(self._force_refresh)
        toolbar.addWidget(self.refresh_btn)

        # Строка поиска
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("🔍 Поиск по названию, описанию или тегам...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_input, stretch=1)

        # Выпадающий список категорий
        self.category_combo = QComboBox()
        self.category_combo.setObjectName("CategoryCombo")
        self.category_combo.setFixedWidth(220)
        self.category_combo.addItem(ALL_CATEGORIES)
        # Заполняем категориями из JSON
        categories = sorted({
            app.get("category", "").strip()
            for app in self.all_apps
            if app.get("category")
        })
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self._apply_filters)
        toolbar.addWidget(self.category_combo)

        # Счётчик
        self.counter_label = QLabel("")
        self.counter_label.setObjectName("CounterLabel")
        self.counter_label.setFixedWidth(120)
        self.counter_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        toolbar.addWidget(self.counter_label)

        layout.addLayout(toolbar)

        # ---- Прокручиваемая область с карточками ----
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
    # Фильтрация
    # ------------------------------------------------------------------
    def _apply_filters(self) -> None:
        """Применяет поиск и фильтр категории, затем перерисовывает список."""
        query = self.search_input.text().strip().lower()
        category = self.category_combo.currentText()

        # Фильтруем
        result = []
        for app in self.all_apps:
            # --- По категории ---
            if category != ALL_CATEGORIES:
                if app.get("category", "") != category:
                    continue

            # --- По поиску ---
            if query:
                haystack_parts = [
                    app.get("name", ""),
                    app.get("description", ""),
                    app.get("developer", ""),
                ]
                # Теги — это список, добавляем все
                haystack_parts.extend(app.get("tags", []))
                haystack = " ".join(haystack_parts).lower()

                if query not in haystack:
                    continue

            result.append(app)

        self.filtered_apps = result
        self._redraw_cards()

    def _redraw_cards(self) -> None:
        """Очищает контейнер и создаёт карточки заново."""
        # Очищаем старые виджеты
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Если пусто — показываем сообщение
        if not self.filtered_apps:
            if not self.all_apps:
                message = "Пока нет ни одной программы. Добавь JSON в app/apps/."
            else:
                message = "Ничего не найдено. Попробуй изменить запрос или категорию."

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

        # Обновляем счётчик
        self.counter_label.setText(f"Найдено: {len(self.filtered_apps)}")

    def _force_refresh(self) -> None:
        """
        Принудительно обновляет каталог с GitHub и перестраивает список.
        Игнорирует троттлинг.
        """
        print("[AppsPage] Принудительное обновление каталога...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Обновление...")

        self._reload_loader = CatalogLoader(force=True)
        self._reload_loader.finished_ok.connect(self._on_reload_finished)
        self._reload_loader.failed.connect(self._on_reload_failed)
        self._reload_loader.start()

    def _on_reload_finished(self, count: int) -> None:
        """Каталог обновлён — перечитываем кэш и перестраиваем список."""
        print(f"[AppsPage] Обновлено файлов: {count}. Перестройка списка...")

        # Перечитываем данные из кэша
        self.all_apps = load_all_apps()
        self.filtered_apps = list(self.all_apps)

        # Обновляем список категорий (могли появиться новые)
        self._rebuild_categories()

        # Перестраиваем карточки (с учётом текущего поиска/фильтра)
        self._apply_filters()

        # Возвращаем кнопку в исходное состояние
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Обновить")

    def _rebuild_categories(self) -> None:
        """Перезаполняет выпадающий список категорий."""
        # Запоминаем текущий выбор
        current = self.category_combo.currentText()

        # Блокируем сигналы, чтобы не триггерить фильтрацию во время перезаполнения
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("Все категории")

        categories = sorted({
            app.get("category", "").strip()
            for app in self.all_apps
            if app.get("category")
        })
        self.category_combo.addItems(categories)

        # Восстанавливаем выбор (если категория ещё существует)
        idx = self.category_combo.findText(current)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        else:
            self.category_combo.setCurrentIndex(0)  # сбрасываем на «Все категории»

        self.category_combo.blockSignals(False)

    def _on_reload_failed(self, error: str) -> None:
        """Ошибка обновления — сообщаем в консоль."""
        print(f"[AppsPage] Ошибка обновления: {error}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Обновить")
    # ------------------------------------------------------------------
    # Переключение страниц
    # ------------------------------------------------------------------
    def _show_details(self, data: dict) -> None:
        print(f"[AppsPage] Открыть страницу: {data.get('name')}")
        self.details_page.set_app_data(data)
        self.stack.setCurrentIndex(1)

    def _show_list(self) -> None:
        self.stack.setCurrentIndex(0)

    def _on_download_clicked(self, data: dict) -> None:
        """Открывает диалог «Сохранить как», затем запускает скачивание."""
        from PySide6.QtWidgets import QFileDialog
        from app.ui.download_dialog import DownloadDialog

        url = data.get("download_url", "")
        default_name = url.split("/")[-1] if url else "download.exe"

        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить файл",
            default_name,
            "Исполняемые файлы (*.exe);;Все файлы (*.*)",
        )

        if not save_path_str:
            print("[AppsPage] Скачивание отменено на этапе выбора пути")
            return

        save_path = Path(save_path_str)
        dialog = DownloadDialog(data, save_path, parent=self)
        dialog.exec()


class AppCard(QFrame):
    """
    Карточка программы в списке.

    Сигнал clicked испускается при клике по карточке или кнопке «Подробнее».
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

        # --- Иконка ---
        # --- Иконка (сначала кэш, потом встроенная) ---
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setObjectName("AppIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ищем иконку в кэше
        cached_icon = find_icon(data)
        icon_path = cached_icon

        # Если в кэше нет — пробуем встроенную
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

        # --- Текст ---
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        name = QLabel(data.get("name", "Без имени"))
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
            meta_parts.append(f"{data['size_mb']} МБ")
        if data.get("license"):
            meta_parts.append(data["license"])

        meta = QLabel(" · ".join(meta_parts))
        meta.setObjectName("AppMeta")

        text_layout.addWidget(name)
        text_layout.addWidget(description)
        text_layout.addWidget(meta)

        layout.addLayout(text_layout, stretch=1)

        # --- Кнопка «Подробнее» ---
        details_btn = QPushButton("Подробнее")
        details_btn.setObjectName("DownloadButton")
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setFixedWidth(120)
        details_btn.clicked.connect(lambda: self.clicked.emit(self._data))

        layout.addWidget(details_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event) -> None:
        """Клик по самой карточке (не по кнопке) открывает страницу."""
        child = self.childAt(event.position().toPoint())
        if isinstance(child, QPushButton):
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._data)
        super().mousePressEvent(event)