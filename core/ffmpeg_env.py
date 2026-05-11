# -*- coding: utf-8 -*-
from __future__ import annotations

"""Ambiente FFmpeg e fontconfig usado pelo drawtext."""

import logging
import os
import shutil
from pathlib import Path

from .constants import TEMP_DIR

LOGGER = logging.getLogger(__name__)

def caminho_pasta_fontes_windows() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("WINDIR", r"C:/Windows")) / "Fonts"
    return Path("/usr/share/fonts")


def preparar_pasta_fontes_ffmpeg() -> Path:
    """Cria uma pasta LIMPA só com fontes .ttf/.otf usadas pelo script.

    Não apontamos o subtitles/fontsdir direto para C:/Windows/Fonts porque essa pasta
    tem muitos arquivos antigos .fon/.dat. Algumas builds novas do FFmpeg/libass tentam
    ler esses arquivos e enchem o log com erros de metadata/charmap.
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    destino = TEMP_DIR / "fonts_ffmpeg"
    destino.mkdir(parents=True, exist_ok=True)

    if os.name != "nt":
        return destino

    origem = caminho_pasta_fontes_windows()
    nomes_fontes = [
        "georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf",
        "arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf",
        "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf",
        "seguisym.ttf",
    ]

    for nome in nomes_fontes:
        src = origem / nome
        dst = destino / nome
        try:
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
        except OSError as exc:
            LOGGER.debug("Falha ao copiar fonte %s para %s: %s", src, dst, exc)

    return destino


def criar_fontconfig_windows() -> Path | None:
    # Cria um fonts.conf mínimo apontando para a pasta limpa de fontes do script.
    if os.name != "nt":
        return None

    try:
        fontes = preparar_pasta_fontes_ffmpeg().as_posix()
        cache = (TEMP_DIR / "font_cache").as_posix()
        conf_path = TEMP_DIR / "fonts.conf"
        conf_text = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            f'  <dir>{fontes}</dir>\n'
            f'  <cachedir>{cache}</cachedir>\n'
            '</fontconfig>\n'
        )
        conf_path.write_text(conf_text, encoding="utf-8")
        return conf_path
    except OSError as exc:
        LOGGER.debug("Falha ao criar fontconfig temporario: %s", exc)
        return None


def criar_env_ffmpeg() -> dict:
    env = os.environ.copy()
    conf = criar_fontconfig_windows()
    if conf:
        env["FONTCONFIG_FILE"] = str(conf)
        env["FONTCONFIG_PATH"] = str(conf.parent)
    return env
