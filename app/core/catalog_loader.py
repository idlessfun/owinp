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

from PySide6.QtCore import QThread, Signal

from app.core.cache_manager import set_last_update_time


# --- Константы ---
GITHUB_USER = "idlessfun"
GITHUB_REPO = "owinp"
GITHUB_BRANCH = "master"
APPS_PATH_IN_REPO = "app/apps"              # где в репозитории лежат JSON-карточки
ICONS_PATH_IN_REPO = "app/resources/icons"  # где иконки
SCREENSHOTS_PATH_IN_REPO = "app/resources/screenshots"  # где скриншоты

# URL для GitHub API — получить список файлов
API_URL = (
    f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
    f"/contents/{APPS_PATH_IN_REPO}?ref={GITHUB_BRANCH}"
)

# Базовые URL для raw-скачивания (для JSON и картинок с GitHub)
RAW_APPS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{APPS_PATH_IN_REPO}/"
)
RAW_ICONS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{ICONS_PATH_IN_REPO}/"
)
RAW_SCREENSHOTS_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/{SCREENSHOTS_PATH_IN_REPO}/"
)

# Куда сохранять кэш — %APPDATA%\OWINP\cache\
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CACHE_ROOT = APPDATA / "OWINP" / "cache"
CACHE_DIR = CACHE_ROOT / "apps"                 # JSON-файлы
CACHE_ICONS = CACHE_ROOT / "icons"              # иконки
CACHE_SCREENSHOTS = CACHE_ROOT / "screenshots"  # скриншоты


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

            # 1. Создаём папки кэша (если их нет)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_ICONS.mkdir(parents=True, exist_ok=True)
            CACHE_SCREENSHOTS.mkdir(parents=True, exist_ok=True)

            # 2. Получаем список файлов в app/apps/ через GitHub API
            files = self._fetch_file_list()
            if not files:
                print("[catalog] Список файлов пуст")
                self.finished_ok.emit(0)
                return

            # 3. Скачиваем каждый .json файл + картинки к нему
            downloaded = 0
            for filename in files:
                if not filename.endswith(".json"):
                    continue

                data = self._download_json(filename)
                if data is None:
                    continue

                downloaded += 1

                # Скачиваем иконку и скриншоты этой программы
                self._download_assets(data)

            print(f"[catalog] Обновлено файлов: {downloaded}")
            set_last_update_time()
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

        if not isinstance(data, list):
            return []

        return [
            item.get("name", "")
            for item in data
            if isinstance(item, dict) and item.get("type") == "file"
        ]

    def _download_json(self, filename: str) -> dict | None:
        """
        Скачивает один JSON-файл через raw.githubusercontent.com
        и сохраняет в кэш. Возвращает dict с данными при успехе, иначе None.
        """
        url = RAW_APPS_BASE + filename

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
                return None

            # Проверка обязательных полей
            if "name" not in data or "id" not in data:
                print(f"[catalog] {filename} — нет полей id/name, пропуск")
                return None

            # Сохраняем в кэш
            target = CACHE_DIR / filename
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[catalog] Скачано: {filename}")
            return data

        except json.JSONDecodeError:
            print(f"[catalog] {filename} — битый JSON, пропуск")
            return None
        except Exception as e:
            print(f"[catalog] {filename} — ошибка: {e}")
            return None

    def _download_assets(self, data: dict) -> None:
        """
        Скачивает иконку и скриншоты программы в кэш.

        Логика:
        - Если в JSON есть icon_url — используем его
        - Если только icon (имя файла) — строим URL из своего GitHub
        - Аналогично для screenshots/screenshots_urls
        """
        app_id = data.get("id", "unknown")

        # --- Иконка ---
        icon_url = data.get("icon_url")
        icon_name = data.get("icon")

        if icon_url:
            ext = self._extract_extension(icon_url)
            local_name = f"{app_id}{ext}"
            self._download_image(icon_url, CACHE_ICONS / local_name)
        elif icon_name:
            url = RAW_ICONS_BASE + icon_name
            self._download_image(url, CACHE_ICONS / icon_name)

        # --- Скриншоты ---
        screenshot_urls = data.get("screenshots_urls", [])
        screenshot_names = data.get("screenshots", [])

        # Внешние URL
        for i, url in enumerate(screenshot_urls):
            ext = self._extract_extension(url)
            local_name = f"{app_id}_{i}{ext}"
            self._download_image(url, CACHE_SCREENSHOTS / local_name)

        # Имена файлов из своего репо
        for name in screenshot_names:
            url = RAW_SCREENSHOTS_BASE + name
            self._download_image(url, CACHE_SCREENSHOTS / name)

    def _download_image(self, url: str, target: Path) -> bool:
        """
        Скачивает одну картинку и сохраняет в target.
        Возвращает True при успехе.
        """
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OWINP/0.1"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()

            if not content or len(content) < 20:
                print(f"[catalog] Картинка пуста: {url}")
                return False

            with open(target, "wb") as f:
                f.write(content)

            print(f"[catalog] Скачана картинка: {target.name}")
            return True

        except Exception as e:
            print(f"[catalog] Картинка не скачана ({url}): {e}")
            return False

    @staticmethod
    def _extract_extension(url: str) -> str:
        """
        Извлекает расширение файла из URL.
        Например: ".../vlc.png" -> ".png"
                  ".../file.jpg?x=1" -> ".jpg"
        Возвращает ".png" по умолчанию.
        """
        clean = url.split("?")[0]
        if "." in clean.rsplit("/", 1)[-1]:
            ext = "." + clean.rsplit(".", 1)[-1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
                return ext
        return ".png"