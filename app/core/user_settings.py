r"""
Пользовательские настройки клиента OWINP.

Хранит выбранную тему и настройки интерфейса.
Сохраняет в %APPDATA%\OWINP\settings.json

Безопасность:
- Файл не содержит секретов
- Хранится локально
- При отсутствии — используются значения по умолчанию
"""

import json
import os
from pathlib import Path


APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
SETTINGS_DIR = APPDATA / "OWINP"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


# ---------- Готовые темы ----------
THEMES = {
    "dark-blue": {
        "name": "🌙  Тёмно-синяя",
        "background": "#1e1f22",
        "sidebar":    "#17181b",
        "card":       "#24262b",
        "border":     "#2f3138",
        "accent":     "#7c9cff",
    },
    "dark-red": {
        "name": "🔴  Тёмно-красная",
        "background": "#1a0d12",
        "sidebar":    "#12080c",
        "card":       "#261218",
        "border":     "#3a1a22",
        "accent":     "#ff5577",
    },
    "dark-green": {
        "name": "🟢  Тёмно-зелёная",
        "background": "#0f1a14",
        "sidebar":    "#08120d",
        "card":       "#16241d",
        "border":     "#1f362a",
        "accent":     "#5adb8a",
    },
    "dark-purple": {
        "name": "🟣  Тёмно-фиолетовая",
        "background": "#150f1f",
        "sidebar":    "#0d0814",
        "card":       "#1d1429",
        "border":     "#2c1e3d",
        "accent":     "#b388ff",
    },
    "light": {
        "name": "☀️  Светлая",
        "background": "#f5f5f7",
        "sidebar":    "#e8e8ec",
        "card":       "#ffffff",
        "border":     "#d0d0d5",
        "accent":     "#3b6fd9",
    },
}


DEFAULT_THEME = "dark-blue"
FONT_SIZES = [12, 14, 16, 18]


# Все настройки клиента с дефолтными значениями
DEFAULTS = {
    "theme": DEFAULT_THEME,              # выбранная тема
    "font_size": 14,                     # размер шрифта
    "check_updates_on_start": True,      # проверять обновления при запуске
    "refresh_catalog_on_start": True,    # обновлять каталог при запуске
    "auto_run_after_download": False,    # запускать файл после скачивания
    "show_update_banner": True,          # показывать баннер «Доступно обновление»
    "compact_mode": False,               # компактный режим (карточки меньше)
    "animations_enabled": True,          # анимации (заглушка — в будущем)
    "show_screenshots": True,            # показывать скриншоты на странице программы
}


def load_user_settings() -> dict:
    """Загружает настройки. Если файла нет — дефолты."""
    if not SETTINGS_FILE.exists():
        return dict(DEFAULTS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = dict(DEFAULTS)
        result.update(data)
        return result
    except Exception as e:
        print(f"[user_settings] Ошибка загрузки: {e}")
        return dict(DEFAULTS)


def save_user_settings(settings: dict) -> bool:
    """Сохраняет настройки."""
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print(f"[user_settings] Сохранено: {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"[user_settings] Ошибка сохранения: {e}")
        return False


def get_user_settings_path() -> Path:
    """Возвращает путь к файлу настроек."""
    return SETTINGS_FILE


def get_theme(theme_id: str) -> dict:
    """Возвращает словарь с цветами темы."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])