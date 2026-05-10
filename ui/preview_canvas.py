# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from core.engine import RenderConfig, limpar_hex

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

class PreviewCanvas(QWidget):
    positionChanged = Signal(str, str, int, int)

    def __init__(self):
        super().__init__()
        self.base_pixmap: QPixmap | None = None
        self.config: RenderConfig | None = None
        self.selected_track_title = ""
        self._handles: list[dict] = []
        self._drag_handle: dict | None = None
        self._drag_start = QPointF()
        self._drag_rect = QRectF()
        self.setMinimumSize(520, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_preview(self, pixmap: QPixmap | None, config: RenderConfig | None, selected_track_title: str = ""):
        self.base_pixmap = pixmap
        self.config = config
        self.selected_track_title = selected_track_title.strip()
        self.update()

    def paintEvent(self, event):
        self._handles = []
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#131D2B"))

        frame = self._video_rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#000000"))
        painter.drawRect(frame)

        if self.base_pixmap and not self.base_pixmap.isNull():
            scaled = self.base_pixmap.scaled(frame.size().toSize(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            source = QRectF(
                (scaled.width() - frame.width()) / 2,
                (scaled.height() - frame.height()) / 2,
                frame.width(),
                frame.height(),
            )
            painter.drawPixmap(frame, scaled, source)
        else:
            placeholder_font = QFont("Segoe UI")
            placeholder_font.setPixelSize(15)
            painter.setFont(placeholder_font)
            painter.setPen(QColor("#8FA4C4"))
            painter.drawText(frame.toRect(), Qt.AlignCenter, "Selecione um vídeo, GIF ou imagem para o preview")

        if self.config:
            self._draw_title(painter, frame)
            self._draw_intro(painter, frame)
            self._draw_watermark(painter, frame)

        painter.setPen(QColor("#26354D"))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(frame)

    def _video_rect(self) -> QRectF:
        area = self.rect().adjusted(16, 12, -16, -4)
        ratio = 16 / 9
        width = area.width()
        height = int(width / ratio)
        if height > area.height():
            height = area.height()
            width = int(height * ratio)
        x = area.x() + (area.width() - width) / 2
        y = area.y() + (area.height() - height) / 2
        return QRectF(x, y, width, height)

    def _positioned_rect(self, frame: QRectF, size: QSize, position: str, margin_x: int, margin_y: int) -> QRectF:
        w = size.width()
        h = size.height()
        if "esquerda" in position:
            x = frame.left() + margin_x
        elif "direita" in position:
            x = frame.right() - margin_x - w
        else:
            x = frame.left() + (frame.width() - w) / 2

        if "superior" in position:
            y = frame.top() + margin_y
        elif "inferior" in position:
            y = frame.bottom() - margin_y - h
        else:
            y = frame.top() + (frame.height() - h) / 2
        return QRectF(x, y, w, h)

    def _register_handle(self, kind: str, rect: QRectF, position: str):
        if rect.isValid():
            self._handles.append({"kind": kind, "rect": QRectF(rect), "position": position})

    def _position_from_rect(self, frame: QRectF, rect: QRectF) -> tuple[str, int, int]:
        cx = (rect.center().x() - frame.left()) / max(1.0, frame.width())
        cy = (rect.center().y() - frame.top()) / max(1.0, frame.height())

        if cy < 0.33:
            vertical = "superior"
        elif cy > 0.67:
            vertical = "inferior"
        else:
            vertical = "centro"

        if cx < 0.33:
            horizontal = "esquerda"
        elif cx > 0.67:
            horizontal = "direita"
        else:
            horizontal = "centro"

        if vertical == "centro":
            position = "centro"
        elif horizontal == "centro":
            position = f"{vertical}_centro"
        else:
            position = f"{vertical}_{horizontal}"

        if "esquerda" in position:
            margin_x = rect.left() - frame.left()
        elif "direita" in position:
            margin_x = frame.right() - rect.right()
        else:
            margin_x = abs(rect.center().x() - frame.center().x())

        if "superior" in position:
            margin_y = rect.top() - frame.top()
        elif "inferior" in position:
            margin_y = frame.bottom() - rect.bottom()
        else:
            margin_y = abs(rect.center().y() - frame.center().y())

        scale = max(0.35, frame.width() / 1280)
        return position, max(0, int(round(margin_x / scale))), max(0, int(round(margin_y / scale)))

    def _draw_text(self, painter: QPainter, frame: QRectF, text: str, font_family: str, font_size: int, color: str,
                   opacity: float, position: str, margin_x: int, margin_y: int, weight: int = 700,
                   shadow_opacity: float = 0.55, shadow_color: str = "#000000",
                   shadow_size: float = 2.0, box: bool = False, box_color: str = "#000000",
                   box_opacity: float = 0.35, background_padding: float = 6.0):
        if not text:
            return QRectF()
        scale = max(0.35, frame.width() / 1280)
        font = QFont(font_family or "Segoe UI")
        font.setPixelSize(max(11, int(font_size * scale)))
        font.setWeight(QFont.Weight(max(100, min(900, int(weight)))))
        painter.setFont(font)
        metrics = QFontMetrics(font)
        bounds = QRectF(metrics.tightBoundingRect(text))
        rect = self._positioned_rect(frame, bounds.size(), position, int(margin_x * scale), int(margin_y * scale))
        text_origin = QPointF(rect.left() - bounds.left(), rect.top() - bounds.top())

        if box:
            painter.setPen(Qt.NoPen)
            background = QColor(limpar_hex(box_color, "#000000"))
            background.setAlphaF(max(0, min(1, box_opacity)))
            painter.setBrush(background)
            padding = max(0.0, float(background_padding))
            painter.drawRoundedRect(rect.adjusted(-padding, -(max(0.0, padding - 2)), padding, padding), 2, 2)

        shadow = QColor(limpar_hex(shadow_color, "#000000"))
        shadow.setAlphaF(max(0, min(1, shadow_opacity)))
        painter.setPen(shadow)
        shadow_offset = max(0.0, float(shadow_size))
        painter.drawText(text_origin + QPointF(shadow_offset, shadow_offset), text)

        main_color = QColor(limpar_hex(color))
        main_color.setAlphaF(max(0, min(1, opacity)))
        painter.setPen(main_color)
        painter.drawText(text_origin, text)
        return rect.adjusted(-4, -4, 4, 4)

    def _draw_title(self, painter: QPainter, frame: QRectF):
        cfg = self.config.fonte_texto
        sample_title = self.selected_track_title or next((title for title in self.config.track_titles.values() if str(title).strip()), "Nome da faixa")
        rect = self._draw_text(
            painter,
            frame,
            sample_title,
            cfg.font_family,
            cfg.font_size,
            cfg.color,
            cfg.opacity,
            cfg.position,
            cfg.margin_left,
            cfg.margin_bottom,
            700,
            cfg.shadow_opacity if cfg.shadow_enabled else 0.0,
            cfg.shadow_color,
            cfg.shadow_size,
            cfg.background_box,
            cfg.background_color,
            cfg.background_opacity,
            cfg.background_padding,
        )
        self._register_handle("title", rect, cfg.position)

    def _draw_intro(self, painter: QPainter, frame: QRectF):
        intro = self.config.intro
        if not intro.enabled:
            return
        text = intro.phrases[0].texto if intro.phrases else "Frase de intro"
        rect = self._draw_text(
            painter,
            frame,
            text,
            intro.font_family,
            intro.font_size,
            intro.color,
            intro.opacity,
            intro.position,
            intro.margin_x,
            intro.margin_y,
            intro.font_weight,
            intro.shadow_opacity if intro.shadow_enabled else 0.0,
            intro.shadow_color,
            intro.shadow_size,
            intro.background_box,
            intro.background_color,
            intro.box_opacity,
            intro.background_padding,
        )
        self._register_handle("intro", rect, intro.position)

    def _draw_watermark(self, painter: QPainter, frame: QRectF):
        wm = self.config.watermark
        if not wm.enabled:
            return
        if wm.mode == "imagem" and wm.image_path and Path(wm.image_path).exists():
            pixmap = QPixmap(wm.image_path)
            if pixmap.isNull():
                return
            scale = max(0.35, frame.width() / 1280)
            width = max(24, int(wm.image_width * scale))
            scaled = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
            rect = self._positioned_rect(frame, scaled.size(), wm.position, int(wm.margin_x * scale), int(wm.margin_y * scale))
            painter.setOpacity(max(0, min(1, wm.opacity)))
            painter.drawPixmap(rect.toRect(), scaled)
            painter.setOpacity(1.0)
            self._register_handle("watermark", rect, wm.position)
        else:
            rect = self._draw_text(
                painter,
                frame,
                wm.text or "Marca",
                wm.font_family,
                wm.font_size,
                wm.color,
                wm.opacity,
                wm.position,
                wm.margin_x,
                wm.margin_y,
                700,
                wm.shadow_opacity if wm.shadow_enabled else 0.0,
                wm.shadow_color,
                wm.shadow_size,
                wm.background_box,
                wm.background_color,
                wm.background_opacity,
                wm.background_padding,
            )
            self._register_handle("watermark", rect, wm.position)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        point = QPointF(event.position()) if hasattr(event, "position") else QPointF(event.pos())
        for handle in reversed(self._handles):
            if handle["rect"].contains(point):
                self._drag_handle = handle
                self._drag_start = point
                self._drag_rect = QRectF(handle["rect"])
                self.setCursor(QCursor(Qt.ClosedHandCursor))
                event.accept()
                return
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._drag_handle:
            return super().mouseMoveEvent(event)
        point = QPointF(event.position()) if hasattr(event, "position") else QPointF(event.pos())
        delta = point - self._drag_start
        frame = self._video_rect()
        rect = QRectF(self._drag_rect)
        rect.translate(delta)
        rect.moveLeft(max(frame.left(), min(rect.left(), frame.right() - rect.width())))
        rect.moveTop(max(frame.top(), min(rect.top(), frame.bottom() - rect.height())))
        position, margin_x, margin_y = self._position_from_rect(frame, rect)
        self.positionChanged.emit(self._drag_handle["kind"], position, margin_x, margin_y)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_handle:
            self._drag_handle = None
            self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept()
            return
        return super().mouseReleaseEvent(event)
