"""
Загрузчик JSON-карточек программ.

Читает все .json-файлы из папки app/apps/ и возвращает
список словарей с информацией о программах.
"""

import json
from pathlib import Path

# Определяем путь к папке с карточками относительно этого файла.
# __file__ — путь к этому файлу (app_loader.py)
# .parent — папка core/
# .parent.parent — папка app/
# / "apps" — добавляем apps/
APPS_DIR = Path(__file__).parent.parent / "apps"


def load_all_apps() -> list[dict]:
    """
    Читает все .json-файлы из папки app/apps/.

    Возвращает список словарей. Если файл битый — пропускает его
    и печатает предупреждение в консоль.
    """
    apps: list[dict] = []

    if not APPS_DIR.exists():
        print(f"[app_loader] Папка не найдена: {APPS_DIR}")
        return apps

    # sorted() — чтобы порядок карточек был стабильным (по имени файла)
    for json_file in sorted(APPS_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            apps.append(data)
            print(f"[app_loader] Загружено: {json_file.name}")
        except json.JSONDecodeError as e:
            print(f"[app_loader] Ошибка в файле {json_file.name}: {e}")
        except Exception as e:
            print(f"[app_loader] Не удалось прочитать {json_file.name}: {e}")

    return apps