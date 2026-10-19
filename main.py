"""
OWINP — Open Windows Programs
Application entry point.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import __version__
from app.ui.main_window import MainWindow


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

    window = MainWindow()
    window.show()

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