# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

from core.engine import SCRIPT_DIR, limpar_hex, popular_combo_posicoes

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

CONTROL_HEIGHT = 34
RIGHT_FORM_WIDTH = 430
PREVIEW_HEIGHT_NORMAL = 380
PREVIEW_HEIGHT_LOG_OPEN = 270
PREVIEW_ASPECT_RATIO = 16 / 9
LOG_HEIGHT_OPEN = 260
BASE_WINDOW_WIDTH = 1520
BASE_WINDOW_HEIGHT = 820
BASE_WINDOW_MIN_WIDTH = 1420
BASE_WINDOW_MIN_HEIGHT = 740
UI_ZOOM_MIN = 0.5
UI_ZOOM_MAX = 2.0


STYLE_PRIME = """
* {
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 12px;
    color: #EAF2FF;
}
QWidget {
    background: #0B111C;
}
QFrame#LeftPanel, QFrame#RightPanel {
    background: #101826;
    border: 1px solid #233047;
    border-radius: 14px;
}
QFrame#CenterPanel {
    background: #0B111C;
}
QFrame#Section, QFrame#Transport, QFrame#PreviewShell {
    background: #131D2B;
    border: 1px solid #26354D;
    border-radius: 18px;
}
QLabel#Brand {
    color: #F6FAFF;
    font-size: 20px;
    font-weight: 800;
}
QLabel#Subtle {
    color: #8FA4C4;
}
QLabel#SectionTitle {
    color: #DCEBFF;
    font-size: 13px;
    font-weight: 700;
}
QLabel#ColumnTitle {
    color: #F6FAFF;
    font-size: 16px;
    font-weight: 800;
}
QLabel#ImagePreview {
    background: #0D1420;
    border: 1px solid #31415C;
    border-radius: 12px;
    color: #8FA4C4;
}
QWidget#PreviewGroup {
    background: transparent;
}
QWidget#PreviewVolumeBar {
    background: transparent;
}
QLabel {
    background: transparent;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #0D1420;
    border: 1px solid #31415C;
    border-radius: 17px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px 12px;
    selection-background-color: #2F86FF;
}
QTextEdit {
    background: #0D1420;
    border: 1px solid #31415C;
    border-radius: 14px;
    padding: 10px 12px;
    selection-background-color: #2F86FF;
}
QLineEdit {
    border-radius: 17px;
}
QSpinBox, QDoubleSpinBox {
    border-radius: 17px;
    padding-left: 12px;
    padding-right: 12px;
}
QComboBox {
    border-radius: 17px;
    padding-left: 12px;
    padding-right: 36px;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background: #0D1420;
    border: 1px solid #26354D;
    border-radius: 17px;
    color: #7C8DA8;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #5EA0FF;
    background: #111B2B;
}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    border: none;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    background: transparent;
    border: none;
    border-top-right-radius: 17px;
    border-bottom-right-radius: 17px;
}
QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6FB1FF;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #101826;
    border: 1px solid #31415C;
    border-radius: 10px;
    selection-background-color: #2F86FF;
    outline: none;
}
QTabWidget {
    background: #101826;
}
QTabWidget::pane {
    border: 1px solid #26354D;
    border-radius: 0px;
    background: #101826;
    top: -1px;
}
QTabBar::tab {
    background: #0A101A;
    color: #8FA4C4;
    border: 1px solid #26354D;
    border-bottom: 1px solid #26354D;
    padding: 8px 8px;
    min-width: 55px;
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
}
QTabBar::tab:selected {
    background: #101826;
    color: #FFFFFF;
    border-color: #26354D;
    border-bottom-color: #101826;
}
QTabBar::tab:!selected {
    background: #0B111C;
    color: #8FA4C4;
}
QProgressBar {
    background: #0D1420;
    border: 1px solid #31415C;
    border-radius: 7px;
    min-height: 10px;
    max-height: 14px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2F86FF;
    border-radius: 6px;
}
QSlider {
    background: transparent;
    min-height: 24px;
    max-height: 24px;
}
QSlider::groove:horizontal {
    background: #131D2B;
    border: 1px solid #26354D;
    height: 6px;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #2F86FF;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4B9AFF;
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #6FB1FF;
}
QTableWidget {
    background: #0D1420;
    border: 1px solid #31415C;
    border-radius: 0px;
    gridline-color: #26354D;
    outline: none;
}
QTableWidget::item {
    padding: 3px 5px;
}
QTableCornerButton::section {
    background: #17263C;
    border: none;
    border-right: 1px solid #31415C;
    border-bottom: 1px solid #31415C;
}
QHeaderView::section {
    background: #17263C;
    border: none;
    border-bottom: 1px solid #31415C;
    padding: 5px;
    color: #CFE2FF;
    font-weight: 700;
}
QScrollBar:vertical {
    background: #0D1420;
    border-left: 1px solid #26354D;
    width: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #26354D;
    border-radius: 5px;
    min-height: 24px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #31415C;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
    height: 0px;
}
QScrollBar:horizontal {
    background: #0D1420;
    border-top: 1px solid #26354D;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #26354D;
    border-radius: 5px;
    min-width: 24px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #31415C;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
    border: none;
    width: 0px;
}
"""


def clamp_zoom(value: float) -> float:
    return max(UI_ZOOM_MIN, min(UI_ZOOM_MAX, float(value)))


def escala(valor: int | float, zoom: float, minimo: int = 1) -> int:
    return max(minimo, int(round(float(valor) * zoom)))


def zoom_stylesheet(zoom: float) -> str:
    control_height = escala(CONTROL_HEIGHT, zoom, 18)
    radius = max(4, control_height // 2)
    tab_padding_y = escala(8, zoom, 3)
    tab_padding_x = escala(8, zoom, 4)
    slider_height = escala(24, zoom, 14)
    slider_handle = escala(14, zoom, 8)
    slider_groove = escala(6, zoom, 3)
    return f"""
* {{
    font-size: {escala(12, zoom, 8)}px;
}}
QLabel#Brand {{
    font-size: {escala(20, zoom, 12)}px;
}}
QLabel#SectionTitle {{
    font-size: {escala(13, zoom, 8)}px;
}}
QLabel#ColumnTitle {{
    font-size: {escala(16, zoom, 10)}px;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    min-height: {control_height - 2}px;
    max-height: {control_height - 2}px;
    border-radius: {radius}px;
    padding-left: {escala(12, zoom, 5)}px;
    padding-right: {escala(12, zoom, 5)}px;
}}
QComboBox {{
    padding-right: {escala(36, zoom, 16)}px;
}}
QComboBox::drop-down {{
    width: {escala(32, zoom, 14)}px;
    border-top-right-radius: {radius}px;
    border-bottom-right-radius: {radius}px;
}}
QTabBar::tab {{
    padding: {tab_padding_y}px {tab_padding_x}px;
    min-width: {escala(55, zoom, 28)}px;
    border-top-left-radius: {escala(11, zoom, 5)}px;
    border-top-right-radius: {escala(11, zoom, 5)}px;
}}
QTextEdit {{
    border-radius: {escala(14, zoom, 6)}px;
    padding: {escala(10, zoom, 4)}px {escala(12, zoom, 5)}px;
}}
QSlider {{
    min-height: {slider_height}px;
    max-height: {slider_height}px;
}}
QSlider::groove:horizontal {{
    height: {slider_groove}px;
    border-radius: {max(2, slider_groove // 2)}px;
}}
QSlider::handle:horizontal {{
    width: {slider_handle}px;
    height: {slider_handle}px;
    margin: -{max(1, (slider_handle - slider_groove) // 2)}px 0;
    border-radius: {max(4, slider_handle // 2)}px;
}}
"""


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
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumWidth(width)
        self.setFixedHeight(CONTROL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFlat(True)
        self.refresh_style()

    def refresh_style(self):
        palette = {
            "normal": ("#18263A", "#213753", "#7EAFFF", "#31415C"),
            "primary": ("#2F86FF", "#4B9AFF", "#FFFFFF", "#1F6FD9"),
            "danger": ("#8A3A4A", "#A94C5F", "#FFFFFF", "#703040"),
            "ghost": ("#111B2B", "#18263A", "#CFE2FF", "#31415C"),
        }
        self._colors = palette.get(self.kind, palette["normal"])
        self.setStyleSheet("")
        self.update()

    def paintEvent(self, event):
        bg, hover, text, border = self._colors
        if not self.isEnabled():
            bg, text, border = "#101826", "#5F6E84", "#243148"
        elif self.isDown():
            bg = border
        elif self.underMouse():
            bg = hover

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        radius = rect.height() / 2
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, radius, radius)

        font = self.font()
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(text))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())


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
        painter.setBrush(QColor("#2F86FF") if self.isChecked() else QColor("#3A4658"))
        painter.drawRoundedRect(track, track_h / 2, track_h / 2)

        knob_x = inset + self._offset * (track_w - knob_d - (2 * inset))
        knob_y = track_y + inset
        painter.setBrush(QColor("#EAF2FF"))
        painter.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

        if self.text():
            painter.setPen(QColor("#DCEBFF"))
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
        painter.setPen(QPen(QColor("#31415C"), 1.5))
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


def combo_posicao(default: str) -> QComboBox:
    combo = QComboBox()
    popular_combo_posicoes(combo, default)
    set_input_width(combo)
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
        if isinstance(child, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, ActionButton)):
            child.setFixedHeight(height)
