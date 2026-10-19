"""
Lightweight UI animation helpers.

Every animation is registered while it runs. This gives one central switch:
when the user enables "Low-end PC mode" (or just turns animations off),
stop_all() stops everything and removes the temporary graphic effects,
so no widget is left half-transparent.

Animations are intentionally short (150-300 ms) and use OutCubic easing:
they feel responsive and do not get in the way of work.
"""

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


# Global switch (set from user settings at startup)
_enabled = True

# animation -> (target widget, kind)
# kind: "effect" — temporary opacity effect, "window" — windowOpacity,
#       "prop" — ordinary Qt property (nothing to clean up)
_active: dict[QAbstractAnimation, tuple[QWidget, str]] = {}


def is_enabled() -> bool:
    """Returns True when UI animations are allowed."""
    return _enabled


def set_enabled(value: bool) -> None:
    """Turns animations on or off. Turning off also stops everything running."""
    global _enabled
    _enabled = bool(value)
    if not _enabled:
        stop_all()


def _register(anim: QAbstractAnimation, widget: QWidget, kind: str) -> None:
    _active[anim] = (widget, kind)
    anim.finished.connect(lambda: _finish(anim))


def _finish(anim: QAbstractAnimation) -> None:
    """Natural finish: forget the animation and drop the opacity effect."""
    entry = _active.pop(anim, None)
    if entry is None:
        return

    widget, kind = entry
    if kind == "effect":
        _clear_effect(widget)


def _clear_effect(widget: QWidget) -> None:
    try:
        if widget.graphicsEffect() is not None:
            widget.setGraphicsEffect(None)
    except RuntimeError:
        # The C++ object is already gone (window closed)
        pass


def _start(anim: QPropertyAnimation) -> None:
    """Starts a delayed animation only if it was not cancelled meanwhile."""
    if not _enabled or anim not in _active:
        return
    try:
        anim.start()
    except RuntimeError:
        _finish(anim)


def stop(anim: QAbstractAnimation | None) -> None:
    """Stops one animation and cleans up its effect (if any)."""
    if anim is None:
        return

    entry = _active.pop(anim, None)
    try:
        anim.stop()
    except RuntimeError:
        pass

    if entry is not None:
        widget, kind = entry
        if kind == "effect":
            _clear_effect(widget)
        elif kind == "window":
            try:
                widget.setWindowOpacity(1.0)
            except RuntimeError:
                pass


def stop_all() -> None:
    """Stops every registered animation and restores widget state."""
    for anim in list(_active):
        entry = _active.pop(anim, None)
        try:
            anim.stop()
        except RuntimeError:
            pass

        if entry is None:
            continue

        widget, kind = entry
        if kind == "effect":
            _clear_effect(widget)
        elif kind == "window":
            try:
                widget.setWindowOpacity(1.0)
            except RuntimeError:
                pass


def fade_in(
    widget: QWidget,
    duration: int = 180,
    delay: int = 0,
) -> QPropertyAnimation | None:
    """
    Fades a widget in from transparent to fully visible.

    A temporary QGraphicsOpacityEffect is used and removed when the
    animation finishes, so it cannot interfere with anything else later.
    """
    if not _enabled or widget is None:
        return None

    try:
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(max(1, duration))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        _register(anim, widget, "effect")

        if delay > 0:
            QTimer.singleShot(delay, lambda: _start(anim))
        else:
            anim.start()

        return anim
    except RuntimeError:
        return None


def fade_window(
    window: QWidget,
    start: float = 0.0,
    end: float = 1.0,
    duration: int = 260,
    on_finished=None,
) -> QPropertyAnimation | None:
    """Animates the opacity of a top-level window (used for splash and main)."""
    if window is None:
        return None

    if not _enabled:
        try:
            window.setWindowOpacity(end)
        except RuntimeError:
            return None
        if callable(on_finished):
            on_finished()
        return None

    try:
        anim = QPropertyAnimation(window, b"windowOpacity", window)
        anim.setDuration(max(1, duration))
        anim.setStartValue(float(start))
        anim.setEndValue(float(end))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if callable(on_finished):
            anim.finished.connect(on_finished)

        _register(anim, window, "window")
        window.setWindowOpacity(float(start))
        anim.start()
        return anim
    except RuntimeError:
        return None


def animate_max_height(
    widget: QWidget,
    start: int,
    end: int,
    duration: int = 220,
    on_finished=None,
) -> QPropertyAnimation | None:
    """Smoothly expands/collapses a widget by animating its maximumHeight."""
    if widget is None:
        return None

    if not _enabled:
        try:
            widget.setMaximumHeight(int(end))
        except RuntimeError:
            return None
        if callable(on_finished):
            on_finished()
        return None

    try:
        anim = QPropertyAnimation(widget, b"maximumHeight", widget)
        anim.setDuration(max(1, duration))
        anim.setStartValue(int(start))
        anim.setEndValue(int(end))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if callable(on_finished):
            anim.finished.connect(on_finished)

        _register(anim, widget, "prop")
        anim.start()
        return anim
    except RuntimeError:
        return None


def animate_value(
    widget: QWidget,
    value: int,
    duration: int = 160,
) -> QPropertyAnimation | None:
    """Smoothly animates an integer property such as QProgressBar.value."""
    if widget is None:
        return None

    if not _enabled:
        try:
            widget.setValue(int(value))
        except (RuntimeError, AttributeError):
            pass
        return None

    try:
        anim = QPropertyAnimation(widget, b"value", widget)
        anim.setDuration(max(1, duration))
        anim.setStartValue(int(widget.value()))
        anim.setEndValue(int(value))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        _register(anim, widget, "prop")
        anim.start()
        return anim
    except (RuntimeError, AttributeError):
        return None
