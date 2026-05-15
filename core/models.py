# -*- coding: utf-8 -*-
from __future__ import annotations

"""Modelos de configuracao usados pela UI e pelo render."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FonteTextoConfig:
    font_family: str = "Georgia"
    font_size: int = 34
    color: str = "#FFFFFF"
    opacity: float = 0.93
    margin_x: int = 45
    margin_y: int = 980
    typing_duration: float = 2.2
    erasing_duration: float = 1.6
    shadow_enabled: bool = True
    shadow_color: str = "#000000"
    shadow_opacity: float = 0.60
    shadow_size: float = 2.0
    background_box: bool = False
    background_color: str = "#000000"
    background_opacity: float = 0.35
    background_padding: float = 6.0


@dataclass
class WatermarkConfig:
    enabled: bool = True
    # "texto" ou "imagem".
    mode: str = "texto"
    text: str = "⚓"
    image_path: str = ""
    image_width: int = 180
    font_family: str = "Segoe UI Symbol"
    font_size: int = 44
    color: str = "#FFFFFF"
    opacity: float = 0.70
    margin_x: int = 1695
    margin_y: int = 950
    shadow_enabled: bool = True
    shadow_color: str = "#000000"
    shadow_opacity: float = 0.60
    shadow_size: float = 2.0
    background_box: bool = False
    background_color: str = "#000000"
    background_opacity: float = 0.35
    background_padding: float = 6.0


@dataclass
class IntroFraseConfig:
    inicio: float = 0.0
    duracao: float = 4.0
    texto: str = "take a slow breath..."


@dataclass
class IntroTextConfig:
    enabled: bool = False
    phrases: list[IntroFraseConfig] = field(default_factory=lambda: [
        IntroFraseConfig(0.0, 4.0, "take a slow breath..."),
        IntroFraseConfig(5.0, 4.0, "let the rain carry the noise away."),
        IntroFraseConfig(10.0, 5.0, "welcome to a quiet little journey."),
    ])
    effect: str = "typewriter"  # typewriter, fade, direct, typewriter_fade
    typing_audio_path: str = ""
    typing_volume: float = 0.30
    typing_cps: float = 18.0
    backspace_cps: float = 22.0
    backspace_audio_enabled: bool = True
    show_cursor: bool = True
    randomize_phrases: bool = False
    random_count: int = 3
    delay_music_seconds: float = 0.0
    font_family: str = "Georgia"
    font_size: int = 48
    font_weight: int = 700
    color: str = "#FFFFFF"
    opacity: float = 0.92
    margin_x: int = 90
    margin_y: int = 900
    shadow_enabled: bool = True
    shadow_color: str = "#000000"
    shadow_opacity: float = 0.65
    shadow_size: float = 2.0
    background_box: bool = False
    background_color: str = "#000000"
    box_opacity: float = 0.35
    background_padding: float = 6.0


@dataclass
class NormalizacaoConfig:
    enabled: bool = True
    target_lufs: float = -14.0
    true_peak: float = -1.0
    loudness_range: float = 11.0


@dataclass
class RenderConfig:
    video_path: Path
    music_folder: Path
    background_audio_path: Path | None
    output_folder: Path
    output_path_override: Path | None = None
    use_gpu: bool = True
    use_fade_in: bool = True
    use_fade_out: bool = True
    fade_in_seconds: float = 3.0
    fade_out_seconds: float = 3.0
    background_volume: float = 0.30
    crossfade_seconds: float = 0.0
    silence_seconds: float = 0.0
    normalizacao: NormalizacaoConfig = field(default_factory=NormalizacaoConfig)
    fonte_texto: FonteTextoConfig = field(default_factory=FonteTextoConfig)
    track_titles: dict[str, str] = field(default_factory=dict)
    track_order: list[str] = field(default_factory=list)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    intro: IntroTextConfig = field(default_factory=IntroTextConfig)


@dataclass
class TrackInfo:
    arquivo: Path
    titulo: str
    inicio: float
    fim: float
    duracao: float
