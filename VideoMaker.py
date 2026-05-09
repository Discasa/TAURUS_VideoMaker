# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Interface PySide6 do TAURUS Video Maker.

A lógica de renderização, FFmpeg e persistência ficam em engine.py.
"""

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from engine import (
    APP_VERSION,
    EXTENSOES_AUDIO,
    EXTENSOES_IMAGEM,
    EXTENSOES_VIDEO,
    FFMPEG,
    SCRIPT_DIR,
    ErroRender,
    FonteTextoConfig,
    IntroFraseConfig,
    IntroTextConfig,
    NormalizacaoConfig,
    RenderConfig,
    WatermarkConfig,
    WorkerRender,
    caminho_ou_vazio,
    carregar_json_config,
    criar_kwargs_subprocess_controlado,
    gerar_pasta_saida_padrao,
    intro_config_from_dict,
    intro_config_to_dict,
    limpar_hex,
    limpar_titulo_musica,
    natural_key,
    popular_combo_posicoes,
    salvar_json_config,
)

CONTROL_HEIGHT = 34

try:
    from PySide6.QtCore import Property, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QUrl
    from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QPixmap, QTextCursor
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractSpinBox,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("PySide6 não está instalado. Instale com: pip install PySide6")
    sys.exit(1)


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
    border-radius: 10px;
    min-height: 16px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2F86FF;
    border-radius: 9px;
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
    form.setHorizontalSpacing(10)
    form.setVerticalSpacing(8)
    form.setColumnMinimumWidth(0, 112)
    form.setColumnStretch(1, 1)


def add_row(form: QGridLayout, row: int, label: str, widget: QWidget):
    lbl = QLabel(label)
    lbl.setObjectName("Subtle")
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
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


def centered_layout(inner_layout, max_width: int = 360) -> QWidget:
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
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self.stateChanged.connect(self._animate)

    def sizeHint(self):
        label_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self.TRACK_W + (10 + label_w if label_w else 0), 26)

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
        track_y = (self.height() - self.TRACK_H) / 2
        track = QRectF(0, track_y, self.TRACK_W, self.TRACK_H)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2F86FF") if self.isChecked() else QColor("#3A4658"))
        painter.drawRoundedRect(track, self.TRACK_H / 2, self.TRACK_H / 2)

        knob_x = 2 + self._offset * (self.TRACK_W - self.KNOB_D - 4)
        knob_y = track_y + 2
        painter.setBrush(QColor("#EAF2FF"))
        painter.drawEllipse(QRectF(knob_x, knob_y, self.KNOB_D, self.KNOB_D))

        if self.text():
            painter.setPen(QColor("#DCEBFF"))
            painter.drawText(
                self.rect().adjusted(self.TRACK_W + 10, 0, 0, 0),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.text(),
            )


class ColorEdit(QLineEdit):
    def __init__(self, value: str = "#FFFFFF"):
        super().__init__(value)
        self.textChanged.connect(self.refresh_color)
        self.refresh_color()

    def refresh_color(self):
        color = limpar_hex(self.text())
        if not QColor(color).isValid():
            color = "#DCEBFF"
        self.setStyleSheet(f"""
            QLineEdit {{
                background: #0D1420;
                border: 1px solid #31415C;
                border-radius: 17px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px 12px;
                color: {color};
                font-weight: 800;
            }}
            QLineEdit:focus {{
                border: 1px solid #5EA0FF;
                background: #111B2B;
            }}
            QLineEdit:disabled {{
                background: #0D1420;
                border: 1px solid #26354D;
                border-radius: 17px;
                color: #7C8DA8;
            }}
        """)


class DecimalSlider(QWidget):
    def __init__(self, minimum: float, maximum: float, step: float, value: float, decimals: int = 2):
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.decimals = decimals
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

    def _to_slider(self, value: float) -> int:
        return int(round(float(value) * self.scale))

    def _from_slider(self, value: int) -> float:
        return max(self.minimum, min(self.maximum, float(value) / self.scale))

    def _refresh_label(self):
        self.label.setText(f"{self.value():.{self.decimals}f}")

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


def padronizar_altura_controles(root: QWidget):
    for child in root.findChildren(QWidget):
        if isinstance(child, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, ActionButton)):
            child.setFixedHeight(CONTROL_HEIGHT)


class PreviewCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.base_pixmap: QPixmap | None = None
        self.config: RenderConfig | None = None
        self.setMinimumSize(520, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_preview(self, pixmap: QPixmap | None, config: RenderConfig | None):
        self.base_pixmap = pixmap
        self.config = config
        self.update()

    def paintEvent(self, event):
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
        y = area.y() + area.height() - height
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

    def _draw_text(self, painter: QPainter, frame: QRectF, text: str, font_family: str, font_size: int, color: str,
                   opacity: float, position: str, margin_x: int, margin_y: int, weight: int = 700,
                   shadow_opacity: float = 0.55, shadow_color: str = "#000000",
                   box: bool = False, box_opacity: float = 0.35):
        if not text:
            return
        scale = max(0.35, frame.width() / 1280)
        font = QFont(font_family or "Segoe UI")
        font.setPixelSize(max(11, int(font_size * scale)))
        font.setWeight(QFont.Weight(max(100, min(900, int(weight)))))
        painter.setFont(font)
        metrics = QFontMetrics(font)
        bounds = metrics.boundingRect(text).adjusted(-10, -7, 10, 7)
        rect = self._positioned_rect(frame, bounds.size(), position, int(margin_x * scale), int(margin_y * scale))

        if box:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, int(255 * max(0, min(1, box_opacity)))))
            painter.drawRoundedRect(rect.adjusted(-8, -5, 8, 5), 7, 7)

        shadow = QColor(limpar_hex(shadow_color, "#000000"))
        shadow.setAlphaF(max(0, min(1, shadow_opacity)))
        painter.setPen(shadow)
        painter.drawText(rect.adjusted(2, 2, 2, 2), Qt.AlignCenter, text)

        main_color = QColor(limpar_hex(color))
        main_color.setAlphaF(max(0, min(1, opacity)))
        painter.setPen(main_color)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _draw_title(self, painter: QPainter, frame: QRectF):
        cfg = self.config.fonte_texto
        sample_title = next((title for title in self.config.track_titles.values() if str(title).strip()), "Nome da faixa")
        self._draw_text(
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
            cfg.shadow_opacity,
            cfg.shadow_color,
        )

    def _draw_intro(self, painter: QPainter, frame: QRectF):
        intro = self.config.intro
        if not intro.enabled:
            return
        text = intro.phrases[0].texto if intro.phrases else "Frase de intro"
        self._draw_text(
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
            intro.shadow_opacity,
            intro.shadow_color,
            intro.background_box,
            intro.box_opacity,
        )

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
        else:
            self._draw_text(
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
                wm.shadow_opacity,
                wm.shadow_color,
            )


class MainUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TAURUS Video Maker {APP_VERSION}")
        self.resize(1520, 820)
        self.setMinimumSize(1420, 740)
        self.setStyleSheet(STYLE_PRIME)

        self.worker = None
        self.render_mode = ""
        self.ultimo_video: Path | None = None
        self.preview_source: Path | None = None
        self.preview_pixmap: QPixmap | None = None
        self._config_loading = False

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(900)
        self.autosave_timer.timeout.connect(self.save_config)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self.update_preview)

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.left_panel = self.build_left_panel()
        self.center_panel = self.build_center_panel()
        self.right_panel = self.build_right_panel()

        root.addWidget(self.left_panel)
        root.addWidget(self.center_panel, 2)
        root.addWidget(self.right_panel)

        self.apply_intro_config(IntroTextConfig())
        self.load_config()
        self.connect_auto_signals()
        self.music_picker.line.textChanged.connect(lambda *_: self.refresh_track_titles_table())
        self.bg_picker.line.textChanged.connect(lambda *_: self.refresh_track_titles_table())
        remove_spin_buttons(self)
        padronizar_altura_controles(self)
        self.update_preview()

    # ---------- Construção visual ----------

    def build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("LeftPanel")
        panel.setFixedWidth(285)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        brand = QLabel("TAURUS Video Maker")
        brand.setObjectName("Brand")
        subtitle = QLabel("Fluxo do projeto")
        subtitle.setObjectName("Subtle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)

        media, media_layout = section("Arquivos de entrada")
        self.video_picker = PathPicker("file", "Mídia visual (*.mp4 *.mov *.mkv *.avi *.webm *.gif *.png *.jpg *.jpeg *.webp);;Todos (*.*)", "Vídeo, GIF ou imagem base")
        self.music_picker = PathPicker("folder", placeholder="Pasta com músicas")
        media_layout.addWidget(QLabel("Visual base"))
        media_layout.addWidget(self.video_picker)
        media_layout.addWidget(QLabel("Músicas"))
        media_layout.addWidget(self.music_picker)
        layout.addWidget(media)

        output, output_layout = section("Saída")
        self.out_picker = PathPicker("folder", placeholder="Automática: render_DATA_HORA")
        self.btn_open_output = ActionButton("Abrir pasta", "ghost")
        self.btn_open_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_open_output.clicked.connect(self.abrir_pasta_saida)
        output_layout.addWidget(self.out_picker)
        output_layout.addWidget(self.btn_open_output)
        layout.addWidget(output)

        render, render_layout = section("Renderização")
        self.set_gpu = ToggleSwitch("Usar GPU NVIDIA/NVENC")
        self.set_gpu.setChecked(True)
        render_note = QLabel("Se desabilitado, renderiza com CPU.\nFFmpeg local incluído no projeto.")
        render_note.setObjectName("Subtle")
        render_note.setWordWrap(True)
        render_note.setMinimumHeight(34)
        render_layout.addWidget(self.set_gpu)
        render_layout.addWidget(render_note)
        layout.addWidget(render)
        layout.addStretch(1)
        return panel

    def build_center_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("CenterPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        preview_shell = QFrame()
        preview_shell.setObjectName("PreviewShell")
        preview_layout = QVBoxLayout(preview_shell)
        preview_layout.setContentsMargins(12, 10, 12, 12)
        preview_layout.setSpacing(4)
        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("ColumnTitle")
        self.preview_status = QLabel("Primeiro frame + sobreposições")
        self.preview_status.setObjectName("Subtle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.preview_status)
        preview_layout.addLayout(header)
        self.preview = PreviewCanvas()
        self.video_player = QMediaPlayer(self)
        self.preview_audio = QAudioOutput(self)
        self.preview_audio.setVolume(0.50)
        self.video_player.setAudioOutput(self.preview_audio)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background: #000000; border: none;")
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.mediaStatusChanged.connect(self.loop_preview_video)
        self.video_widget.hide()
        preview_layout.addWidget(self.preview, 1)
        preview_layout.addWidget(self.video_widget, 1)
        volume_row = QHBoxLayout()
        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.addStretch(1)
        self.preview_volume_label = QLabel("50%")
        self.preview_volume_label.setObjectName("Subtle")
        self.preview_volume_slider = QSlider(Qt.Horizontal)
        self.preview_volume_slider.setRange(0, 20)
        self.preview_volume_slider.setValue(10)
        self.preview_volume_slider.setFixedWidth(150)
        self.preview_volume_slider.valueChanged.connect(self.set_preview_volume)
        volume_row.addWidget(QLabel("Volume"))
        volume_row.addWidget(self.preview_volume_slider)
        volume_row.addWidget(self.preview_volume_label)
        preview_layout.addLayout(volume_row)
        layout.addWidget(preview_shell, 1)

        transport = QFrame()
        transport.setObjectName("Transport")
        transport_layout = QVBoxLayout(transport)
        transport_layout.setContentsMargins(12, 10, 12, 12)
        transport_layout.setSpacing(8)

        self.lbl_status = QLabel("")
        self.lbl_status.hide()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        transport_layout.addWidget(self.prog_bar)

        buttons = QHBoxLayout()
        self.btn_log = ActionButton("Mostrar log", "ghost")
        self.btn_log.clicked.connect(self.toggle_log)
        self.btn_clear_log = ActionButton("Limpar log", "ghost")
        self.btn_clear_log.clicked.connect(lambda: self.log_widget.clear())
        self.btn_test = ActionButton("Render", "normal")
        self.btn_test.clicked.connect(self.render_preview_toggle)
        self.btn_start = ActionButton("Iniciar", "primary")
        self.btn_start.clicked.connect(self.iniciar_ou_pausar)
        self.btn_cancel = ActionButton("Cancelar", "danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancelar_render)
        buttons.addWidget(self.btn_log)
        buttons.addWidget(self.btn_clear_log)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_test)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_start)
        transport_layout.addLayout(buttons)

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFixedHeight(300)
        self.log_widget.hide()
        transport_layout.addWidget(self.log_widget)
        layout.addWidget(transport)
        return panel

    def build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("RightPanel")
        panel.setFixedWidth(500)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)
        title = QLabel("Ajustes")
        title.setObjectName("ColumnTitle")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_titles_tab(), "Títulos")
        self.tabs.addTab(self.build_intro_tab(), "Intro")
        self.tabs.addTab(self.build_watermark_tab(), "Marca")
        self.tabs.addTab(self.build_audio_tab(), "Áudio")
        self.tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(self.tabs, 1)
        return panel

    def build_titles_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.title_tabs = QTabWidget()
        self.title_tabs.addTab(self.build_title_font_tab(), "Fonte")
        self.title_tabs.addTab(self.build_title_tracks_tab(), "Músicas")
        self.title_tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(self.title_tabs)
        return tab

    def build_title_font_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        form = QGridLayout()
        setup_form(form)

        self.font_titles = combo_fontes("Georgia")
        self.font_titles_size = QSpinBox(); self.font_titles_size.setRange(8, 160); self.font_titles_size.setValue(34)
        self.font_titles_color = ColorEdit("#FFFFFF")
        self.font_titles_pos = combo_posicao("inferior_esquerda")
        self.font_titles_mx = QSpinBox(); self.font_titles_mx.setRange(0, 800); self.font_titles_mx.setValue(45)
        self.font_titles_my = QSpinBox(); self.font_titles_my.setRange(0, 800); self.font_titles_my.setValue(42)
        self.font_titles_typ = QDoubleSpinBox(); self.font_titles_typ.setRange(0.1, 20); self.font_titles_typ.setValue(2.2)
        self.font_titles_era = QDoubleSpinBox(); self.font_titles_era.setRange(0.1, 20); self.font_titles_era.setValue(1.6)
        self.font_titles_opc = DecimalSlider(0.05, 1.0, 0.05, 0.95)
        self.font_titles_shadow_color = ColorEdit("#000000")
        self.font_titles_shadow = DecimalSlider(0.0, 1.0, 0.05, 0.60)

        color_row = self.color_row(self.font_titles_color)
        add_row(form, 0, "Fonte", self.font_titles)
        add_row(form, 1, "Tamanho", self.font_titles_size)
        add_row(form, 2, "Cor", color_row)
        add_row(form, 3, "Posição", self.font_titles_pos)
        add_row(form, 4, "Margens", margins_widget(self.font_titles_mx, self.font_titles_my))
        add_row(form, 5, "Digita por", self.font_titles_typ)
        add_row(form, 6, "Apaga por", self.font_titles_era)
        add_row(form, 7, "Opacidade", self.font_titles_opc)
        add_row(form, 8, "Cor sombra", self.color_row(self.font_titles_shadow_color))
        add_row(form, 9, "Sombra", self.font_titles_shadow)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def build_title_tracks_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.track_titles_table = QTableWidget(0, 2)
        self.track_titles_table.setHorizontalHeaderLabels(["Arquivo", "Título no vídeo"])
        self.track_titles_table.setShowGrid(True)
        self.track_titles_table.setCornerButtonEnabled(False)
        self.track_titles_table.setFrameShape(QFrame.NoFrame)
        self.track_titles_table.verticalHeader().setVisible(False)
        self.track_titles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.track_titles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.track_titles_table.setFixedHeight(285)
        layout.addWidget(self.track_titles_table)

        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_auto_titles = ActionButton("Gerar títulos", "normal", 130)
        self.btn_clear_titles = ActionButton("Limpar títulos", "ghost", 130)
        self.btn_auto_titles.clicked.connect(self.auto_fill_track_titles)
        self.btn_clear_titles.clicked.connect(self.clear_track_titles)
        row.addWidget(self.btn_auto_titles)
        row.addWidget(self.btn_clear_titles)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addStretch(1)
        return tab

    def build_intro_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.intro_tabs = QTabWidget()
        self.intro_tabs.addTab(self.build_intro_phrases_tab(), "Frases")
        self.intro_tabs.addTab(self.build_intro_text_tab(), "Texto")
        self.intro_tabs.addTab(self.build_intro_sound_tab(), "Som")
        self.intro_tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(self.intro_tabs)
        return tab

    def build_intro_phrases_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self.intro_enabled = ToggleSwitch("Usar intro no começo do vídeo")
        layout.addWidget(self.intro_enabled)
        self.intro_table = QTableWidget(0, 3)
        self.intro_table.setHorizontalHeaderLabels(["Início", "Duração", "Frase"])
        self.intro_table.setShowGrid(True)
        self.intro_table.setCornerButtonEnabled(False)
        self.intro_table.setFrameShape(QFrame.NoFrame)
        self.intro_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.intro_table.setFixedHeight(200)
        layout.addWidget(self.intro_table)

        row = QHBoxLayout()
        row.addStretch(1)
        for text, slot in (
            ("Adicionar", lambda: self.add_intro_row("0.0", "4.0", "Nova frase...")),
            ("Remover", self.remove_intro_rows),
            ("Limpar", lambda: self.intro_table.setRowCount(0)),
        ):
            btn = ActionButton(text, "ghost", 84)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch(1)
        layout.addLayout(row)

        form = QGridLayout()
        setup_form(form)
        self.intro_eff = QComboBox()
        self.intro_eff.addItems(["typewriter", "fade", "direct", "typewriter_fade"])
        set_input_width(self.intro_eff)
        self.intro_delay = QDoubleSpinBox(); self.intro_delay.setRange(0, 120); self.intro_delay.setSuffix(" s")
        self.intro_delay.setToolTip("Define quantos segundos a música principal espera antes de começar.")
        self.intro_randomize = ToggleSwitch("Escolher frases aleatórias")
        self.intro_random_count = QSpinBox(); self.intro_random_count.setRange(1, 99); self.intro_random_count.setValue(3)
        add_row(form, 0, "Efeito", self.intro_eff)
        add_row(form, 1, "Música após", self.intro_delay)
        add_wide(form, 2, self.intro_randomize)
        add_row(form, 3, "Qtd. aleatória", self.intro_random_count)
        layout.addWidget(centered_layout(form))

        preset_row = QHBoxLayout()
        preset_row.addStretch(1)
        btn_save = ActionButton("Salvar preset", "ghost")
        btn_load = ActionButton("Carregar preset", "ghost")
        btn_save.clicked.connect(self.save_intro_preset)
        btn_load.clicked.connect(self.load_intro_preset)
        preset_row.addWidget(btn_save)
        preset_row.addWidget(btn_load)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)
        layout.addStretch(1)
        return tab

    def build_intro_text_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        form = QGridLayout()
        setup_form(form)
        self.intro_font = combo_fontes("Georgia")
        self.intro_font_size = QSpinBox(); self.intro_font_size.setRange(8, 180); self.intro_font_size.setValue(48)
        self.intro_font_weight = QSpinBox(); self.intro_font_weight.setRange(100, 900); self.intro_font_weight.setSingleStep(50); self.intro_font_weight.setValue(700)
        self.intro_color = ColorEdit("#FFFFFF")
        self.intro_opacity = DecimalSlider(0.05, 1.0, 0.05, 0.90)
        self.intro_pos = combo_posicao("inferior_esquerda")
        self.intro_mx = QSpinBox(); self.intro_mx.setRange(0, 800); self.intro_mx.setValue(90)
        self.intro_my = QSpinBox(); self.intro_my.setRange(0, 800); self.intro_my.setValue(120)
        self.intro_shadow_color = ColorEdit("#000000")
        self.intro_shadow_size = DecimalSlider(0.0, 10.0, 0.5, 1.5, decimals=1)
        self.intro_shadow_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.65)
        self.intro_background_box = ToggleSwitch("Fundo transparente atrás do texto")
        self.intro_box_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.35)

        add_row(form, 0, "Fonte", self.intro_font)
        add_row(form, 1, "Tamanho", self.intro_font_size)
        add_row(form, 2, "Peso", self.intro_font_weight)
        add_row(form, 3, "Cor", self.color_row(self.intro_color))
        add_row(form, 4, "Opacidade", self.intro_opacity)
        add_row(form, 5, "Posição", self.intro_pos)
        add_row(form, 6, "Margens", margins_widget(self.intro_mx, self.intro_my))
        add_row(form, 7, "Cor sombra", self.color_row(self.intro_shadow_color))
        add_row(form, 8, "Sombra", self.intro_shadow_size)
        add_row(form, 9, "Opac. sombra", self.intro_shadow_opacity)
        add_wide(form, 10, self.intro_background_box)
        add_row(form, 11, "Opac. fundo", self.intro_box_opacity)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def build_intro_sound_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        form = QGridLayout()
        setup_form(form)
        self.intro_audio = PathPicker("file", "Áudios (*.wav *.mp3);;Todos (*.*)", "Áudio de digitação opcional")
        self.intro_typing_volume = QDoubleSpinBox(); self.intro_typing_volume.setRange(0, 1); self.intro_typing_volume.setSingleStep(0.05); self.intro_typing_volume.setValue(0.30)
        self.intro_typing_cps = QDoubleSpinBox(); self.intro_typing_cps.setRange(1, 120); self.intro_typing_cps.setValue(18.0); self.intro_typing_cps.setSuffix(" car/s")
        self.intro_backspace_cps = QDoubleSpinBox(); self.intro_backspace_cps.setRange(1, 120); self.intro_backspace_cps.setValue(22.0); self.intro_backspace_cps.setSuffix(" car/s")
        self.intro_show_cursor = ToggleSwitch("Cursor piscando")
        self.intro_show_cursor.setChecked(True)
        self.intro_backspace_audio = ToggleSwitch("Som no backspace")
        self.intro_backspace_audio.setChecked(True)
        add_row(form, 0, "Som teclado", self.intro_audio)
        add_row(form, 1, "Volume", self.intro_typing_volume)
        add_row(form, 2, "Digitação", self.intro_typing_cps)
        add_row(form, 3, "Backspace", self.intro_backspace_cps)
        add_wide(form, 4, self.intro_show_cursor)
        add_wide(form, 5, self.intro_backspace_audio)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def build_watermark_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QGridLayout()
        setup_form(form)
        self.wm_enabled = ToggleSwitch("Mostrar marca d'água")
        self.wm_enabled.setChecked(True)
        self.wm_mode = QComboBox(); self.wm_mode.addItems(["Texto", "Imagem"]); set_input_width(self.wm_mode)
        self.wm_text = QLineEdit("⚓")
        self.wm_image_preview = QLabel("Nenhuma imagem selecionada")
        self.wm_image_preview.setObjectName("ImagePreview")
        self.wm_image_preview.setAlignment(Qt.AlignCenter)
        self.wm_image_preview.setFixedHeight(86)
        self.wm_image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.wm_img = PathPicker("file", "Imagens (*.png *.jpg *.jpeg *.webp);;Todos (*.*)", "Imagem da marca")
        self.wm_width = QSpinBox(); self.wm_width.setRange(16, 1000); self.wm_width.setValue(180)
        self.wm_font = combo_fontes("Segoe UI Symbol")
        self.wm_font_size = QSpinBox(); self.wm_font_size.setRange(8, 180); self.wm_font_size.setValue(44)
        self.wm_color = ColorEdit("#FFFFFF")
        self.wm_opacity = DecimalSlider(0.05, 1.0, 0.05, 0.70)
        self.wm_pos = combo_posicao("inferior_direita")
        self.wm_mx = QSpinBox(); self.wm_mx.setRange(0, 800); self.wm_mx.setValue(45)
        self.wm_my = QSpinBox(); self.wm_my.setRange(0, 800); self.wm_my.setValue(42)
        self.wm_shadow_color = ColorEdit("#000000")
        self.wm_shadow = DecimalSlider(0.0, 1.0, 0.05, 0.60)
        add_wide(form, 0, self.wm_enabled)
        add_row(form, 1, "Tipo", self.wm_mode)
        self.wm_text_label = add_row(form, 2, "Texto", self.wm_text)
        self.wm_preview_label = add_row(form, 2, "Preview", self.wm_image_preview)
        add_row(form, 3, "Imagem", self.wm_img)
        add_row(form, 4, "Largura img.", self.wm_width)
        add_row(form, 5, "Fonte", self.wm_font)
        add_row(form, 6, "Tamanho", self.wm_font_size)
        add_row(form, 7, "Cor", self.color_row(self.wm_color))
        add_row(form, 8, "Opacidade", self.wm_opacity)
        add_row(form, 9, "Posição", self.wm_pos)
        add_row(form, 10, "Margens", margins_widget(self.wm_mx, self.wm_my))
        add_row(form, 11, "Cor sombra", self.color_row(self.wm_shadow_color))
        add_row(form, 12, "Sombra", self.wm_shadow)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        self.wm_mode.currentTextChanged.connect(self.update_watermark_mode)
        self.wm_img.line.textChanged.connect(self.update_watermark_image_preview)
        self.update_watermark_mode(self.wm_mode.currentText())
        return tab

    def build_audio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ambience, ambience_layout = section("Som ambiente opcional")
        self.bg_picker = PathPicker("file", "Áudios (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma);;Todos (*.*)", "Chuva, vinil, ruído etc.")
        self.bg_vol_slider = QSlider(Qt.Horizontal)
        self.bg_vol_slider.setRange(0, 20)
        self.bg_vol_slider.setValue(6)
        self.bg_vol_label = QLabel("30%")
        self.bg_vol_slider.valueChanged.connect(lambda value: self.bg_vol_label.setText(f"{value * 5}%"))
        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Volume"))
        volume_row.addWidget(self.bg_vol_slider, 1)
        volume_row.addWidget(self.bg_vol_label)
        btn_clear_bg = ActionButton("Limpar", "ghost", 92)
        btn_clear_bg.clicked.connect(lambda: self.bg_picker.set_path(""))
        ambience_layout.addWidget(self.bg_picker)
        ambience_layout.addLayout(volume_row)
        ambience_layout.addWidget(btn_clear_bg, 0, Qt.AlignHCenter)
        layout.addWidget(centered_widget(ambience, 380))

        form = QGridLayout()
        setup_form(form)
        self.set_fadein = ToggleSwitch("Fade in")
        self.set_fadein.setChecked(True)
        self.set_fadeout = ToggleSwitch("Fade out")
        self.set_fadeout.setChecked(True)
        self.set_fadein_s = QDoubleSpinBox(); self.set_fadein_s.setRange(0, 60); self.set_fadein_s.setValue(3)
        self.set_fadeout_s = QDoubleSpinBox(); self.set_fadeout_s.setRange(0, 60); self.set_fadeout_s.setValue(3)
        self.set_norm = ToggleSwitch("Normalizar loudness")
        self.set_norm.setChecked(True)
        self.set_lufs = QDoubleSpinBox(); self.set_lufs.setRange(-40, 0); self.set_lufs.setValue(-14)
        self.set_peak = QDoubleSpinBox(); self.set_peak.setRange(-9, 0); self.set_peak.setValue(-1)
        add_wide(form, 0, self.set_fadein)
        add_row(form, 1, "Duração in", self.set_fadein_s)
        add_wide(form, 2, self.set_fadeout)
        add_row(form, 3, "Duração out", self.set_fadeout_s)
        add_wide(form, 4, self.set_norm)
        add_row(form, 5, "Target LUFS", self.set_lufs)
        add_row(form, 6, "True peak", self.set_peak)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def color_row(self, edit: ColorEdit) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        button = ActionButton("Cor", "ghost")
        button.setFixedWidth(70)
        button.clicked.connect(lambda: self.pick_color(edit))
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return box

    # ---------- Preview ----------

    def extract_preview_frame(self, source: Path | None):
        if not source or not source.exists():
            self.preview_source = None
            self.preview_pixmap = None
            self.preview_status.setText("Aguardando mídia visual")
            return
        if self.preview_source == source and self.preview_pixmap:
            return
        self.preview_source = source
        self.preview_pixmap = None
        suffix = source.suffix.lower()
        if suffix in EXTENSOES_IMAGEM:
            pixmap = QPixmap(str(source))
            self.preview_pixmap = pixmap if not pixmap.isNull() else None
            self.preview_status.setText("Imagem base")
            return
        if suffix not in EXTENSOES_VIDEO or not FFMPEG.exists():
            self.preview_status.setText("Preview indisponível")
            return
        try:
            preview_dir = SCRIPT_DIR / "_temp_audio_processado"
            preview_dir.mkdir(parents=True, exist_ok=True)
            target = preview_dir / "preview_primeiro_frame.jpg"
            command = [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(target)]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, **criar_kwargs_subprocess_controlado())
            pixmap = QPixmap(str(target))
            self.preview_pixmap = pixmap if not pixmap.isNull() else None
            self.preview_status.setText("Primeiro frame do vídeo")
        except Exception:
            self.preview_pixmap = None
            self.preview_status.setText("Não foi possível gerar preview")

    def update_preview(self):
        try:
            config = self.get_config_obj(validar=False)
        except Exception:
            config = None
        self.extract_preview_frame(self.video_picker.path())
        if hasattr(self, "video_widget") and self.video_widget.isVisible():
            return
        self.preview.set_preview(self.preview_pixmap, config)

    def set_preview_volume(self, value: int):
        volume = max(0.0, min(1.0, value / 20.0))
        self.preview_audio.setVolume(volume)
        self.preview_volume_label.setText(f"{value * 5}%")

    def show_static_preview(self):
        self.video_player.stop()
        self.video_player.setSource(QUrl())
        self.video_widget.hide()
        self.preview.show()
        self.btn_test.setText("Render")
        self.update_preview()

    def play_preview_video(self, video_path: Path):
        if not video_path.exists():
            return
        self.preview.hide()
        self.video_widget.show()
        self.video_player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.video_player.play()
        self.btn_test.setText("Parar")

    def loop_preview_video(self, status):
        if status == QMediaPlayer.EndOfMedia and self.video_widget.isVisible():
            self.video_player.setPosition(0)
            self.video_player.play()

    # ---------- Configuração ----------

    def get_intro_phrases(self) -> list[IntroFraseConfig]:
        phrases: list[IntroFraseConfig] = []
        for row in range(self.intro_table.rowCount()):
            start_item = self.intro_table.item(row, 0)
            dur_item = self.intro_table.item(row, 1)
            text_item = self.intro_table.item(row, 2)
            try:
                start = float((start_item.text() if start_item else "") or 0)
                duration = float((dur_item.text() if dur_item else "") or 4)
            except ValueError as exc:
                raise ErroRender(f"Revise os tempos da frase de intro na linha {row + 1}.") from exc
            text = (text_item.text() if text_item else "").strip()
            if text:
                phrases.append(IntroFraseConfig(start, duration, text))
        return phrases

    def music_files_from_folder(self) -> list[Path]:
        folder = self.music_picker.path()
        if not folder or not folder.exists():
            return []
        files = [
            path for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in EXTENSOES_AUDIO
            and not path.name.startswith("_temp_")
        ]
        bg_path = self.bg_picker.path()
        if bg_path:
            try:
                bg_resolved = bg_path.resolve()
                files = [path for path in files if path.resolve() != bg_resolved]
            except OSError:
                pass
        return sorted(files, key=natural_key)

    def get_track_titles(self) -> dict[str, str]:
        titles: dict[str, str] = {}
        if not hasattr(self, "track_titles_table"):
            return titles
        for row in range(self.track_titles_table.rowCount()):
            file_item = self.track_titles_table.item(row, 0)
            title_item = self.track_titles_table.item(row, 1)
            file_name = (file_item.text() if file_item else "").strip()
            title = (title_item.text() if title_item else "").strip()
            if file_name and title:
                titles[file_name] = title
        return titles

    def get_config_obj(self, validar: bool = True) -> RenderConfig:
        video = self.video_picker.path()
        music = self.music_picker.path()
        if validar:
            if video is None:
                raise ErroRender("Escolha o vídeo, GIF ou imagem base.")
            if music is None:
                raise ErroRender("Escolha a pasta onde estão as músicas.")

        title_font = FonteTextoConfig(
            font_family=self.font_titles.currentText(),
            font_size=self.font_titles_size.value(),
            color=limpar_hex(self.font_titles_color.text()),
            opacity=self.font_titles_opc.value(),
            position=self.font_titles_pos.currentData(),
            margin_left=self.font_titles_mx.value(),
            margin_bottom=self.font_titles_my.value(),
            typing_duration=self.font_titles_typ.value(),
            erasing_duration=self.font_titles_era.value(),
            shadow_color=limpar_hex(self.font_titles_shadow_color.text(), "#000000"),
            shadow_opacity=self.font_titles_shadow.value(),
        )
        watermark = WatermarkConfig(
            enabled=self.wm_enabled.isChecked(),
            mode=self.wm_mode.currentText().lower(),
            text=self.wm_text.text(),
            image_path=self.wm_img.line.text(),
            image_width=self.wm_width.value(),
            font_family=self.wm_font.currentText(),
            font_size=self.wm_font_size.value(),
            color=limpar_hex(self.wm_color.text()),
            opacity=self.wm_opacity.value(),
            position=self.wm_pos.currentData(),
            margin_x=self.wm_mx.value(),
            margin_y=self.wm_my.value(),
            shadow_color=limpar_hex(self.wm_shadow_color.text(), "#000000"),
            shadow_opacity=self.wm_shadow.value(),
        )
        intro = IntroTextConfig(
            enabled=self.intro_enabled.isChecked(),
            phrases=self.get_intro_phrases(),
            effect=self.intro_eff.currentText(),
            typing_audio_path=self.intro_audio.line.text(),
            typing_volume=self.intro_typing_volume.value(),
            typing_cps=self.intro_typing_cps.value(),
            backspace_cps=self.intro_backspace_cps.value(),
            backspace_audio_enabled=self.intro_backspace_audio.isChecked(),
            show_cursor=self.intro_show_cursor.isChecked(),
            randomize_phrases=self.intro_randomize.isChecked(),
            random_count=self.intro_random_count.value(),
            delay_music_seconds=self.intro_delay.value(),
            font_family=self.intro_font.currentText(),
            font_size=self.intro_font_size.value(),
            font_weight=self.intro_font_weight.value(),
            color=limpar_hex(self.intro_color.text()),
            opacity=self.intro_opacity.value(),
            position=self.intro_pos.currentData(),
            margin_x=self.intro_mx.value(),
            margin_y=self.intro_my.value(),
            shadow_color=limpar_hex(self.intro_shadow_color.text(), "#000000"),
            shadow_opacity=self.intro_shadow_opacity.value(),
            shadow_size=self.intro_shadow_size.value(),
            background_box=self.intro_background_box.isChecked(),
            box_opacity=self.intro_box_opacity.value(),
        )
        return RenderConfig(
            video_path=video,
            music_folder=music,
            background_audio_path=self.bg_picker.path(),
            output_folder=self.out_picker.path() or gerar_pasta_saida_padrao(),
            use_gpu=self.set_gpu.isChecked(),
            use_fade_in=self.set_fadein.isChecked(),
            use_fade_out=self.set_fadeout.isChecked(),
            fade_in_seconds=self.set_fadein_s.value(),
            fade_out_seconds=self.set_fadeout_s.value(),
            background_volume=self.bg_vol_slider.value() / 20.0,
            normalizacao=NormalizacaoConfig(
                enabled=self.set_norm.isChecked(),
                target_lufs=self.set_lufs.value(),
                true_peak=self.set_peak.value(),
            ),
            fonte_texto=title_font,
            track_titles=self.get_track_titles(),
            watermark=watermark,
            intro=intro,
        )

    def save_config(self):
        try:
            cfg = self.get_config_obj(validar=False)
            salvar_json_config({
                "app_version": APP_VERSION,
                "paths": {
                    "video_path": caminho_ou_vazio(self.video_picker.path()),
                    "music_folder": caminho_ou_vazio(self.music_picker.path()),
                    "background_audio_path": caminho_ou_vazio(self.bg_picker.path()),
                    "output_folder": caminho_ou_vazio(self.out_picker.path()),
                },
                "render": {
                    "use_gpu": cfg.use_gpu,
                    "use_fade_in": cfg.use_fade_in,
                    "use_fade_out": cfg.use_fade_out,
                    "fade_in_seconds": cfg.fade_in_seconds,
                    "fade_out_seconds": cfg.fade_out_seconds,
                    "background_volume": cfg.background_volume,
                },
                "normalizacao": asdict(cfg.normalizacao),
                "fonte_texto": asdict(cfg.fonte_texto),
                "titulos_musicas": cfg.track_titles,
                "watermark": asdict(cfg.watermark),
                "intro": intro_config_to_dict(cfg.intro),
            })
        except Exception as exc:
            print(f"Erro ao salvar config: {exc}")

    def load_config(self):
        self._config_loading = True
        data = carregar_json_config()
        if data:
            paths = data.get("paths", {})
            self.video_picker.set_path(paths.get("video_path"))
            self.music_picker.set_path(paths.get("music_folder"))
            self.bg_picker.set_path(paths.get("background_audio_path"))
            self.out_picker.set_path(paths.get("output_folder"))

            render = data.get("render", {})
            self.set_gpu.setChecked(bool(render.get("use_gpu", True)))
            self.set_fadein.setChecked(bool(render.get("use_fade_in", True)))
            self.set_fadeout.setChecked(bool(render.get("use_fade_out", True)))
            self.set_fadein_s.setValue(float(render.get("fade_in_seconds", 3.0)))
            self.set_fadeout_s.setValue(float(render.get("fade_out_seconds", 3.0)))
            self.bg_vol_slider.setValue(int(float(render.get("background_volume", 0.3)) * 20))

            norm = data.get("normalizacao", {})
            if self.normalizacao_config_antiga_zerada(str(data.get("app_version", "")), norm):
                self.set_norm.setChecked(True)
                self.set_lufs.setValue(-14.0)
                self.set_peak.setValue(-1.0)
            else:
                self.set_norm.setChecked(bool(norm.get("enabled", True)))
                self.set_lufs.setValue(float(norm.get("target_lufs", -14.0)))
                self.set_peak.setValue(float(norm.get("true_peak", -1.0)))

            self.apply_title_config(FonteTextoConfig(**{k: v for k, v in data.get("fonte_texto", {}).items() if k in FonteTextoConfig.__dataclass_fields__}))
            self.refresh_track_titles_table(data.get("titulos_musicas", {}))
            self.apply_watermark_config(WatermarkConfig(**{k: v for k, v in data.get("watermark", {}).items() if k in WatermarkConfig.__dataclass_fields__}))
            self.apply_intro_config(intro_config_from_dict(data.get("intro", {})))
        self._config_loading = False

    def apply_title_config(self, cfg: FonteTextoConfig):
        self.set_combo_text(self.font_titles, cfg.font_family)
        self.font_titles_size.setValue(int(cfg.font_size))
        self.font_titles_color.setText(cfg.color)
        self.font_titles_opc.setValue(float(cfg.opacity))
        self.set_combo_data(self.font_titles_pos, cfg.position)
        self.font_titles_mx.setValue(int(cfg.margin_left))
        self.font_titles_my.setValue(int(cfg.margin_bottom))
        self.font_titles_typ.setValue(float(cfg.typing_duration))
        self.font_titles_era.setValue(float(cfg.erasing_duration))
        self.font_titles_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.font_titles_shadow.setValue(float(cfg.shadow_opacity))

    def refresh_track_titles_table(self, existing_titles: dict | None = None):
        current_titles = self.get_track_titles()
        if isinstance(existing_titles, dict):
            current_titles.update({str(k): str(v) for k, v in existing_titles.items()})
        files = self.music_files_from_folder()
        self.track_titles_table.blockSignals(True)
        self.track_titles_table.setRowCount(0)
        for file in files:
            row = self.track_titles_table.rowCount()
            self.track_titles_table.insertRow(row)
            file_item = QTableWidgetItem(file.name)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            title_item = QTableWidgetItem(current_titles.get(file.name, limpar_titulo_musica(file)))
            self.track_titles_table.setItem(row, 0, file_item)
            self.track_titles_table.setItem(row, 1, title_item)
        self.track_titles_table.blockSignals(False)
        self.trigger_autosave()

    def auto_fill_track_titles(self):
        files = self.music_files_from_folder()
        file_map = {file.name: limpar_titulo_musica(file) for file in files}
        self.track_titles_table.blockSignals(True)
        for row in range(self.track_titles_table.rowCount()):
            file_item = self.track_titles_table.item(row, 0)
            title_item = self.track_titles_table.item(row, 1)
            if file_item and title_item:
                title_item.setText(file_map.get(file_item.text(), title_item.text()))
        self.track_titles_table.blockSignals(False)
        self.trigger_autosave()

    def clear_track_titles(self):
        self.track_titles_table.blockSignals(True)
        for row in range(self.track_titles_table.rowCount()):
            item = self.track_titles_table.item(row, 1)
            if item:
                item.setText("")
        self.track_titles_table.blockSignals(False)
        self.trigger_autosave()

    def apply_watermark_config(self, cfg: WatermarkConfig):
        self.wm_enabled.setChecked(bool(cfg.enabled))
        self.set_combo_text(self.wm_mode, "Imagem" if cfg.mode == "imagem" else "Texto")
        self.wm_text.setText(cfg.text)
        self.wm_img.set_path(cfg.image_path)
        self.wm_width.setValue(int(cfg.image_width))
        self.set_combo_text(self.wm_font, cfg.font_family)
        self.wm_font_size.setValue(int(cfg.font_size))
        self.wm_color.setText(cfg.color)
        self.wm_opacity.setValue(float(cfg.opacity))
        self.set_combo_data(self.wm_pos, cfg.position)
        self.wm_mx.setValue(int(cfg.margin_x))
        self.wm_my.setValue(int(cfg.margin_y))
        self.wm_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.wm_shadow.setValue(float(cfg.shadow_opacity))
        self.update_watermark_mode(self.wm_mode.currentText())

    def apply_intro_config(self, cfg: IntroTextConfig):
        self.intro_enabled.setChecked(bool(cfg.enabled))
        self.set_combo_text(self.intro_eff, cfg.effect)
        self.intro_delay.setValue(float(cfg.delay_music_seconds))
        self.intro_randomize.setChecked(bool(cfg.randomize_phrases))
        self.intro_random_count.setValue(int(cfg.random_count))
        self.set_intro_rows(cfg.phrases)
        self.set_combo_text(self.intro_font, cfg.font_family)
        self.intro_font_size.setValue(int(cfg.font_size))
        self.intro_font_weight.setValue(int(cfg.font_weight))
        self.intro_color.setText(cfg.color)
        self.intro_opacity.setValue(float(cfg.opacity))
        self.set_combo_data(self.intro_pos, cfg.position)
        self.intro_mx.setValue(int(cfg.margin_x))
        self.intro_my.setValue(int(cfg.margin_y))
        self.intro_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.intro_shadow_size.setValue(float(cfg.shadow_size))
        self.intro_shadow_opacity.setValue(float(cfg.shadow_opacity))
        self.intro_background_box.setChecked(bool(cfg.background_box))
        self.intro_box_opacity.setValue(float(cfg.box_opacity))
        self.intro_audio.set_path(cfg.typing_audio_path)
        self.intro_typing_volume.setValue(float(cfg.typing_volume))
        self.intro_typing_cps.setValue(float(cfg.typing_cps))
        self.intro_backspace_cps.setValue(float(cfg.backspace_cps))
        self.intro_show_cursor.setChecked(bool(cfg.show_cursor))
        self.intro_backspace_audio.setChecked(bool(cfg.backspace_audio_enabled))

    @staticmethod
    def set_combo_text(combo: QComboBox, text: str):
        index = combo.findText(str(text))
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def set_combo_data(combo: QComboBox, value: str):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def normalizacao_config_antiga_zerada(app_version: str, norm: dict) -> bool:
        if app_version == APP_VERSION:
            return False
        try:
            return float(norm.get("target_lufs", -14.0)) == 0.0 and float(norm.get("true_peak", -1.0)) == 0.0
        except (TypeError, ValueError):
            return True

    # ---------- Intro ----------

    def add_intro_row(self, start, duration, text):
        row = self.intro_table.rowCount()
        self.intro_table.insertRow(row)
        self.intro_table.setItem(row, 0, QTableWidgetItem(str(start)))
        self.intro_table.setItem(row, 1, QTableWidgetItem(str(duration)))
        self.intro_table.setItem(row, 2, QTableWidgetItem(str(text)))
        self.trigger_autosave()

    def set_intro_rows(self, phrases: list[IntroFraseConfig]):
        self.intro_table.setRowCount(0)
        for phrase in phrases:
            self.add_intro_row(f"{phrase.inicio:.2f}", f"{phrase.duracao:.2f}", phrase.texto)

    def remove_intro_rows(self):
        rows = sorted({idx.row() for idx in self.intro_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.intro_table.removeRow(row)
        self.trigger_autosave()

    def save_intro_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar preset da intro", str(SCRIPT_DIR), "Preset JSON (*.json)")
        if not path:
            return
        intro = self.get_config_obj(validar=False).intro
        Path(path).write_text(json.dumps(intro_config_to_dict(intro), ensure_ascii=False, indent=2), encoding="utf-8")

    def load_intro_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carregar preset da intro", str(SCRIPT_DIR), "Preset JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.apply_intro_config(intro_config_from_dict(data))
        except Exception as exc:
            QMessageBox.warning(self, "Preset da intro", f"Não foi possível carregar o preset:\n{exc}")

    # ---------- Eventos e execução ----------

    def connect_auto_signals(self):
        for child in self.findChildren(QWidget):
            if isinstance(child, QLineEdit):
                child.textChanged.connect(self.trigger_autosave)
            elif isinstance(child, (QSpinBox, QDoubleSpinBox)):
                child.valueChanged.connect(self.trigger_autosave)
            elif isinstance(child, QComboBox):
                child.currentIndexChanged.connect(self.trigger_autosave)
            elif isinstance(child, QSlider):
                child.valueChanged.connect(self.trigger_autosave)
            elif isinstance(child, QCheckBox):
                child.stateChanged.connect(self.trigger_autosave)
        self.intro_table.itemChanged.connect(self.trigger_autosave)
        self.track_titles_table.itemChanged.connect(self.trigger_autosave)

    def trigger_autosave(self, *args):
        if self._config_loading:
            return
        self.autosave_timer.start()
        self.preview_timer.start()

    def pick_color(self, edit: ColorEdit):
        color = QColorDialog.getColor(QColor(limpar_hex(edit.text())), self)
        if color.isValid():
            edit.setText(color.name().upper())

    def update_watermark_mode(self, text: str):
        image_mode = text == "Imagem"
        self.wm_text_label.setVisible(not image_mode)
        self.wm_text.setVisible(not image_mode)
        self.wm_preview_label.setVisible(image_mode)
        self.wm_image_preview.setVisible(image_mode)
        self.wm_font.setEnabled(not image_mode)
        self.wm_font_size.setEnabled(not image_mode)
        self.wm_color.setEnabled(not image_mode)
        self.wm_img.setEnabled(image_mode)
        self.wm_width.setEnabled(image_mode)
        self.update_watermark_image_preview()
        self.trigger_autosave()

    def update_watermark_image_preview(self):
        if not hasattr(self, "wm_image_preview"):
            return
        path = self.wm_img.path()
        if not path or not path.exists():
            self.wm_image_preview.setPixmap(QPixmap())
            self.wm_image_preview.setText("Nenhuma imagem selecionada")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.wm_image_preview.setPixmap(QPixmap())
            self.wm_image_preview.setText("Imagem inválida")
            return
        self.wm_image_preview.setText("")
        size = self.wm_image_preview.size()
        target = QSize(max(1, size.width() - 20), max(1, size.height() - 20))
        self.wm_image_preview.setPixmap(pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def log_msg(self, text: str):
        self.log_widget.moveCursor(QTextCursor.End)
        self.log_widget.insertPlainText(text)
        self.log_widget.moveCursor(QTextCursor.End)

    def toggle_log(self):
        visible = not self.log_widget.isVisible()
        self.log_widget.setVisible(visible)
        self.btn_log.setText("Ocultar log" if visible else "Mostrar log")

    def start_render(self, teste=False):
        if self.worker and self.worker.isRunning():
            return
        try:
            config = self.get_config_obj(validar=True)
            self.save_config()
        except Exception as exc:
            QMessageBox.warning(self, "Configuração incompleta", str(exc))
            return
        self.log_widget.clear()
        self.prog_bar.setValue(0)
        self.ultimo_video = None
        self.render_mode = "preview" if teste else "final"
        self.lbl_status.setText("Iniciando teste de 30s" if teste else "Iniciando renderização")
        if teste:
            self.show_static_preview()
            self.btn_test.setText("Parar")
            self.btn_start.setEnabled(False)
        else:
            self.btn_start.setText("Pausar")
            self.btn_start.setEnabled(True)
            self.btn_test.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.worker = WorkerRender(config, modo="teste_30s" if teste else "final")
        self.worker.log.connect(self.log_msg)
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.etapa.connect(self.lbl_status.setText)
        self.worker.terminado.connect(self.finalizar_render)
        self.worker.start()

    def iniciar_ou_pausar(self):
        if self.worker and self.worker.isRunning():
            paused = self.worker.alternar_pausa()
            self.btn_start.setText("Retomar" if paused else "Pausar")
            self.lbl_status.setText("Pausado" if paused else "Retomando")
            self.log_msg("\nProcesso pausado.\n" if paused else "\nProcesso retomado.\n")
        else:
            self.start_render(teste=False)

    def render_preview_toggle(self):
        if self.worker and self.worker.isRunning() and self.render_mode == "preview":
            self.cancelar_render()
            return
        if self.worker and self.worker.isRunning():
            return
        if self.video_widget.isVisible():
            self.show_static_preview()
            self.lbl_status.setText("Preview parado")
            return
        self.start_render(teste=True)

    def cancelar_render(self):
        if not self.worker or not self.worker.isRunning():
            return
        self.lbl_status.setText("Cancelando")
        self.btn_cancel.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.log_msg("\nCancelamento solicitado. Encerrando FFmpeg e removendo arquivo incompleto...\n")
        self.worker.cancelar()

    def atualizar_progresso(self, value: int):
        self.prog_bar.setValue(max(0, min(100, int(value))))

    def finalizar_render(self, sucesso: bool, mensagem: str, caminho_saida: str):
        self.btn_start.setText("Iniciar")
        self.btn_start.setEnabled(True)
        self.btn_test.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if sucesso:
            self.ultimo_video = Path(caminho_saida)
            self.prog_bar.setValue(100)
            self.lbl_status.setText("Finalizado com sucesso")
            if self.render_mode == "preview":
                self.play_preview_video(self.ultimo_video)
            else:
                QMessageBox.information(self, "Finalizado", f"{mensagem}\n\n{caminho_saida}")
        else:
            self.prog_bar.setValue(0)
            self.lbl_status.setText("Cancelado" if "cancel" in mensagem.lower() else "Erro")
            if "cancel" in mensagem.lower():
                if self.render_mode != "preview":
                    QMessageBox.information(self, "Cancelado", mensagem)
            else:
                log_path = SCRIPT_DIR / "erro_ffmpeg_log.txt"
                try:
                    log_path.write_text(mensagem, encoding="utf-8", errors="ignore")
                except Exception:
                    pass
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Erro")
                msg.setText("Erro ao executar o render.")
                msg.setInformativeText(f"O log foi salvo em:\n{log_path}")
                msg.setDetailedText(mensagem)
                msg.exec()
        self.render_mode = ""
        self.worker = None

    def abrir_pasta_saida(self):
        folder = self.out_picker.path()
        if folder is None and self.ultimo_video and self.ultimo_video.exists():
            folder = self.ultimo_video.parent
        if folder is None:
            folder = SCRIPT_DIR
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            QMessageBox.information(self, "Pasta de saída", f"Não foi possível abrir:\n{folder}\n\n{exc}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            answer = QMessageBox.question(
                self,
                "Cancelar renderização?",
                "Existe uma renderização em andamento. Fechar a janela vai cancelar o processo e apagar arquivos incompletos. Deseja fechar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.save_config()
                self.cancelar_render()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_config()
            event.accept()


def iniciar_ui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    iniciar_ui()
