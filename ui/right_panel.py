# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QTabWidget, QVBoxLayout

class RightPanel(QFrame):
    def __init__(self, ui):
        super().__init__()
        self.setObjectName("RightPanel")
        self.setFixedWidth(500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)
        title = QLabel("Ajustes de legenda")
        title.setObjectName("ColumnTitle")
        layout.addWidget(title)

        ui.tabs = QTabWidget()
        ui.tabs.addTab(ui.build_music_tab(), "Músicas")
        ui.tabs.addTab(ui.build_intro_tab(), "Frases")
        ui.tabs.addTab(ui.build_watermark_tab(), "Marca")
        ui.tabs.addTab(ui.build_audio_tab(), "Áudio")
        ui.tabs.tabBar().setUsesScrollButtons(False)
        layout.addWidget(ui.tabs, 1)
