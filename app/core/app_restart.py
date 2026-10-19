"""
Restarting the application after a setting that requires a restart.

Used by the language switcher: instead of asking the user to close and
reopen OWINP manually (which is easy to get wrong), the app starts a fresh
copy of itself and exits.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QProcess


def _launch_command() -> tuple[str, list[str]]:
    """Returns (executable, arguments) for a fresh application instance."""
    program = sys.executable

    # Running from source: python.exe main.py
    if sys.argv and str(sys.argv[0]).lower().endswith(".py"):
        script = Path(sys.argv[0]).resolve()
        args = [str(script)]
    else:
        # Compiled with Nuitka: sys.executable is OWINP.exe
        args = []

    # Never propagate the build-verification flag to the new instance
    args += [arg for arg in sys.argv[1:] if arg != "--smoke-test"]

    return program, args


def restart_application() -> bool:
    """
    Starts a fresh copy of the app.

    Returns True if the new process was started. The caller is responsible
    for quitting the current instance afterwards.
    """
    program, args = _launch_command()
    working_dir = str(Path(program).resolve().parent)

    try:
        result = QProcess.startDetached(program, args, working_dir)
    except Exception as e:
        print(f"[restart] Failed to start a new instance: {e}")
        return False

    # PySide6 returns (started, pid); older bindings return a bool
    if isinstance(result, tuple):
        started = bool(result[0])
    else:
        started = bool(result)

    print(f"[restart] New instance started: {started} ({program} {args})")
    return started
