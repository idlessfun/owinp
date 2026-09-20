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


def main() -> int:
    """Creates an application and displays the main window."""
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

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())