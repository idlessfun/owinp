"""
Красивый диалог скачивания в стиле OWINP.
"""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
)

from app.core.downloader import Downloader


ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


class DownloadDialog(QDialog):
    """
    Окно скачивания.
    Показывает прогресс-бар, скорость, размер.
    По завершении предлагает открыть папку или запустить файл.
    """

    def __init__(self, app_data: dict, save_path: Path, parent=None) -> None:
        super().__init__(parent)

        self.app_data = app_data
        self.save_path = save_path
        self.downloader: Downloader | None = None

        self.setWindowTitle(f"Загрузка — {app_data.get('name', '')}")
        self.setModal(True)
        self.setFixedSize(480, 260)

        self._build_ui()
        self._apply_styles()
        self._start_download()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Шапка: иконка + название ---
        header = QHBoxLayout()
        header.setSpacing(16)

        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_name = self.app_data.get("icon", "")
        icon_path = ICONS_DIR / icon_name if icon_name else None
        if icon_path and icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("?")
            icon_label.setObjectName("DlIconPlaceholder")

        header.addWidget(icon_label)

        text_block = QVBoxLayout()
        text_block.setSpacing(4)

        self.title_label = QLabel(f"Загрузка: {self.app_data.get('name', '')}")
        self.title_label.setObjectName("DlTitle")

        self.status_label = QLabel("Подключение…")
        self.status_label.setObjectName("DlStatus")

        text_block.addWidget(self.title_label)
        text_block.addWidget(self.status_label)

        header.addLayout(text_block, stretch=1)
        layout.addLayout(header)

        # --- Прогресс-бар ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("DlProgress")
        layout.addWidget(self.progress_bar)

        # --- Детали: размер, скорость, проценты ---
        self.details_label = QLabel("0 Б / 0 Б · 0 Б/с")
        self.details_label.setObjectName("DlDetails")
        layout.addWidget(self.details_label)

        layout.addStretch(1)

        # --- Кнопки (сначала только «Отмена») ---
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(8)
        self.buttons_layout.addStretch(1)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(self.buttons_layout)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1f22;
                color: #e6e6e6;
                font-family: "Segoe UI", "Inter", sans-serif;
            }

            #DlTitle {
                font-size: 17px;
                font-weight: 700;
                color: #ffffff;
            }

            #DlStatus {
                font-size: 13px;
                color: #9a9a9a;
            }

            #DlDetails {
                font-size: 12px;
                color: #7c9cff;
            }

            #DlIconPlaceholder {
                background-color: #2f3138;
                border-radius: 8px;
                color: #666;
                font-size: 24px;
                font-weight: 700;
            }

            #DlProgress {
                background-color: #24262b;
                border: none;
                border-radius: 8px;
                height: 12px;
            }

            #DlProgress::chunk {
                background-color: #7c9cff;
                border-radius: 8px;
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

    # ------------------------------------------------------------------
    # Логика скачивания
    # ------------------------------------------------------------------
    def _start_download(self) -> None:
        # URL может прийти из кнопки (_clicked_url) или из старого поля
        url = self.app_data.get("_clicked_url") or self.app_data.get("download_url", "")
        if not url:
            QMessageBox.warning(
                self, "Ошибка",
                "У программы не указана ссылка на скачивание."
            )
            self.reject()
            return

        self.downloader = Downloader(url, self.save_path)
        self.downloader.progress_changed.connect(self._on_progress)
        self.downloader.finished_ok.connect(self._on_finished)
        self.downloader.cancelled.connect(self._on_cancelled)
        self.downloader.failed.connect(self._on_failed)
        self.downloader.start()

        # Логируем в консоль
        print(f"[download] Начато скачивание: {self.app_data.get('name')}")
        print(f"[download] URL: {url}")
        print(f"[download] Куда: {self.save_path}")

    def _on_progress(self, downloaded: int, total: int, speed: float) -> None:
        """Обновляет прогресс-бар и тексты."""
        # Защита: если диалог уже закрывается — игнорируем
        if self.downloader and self.downloader._closing:
            return

        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
        else:
            # Если сервер не отдал размер — показываем "бесконечный" прогресс
            self.progress_bar.setRange(0, 0)

        # Форматируем размеры
        dl_text = self._format_size(downloaded)
        total_text = self._format_size(total) if total else "?"
        speed_text = self._format_size(speed) + "/с"

        self.details_label.setText(f"{dl_text} / {total_text} · {speed_text}")

        # В консоль — тоже
        if total:
            percent = int(downloaded * 100 / total)
            print(f"[download] {percent}% ({dl_text}/{total_text}, {speed_text})")

    def _on_finished(self, path: str) -> None:
        """Успех. Меняем интерфейс на «готово»."""
        if self.downloader and self.downloader._closing:
            return
        ...
        print(f"[download] Завершено: {path}")

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.title_label.setText(f"{self.app_data.get('name', '')}")
        self.status_label.setText("Загрузка завершена")
        self.details_label.setText(f"Файл сохранён:\n{path}")
        self.details_label.setWordWrap(True)

        # Меняем кнопки
        self._swap_buttons_to_done(Path(path))

    def _on_failed(self, error: str) -> None:
        if self.downloader and self.downloader._closing:
            return
        ...
        print(f"[download] Ошибка: {error}")
        QMessageBox.critical(
            self,
            "Ошибка загрузки",
            f"Не удалось скачать файл:\n\n{error}",
        )
        self.reject()

    def _on_cancel(self) -> None:
        """Кнопка «Отмена»."""
        if self.downloader and self.downloader.isRunning():
            self.downloader.mark_closing()
            self.downloader.cancel()
            self.downloader.wait(3000)
        self.reject()

    def _on_cancelled(self) -> None:
        """Поток сообщил, что отмена выполнена."""
        print("[download] Отменено пользователем")
        self.reject()

    # ------------------------------------------------------------------
    # Замена кнопок после завершения
    # ------------------------------------------------------------------
    def _swap_buttons_to_done(self, file_path: Path) -> None:
        # Удаляем старые кнопки
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.buttons_layout.addStretch(1)

        open_folder_btn = QPushButton("Открыть папку")
        open_folder_btn.setObjectName("SecondaryButton")
        open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_btn.clicked.connect(lambda: self._open_folder(file_path))
        self.buttons_layout.addWidget(open_folder_btn)

        run_btn = QPushButton("Запустить")
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.clicked.connect(lambda: self._run_file(file_path))
        self.buttons_layout.addWidget(run_btn)

        close_btn = QPushButton("ОК")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        self.buttons_layout.addWidget(close_btn)

    def _open_folder(self, file_path: Path) -> None:
        """Открывает проводник с выделенным файлом."""
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(file_path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(file_path)])
        else:
            subprocess.Popen(["xdg-open", str(file_path.parent)])

    def _run_file(self, file_path: Path) -> None:
        """Запускает скачанный файл."""
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(file_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось запустить файл:\n{e}")

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------
    def _format_size(self, size: float) -> str:
        """Преобразует байты в человекочитаемый вид."""
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} ТБ"
    # ------------------------------------------------------------------
    # Закрытие окна (крестик)
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        """
        Вызывается при закрытии окна (крестик, Alt+F4).
        Корректно останавливает поток скачивания.
        """
        if self.downloader and self.downloader.isRunning():
            print("[download] Диалог закрывается — отмена скачивания")
            self.downloader.mark_closing()
            self.downloader.cancel()
            # Ждём завершения потока (до 3 секунд)
            if not self.downloader.wait(3000):
                print("[download] Поток не завершился за 3 сек — принудительно")
        event.accept()