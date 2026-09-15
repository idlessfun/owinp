"""
Проверка обновлений OWINP через GitHub API.

Работает в фоновом потоке, чтобы не блокировать интерфейс.
"""

import json
import urllib.request
import urllib.error

from PySide6.QtCore import QThread, Signal

from app import __version__


# Репозиторий на GitHub — сюда будем обращаться
GITHUB_REPO = "idlessfun/owinp"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateChecker(QThread):
    """
    Фоновый поток для проверки обновлений.

    Сигналы:
        update_available — (info_dict) есть новая версия
        no_update       — обновлений нет (тихо, ничего не делаем)
        check_failed    — (error_text) не удалось проверить (нет интернета и т.п.)
    """

    update_available = Signal(dict)
    no_update = Signal()
    check_failed = Signal(str)

    def run(self) -> None:
        """Основной метод потока. Запускается автоматически при .start()."""
        try:
            print("[updater] Проверка обновлений...")
            print(f"[updater] Текущая версия: {__version__}")

            # Запрос к GitHub API
            req = urllib.request.Request(
                API_URL,
                headers={
                    "User-Agent": f"OWINP/{__version__}",
                    "Accept": "application/vnd.github+json",
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Извлекаем данные о релизе
            tag_name = data.get("tag_name", "")          # например "v0.2.0"
            release_name = data.get("name", "")          # например "OWINP v0.2.0"
            body = data.get("body", "")                  # описание релиза
            html_url = data.get("html_url", "")          # ссылка на страницу релиза
            published_at = data.get("published_at", "")  # дата публикации

            # Убираем префикс "v" из тега: "v0.2.0" → "0.2.0"
            latest_version = tag_name.lstrip("v").strip()

            print(f"[updater] Последняя версия на GitHub: {latest_version}")

            # Сравниваем версии
            if self._is_newer(latest_version, __version__):
                print(f"[updater] ✅ Доступно обновление: {latest_version}")
                self.update_available.emit({
                    "version": latest_version,
                    "name": release_name,
                    "body": body,
                    "url": html_url,
                    "published_at": published_at,
                })
            else:
                print("[updater] У вас последняя версия")
                self.no_update.emit()

        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {e.reason}"
            print(f"[updater] Ошибка проверки: {msg}")
            self.check_failed.emit(msg)

        except urllib.error.URLError as e:
            msg = f"Нет соединения: {e.reason}"
            print(f"[updater] Ошибка проверки: {msg}")
            self.check_failed.emit(msg)

        except Exception as e:
            msg = f"Неизвестная ошибка: {e}"
            print(f"[updater] Ошибка проверки: {msg}")
            self.check_failed.emit(msg)

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        """
        Сравнивает две версии вида "0.1.0" и "0.2.0".
        Возвращает True, если remote новее local.
        """
        try:
            remote_parts = [int(x) for x in remote.split(".")]
            local_parts = [int(x) for x in local.split(".")]
        except ValueError:
            # Если версия нестандартная (например "0.2.0-beta") — считаем как "не новее"
            return False

        # Дополняем нулями до одинаковой длины
        while len(remote_parts) < len(local_parts):
            remote_parts.append(0)
        while len(local_parts) < len(remote_parts):
            local_parts.append(0)

        return remote_parts > local_parts