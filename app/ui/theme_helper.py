"""
Helper to apply the current theme to dialogs.

Dialogs (QDialog) are separate windows, so they don't inherit
the MainWindow stylesheet. This module builds a QSS for them
using the current theme colors.
"""

from app.core.user_settings import load_user_settings, get_theme, DEFAULT_THEME


def get_dialog_qss(extra: str = "") -> str:
    """
    Returns a QSS for a dialog, using the current theme.

    extra: additional QSS to append (e.g. custom widget styles)
    """
    settings = load_user_settings()
    theme_id = settings.get("theme", DEFAULT_THEME)
    theme = get_theme(theme_id)

    accent = theme["accent"]
    background = theme["background"]
    card_bg = theme["card"]
    border = theme["border"]

    is_light = theme_id == "light"
    text_primary = "#1a1a1a" if is_light else "#ffffff"
    text_normal = "#2a2a2a" if is_light else "#e6e6e6"
    text_secondary = "#555555" if is_light else "#9a9a9a"
    text_muted = "#888888" if is_light else "#666666"

    # Soft accent (same mix as in MainWindow._mix)
    accent_soft = _mix(accent, background, 0.75)

    base_qss = f"""
        QDialog {{
            background-color: {background};
            color: {text_normal};
            font-family: "Segoe UI", "Inter", sans-serif;
        }}

        QLabel {{
            color: {text_normal};
        }}

        QPushButton {{
            background-color: {accent_soft};
            color: {accent};
            border: 1px solid {accent};
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 13px;
            min-width: 100px;
        }}

        QPushButton:hover {{
            background-color: {accent};
            color: {background};
        }}

        QPushButton:pressed {{
            background-color: {accent_soft};
        }}

        #SecondaryButton {{
            background-color: transparent;
            color: {text_secondary};
            border: 1px solid {border};
        }}

        #SecondaryButton:hover {{
            background-color: {card_bg};
            color: {text_primary};
            border: 1px solid {accent};
        }}
    """

    # Common colors available as CSS comments for extra QSS
    # (some parts of extra QSS may reference these via string replace)
    header = f"""
        /* Theme colors (for reference):
           accent={accent}
           background={background}
           card={card_bg}
           border={border}
           text_primary={text_primary}
           text_secondary={text_secondary}
           text_muted={text_muted}
        */
    """

    full = base_qss + header + extra

    # Replace placeholders in extra QSS
    replacements = {
        "__ACCENT__": accent,
        "__ACCENT_SOFT__": accent_soft,
        "__BACKGROUND__": background,
        "__CARD__": card_bg,
        "__BORDER__": border,
        "__TEXT_PRIMARY__": text_primary,
        "__TEXT_NORMAL__": text_normal,
        "__TEXT_SECONDARY__": text_secondary,
        "__TEXT_MUTED__": text_muted,
    }
    for key, value in replacements.items():
        full = full.replace(key, value)

    return full


def _mix(color1: str, color2: str, alpha: float) -> str:
    """Mixes two hex colors. Same logic as in MainWindow."""
    def hex_to_rgb(h: str):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    r = int(r1 * (1 - alpha) + r2 * alpha)
    g = int(g1 * (1 - alpha) + g2 * alpha)
    b = int(b1 * (1 - alpha) + b2 * alpha)

    return f"#{r:02x}{g:02x}{b:02x}"