"""
Загрузчик каталога программ с GitHub.

Скачивает свежие JSON-карточки программ с GitHub
и сохраняет их в локальный кэш, чтобы приложение
всегда показывало актуальный каталог.

Безопасность:
- Только HTTPS
- Только два домена: api.github.com и raw.githubusercontent.com
- Скачанные данные проверяются как JSON
- Никаких eval/exec на скачанных данных
- Никаких shell-команд
- Пишем только в свою папку в %APPDATA%
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from app.core.cache_manager import set_last_update_time

from PySide6.QtCore import QThread, Signal


# --- Константы ---
GITHUB_USER = "idlessfun"
GITHUB_REPO = "owinp"
GITHUB_BRANCH = "master"
APPS_PATH_IN_REPO = "app/apps"   # где в репозитории лежат JSON-карточки

# Разрешённые домены (whitelist — код не сможет обратиться никуда, кроме них)
API_URL = (
    f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
    f"/contents/{APPS_PATH_IN_REPO}?ref={GITHUB_BRANCH}"
)
RAW_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{APPS_PATH_IN_REPO}/"
)

# Куда сохранять кэш — %APPDATA%\OWINP\cache\apps\
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CACHE_DIR = APPDATA / "OWINP" / "cache" / "apps"


class CatalogLoader(QThread):
    """
    Фоновый поток для скачивания свежего каталога с GitHub.

    Сигналы:
        finished_ok — (количество скачанных JSON) успех
        failed      — (текст ошибки) не удалось
    """

    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(self, force: bool = False) -> None:
        """
        force=True — игнорировать троттлинг, обновить прямо сейчас.
        force=False — обновлять только если прошёл час (по умолчанию).
        """
        super().__init__()
        self.force = force

    def run(self) -> None:
        """Основной метод потока."""
        try:
            # Троттлинг: если не force и недавно обновлялись — пропускаем
            if not self.force:
                from app.core.cache_manager import should_update_now
                if not should_update_now():
                    print("[catalog] Обновление каталога пропущено (троттлинг)")
                    self.finished_ok.emit(0)
                    return

            print("[catalog] Проверка обновлений каталога...")

            # 1. Создаём папку кэша (если её нет)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # 2. Получаем список файлов в app/apps/ через GitHub API
            files = self._fetch_file_list()
            if not files:
                print("[catalog] Список файлов пуст")
                self.finished_ok.emit(0)
                return

            # 3. Скачиваем каждый .json файл
            downloaded = 0
            for filename in files:
                if not filename.endswith(".json"):
                    continue

                if self._download_json(filename):
                    downloaded += 1

            print(f"[catalog] Обновлено файлов: {downloaded}")
            set_last_update_time()   # записываем время
            self.finished_ok.emit(downloaded)

        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {e.reason}"
            print(f"[catalog] Ошибка: {msg}")
            self.failed.emit(msg)

        except urllib.error.URLError as e:
            msg = f"Нет соединения: {e.reason}"
            print(f"[catalog] Ошибка: {msg}")
            self.failed.emit(msg)

        except Exception as e:
            msg = f"Неизвестная ошибка: {e}"
            print(f"[catalog] Ошибка: {msg}")
            self.failed.emit(msg)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------
    def _fetch_file_list(self) -> list[str]:
        """
        Запрашивает список файлов в папке app/apps/ через GitHub API.
        Возвращает список имён файлов (например, ["7-zip.json", "notepadpp.json"]).
        """
        req = urllib.request.Request(
            API_URL,
            headers={
                "User-Agent": "OWINP/0.1",
                "Accept": "application/vnd.github+json",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        # GitHub возвращает список объектов с полем "name"
        if not isinstance(data, list):
            return []

        return [
            item.get("name", "")
            for item in data
            if isinstance(item, dict) and item.get("type") == "file"
        ]

    def _download_json(self, filename: str) -> bool:
        """
        Скачивает один JSON-файл через raw.githubusercontent.com
        и сохраняет в кэш. Возвращает True при успехе.
        """
        url = RAW_BASE + filename

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OWINP/0.1"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")

            # Валидация: это правда JSON?
            data = json.loads(raw)
            if not isinstance(data, dict):
                print(f"[catalog] {filename} — не объект JSON, пропуск")
                return False

            # Проверка обязательных полей
            if "name" not in data or "id" not in data:
                print(f"[catalog] {filename} — нет полей id/name, пропуск")
                return False

            # Сохраняем в кэш
            target = CACHE_DIR / filename
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[catalog] Скачано: {filename}")
            return True

        except json.JSONDecodeError:
            print(f"[catalog] {filename} — битый JSON, пропуск")
            return False
        except Exception as e:
            print(f"[catalog] {filename} — ошибка: {e}")
            return False