"""
Custom startup splash screen.

Everything is painted with QPainter: a rounded card, the application icon
inside a rotating accent ring, the title and a thin progress bar. There are
no external video/GIF assets, so the splash looks the same on every machine
and can be turned into a static picture in "low-end PC" mode.
"""

from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QWidget

from app import __version__
from app.core.translator import t
from app.core.user_settings import get_theme, load_user_settings
from app.ui import animations


ICON_PATH = Path(__file__).parent.parent / "resources" / "icon.png"

CARD_WIDTH = 560
CARD_HEIGHT = 320
CARD_RADIUS = 26


class SplashScreen(QWidget):
    """Frameless, translucent startup splash with a soft accent animation."""

    def __init__(self, animated: bool = True) -> None:
        super().__init__(None)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setWindowTitle("OWINP")

        self._animated = bool(animated) and animations.is_enabled()
        self._angle = 35.0
        # Static splash (low-end mode) looks better with a partially filled bar
        self._progress = 0.06 if self._animated else 0.55
        self._target_window: QWidget | None = None
        self._elapsed = QElapsedTimer()
        self._elapsed.start()

        # Match the user's current theme
        settings = load_user_settings()
        self._accent = QColor(get_theme(settings.get("theme", "dark-blue"))["accent"])

        # Icon is loaded once; it is small and already shipped with the app
        self._icon = QPixmap(str(ICON_PATH)) if ICON_PATH.exists() else QPixmap()

        self._center_on_screen()

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        if self._animated:
            self._timer.start()

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        self._angle = (self._angle + 3.2) % 360.0
        if self._progress < 0.95:
            self._progress = min(0.95, self._progress + 0.012)
        self.update()

    def _stop_timer(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.move(
            available.center().x() - self.width() // 2,
            available.center().y() - self.height() // 2,
        )

    def _status_text(self) -> str:
        if self._progress >= 0.90:
            return t("splash.ready")
        if self._progress >= 0.40:
            return t("splash.loading")
        return t("splash.preparing")

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        card = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        card_path = QPainterPath()
        card_path.addRoundedRect(card, CARD_RADIUS, CARD_RADIUS)

        # Card background
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0.0, QColor("#1d1f26"))
        background.setColorAt(1.0, QColor("#13141a"))
        painter.fillPath(card_path, background)

        # Soft accent glow in the top-left corner
        glow = QRadialGradient(QPointF(90, 30), 300)
        glow.setColorAt(0.0, QColor(self._accent.red(), self._accent.green(),
                                   self._accent.blue(), 46))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(card_path, glow)

        # Card border
        painter.setPen(QPen(QColor("#30323b"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(card_path)

        # --- Icon in a circle with a rotating ring ---
        center = QPointF(CARD_WIDTH / 2, 112)
        icon_rect = QRectF(center.x() - 44, center.y() - 44, 88, 88)
        self._paint_icon(painter, icon_rect)
        self._paint_ring(painter, center)

        # --- Title ---
        title_font = QFont("Segoe UI", 1)
        title_font.setPixelSize(30)
        title_font.setWeight(QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6.0)
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRectF(0, 178, CARD_WIDTH, 42),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "OWINP",
        )

        # --- Subtitle ---
        subtitle_font = QFont("Segoe UI", 1)
        subtitle_font.setPixelSize(12)
        subtitle_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#9a9daa"))
        painter.drawText(
            QRectF(0, 218, CARD_WIDTH, 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            t("splash.subtitle", version=__version__),
        )

        # --- Status and percent ---
        status_font = QFont("Segoe UI", 1)
        status_font.setPixelSize(11)
        painter.setFont(status_font)
        painter.setPen(QColor("#7f8496"))
        painter.drawText(
            QRectF(80, 248, 340, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._status_text(),
        )
        painter.setPen(self._accent)
        painter.drawText(
            QRectF(400, 248, 80, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{int(self._progress * 100)}%",
        )

        # --- Progress bar ---
        track = QRectF(80, 276, 400, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2a2c34"))
        painter.drawRoundedRect(track, 3, 3)

        if self._progress > 0:
            fill = QRectF(
                track.x(), track.y(), max(6.0, track.width() * self._progress), track.height()
            )
            fill_gradient = QLinearGradient(track.topLeft(), track.topRight())
            fill_gradient.setColorAt(0.0, self._accent)
            fill_gradient.setColorAt(1.0, self._accent.lighter(135))
            painter.setBrush(fill_gradient)
            painter.drawRoundedRect(fill, 3, 3)

    def _paint_icon(self, painter: QPainter, rect: QRectF) -> None:
        clip = QPainterPath()
        clip.addRoundedRect(rect, 22, 22)

        painter.save()
        painter.setClipPath(clip)

        if not self._icon.isNull():
            painter.drawPixmap(rect.toRect(), self._icon)
        else:
            painter.fillRect(rect, QColor("#24262d"))
            fallback_font = QFont("Segoe UI", 1)
            fallback_font.setPixelSize(40)
            fallback_font.setWeight(QFont.Weight.Bold)
            painter.setFont(fallback_font)
            painter.setPen(self._accent)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "O")

        painter.restore()

        painter.setPen(QPen(QColor("#3a3d47"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(clip)

    def _paint_ring(self, painter: QPainter, center: QPointF) -> None:
        radius = 60.0
        ring_rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )

        # Faint full circle so the rotating accent does not look like a stray arc
        painter.setPen(QPen(QColor("#2b2d35"), 2.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(ring_rect)

        segments = 16
        segment_angle = 7.0
        for index in range(segments):
            alpha = int(18 + 232 * (index / (segments - 1)))
            color = QColor(
                self._accent.red(),
                self._accent.green(),
                self._accent.blue(),
                alpha,
            )
            pen = QPen(color, 2.6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(
                ring_rect,
                int((self._angle + index * segment_angle) * 16),
                int(segment_angle * 16),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def minimum_duration_ms(self) -> int:
        """How long the splash stays visible at least."""
        return 1150 if self._animated else 450

    def finish(self, window: QWidget) -> None:
        """
        Schedules the transition from the splash to the main window.

        The splash stays visible at least `minimum_duration_ms`, then fades
        out while the main window fades in.
        """
        self._target_window = window
        remaining = max(0, self.minimum_duration_ms() - self._elapsed.elapsed())
        QTimer.singleShot(remaining, self._reveal)

    def _reveal(self) -> None:
        window = self._target_window
        if window is None:
            self.close()
            return

        self._stop_timer()
        self._progress = 1.0
        self.update()

        if animations.is_enabled():
            animations.fade_window(self, 1.0, 0.0, 200, on_finished=self.close)
            window.setWindowOpacity(0.0)
            window.show()
            animations.fade_window(window, 0.0, 1.0, 280)
        else:
            self.close()
            window.setWindowOpacity(1.0)
            window.show()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._stop_timer()
        super().closeEvent(event)
