"""
Диалоговое окно с информацией об обновлении.
Показывает версию, описание релиза и кнопки действий.
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


class UpdateDialog(QDialog):
    """
    Окно с описанием доступного обновления.

    Показывает: заголовок, текущую и новую версии, описание релиза
    (в формате Markdown от GitHub), кнопки «Скачать» и «Позже».
    """

    def __init__(self, info: dict, current_version: str, parent=None) -> None:
        super().__init__(parent)

        self.info = info
        self.current_version = current_version

        self.setWindowTitle("Доступно обновление")
        self.setModal(True)
        self.resize(640, 560)
        self.setMinimumSize(500, 400)

        self._build_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Заголовок ---
        title = QLabel("🎉 Доступно обновление OWINP")
        title.setObjectName("UpdateTitle")
        layout.addWidget(title)

        # --- Версии ---
        versions_layout = QHBoxLayout()
        versions_layout.setSpacing(8)

        current_label = QLabel(f"Текущая: v{self.current_version}")
        current_label.setObjectName("VersionCurrent")

        arrow = QLabel("→")
        arrow.setObjectName("VersionArrow")

        new_label = QLabel(f"Новая: v{self.info.get('version', '?')}")
        new_label.setObjectName("VersionNew")

        versions_layout.addWidget(current_label)
        versions_layout.addWidget(arrow)
        versions_layout.addWidget(new_label)
        versions_layout.addStretch(1)

        layout.addLayout(versions_layout)

        # --- Что нового (Markdown из GitHub) ---
        what_new_title = QLabel("Что нового:")
        what_new_title.setObjectName("SectionLabel")
        layout.addWidget(what_new_title)

        # QTextBrowser умеет рендерить Markdown
        self.body_browser = QTextBrowser()
        self.body_browser.setObjectName("ReleaseBody")
        self.body_browser.setOpenExternalLinks(True)

        body_text = self.info.get("body", "").strip()
        if not body_text:
            body_text = "Описание релиза отсутствует."

        # setMarkdown — превращает ## и ** в красивое форматирование
        try:
            self.body_browser.setMarkdown(body_text)
        except AttributeError:
            # На старых версиях PySide6 может не быть setMarkdown
            self.body_browser.setPlainText(body_text)

        layout.addWidget(self.body_browser, stretch=1)

        # --- Дата публикации ---
        published = self.info.get("published_at", "")
        if published:
            date_label = QLabel(f"Дата выпуска: {published[:10]}")
            date_label.setObjectName("DateLabel")
            layout.addWidget(date_label)

        # --- Кнопки ---
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addStretch(1)

        later_btn = QPushButton("Позже")
        later_btn.setObjectName("SecondaryButton")
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(later_btn)

        download_btn = QPushButton("Скачать со страницы релиза")
        download_btn.setObjectName("PrimaryButton")
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.clicked.connect(self._open_release_page)
        buttons_layout.addWidget(download_btn)

        layout.addLayout(buttons_layout)

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _open_release_page(self) -> None:
        """Открывает страницу релиза в браузере."""
        url = self.info.get("url", "")
        if url:
            print(f"[updater] Открываем в браузере: {url}")
            webbrowser.open(url)
        self.accept()

    # ------------------------------------------------------------------
    # Стили
    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1f22;
                color: #e6e6e6;
                font-family: "Segoe UI", "Inter", sans-serif;
            }

            #UpdateTitle {
                font-size: 20px;
                font-weight: 700;
                color: #ffffff;
            }

            #VersionCurrent {
                font-size: 14px;
                color: #9a9a9a;
            }

            #VersionArrow {
                font-size: 14px;
                color: #7c9cff;
            }

            #VersionNew {
                font-size: 14px;
                color: #7c9cff;
                font-weight: 700;
            }

            #SectionLabel {
                font-size: 13px;
                color: #9a9a9a;
                margin-top: 8px;
            }

            #ReleaseBody {
                background-color: #24262b;
                color: #e6e6e6;
                border: 1px solid #2f3138;
                border-radius: 10px;
                padding: 14px;
                font-size: 13px;
                selection-background-color: #2b3557;
            }

            #DateLabel {
                font-size: 12px;
                color: #7c9cff;
            }

            QPushButton {
                background-color: #2b3557;
                color: #7c9cff;
                border: 1px solid #3a4a7a;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 100px;
            }

            QPushButton:hover {
                background-color: #37427a;
                color: #a0b4ff;
            }

            QPushButton:pressed {
                background-color: #222a4a;
            }

            #SecondaryButton {
                background-color: transparent;
                color: #b8b8b8;
                border: 1px solid #3a3a3a;
            }

            #SecondaryButton:hover {
                background-color: #2a2b30;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
        """)