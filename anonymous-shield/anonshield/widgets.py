# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — widgets modernos (botão-escudo + toggle switch)."""
from __future__ import annotations

import math

from PyQt6.QtCore import QMimeData, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget


class OnionWidget(QWidget):
    """Botão-escudo desenhado: glow pulsante + anel de progresso + escudo."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "off"  # on | ing | off
        self.progress = 0.0
        self._phase = 0.0
        self.setMinimumSize(190, 190)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(90)

    def set_state(self, mode: str, progress: float = 0.0) -> None:
        self.mode = mode
        self.progress = max(0.0, min(1.0, progress))

    def _step(self) -> None:
        if self.mode == "off":
            return
        self._phase += 0.12
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2 - 4
        R = min(self.width(), self.height()) / 2 - 22

        if self.mode == "on":
            base, ring, glow = QColor("#10b981"), QColor("#10b981"), QColor(16, 185, 129, 26)
        elif self.mode == "ing":
            base, ring, glow = QColor("#f5a816"), QColor("#f59e0b"), QColor(245, 158, 11, 30)
        else:
            base, ring, glow = QColor("#343452"), QColor("#4a4870"), QColor(124, 58, 237, 14)

        # glow pulsante
        pulse = 0.0 if self.mode == "off" else (math.sin(self._phase) * 0.5 + 0.5)
        for i in range(3):
            r = R + 12 + i * 9 + pulse * (5 - i)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # sombra + base
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawEllipse(int(cx - R), int(cy - R + 5), int(R * 2), int(R * 2))
        p.setBrush(base)
        p.drawEllipse(int(cx - R), int(cy - R), int(R * 2), int(R * 2))

        # anel de progresso
        pen = QPen(ring, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        span = int(self.progress * 360 * 16) if self.mode != "off" else int(360 * 16)
        if self.mode == "off":
            pen.setColor(QColor("#4a4870"))
            p.setPen(pen)
        # começa no topo (-90°)
        p.drawArc(int(cx - R - 7), int(cy - R - 7), int((R + 7) * 2), int((R + 7) * 2),
                  90 * 16, -span if self.mode != "off" else -360 * 16)

        # escudo: contorno + visto central
        white = QColor(255, 255, 255)
        m = R * 0.52
        shield = QPolygonF([
            QPointF(cx, cy - m),
            QPointF(cx + m * 0.86, cy - m * 0.45),
            QPointF(cx + m * 0.86, cy + m * 0.25),
            QPointF(cx, cy + m * 0.95),
            QPointF(cx - m * 0.86, cy + m * 0.25),
            QPointF(cx - m * 0.86, cy - m * 0.45),
        ])
        p.setPen(QPen(white, 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(shield)
        p.setPen(QPen(white, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(cx - m * 0.34), int(cy + m * 0.05),
                   int(cx - m * 0.07), int(cy + m * 0.34))
        p.drawLine(int(cx - m * 0.07), int(cy + m * 0.34),
                   int(cx + m * 0.42), int(cy - m * 0.30))

        # rótulo
        p.setPen(QColor(255, 255, 255, 200))
        f = p.font()
        f.setPointSize(11)
        f.setBold(True)
        p.setFont(f)
        label = "TOR" if self.mode == "on" else (f"{int(self.progress*100)}%" if self.mode == "ing" else "OFF")
        p.drawText(int(cx - 40), int(cy + R * 0.62), 80, 20,
                   Qt.AlignmentFlag.AlignCenter, label)
        p.end()


class KpiCard(QFrame):
    """Card clicável do dashboard (KPIs que navegam ou alternam)."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SparkWidget(QWidget):
    """Mini-gráfico de banda (↓ verde, ↑ roxo). push(down, up) em bytes/s."""

    def __init__(self, parent=None, capacity: int = 60):
        super().__init__(parent)
        from collections import deque
        self._down = deque(maxlen=capacity)
        self._up = deque(maxlen=capacity)
        self.setMinimumHeight(84)

    def push(self, down: float, up: float) -> None:
        self._down.append(max(0.0, float(down)))
        self._up.append(max(0.0, float(up)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        from PyQt6.QtGui import QColor, QPainter, QPen, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = max(1, self.width()), max(1, self.height())
        peak = max([1.0] + list(self._down) + list(self._up))
        for series, color in ((self._down, QColor("#34d399")),
                              (self._up, QColor("#a78bfa"))):
            if len(series) < 2:
                continue
            path = QPainterPath()
            n = len(series)
            for i, v in enumerate(series):
                x = i / (n - 1) * (w - 4) + 2
                y = h - 4 - (v / peak) * (h - 10)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(color, 2))
            p.drawPath(path)
        p.setPen(QColor(255, 255, 255, 90))
        f = p.font()
        f.setPointSize(9)
        p.setFont(f)
        if self._down:
            p.drawText(6, 14, f"↓ {self._fmt(self._down[-1])}   ↑ {self._fmt(self._up[-1])}")

    @staticmethod
    def _fmt(bps: float) -> str:
        for unit in ("B/s", "KB/s", "MB/s"):
            if bps < 1024 or unit == "MB/s":
                return f"{bps:.1f} {unit}" if unit != "B/s" else f"{bps:.0f} {unit}"
            bps /= 1024
        return f"{bps:.1f} GB/s"


class SideItem(QPushButton):
    """Botão da sidebar com arrastar-para-reordenar (modo organizar).

    Arrastar solta `moved(drag_pid, target_pid)`; soltar no vazio da
    seção não faz nada. Fora do modo organizar comporta-se como botão.
    """

    moved = pyqtSignal(str, str)

    MIME = "application/x-anonshield-nav"

    def __init__(self, pid: str, parent=None):
        super().__init__(parent)
        self.pid = pid
        self._draggable = False
        self._press_pos = None
        self.setAcceptDrops(True)

    def set_draggable(self, on: bool) -> None:
        self._draggable = bool(on)
        self.setCursor(Qt.CursorShape.OpenHandCursor if on
                       else Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (self._draggable and self._press_pos is not None
                and (event.buttons() & Qt.MouseButton.LeftButton)):
            if (event.position().toPoint() - self._press_pos).manhattanLength() >= 12:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData(self.MIME, self.pid.encode("utf-8"))
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                self._press_pos = None
                return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._draggable and event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if self._draggable and event.mimeData().hasFormat(self.MIME):
            src = bytes(event.mimeData().data(self.MIME)).decode("utf-8", "replace")
            if src and src != self.pid:
                self.moved.emit(src, self.pid)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class ToggleSwitch(QWidget):
    """Interruptor iOS-like com knob deslizante. API compatível p/ trocar QCheckBox."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, on_color="#10b981", off_color="#9aa0b0"):
        super().__init__(parent)
        self._on = False
        self._pos = 0.0
        self._on_color = QColor(on_color)
        self._off_color = QColor(off_color)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def isChecked(self) -> bool:  # noqa: N802
        return self._on

    def setChecked(self, v: bool) -> None:  # noqa: N802
        v = bool(v)
        if v != self._on:
            self._on = v
            if not self._timer.isActive():
                self._timer.start(16)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.setChecked(not self._on)
        self.toggled.emit(self._on)

    def _step(self) -> None:
        target = 1.0 if self._on else 0.0
        diff = target - self._pos
        if abs(diff) < 0.05:
            self._pos = target
            self._timer.stop()
        else:
            self._pos += diff * 0.25
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # interpola cor
        c0, c1 = self._off_color, self._on_color
        t = self._pos
        bg = QColor(
            int(c0.red() + (c1.red() - c0.red()) * t),
            int(c0.green() + (c1.green() - c0.green()) * t),
            int(c0.blue() + (c1.blue() - c0.blue()) * t),
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)
        r = h / 2 - 3
        x = 3 + r + (w - 6 - 2 * r) * self._pos
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(int(x - r), int(h / 2 - r), int(r * 2), int(r * 2))
        p.end()
