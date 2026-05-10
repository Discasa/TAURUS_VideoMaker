# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QSlider, QVBoxLayout

from .common import ActionButton, PathPicker, ToggleSwitch, UI_ZOOM_MAX, UI_ZOOM_MIN, section

class LeftPanel(QFrame):
    def __init__(self, ui):
        super().__init__()
        self.setObjectName("LeftPanel")
        self.setFixedWidth(285)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        brand = QLabel("TAURUS Video Maker")
        brand.setObjectName("Brand")
        subtitle = QLabel("Fluxo do projeto")
        subtitle.setObjectName("Subtle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)

        media, media_layout = section("Arquivos de entrada")
        ui.video_picker = PathPicker("file", "Mídia visual (*.mp4 *.mov *.mkv *.avi *.webm *.gif *.png *.jpg *.jpeg *.webp);;Todos (*.*)", "Vídeo, GIF ou imagem base")
        ui.music_picker = PathPicker("folder", placeholder="Pasta com músicas")
        media_layout.addWidget(QLabel("Visual base"))
        media_layout.addWidget(ui.video_picker)
        media_layout.addWidget(QLabel("Músicas"))
        media_layout.addWidget(ui.music_picker)
        layout.addWidget(media)

        output, output_layout = section("Saída")
        ui.out_picker = PathPicker("folder", placeholder="Automática: Área de Trabalho")
        ui.btn_open_output = ActionButton("Abrir pasta", "ghost")
        ui.btn_open_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ui.btn_open_output.clicked.connect(ui.abrir_pasta_saida)
        output_layout.addWidget(ui.out_picker)
        output_layout.addWidget(ui.btn_open_output)
        layout.addWidget(output)

        render, render_layout = section("Renderização")
        ui.set_gpu = ToggleSwitch("Usar GPU NVIDIA/NVENC")
        ui.set_gpu.setChecked(True)
        render_note = QLabel("Se desabilitado, renderiza com CPU.")
        render_note.setObjectName("Subtle")
        zoom_row = QHBoxLayout()
        zoom_row.setContentsMargins(0, 0, 0, 0)
        zoom_row.setSpacing(6)
        ui.ui_zoom_slider = QSlider(Qt.Horizontal)
        ui.ui_zoom_slider.setRange(int(UI_ZOOM_MIN * 100), int(UI_ZOOM_MAX * 100))
        ui.ui_zoom_slider.setSingleStep(5)
        ui.ui_zoom_slider.setPageStep(10)
        ui.ui_zoom_slider.setValue(100)
        ui.ui_zoom_label = QLabel("100%")
        ui.ui_zoom_label.setObjectName("Subtle")
        ui.ui_zoom_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ui.ui_zoom_label.setFixedWidth(44)
        ui.ui_zoom_slider.valueChanged.connect(ui.set_ui_zoom_percent)
        zoom_row.addWidget(ui.ui_zoom_slider, 1)
        zoom_row.addWidget(ui.ui_zoom_label)
        render_layout.addWidget(ui.set_gpu)
        render_layout.addWidget(render_note)
        render_layout.addWidget(QLabel("Zoom da interface"))
        render_layout.addLayout(zoom_row)
        layout.addWidget(render)
        layout.addStretch(1)
