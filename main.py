"""
OWINP — Open Windows Programs
Application entry point.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import __version__
from app.core.translator import detect_system_language, set_language
from app.core.user_settings import has_saved_settings, load_user_settings
from app.ui import animations
from app.ui.main_window import MainWindow
from app.ui.splash_screen import SplashScreen


def _prepare_language(settings: dict) -> None:
    """Loads the UI language before the splash screen is painted."""
    lang = settings.get("language", "")
    if not lang or not has_saved_settings():
        lang = detect_system_language()
    set_language(lang)


def _should_show_splash(settings: dict, first_run: bool) -> bool:
    """always / first / never, with a safe fallback for unknown values."""
    mode = settings.get("splash_mode", "always")

    if mode == "never":
        return False
    if mode == "first":
        return first_run
    return True


def _configure_console() -> None:
    """
    Makes console output safe on Windows code pages (cp1251/cp866).

    Log messages may contain non-ASCII characters; without this, a print()
    can raise UnicodeEncodeError inside a worker thread and turn a successful
    check into a fake "unknown error".
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    """Creates an application and displays the main window."""
    _configure_console()

    first_run = not has_saved_settings()
    settings = load_user_settings()

    # One global switch for the whole UI, including the splash screen
    animations.set_enabled(
        bool(settings.get("animations_enabled", True))
        and not bool(settings.get("low_end_mode", False))
    )

    _prepare_language(settings)

    app = QApplication(sys.argv)

    app.setApplicationName("OWINP")
    app.setApplicationDisplayName(f"v{__version__}")
    app.setOrganizationName("OWINP")

    # Application icon — used in the taskbar, Alt+Tab, and the window title bar
    icon_path = Path(__file__).parent / "app" / "resources" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[main] Icon not found: {icon_path}")

    # Migrate old flat cache structure (v0.1.x -> v0.2.x)
    from app.core.cache_manager import migrate_old_cache
    migrate_old_cache()

    splash: SplashScreen | None = None
    if _should_show_splash(settings, first_run):
        splash = SplashScreen()
        splash.show()
        app.processEvents()  # paint the splash before the window is built

    window = MainWindow()

    if splash is not None:
        splash.finish(window)
    else:
        # Set opacity before show() so the window does not flash at full opacity
        if animations.is_enabled():
            window.setWindowOpacity(0.0)
        window.show()
        animations.fade_window(window, 0.0, 1.0, 260)

    try:
        return app.exec()
    finally:
        # Never let a running QThread be destroyed with the process:
        # Qt aborts in that case. Also covers a download dialog that was
        # closed while its download was still in progress.
        from app.core.thread_registry import shutdown_all
        shutdown_all()


if __name__ == "__main__":
    sys.exit(main())