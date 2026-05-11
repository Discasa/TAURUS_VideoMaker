# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from core.engine import (
    APP_ICON,
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
    LOG_DIR,
    PRE_RENDER_DIR,
    RenderConfig,
    WatermarkConfig,
    WorkerRender,
    PREVIEW_CACHE_DIR,
    caminho_ou_vazio,
    carregar_config,
    criar_kwargs_subprocess_controlado,
    gerar_pasta_saida_padrao,
    intro_config_from_dict,
    intro_config_to_dict,
    limpar_pre_render,
    limpar_hex,
    limpar_titulo_musica,
    natural_key,
    salvar_config,
)

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut, QTextCursor
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractScrollArea,
    QCheckBox,
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
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .center_panel import CenterPanel
from .common import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_MIN_HEIGHT,
    BASE_WINDOW_MIN_WIDTH,
    BASE_WINDOW_WIDTH,
    CONTROL_HEIGHT,
    LOG_HEIGHT_OPEN,
    PREVIEW_ASPECT_RATIO,
    PREVIEW_HEIGHT_LOG_OPEN,
    PREVIEW_HEIGHT_NORMAL,
    STYLE_PRIME,
    UI_ZOOM_MAX,
    UI_ZOOM_MIN,
    ActionButton,
    ColorSwatch,
    DecimalSlider,
    PathPicker,
    ToggleSwitch,
    add_row,
    add_wide,
    centered_layout,
    centered_widget,
    clamp_zoom,
    combo_fontes,
    combo_posicao,
    escala,
    margins_widget,
    padronizar_altura_controles,
    remove_spin_buttons,
    section,
    set_input_width,
    setup_form,
    zoom_stylesheet,
)
from .left_panel import LeftPanel
from .right_panel import RightPanel

class MainUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TAURUS Video Maker {APP_VERSION}")
        if APP_ICON.exists():
            self.setWindowIcon(QIcon(str(APP_ICON)))
        self.ui_zoom = 1.0
        self._zoom_loaded = False
        self.resize(BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT)
        self.setMinimumSize(escala(BASE_WINDOW_MIN_WIDTH, UI_ZOOM_MIN, 700), escala(BASE_WINDOW_MIN_HEIGHT, UI_ZOOM_MIN, 360))
        self.setStyleSheet(STYLE_PRIME + zoom_stylesheet(self.ui_zoom))

        self.worker = None
        self.render_mode = ""
        self.ultimo_video: Path | None = None
        self.preview_source: Path | None = None
        self.preview_pixmap: QPixmap | None = None
        self.pre_render_path: Path | None = None
        self._ui_ready = False
        self._config_loading = True
        self._undo_restoring = False
        self._undo_stack: list[dict] = []
        self._last_undo_snapshot = ""

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(900)
        self.autosave_timer.timeout.connect(self.save_config)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self.update_preview)

        self.preview_play_timer = QTimer(self)
        self.preview_play_timer.setInterval(1000)
        self.preview_play_timer.timeout.connect(self.try_play_pre_render)

        root = QHBoxLayout(self)
        self.root_layout = root
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.left_panel = LeftPanel(self)
        self.center_panel = CenterPanel(self)
        self.right_panel = RightPanel(self)

        root.addWidget(self.left_panel)
        root.addWidget(self.center_panel, 2)
        root.addWidget(self.right_panel)

        self.apply_intro_config(IntroTextConfig())
        self.load_config()
        if not self._zoom_loaded:
            self.set_ui_zoom_percent(int(round(self.zoom_inicial_para_tela() * 100)), resize_window=True)
        self.connect_auto_signals()
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.undo_last_change)
        self.music_picker.line.textChanged.connect(lambda *_: self.refresh_track_titles_table())
        self.bg_picker.line.textChanged.connect(lambda *_: self.refresh_track_titles_table())
        remove_spin_buttons(self)
        padronizar_altura_controles(self, self.ui_zoom)
        self._ui_ready = True
        self.record_undo_snapshot(force=True)
        self.update_preview()

    # ---------- Construção visual ----------

    def build_music_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.music_tabs = QTabWidget()
        self.music_tabs.addTab(self.build_title_tracks_tab(), "Nomes")
        self.music_tabs.addTab(self.build_title_font_tab(), "Fonte")
        self.music_tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(self.music_tabs)
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
        self.font_titles_color = ColorSwatch("#FFFFFF")
        self.font_titles_pos = combo_posicao("inferior_esquerda")
        self.font_titles_mx = QSpinBox(); self.font_titles_mx.setRange(0, 800); self.font_titles_mx.setValue(45)
        self.font_titles_my = QSpinBox(); self.font_titles_my.setRange(0, 800); self.font_titles_my.setValue(42)
        self.font_titles_typ = QDoubleSpinBox(); self.font_titles_typ.setRange(0.1, 20); self.font_titles_typ.setValue(2.2)
        self.font_titles_era = QDoubleSpinBox(); self.font_titles_era.setRange(0.1, 20); self.font_titles_era.setValue(1.6)
        self.font_titles_opc = DecimalSlider(0.05, 1.0, 0.05, 0.95)
        self.font_titles_shadow_enabled = ToggleSwitch("Sombra do texto")
        self.font_titles_shadow_enabled.setChecked(True)
        self.font_titles_shadow_color = ColorSwatch("#000000")
        self.font_titles_shadow = DecimalSlider(0.0, 1.0, 0.05, 0.60)
        self.font_titles_shadow_size = DecimalSlider(0.0, 20.0, 1.0, 2.0, decimals=0, suffix=" px")
        self.font_titles_background_box = ToggleSwitch("Fundo do texto")
        self.font_titles_background_color = ColorSwatch("#000000")
        self.font_titles_background_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.35)
        self.font_titles_background_padding = DecimalSlider(0.0, 40.0, 1.0, 6.0, decimals=0)

        add_row(form, 0, "Posição", self.font_titles_pos)
        add_row(form, 1, "Margens", margins_widget(self.font_titles_mx, self.font_titles_my))
        add_row(form, 2, "Fonte", self.font_inline_row(self.font_titles, self.font_titles_size, self.font_titles_color))
        add_row(form, 3, "Opacidade", self.font_titles_opc)
        add_row(form, 4, "Sombra do texto", self.toggle_color_row(self.font_titles_shadow_enabled, self.font_titles_shadow_color))
        add_row(form, 5, "Tam. sombra", self.font_titles_shadow_size)
        add_row(form, 6, "Opac. sombra", self.font_titles_shadow)
        add_row(form, 7, "Fundo do texto", self.toggle_color_row(self.font_titles_background_box, self.font_titles_background_color))
        add_row(form, 8, "Tam. fundo", self.font_titles_background_padding)
        add_row(form, 9, "Opac. fundo", self.font_titles_background_opacity)
        add_row(form, 10, "Digita por", self.font_titles_typ)
        add_row(form, 11, "Apaga por", self.font_titles_era)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def build_title_tracks_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.track_titles_table = QTableWidget(0, 1)
        self.track_titles_table.setHorizontalHeaderLabels(["Nome"])
        self.track_titles_table.setShowGrid(True)
        self.track_titles_table.setCornerButtonEnabled(False)
        self.track_titles_table.setFrameShape(QFrame.NoFrame)
        self.track_titles_table.verticalHeader().setVisible(False)
        self.track_titles_table.horizontalHeader().setVisible(False)
        self.track_titles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.track_titles_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.track_titles_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.track_titles_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.track_titles_table, 1)

        order_row = QHBoxLayout()
        order_row.addStretch(1)
        self.btn_track_up = ActionButton("Subir", "ghost", 84)
        self.btn_track_down = ActionButton("Descer", "ghost", 84)
        self.btn_track_up.clicked.connect(lambda: self.move_track_row(-1))
        self.btn_track_down.clicked.connect(lambda: self.move_track_row(1))
        order_row.addWidget(self.btn_track_up)
        order_row.addWidget(self.btn_track_down)
        order_row.addStretch(1)
        layout.addLayout(order_row)
        return tab

    def build_intro_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.intro_tabs = QTabWidget()
        self.intro_tabs.addTab(self.build_intro_text_tab(), "Texto")
        self.intro_tabs.addTab(self.build_intro_font_tab(), "Fonte")
        self.intro_tabs.addTab(self.build_intro_effect_tab(), "Efeito")
        self.intro_tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(self.intro_tabs)
        return tab

    def build_intro_text_tab(self) -> QWidget:
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
            ("Limpar", self.clear_intro_rows),
        ):
            btn = ActionButton(text, "ghost", 84)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addStretch(1)
        return tab

    def build_intro_font_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        form = QGridLayout()
        setup_form(form)
        self.intro_font = combo_fontes("Georgia")
        self.intro_font_size = QSpinBox(); self.intro_font_size.setRange(8, 180); self.intro_font_size.setValue(48)
        self.intro_font_weight = QSpinBox(); self.intro_font_weight.setRange(100, 900); self.intro_font_weight.setSingleStep(50); self.intro_font_weight.setValue(700)
        self.intro_color = ColorSwatch("#FFFFFF")
        self.intro_opacity = DecimalSlider(0.05, 1.0, 0.05, 0.90)
        self.intro_pos = combo_posicao("inferior_esquerda")
        self.intro_mx = QSpinBox(); self.intro_mx.setRange(0, 800); self.intro_mx.setValue(90)
        self.intro_my = QSpinBox(); self.intro_my.setRange(0, 800); self.intro_my.setValue(120)
        self.intro_shadow_color = ColorSwatch("#000000")
        self.intro_shadow_enabled = ToggleSwitch("Sombra do texto")
        self.intro_shadow_enabled.setChecked(True)
        self.intro_shadow_size = DecimalSlider(0.0, 20.0, 1.0, 2.0, decimals=0, suffix=" px")
        self.intro_shadow_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.65)
        self.intro_background_box = ToggleSwitch("Fundo do texto")
        self.intro_background_color = ColorSwatch("#000000")
        self.intro_box_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.35)
        self.intro_background_padding = DecimalSlider(0.0, 40.0, 1.0, 6.0, decimals=0)

        add_row(form, 0, "Posição", self.intro_pos)
        add_row(form, 1, "Margens", margins_widget(self.intro_mx, self.intro_my))
        add_row(form, 2, "Fonte", self.font_inline_row(self.intro_font, self.intro_font_size, self.intro_color))
        add_row(form, 3, "Peso", self.intro_font_weight)
        add_row(form, 4, "Opacidade", self.intro_opacity)
        add_row(form, 5, "Sombra do texto", self.toggle_color_row(self.intro_shadow_enabled, self.intro_shadow_color))
        add_row(form, 6, "Tam. sombra", self.intro_shadow_size)
        add_row(form, 7, "Opac. sombra", self.intro_shadow_opacity)
        add_row(form, 8, "Fundo do texto", self.toggle_color_row(self.intro_background_box, self.intro_background_color))
        add_row(form, 9, "Tam. fundo", self.intro_background_padding)
        add_row(form, 10, "Opac. fundo", self.intro_box_opacity)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def build_intro_effect_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        form = QGridLayout()
        setup_form(form)
        self.intro_eff = QComboBox()
        self.intro_eff.addItems(["typewriter", "fade", "direct", "typewriter_fade"])
        set_input_width(self.intro_eff)
        self.intro_delay = QDoubleSpinBox(); self.intro_delay.setRange(0, 120); self.intro_delay.setSuffix(" s")
        self.intro_delay.setToolTip("Define quantos segundos a música principal espera antes de começar.")
        self.intro_randomize = ToggleSwitch("Escolher frases aleatórias")
        self.intro_random_count = QSpinBox(); self.intro_random_count.setRange(1, 99); self.intro_random_count.setValue(3)
        self.intro_audio = PathPicker("file", "Áudios (*.wav *.mp3);;Todos (*.*)", "Áudio de digitação opcional")
        self.intro_typing_volume = QDoubleSpinBox(); self.intro_typing_volume.setRange(0, 1); self.intro_typing_volume.setSingleStep(0.05); self.intro_typing_volume.setValue(0.30)
        self.intro_typing_cps = QDoubleSpinBox(); self.intro_typing_cps.setRange(1, 120); self.intro_typing_cps.setValue(18.0); self.intro_typing_cps.setSuffix(" car/s")
        self.intro_backspace_cps = QDoubleSpinBox(); self.intro_backspace_cps.setRange(1, 120); self.intro_backspace_cps.setValue(22.0); self.intro_backspace_cps.setSuffix(" car/s")
        self.intro_show_cursor = ToggleSwitch("Cursor piscando")
        self.intro_show_cursor.setChecked(True)
        self.intro_backspace_audio = ToggleSwitch("Som no backspace")
        self.intro_backspace_audio.setChecked(True)
        add_row(form, 0, "Efeito", self.intro_eff)
        add_row(form, 1, "Música após", self.intro_delay)
        add_wide(form, 2, self.intro_randomize)
        add_row(form, 3, "Qtd. aleatória", self.intro_random_count)
        add_row(form, 4, "Som teclado", self.intro_audio)
        add_row(form, 5, "Volume", self.intro_typing_volume)
        add_row(form, 6, "Digitação", self.intro_typing_cps)
        add_row(form, 7, "Backspace", self.intro_backspace_cps)
        add_wide(form, 8, self.intro_show_cursor)
        add_wide(form, 9, self.intro_backspace_audio)
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
        self.wm_color = ColorSwatch("#FFFFFF")
        self.wm_opacity = DecimalSlider(0.05, 1.0, 0.05, 0.70)
        self.wm_pos = combo_posicao("inferior_direita")
        self.wm_mx = QSpinBox(); self.wm_mx.setRange(0, 800); self.wm_mx.setValue(45)
        self.wm_my = QSpinBox(); self.wm_my.setRange(0, 800); self.wm_my.setValue(42)
        self.wm_shadow_color = ColorSwatch("#000000")
        self.wm_shadow_enabled = ToggleSwitch("Sombra do texto")
        self.wm_shadow_enabled.setChecked(True)
        self.wm_shadow = DecimalSlider(0.0, 1.0, 0.05, 0.60)
        self.wm_shadow_size = DecimalSlider(0.0, 20.0, 1.0, 2.0, decimals=0, suffix=" px")
        self.wm_background_box = ToggleSwitch("Fundo do texto")
        self.wm_background_color = ColorSwatch("#000000")
        self.wm_background_opacity = DecimalSlider(0.0, 1.0, 0.05, 0.35)
        self.wm_background_padding = DecimalSlider(0.0, 40.0, 1.0, 6.0, decimals=0)
        add_wide(form, 0, self.wm_enabled)
        add_row(form, 1, "Tipo", self.wm_mode)
        self.wm_text_label = add_row(form, 2, "Texto", self.wm_text)
        self.wm_preview_label = add_row(form, 2, "Preview", self.wm_image_preview)
        add_row(form, 3, "Imagem", self.wm_img)
        add_row(form, 4, "Largura img.", self.wm_width)
        add_row(form, 5, "Posição", self.wm_pos)
        add_row(form, 6, "Margens", margins_widget(self.wm_mx, self.wm_my))
        add_row(form, 7, "Fonte", self.font_inline_row(self.wm_font, self.wm_font_size, self.wm_color))
        add_row(form, 8, "Opacidade", self.wm_opacity)
        add_row(form, 9, "Sombra do texto", self.toggle_color_row(self.wm_shadow_enabled, self.wm_shadow_color))
        add_row(form, 10, "Tam. sombra", self.wm_shadow_size)
        add_row(form, 11, "Opac. sombra", self.wm_shadow)
        add_row(form, 12, "Fundo do texto", self.toggle_color_row(self.wm_background_box, self.wm_background_color))
        add_row(form, 13, "Tam. fundo", self.wm_background_padding)
        add_row(form, 14, "Opac. fundo", self.wm_background_opacity)
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
        self.set_crossfade_s = QDoubleSpinBox(); self.set_crossfade_s.setRange(0, 30); self.set_crossfade_s.setSingleStep(0.5); self.set_crossfade_s.setSuffix(" s")
        self.set_silence_s = QDoubleSpinBox(); self.set_silence_s.setRange(0, 30); self.set_silence_s.setSingleStep(0.5); self.set_silence_s.setSuffix(" s")
        self.set_norm = ToggleSwitch("Normalizar loudness")
        self.set_norm.setChecked(True)
        self.set_lufs = QDoubleSpinBox(); self.set_lufs.setRange(-40, 0); self.set_lufs.setValue(-14)
        self.set_peak = QDoubleSpinBox(); self.set_peak.setRange(-9, 0); self.set_peak.setValue(-1)
        add_wide(form, 0, self.set_fadein)
        add_row(form, 1, "Duração in", self.set_fadein_s)
        add_wide(form, 2, self.set_fadeout)
        add_row(form, 3, "Duração out", self.set_fadeout_s)
        add_row(form, 4, "Crossfade", self.set_crossfade_s)
        add_row(form, 5, "Silêncio", self.set_silence_s)
        add_wide(form, 6, self.set_norm)
        add_row(form, 7, "Target LUFS", self.set_lufs)
        add_row(form, 8, "True peak", self.set_peak)
        layout.addWidget(centered_layout(form))
        layout.addStretch(1)
        return tab

    def font_inline_row(self, font_widget: QWidget, size_widget: QWidget, color_widget: ColorSwatch) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        size_widget.setFixedWidth(72)
        layout.addWidget(font_widget, 1)
        layout.addWidget(size_widget)
        layout.addWidget(color_widget)
        return box

    def toggle_color_row(self, toggle: ToggleSwitch, color_widget: ColorSwatch) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        toggle.setText("")
        toggle.setFixedSize(ToggleSwitch.TRACK_W, 26)
        layout.addWidget(toggle)
        layout.addStretch(1)
        layout.addWidget(color_widget)
        return box

    def zoom_inicial_para_tela(self) -> float:
        screen = QApplication.primaryScreen()
        if not screen:
            return 0.75
        area = screen.availableGeometry()
        largura = max(320, area.width() - 40)
        altura = max(260, area.height() - 40)
        return clamp_zoom(min(1.0, largura / BASE_WINDOW_WIDTH, altura / BASE_WINDOW_HEIGHT))

    def set_ui_zoom_percent(self, value: int, resize_window: bool = False):
        percent = max(int(UI_ZOOM_MIN * 100), min(int(UI_ZOOM_MAX * 100), int(value)))
        zoom = clamp_zoom(percent / 100.0)
        if hasattr(self, "ui_zoom_slider") and self.ui_zoom_slider.value() != percent:
            self.ui_zoom_slider.blockSignals(True)
            self.ui_zoom_slider.setValue(percent)
            self.ui_zoom_slider.blockSignals(False)
        if hasattr(self, "ui_zoom_label"):
            self.ui_zoom_label.setText(f"{percent}%")
        if abs(getattr(self, "ui_zoom", 1.0) - zoom) < 0.001 and not resize_window:
            return
        self.ui_zoom = zoom
        self.aplicar_zoom_interface(resize_window=resize_window)

    def _scale_layout(self, layout):
        if not layout:
            return
        if not hasattr(layout, "_base_margins"):
            margins = layout.contentsMargins()
            layout._base_margins = (margins.left(), margins.top(), margins.right(), margins.bottom())
            layout._base_spacing = layout.spacing()
        left, top, right, bottom = layout._base_margins
        layout.setContentsMargins(
            escala(left, self.ui_zoom, 0),
            escala(top, self.ui_zoom, 0),
            escala(right, self.ui_zoom, 0),
            escala(bottom, self.ui_zoom, 0),
        )
        if layout._base_spacing >= 0:
            layout.setSpacing(escala(layout._base_spacing, self.ui_zoom, 0))
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item and item.layout():
                self._scale_layout(item.layout())

    def aplicar_zoom_interface(self, resize_window: bool = False):
        zoom = self.ui_zoom
        self.setStyleSheet(STYLE_PRIME + zoom_stylesheet(zoom))
        self.setMinimumSize(escala(BASE_WINDOW_MIN_WIDTH, zoom, 700), escala(BASE_WINDOW_MIN_HEIGHT, zoom, 360))
        self._scale_layout(self.layout())
        if hasattr(self, "left_panel"):
            self.left_panel.setFixedWidth(escala(285, zoom, 150))
        if hasattr(self, "right_panel"):
            self.right_panel.setFixedWidth(escala(500, zoom, 260))

        height = escala(CONTROL_HEIGHT, zoom, 18)
        for child in self.findChildren(QWidget):
            if isinstance(child, ActionButton):
                child.setFixedHeight(height)
                width = escala(getattr(child, "base_width", 112), zoom, 48)
                if child.maximumWidth() < 16777215 and child.minimumWidth() == child.maximumWidth():
                    child.setFixedWidth(width)
                else:
                    child.setMinimumWidth(width)
            elif isinstance(child, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox)):
                child.setFixedHeight(height)
            elif isinstance(child, DecimalSlider):
                child.set_zoom(zoom)
            elif isinstance(child, ColorSwatch):
                child.set_zoom(zoom)
            elif isinstance(child, ToggleSwitch):
                child.set_zoom(zoom)
                if not child.text():
                    child.setFixedSize(escala(ToggleSwitch.TRACK_W, zoom, 20), escala(26, zoom, 16))
            elif isinstance(child, QSlider):
                child.setFixedHeight(height)

        if hasattr(self, "preview_volume_slider"):
            self.preview_volume_slider.setFixedWidth(escala(148, zoom, 72))
            self.preview_volume_label.setFixedWidth(escala(30, zoom, 24))
        if hasattr(self, "ui_zoom_label"):
            self.ui_zoom_label.setFixedWidth(escala(44, zoom, 28))
        if hasattr(self, "prog_bar"):
            self.prog_bar.setFixedHeight(escala(14, zoom, 7))
        if hasattr(self, "log_widget"):
            self.log_widget.setFixedHeight(escala(LOG_HEIGHT_OPEN, zoom, 120))
        if hasattr(self, "intro_table"):
            self.intro_table.setFixedHeight(escala(200, zoom, 110))
        if hasattr(self, "wm_image_preview"):
            self.wm_image_preview.setFixedHeight(escala(86, zoom, 44))
        if hasattr(self, "preview"):
            self.preview.setMinimumSize(escala(520, zoom, 260), escala(300, zoom, 150))
        if hasattr(self, "preview_group"):
            base_height = PREVIEW_HEIGHT_LOG_OPEN if hasattr(self, "log_widget") and self.log_widget.isVisible() else PREVIEW_HEIGHT_NORMAL
            self.set_preview_group_height(base_height)

        if resize_window:
            self.resize(escala(BASE_WINDOW_WIDTH, zoom, 760), escala(BASE_WINDOW_HEIGHT, zoom, 410))
        self.updateGeometry()

    def set_preview_group_height(self, height: int):
        scaled_height = escala(height, self.ui_zoom, 135)
        width = int(scaled_height * PREVIEW_ASPECT_RATIO)
        self.preview.setFixedSize(width, scaled_height)
        self.video_widget.setFixedSize(width, scaled_height)
        self.preview_group.setFixedWidth(width)

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
            preview_dir = PREVIEW_CACHE_DIR
            preview_dir.mkdir(parents=True, exist_ok=True)
            target = preview_dir / "preview_primeiro_frame.jpg"
            command = [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(target)]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, **criar_kwargs_subprocess_controlado())
            pixmap = QPixmap(str(target))
            self.preview_pixmap = pixmap if not pixmap.isNull() else None
            self.preview_status.setText("Primeiro frame do vídeo")
        except (OSError, subprocess.SubprocessError):
            self.preview_pixmap = None
            self.preview_status.setText("Não foi possível gerar preview")

    def update_preview(self):
        try:
            config = self.get_config_obj(validar=False)
        except (TypeError, ValueError):
            config = None
        self.extract_preview_frame(self.video_picker.path())
        if hasattr(self, "video_widget") and self.video_widget.isVisible():
            return
        self.preview.set_preview(self.preview_pixmap, config, self.selected_track_title())

    def set_preview_volume(self, value: int):
        volume = max(0.0, min(1.0, value / 20.0))
        self.preview_audio.setVolume(volume)
        self.preview_volume_label.setText(f"{value * 5}%")
        self.trigger_autosave()

    def show_static_preview(self):
        self.video_player.stop()
        self.video_player.setSource(QUrl())
        self.video_widget.hide()
        self.preview.show()
        self.btn_pre_render.setText("Preview")
        self.update_preview()

    def play_preview_video(self, video_path: Path):
        if not video_path.exists():
            return
        self.preview.hide()
        self.video_widget.show()
        self.video_player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.video_player.play()
        self.btn_pre_render.setText("Parar")

    def try_play_pre_render(self):
        if self.render_mode != "pre_render" or not self.pre_render_path:
            self.preview_play_timer.stop()
            return
        if self.video_widget.isVisible():
            return
        try:
            if self.pre_render_path.exists() and self.pre_render_path.stat().st_size > 4096:
                self.play_preview_video(self.pre_render_path)
        except OSError:
            return

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
            except OSError as exc:
                print(f"Erro ao resolver áudio de fundo: {exc}")
        return sorted(files, key=natural_key)

    def get_track_titles(self) -> dict[str, str]:
        titles: dict[str, str] = {}
        if not hasattr(self, "track_titles_table"):
            return titles
        for row in range(self.track_titles_table.rowCount()):
            title_item = self.track_titles_table.item(row, 0)
            file_name = str(title_item.data(Qt.UserRole) if title_item else "").strip()
            title = (title_item.text() if title_item else "").strip()
            if file_name and title:
                titles[file_name] = title
        return titles

    def get_track_order(self) -> list[str]:
        if not hasattr(self, "track_titles_table"):
            return []
        order = []
        for row in range(self.track_titles_table.rowCount()):
            item = self.track_titles_table.item(row, 0)
            file_name = str(item.data(Qt.UserRole) if item else "").strip()
            if file_name:
                order.append(file_name)
        return order

    def selected_track_title(self) -> str:
        if not hasattr(self, "track_titles_table"):
            return ""
        item = self.track_titles_table.currentItem()
        return (item.text() if item else "").strip()

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
            shadow_enabled=self.font_titles_shadow_enabled.isChecked(),
            shadow_color=limpar_hex(self.font_titles_shadow_color.text(), "#000000"),
            shadow_opacity=self.font_titles_shadow.value(),
            shadow_size=self.font_titles_shadow_size.value(),
            background_box=self.font_titles_background_box.isChecked(),
            background_color=limpar_hex(self.font_titles_background_color.text(), "#000000"),
            background_opacity=self.font_titles_background_opacity.value(),
            background_padding=self.font_titles_background_padding.value(),
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
            shadow_enabled=self.wm_shadow_enabled.isChecked(),
            shadow_color=limpar_hex(self.wm_shadow_color.text(), "#000000"),
            shadow_opacity=self.wm_shadow.value(),
            shadow_size=self.wm_shadow_size.value(),
            background_box=self.wm_background_box.isChecked(),
            background_color=limpar_hex(self.wm_background_color.text(), "#000000"),
            background_opacity=self.wm_background_opacity.value(),
            background_padding=self.wm_background_padding.value(),
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
            shadow_enabled=self.intro_shadow_enabled.isChecked(),
            shadow_color=limpar_hex(self.intro_shadow_color.text(), "#000000"),
            shadow_opacity=self.intro_shadow_opacity.value(),
            shadow_size=self.intro_shadow_size.value(),
            background_box=self.intro_background_box.isChecked(),
            background_color=limpar_hex(self.intro_background_color.text(), "#000000"),
            box_opacity=self.intro_box_opacity.value(),
            background_padding=self.intro_background_padding.value(),
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
            crossfade_seconds=self.set_crossfade_s.value(),
            silence_seconds=self.set_silence_s.value(),
            normalizacao=NormalizacaoConfig(
                enabled=self.set_norm.isChecked(),
                target_lufs=self.set_lufs.value(),
                true_peak=self.set_peak.value(),
            ),
            fonte_texto=title_font,
            track_titles=self.get_track_titles(),
            track_order=self.get_track_order(),
            watermark=watermark,
            intro=intro,
        )

    def current_config_data(self) -> dict:
        cfg = self.get_config_obj(validar=False)
        return {
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
                "crossfade_seconds": cfg.crossfade_seconds,
                "silence_seconds": cfg.silence_seconds,
            },
            "normalizacao": asdict(cfg.normalizacao),
            "preview": {
                "volume": self.preview_volume_slider.value() / 20.0,
            },
            "ui": {
                "zoom": self.ui_zoom_slider.value() / 100.0,
            },
            "fonte_texto": asdict(cfg.fonte_texto),
            "titulos_musicas": cfg.track_titles,
            "ordem_musicas": cfg.track_order,
            "watermark": asdict(cfg.watermark),
            "intro": intro_config_to_dict(cfg.intro),
        }

    def save_config(self):
        try:
            salvar_config(self.current_config_data())
        except (OSError, TypeError, ValueError) as exc:
            print(f"Erro ao salvar config: {exc}")

    def load_config(self):
        data = carregar_config()
        self.apply_config_data(data)

    def apply_config_data(self, data: dict):
        self._config_loading = True
        try:
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
                self.set_crossfade_s.setValue(float(render.get("crossfade_seconds", 0.0)))
                self.set_silence_s.setValue(float(render.get("silence_seconds", 0.0)))

                norm = data.get("normalizacao", {})
                if self.normalizacao_config_antiga_zerada(str(data.get("app_version", "")), norm):
                    self.set_norm.setChecked(True)
                    self.set_lufs.setValue(-14.0)
                    self.set_peak.setValue(-1.0)
                else:
                    self.set_norm.setChecked(bool(norm.get("enabled", True)))
                    self.set_lufs.setValue(float(norm.get("target_lufs", -14.0)))
                    self.set_peak.setValue(float(norm.get("true_peak", -1.0)))

                preview = data.get("preview", {})
                self.preview_volume_slider.setValue(int(float(preview.get("volume", 1.0)) * 20))

                ui = data.get("ui", {})
                if "zoom" in ui:
                    self._zoom_loaded = True
                    self.set_ui_zoom_percent(int(round(float(ui.get("zoom", 1.0)) * 100)), resize_window=True)

                self.apply_title_config(FonteTextoConfig(**{k: v for k, v in data.get("fonte_texto", {}).items() if k in FonteTextoConfig.__dataclass_fields__}))
                self.refresh_track_titles_table(data.get("titulos_musicas", {}), data.get("ordem_musicas", []))
                self.apply_watermark_config(WatermarkConfig(**{k: v for k, v in data.get("watermark", {}).items() if k in WatermarkConfig.__dataclass_fields__}))
                self.apply_intro_config(intro_config_from_dict(data.get("intro", {})))
        finally:
            self._config_loading = False

    def record_undo_snapshot(self, force: bool = False):
        if not self._ui_ready or self._config_loading or self._undo_restoring:
            return
        try:
            data = json.loads(json.dumps(self.current_config_data(), ensure_ascii=False, default=str))
            key = json.dumps(data, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            print(f"Erro ao registrar undo: {exc}")
            return

        if not force and key == self._last_undo_snapshot:
            return

        self._undo_stack.append({"key": key, "data": data})
        if len(self._undo_stack) > 80:
            self._undo_stack = self._undo_stack[-80:]
        self._last_undo_snapshot = key

    def undo_last_change(self):
        if self.worker and self.worker.isRunning():
            return

        self.record_undo_snapshot()
        if len(self._undo_stack) < 2:
            return

        self._undo_stack.pop()
        snapshot = self._undo_stack[-1]
        self._undo_restoring = True
        try:
            self.apply_config_data(snapshot["data"])
            self._last_undo_snapshot = snapshot["key"]
            self.save_config()
            self.update_preview()
            self.lbl_status.setText("Alteração desfeita")
        finally:
            self._undo_restoring = False

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
        self.font_titles_shadow_enabled.setChecked(bool(getattr(cfg, "shadow_enabled", True)))
        self.font_titles_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.font_titles_shadow.setValue(float(cfg.shadow_opacity))
        self.font_titles_shadow_size.setValue(float(getattr(cfg, "shadow_size", 2.0)))
        self.font_titles_background_box.setChecked(bool(getattr(cfg, "background_box", False)))
        self.font_titles_background_color.setText(getattr(cfg, "background_color", "#000000"))
        self.font_titles_background_opacity.setValue(float(getattr(cfg, "background_opacity", 0.35)))
        self.font_titles_background_padding.setValue(float(getattr(cfg, "background_padding", 6.0)))

    def refresh_track_titles_table(self, existing_titles: dict | None = None, existing_order: list[str] | None = None):
        current_titles = self.get_track_titles()
        if isinstance(existing_titles, dict):
            current_titles.update({str(k): str(v) for k, v in existing_titles.items()})
        files = self.music_files_from_folder()
        order = [str(item) for item in (existing_order or self.get_track_order()) if str(item).strip()]
        if order:
            order_map = {name: index for index, name in enumerate(order)}
            files = sorted(files, key=lambda path: (order_map.get(path.name, len(order_map)), natural_key(path)))
        selected_file = ""
        selected_item = self.track_titles_table.currentItem()
        if selected_item:
            selected_file = str(selected_item.data(Qt.UserRole) or "")
        self.track_titles_table.blockSignals(True)
        self.track_titles_table.setRowCount(0)
        selected_row = 0
        for file in files:
            row = self.track_titles_table.rowCount()
            self.track_titles_table.insertRow(row)
            title_item = QTableWidgetItem(current_titles.get(file.name, limpar_titulo_musica(file)))
            title_item.setData(Qt.UserRole, file.name)
            self.track_titles_table.setItem(row, 0, title_item)
            if file.name == selected_file:
                selected_row = row
        self.track_titles_table.blockSignals(False)
        if files:
            self.track_titles_table.selectRow(selected_row)
        self.trigger_autosave()

    def move_track_row(self, offset: int):
        row = self.track_titles_table.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.track_titles_table.rowCount():
            return
        item = self.track_titles_table.takeItem(row, 0)
        self.track_titles_table.removeRow(row)
        self.track_titles_table.insertRow(target)
        self.track_titles_table.setItem(target, 0, item)
        self.track_titles_table.selectRow(target)
        self.trigger_autosave()
        self.update_preview()

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
        self.wm_shadow_enabled.setChecked(bool(getattr(cfg, "shadow_enabled", True)))
        self.wm_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.wm_shadow.setValue(float(cfg.shadow_opacity))
        self.wm_shadow_size.setValue(float(getattr(cfg, "shadow_size", 2.0)))
        self.wm_background_box.setChecked(bool(getattr(cfg, "background_box", False)))
        self.wm_background_color.setText(getattr(cfg, "background_color", "#000000"))
        self.wm_background_opacity.setValue(float(getattr(cfg, "background_opacity", 0.35)))
        self.wm_background_padding.setValue(float(getattr(cfg, "background_padding", 6.0)))
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
        self.intro_shadow_enabled.setChecked(bool(getattr(cfg, "shadow_enabled", True)))
        self.intro_shadow_color.setText(getattr(cfg, "shadow_color", "#000000"))
        self.intro_shadow_size.setValue(float(cfg.shadow_size))
        self.intro_shadow_opacity.setValue(float(cfg.shadow_opacity))
        self.intro_background_box.setChecked(bool(cfg.background_box))
        self.intro_background_color.setText(getattr(cfg, "background_color", "#000000"))
        self.intro_box_opacity.setValue(float(cfg.box_opacity))
        self.intro_background_padding.setValue(float(getattr(cfg, "background_padding", 6.0)))
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

    def apply_preview_drag_position(self, kind: str, position: str, margin_x: int, margin_y: int):
        if kind == "title":
            self.set_combo_data(self.font_titles_pos, position)
            self.font_titles_mx.setValue(margin_x)
            self.font_titles_my.setValue(margin_y)
        elif kind == "intro":
            self.set_combo_data(self.intro_pos, position)
            self.intro_mx.setValue(margin_x)
            self.intro_my.setValue(margin_y)
        elif kind == "watermark":
            self.set_combo_data(self.wm_pos, position)
            self.wm_mx.setValue(margin_x)
            self.wm_my.setValue(margin_y)
        self.trigger_autosave()
        self.update_preview()

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

    def clear_intro_rows(self):
        self.intro_table.setRowCount(0)
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
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
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
            elif isinstance(child, ColorSwatch):
                child.colorChanged.connect(self.trigger_autosave)
        self.intro_table.itemChanged.connect(self.trigger_autosave)
        self.track_titles_table.itemChanged.connect(self.trigger_autosave)
        self.track_titles_table.itemSelectionChanged.connect(self.update_preview)

    def trigger_autosave(self, *args):
        if not self._ui_ready or self._config_loading:
            return
        self.record_undo_snapshot()
        self.autosave_timer.start()
        self.preview_timer.start()

    def update_watermark_mode(self, text: str):
        image_mode = text == "Imagem"
        self.wm_text_label.setVisible(not image_mode)
        self.wm_text.setVisible(not image_mode)
        self.wm_preview_label.setVisible(image_mode)
        self.wm_image_preview.setVisible(image_mode)
        self.wm_font.setEnabled(not image_mode)
        self.wm_font_size.setEnabled(not image_mode)
        self.wm_color.setEnabled(not image_mode)
        self.wm_shadow_enabled.setEnabled(not image_mode)
        self.wm_shadow_color.setEnabled(not image_mode)
        self.wm_shadow.setEnabled(not image_mode)
        self.wm_shadow_size.setEnabled(not image_mode)
        self.wm_background_box.setEnabled(not image_mode)
        self.wm_background_color.setEnabled(not image_mode)
        self.wm_background_opacity.setEnabled(not image_mode)
        self.wm_background_padding.setEnabled(not image_mode)
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
        preview_height = PREVIEW_HEIGHT_LOG_OPEN if visible else PREVIEW_HEIGHT_NORMAL
        self.set_preview_group_height(preview_height)
        self.preview_group.updateGeometry()
        self.preview.updateGeometry()
        self.video_widget.updateGeometry()
        self.center_panel.updateGeometry()

    def start_render(self, pre_render=False):
        if self.worker and self.worker.isRunning():
            return
        try:
            config = self.get_config_obj(validar=True)
            self.save_config()
        except (ErroRender, OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Configuração incompleta", str(exc))
            return
        self.log_widget.clear()
        self.prog_bar.setValue(0)
        self.ultimo_video = None
        self.render_mode = "pre_render" if pre_render else "final"
        self.lbl_status.setText("Iniciando preview" if pre_render else "Iniciando exportação")
        if pre_render:
            limpar_pre_render()
            PRE_RENDER_DIR.mkdir(parents=True, exist_ok=True)
            config.output_folder = PRE_RENDER_DIR
            self.pre_render_path = PRE_RENDER_DIR / "preview.mp4"
            config.output_path_override = self.pre_render_path
            self.show_static_preview()
            self.btn_pre_render.setText("Parar")
            self.btn_start.setEnabled(False)
            self.preview_play_timer.start()
        else:
            self.pre_render_path = None
            self.btn_start.setText("Cancelar")
            self.btn_start.setEnabled(True)
            self.btn_pre_render.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.worker = WorkerRender(config, modo="pre_render" if pre_render else "final")
        self.worker.log.connect(self.log_msg)
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.etapa.connect(self.lbl_status.setText)
        self.worker.terminado.connect(self.finalizar_render)
        self.worker.start()

    def export_toggle(self):
        if self.worker and self.worker.isRunning():
            if self.render_mode == "final":
                self.cancelar_render()
        else:
            self.start_render(pre_render=False)

    def pre_render_toggle(self):
        if self.worker and self.worker.isRunning() and self.render_mode == "pre_render":
            self.cancelar_render()
            return
        if self.worker and self.worker.isRunning():
            return
        if self.video_widget.isVisible():
            self.show_static_preview()
            self.preview_play_timer.stop()
            self.pre_render_path = None
            limpar_pre_render()
            self.lbl_status.setText("Preview parado")
            return
        self.start_render(pre_render=True)

    def cancelar_render(self):
        if not self.worker or not self.worker.isRunning():
            return
        self.lbl_status.setText("Cancelando")
        self.btn_cancel.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_pre_render.setEnabled(False)
        self.log_msg("\nCancelamento solicitado. Encerrando FFmpeg e removendo arquivo incompleto...\n")
        self.worker.cancelar()

    def atualizar_progresso(self, value: int):
        self.prog_bar.setValue(max(0, min(100, int(value))))

    def finalizar_render(self, sucesso: bool, mensagem: str, caminho_saida: str):
        self.btn_start.setText("Exportar")
        self.btn_start.setEnabled(True)
        self.btn_pre_render.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if sucesso:
            caminho_render = Path(caminho_saida)
            self.prog_bar.setValue(100)
            self.lbl_status.setText("Finalizado com sucesso")
            if self.render_mode == "pre_render":
                self.preview_play_timer.stop()
                self.play_preview_video(caminho_render)
            else:
                self.ultimo_video = caminho_render
                QMessageBox.information(self, "Finalizado", f"{mensagem}\n\n{caminho_saida}")
        else:
            self.prog_bar.setValue(0)
            self.lbl_status.setText("Cancelado" if "cancel" in mensagem.lower() else "Erro")
            if self.render_mode == "pre_render":
                self.preview_play_timer.stop()
                limpar_pre_render()
                self.show_static_preview()
            if "cancel" in mensagem.lower():
                if self.render_mode != "pre_render":
                    QMessageBox.information(self, "Cancelado", mensagem)
            else:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                log_path = LOG_DIR / "erro_ffmpeg_log.txt"
                try:
                    log_path.write_text(mensagem, encoding="utf-8", errors="ignore")
                except OSError as exc:
                    print(f"Erro ao salvar log de render: {exc}")
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
            folder = gerar_pasta_saida_padrao()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except (OSError, subprocess.SubprocessError) as exc:
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
    if APP_ICON.exists():
        app.setWindowIcon(QIcon(str(APP_ICON)))
    app.setStyle("Fusion")
    window = MainUI()
    window.show()
    sys.exit(app.exec())
