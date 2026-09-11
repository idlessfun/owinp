"""
OWINP — Open Windows Programs
Точка входа приложения.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import __version__
from app.ui.main_window import MainWindow


def main() -> int:
    """Создаёт приложение и показывает главное окно."""
    app = QApplication(sys.argv)

    app.setApplicationName("OWINP")
    app.setApplicationDisplayName(f"v{__version__}")
    app.setOrganizationName("OWINP")

    # Иконка приложения — используется в панели задач, Alt+Tab и заголовке окна
    icon_path = Path(__file__).parent / "app" / "resources" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[main] Иконка не найдена: {icon_path}")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())