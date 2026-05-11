# -*- coding: utf-8 -*-
from __future__ import annotations

"""Utilitarios de texto, tempo e nomes de arquivos."""

import re
from datetime import datetime
from pathlib import Path

from .constants import obter_desktop_usuario

def segundos_para_ffmpeg(segundos: float) -> str:
    return f"{max(0.0, float(segundos)):.3f}"


def caminho_ou_vazio(caminho: Path | None) -> str:
    return str(caminho) if caminho else ""

def natural_key(path: Path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", path.name)]


def limpar_titulo_musica(arquivo: Path) -> str:
    titulo = arquivo.stem
    titulo = re.sub(r"^\s*\d+\s*[\._\-\)]\s*", "", titulo)
    titulo = titulo.replace("_", " ").replace("-", " ")
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo or arquivo.stem


def segundos_para_legivel(segundos: float) -> str:
    segundos = max(0, int(round(segundos)))
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def escape_drawtext(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def escape_fontfile(caminho) -> str:
    caminho = str(caminho).replace("\\", "/")
    caminho = caminho.replace(":", "\\:")
    caminho = caminho.replace("'", "\\'")
    return caminho


def limpar_hex(cor: str, fallback: str = "#FFFFFF") -> str:
    cor = (cor or "").strip()
    if not cor.startswith("#"):
        cor = "#" + cor
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", cor):
        return cor.upper()
    return fallback


def cor_drawtext(cor_hex: str, opacity: float) -> str:
    cor = limpar_hex(cor_hex).replace("#", "0x")
    opacity = max(0.0, min(1.0, float(opacity)))
    return f"{cor}@{opacity:.3f}"


def tamanho_sombra_drawtext(valor: float) -> int:
    return max(0, min(50, int(round(float(valor)))))


def boxborderw_texto(valor: float) -> str:
    padding = max(0, min(80, int(round(float(valor)))))
    topo = max(0, padding - 2)
    return f"{topo}|{padding}|{padding}|{padding}"


def opcoes_posicao():
    return [
        ("Inferior direita", "inferior_direita"),
        ("Inferior esquerda", "inferior_esquerda"),
        ("Inferior centro", "inferior_centro"),
        ("Superior direita", "superior_direita"),
        ("Superior esquerda", "superior_esquerda"),
        ("Superior centro", "superior_centro"),
        ("Centro", "centro"),
    ]


def popular_combo_posicoes(combo, valor_atual: str):
    for texto, valor in opcoes_posicao():
        combo.addItem(texto, valor)
    idx = combo.findData(valor_atual)
    combo.setCurrentIndex(max(0, idx))


def overlay_position_expr(position: str, margin_x: int, margin_y: int) -> tuple[str, str]:
    posicoes = {
        "inferior_direita": (f"W-w-{margin_x}", f"H-h-{margin_y}"),
        "inferior_esquerda": (f"{margin_x}", f"H-h-{margin_y}"),
        "inferior_centro": ("(W-w)/2", f"H-h-{margin_y}"),
        "superior_direita": (f"W-w-{margin_x}", f"{margin_y}"),
        "superior_esquerda": (f"{margin_x}", f"{margin_y}"),
        "superior_centro": ("(W-w)/2", f"{margin_y}"),
        "centro": ("(W-w)/2", "(H-h)/2"),
    }
    return posicoes.get(position, posicoes["inferior_direita"])


def gerar_nome_video(prefixo: str = "video_final") -> str:
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    prefixo = re.sub(r"[^A-Za-z0-9_\-]+", "_", prefixo or "video_final").strip("_") or "video_final"
    return f"{prefixo}_{data_hora}.mp4"


def gerar_pasta_saida_padrao() -> Path:
    return obter_desktop_usuario()
