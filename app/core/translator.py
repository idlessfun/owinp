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


def _read_json(path: Path) -> dict:
    """Read JSON file, return dict. On error — empty dict."""
    try:
        with open(path, "r", encoding="utf-8") as f:
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


def set_language(lang_code: str) -> bool:
    """
    Sets the current language and loads its translations.
    Returns True on success.
    """
    global _current_lang, _translations, _fallback

    # Always load fallback (English)
    fallback_path = LOCALES_DIR / f"{FALLBACK_LANG}.json"
    _fallback = _read_json(fallback_path)

    if lang_code == FALLBACK_LANG:
        _translations = _fallback
        _current_lang = FALLBACK_LANG
        print(f"[translator] Language set: {FALLBACK_LANG}")
        return True

    path = LOCALES_DIR / f"{lang_code}.json"
    if not path.exists():
        print(f"[translator] Language file not found: {path}")
        _translations = _fallback
        _current_lang = FALLBACK_LANG
        return False

    _translations = _read_json(path)
    _current_lang = lang_code
    print(f"[translator] Language set: {lang_code}")
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
    text = _translations.get(key) or _fallback.get(key) or key
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
    try:
        system_lang, _ = locale.getdefaultlocale()
        if system_lang:
            code = system_lang.split("_")[0].lower()
            if (LOCALES_DIR / f"{code}.json").exists():
                return code
    except Exception:
        pass
    return FALLBACK_LANG