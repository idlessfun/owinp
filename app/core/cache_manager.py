"""
Менеджер кэша каталога программ.

Читает и управляет скачанными JSON-файлами
из кэша (папка задаётся константой CACHE_DIR ниже).

Безопасность:
- Читает только свою папку
- Не удаляет ничего вне своей папки
- Валидирует каждый JSON перед возвратом
"""

import json
import os
import shutil
from pathlib import Path


# --- Пути (те же, что в catalog_loader.py) ---
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CACHE_ROOT = APPDATA / "OWINP" / "cache"
CACHE_DIR = CACHE_ROOT / "apps"                 # JSON-файлы
CACHE_ICONS = CACHE_ROOT / "icons"              # иконки
CACHE_SCREENSHOTS = CACHE_ROOT / "screenshots"  # скриншоты


def cache_exists() -> bool:
    """Есть ли хотя бы один JSON-файл в кэше."""
    if not CACHE_DIR.exists():
        return False
    return any(CACHE_DIR.glob("*.json"))


def load_cached_apps() -> list[dict]:
    """
    Читает все JSON-файлы из кэша.

    Возвращает список словарей. Битые файлы пропускает
    (не ломает приложение из-за одного плохого файла).
    """
    if not CACHE_DIR.exists():
        return []

    apps: list[dict] = []

    for json_file in sorted(CACHE_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Валидация: словарь? есть обязательные поля?
            if not isinstance(data, dict):
                print(f"[cache] {json_file.name} — не объект JSON, пропуск")
                continue

            if "id" not in data or "name" not in data:
                print(f"[cache] {json_file.name} — нет полей id/name, пропуск")
                continue

            apps.append(data)

        except json.JSONDecodeError as e:
            print(f"[cache] {json_file.name} — битый JSON: {e}")
        except Exception as e:
            print(f"[cache] {json_file.name} — ошибка чтения: {e}")

    return apps


def clear_cache() -> bool:
    """
    Полностью очищает папку кэша.
    Возвращает True при успехе.
    """
    if not CACHE_DIR.exists():
        return True

    try:
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[cache] Очищено: {CACHE_DIR}")
        return True
    except Exception as e:
        print(f"[cache] Не удалось очистить кэш: {e}")
        return False


def get_cache_dir() -> Path:
    """Возвращает путь к папке кэша (для отладки или показа пользователю)."""
    return CACHE_DIR
# --- Работа со временем последнего обновления ---

import time

LAST_UPDATE_FILE = APPDATA / "OWINP" / "cache" / "last_update.txt"
THROTTLE_SECONDS = 3600  # 1 час


def get_last_update_time() -> float:
    """
    Возвращает Unix-время последнего успешного обновления каталога.
    Если файла нет или он битый — возвращает 0 (давно).
    """
    if not LAST_UPDATE_FILE.exists():
        return 0.0
    try:
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except Exception:
        return 0.0


def set_last_update_time() -> None:
    """Записывает текущее время как момент последнего обновления."""
    try:
        LAST_UPDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"[cache] Не удалось сохранить время обновления: {e}")


def should_update_now() -> bool:
    """
    Проверяет, надо ли обновлять каталог сейчас.

    Возвращает True если:
    - никогда не обновлялись, или
    - прошло больше THROTTLE_SECONDS с последнего обновления
    """
    last = get_last_update_time()
    if last == 0:
        return True
    return (time.time() - last) > THROTTLE_SECONDS
# --- Работа с картинками ---


def find_icon(app_data: dict) -> Path | None:
    """
    Ищет иконку программы в кэше.

    Логика:
    1. Если есть поле "icon_url" — ищем файл <id>.<ext> в CACHE_ICONS
    2. Если есть поле "icon" — ищем файл с этим именем в CACHE_ICONS
    3. Если ничего не нашли — возвращаем None

    Возвращает Path к найденному файлу или None.
    """
    if not CACHE_ICONS.exists():
        return None

    app_id = app_data.get("id", "")

    # Сначала — icon_url: имя файла = <id>.<ext>
    if app_data.get("icon_url") and app_id:
        # Пробуем популярные расширения
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
            candidate = CACHE_ICONS / f"{app_id}{ext}"
            if candidate.exists():
                return candidate

    # Потом — icon: имя файла как есть
    icon_name = app_data.get("icon")
    if icon_name:
        candidate = CACHE_ICONS / icon_name
        if candidate.exists():
            return candidate

    return None


def find_screenshot(app_data: dict, name_or_index) -> Path | None:
    """
    Ищет скриншот программы в кэше.

    name_or_index — это:
    - str: имя файла из поля "screenshots" (например, "7zip_1.png")
    - int: индекс из поля "screenshots_urls" (например, 0, 1, 2)

    Возвращает Path к найденному файлу или None.
    """
    if not CACHE_SCREENSHOTS.exists():
        return None

    app_id = app_data.get("id", "")

    # По имени файла (из нашего репо)
    if isinstance(name_or_index, str):
        candidate = CACHE_SCREENSHOTS / name_or_index
        if candidate.exists():
            return candidate
        return None

    # По индексу (из внешнего URL)
    if isinstance(name_or_index, int) and app_id:
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"):
            candidate = CACHE_SCREENSHOTS / f"{app_id}_{name_or_index}{ext}"
            if candidate.exists():
                return candidate

    return None


def clear_assets_cache() -> bool:
    """
    Очищает только картинки (иконки и скриншоты), не трогая JSON.
    Возвращает True при успехе.
    """
    success = True
    for folder in (CACHE_ICONS, CACHE_SCREENSHOTS):
        if folder.exists():
            try:
                shutil.rmtree(folder)
                folder.mkdir(parents=True, exist_ok=True)
                print(f"[cache] Очищено: {folder}")
            except Exception as e:
                print(f"[cache] Не удалось очистить {folder}: {e}")
                success = False
    return success