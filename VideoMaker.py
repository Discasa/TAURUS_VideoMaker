# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Interface PySide6 do LoFi VideoMaker.

A lógica de renderização, FFmpeg e persistência ficam em engine.py.
"""

import os
import sys
from dataclasses import asdict
from pathlib import Path

from engine import (
    APP_VERSION,
    ErroRender,
    FonteTextoConfig,
    IntroFraseConfig,
    IntroTextConfig,
    NormalizacaoConfig,
    RenderConfig,
    SCRIPT_DIR,
    WatermarkConfig,
    WorkerRender,
    caminho_ou_vazio,
    carregar_json_config,
    gerar_pasta_saida_padrao,
    intro_config_from_dict,
    intro_config_to_dict,
    limpar_hex,
    popular_combo_posicoes,
    salvar_json_config,
)
# ==========================
# UI PYSIDE6 MODERNA
# ==========================

try:
    from PySide6.QtCore import Property, QPropertyAnimation, QRectF, QSize, Qt, QTimer
    from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QPainter, QTextCursor
    from PySide6.QtWidgets import (
        QApplication, QAbstractSpinBox, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox,
        QFileDialog, QFontComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
        QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QTextEdit,
        QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QStackedWidget, QListWidget, QListWidgetItem,
        QGroupBox, QFormLayout
    )
except ImportError:
    print("PySide6 não está instalado. Instale com: pip install PySide6")
    sys.exit(1)

# ---------- Estilos ----------
STYLE_DARK = """
* {
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 12px;
    color: #E0E0E0;
}
QMainWindow, QWidget#MainContent {
    background-color: #1A1A1C;
}
QFrame#Sidebar {
    background-color: #222325;
    border-right: 1px solid #323438;
}
QFrame#ContentArea {
    background-color: #1A1A1C;
}
QFrame#Footer {
    background-color: #222325;
    border-top: 1px solid #323438;
}
QGroupBox {
    border: 1px solid #323438;
    border-radius: 6px;
    margin-top: 14px;
    background-color: #1F2022;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #8A929B;
    font-weight: 600;
}
QLabel {
    background: transparent;
}
QLabel#PageTitle {
    font-size: 18px;
    font-weight: bold;
    color: #FFFFFF;
}
QLabel#AppTitle {
    font-size: 14px;
    font-weight: bold;
    color: #FFFFFF;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox, QTextEdit {
    background: #151516;
    border: 1px solid #383A3F;
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 22px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QFontComboBox:focus {
    border: 1px solid #5EA0FF;
    background: #1B1D20;
}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    border: none;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QListWidget#SidebarList {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#SidebarList::item {
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 8px;
}
QListWidget#SidebarList::item:hover {
    background: #2D2F33;
}
QListWidget#SidebarList::item:selected {
    background: #364254;
    color: #9EC1FF;
    font-weight: bold;
}
QProgressBar {
    background: #151516;
    border: 1px solid #323438;
    border-radius: 4px;
    text-align: center;
    color: #FFF;
    font-weight: bold;
    min-height: 16px;
}
QProgressBar::chunk {
    background: #5EA0FF;
    border-radius: 3px;
}
QSlider::groove:horizontal {
    background: #151516;
    border: 1px solid #323438;
    height: 6px;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #5EA0FF;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFF;
    border: 1px solid #5EA0FF;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QTableWidget {
    background: #151516;
    border: 1px solid #323438;
    border-radius: 4px;
    gridline-color: #2D2F33;
}
QHeaderView::section {
    background: #1F2022;
    padding: 4px;
    border: none;
    border-bottom: 1px solid #323438;
    font-weight: bold;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #4A4D52;
    border-radius: 4px;
}
"""

# ---------- Componentes Reutilizáveis ----------

class ModernButton(QPushButton):
    def __init__(self, texto="", kind="normal", parent=None):
        super().__init__(texto, parent)
        self.kind = kind
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._update_style()

    def _update_style(self):
        if self.kind == "primary":
            bg, hover, text = "#2563EB", "#3B82F6", "#FFFFFF"
            border = "#1D4ED8"
        elif self.kind == "danger":
            bg, hover, text = "#991B1B", "#DC2626", "#FFFFFF"
            border = "#7F1D1D"
        else:
            bg, hover, text = "#2D2F33", "#3A3D42", "#E0E0E0"
            border = "#4A4D52"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {border}; }}
            QPushButton:disabled {{ background-color: #1A1A1C; color: #555; border: 1px solid #333; }}
        """)

class ToggleSwitch(QCheckBox):
    # Uma versão mais enxuta do seu toggle original
    TRACK_W, TRACK_H, KNOB_D, HEIGHT = 36, 18, 14, 24
    GAP_TEXT = 8
    def __init__(self, texto="", parent=None):
        super().__init__(texto, parent)
        self._offset = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(self.HEIGHT)
        self.stateChanged.connect(self._animar)

    def sizeHint(self):
        w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self.TRACK_W + (self.GAP_TEXT + w if w else 0), self.HEIGHT)

    def getOffset(self): return self._offset
    def setOffset(self, val): self._offset = val; self.update()
    offset = Property(float, getOffset, setOffset)

    def _animar(self, *args):
        self._anim.stop()
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ty = (self.HEIGHT - self.TRACK_H) / 2
        track = QRectF(0, ty, self.TRACK_W, self.TRACK_H)

        color = QColor("#2563EB") if self.isChecked() else QColor("#4A4D52")
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(track, self.TRACK_H/2, self.TRACK_H/2)

        kx = 2 + self._offset * (self.TRACK_W - self.KNOB_D - 4)
        ky = ty + (self.TRACK_H - self.KNOB_D) / 2
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(kx, ky, self.KNOB_D, self.KNOB_D))

        if self.text():
            p.setPen(QColor("#E0E0E0") if self.isEnabled() else QColor("#777"))
            p.setFont(self.font())
            p.drawText(self.rect().adjusted(self.TRACK_W + self.GAP_TEXT, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())

class PathPicker(QWidget):
    def __init__(self, mode: str, filter_text: str = "*.*", placeholder: str = ""):
        super().__init__()
        self.mode = mode
        self.filter_text = filter_text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line = QLineEdit()
        self.line.setPlaceholderText(placeholder)
        self.btn = ModernButton("Procurar")
        self.btn.clicked.connect(self.escolher)
        layout.addWidget(self.line)
        layout.addWidget(self.btn)

    def escolher(self):
        if self.mode == "file": path, _ = QFileDialog.getOpenFileName(self, "Escolher Arquivo", str(SCRIPT_DIR), self.filter_text)
        else: path = QFileDialog.getExistingDirectory(self, "Escolher Pasta", str(SCRIPT_DIR))
        if path: self.line.setText(path)

    def path(self) -> Path | None:
        t = self.line.text().strip()
        return Path(t) if t else None

    def set_path(self, path):
        self.line.setText(str(path) if path else "")

def remove_spinbox_buttons(widget: QWidget):
    for spin in widget.findChildren(QAbstractSpinBox):
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spin.setAlignment(Qt.AlignLeft)

def criar_linha_margens(spin_x: QSpinBox, spin_y: QSpinBox) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    for spin in (spin_x, spin_y):
        spin.setMinimumWidth(120)
        spin.setMaximumWidth(170)
        spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    label_x = QLabel("X:")
    label_y = QLabel("Y:")
    label_x.setFixedWidth(18)
    label_y.setFixedWidth(18)

    layout.addWidget(label_x)
    layout.addWidget(spin_x)
    layout.addSpacing(18)
    layout.addWidget(label_y)
    layout.addWidget(spin_y)
    layout.addStretch(1)
    return container

_FONTES_DO_SISTEMA_REGISTRADAS = False

def registrar_fontes_do_sistema():
    global _FONTES_DO_SISTEMA_REGISTRADAS
    if _FONTES_DO_SISTEMA_REGISTRADAS:
        return

    pastas = []
    if os.name == "nt":
        pastas.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    else:
        pastas.extend([Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"])

    vistos = set()
    for pasta in pastas:
        if not pasta.exists():
            continue
        for padrao in ("*.ttf", "*.otf", "*.ttc"):
            for fonte in pasta.rglob(padrao):
                chave = fonte.resolve()
                if chave in vistos:
                    continue
                vistos.add(chave)
                QFontDatabase.addApplicationFont(str(fonte))

    _FONTES_DO_SISTEMA_REGISTRADAS = True

# ---------- Páginas da Sidebar ----------

class PageMedia(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        lbl = QLabel("📁 Mídias e Saída")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)

        grp = QGroupBox("Arquivos Base")
        fl = QFormLayout(grp)
        self.mw.video_picker = PathPicker("file", "Vídeos/GIF (*.mp4 *.mov *.mkv *.avi *.webm *.gif);;Todos (*.*)", "Vídeo/GIF de fundo")
        self.mw.music_picker = PathPicker("folder", placeholder="Pasta com as músicas (arquivos de áudio)")
        self.mw.bg_picker = PathPicker("file", "Áudios (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma);;Todos (*.*)", "Áudio contínuo (ex: chuva)")
        fl.addRow("Vídeo Lo-fi:", self.mw.video_picker)
        fl.addRow("Músicas:", self.mw.music_picker)
        fl.addRow("Som Ambiente:", self.mw.bg_picker)

        # Volume do som ambiente
        vol_layout = QHBoxLayout()
        self.mw.bg_vol_slider = QSlider(Qt.Horizontal)
        self.mw.bg_vol_slider.setRange(0, 20)
        self.mw.bg_vol_slider.setValue(3)
        self.mw.bg_vol_lbl = QLabel("30%")
        self.mw.bg_vol_slider.valueChanged.connect(lambda v: self.mw.bg_vol_lbl.setText(f"{v*10}%"))
        vol_layout.addWidget(self.mw.bg_vol_slider)
        vol_layout.addWidget(self.mw.bg_vol_lbl)
        fl.addRow("Vol. Ambiente:", vol_layout)
        layout.addWidget(grp)

        grp_out = QGroupBox("Exportação")
        fl_out = QFormLayout(grp_out)
        self.mw.out_picker = PathPicker("folder", placeholder="Padrão: render_DATA_HORA na pasta do script")
        fl_out.addRow("Salvar em:", self.mw.out_picker)

        btn_open = ModernButton("Abrir pasta de saída")
        btn_open.clicked.connect(self.mw.abrir_pasta_saida)
        fl_out.addRow("", btn_open)
        layout.addWidget(grp_out)

class PageTitles(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        lbl = QLabel("✍️ Títulos das Músicas")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)

        grp = QGroupBox("Tipografia e Posição")
        fl = QFormLayout(grp)

        registrar_fontes_do_sistema()
        self.mw.font_titles = QFontComboBox()
        self.mw.font_titles.setFontFilters(QFontComboBox.FontFilter.AllFonts)
        self.mw.font_titles.setWritingSystem(QFontDatabase.WritingSystem.Any)
        self.mw.font_titles.setToolTip("Lista de fontes instaladas no sistema.")
        self.mw.font_titles_size = QSpinBox(); self.mw.font_titles_size.setRange(8,160)
        self.mw.font_titles_color = QLineEdit()
        btn_color = ModernButton("Cor")
        btn_color.clicked.connect(lambda: self.pick_color(self.mw.font_titles_color))
        c_layout = QHBoxLayout()
        c_layout.addWidget(self.mw.font_titles_color); c_layout.addWidget(btn_color)

        self.mw.font_titles_pos = QComboBox()
        popular_combo_posicoes(self.mw.font_titles_pos, "inferior_esquerda")

        self.mw.font_titles_mx = QSpinBox(); self.mw.font_titles_mx.setRange(0,500)
        self.mw.font_titles_my = QSpinBox(); self.mw.font_titles_my.setRange(0,500)
        marg_layout = criar_linha_margens(self.mw.font_titles_mx, self.mw.font_titles_my)

        fl.addRow("Fonte:", self.mw.font_titles)
        fl.addRow("Tamanho:", self.mw.font_titles_size)
        fl.addRow("Cor Hex:", c_layout)
        fl.addRow("Posição:", self.mw.font_titles_pos)
        fl.addRow("Margens:", marg_layout)
        layout.addWidget(grp)

        grp_anim = QGroupBox("Animação (Máquina de Escrever)")
        fl_anim = QFormLayout(grp_anim)
        self.mw.font_titles_typ = QDoubleSpinBox(); self.mw.font_titles_typ.setRange(0.1,20)
        self.mw.font_titles_era = QDoubleSpinBox(); self.mw.font_titles_era.setRange(0.1,20)
        self.mw.font_titles_opc = QDoubleSpinBox(); self.mw.font_titles_opc.setRange(0.05, 1.0); self.mw.font_titles_opc.setSingleStep(0.1)
        fl_anim.addRow("Tempo Digitando (s):", self.mw.font_titles_typ)
        fl_anim.addRow("Tempo Apagando (s):", self.mw.font_titles_era)
        fl_anim.addRow("Opacidade Final:", self.mw.font_titles_opc)
        layout.addWidget(grp_anim)
        remove_spinbox_buttons(self)

    def pick_color(self, le):
        c = QColorDialog.getColor(QColor(limpar_hex(le.text())), self)
        if c.isValid(): le.setText(c.name().upper())

class PageWatermark(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        lbl = QLabel("🏷️ Marca d'água")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)

        self.mw.wm_enabled = ToggleSwitch("Ativar Marca d'água")
        layout.addWidget(self.mw.wm_enabled)

        grp = QGroupBox("Configurações")
        fl = QFormLayout(grp)
        self.mw.wm_mode = QComboBox()
        self.mw.wm_mode.addItems(["Texto", "Imagem"])
        self.mw.wm_text = QLineEdit()
        self.mw.wm_img = PathPicker("file", "Imagens (*.png *.jpg);;Todos (*.*)", "Caminho da Imagem")

        self.mw.wm_mode.currentTextChanged.connect(self.toggle_mode)

        self.mw.wm_pos = QComboBox(); popular_combo_posicoes(self.mw.wm_pos, "inferior_direita")

        self.mw.wm_mx = QSpinBox(); self.mw.wm_mx.setRange(0,800)
        self.mw.wm_my = QSpinBox(); self.mw.wm_my.setRange(0,800)
        marg_layout = criar_linha_margens(self.mw.wm_mx, self.mw.wm_my)

        fl.addRow("Modo:", self.mw.wm_mode)
        fl.addRow("Texto:", self.mw.wm_text)
        fl.addRow("Imagem:", self.mw.wm_img)
        fl.addRow("Posição:", self.mw.wm_pos)
        fl.addRow("Margens:", marg_layout)
        layout.addWidget(grp)
        remove_spinbox_buttons(self)
        self.toggle_mode(self.mw.wm_mode.currentText())

    def toggle_mode(self, text):
        is_txt = (text == "Texto")
        self.mw.wm_text.setEnabled(is_txt)
        self.mw.wm_img.setEnabled(not is_txt)

class PageIntro(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        layout = QVBoxLayout(self)

        lbl = QLabel("🎬 Frases de Introdução")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)

        self.mw.intro_enabled = ToggleSwitch("Ativar Frases Iniciais")
        layout.addWidget(self.mw.intro_enabled)

        self.mw.intro_table = QTableWidget(0, 3)
        self.mw.intro_table.setHorizontalHeaderLabels(["Início", "Duração", "Frase"])
        self.mw.intro_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.mw.intro_table)

        btn_row = QHBoxLayout()
        btn_add = ModernButton("Adicionar Frase")
        btn_rem = ModernButton("Remover")
        btn_add.clicked.connect(lambda: self._add_row("0.0", "4.0", "Nova frase..."))
        btn_rem.clicked.connect(self._rem_row)
        btn_row.addWidget(btn_add); btn_row.addWidget(btn_rem); btn_row.addStretch()
        layout.addLayout(btn_row)

        grp = QGroupBox("Configurações da Intro")
        fl = QFormLayout(grp)

        self.mw.intro_eff = QComboBox()
        self.mw.intro_eff.addItems(["typewriter", "fade", "direct", "typewriter_fade"])
        self.mw.intro_audio = PathPicker("file", "Áudios (*.wav *.mp3);;Todos (*.*)", "Áudio de digitação (opcional)")
        self.mw.intro_delay = QDoubleSpinBox(); self.mw.intro_delay.setRange(0, 120)
        self.mw.intro_delay.setSuffix(" s")
        self.mw.intro_delay.setToolTip("Tempo de espera antes de iniciar a música principal. Use 0 para tocar imediatamente.")

        fl.addRow("Efeito:", self.mw.intro_eff)
        fl.addRow("Som (Teclado):", self.mw.intro_audio)
        fl.addRow("Atrasar início da música:", self.mw.intro_delay)
        layout.addWidget(grp)
        remove_spinbox_buttons(self)

    def _add_row(self, start, dur, txt):
        r = self.mw.intro_table.rowCount()
        self.mw.intro_table.insertRow(r)
        self.mw.intro_table.setItem(r, 0, QTableWidgetItem(start))
        self.mw.intro_table.setItem(r, 1, QTableWidgetItem(dur))
        self.mw.intro_table.setItem(r, 2, QTableWidgetItem(txt))
    def _rem_row(self):
        for idx in sorted({i.row() for i in self.mw.intro_table.selectedIndexes()}, reverse=True):
            self.mw.intro_table.removeRow(idx)

class PageSettings(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        lbl = QLabel("⚙️ Configurações Avançadas")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)

        grp_rnd = QGroupBox("Renderização")
        fl_rnd = QFormLayout(grp_rnd)
        self.mw.set_gpu = ToggleSwitch("Usar GPU (NVIDIA NVENC)")
        fl_rnd.addRow("", self.mw.set_gpu)
        layout.addWidget(grp_rnd)

        grp_fade = QGroupBox("Transições de Áudio")
        fl_fade = QFormLayout(grp_fade)
        self.mw.set_fadein = ToggleSwitch("Fade In")
        self.mw.set_fadeout = ToggleSwitch("Fade Out")
        self.mw.set_fadein_s = QDoubleSpinBox(); self.mw.set_fadein_s.setRange(0, 60)
        self.mw.set_fadeout_s = QDoubleSpinBox(); self.mw.set_fadeout_s.setRange(0, 60)
        fl_fade.addRow(self.mw.set_fadein, self.mw.set_fadein_s)
        fl_fade.addRow(self.mw.set_fadeout, self.mw.set_fadeout_s)
        layout.addWidget(grp_fade)

        grp_norm = QGroupBox("Normalização de Áudio (Loudnorm)")
        fl_norm = QFormLayout(grp_norm)
        self.mw.set_norm = ToggleSwitch("Ativar Normalização")
        self.mw.set_lufs = QDoubleSpinBox(); self.mw.set_lufs.setRange(-40, 0)
        self.mw.set_peak = QDoubleSpinBox(); self.mw.set_peak.setRange(-9, 0)
        fl_norm.addRow("", self.mw.set_norm)
        fl_norm.addRow("Target LUFS:", self.mw.set_lufs)
        fl_norm.addRow("True Peak:", self.mw.set_peak)
        layout.addWidget(grp_norm)
        remove_spinbox_buttons(self)

# ---------- Janela Principal ----------

class MainUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Criador de Vídeo Lo-fi {APP_VERSION}")
        self.resize(900, 640)
        self.setStyleSheet(STYLE_DARK)

        # State
        self.worker = None
        self.ultimo_video = None
        self._config_loading = False
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1000)
        self.autosave_timer.timeout.connect(self.save_config)

        # Layout Principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # Top Content Area (Sidebar + Pages)
        content_split = QHBoxLayout()
        content_split.setContentsMargins(0,0,0,0)
        content_split.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)

        app_title = QLabel("LO-FI MAKER")
        app_title.setObjectName("AppTitle")
        app_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addSpacing(20)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("SidebarList")
        items = ["📁 Mídias", "🎬 Intro", "✍️ Títulos", "🏷️ Watermark", "⚙️ Avançado"]
        self.nav_list.addItems(items)
        self.nav_list.setCurrentRow(0)
        sidebar_layout.addWidget(self.nav_list)

        # Pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")

        self.page_media = PageMedia(self)
        self.page_intro = PageIntro(self)
        self.page_titles = PageTitles(self)
        self.page_watermark = PageWatermark(self)
        self.page_settings = PageSettings(self)

        self.stack.addWidget(self.page_media)
        self.stack.addWidget(self.page_intro)
        self.stack.addWidget(self.page_titles)
        self.stack.addWidget(self.page_watermark)
        self.stack.addWidget(self.page_settings)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        content_split.addWidget(self.sidebar)
        content_split.addWidget(self.stack)
        main_layout.addLayout(content_split, 1)

        # Footer (Controles persistentes)
        self.footer = QFrame()
        self.footer.setObjectName("Footer")
        self.footer.setFixedHeight(70)
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(15, 10, 15, 10)

        # Log toggle e Progresso
        row1 = QHBoxLayout()
        self.lbl_status = QLabel("Pronto.")
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.btn_log = ModernButton("Exibir Log")
        self.btn_log.clicked.connect(self.toggle_log)
        row1.addWidget(self.lbl_status)
        row1.addWidget(self.prog_bar, 1)
        row1.addWidget(self.btn_log)

        # Actions
        row2 = QHBoxLayout()
        self.btn_test = ModernButton("Renderizar Teste 30s")
        self.btn_test.clicked.connect(lambda: self.start_render(teste=True))
        self.btn_start = ModernButton("Iniciar Renderização Final", "primary")
        self.btn_start.clicked.connect(self.iniciar_ou_pausar)
        self.btn_cancel = ModernButton("Cancelar", "danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancelar_render)
        row2.addWidget(self.btn_test)
        row2.addStretch()
        row2.addWidget(self.btn_cancel)
        row2.addWidget(self.btn_start)

        footer_layout.addLayout(row1)
        footer_layout.addLayout(row2)
        main_layout.addWidget(self.footer)

        # Overlay de Log (Oculto por padrão)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFixedHeight(120)
        self.log_widget.hide()
        main_layout.addWidget(self.log_widget)

        self.load_config()
        self._connect_autosave_signals(self)

    def toggle_log(self):
        vis = not self.log_widget.isVisible()
        self.log_widget.setVisible(vis)
        self.btn_log.setText("Ocultar Log" if vis else "Exibir Log")

    def _connect_autosave_signals(self, widget):
        # Auto-binder genérico
        for child in widget.findChildren(QWidget):
            if isinstance(child, QLineEdit): child.textChanged.connect(self.trigger_autosave)
            elif isinstance(child, QSpinBox) or isinstance(child, QDoubleSpinBox): child.valueChanged.connect(self.trigger_autosave)
            elif isinstance(child, ToggleSwitch): child.stateChanged.connect(self.trigger_autosave)
            elif isinstance(child, QComboBox): child.currentIndexChanged.connect(self.trigger_autosave)
            elif isinstance(child, QSlider): child.valueChanged.connect(self.trigger_autosave)

    def trigger_autosave(self, *args):
        if not self._config_loading: self.autosave_timer.start()

    # --- Mapeamento Config <-> UI ---
    def get_config_obj(self, validar: bool = True) -> RenderConfig:
        f_txt = FonteTextoConfig(
            font_family=self.font_titles.currentFont().family(),
            font_size=self.font_titles_size.value(),
            color=limpar_hex(self.font_titles_color.text()),
            position=self.font_titles_pos.currentData(),
            margin_left=self.font_titles_mx.value(),
            margin_bottom=self.font_titles_my.value(),
            typing_duration=self.font_titles_typ.value(),
            erasing_duration=self.font_titles_era.value(),
            opacity=self.font_titles_opc.value()
        )
        wm = WatermarkConfig(
            enabled=self.wm_enabled.isChecked(),
            mode=self.wm_mode.currentText().lower(),
            text=self.wm_text.text(),
            image_path=self.wm_img.line.text(),
            position=self.wm_pos.currentData(),
            margin_x=self.wm_mx.value(),
            margin_y=self.wm_my.value()
        )
        norm = NormalizacaoConfig(
            enabled=self.set_norm.isChecked(),
            target_lufs=self.set_lufs.value(),
            true_peak=self.set_peak.value()
        )

        phrases = []
        for r in range(self.intro_table.rowCount()):
            item_start = self.intro_table.item(r, 0)
            item_dur = self.intro_table.item(r, 1)
            item_txt = self.intro_table.item(r, 2)
            try:
                start = float((item_start.text() if item_start else "") or 0)
                dur = float((item_dur.text() if item_dur else "") or 4)
            except ValueError as erro:
                raise ErroRender(f"Revise os tempos da frase de intro na linha {r + 1}.") from erro
            txt = (item_txt.text() if item_txt else "") or ""
            if txt: phrases.append(IntroFraseConfig(start, dur, txt))

        intro = IntroTextConfig(
            enabled=self.intro_enabled.isChecked(),
            phrases=phrases,
            effect=self.intro_eff.currentText(),
            typing_audio_path=self.intro_audio.line.text(),
            delay_music_seconds=self.intro_delay.value()
        )

        video_path = self.video_picker.path()
        music_folder = self.music_picker.path()
        output_folder = self.out_picker.path() or gerar_pasta_saida_padrao()

        if validar:
            if video_path is None:
                raise ErroRender("Escolha o vídeo ou GIF base.")
            if music_folder is None:
                raise ErroRender("Escolha a pasta onde estão as músicas.")

        return RenderConfig(
            video_path=video_path,
            music_folder=music_folder,
            background_audio_path=self.bg_picker.path(),
            output_folder=output_folder,
            use_gpu=self.set_gpu.isChecked(),
            use_fade_in=self.set_fadein.isChecked(),
            use_fade_out=self.set_fadeout.isChecked(),
            fade_in_seconds=self.set_fadein_s.value(),
            fade_out_seconds=self.set_fadeout_s.value(),
            background_volume=self.bg_vol_slider.value() / 10.0,
            normalizacao=norm,
            fonte_texto=f_txt,
            watermark=wm,
            intro=intro
        )

    def save_config(self):
        try:
            cfg = self.get_config_obj(validar=False)
            # Mapeia pro dictionary esperado
            dados = {
                "paths": {
                    "video_path": caminho_ou_vazio(self.video_picker.path()),
                    "music_folder": caminho_ou_vazio(self.music_picker.path()),
                    "background_audio_path": caminho_ou_vazio(self.bg_picker.path()),
                    "output_folder": caminho_ou_vazio(self.out_picker.path()),
                },
                "render": {
                    "use_gpu": cfg.use_gpu, "use_fade_in": cfg.use_fade_in, "use_fade_out": cfg.use_fade_out,
                    "fade_in_seconds": cfg.fade_in_seconds, "fade_out_seconds": cfg.fade_out_seconds,
                    "background_volume": cfg.background_volume,
                },
                "normalizacao": asdict(cfg.normalizacao),
                "fonte_texto": asdict(cfg.fonte_texto),
                "watermark": asdict(cfg.watermark),
                "intro": intro_config_to_dict(cfg.intro)
            }
            salvar_json_config(dados)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")

    def load_config(self):
        self._config_loading = True
        dados = carregar_json_config()
        if not dados:
            self._config_loading = False
            return

        p = dados.get("paths", {})
        self.video_picker.set_path(p.get("video_path"))
        self.music_picker.set_path(p.get("music_folder"))
        self.bg_picker.set_path(p.get("background_audio_path"))
        self.out_picker.set_path(p.get("output_folder"))

        r = dados.get("render", {})
        self.set_gpu.setChecked(r.get("use_gpu", True))
        self.set_fadein.setChecked(r.get("use_fade_in", True))
        self.set_fadeout.setChecked(r.get("use_fade_out", True))
        self.set_fadein_s.setValue(r.get("fade_in_seconds", 3.0))
        self.set_fadeout_s.setValue(r.get("fade_out_seconds", 3.0))
        self.bg_vol_slider.setValue(int(r.get("background_volume", 0.3) * 10))

        n = dados.get("normalizacao", {})
        self.set_norm.setChecked(bool(n.get("enabled", self.set_norm.isChecked())))
        self.set_lufs.setValue(float(n.get("target_lufs", self.set_lufs.value())))
        self.set_peak.setValue(float(n.get("true_peak", self.set_peak.value())))

        f = dados.get("fonte_texto", {})
        familia = f.get("font_family")
        if familia:
            self.font_titles.setCurrentFont(QFont(str(familia)))
        self.font_titles_size.setValue(int(f.get("font_size", self.font_titles_size.value())))
        self.font_titles_color.setText(str(f.get("color", self.font_titles_color.text()) or "#FFFFFF"))
        idx = self.font_titles_pos.findData(f.get("position", self.font_titles_pos.currentData()))
        if idx >= 0:
            self.font_titles_pos.setCurrentIndex(idx)
        self.font_titles_mx.setValue(int(f.get("margin_left", self.font_titles_mx.value())))
        self.font_titles_my.setValue(int(f.get("margin_bottom", self.font_titles_my.value())))
        self.font_titles_typ.setValue(float(f.get("typing_duration", self.font_titles_typ.value())))
        self.font_titles_era.setValue(float(f.get("erasing_duration", self.font_titles_era.value())))
        self.font_titles_opc.setValue(float(f.get("opacity", self.font_titles_opc.value())))

        w = dados.get("watermark", {})
        self.wm_enabled.setChecked(bool(w.get("enabled", self.wm_enabled.isChecked())))
        modo = str(w.get("mode", "texto")).lower()
        idx = self.wm_mode.findText("Imagem" if modo == "imagem" else "Texto")
        if idx >= 0:
            self.wm_mode.setCurrentIndex(idx)
        self.wm_text.setText(str(w.get("text", self.wm_text.text()) or ""))
        self.wm_img.set_path(w.get("image_path"))
        idx = self.wm_pos.findData(w.get("position", self.wm_pos.currentData()))
        if idx >= 0:
            self.wm_pos.setCurrentIndex(idx)
        self.wm_mx.setValue(int(w.get("margin_x", self.wm_mx.value())))
        self.wm_my.setValue(int(w.get("margin_y", self.wm_my.value())))
        self.page_watermark.toggle_mode(self.wm_mode.currentText())

        intro = intro_config_from_dict(dados.get("intro", {}))
        self.intro_enabled.setChecked(bool(intro.enabled))
        idx = self.intro_eff.findText(intro.effect)
        if idx >= 0:
            self.intro_eff.setCurrentIndex(idx)
        self.intro_audio.set_path(intro.typing_audio_path)
        self.intro_delay.setValue(float(intro.delay_music_seconds))
        self.intro_table.setRowCount(0)
        for frase in intro.phrases:
            self.page_intro._add_row(f"{frase.inicio:.2f}", f"{frase.duracao:.2f}", frase.texto)

        self._config_loading = False

    def log_msg(self, msg):
        self.log_widget.moveCursor(QTextCursor.End)
        self.log_widget.insertPlainText(msg)
        self.log_widget.moveCursor(QTextCursor.End)

    def iniciar_ou_pausar(self):
        if self.worker and self.worker.isRunning():
            self.alternar_pausa()
            return
        self.start_render(teste=False)

    def start_render(self, teste=False):
        if self.worker and self.worker.isRunning():
            return

        try:
            config = self.get_config_obj()
            self.save_config()
        except Exception as erro:
            QMessageBox.warning(self, "Configuração incompleta", str(erro))
            return

        self.log_widget.clear()
        self.prog_bar.setValue(0)
        self.ultimo_video = None
        self.lbl_status.setText("Iniciando teste de 30s" if teste else "Iniciando renderização")

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Pausar")
        self.btn_test.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.worker = WorkerRender(config, modo="teste_30s" if teste else "final")
        self.worker.log.connect(self.log_msg)
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.etapa.connect(self.lbl_status.setText)
        self.worker.terminado.connect(self.finalizar_render)
        self.worker.start()

    def alternar_pausa(self):
        if not self.worker or not self.worker.isRunning():
            return
        pausado = self.worker.alternar_pausa()
        if pausado:
            self.btn_start.setText("Retomar")
            self.lbl_status.setText("Pausado")
            self.log_msg("\nProcesso pausado.\n")
        else:
            self.btn_start.setText("Pausar")
            self.lbl_status.setText("Retomando")
            self.log_msg("\nProcesso retomado.\n")

    def cancelar_render(self):
        if not self.worker or not self.worker.isRunning():
            return
        self.lbl_status.setText("Cancelando")
        self.btn_cancel.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.log_msg("\nCancelamento solicitado. Encerrando FFmpeg e removendo arquivo incompleto...\n")
        self.worker.cancelar()

    def atualizar_progresso(self, valor: int):
        self.prog_bar.setValue(max(0, min(100, int(valor))))

    def finalizar_render(self, sucesso: bool, mensagem: str, caminho_saida: str):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Iniciar Renderização Final")
        self.btn_test.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if sucesso:
            self.ultimo_video = Path(caminho_saida)
            self.prog_bar.setValue(100)
            self.lbl_status.setText("Finalizado com sucesso")
            QMessageBox.information(self, "Finalizado", f"{mensagem}\n\n{caminho_saida}")
        else:
            self.prog_bar.setValue(0)
            self.lbl_status.setText("Cancelado" if "cancel" in mensagem.lower() else "Erro")
            if "cancel" in mensagem.lower():
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

        self.worker = None

    def abrir_pasta_saida(self):
        # Pega o caminho do picker da interface nova
        pasta = self.out_picker.path()

        if pasta is None and self.ultimo_video and self.ultimo_video.exists():
            pasta = self.ultimo_video.parent
        if pasta is None:
            pasta = SCRIPT_DIR

        try:
            pasta.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(pasta))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(pasta)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(pasta)])
        except Exception as e:
            QMessageBox.information(self, "Pasta de saída", f"Não foi possível abrir a pasta:\n{pasta}\n\nErro: {e}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            resposta = QMessageBox.question(
                self,
                "Cancelar renderização?",
                "Existe uma renderização em andamento. Fechar a janela vai cancelar o processo e apagar arquivos incompletos. Deseja fechar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resposta == QMessageBox.Yes:
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
    win = MainUI()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    iniciar_ui()
