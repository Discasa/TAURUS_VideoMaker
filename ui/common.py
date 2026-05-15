# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

from core.engine import SCRIPT_DIR, limpar_hex

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .style_tokens import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_MIN_HEIGHT,
    BASE_WINDOW_MIN_WIDTH,
    BASE_WINDOW_WIDTH,
    COLORS,
    CONTROL_HEIGHT,
    LOG_HEIGHT_OPEN,
    PREVIEW_ASPECT_RATIO,
    PREVIEW_HEIGHT_LOG_OPEN,
    PREVIEW_HEIGHT_NORMAL,
    RIGHT_FORM_WIDTH,
    STYLE_PRIME,
    UI_ZOOM_MAX,
    UI_ZOOM_MIN,
    action_button_stylesheet,
    clamp_zoom,
    escala,
    zoom_stylesheet,
)


def section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Section")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 12)
    layout.setSpacing(8)
    label = QLabel(title)
    label.setObjectName("SectionTitle")
    layout.addWidget(label)
    return frame, layout


def setup_form(form: QGridLayout):
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)
    form.setColumnMinimumWidth(0, 104)
    form.setColumnStretch(1, 1)


def add_row(form: QGridLayout, row: int, label: str, widget: QWidget):
    lbl = QLabel(label)
    lbl.setObjectName("Subtle")
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.addWidget(lbl, row, 0)
    form.addWidget(widget, row, 1)
    return lbl


def add_wide(form: QGridLayout, row: int, widget: QWidget):
    form.addWidget(widget, row, 0, 1, 2)


def centered_widget(widget: QWidget, max_width: int = 360) -> QWidget:
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch(1)
    widget.setMaximumWidth(max_width)
    layout.addWidget(widget)
    layout.addStretch(1)
    return wrapper


def centered_layout(inner_layout, max_width: int = RIGHT_FORM_WIDTH) -> QWidget:
    box = QWidget()
    box.setMaximumWidth(max_width)
    box.setLayout(inner_layout)
    return centered_widget(box, max_width)


def set_input_width(widget: QWidget):
    widget.setFixedHeight(CONTROL_HEIGHT)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    if isinstance(widget, QComboBox):
        widget.setMaxVisibleItems(12)
        widget.setMinimumContentsLength(16)
        widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        widget.view().setTextElideMode(Qt.ElideRight)


class ActionButton(QPushButton):
    def __init__(self, text: str, kind: str = "normal", width: int = 112):
        super().__init__(text)
        self.kind = kind
        self.base_width = width
        self._zoom = 1.0
        self.setObjectName("ActionButton")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumWidth(width)
        self.setFixedHeight(CONTROL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_style()

    def set_zoom(self, zoom: float):
        self._zoom = clamp_zoom(zoom)
        self.setFixedHeight(escala(CONTROL_HEIGHT, self._zoom, 18))
        self.refresh_style()

    def refresh_style(self):
        self.setStyleSheet(action_button_stylesheet(self.kind, self._zoom))


class ToggleSwitch(QCheckBox):
    TRACK_W = 40
    TRACK_H = 20
    KNOB_D = 16

    def __init__(self, text: str = ""):
        super().__init__(text)
        self._offset = 1.0 if self.isChecked() else 0.0
        self._zoom = 1.0
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self.stateChanged.connect(self._animate)

    def set_zoom(self, zoom: float):
        self._zoom = clamp_zoom(zoom)
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        label_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        track_w = escala(self.TRACK_W, self._zoom, 20)
        return QSize(track_w + (escala(10, self._zoom, 4) + label_w if label_w else 0), escala(26, self._zoom, 16))

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def _animate(self):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_w = escala(self.TRACK_W, self._zoom, 20)
        track_h = escala(self.TRACK_H, self._zoom, 10)
        knob_d = escala(self.KNOB_D, self._zoom, 8)
        inset = max(1, escala(2, self._zoom, 1))
        track_y = (self.height() - track_h) / 2
        track = QRectF(0, track_y, track_w, track_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLORS.accent if self.isChecked() else COLORS.switch_off))
        painter.drawRoundedRect(track, track_h / 2, track_h / 2)

        knob_x = inset + self._offset * (track_w - knob_d - (2 * inset))
        knob_y = track_y + inset
        painter.setBrush(QColor(COLORS.text_main))
        painter.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

        if self.text():
            painter.setPen(QColor(COLORS.text_section))
            painter.drawText(
                self.rect().adjusted(track_w + escala(10, self._zoom, 4), 0, 0, 0),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.text(),
            )


class ColorSwatch(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, value: str = "#FFFFFF"):
        super().__init__("")
        self._color = ""
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(24, 24)
        self.setToolTip("Escolher cor")
        self.setFlat(True)
        self.clicked.connect(self.choose)
        self.setText(value)

    def set_zoom(self, zoom: float):
        size = escala(24, zoom, 14)
        self.setFixedSize(size, size)
        self.update()

    def text(self) -> str:
        return self._color

    def setText(self, value: str):
        color = limpar_hex(value, self._color)
        if color == self._color:
            return
        self._color = color
        self.update()
        self.colorChanged.emit(color)

    def choose(self):
        color = QColorDialog.getColor(QColor(limpar_hex(self._color)), self)
        if color.isValid():
            self.setText(color.name().upper())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        painter.setPen(QPen(QColor(COLORS.border_control), 1.5))
        painter.setBrush(QColor(limpar_hex(self._color)))
        painter.drawEllipse(rect)


class DecimalSlider(QWidget):
    def __init__(self, minimum: float, maximum: float, step: float, value: float, decimals: int = 2, suffix: str = ""):
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.decimals = decimals
        self.suffix = suffix
        self.scale = int(round(1 / step))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self._to_slider(minimum), self._to_slider(maximum))
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.slider.setFixedHeight(CONTROL_HEIGHT)
        self.label = QLabel()
        self.label.setObjectName("Subtle")
        self.label.setFixedWidth(44)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.label)

        self.slider.valueChanged.connect(self._refresh_label)
        self.setValue(value)

    def set_zoom(self, zoom: float):
        self.slider.setFixedHeight(escala(CONTROL_HEIGHT, zoom, 18))
        self.label.setFixedWidth(escala(44, zoom, 28))

    def _to_slider(self, value: float) -> int:
        return int(round(float(value) * self.scale))

    def _from_slider(self, value: int) -> float:
        return max(self.minimum, min(self.maximum, float(value) / self.scale))

    def _refresh_label(self):
        if self.decimals == 0:
            texto = str(int(round(self.value())))
        else:
            texto = f"{self.value():.{self.decimals}f}"
        self.label.setText(f"{texto}{self.suffix}")

    def value(self) -> float:
        return self._from_slider(self.slider.value())

    def setValue(self, value: float):
        self.slider.setValue(self._to_slider(value))
        self._refresh_label()


class PathPicker(QWidget):
    def __init__(self, mode: str, filter_text: str = "Todos (*.*)", placeholder: str = ""):
        super().__init__()
        self.mode = mode
        self.filter_text = filter_text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.line = QLineEdit()
        self.line.setFixedHeight(CONTROL_HEIGHT)
        self.line.setPlaceholderText(placeholder)
        self.button = ActionButton("Escolher", "ghost")
        self.button.base_width = 86
        self.button.setFixedWidth(86)
        self.button.clicked.connect(self.choose)
        layout.addWidget(self.line, 1)
        layout.addWidget(self.button)

    def choose(self):
        if self.mode == "folder":
            path = QFileDialog.getExistingDirectory(self, "Escolher pasta", str(SCRIPT_DIR))
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Escolher arquivo", str(SCRIPT_DIR), self.filter_text)
        if path:
            self.line.setText(path)

    def path(self) -> Path | None:
        text = self.line.text().strip()
        return Path(text) if text else None

    def set_path(self, path):
        self.line.setText(str(path) if path else "")


_FONTES_REGISTRADAS = False


def registrar_fontes():
    global _FONTES_REGISTRADAS
    if _FONTES_REGISTRADAS:
        return
    if QFontDatabase.families():
        _FONTES_REGISTRADAS = True
        return
    pasta = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" if os.name == "nt" else Path("/usr/share/fonts")
    if pasta.exists():
        for padrao in ("*.ttf", "*.otf"):
            for fonte in pasta.rglob(padrao):
                QFontDatabase.addApplicationFont(str(fonte))
    _FONTES_REGISTRADAS = True


def combo_fontes(default_family: str = "Georgia") -> QComboBox:
    registrar_fontes()
    combo = QComboBox()
    set_input_width(combo)
    fonts = sorted(set(QFontDatabase.families()), key=str.casefold) or ["Georgia", "Segoe UI", "Arial"]
    combo.addItems(fonts)
    index = combo.findText(default_family)
    if index < 0:
        index = combo.findText("Segoe UI")
    combo.setCurrentIndex(max(0, index))
    return combo


def margins_widget(x_spin: QSpinBox, y_spin: QSpinBox) -> QWidget:
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    for spin in (x_spin, y_spin):
        spin.base_min_width = 80
        spin.base_max_width = 90
        spin.setMinimumWidth(80)
        spin.setMaximumWidth(90)
    layout.addWidget(QLabel("X"))
    layout.addWidget(x_spin)
    layout.addWidget(QLabel("Y"))
    layout.addWidget(y_spin)
    layout.addStretch(1)
    return box


def remove_spin_buttons(root: QWidget):
    for spin in root.findChildren(QAbstractSpinBox):
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spin.setAlignment(Qt.AlignLeft)
        spin.setFixedHeight(CONTROL_HEIGHT)


def padronizar_altura_controles(root: QWidget, zoom: float = 1.0):
    height = escala(CONTROL_HEIGHT, zoom, 18)
    for child in root.findChildren(QWidget):
        if isinstance(child, ActionButton):
            child.set_zoom(zoom)
        elif isinstance(child, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox)):
            child.setFixedHeight(height)
