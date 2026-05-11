# -*- coding: utf-8 -*-
from __future__ import annotations

"""Limpeza de arquivos temporarios e cache."""

import logging
import shutil
import time
from pathlib import Path

from .constants import CACHE_DIR, LEGACY_TEMP_DIR, PRE_RENDER_DIR, TEMP_DIR

LOGGER = logging.getLogger(__name__)


def remover_arquivo_ou_pasta(caminho: Path):
    try:
        if caminho.is_dir():
            shutil.rmtree(caminho)
        elif caminho.exists():
            caminho.unlink()
    except OSError as exc:
        LOGGER.debug("Falha ao remover %s: %s", caminho, exc)


def limpar_cache_antigo(dias: int = 7):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    limite = time.time() - (max(1, int(dias)) * 24 * 60 * 60)
    for item in CACHE_DIR.iterdir():
        try:
            if item.stat().st_mtime < limite:
                remover_arquivo_ou_pasta(item)
        except OSError as exc:
            LOGGER.debug("Falha ao inspecionar cache %s: %s", item, exc)
    if LEGACY_TEMP_DIR.exists():
        remover_arquivo_ou_pasta(LEGACY_TEMP_DIR)


def limpar_cache_render():
    remover_arquivo_ou_pasta(TEMP_DIR)


def limpar_pre_render():
    remover_arquivo_ou_pasta(PRE_RENDER_DIR)
