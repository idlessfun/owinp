"""
Translation system for OWINP.

Loads translations from JSON files in app/locales/.
Each file is named <lang_code>.json, e.g. ru.json, en.json, fr.json.

Fallback: if a key is missing in the current language, use English.
If English is missing too — return the key itself.
"""

import json
import locale
from pathlib import Path


# Directory with locale files
LOCALES_DIR = Path(__file__).parent.parent / "locales"

FALLBACK_LANG = "en"

# Current state
_current_lang = FALLBACK_LANG
_translations: dict[str, str] = {}
_fallback: dict[str, str] = {}
_fallback_loaded = False


def _read_json(path: Path) -> dict:
    """Read JSON file, return dict. On error — empty dict."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[translator] Error reading {path.name}: {e}")
        return {}


def load_available_languages() -> list[dict]:
    """
    Scans app/locales/ for *.json files.
    Returns list of dicts: [{"code": "ru", "name": "Русский"}, ...]
    Sorted: English and Russian first, then alphabetically.
    """
    if not LOCALES_DIR.exists():
        print(f"[translator] Locales dir not found: {LOCALES_DIR}")
        return []

    languages = []
    for file in sorted(LOCALES_DIR.glob("*.json")):
        code = file.stem
        data = _read_json(file)
        name = data.get("_language_name", code)
        languages.append({"code": code, "name": name})

    # Sort: en first, then ru, then others alphabetically
    def sort_key(lang):
        if lang["code"] == "en":
            return (0, "")
        if lang["code"] == "ru":
            return (1, "")
        return (2, lang["code"])

    return sorted(languages, key=sort_key)


def _load_fallback() -> None:
    """Loads the English fallback dictionary once."""
    global _fallback, _fallback_loaded
    if _fallback_loaded:
        return
    _fallback = _read_json(LOCALES_DIR / f"{FALLBACK_LANG}.json")
    _fallback_loaded = True


def _normalize_language_code(value: object) -> str:
    """Keeps language codes to a single safe file-name component."""
    if not isinstance(value, str):
        return ""

    code = value.strip().lower()
    if not code or len(code) > 16:
        return ""
    if not all(ch.isalnum() or ch in "_-" for ch in code):
        return ""
    return code


def set_language(lang_code: str) -> bool:
    """
    Sets the current language and loads its translations.
    Returns True on success.
    """
    global _current_lang, _translations, _fallback_loaded

    # Always reload fallback (English)
    _fallback_loaded = False
    _load_fallback()

    code = _normalize_language_code(lang_code)
    if not code:
        print(f"[translator] Invalid language code: {lang_code!r}")
        _translations = dict(_fallback)
        _current_lang = FALLBACK_LANG
        return False

    if code == FALLBACK_LANG:
        _translations = dict(_fallback)
        _current_lang = FALLBACK_LANG
        print(f"[translator] Language set: {FALLBACK_LANG}")
        return True

    path = LOCALES_DIR / f"{code}.json"
    if not path.exists():
        print(f"[translator] Language file not found: {path}")
        _translations = dict(_fallback)
        _current_lang = FALLBACK_LANG
        return False

    data = _read_json(path)
    if not data:
        print(f"[translator] Language file is empty or broken: {path}")
        _translations = dict(_fallback)
        _current_lang = FALLBACK_LANG
        return False

    _translations = data
    _current_lang = code
    print(f"[translator] Language set: {code}")
    return True


def get_current_language() -> str:
    """Returns the current language code (e.g. 'ru', 'en')."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """
    Returns translation for the given key.

    If key not found in current language — tries English.
    If not found in English — returns key itself.

    kwargs: substitute {name} placeholders.
        Example: t("hello", name="Anton") → "Hello, Anton"
    """
    _load_fallback()

    text = _translations.get(key) or _fallback.get(key) or key
    if not isinstance(text, str):
        text = str(text)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


def detect_system_language() -> str:
    """
    Tries to detect system language.
    Returns language code if a matching locale file exists, else 'en'.
    """
    system_lang = ""

    # Qt knows the real system locale even on Windows ("ru_RU", not "Russian_Russia")
    try:
        from PySide6.QtCore import QLocale
        system_lang = QLocale.system().name() or ""
    except Exception:
        system_lang = ""

    if not system_lang:
        try:
            # Python 3.12+: getdefaultlocale() is deprecated, getlocale() is preferred
            system_lang = locale.getlocale()[0] or ""
        except Exception:
            system_lang = ""

    if not system_lang:
        try:
            getter = getattr(locale, "getdefaultlocale", None)
            if callable(getter):
                system_lang = getter()[0] or ""
        except Exception:
            system_lang = ""

    if system_lang:
        code = system_lang.replace("-", "_").split("_")[0].lower()
        if (LOCALES_DIR / f"{code}.json").exists():
            return code

    return FALLBACK_LANG