"""
Загрузчик JSON-карточек программ.

Сначала пытается прочитать кэшированные JSON
из кэша (скачанные с GitHub).
Если кэша нет — читает встроенные JSON из app/apps/.
"""

import json
from pathlib import Path

from app.core.cache_manager import cache_exists, load_cached_apps


# Путь к встроенным JSON (поставляются с приложением)
APPS_DIR = Path(__file__).parent.parent / "apps"


def load_all_apps() -> list[dict]:
    """
    Возвращает список всех программ.

    Приоритет:
    1. Кэш (из %APPDATA%) — если есть
    2. Встроенные (app/apps/) — как запасной вариант
    """
    # Сначала пробуем кэш
    if cache_exists():
        cached = load_cached_apps()
        if cached:
            print(f"[app_loader] Загружено из кэша: {len(cached)} шт.")
            return cached

    # Если кэша нет или он пуст — используем встроенные
    print("[app_loader] Кэш пуст — используем встроенный каталог")
    return load_builtin_apps()


def load_builtin_apps() -> list[dict]:
    """
    Читает JSON-файлы из встроенной папки app/apps/.

    Возвращает список словарей. Битые файлы пропускает.
    """
    apps: list[dict] = []

    if not APPS_DIR.exists():
        print(f"[app_loader] Папка не найдена: {APPS_DIR}")
        return apps

    for json_file in sorted(APPS_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            apps.append(data)
            print(f"[app_loader] Загружено (встроенное): {json_file.name}")
        except json.JSONDecodeError as e:
            print(f"[app_loader] Ошибка в файле {json_file.name}: {e}")
        except Exception as e:
            print(f"[app_loader] Не удалось прочитать {json_file.name}: {e}")

    return apps