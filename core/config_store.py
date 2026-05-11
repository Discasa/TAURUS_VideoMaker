# -*- coding: utf-8 -*-
from __future__ import annotations

"""Persistencia de configuracoes em INI, com leitura legada do JSON antigo."""

import configparser
import json
import logging
from dataclasses import asdict, fields

from .constants import APP_DATA_DIR, APP_VERSION, LEGACY_CONFIG_JSON_PATH, SETTINGS_INI_PATH
from .models import (
    FonteTextoConfig,
    IntroFraseConfig,
    IntroTextConfig,
    NormalizacaoConfig,
    WatermarkConfig,
)

LOGGER = logging.getLogger(__name__)

def dataclass_from_dict(cls, dados: dict | None):
    if not isinstance(dados, dict):
        return cls()
    nomes_validos = {item.name for item in fields(cls)}
    filtrado = {chave: valor for chave, valor in dados.items() if chave in nomes_validos}
    try:
        return cls(**filtrado)
    except (TypeError, ValueError) as exc:
        LOGGER.debug("Config invalida para %s: %s", getattr(cls, "__name__", cls), exc)
        return cls()


def intro_config_from_dict(dados: dict | None) -> IntroTextConfig:
    cfg = dataclass_from_dict(IntroTextConfig, dados)
    frases = []
    if isinstance(dados, dict):
        for item in dados.get("phrases", []):
            if isinstance(item, dict):
                try:
                    frases.append(IntroFraseConfig(
                        inicio=float(item.get("inicio", item.get("start", 0.0))),
                        duracao=float(item.get("duracao", item.get("duration", 4.0))),
                        texto=str(item.get("texto", item.get("text", ""))),
                    ))
                except (TypeError, ValueError) as exc:
                    LOGGER.debug("Frase de intro invalida ignorada: %s", exc)
    if frases:
        cfg.phrases = frases
    return cfg


def intro_config_to_dict(cfg: IntroTextConfig) -> dict:
    dados = asdict(cfg)
    dados["phrases"] = [asdict(frase) for frase in cfg.phrases]
    return dados

def _config_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    return parser


def _valor_para_ini(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if valor is None:
        return ""
    return str(valor)


def _bool_ini(valor, padrao=False) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return bool(padrao)
    texto = str(valor).strip().lower()
    if texto in {"1", "true", "yes", "sim", "on"}:
        return True
    if texto in {"0", "false", "no", "nao", "não", "off"}:
        return False
    return bool(padrao)


def _int_ini(valor, padrao=0) -> int:
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return int(padrao)


def _float_ini(valor, padrao=0.0) -> float:
    try:
        return float(str(valor).strip())
    except (TypeError, ValueError):
        return float(padrao)


def _converter_ini(valor, padrao):
    if isinstance(padrao, bool):
        return _bool_ini(valor, padrao)
    if isinstance(padrao, int) and not isinstance(padrao, bool):
        return _int_ini(valor, padrao)
    if isinstance(padrao, float):
        return _float_ini(valor, padrao)
    return "" if valor is None else str(valor)


def _salvar_secao(parser: configparser.ConfigParser, nome: str, dados: dict):
    parser[nome] = {
        str(chave): _valor_para_ini(valor)
        for chave, valor in dados.items()
        if not isinstance(valor, (dict, list, tuple))
    }


def _carregar_secao(parser: configparser.ConfigParser, nome: str) -> dict:
    if not parser.has_section(nome):
        return {}
    return {chave: valor for chave, valor in parser.items(nome)}


def _carregar_dataclass(parser: configparser.ConfigParser, nome: str, cls) -> dict:
    if not parser.has_section(nome):
        return {}
    padrao = cls()
    dados = {}
    secao = parser[nome]
    for campo in fields(cls):
        if campo.name not in secao:
            continue
        valor_padrao = getattr(padrao, campo.name)
        if isinstance(valor_padrao, list):
            continue
        dados[campo.name] = _converter_ini(secao.get(campo.name), valor_padrao)
    return dados


def _salvar_titulos_musicas(parser: configparser.ConfigParser, titulos: dict):
    secao = {"count": str(len(titulos))}
    for indice, (arquivo, titulo) in enumerate(titulos.items()):
        prefixo = f"item_{indice:04d}"
        secao[f"{prefixo}_file"] = str(arquivo)
        secao[f"{prefixo}_title"] = str(titulo)
    parser["titulos_musicas"] = secao


def _carregar_titulos_musicas(parser: configparser.ConfigParser) -> dict[str, str]:
    if not parser.has_section("titulos_musicas"):
        return {}
    secao = parser["titulos_musicas"]
    titulos = {}
    total = _int_ini(secao.get("count"), 0)
    for indice in range(total):
        prefixo = f"item_{indice:04d}"
        arquivo = str(secao.get(f"{prefixo}_file", "")).strip()
        titulo = str(secao.get(f"{prefixo}_title", "")).strip()
        if arquivo and titulo:
            titulos[arquivo] = titulo
    return titulos


def _salvar_ordem_musicas(parser: configparser.ConfigParser, ordem: list[str]):
    secao = {"count": str(len(ordem))}
    for indice, arquivo in enumerate(ordem):
        secao[f"item_{indice:04d}"] = str(arquivo)
    parser["ordem_musicas"] = secao


def _carregar_ordem_musicas(parser: configparser.ConfigParser) -> list[str]:
    if not parser.has_section("ordem_musicas"):
        return []
    secao = parser["ordem_musicas"]
    total = _int_ini(secao.get("count"), 0)
    ordem = []
    for indice in range(total):
        arquivo = str(secao.get(f"item_{indice:04d}", "")).strip()
        if arquivo:
            ordem.append(arquivo)
    return ordem


def _salvar_intro_phrases(parser: configparser.ConfigParser, frases: list[dict]):
    secao = {"count": str(len(frases))}
    for indice, frase in enumerate(frases):
        prefixo = f"item_{indice:04d}"
        secao[f"{prefixo}_inicio"] = _valor_para_ini(frase.get("inicio", 0.0))
        secao[f"{prefixo}_duracao"] = _valor_para_ini(frase.get("duracao", 4.0))
        secao[f"{prefixo}_texto"] = _valor_para_ini(frase.get("texto", ""))
    parser["intro_phrases"] = secao


def _carregar_intro_phrases(parser: configparser.ConfigParser) -> list[dict]:
    if not parser.has_section("intro_phrases"):
        return []
    secao = parser["intro_phrases"]
    frases = []
    total = _int_ini(secao.get("count"), 0)
    for indice in range(total):
        prefixo = f"item_{indice:04d}"
        texto = str(secao.get(f"{prefixo}_texto", "")).strip()
        if texto:
            frases.append({
                "inicio": _float_ini(secao.get(f"{prefixo}_inicio"), 0.0),
                "duracao": _float_ini(secao.get(f"{prefixo}_duracao"), 4.0),
                "texto": texto,
            })
    return frases


def carregar_config() -> dict:
    if SETTINGS_INI_PATH.exists():
        parser = _config_parser()
        try:
            parser.read(SETTINGS_INI_PATH, encoding="utf-8")
        except configparser.Error as exc:
            LOGGER.debug("Falha ao ler settings.ini: %s", exc)
            return {}

        render = _carregar_secao(parser, "render")
        normalizacao = _carregar_dataclass(parser, "normalizacao", NormalizacaoConfig)
        fonte_texto = _carregar_dataclass(parser, "fonte_texto", FonteTextoConfig)
        watermark = _carregar_dataclass(parser, "watermark", WatermarkConfig)
        intro = _carregar_dataclass(parser, "intro", IntroTextConfig)
        intro["phrases"] = _carregar_intro_phrases(parser)

        return {
            "app_version": parser.get("app", "app_version", fallback=""),
            "paths": _carregar_secao(parser, "paths"),
            "render": {
                "use_gpu": _bool_ini(render.get("use_gpu"), True),
                "use_fade_in": _bool_ini(render.get("use_fade_in"), True),
                "use_fade_out": _bool_ini(render.get("use_fade_out"), True),
                "fade_in_seconds": _float_ini(render.get("fade_in_seconds"), 3.0),
                "fade_out_seconds": _float_ini(render.get("fade_out_seconds"), 3.0),
                "background_volume": _float_ini(render.get("background_volume"), 0.3),
                "crossfade_seconds": _float_ini(render.get("crossfade_seconds"), 0.0),
                "silence_seconds": _float_ini(render.get("silence_seconds"), 0.0),
            },
            "normalizacao": normalizacao,
            "preview": {"volume": _float_ini(parser.get("preview", "volume", fallback="1.0"), 1.0)},
            "ui": {"zoom": _float_ini(parser.get("ui", "zoom", fallback="1.0"), 1.0)} if parser.has_section("ui") else {},
            "fonte_texto": fonte_texto,
            "titulos_musicas": _carregar_titulos_musicas(parser),
            "ordem_musicas": _carregar_ordem_musicas(parser),
            "watermark": watermark,
            "intro": intro,
        }

    if not LEGACY_CONFIG_JSON_PATH.exists():
        return {}
    try:
        return json.loads(LEGACY_CONFIG_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.debug("Falha ao ler config JSON legado: %s", exc)
        return {}


def salvar_config(dados: dict):
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    parser = _config_parser()
    parser["app"] = {"app_version": str(dados.get("app_version", APP_VERSION))}
    _salvar_secao(parser, "paths", dados.get("paths", {}))
    _salvar_secao(parser, "render", dados.get("render", {}))
    _salvar_secao(parser, "normalizacao", dados.get("normalizacao", {}))
    _salvar_secao(parser, "preview", dados.get("preview", {}))
    _salvar_secao(parser, "ui", dados.get("ui", {}))
    _salvar_secao(parser, "fonte_texto", dados.get("fonte_texto", {}))
    _salvar_titulos_musicas(parser, dados.get("titulos_musicas", {}))
    _salvar_ordem_musicas(parser, dados.get("ordem_musicas", []))
    _salvar_secao(parser, "watermark", dados.get("watermark", {}))

    intro = dict(dados.get("intro", {}))
    frases = intro.pop("phrases", [])
    _salvar_secao(parser, "intro", intro)
    _salvar_intro_phrases(parser, frases)

    temporario = SETTINGS_INI_PATH.with_name(SETTINGS_INI_PATH.name + ".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        parser.write(arquivo)
    temporario.replace(SETTINGS_INI_PATH)
