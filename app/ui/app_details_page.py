"""
Страница подробной информации о программе.

Открывается при клике на карточку в списке.
Показывает: иконку, название, разработчика, описание,
характеристики, требования, возможности и кнопки действий.
"""

from pathlib import Path
from app.core.cache_manager import find_icon, find_screenshot
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

ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "resources" / "screenshots"


class AppDetailsPage(QWidget):
    """
    Подробная страница программы.

    Сигналы:
        back_requested — испускается при клике на «← Назад».
                         AppsPage ловит его и возвращает список.
        download_requested — испускается при клике на «Скачать».
                             С app_data в качестве аргумента.
    """

    back_requested = Signal()
    download_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()

        self._current_data: dict = {}

        # Общий вертикальный layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Верхняя панель с кнопкой «Назад» ----
        top_bar = QFrame()
        top_bar.setObjectName("DetailsTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 12, 20, 12)

        back_btn = QPushButton("← Назад")
        back_btn.setObjectName("BackButton")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        top_layout.addWidget(back_btn)

        top_layout.addStretch(1)

        outer.addWidget(top_bar)

        # ---- Прокручиваемая область с контентом ----
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
    # Заполнение страницы данными
    # ------------------------------------------------------------------
    def set_app_data(self, data: dict) -> None:
        """
        Заполняет страницу данными программы.
        Очищает предыдущее содержимое и строит новое.
        """
        self._current_data = data

        # Удаляем все виджеты со старого контента
        self._clear_layout(self.content_layout)

        # ---- Шапка: иконка + имя + разработчик + кнопки ----
        self.content_layout.addWidget(self._build_header(data))

        # ---- Описание ----
        long_desc = data.get("long_description") or data.get("description")
        if long_desc:
            self.content_layout.addWidget(self._build_section("Описание", long_desc))

        # ---- Характеристики (таблица) ----
        specs = self._build_specs(data)
        if specs:
            self.content_layout.addWidget(specs)

        # ---- Возможности ----
        features = data.get("features", [])
        if features:
            self.content_layout.addWidget(
                self._build_section("Возможности", None, features)
            )

        # ---- Системные требования ----
        requirements = data.get("requirements", [])
        if requirements:
            self.content_layout.addWidget(
                self._build_section("Системные требования", None, requirements)
            )

        # ---- Скриншоты ----
        screenshots = data.get("screenshots", [])
        if screenshots:
            self.content_layout.addWidget(
                self._build_screenshots(screenshots)
            )

        # Растяжка в конце
        self.content_layout.addStretch(1)

    def _clear_layout(self, layout) -> None:
        """Удаляет все виджеты и под-layout'ы из layout'а."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    # ------------------------------------------------------------------
    # Построение блоков страницы
    # ------------------------------------------------------------------
    def _build_header(self, data: dict) -> QWidget:
        """Шапка: большая иконка, имя, разработчик, кнопки действий."""

        header = QFrame()
        header.setObjectName("DetailsHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- Иконка 96x96 ---
        # --- Иконка 96x96 (сначала кэш, потом встроенная) ---
        icon_label = QLabel()
        icon_label.setFixedSize(96, 96)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("DetailsIcon")

        # Ищем иконку в кэше
        icon_path = find_icon(data)

        # Если в кэше нет — пробуем встроенную
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

        # --- Текстовый блок ---
        text_block = QVBoxLayout()
        text_block.setSpacing(6)

        name = QLabel(data.get("name", "Без имени"))
        name.setObjectName("DetailsName")

        developer = data.get("developer", "")
        if developer:
            dev_label = QLabel(f"Разработчик: {developer}")
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

        # --- Кнопки действий (справа) ---
        actions = QVBoxLayout()
        actions.setSpacing(8)

        download_btn = QPushButton("Скачать")
        download_btn.setObjectName("PrimaryButton")
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.setFixedWidth(160)
        download_btn.clicked.connect(
            lambda: self.download_requested.emit(self._current_data)
        )
        actions.addWidget(download_btn)

        website = data.get("website", "")
        if website:
            site_btn = QPushButton("Открыть сайт")
            site_btn.setObjectName("SecondaryButton")
            site_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            site_btn.setFixedWidth(160)
            site_btn.clicked.connect(lambda: self._open_website(website))
            actions.addWidget(site_btn)

        actions.addStretch(1)
        layout.addLayout(actions)

        return header

    def _build_section(self, title: str, text: str | None, items: list | None = None) -> QWidget:
        """
        Универсальный блок-секция.
        Если передан text — покажет абзац.
        Если передан items — покажет маркированный список.
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
        """Блок с характеристиками: версия, размер, лицензия, категория и т.д."""

        rows = []
        if data.get("version"):
            rows.append(("Версия", data["version"]))
        if data.get("release_date"):
            rows.append(("Дата выпуска", data["release_date"]))
        if data.get("category"):
            rows.append(("Категория", data["category"]))
        if data.get("size_mb"):
            rows.append(("Размер", f"{data['size_mb']} МБ"))
        if data.get("license"):
            rows.append(("Лицензия", data["license"]))

        if not rows:
            return None

        section = QFrame()
        section.setObjectName("DetailsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel("Характеристики")
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
        """Блок со скриншотами."""

        section = QFrame()
        section.setObjectName("DetailsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel("Скриншоты")
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        # Пробуем два источника: "screenshots" (имена) и "screenshots_urls" (URL)
        names = self._current_data.get("screenshots", [])
        urls = self._current_data.get("screenshots_urls", [])

        # Сначала — по именам (наши скриншоты)
        for name in names:
            shot_path = find_screenshot(self._current_data, name)
            if shot_path is None:
                # Fallback: встроенный скриншот
                builtin = SCREENSHOTS_DIR / name
                if builtin.exists():
                    shot_path = builtin

            if shot_path is None:
                continue

            self._add_screenshot_to_layout(shot_path, layout)

        # Потом — по внешним URL (индексы)
        for idx in range(len(urls)):
            shot_path = find_screenshot(self._current_data, idx)
            if shot_path is None:
                continue

            self._add_screenshot_to_layout(shot_path, layout)

        return section

    def _add_screenshot_to_layout(self, shot_path: Path, layout) -> None:
        """
        Загружает картинку, масштабирует до ширины 600 и добавляет в layout.
        Пропускает битые/несуществующие файлы.
        """
        if not shot_path.exists():
            return

        pixmap = QPixmap(str(shot_path))
        if pixmap.isNull():
            print(f"[details] Битый скриншот: {shot_path.name}")
            return

        scaled = pixmap.scaledToWidth(
            600,
            Qt.TransformationMode.SmoothTransformation,
        )

        img_label = QLabel()
        img_label.setPixmap(scaled)
        img_label.setObjectName("Screenshot")
        layout.addWidget(img_label)
    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _open_website(self, url: str) -> None:
        """Открывает сайт в системном браузере."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))