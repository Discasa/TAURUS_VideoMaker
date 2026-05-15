# -*- coding: utf-8 -*-
from __future__ import annotations

"""Design tokens and stylesheet builders for the PySide interface."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokens:
    text_main: str = "#EAF2FF"
    text_strong: str = "#F6FAFF"
    text_section: str = "#DCEBFF"
    text_muted: str = "#8FA4C4"
    text_header: str = "#CFE2FF"
    text_disabled: str = "#7C8DA8"
    text_disabled_button: str = "#5F6E84"

    app_bg: str = "#0B111C"
    panel_bg: str = "#101826"
    panel_bg_dark: str = "#0A101A"
    section_bg: str = "#131D2B"
    input_bg: str = "#0D1420"
    input_focus_bg: str = "#111B2B"
    table_header_bg: str = "#17263C"
    disabled_bg: str = "#101826"

    border_panel: str = "#233047"
    border_subtle: str = "#26354D"
    border_control: str = "#31415C"
    border_focus: str = "#5EA0FF"
    border_disabled_button: str = "#243148"

    accent: str = "#2F86FF"
    accent_hover: str = "#4B9AFF"
    accent_soft: str = "#6FB1FF"
    black: str = "#000000"
    white: str = "#FFFFFF"
    switch_off: str = "#3A4658"


@dataclass(frozen=True)
class RadiusTokens:
    panel: int = 14
    shell: int = 18
    image_preview: int = 12
    control: int = 17
    text_area: int = 14
    popup: int = 10
    tab: int = 11
    progress: int = 7
    progress_chunk: int = 6
    slider_groove: int = 3
    slider_handle: int = 7
    scrollbar: int = 5


@dataclass(frozen=True)
class SizeTokens:
    control_height: int = 34
    right_form_width: int = 430
    preview_height_normal: int = 380
    preview_height_log_open: int = 270
    preview_aspect_ratio: float = 16 / 9
    log_height_open: int = 260
    base_window_width: int = 1520
    base_window_height: int = 820
    base_window_min_width: int = 1420
    base_window_min_height: int = 740
    ui_zoom_min: float = 0.5
    ui_zoom_max: float = 2.0


@dataclass(frozen=True)
class ButtonVariant:
    bg: str
    hover: str
    text: str
    border: str


COLORS = ColorTokens()
RADIUS = RadiusTokens()
SIZES = SizeTokens()

BUTTON_VARIANTS = {
    "normal": ButtonVariant("#18263A", "#213753", "#7EAFFF", COLORS.border_control),
    "primary": ButtonVariant(COLORS.accent, COLORS.accent_hover, COLORS.white, "#1F6FD9"),
    "danger": ButtonVariant("#8A3A4A", "#A94C5F", COLORS.white, "#703040"),
    "ghost": ButtonVariant("#111B2B", "#18263A", COLORS.text_header, COLORS.border_control),
}

CONTROL_HEIGHT = SIZES.control_height
RIGHT_FORM_WIDTH = SIZES.right_form_width
PREVIEW_HEIGHT_NORMAL = SIZES.preview_height_normal
PREVIEW_HEIGHT_LOG_OPEN = SIZES.preview_height_log_open
PREVIEW_ASPECT_RATIO = SIZES.preview_aspect_ratio
LOG_HEIGHT_OPEN = SIZES.log_height_open
BASE_WINDOW_WIDTH = SIZES.base_window_width
BASE_WINDOW_HEIGHT = SIZES.base_window_height
BASE_WINDOW_MIN_WIDTH = SIZES.base_window_min_width
BASE_WINDOW_MIN_HEIGHT = SIZES.base_window_min_height
UI_ZOOM_MIN = SIZES.ui_zoom_min
UI_ZOOM_MAX = SIZES.ui_zoom_max


def clamp_zoom(value: float) -> float:
    return max(UI_ZOOM_MIN, min(UI_ZOOM_MAX, float(value)))


def escala(valor: int | float, zoom: float, minimo: int = 1) -> int:
    return max(minimo, int(round(float(valor) * zoom)))


def pill_radius(height: int | float) -> int:
    # Qt can render square corners when border-radius is equal to half an odd
    # control height. Keeping it one pixel below half preserves the pill shape.
    return max(4, int((float(height) - 1) // 2))


def button_variant(kind: str) -> ButtonVariant:
    return BUTTON_VARIANTS.get(kind, BUTTON_VARIANTS["normal"])


def action_button_stylesheet(kind: str, zoom: float) -> str:
    variant = button_variant(kind)
    height = escala(CONTROL_HEIGHT, clamp_zoom(zoom), 18)
    radius = pill_radius(height)
    padding_x = escala(14, zoom, 6)
    return f"""
QPushButton {{
    background-color: {variant.bg};
    color: {variant.text};
    border: 1px solid {variant.border};
    border-radius: {radius}px;
    font-weight: 700;
    padding: 0px {padding_x}px;
}}
QPushButton:hover {{
    background-color: {variant.hover};
}}
QPushButton:pressed {{
    background-color: {variant.border};
}}
QPushButton:disabled {{
    background-color: {COLORS.disabled_bg};
    color: {COLORS.text_disabled_button};
    border: 1px solid {COLORS.border_disabled_button};
    border-radius: {radius}px;
}}
"""


def build_base_stylesheet() -> str:
    c = COLORS
    r = RADIUS
    return f"""
* {{
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 12px;
    color: {c.text_main};
}}
QWidget {{
    background-color: {c.app_bg};
}}
QFrame#LeftPanel, QFrame#RightPanel {{
    background-color: {c.panel_bg};
    border: 1px solid {c.border_panel};
    border-radius: {r.panel}px;
}}
QFrame#CenterPanel {{
    background-color: {c.app_bg};
}}
QFrame#Section, QFrame#Transport, QFrame#PreviewShell {{
    background-color: {c.section_bg};
    border: 1px solid {c.border_subtle};
    border-radius: {r.shell}px;
}}
QLabel#Brand {{
    color: {c.text_strong};
    font-size: 20px;
    font-weight: 800;
}}
QLabel#Subtle {{
    color: {c.text_muted};
}}
QLabel#SectionTitle {{
    color: {c.text_section};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#ColumnTitle {{
    color: {c.text_strong};
    font-size: 16px;
    font-weight: 800;
}}
QLabel#ImagePreview {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_control};
    border-radius: {r.image_preview}px;
    color: {c.text_muted};
}}
QWidget#PreviewGroup {{
    background-color: transparent;
}}
QWidget#PreviewVolumeBar {{
    background-color: transparent;
}}
QLabel {{
    background-color: transparent;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_control};
    border-radius: {r.control}px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px 12px;
    selection-background-color: {c.accent};
}}
QTextEdit {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_control};
    border-radius: {r.text_area}px;
    padding: 10px 12px;
    selection-background-color: {c.accent};
}}
QLineEdit {{
    border-radius: {r.control}px;
}}
QSpinBox, QDoubleSpinBox {{
    border-radius: {r.control}px;
    padding-left: 12px;
    padding-right: 12px;
}}
QComboBox {{
    border-radius: {r.control}px;
    padding-left: 12px;
    padding-right: 36px;
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_subtle};
    border-radius: {r.control}px;
    color: {c.text_disabled};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {c.border_focus};
    background-color: {c.input_focus_bg};
}}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0px;
    border: none;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    background-color: transparent;
    border: none;
    border-top-right-radius: {r.control}px;
    border-bottom-right-radius: {r.control}px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {c.accent_soft};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c.panel_bg};
    border: 1px solid {c.border_control};
    border-radius: {r.popup}px;
    selection-background-color: {c.accent};
    outline: none;
}}
QTabWidget {{
    background-color: {c.panel_bg};
}}
QTabWidget::pane {{
    border: 1px solid {c.border_subtle};
    border-radius: 0px;
    background-color: {c.panel_bg};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {c.panel_bg_dark};
    color: {c.text_muted};
    border: 1px solid {c.border_subtle};
    border-bottom: 1px solid {c.border_subtle};
    padding: 8px 8px;
    min-width: 55px;
    border-top-left-radius: {r.tab}px;
    border-top-right-radius: {r.tab}px;
}}
QTabBar::tab:selected {{
    background-color: {c.panel_bg};
    color: {c.white};
    border-color: {c.border_subtle};
    border-bottom-color: {c.panel_bg};
}}
QTabBar::tab:!selected {{
    background-color: {c.app_bg};
    color: {c.text_muted};
}}
QProgressBar {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_control};
    border-radius: {r.progress}px;
    min-height: 10px;
    max-height: 14px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {c.accent};
    border-radius: {r.progress_chunk}px;
}}
QSlider {{
    background-color: transparent;
    min-height: 24px;
    max-height: 24px;
}}
QSlider::groove:horizontal {{
    background-color: {c.section_bg};
    border: 1px solid {c.border_subtle};
    height: 6px;
    border-radius: {r.slider_groove}px;
}}
QSlider::sub-page:horizontal {{
    background-color: {c.accent};
    border-radius: {r.slider_groove}px;
}}
QSlider::handle:horizontal {{
    background-color: {c.accent_hover};
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: {r.slider_handle}px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {c.accent_soft};
}}
QTableWidget {{
    background-color: {c.input_bg};
    border: 1px solid {c.border_control};
    border-radius: 0px;
    gridline-color: {c.border_subtle};
    outline: none;
}}
QTableWidget::item {{
    padding: 3px 5px;
}}
QTableCornerButton::section {{
    background-color: {c.table_header_bg};
    border: none;
    border-right: 1px solid {c.border_control};
    border-bottom: 1px solid {c.border_control};
}}
QHeaderView::section {{
    background-color: {c.table_header_bg};
    border: none;
    border-bottom: 1px solid {c.border_control};
    padding: 5px;
    color: {c.text_header};
    font-weight: 700;
}}
QScrollBar:vertical {{
    background-color: {c.input_bg};
    border-left: 1px solid {c.border_subtle};
    width: 12px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {c.border_subtle};
    border-radius: {r.scrollbar}px;
    min-height: 24px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {c.border_control};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background-color: transparent;
    border: none;
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {c.input_bg};
    border-top: 1px solid {c.border_subtle};
    height: 12px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {c.border_subtle};
    border-radius: {r.scrollbar}px;
    min-width: 24px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {c.border_control};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background-color: transparent;
    border: none;
    width: 0px;
}}
"""


def zoom_stylesheet(zoom: float) -> str:
    control_height = escala(CONTROL_HEIGHT, zoom, 18)
    radius = pill_radius(control_height)
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
    border-top-left-radius: {escala(RADIUS.tab, zoom, 5)}px;
    border-top-right-radius: {escala(RADIUS.tab, zoom, 5)}px;
}}
QTextEdit {{
    border-radius: {escala(RADIUS.text_area, zoom, 6)}px;
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
    border-radius: {pill_radius(slider_handle)}px;
}}
"""


STYLE_PRIME = build_base_stylesheet()
