# -*- coding: utf-8 -*-
from __future__ import annotations

"""Constantes e caminhos base do TAURUS Video Maker."""

import os
import sys
from pathlib import Path

APP_VERSION = "8.0.75"


def obter_diretorio_aplicacao() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def obter_diretorio_recursos() -> Path:
    pacote_temporario = getattr(sys, "_MEIPASS", None)
    if pacote_temporario:
        return Path(pacote_temporario).resolve()
    return obter_diretorio_aplicacao()


def obter_appdata_local() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    if os.name == "nt":
        return Path.home() / "AppData" / "Local"
    return Path.home() / ".local" / "share"


def obter_desktop_usuario() -> Path:
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    if desktop.exists():
        return desktop
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop
    return Path.home()


SCRIPT_DIR = obter_diretorio_aplicacao()
RESOURCE_DIR = obter_diretorio_recursos()
APP_DATA_DIR = obter_appdata_local() / "TAURUS_VideoMaker"
CACHE_DIR = APP_DATA_DIR / "cache"
FFMPEG_BIN = RESOURCE_DIR / "ffmpeg" / "bin"
TEMP_DIR = CACHE_DIR / "render"
PREVIEW_CACHE_DIR = CACHE_DIR / "preview"
LOG_DIR = APP_DATA_DIR / "logs"
SETTINGS_INI_PATH = APP_DATA_DIR / "settings.ini"
PRE_RENDER_DIR = CACHE_DIR / "pre_render"
LEGACY_TEMP_DIR = SCRIPT_DIR / "_temp_audio_processado"
LEGACY_CONFIG_JSON_PATH = SCRIPT_DIR / "video_creator_config.json"

FFMPEG = FFMPEG_BIN / "ffmpeg.exe"
FFPROBE = FFMPEG_BIN / "ffprobe.exe"
APP_ICON = RESOURCE_DIR / "img" / "anchor_media_editor_windows_multi_size.ico"

EXTENSOES_AUDIO = [
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"
]

EXTENSOES_VIDEO = [
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".gif"
]

EXTENSOES_IMAGEM = [
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
]

# Pesos da barra de progresso total.
PESO_PROCESSAR_AUDIOS = 1.0
PESO_CONCATENAR = 0.3
PESO_NORMALIZAR_ANALISE = 0.7
PESO_NORMALIZAR_APLICAR = 1.0
PESO_MONTAR = 3.0

NVENC_CQ = "18"
NVENC_PRESET = "slow"
NVENC_MAXRATE = "30M"
NVENC_BUFSIZE = "60M"

FINAL_RENDER_SIZE = (1920, 1080)
PRE_RENDER_SIZE = (960, 540)
PRE_RENDER_VISUAL_SCALE = PRE_RENDER_SIZE[1] / FINAL_RENDER_SIZE[1]
