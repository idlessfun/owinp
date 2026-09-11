"""
Скачивание файлов в фоновом потоке.

Использует QThread, чтобы не подвешивать интерфейс.
Прогресс передаётся через сигналы Qt.
"""

import urllib.request
import urllib.error
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class Downloader(QThread):
    """
    Фоновый поток для скачивания файла.

    Сигналы:
        progress_changed — (скачано_байт, всего_байт, скорость_байт/с)
        finished_ok      — (путь_к_файлу)
        failed           — (текст_ошибки)
    """

    progress_changed = Signal(int, int, float)  # скачано, всего, скорость
    finished_ok = Signal(str)  # путь к файлу
    failed = Signal(str)  # текст ошибки

    def __init__(self, url: str, save_path: Path) -> None:
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._cancelled = False

    def cancel(self) -> None:
        """Запросить отмену. Поток прервётся при следующей итерации."""
        self._cancelled = True

    def run(self) -> None:
        """
        Основной метод потока. Вызывается автоматически при .start().
        Здесь и происходит скачивание.
        """
        try:
            # Открываем соединение
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "OWINP/0.1 (+https://github.com/)"},
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                # Размер файла (может быть None, если сервер не отдаёт Content-Length)
                total = int(response.headers.get("Content-Length", 0))

                # Создаём папку, если её нет
                self.save_path.parent.mkdir(parents=True, exist_ok=True)

                # Скачиваем блоками по 64 КБ
                chunk_size = 64 * 1024
                downloaded = 0
                last_emit = 0

                import time
                start_time = time.time()

                with open(self.save_path, "wb") as f:
                    while True:
                        if self._cancelled:
                            f.close()
                            self.save_path.unlink(missing_ok=True)
                            self.failed.emit("Скачивание отменено пользователем")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Считаем скорость
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        # Испускаем сигнал прогресса не чаще 10 раз в секунду
                        now = time.time()
                        if now - last_emit >= 0.1:
                            self.progress_changed.emit(downloaded, total, speed)
                            last_emit = now

                # Финальный сигнал прогресса — 100%
                self.progress_changed.emit(downloaded, total, 0)

            # Успех
            self.finished_ok.emit(str(self.save_path))

        except urllib.error.HTTPError as e:
            self.failed.emit(f"Ошибка HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            self.failed.emit(f"Нет соединения: {e.reason}")
        except Exception as e:
            self.failed.emit(f"Неизвестная ошибка: {e}")