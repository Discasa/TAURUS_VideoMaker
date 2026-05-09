# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Criador de vídeo lo-fi com interface PySide6 moderna.
Versão 8.0.9.

Recursos principais:
- Escolha de vídeo/GIF base por file chooser.
- Escolha da pasta com músicas por folder chooser.
- Escolha opcional de som de fundo por file chooser.
- Renderização por CPU ou GPU NVIDIA/NVENC.
- Configurações de fonte, tamanho, cor e fontface em modal separado.
- Configurações de marca d'água em modal separado.
- Fade in/out opcional com duração configurável.
- Normalização loudnorm configurável.
- Detecção automática do nome das músicas e dos tempos de início/fim reais.
- Janela sem barra nativa do Windows, com botões próprios de minimizar/fechar.
- Salva e carrega automaticamente as configurações em JSON ao lado do script.

Requisitos:
    pip install PySide6

FFmpeg esperado em:
    ./ffmpeg/bin/ffmpeg.exe
    ./ffmpeg/bin/ffprobe.exe

Quando empacotado como executável, os binários devem ser incluídos como dados
do pacote no mesmo caminho interno: ffmpeg/bin/.
"""

import ctypes
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

# ==========================
# CONFIGURAÇÕES BASE
# ==========================

APP_VERSION = "8.0.9"


def obter_diretorio_aplicacao() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def obter_diretorio_recursos() -> Path:
    pacote_temporario = getattr(sys, "_MEIPASS", None)
    if pacote_temporario:
        return Path(pacote_temporario).resolve()
    return obter_diretorio_aplicacao()


SCRIPT_DIR = obter_diretorio_aplicacao()
RESOURCE_DIR = obter_diretorio_recursos()
FFMPEG_BIN = RESOURCE_DIR / "ffmpeg" / "bin"
TEMP_DIR = SCRIPT_DIR / "_temp_audio_processado"
CONFIG_JSON_PATH = SCRIPT_DIR / "video_creator_config.json"  # JSON salvo ao lado deste script

FFMPEG = FFMPEG_BIN / "ffmpeg.exe"
FFPROBE = FFMPEG_BIN / "ffprobe.exe"

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


# ==========================
# DADOS DE CONFIGURAÇÃO
# ==========================

@dataclass
class FonteTextoConfig:
    font_family: str = "Georgia"
    # Mantido apenas para compatibilidade com configs antigas.
    # O modal novo usa fontes do sistema pelo QFontComboBox.
    font_file: str = ""
    font_size: int = 34
    color: str = "#FFFFFF"
    opacity: float = 0.93
    position: str = "inferior_esquerda"
    margin_left: int = 45
    margin_bottom: int = 42
    typing_duration: float = 2.2
    erasing_duration: float = 1.6
    shadow_opacity: float = 0.60


@dataclass
class WatermarkConfig:
    enabled: bool = True
    # "texto" ou "imagem".
    mode: str = "texto"
    text: str = "⚓"
    image_path: str = ""
    image_width: int = 180
    font_family: str = "Segoe UI Symbol"
    # Mantido apenas para compatibilidade com configs antigas.
    font_file: str = ""
    font_size: int = 44
    color: str = "#FFFFFF"
    opacity: float = 0.70
    position: str = "inferior_direita"
    margin_x: int = 45
    margin_y: int = 42
    shadow_opacity: float = 0.60


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
    font_file: str = ""
    font_size: int = 48
    font_weight: int = 700
    color: str = "#FFFFFF"
    opacity: float = 0.92
    position: str = "inferior_esquerda"
    margin_x: int = 90
    margin_y: int = 120
    shadow_opacity: float = 0.65
    shadow_size: float = 1.4
    background_box: bool = False
    box_opacity: float = 0.35


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
    use_gpu: bool = True
    use_fade_in: bool = True
    use_fade_out: bool = True
    fade_in_seconds: float = 3.0
    fade_out_seconds: float = 3.0
    background_volume: float = 0.30
    normalizacao: NormalizacaoConfig = field(default_factory=NormalizacaoConfig)
    fonte_texto: FonteTextoConfig = field(default_factory=FonteTextoConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    intro: IntroTextConfig = field(default_factory=IntroTextConfig)


@dataclass
class TrackInfo:
    arquivo: Path
    titulo: str
    inicio: float
    fim: float
    duracao: float


# ==========================
# JSON DE CONFIGURAÇÕES
# ==========================

def dataclass_from_dict(cls, dados: dict | None):
    if not isinstance(dados, dict):
        return cls()
    nomes_validos = {item.name for item in fields(cls)}
    filtrado = {chave: valor for chave, valor in dados.items() if chave in nomes_validos}
    try:
        return cls(**filtrado)
    except Exception:
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
                except Exception:
                    pass
    if frases:
        cfg.phrases = frases
    return cfg


def intro_config_to_dict(cfg: IntroTextConfig) -> dict:
    dados = asdict(cfg)
    dados["phrases"] = [asdict(frase) for frase in cfg.phrases]
    return dados


def segundos_para_ffmpeg(segundos: float) -> str:
    return f"{max(0.0, float(segundos)):.3f}"


def caminho_ou_vazio(caminho: Path | None) -> str:
    return str(caminho) if caminho else ""


def texto_para_path_ou_none(texto: str | None) -> Path | None:
    texto = (texto or "").strip()
    return Path(texto) if texto else None


def carregar_json_config() -> dict:
    if not CONFIG_JSON_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_json_config(dados: dict):
    CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporario = CONFIG_JSON_PATH.with_name(CONFIG_JSON_PATH.name + ".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(CONFIG_JSON_PATH)


# ==========================
# ERROS E CONTROLE
# ==========================

class RenderCancelado(Exception):
    pass


class ErroRender(Exception):
    pass


class ControleExecucao:
    def __init__(self):
        self.lock = threading.RLock()
        self.processo_atual = None
        self.cancelado = False
        self.pausado = False
        self.arquivos_para_excluir: list[Path] = []

    def resetar(self):
        with self.lock:
            self.processo_atual = None
            self.cancelado = False
            self.pausado = False
            self.arquivos_para_excluir = []

    def definir_processo(self, processo):
        with self.lock:
            self.processo_atual = processo

    def limpar_processo(self, processo):
        with self.lock:
            if self.processo_atual is processo:
                self.processo_atual = None

    def registrar_arquivo_temporario(self, caminho):
        caminho = Path(caminho)
        with self.lock:
            if caminho not in self.arquivos_para_excluir:
                self.arquivos_para_excluir.append(caminho)

    def solicitar_cancelamento(self):
        with self.lock:
            self.cancelado = True
            self.pausado = False
            processo = self.processo_atual

        if processo and processo.poll() is None:
            self._retomar_processo(processo.pid)
            self._encerrar_arvore_processo(processo)

        self.excluir_arquivos_cancelados()

    def alternar_pausa(self):
        with self.lock:
            processo = self.processo_atual
            if not processo or processo.poll() is not None:
                return self.pausado

            if self.pausado:
                self._retomar_processo(processo.pid)
                self.pausado = False
            else:
                self._pausar_processo(processo.pid)
                self.pausado = True

            return self.pausado

    def verificar_cancelamento(self):
        with self.lock:
            if self.cancelado:
                raise RenderCancelado("Renderização cancelada pelo usuário.")

    def excluir_arquivos_cancelados(self):
        with self.lock:
            arquivos = list(self.arquivos_para_excluir)

        for arquivo in arquivos:
            try:
                arquivo = Path(arquivo)
                if arquivo.exists() and arquivo.is_file():
                    arquivo.unlink()
            except Exception:
                pass

    def _encerrar_arvore_processo(self, processo):
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
            else:
                try:
                    os.killpg(os.getpgid(processo.pid), signal.SIGTERM)
                except Exception:
                    processo.terminate()
        except Exception:
            try:
                processo.kill()
            except Exception:
                pass

    def _pausar_processo(self, pid):
        try:
            if os.name == "nt":
                PROCESS_SUSPEND_RESUME = 0x0800
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
                if handle:
                    ctypes.windll.ntdll.NtSuspendProcess(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.killpg(os.getpgid(pid), signal.SIGSTOP)
        except Exception:
            pass

    def _retomar_processo(self, pid):
        try:
            if os.name == "nt":
                PROCESS_SUSPEND_RESUME = 0x0800
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
                if handle:
                    ctypes.windll.ntdll.NtResumeProcess(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.killpg(os.getpgid(pid), signal.SIGCONT)
        except Exception:
            pass


CONTROLE_EXECUCAO = ControleExecucao()


# ==========================
# UTILITÁRIOS FFMPEG/TEXTO
# ==========================

def criar_kwargs_subprocess_controlado():
    kwargs = {}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs["creationflags"] = creationflags

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    else:
        kwargs["preexec_fn"] = os.setsid
    return kwargs


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
        except Exception:
            pass

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
    except Exception:
        return None


def criar_env_ffmpeg() -> dict:
    env = os.environ.copy()
    conf = criar_fontconfig_windows()
    if conf:
        env["FONTCONFIG_FILE"] = str(conf)
        env["FONTCONFIG_PATH"] = str(conf.parent)
    return env

def natural_key(path: Path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", path.name)]


def limpar_titulo_musica(arquivo: Path) -> str:
    titulo = arquivo.stem
    titulo = re.sub(r"^\s*\d+\s*[\._\-\)]\s*", "", titulo)
    titulo = titulo.replace("_", " ").replace("-", " ")
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo or arquivo.stem


def segundos_para_ass_tempo(segundos: float) -> str:
    segundos = max(0.0, float(segundos))
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    seg = int(segundos % 60)
    centesimos = int(round((segundos - int(segundos)) * 100))

    if centesimos >= 100:
        centesimos = 0
        seg += 1
        if seg >= 60:
            seg = 0
            minutos += 1
        if minutos >= 60:
            minutos = 0
            horas += 1

    return f"{horas}:{minutos:02d}:{seg:02d}.{centesimos:02d}"


def segundos_para_legivel(segundos: float) -> str:
    segundos = max(0, int(round(segundos)))
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def escape_ass_texto(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\N")
    )


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


def escape_path_filter(path) -> str:
    caminho = Path(path).resolve().as_posix()
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


def hex_para_rgb(cor: str):
    cor = limpar_hex(cor).lstrip("#")
    return int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)


def cor_ass(cor_hex: str, opacity: float) -> str:
    r, g, b = hex_para_rgb(cor_hex)
    opacity = max(0.0, min(1.0, float(opacity)))
    alpha = int(round((1.0 - opacity) * 255))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def cor_drawtext(cor_hex: str, opacity: float) -> str:
    cor = limpar_hex(cor_hex).replace("#", "0x")
    opacity = max(0.0, min(1.0, float(opacity)))
    return f"{cor}@{opacity:.3f}"


def escape_filter_value(texto: str) -> str:
    return (
        (texto or "")
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


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


def ass_alignment_from_position(position: str) -> int:
    # ASS/libass: 1=inferior esquerda, 2=inferior centro, 3=inferior direita,
    # 7=superior esquerda, 8=superior centro, 9=superior direita, 5=centro.
    return {
        "inferior_esquerda": 1,
        "inferior_direita": 3,
        "superior_esquerda": 7,
        "superior_direita": 9,
        "superior_centro": 8,
        "inferior_centro": 2,
        "centro": 5,
    }.get(position, 1)


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
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return SCRIPT_DIR / f"render_{data_hora}"


# ==========================
# MOTOR DE RENDERIZAÇÃO
# ==========================

class RenderEngine:
    def __init__(self, config: RenderConfig, log_cb, progress_cb, stage_cb):
        self.config = config
        self.log = log_cb
        self.progress = progress_cb
        self.stage = stage_cb
        self.progresso_peso = 0.0
        self.peso_total = self._calcular_peso_total()

    def _calcular_peso_total(self) -> float:
        return (
            PESO_PROCESSAR_AUDIOS
            + PESO_CONCATENAR
            + PESO_NORMALIZAR_ANALISE
            + PESO_NORMALIZAR_APLICAR
            + PESO_MONTAR
        )

    def emitir_progresso_por_peso(self, peso_atual: float):
        percentual = int(max(0, min(100, round((peso_atual / self.peso_total) * 100))))
        self.progress(percentual)

    def adicionar_peso(self, peso: float):
        self.progresso_peso += peso
        self.emitir_progresso_por_peso(self.progresso_peso)

    def validar(self):
        if not FFMPEG.exists():
            raise ErroRender(f"ffmpeg.exe não encontrado em: {FFMPEG}")
        if not FFPROBE.exists():
            raise ErroRender(f"ffprobe.exe não encontrado em: {FFPROBE}")

        video = self.config.video_path
        if not video or not video.exists() or video.suffix.lower() not in EXTENSOES_VIDEO:
            raise ErroRender("Escolha um vídeo ou GIF base válido.")

        pasta = self.config.music_folder
        if not pasta or not pasta.exists() or not pasta.is_dir():
            raise ErroRender("Escolha uma pasta válida com as músicas.")

        if self.config.background_audio_path:
            fundo = self.config.background_audio_path
            if not fundo.exists() or fundo.suffix.lower() not in EXTENSOES_AUDIO:
                raise ErroRender("Escolha um áudio de fundo válido ou deixe o campo vazio.")

        if self.config.intro.enabled and self.config.intro.typing_audio_path:
            typing = Path(self.config.intro.typing_audio_path)
            if not typing.exists() or typing.suffix.lower() not in EXTENSOES_AUDIO:
                raise ErroRender("Escolha um áudio de digitação válido ou limpe o campo da intro.")

        watermark = self.config.watermark
        if watermark.enabled and watermark.mode == "imagem":
            imagem = Path(watermark.image_path) if watermark.image_path else None
            if not imagem or not imagem.exists() or imagem.suffix.lower() not in EXTENSOES_IMAGEM:
                raise ErroRender("Escolha uma imagem válida para a marca d'água ou use o modo texto.")

        self.config.output_folder.mkdir(parents=True, exist_ok=True)

    def preparar_pastas(self):
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    def run(self) -> Path:
        CONTROLE_EXECUCAO.verificar_cancelamento()
        self.validar()
        self.preparar_pastas()

        self.progress(0)
        self.stage("Lendo arquivos")
        self.log("\n=== Configuração usada ===\n")
        self.log(f"Vídeo/GIF base: {self.config.video_path}\n")
        self.log(f"Pasta das músicas: {self.config.music_folder}\n")
        self.log(f"Som de fundo: {self.config.background_audio_path or 'não usado'}\n")
        self.log(f"Pasta de saída: {self.config.output_folder}\n")
        self.log(f"Renderização: {'GPU NVIDIA / NVENC' if self.config.use_gpu else 'CPU / libx264'}\n")

        self.testar_filtro_subtitles()
        usar_gpu = self.config.use_gpu and self.testar_nvenc()

        tracks = self.detectar_tracks()
        duracao_total_musicas = tracks[-1].fim if tracks else 0.0
        duracao_total = duracao_total_musicas + max(0.0, self.config.intro.delay_music_seconds if self.config.intro.enabled else 0.0)

        self.log("\n=== Músicas detectadas automaticamente ===\n")
        for i, track in enumerate(tracks, start=1):
            self.log(
                f"{i:02d}. {track.titulo} | "
                f"{segundos_para_legivel(track.inicio)} - {segundos_para_legivel(track.fim)} "
                f"({segundos_para_legivel(track.duracao)})\n"
            )

        arquivos_processados = self.processar_audios(tracks, duracao_total_musicas)
        audio_final = self.concatenar_audios(arquivos_processados)
        audio_final = self.normalizar_audio(audio_final, duracao_total_musicas)
        saida_final = self.montar_video(audio_final, duracao_total, tracks, usar_gpu)

        self.stage("Finalizado")
        self.progress(100)
        self.log("\nFinalizado com sucesso!\n")
        self.log(f"Vídeo criado em: {saida_final}\n")
        self.log(f"Duração total: {segundos_para_legivel(duracao_total)}\n")
        return saida_final

    def detectar_tracks(self) -> list[TrackInfo]:
        self.stage("Detectando músicas e minutagens reais")
        arquivos = sorted(
            [
                p for p in self.config.music_folder.iterdir()
                if p.is_file()
                and p.suffix.lower() in EXTENSOES_AUDIO
                and not p.name.startswith("_temp_")
            ],
            key=natural_key,
        )

        if self.config.background_audio_path:
            fundo_resolvido = self.config.background_audio_path.resolve()
            arquivos = [p for p in arquivos if p.resolve() != fundo_resolvido]

        if not arquivos:
            raise ErroRender("Nenhum arquivo de música foi encontrado na pasta escolhida.")

        tracks: list[TrackInfo] = []
        cursor = 0.0
        for arquivo in arquivos:
            CONTROLE_EXECUCAO.verificar_cancelamento()
            duracao = self.obter_duracao(arquivo)
            if duracao <= 0:
                self.log(f"Aviso: ignorando arquivo sem duração válida: {arquivo.name}\n")
                continue
            inicio = cursor
            fim = cursor + duracao
            tracks.append(
                TrackInfo(
                    arquivo=arquivo,
                    titulo=limpar_titulo_musica(arquivo),
                    inicio=inicio,
                    fim=fim,
                    duracao=duracao,
                )
            )
            cursor = fim

        if not tracks:
            raise ErroRender("Nenhuma música válida foi encontrada após leitura das durações.")

        return tracks

    def obter_duracao(self, arquivo: Path) -> float:
        comando = [
            str(FFPROBE),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(arquivo),
        ]
        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            **criar_kwargs_subprocess_controlado(),
        )
        if resultado.returncode != 0:
            raise ErroRender(f"Não foi possível obter a duração de: {arquivo.name}\n{resultado.stderr}")
        try:
            return float(resultado.stdout.strip())
        except ValueError:
            raise ErroRender(f"Duração inválida retornada pelo ffprobe para: {arquivo.name}")

    def criar_filtro_fade(self, duracao: float) -> str | None:
        filtros = []
        if self.config.use_fade_in and self.config.fade_in_seconds > 0:
            duracao_fade = min(self.config.fade_in_seconds, duracao)
            filtros.append(f"afade=t=in:st=0:d={duracao_fade}")
        if self.config.use_fade_out and self.config.fade_out_seconds > 0:
            duracao_fade = min(self.config.fade_out_seconds, duracao)
            inicio = max(0, duracao - duracao_fade)
            filtros.append(f"afade=t=out:st={inicio}:d={duracao_fade}")
        return ",".join(filtros) if filtros else None

    def processar_audios(self, tracks: list[TrackInfo], duracao_total: float) -> list[Path]:
        self.stage("Processando músicas com fade")
        arquivos_processados: list[Path] = []
        duracao_processada = 0.0
        inicio_bloco = self.progresso_peso

        for i, track in enumerate(tracks, start=1):
            CONTROLE_EXECUCAO.verificar_cancelamento()
            self.stage(f"Processando música {i}/{len(tracks)}: {track.titulo}")
            self.log(f"\nProcessando música {i}/{len(tracks)}: {track.arquivo.name}\n")

            saida = TEMP_DIR / f"audio_{i:03d}.wav"
            CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida)

            comando = [
                str(FFMPEG),
                "-y",
                "-i", str(track.arquivo),
                "-vn",
                "-ar", "48000",
                "-ac", "2",
            ]

            filtro = self.criar_filtro_fade(track.duracao)
            if filtro:
                comando += ["-af", filtro]

            comando += [
                "-c:a", "pcm_s16le",
                "-progress", "pipe:1",
                "-nostats",
                str(saida),
            ]

            progresso_inicio_audio = inicio_bloco + ((duracao_processada / duracao_total) * PESO_PROCESSAR_AUDIOS)
            peso_audio_atual = (track.duracao / duracao_total) * PESO_PROCESSAR_AUDIOS

            self.rodar_ffmpeg_com_progresso(
                comando=comando,
                duracao_etapa=track.duracao,
                progresso_inicio_peso=progresso_inicio_audio,
                peso_etapa=peso_audio_atual,
            )

            duracao_processada += track.duracao
            arquivos_processados.append(saida)

        self.progresso_peso = inicio_bloco + PESO_PROCESSAR_AUDIOS
        self.emitir_progresso_por_peso(self.progresso_peso)
        return arquivos_processados

    def concatenar_audios(self, arquivos_processados: list[Path]) -> Path:
        self.stage("Concatenando músicas")
        self.log("\nConcatenando músicas...\n")

        lista_concat = TEMP_DIR / "lista_audios.txt"
        audio_final = TEMP_DIR / "audio_final.wav"
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(audio_final)

        with open(lista_concat, "w", encoding="utf-8") as f:
            for arquivo in arquivos_processados:
                caminho = arquivo.resolve().as_posix().replace("'", r"'\''")
                f.write(f"file '{caminho}'\n")

        comando = [
            str(FFMPEG),
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(lista_concat),
            "-c", "copy",
            str(audio_final),
        ]
        self.rodar_comando(comando)
        self.adicionar_peso(PESO_CONCATENAR)
        return audio_final

    def extrair_json_loudnorm(self, texto: str) -> dict:
        match = re.search(r"\{[\s\S]*?\}", texto)
        if not match:
            raise ErroRender("Não foi possível ler os dados JSON do loudnorm.")
        return json.loads(match.group(0))

    def normalizar_audio(self, audio_entrada: Path, duracao_total: float) -> Path:
        cfg = self.config.normalizacao
        if not cfg.enabled:
            self.log("\nNormalização desativada.\n")
            self.adicionar_peso(PESO_NORMALIZAR_ANALISE + PESO_NORMALIZAR_APLICAR)
            return audio_entrada

        self.stage("Analisando normalização loudnorm")
        self.log("\nNormalizando áudio com loudnorm:\n")
        self.log(f"Target LUFS: {cfg.target_lufs}\n")
        self.log(f"True Peak: {cfg.true_peak} dBTP\n")
        self.log(f"LRA: {cfg.loudness_range}\n")

        audio_normalizado = TEMP_DIR / "audio_final_normalizado.wav"
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(audio_normalizado)

        filtro_primeira = (
            f"loudnorm="
            f"I={cfg.target_lufs}:"
            f"TP={cfg.true_peak}:"
            f"LRA={cfg.loudness_range}:"
            f"print_format=json"
        )

        comando_analise = [
            str(FFMPEG),
            "-y",
            "-i", str(audio_entrada),
            "-af", filtro_primeira,
            "-f", "null",
            "NUL" if os.name == "nt" else "/dev/null",
        ]

        resultado = self.rodar_comando(comando_analise)
        dados = self.extrair_json_loudnorm(resultado.stderr)
        self.adicionar_peso(PESO_NORMALIZAR_ANALISE)

        filtro_segunda = (
            f"loudnorm="
            f"I={cfg.target_lufs}:"
            f"TP={cfg.true_peak}:"
            f"LRA={cfg.loudness_range}:"
            f"measured_I={dados['input_i']}:"
            f"measured_TP={dados['input_tp']}:"
            f"measured_LRA={dados['input_lra']}:"
            f"measured_thresh={dados['input_thresh']}:"
            f"offset={dados['target_offset']}:"
            f"linear=true:"
            f"print_format=summary"
        )

        self.stage("Aplicando normalização loudnorm")
        comando_normalizar = [
            str(FFMPEG),
            "-y",
            "-i", str(audio_entrada),
            "-af", filtro_segunda,
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            "-progress", "pipe:1",
            "-nostats",
            str(audio_normalizado),
        ]

        inicio = self.progresso_peso
        self.rodar_ffmpeg_com_progresso(
            comando=comando_normalizar,
            duracao_etapa=duracao_total,
            progresso_inicio_peso=inicio,
            peso_etapa=PESO_NORMALIZAR_APLICAR,
        )
        self.progresso_peso = inicio + PESO_NORMALIZAR_APLICAR
        self.emitir_progresso_por_peso(self.progresso_peso)
        return audio_normalizado

    def frases_intro_ativas(self) -> list[IntroFraseConfig]:
        cfg = self.config.intro
        frases = [frase for frase in cfg.phrases if str(frase.texto).strip() and frase.duracao > 0]
        if cfg.randomize_phrases and frases:
            quantidade = max(1, min(int(cfg.random_count), len(frases)))
            frases = random.sample(frases, quantidade)
            cursor = 0.0
            reorganizadas: list[IntroFraseConfig] = []
            for frase in frases:
                reorganizadas.append(IntroFraseConfig(cursor, frase.duracao, frase.texto))
                cursor += frase.duracao + 1.0
            frases = reorganizadas
        return frases

    def tempos_intro_frase(self, frase: IntroFraseConfig) -> dict:
        cfg = self.config.intro
        texto = str(frase.texto or "")
        total_chars = max(1, len(texto))
        inicio = max(0.0, float(frase.inicio))
        duracao = max(0.1, float(frase.duracao))
        fim = inicio + duracao
        dur_digitando = min(max(0.2, total_chars / max(1.0, cfg.typing_cps)), duracao * 0.45)
        dur_backspace = min(max(0.2, total_chars / max(1.0, cfg.backspace_cps)), duracao * 0.45)
        inicio_digitando = inicio
        fim_digitando = inicio + dur_digitando
        inicio_backspace = max(fim_digitando, fim - dur_backspace)
        fim_backspace = fim
        return {
            "inicio": inicio,
            "fim": fim,
            "duracao": duracao,
            "dur_digitando": dur_digitando,
            "inicio_digitando": inicio_digitando,
            "fim_digitando": fim_digitando,
            "dur_backspace": dur_backspace,
            "inicio_backspace": inicio_backspace,
            "fim_backspace": fim_backspace,
        }

    def criar_eventos_typewriter_intro(self, start: float, end: float, texto: str, estilo: str) -> list[str]:
        cfg = self.config.intro
        eventos: list[str] = []
        texto_limpo = escape_ass_texto(texto)
        total_chars = len(texto_limpo)
        if total_chars <= 0 or end <= start:
            return eventos

        efeito = (cfg.effect or "typewriter").lower()
        usar_fade = efeito in {"fade", "typewriter_fade"}
        usar_typewriter = efeito in {"typewriter", "typewriter_fade"}
        fade_tag = r"{\fad(350,650)}" if usar_fade else ""
        peso = max(100, min(900, int(getattr(cfg, "font_weight", 700))))
        peso_tag = rf"{{\b{peso}}}"
        prefixo = peso_tag + fade_tag

        if not usar_typewriter:
            eventos.append(
                f"Dialogue: 2,{segundos_para_ass_tempo(start)},{segundos_para_ass_tempo(end)},{estilo},,0,0,0,,{prefixo}{texto_limpo}"
            )
            return eventos

        fake = IntroFraseConfig(start, end - start, texto)
        tempos = self.tempos_intro_frase(fake)
        cursor = "|" if cfg.show_cursor else ""

        dur_digitando = tempos["dur_digitando"]
        passo = dur_digitando / total_chars
        for i in range(1, total_chars + 1):
            t1 = start + ((i - 1) * passo)
            t2 = min(start + (i * passo), tempos["inicio_backspace"])
            if t2 <= t1:
                continue
            parte = texto_limpo[:i] + cursor
            eventos.append(
                f"Dialogue: 2,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},{estilo},,0,0,0,,{prefixo}{parte}"
            )

        # Trecho parado com cursor piscando de verdade.
        hold_inicio = max(start + dur_digitando, tempos["fim_digitando"])
        hold_fim = tempos["inicio_backspace"]
        if hold_fim > hold_inicio:
            if cfg.show_cursor:
                t = hold_inicio
                visivel = True
                passo_blink = 0.45
                while t < hold_fim:
                    t2 = min(t + passo_blink, hold_fim)
                    cursor_atual = "|" if visivel else ""
                    eventos.append(
                        f"Dialogue: 2,{segundos_para_ass_tempo(t)},{segundos_para_ass_tempo(t2)},{estilo},,0,0,0,,{prefixo}{texto_limpo}{cursor_atual}"
                    )
                    visivel = not visivel
                    t = t2
            else:
                eventos.append(
                    f"Dialogue: 2,{segundos_para_ass_tempo(hold_inicio)},{segundos_para_ass_tempo(hold_fim)},{estilo},,0,0,0,,{prefixo}{texto_limpo}"
                )

        # Backspace: apaga letra por letra no final da duração da frase.
        dur_backspace = tempos["dur_backspace"]
        passo_back = dur_backspace / total_chars
        for chars_restantes in range(total_chars, -1, -1):
            indice = total_chars - chars_restantes
            t1 = tempos["inicio_backspace"] + (indice * passo_back)
            t2 = min(tempos["inicio_backspace"] + ((indice + 1) * passo_back), end)
            if t2 <= t1:
                continue
            parte = texto_limpo[:chars_restantes]
            if chars_restantes > 0 and cfg.show_cursor:
                parte += "|"
            eventos.append(
                f"Dialogue: 2,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},{estilo},,0,0,0,,{prefixo}{parte}"
            )
        return eventos

    def gerar_arquivo_ass_completo(self, tracks: list[TrackInfo] | None = None) -> Path:
        tracks = tracks or []
        cfg = self.config.fonte_texto
        intro = self.config.intro
        arquivo_ass = TEMP_DIR / "legendas_completas.ass"

        primary = cor_ass(cfg.color, cfg.opacity)
        outline = cor_ass("#000000", 0.60)
        shadow = cor_ass("#000000", cfg.shadow_opacity)
        alignment = ass_alignment_from_position(cfg.position)
        margem_horizontal = max(0, int(cfg.margin_left))
        margem_vertical = max(0, int(cfg.margin_bottom))

        intro_primary = cor_ass(intro.color, intro.opacity)
        intro_outline = cor_ass("#000000", 0.70)
        intro_shadow = cor_ass("#000000", intro.shadow_opacity)
        intro_back = cor_ass("#000000", intro.box_opacity if intro.background_box else intro.shadow_opacity)
        intro_border_style = 3 if intro.background_box else 1
        intro_bold_style = -1 if int(getattr(intro, "font_weight", 700)) >= 600 else 0
        intro_shadow_size = max(0.0, float(getattr(intro, "shadow_size", 1.4)))
        intro_alignment = ass_alignment_from_position(intro.position)
        intro_margin_x = max(0, int(intro.margin_x))
        intro_margin_y = max(0, int(intro.margin_y))

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Musica,{cfg.font_family},{cfg.font_size},{primary},&H000000FF,{outline},{shadow},0,0,0,0,100,100,0,0,1,1.6,1.4,{alignment},{margem_horizontal},{margem_horizontal},{margem_vertical},1
Style: Intro,{intro.font_family},{intro.font_size},{intro_primary},&H000000FF,{intro_outline},{intro_back},{intro_bold_style},0,0,0,100,100,0,0,{intro_border_style},1.8,{intro_shadow_size:.2f},{intro_alignment},{intro_margin_x},{intro_margin_x},{intro_margin_y},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        eventos: list[str] = []

        if intro.enabled:
            for frase in self.frases_intro_ativas():
                inicio = max(0.0, float(frase.inicio))
                fim = inicio + max(0.1, float(frase.duracao))
                eventos.extend(self.criar_eventos_typewriter_intro(inicio, fim, frase.texto, "Intro"))

        for track in tracks:
            start = track.inicio + max(0.0, self.config.intro.delay_music_seconds if self.config.intro.enabled else 0.0)
            end = track.fim + max(0.0, self.config.intro.delay_music_seconds if self.config.intro.enabled else 0.0)
            duracao = max(0.1, end - start)
            texto = escape_ass_texto(track.titulo)
            total_chars = len(texto)
            if total_chars <= 0:
                continue

            dur_digitando = min(cfg.typing_duration, duracao * 0.35)
            dur_apagando = min(cfg.erasing_duration, duracao * 0.25)
            inicio_digitando = start
            fim_digitando = start + dur_digitando
            inicio_apagando = max(fim_digitando, end - dur_apagando)
            passo_digitar = dur_digitando / total_chars
            for i in range(1, total_chars + 1):
                t1 = inicio_digitando + ((i - 1) * passo_digitar)
                t2 = inicio_digitando + (i * passo_digitar)
                parte = texto[:i]
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},Musica,,0,0,0,,{parte}"
                )
            if inicio_apagando > fim_digitando:
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(fim_digitando)},{segundos_para_ass_tempo(inicio_apagando)},Musica,,0,0,0,,{texto}"
                )
            passo_apagar = dur_apagando / total_chars
            for i in range(total_chars, 0, -1):
                indice = total_chars - i
                t1 = inicio_apagando + (indice * passo_apagar)
                t2 = inicio_apagando + ((indice + 1) * passo_apagar)
                parte = texto[:i]
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},Musica,,0,0,0,,{parte}"
                )

        arquivo_ass.write_text(header + "\n".join(eventos), encoding="utf-8")
        return arquivo_ass

    def gerar_arquivo_ass_musicas(self, tracks: list[TrackInfo]) -> Path:
        cfg = self.config.fonte_texto
        arquivo_ass = TEMP_DIR / "musicas_typewriter.ass"

        primary = cor_ass(cfg.color, cfg.opacity)
        outline = cor_ass("#000000", 0.60)
        shadow = cor_ass("#000000", cfg.shadow_opacity)

        alignment = ass_alignment_from_position(cfg.position)
        margem_horizontal = max(0, int(cfg.margin_left))
        margem_vertical = max(0, int(cfg.margin_bottom))

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Musica,{cfg.font_family},{cfg.font_size},{primary},&H000000FF,{outline},{shadow},0,0,0,0,100,100,0,0,1,1.6,1.4,{alignment},{margem_horizontal},{margem_horizontal},{margem_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        eventos: list[str] = []

        for track in tracks:
            start = track.inicio
            end = track.fim
            duracao = max(0.1, end - start)
            texto = escape_ass_texto(track.titulo)
            total_chars = len(texto)
            if total_chars <= 0:
                continue

            dur_digitando = min(cfg.typing_duration, duracao * 0.35)
            dur_apagando = min(cfg.erasing_duration, duracao * 0.25)

            inicio_digitando = start
            fim_digitando = start + dur_digitando
            inicio_apagando = max(fim_digitando, end - dur_apagando)
            fim_apagando = end

            passo_digitar = dur_digitando / total_chars
            for i in range(1, total_chars + 1):
                t1 = inicio_digitando + ((i - 1) * passo_digitar)
                t2 = inicio_digitando + (i * passo_digitar)
                parte = texto[:i]
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},Musica,,0,0,0,,{parte}"
                )

            if inicio_apagando > fim_digitando:
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(fim_digitando)},{segundos_para_ass_tempo(inicio_apagando)},Musica,,0,0,0,,{texto}"
                )

            passo_apagar = dur_apagando / total_chars
            for i in range(total_chars, 0, -1):
                indice = total_chars - i
                t1 = inicio_apagando + (indice * passo_apagar)
                t2 = inicio_apagando + ((indice + 1) * passo_apagar)
                parte = texto[:i]
                eventos.append(
                    f"Dialogue: 0,{segundos_para_ass_tempo(t1)},{segundos_para_ass_tempo(t2)},Musica,,0,0,0,,{parte}"
                )

        arquivo_ass.write_text(header + "\n".join(eventos), encoding="utf-8")
        return arquivo_ass

    def criar_drawtext_watermark(self) -> str | None:
        cfg = self.config.watermark
        if not cfg.enabled or cfg.mode != "texto" or not cfg.text.strip():
            return None

        opcoes = []
        fontfile = escape_fontfile(self.caminho_fontfile_drawtext(cfg.font_family, False))
        opcoes.append(f"fontfile='{fontfile}'")

        posicoes = {
            "inferior_direita": (f"w-tw-{cfg.margin_x}", f"h-th-{cfg.margin_y}"),
            "inferior_esquerda": (f"{cfg.margin_x}", f"h-th-{cfg.margin_y}"),
            "inferior_centro": ("(w-tw)/2", f"h-th-{cfg.margin_y}"),
            "superior_direita": (f"w-tw-{cfg.margin_x}", f"{cfg.margin_y}"),
            "superior_esquerda": (f"{cfg.margin_x}", f"{cfg.margin_y}"),
            "superior_centro": ("(w-tw)/2", f"{cfg.margin_y}"),
            "centro": ("(w-tw)/2", "(h-th)/2"),
        }
        x, y = posicoes.get(cfg.position, posicoes["inferior_direita"])

        opcoes += [
            f"text='{escape_drawtext(cfg.text)}'",
            f"fontcolor={cor_drawtext(cfg.color, cfg.opacity)}",
            f"fontsize={cfg.font_size}",
            f"x={x}",
            f"y={y}",
            f"shadowcolor=black@{cfg.shadow_opacity}",
            "shadowx=2",
            "shadowy=2",
        ]
        return "drawtext=" + ":".join(opcoes)

    def criar_overlay_watermark_imagem(self, entrada_video: str, indice_imagem: int) -> list[str]:
        cfg = self.config.watermark
        x, y = overlay_position_expr(cfg.position, cfg.margin_x, cfg.margin_y)
        filtros: list[str] = []

        # Corrige a marca d'água por imagem: normaliza a imagem para RGBA,
        # preserva transparência de PNG/WebP e aplica a opacidade escolhida.
        # setsar=1 evita distorção em imagens/vídeos com sample aspect ratio estranho.
        largura = int(getattr(cfg, "image_width", 0) or 0)
        opacity = max(0.0, min(1.0, float(getattr(cfg, "opacity", 1.0))))
        if largura > 0:
            filtros.append(
                f"[{indice_imagem}:v]scale={largura}:-1:flags=lanczos,setsar=1,format=rgba,"
                f"colorchannelmixer=aa={opacity:.3f}[wm]"
            )
        else:
            filtros.append(
                f"[{indice_imagem}:v]setsar=1,format=rgba,colorchannelmixer=aa={opacity:.3f}[wm]"
            )

        filtros.append(
            f"[{entrada_video}][wm]overlay=x={x}:y={y}:format=auto:eof_action=repeat[vout]"
        )
        return filtros

    def caminho_fontfile_drawtext(self, font_family: str, bold: bool = False) -> Path:
        """Escolhe um arquivo .ttf direto para o drawtext.

        Isso evita o filtro subtitles/libass, que estava causando crash no FFmpeg
        novo no Windows com Returncode 3221225477.
        """
        pasta = preparar_pasta_fontes_ffmpeg()
        fam = (font_family or "").lower()

        if "georgia" in fam:
            candidatos = ["georgiab.ttf", "georgia.ttf"] if bold else ["georgia.ttf", "georgiab.ttf"]
        elif "segoe" in fam:
            candidatos = ["segoeuib.ttf", "segoeui.ttf", "seguisym.ttf"] if bold else ["segoeui.ttf", "seguisym.ttf", "segoeuib.ttf"]
        elif "symbol" in fam:
            candidatos = ["seguisym.ttf", "segoeui.ttf", "arial.ttf"]
        else:
            candidatos = ["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf", "georgia.ttf"]

        for nome in candidatos:
            caminho = pasta / nome
            if caminho.exists():
                return caminho

        # fallback direto para fontes do Windows, caso a cópia não tenha ocorrido
        winfonts = caminho_pasta_fontes_windows()
        for nome in candidatos:
            caminho = winfonts / nome
            if caminho.exists():
                return caminho

        return winfonts / "arial.ttf"

    def posicao_drawtext_expr(self, position: str, margin_x: int, margin_y: int) -> tuple[str, str]:
        posicoes = {
            "inferior_direita": (f"w-tw-{margin_x}", f"h-th-{margin_y}"),
            "inferior_esquerda": (f"{margin_x}", f"h-th-{margin_y}"),
            "inferior_centro": ("(w-tw)/2", f"h-th-{margin_y}"),
            "superior_direita": (f"w-tw-{margin_x}", f"{margin_y}"),
            "superior_esquerda": (f"{margin_x}", f"{margin_y}"),
            "superior_centro": ("(w-tw)/2", f"{margin_y}"),
            "centro": ("(w-tw)/2", "(h-th)/2"),
        }
        return posicoes.get(position, posicoes["inferior_esquerda"])

    def criar_drawtext_filtro_evento(self, entrada: str, saida: str, texto: str, inicio: float, fim: float, cfg, intro: bool = False) -> str:
        inicio = max(0.0, float(inicio))
        fim = max(inicio + 0.01, float(fim))
        texto = escape_drawtext(texto)

        font_size = int(getattr(cfg, "font_size", 34))
        color = getattr(cfg, "color", "#FFFFFF")
        opacity = float(getattr(cfg, "opacity", 0.93))
        shadow_opacity = float(getattr(cfg, "shadow_opacity", 0.60))
        font_family = getattr(cfg, "font_family", "Georgia")
        bold = int(getattr(cfg, "font_weight", 400)) >= 600 if intro else False
        fontfile = escape_fontfile(self.caminho_fontfile_drawtext(font_family, bold))

        if intro:
            x, y = self.posicao_drawtext_expr(
                getattr(cfg, "position", "inferior_esquerda"),
                int(getattr(cfg, "margin_x", 90)),
                int(getattr(cfg, "margin_y", 120)),
            )
        else:
            x, y = self.posicao_drawtext_expr(
                getattr(cfg, "position", "inferior_esquerda"),
                int(getattr(cfg, "margin_left", 45)),
                int(getattr(cfg, "margin_bottom", 42)),
            )

        opcoes = [
            f"fontfile='{fontfile}'",
            f"text='{texto}'",
            f"fontcolor={cor_drawtext(color, opacity)}",
            f"fontsize={font_size}",
            f"x={x}",
            f"y={y}",
            f"shadowcolor=black@{shadow_opacity}",
            "shadowx=2",
            "shadowy=2",
            f"enable='between(t,{inicio:.3f},{fim:.3f})'",
        ]

        if intro and getattr(cfg, "background_box", False):
            opcoes += [
                "box=1",
                f"boxcolor=black@{float(getattr(cfg, 'box_opacity', 0.35)):.3f}",
                "boxborderw=14",
            ]

        return f"[{entrada}]drawtext=" + ":".join(opcoes) + f"[{saida}]"

    def criar_eventos_drawtext_intro(self) -> list[tuple[float, float, str, bool]]:
        cfg = self.config.intro
        eventos: list[tuple[float, float, str, bool]] = []
        if not cfg.enabled:
            return eventos

        for frase in self.frases_intro_ativas():
            texto = str(frase.texto or "")
            total_chars = len(texto)
            if total_chars <= 0:
                continue

            tempos = self.tempos_intro_frase(frase)
            start = tempos["inicio"]
            end = tempos["fim"]
            efeito = (cfg.effect or "typewriter").lower()
            usar_typewriter = efeito in {"typewriter", "typewriter_fade"}
            cursor = "|" if cfg.show_cursor else ""

            if not usar_typewriter:
                eventos.append((start, end, texto, True))
                continue

            passo = tempos["dur_digitando"] / max(1, total_chars)
            for i in range(1, total_chars + 1):
                t1 = start + ((i - 1) * passo)
                t2 = min(start + (i * passo), tempos["inicio_backspace"])
                if t2 > t1:
                    eventos.append((t1, t2, texto[:i] + cursor, True))

            hold_inicio = max(start + tempos["dur_digitando"], tempos["fim_digitando"])
            hold_fim = tempos["inicio_backspace"]
            if hold_fim > hold_inicio:
                if cfg.show_cursor:
                    t = hold_inicio
                    visivel = True
                    while t < hold_fim:
                        t2 = min(t + 0.45, hold_fim)
                        eventos.append((t, t2, texto + ("|" if visivel else ""), True))
                        visivel = not visivel
                        t = t2
                else:
                    eventos.append((hold_inicio, hold_fim, texto, True))

            passo_back = tempos["dur_backspace"] / max(1, total_chars)
            for chars_restantes in range(total_chars, -1, -1):
                indice = total_chars - chars_restantes
                t1 = tempos["inicio_backspace"] + (indice * passo_back)
                t2 = min(tempos["inicio_backspace"] + ((indice + 1) * passo_back), end)
                if t2 > t1:
                    parte = texto[:chars_restantes]
                    if chars_restantes > 0 and cfg.show_cursor:
                        parte += "|"
                    eventos.append((t1, t2, parte, True))
        return eventos

    def criar_eventos_drawtext_musicas(self, tracks: list[TrackInfo]) -> list[tuple[float, float, str, bool]]:
        cfg = self.config.fonte_texto
        eventos: list[tuple[float, float, str, bool]] = []
        delay = max(0.0, self.config.intro.delay_music_seconds if self.config.intro.enabled else 0.0)

        for track in tracks:
            start = track.inicio + delay
            end = track.fim + delay
            duracao = max(0.1, end - start)
            texto = str(track.titulo or "")
            total_chars = len(texto)
            if total_chars <= 0:
                continue

            dur_digitando = min(float(cfg.typing_duration), duracao * 0.35)
            dur_apagando = min(float(cfg.erasing_duration), duracao * 0.25)
            inicio_digitando = start
            fim_digitando = start + dur_digitando
            inicio_apagando = max(fim_digitando, end - dur_apagando)

            passo_digitar = dur_digitando / max(1, total_chars)
            for i in range(1, total_chars + 1):
                t1 = inicio_digitando + ((i - 1) * passo_digitar)
                t2 = inicio_digitando + (i * passo_digitar)
                if t2 > t1:
                    eventos.append((t1, t2, texto[:i], False))

            if inicio_apagando > fim_digitando:
                eventos.append((fim_digitando, inicio_apagando, texto, False))

            passo_apagar = dur_apagando / max(1, total_chars)
            for i in range(total_chars, 0, -1):
                indice = total_chars - i
                t1 = inicio_apagando + (indice * passo_apagar)
                t2 = inicio_apagando + ((indice + 1) * passo_apagar)
                if t2 > t1:
                    eventos.append((t1, t2, texto[:i], False))
        return eventos

    def criar_filtro_video(self, tracks: list[TrackInfo], watermark_image_index: int | None = None) -> str:
        filtros: list[str] = []
        entrada_atual = "0:v"
        contador = 0

        eventos = self.criar_eventos_drawtext_intro() + self.criar_eventos_drawtext_musicas(tracks)
        self.log(f"\nUsando drawtext direto para textos/nomes das músicas ({len(eventos)} eventos). Filtro subtitles/libass desativado para evitar crash.\n")

        for inicio, fim, texto, is_intro in eventos:
            if not str(texto).strip():
                continue
            saida = f"vdt{contador}"
            cfg_texto = self.config.intro if is_intro else self.config.fonte_texto
            filtros.append(self.criar_drawtext_filtro_evento(entrada_atual, saida, texto, inicio, fim, cfg_texto, intro=is_intro))
            entrada_atual = saida
            contador += 1

        cfg = self.config.watermark
        if cfg.enabled and cfg.mode == "imagem" and watermark_image_index is not None:
            filtros.extend(self.criar_overlay_watermark_imagem(entrada_atual, watermark_image_index))
        else:
            watermark = self.criar_drawtext_watermark()
            if watermark:
                filtros.append(f"[{entrada_atual}]{watermark}[vout]")
            else:
                filtros.append(f"[{entrada_atual}]null[vout]")

        return ";\n".join(filtros)

    def criar_filter_complex(self, tracks: list[TrackInfo], usar_fundo: bool, watermark_image_index: int | None = None, typing_audio_index: int | None = None, duracao_total: float | None = None) -> Path:
        filtros = [self.criar_filtro_video(tracks, watermark_image_index)]
        audio_labels: list[str] = []
        intro = self.config.intro
        delay = max(0.0, intro.delay_music_seconds if intro.enabled else 0.0)

        if delay > 0:
            atraso_ms = int(round(delay * 1000))
            if duracao_total:
                filtros.append(
                    f"[1:a]adelay={atraso_ms}:all=1,"
                    f"apad=whole_dur={segundos_para_ffmpeg(duracao_total)},"
                    f"atrim=0:{segundos_para_ffmpeg(duracao_total)},asetpts=PTS-STARTPTS,volume=1.0[music]"
                )
            else:
                filtros.append(f"[1:a]adelay={atraso_ms}:all=1,volume=1.0[music]")
        else:
            if duracao_total:
                filtros.append(
                    f"[1:a]apad=whole_dur={segundos_para_ffmpeg(duracao_total)},"
                    f"atrim=0:{segundos_para_ffmpeg(duracao_total)},asetpts=PTS-STARTPTS,volume=1.0[music]"
                )
            else:
                filtros.append("[1:a]volume=1.0[music]")
        audio_labels.append("[music]")

        if usar_fundo:
            filtros.append(f"[2:a]volume={self.config.background_volume}[bg]")
            audio_labels.append("[bg]")

        if typing_audio_index is not None and intro.enabled and intro.typing_audio_path:
            typing_parts: list[str] = []
            for idx, frase in enumerate(self.frases_intro_ativas()):
                tempos = self.tempos_intro_frase(frase)

                type_label = f"ty{idx}a"
                type_delay_ms = int(round(tempos["inicio_digitando"] * 1000))
                filtros.append(
                    f"[{typing_audio_index}:a]atrim=0:{segundos_para_ffmpeg(tempos['dur_digitando'])},asetpts=PTS-STARTPTS,"
                    f"volume={intro.typing_volume},adelay={type_delay_ms}:all=1[{type_label}]"
                )
                typing_parts.append(f"[{type_label}]")

                if intro.backspace_audio_enabled:
                    back_label = f"ty{idx}b"
                    back_delay_ms = int(round(tempos["inicio_backspace"] * 1000))
                    filtros.append(
                        f"[{typing_audio_index}:a]atrim=0:{segundos_para_ffmpeg(tempos['dur_backspace'])},asetpts=PTS-STARTPTS,"
                        f"volume={intro.typing_volume},adelay={back_delay_ms}:all=1[{back_label}]"
                    )
                    typing_parts.append(f"[{back_label}]")
            if typing_parts:
                filtros.append(f"{''.join(typing_parts)}amix=inputs={len(typing_parts)}:duration=longest:dropout_transition=0[typing]")
                audio_labels.append("[typing]")

        if len(audio_labels) == 1:
            filtros.append(f"{audio_labels[0]}anull[aout]")
        else:
            filtros.append(f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=2[aout]")

        filter_complex = ";\n".join(filtros)
        arquivo_filtro = TEMP_DIR / "filter_complex.txt"
        arquivo_filtro.write_text(filter_complex, encoding="utf-8")

        self.log("\nFiltro complex gerado:\n")
        self.log(filter_complex + "\n")
        return arquivo_filtro

    def montar_video(self, audio_final: Path, duracao_total: float, tracks: list[TrackInfo], usar_gpu: bool, prefixo_saida: str = "video_final") -> Path:
        self.stage("Montando vídeo final")
        self.log("\nMontando vídeo final...\n")

        saida_final = self.config.output_folder / gerar_nome_video(prefixo_saida)
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida_final)

        usar_fundo = self.config.background_audio_path is not None
        usar_typing = bool(self.config.intro.enabled and self.config.intro.typing_audio_path)
        usar_watermark_imagem = (
            self.config.watermark.enabled
            and self.config.watermark.mode == "imagem"
            and bool(self.config.watermark.image_path)
        )

        comando = [
            str(FFMPEG),
            "-y",
            "-stream_loop", "-1",
            "-i", str(self.config.video_path),
            "-i", str(audio_final),
        ]

        proximo_indice = 2
        indice_fundo = None
        indice_typing = None
        indice_watermark_imagem = None

        if usar_fundo:
            indice_fundo = proximo_indice
            proximo_indice += 1
            comando += [
                "-stream_loop", "-1",
                "-i", str(self.config.background_audio_path),
            ]

        if usar_typing:
            indice_typing = proximo_indice
            proximo_indice += 1
            comando += [
                "-stream_loop", "-1",
                "-i", str(self.config.intro.typing_audio_path),
            ]

        if usar_watermark_imagem:
            indice_watermark_imagem = proximo_indice
            comando += [
                "-loop", "1",
                "-i", str(self.config.watermark.image_path),
            ]

        arquivo_filtro = self.criar_filter_complex(
            tracks,
            usar_fundo,
            indice_watermark_imagem if usar_watermark_imagem else None,
            indice_typing,
            duracao_total,
        )

        comando += [
            "-/filter_complex", str(arquivo_filtro),
            "-t", str(duracao_total),
            "-map", "[vout]",
        ]

        comando += ["-map", "[aout]"]

        if usar_gpu:
            comando += [
                "-c:v", "h264_nvenc",
                "-preset", NVENC_PRESET,
                "-rc", "vbr",
                "-cq", NVENC_CQ,
                "-b:v", "0",
                "-maxrate", NVENC_MAXRATE,
                "-bufsize", NVENC_BUFSIZE,
            ]
        else:
            comando += [
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
            ]

        comando += [
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-progress", "pipe:1",
            "-nostats",
            str(saida_final),
        ]

        inicio = self.progresso_peso
        self.rodar_ffmpeg_com_progresso(
            comando=comando,
            duracao_etapa=duracao_total,
            progresso_inicio_peso=inicio,
            peso_etapa=PESO_MONTAR,
        )
        self.progresso_peso = inicio + PESO_MONTAR
        self.emitir_progresso_por_peso(self.progresso_peso)
        return saida_final

    def rodar_comando(self, comando: list[str], mostrar_saida: bool = False):
        CONTROLE_EXECUCAO.verificar_cancelamento()
        self.log("\nExecutando:\n")
        self.log(" ".join(f'\"{c}\"' if " " in str(c) else str(c) for c in comando) + "\n")

        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=criar_env_ffmpeg(),
            **criar_kwargs_subprocess_controlado(),
        )
        CONTROLE_EXECUCAO.definir_processo(processo)

        try:
            stdout, stderr = processo.communicate()
        finally:
            CONTROLE_EXECUCAO.limpar_processo(processo)

        if mostrar_saida:
            self.log(stdout + "\n" + stderr + "\n")

        if CONTROLE_EXECUCAO.cancelado:
            raise RenderCancelado("Renderização cancelada pelo usuário.")

        if processo.returncode != 0:
            log_path = SCRIPT_DIR / "erro_ffmpeg_log.txt"
            log_completo = (
                "COMANDO EXECUTADO:\n" + " ".join(str(c) for c in comando) + "\n\n"
                f"RETURNCODE: {processo.returncode}\n\n"
                "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr
            )
            try:
                log_path.write_text(log_completo, encoding="utf-8", errors="ignore")
            except Exception:
                pass
            raise ErroRender(
                "Erro ao executar comando.\n"
                f"Log completo salvo em: {log_path}\n"
                f"Returncode: {processo.returncode}\n\n"
                + stderr[-4000:]
            )

        class Resultado:
            def __init__(self, stdout, stderr, returncode):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode

        return Resultado(stdout, stderr, processo.returncode)

    def rodar_ffmpeg_com_progresso(self, comando: list[str], duracao_etapa: float, progresso_inicio_peso: float, peso_etapa: float):
        CONTROLE_EXECUCAO.verificar_cancelamento()
        self.log("\nExecutando:\n")
        self.log(" ".join(f'\"{c}\"' if " " in str(c) else str(c) for c in comando) + "\n")

        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
            env=criar_env_ffmpeg(),
            **criar_kwargs_subprocess_controlado(),
        )
        CONTROLE_EXECUCAO.definir_processo(processo)
        linhas_erro: list[str] = []

        try:
            for linha in processo.stdout:
                CONTROLE_EXECUCAO.verificar_cancelamento()
                linha = linha.strip()
                if linha:
                    linhas_erro.append(linha)

                if linha.startswith("out_time_ms="):
                    try:
                        tempo_ms = int(linha.split("=")[1])
                        tempo_segundos = tempo_ms / 1_000_000
                        etapa = min(tempo_segundos / max(duracao_etapa, 0.1), 1.0)
                        peso = progresso_inicio_peso + (etapa * peso_etapa)
                        self.emitir_progresso_por_peso(peso)
                    except Exception:
                        pass
                elif linha.startswith("progress=end"):
                    self.emitir_progresso_por_peso(progresso_inicio_peso + peso_etapa)

            processo.wait()
        finally:
            CONTROLE_EXECUCAO.limpar_processo(processo)

        if CONTROLE_EXECUCAO.cancelado:
            raise RenderCancelado("Renderização cancelada pelo usuário.")

        if processo.returncode != 0:
            log_path = SCRIPT_DIR / "erro_ffmpeg_log.txt"
            log_completo = (
                "COMANDO EXECUTADO:\n" + " ".join(str(c) for c in comando) + "\n\n"
                f"RETURNCODE: {processo.returncode}\n\n"
                "LOG FFmpeg:\n" + "\n".join(linhas_erro)
            )
            try:
                log_path.write_text(log_completo, encoding="utf-8", errors="ignore")
            except Exception:
                pass
            raise ErroRender(
                "Erro ao executar FFmpeg.\n"
                f"Log completo salvo em: {log_path}\n"
                f"Returncode: {processo.returncode}\n\n"
                + "\n".join(linhas_erro[-80:])
            )

    def selecionar_tracks_teste(self, tracks: list[TrackInfo], duracao_musica: float) -> list[TrackInfo]:
        """Seleciona apenas o começo da playlist para gerar teste curto.

        Se uma música passar do limite, ela é cortada só para o teste.
        Assim o botão de teste não precisa processar a playlist inteira.
        """
        limite = max(0.1, float(duracao_musica))
        selecionados: list[TrackInfo] = []
        cursor = 0.0

        for track in tracks:
            if cursor >= limite:
                break
            duracao_segmento = min(float(track.duracao), limite - cursor)
            if duracao_segmento <= 0:
                continue
            selecionados.append(
                TrackInfo(
                    arquivo=track.arquivo,
                    titulo=track.titulo,
                    inicio=cursor,
                    fim=cursor + duracao_segmento,
                    duracao=duracao_segmento,
                )
            )
            cursor += duracao_segmento

        return selecionados

    def criar_filtro_fade_teste(self, duracao_segmento: float, duracao_original: float) -> str | None:
        filtros = []
        if self.config.use_fade_in and self.config.fade_in_seconds > 0:
            duracao_fade = min(self.config.fade_in_seconds, duracao_segmento)
            filtros.append(f"afade=t=in:st=0:d={duracao_fade}")

        # Só aplica fade-out se o segmento de teste contém o final real da música.
        # Se a música continua depois dos 30s, o teste não inventa um fade que não existirá no render final.
        segmento_chega_no_fim = duracao_segmento >= (duracao_original - 0.05)
        if segmento_chega_no_fim and self.config.use_fade_out and self.config.fade_out_seconds > 0:
            duracao_fade = min(self.config.fade_out_seconds, duracao_segmento)
            inicio = max(0, duracao_segmento - duracao_fade)
            filtros.append(f"afade=t=out:st={inicio}:d={duracao_fade}")

        return ",".join(filtros) if filtros else None

    def processar_audios_teste(self, tracks_teste: list[TrackInfo], tracks_originais: list[TrackInfo], duracao_total: float) -> list[Path]:
        self.stage("Processando músicas do teste de 30s")
        arquivos_processados: list[Path] = []
        duracao_processada = 0.0
        inicio_bloco = self.progresso_peso
        mapa_duracoes_originais = {track.arquivo.resolve(): track.duracao for track in tracks_originais}

        for i, track in enumerate(tracks_teste, start=1):
            CONTROLE_EXECUCAO.verificar_cancelamento()
            self.stage(f"Processando trecho {i}/{len(tracks_teste)}: {track.titulo}")
            self.log(f"\nProcessando trecho de teste {i}/{len(tracks_teste)}: {track.arquivo.name} ({segundos_para_legivel(track.duracao)})\n")

            saida = TEMP_DIR / f"audio_teste_{i:03d}.wav"
            CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida)

            comando = [
                str(FFMPEG),
                "-y",
                "-i", str(track.arquivo),
                "-t", segundos_para_ffmpeg(track.duracao),
                "-vn",
                "-ar", "48000",
                "-ac", "2",
            ]

            duracao_original = mapa_duracoes_originais.get(track.arquivo.resolve(), track.duracao)
            filtro = self.criar_filtro_fade_teste(track.duracao, duracao_original)
            if filtro:
                comando += ["-af", filtro]

            comando += [
                "-c:a", "pcm_s16le",
                "-progress", "pipe:1",
                "-nostats",
                str(saida),
            ]

            progresso_inicio_audio = inicio_bloco + ((duracao_processada / max(duracao_total, 0.1)) * PESO_PROCESSAR_AUDIOS)
            peso_audio_atual = (track.duracao / max(duracao_total, 0.1)) * PESO_PROCESSAR_AUDIOS

            self.rodar_ffmpeg_com_progresso(
                comando=comando,
                duracao_etapa=track.duracao,
                progresso_inicio_peso=progresso_inicio_audio,
                peso_etapa=peso_audio_atual,
            )

            duracao_processada += track.duracao
            arquivos_processados.append(saida)

        self.progresso_peso = inicio_bloco + PESO_PROCESSAR_AUDIOS
        self.emitir_progresso_por_peso(self.progresso_peso)
        return arquivos_processados

    def gerar_teste_30s(self) -> Path:
        self.validar()
        self.preparar_pastas()
        self.progress(0)
        self.stage("Preparando render de teste de 30s")
        self.log("\n=== Render de teste de 30 segundos ===\n")
        self.log("O teste renderiza somente o começo da playlist, com textos, intro, áudio de fundo e marca d'água.\n")

        self.testar_filtro_subtitles()
        usar_gpu = self.config.use_gpu and self.testar_nvenc()

        tracks_originais = self.detectar_tracks()
        duracao_teste = 30.0
        tracks_teste = self.selecionar_tracks_teste(tracks_originais, duracao_teste)
        if not tracks_teste:
            raise ErroRender("Não foi possível preparar músicas para o teste de 30s.")

        duracao_total_musica = sum(track.duracao for track in tracks_teste)
        self.log("\n=== Trechos usados no teste ===\n")
        for i, track in enumerate(tracks_teste, start=1):
            self.log(
                f"{i:02d}. {track.titulo} | "
                f"{segundos_para_legivel(track.inicio)} - {segundos_para_legivel(track.fim)} "
                f"({segundos_para_legivel(track.duracao)})\n"
            )

        arquivos_processados = self.processar_audios_teste(tracks_teste, tracks_originais, duracao_total_musica)
        audio_final = self.concatenar_audios(arquivos_processados)
        audio_final = self.normalizar_audio(audio_final, duracao_total_musica)
        saida_final = self.montar_video(audio_final, duracao_teste, tracks_teste, usar_gpu, prefixo_saida="teste_30s")

        self.stage("Teste finalizado")
        self.progress(100)
        self.log("\nTeste de 30 segundos finalizado com sucesso!\n")
        self.log(f"Vídeo de teste criado em: {saida_final}\n")
        return saida_final

    def gerar_preview_intro(self) -> Path:
        self.validar()
        self.preparar_pastas()
        self.stage("Gerando prévia da intro com música")
        intro = self.config.intro
        frases = self.frases_intro_ativas() if intro.enabled else []
        tracks = self.detectar_tracks()

        duracao_intro = max([frase.inicio + frase.duracao for frase in frases], default=12.0)
        # A prévia inclui alguns segundos extras depois da intro para você ouvir a relação
        # entre música, chuva/fundo e som de digitação.
        duracao = duracao_intro + 6.0
        duracao = min(max(duracao, 8.0), 75.0)
        saida = self.config.output_folder / f"preview_intro_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida)

        usar_typing = bool(intro.enabled and intro.typing_audio_path)
        usar_fundo = self.config.background_audio_path is not None
        usar_gpu = self.config.use_gpu and self.testar_nvenc()
        delay_musica = max(0.0, intro.delay_music_seconds if intro.enabled else 0.0)

        # Entrada 0 = vídeo base; entrada 1 = primeira música detectada.
        primeira_musica = tracks[0].arquivo
        comando = [
            str(FFMPEG),
            "-y",
            "-stream_loop", "-1",
            "-i", str(self.config.video_path),
            "-i", str(primeira_musica),
        ]

        proximo_indice = 2
        indice_fundo = None
        indice_typing = None
        indice_watermark_imagem = None
        usar_watermark_imagem = (
            self.config.watermark.enabled
            and self.config.watermark.mode == "imagem"
            and bool(self.config.watermark.image_path)
        )

        if usar_fundo:
            indice_fundo = proximo_indice
            proximo_indice += 1
            comando += ["-stream_loop", "-1", "-i", str(self.config.background_audio_path)]

        if usar_typing:
            indice_typing = proximo_indice
            proximo_indice += 1
            comando += ["-stream_loop", "-1", "-i", str(intro.typing_audio_path)]

        if usar_watermark_imagem:
            indice_watermark_imagem = proximo_indice
            proximo_indice += 1
            comando += ["-loop", "1", "-i", str(self.config.watermark.image_path)]

        # Usa drawtext direto também na prévia, sem subtitles/libass.
        # Isso evita o crash 3221225477 em algumas builds novas do FFmpeg no Windows.
        filtros = [self.criar_filtro_video([], indice_watermark_imagem if usar_watermark_imagem else None)]

        audio_labels: list[str] = []
        filtros.append(f"[1:a]atrim=0:{segundos_para_ffmpeg(duracao)},asetpts=PTS-STARTPTS[music_raw]")
        if delay_musica > 0:
            atraso_ms = int(round(delay_musica * 1000))
            filtros.append(
                f"[music_raw]adelay={atraso_ms}:all=1,apad=whole_dur={segundos_para_ffmpeg(duracao)},"
                f"atrim=0:{segundos_para_ffmpeg(duracao)},asetpts=PTS-STARTPTS,volume=1.0[music]"
            )
        else:
            filtros.append(
                f"[music_raw]apad=whole_dur={segundos_para_ffmpeg(duracao)},"
                f"atrim=0:{segundos_para_ffmpeg(duracao)},asetpts=PTS-STARTPTS,volume=1.0[music]"
            )
        audio_labels.append("[music]")

        if usar_fundo:
            filtros.append(
                f"[{indice_fundo}:a]volume={self.config.background_volume},"
                f"atrim=0:{segundos_para_ffmpeg(duracao)},asetpts=PTS-STARTPTS[bg]"
            )
            audio_labels.append("[bg]")

        if usar_typing and indice_typing is not None:
            parts: list[str] = []
            for idx, frase in enumerate(frases):
                tempos = self.tempos_intro_frase(frase)

                type_delay_ms = int(round(tempos["inicio_digitando"] * 1000))
                filtros.append(
                    f"[{indice_typing}:a]atrim=0:{segundos_para_ffmpeg(tempos['dur_digitando'])},"
                    f"asetpts=PTS-STARTPTS,volume={intro.typing_volume},"
                    f"adelay={type_delay_ms}:all=1[ty{idx}a]"
                )
                parts.append(f"[ty{idx}a]")

                if intro.backspace_audio_enabled:
                    back_delay_ms = int(round(tempos["inicio_backspace"] * 1000))
                    filtros.append(
                        f"[{indice_typing}:a]atrim=0:{segundos_para_ffmpeg(tempos['dur_backspace'])},"
                        f"asetpts=PTS-STARTPTS,volume={intro.typing_volume},"
                        f"adelay={back_delay_ms}:all=1[ty{idx}b]"
                    )
                    parts.append(f"[ty{idx}b]")

            if parts:
                filtros.append(f"{''.join(parts)}amix=inputs={len(parts)}:duration=longest:dropout_transition=0[typing]")
                audio_labels.append("[typing]")

        if len(audio_labels) == 1:
            filtros.append(f"{audio_labels[0]}anull[aout]")
        else:
            filtros.append(f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=1[aout]")

        arquivo_filtro = TEMP_DIR / "filter_preview_intro.txt"
        arquivo_filtro.write_text(";\n".join(filtros), encoding="utf-8")

        self.log("\nPrévia da intro usando música:\n")
        self.log(f"Música: {primeira_musica.name}\n")
        self.log(f"Duração da prévia: {segundos_para_legivel(duracao)}\n")

        comando += ["-/filter_complex", str(arquivo_filtro), "-t", str(duracao), "-map", "[vout]", "-map", "[aout]"]
        if usar_gpu:
            comando += ["-c:v", "h264_nvenc", "-preset", NVENC_PRESET, "-rc", "vbr", "-cq", NVENC_CQ, "-b:v", "0"]
        else:
            comando += ["-c:v", "libx264", "-preset", "medium", "-crf", "22"]
        comando += ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-progress", "pipe:1", "-nostats", str(saida)]
        self.rodar_ffmpeg_com_progresso(comando, duracao, 0.0, 1.0)
        return saida

    def testar_nvenc(self) -> bool:
        if not self.config.use_gpu:
            return False

        self.stage("Verificando NVENC")
        comando = [str(FFMPEG), "-hide_banner", "-encoders"]
        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            **criar_kwargs_subprocess_controlado(),
        )
        saida = resultado.stdout + resultado.stderr
        if "h264_nvenc" not in saida:
            self.log("\nAviso: h264_nvenc não foi encontrado neste FFmpeg. Usando CPU/libx264.\n")
            return False
        self.log("\nNVENC encontrado: GPU ativada.\n")
        return True

    def testar_filtro_subtitles(self):
        self.stage("Verificando filtro subtitles")
        comando = [str(FFMPEG), "-hide_banner", "-filters"]
        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            **criar_kwargs_subprocess_controlado(),
        )
        saida = resultado.stdout + resultado.stderr
        if "subtitles" not in saida:
            self.log("\nAviso: o filtro subtitles/libass pode não estar disponível no FFmpeg.\n")
        else:
            self.log("\nFiltro subtitles/libass encontrado.\n")


# ==========================
# UI PYSIDE6
# ==========================

try:
    from PySide6.QtCore import QEasingCurve, QPoint, Property, QPropertyAnimation, QRectF, QSize, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QPixmap, QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractSpinBox,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QFontComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QTextEdit,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("PySide6 não está instalado.")
    print("Instale com: pip install PySide6")
    sys.exit(1)


# ---------- Widgets visuais ----------

class PillButton(QPushButton):
    def __init__(self, texto="", kind="normal", parent=None):
        super().__init__(texto, parent)
        self.kind = kind
        self._hover_progress = 0.0
        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(30)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.setFlat(True)

    def getHoverProgress(self):
        return self._hover_progress

    def setHoverProgress(self, valor):
        self._hover_progress = float(valor)
        self.update()

    hoverProgress = Property(float, getHoverProgress, setHoverProgress)

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def _cores(self):
        if not self.isEnabled():
            return QColor("#2B2D30"), QColor("#2B2D30"), QColor("#777B80"), QColor("#3A3D42")
        if self.kind == "primary":
            return QColor("#555B62"), QColor("#676E76"), QColor("#F4F5F6"), QColor("#7A828B")
        if self.kind == "danger":
            return QColor("#7A3B3B"), QColor("#8C4848"), QColor("#FFF7F7"), QColor("#A25A5A")
        if self.kind == "title":
            return QColor("#25272B"), QColor("#303338"), QColor("#F0F1F2"), QColor("#42464D")
        return QColor("#34373D"), QColor("#42464D"), QColor("#E8EAED"), QColor("#555B63")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        base, hover, texto, borda = self._cores()
        t = self._hover_progress
        cor = QColor(
            int(base.red() + (hover.red() - base.red()) * t),
            int(base.green() + (hover.green() - base.green()) * t),
            int(base.blue() + (hover.blue() - base.blue()) * t),
        )

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        painter.setPen(QPen(borda, 1))
        painter.setBrush(cor)
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(texto)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())


class ToggleSwitch(QCheckBox):
    """Toggle estilo celular, com trilho e bolinha sempre proporcionais.

    Mantém a API de QCheckBox: isChecked(), setChecked() e stateChanged.
    """
    TRACK_W = 46
    TRACK_H = 24
    KNOB_D = 20
    HEIGHT = 30
    GAP_TEXT = 10

    def __init__(self, texto="", parent=None, checked_color: str = "#5EA0FF"):
        super().__init__(texto, parent)
        self._offset = 1.0 if self.isChecked() else 0.0
        self._checked_color = QColor(checked_color)
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setTristate(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stateChanged.connect(self._animar_estado)

    def sizeHint(self):
        texto_largura = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        largura = self.TRACK_W + (self.GAP_TEXT + texto_largura if texto_largura else 0)
        return QSize(largura, self.HEIGHT)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def getOffset(self):
        return self._offset

    def setOffset(self, valor):
        self._offset = max(0.0, min(1.0, float(valor)))
        self.update()

    offset = Property(float, getOffset, setOffset)

    def _animar_estado(self, *args):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        if self._anim.state() != QPropertyAnimation.Running:
            self._offset = 1.0 if checked else 0.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        track_x = 0.5
        track_y = (self.HEIGHT - self.TRACK_H) / 2
        track = QRectF(track_x, track_y, self.TRACK_W, self.TRACK_H)

        if not self.isEnabled():
            track_color = QColor("#35383D")
            knob_color = QColor("#858A91")
            text_color = QColor("#777B80")
            border_color = QColor("#484B51")
        elif self.isChecked():
            track_color = self._checked_color
            knob_color = QColor("#FFFFFF")
            text_color = QColor("#EDEFF2")
            border_color = self._checked_color.lighter(112)
        else:
            track_color = QColor("#4A4D52")
            knob_color = QColor("#F1F2F3")
            text_color = QColor("#C9CCD1")
            border_color = QColor("#63676E")

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, self.TRACK_H / 2, self.TRACK_H / 2)

        knob_margin = 2
        knob_x = track_x + knob_margin + self._offset * (self.TRACK_W - self.KNOB_D - (knob_margin * 2))
        knob_y = track_y + (self.TRACK_H - self.KNOB_D) / 2
        knob = QRectF(knob_x, knob_y, self.KNOB_D, self.KNOB_D)
        painter.setPen(QPen(QColor(0, 0, 0, 42), 1))
        painter.setBrush(knob_color)
        painter.drawEllipse(knob)

        if self.text():
            text_rect = self.rect().adjusted(self.TRACK_W + self.GAP_TEXT, 0, 0, 0)
            painter.setPen(text_color)
            painter.setFont(self.font())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


def aplicar_visual_campos_numericos(widget: QWidget):
    """Remove os botões laterais nativos dos spinboxes e padroniza o visual.

    Em alguns temas do Windows, os botões up/down do QSpinBox/QDoubleSpinBox
    ficam com artefatos escuros e cantos quebrados. Como os campos deste app
    funcionam bem por digitação e scroll do mouse, usamos um visual limpo e
    consistente, igual a um campo arredondado normal.
    """
    for spin in widget.findChildren(QAbstractSpinBox):
        try:
            spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            spin.setKeyboardTracking(False)
            spin.setAccelerated(True)
            spin.setAlignment(Qt.AlignLeft)
            spin.setMinimumHeight(max(spin.minimumHeight(), 28))
            spin.setContentsMargins(0, 0, 0, 0)
            line = spin.lineEdit()
            if line is not None:
                line.setAlignment(Qt.AlignLeft)
                line.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass

class Card(QFrame):
    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(10, 0, 10, 8)
        self.layout_principal.setSpacing(8)

        label = QLabel(titulo)
        label.setObjectName("CardTitle")
        self.layout_principal.addWidget(label)

    def addLayout(self, layout):
        self.layout_principal.addLayout(layout)

    def addWidget(self, widget):
        self.layout_principal.addWidget(widget)


class PathPicker(QWidget):
    def __init__(self, label: str, mode: str, filter_text: str = "Todos os arquivos (*.*)", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.filter_text = filter_text

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(2)

        self.label = QLabel(label)
        self.label.setObjectName("FieldLabel")
        self.label.setFixedWidth(150)
        self.line = QLineEdit()
        self.line.setPlaceholderText("Nenhum caminho escolhido")
        self.line.setReadOnly(True)
        self.line.setMinimumHeight(24)
        self.line.setFixedWidth(300)
        self.line.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button = PillButton("Escolher", "normal")
        self.button.setFixedWidth(76)
        self.button.clicked.connect(self.escolher)

        layout.addWidget(self.label, 0, 0)
        layout.addWidget(self.line, 0, 1)
        layout.addWidget(self.button, 0, 2)
        layout.setColumnStretch(1, 1)

    def ocultar_rotulo(self):
        self.label.hide()
        self.label.setFixedWidth(0)

    def escolher(self):
        if self.mode == "file":
            caminho, _ = QFileDialog.getOpenFileName(self, self.label.text(), str(SCRIPT_DIR), self.filter_text)
        elif self.mode == "folder":
            caminho = QFileDialog.getExistingDirectory(self, self.label.text(), str(SCRIPT_DIR))
        else:
            caminho = ""
        if caminho:
            self.line.setText(caminho)

    def path(self) -> Path | None:
        texto = self.line.text().strip()
        return Path(texto) if texto else None

    def set_path(self, caminho: str | Path | None):
        self.line.setText(str(caminho) if caminho else "")



class WatermarkPreview(QFrame):
    """Prévia visual aproximada da marca d'água dentro do modal.

    A área simula um vídeo 16:9 em 1920x1080 e aplica posição, margem,
    opacidade, largura da imagem, fonte e cor do texto.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = WatermarkConfig()
        self.setObjectName("WatermarkPreview")
        self.setMinimumSize(430, 242)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_config(self, config: WatermarkConfig):
        self.config = config
        self.update()

    def _video_rect(self) -> QRectF:
        area = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        proporcao = 16 / 9
        w = area.width()
        h = w / proporcao
        if h > area.height():
            h = area.height()
            w = h * proporcao
        x = area.x() + (area.width() - w) / 2
        y = area.y() + (area.height() - h) / 2
        return QRectF(x, y, w, h)

    def _posicionar(self, video: QRectF, item_w: float, item_h: float, cfg: WatermarkConfig) -> tuple[float, float]:
        mx = max(0, int(cfg.margin_x)) * (video.width() / 1920.0)
        my = max(0, int(cfg.margin_y)) * (video.height() / 1080.0)
        pos = cfg.position or "inferior_direita"

        if pos == "inferior_direita":
            return video.right() - item_w - mx, video.bottom() - item_h - my
        if pos == "inferior_esquerda":
            return video.left() + mx, video.bottom() - item_h - my
        if pos == "inferior_centro":
            return video.left() + (video.width() - item_w) / 2, video.bottom() - item_h - my
        if pos == "superior_direita":
            return video.right() - item_w - mx, video.top() + my
        if pos == "superior_esquerda":
            return video.left() + mx, video.top() + my
        if pos == "superior_centro":
            return video.left() + (video.width() - item_w) / 2, video.top() + my
        if pos == "centro":
            return video.left() + (video.width() - item_w) / 2, video.top() + (video.height() - item_h) / 2
        return video.right() - item_w - mx, video.bottom() - item_h - my

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        video = self._video_rect()
        painter.setPen(QPen(QColor("#50545B"), 1))
        painter.setBrush(QColor("#17181A"))
        painter.drawRoundedRect(video, 12, 12)

        # Fundo simples para dar referência visual sem depender do vídeo real.
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for i in range(1, 4):
            x = video.left() + video.width() * i / 4
            painter.drawLine(int(x), int(video.top()), int(x), int(video.bottom()))
        for i in range(1, 3):
            y = video.top() + video.height() * i / 3
            painter.drawLine(int(video.left()), int(y), int(video.right()), int(y))

        painter.setPen(QColor("#8E939B"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(video.adjusted(12, 9, -12, -9), Qt.AlignTop | Qt.AlignLeft, "Prévia aproximada 16:9")

        cfg = self.config
        if not cfg.enabled:
            painter.setPen(QColor("#777B80"))
            painter.drawText(video, Qt.AlignCenter, "Marca d'água desativada")
            return

        painter.save()
        painter.setClipRect(video)

        if cfg.mode == "imagem":
            caminho = Path(cfg.image_path or "")
            pix = QPixmap(str(caminho)) if caminho.exists() else QPixmap()
            if pix.isNull():
                painter.setPen(QColor("#D8A0A0"))
                painter.drawText(video, Qt.AlignCenter, "Escolha uma imagem válida para visualizar")
                painter.restore()
                return

            if int(cfg.image_width or 0) > 0:
                preview_w = max(8, int(cfg.image_width * (video.width() / 1920.0)))
            else:
                preview_w = min(int(video.width() * 0.22), pix.width())
            scaled = pix.scaledToWidth(preview_w, Qt.SmoothTransformation)
            x, y = self._posicionar(video, scaled.width(), scaled.height(), cfg)
            painter.setOpacity(max(0.0, min(1.0, float(cfg.opacity))))
            painter.drawPixmap(int(x), int(y), scaled)
            painter.restore()
            return

        texto = (cfg.text or "").strip() or "Marca"
        font_size = max(7, int(cfg.font_size * (video.height() / 1080.0)))
        fonte = QFont(cfg.font_family or "Segoe UI", font_size)
        painter.setFont(fonte)
        bounds = painter.boundingRect(video, Qt.AlignLeft | Qt.AlignTop, texto)
        item_w = bounds.width()
        item_h = bounds.height()
        x, y = self._posicionar(video, item_w, item_h, cfg)

        sombra = QColor("#000000")
        sombra.setAlphaF(max(0.0, min(1.0, float(cfg.shadow_opacity))))
        cor = QColor(limpar_hex(cfg.color))
        cor.setAlphaF(max(0.0, min(1.0, float(cfg.opacity))))

        painter.setPen(sombra)
        painter.drawText(QRectF(x + 2, y + 2, item_w + 8, item_h + 8), Qt.AlignLeft | Qt.AlignTop, texto)
        painter.setPen(cor)
        painter.drawText(QRectF(x, y, item_w + 8, item_h + 8), Qt.AlignLeft | Qt.AlignTop, texto)
        painter.restore()

# ---------- Modais ----------

class DialogTitleBar(QFrame):
    def __init__(self, parent_dialog, titulo: str):
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.drag_position: QPoint | None = None
        self.setObjectName("DialogTitleBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 10, 5)
        layout.setSpacing(8)

        label = QLabel(titulo)
        label.setObjectName("DialogTitleText")

        self.min_btn = PillButton("—", "title")
        self.min_btn.setFixedSize(30, 24)
        self.min_btn.clicked.connect(parent_dialog.showMinimized)

        self.close_btn = PillButton("×", "danger")
        self.close_btn.setFixedSize(30, 24)
        self.close_btn.clicked.connect(parent_dialog.reject)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_dialog.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() & Qt.LeftButton:
            self.parent_dialog.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)


def criar_layout_modal_frameless(dialog: QDialog, titulo: str) -> QVBoxLayout:
    dialog.setWindowTitle(titulo)
    dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
    dialog.setAttribute(Qt.WA_TranslucentBackground, True)

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(8, 8, 8, 8)
    outer.setSpacing(0)

    frame = QFrame()
    frame.setObjectName("DialogFrame")
    frame_layout = QVBoxLayout(frame)
    frame_layout.setContentsMargins(0, 0, 0, 0)
    frame_layout.setSpacing(0)

    frame_layout.addWidget(DialogTitleBar(dialog, titulo))

    body = QVBoxLayout()
    body.setContentsMargins(14, 10, 14, 12)
    body.setSpacing(8)
    frame_layout.addLayout(body)

    outer.addWidget(frame)
    return body


class FonteDialog(QDialog):
    def __init__(self, config: FonteTextoConfig, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.config = FonteTextoConfig(**config.__dict__)
        self.setMinimumWidth(560)
        self._build()

    def _build(self):
        layout = criar_layout_modal_frameless(self, "Configurar fonte dos nomes")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(7)
        grid.setContentsMargins(0, 0, 0, 0)

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.config.font_family))

        self.position = QComboBox()
        popular_combo_posicoes(self.position, self.config.position)

        self.size = QSpinBox()
        self.size.setRange(8, 160)
        self.size.setValue(self.config.font_size)
        self.size.setFixedWidth(92)

        self.color = QLineEdit(limpar_hex(self.config.color))
        self.color.setFixedWidth(110)
        self.color_btn = PillButton("Cor", "normal")
        self.color_btn.setFixedWidth(62)
        self.color_btn.clicked.connect(self.escolher_cor)

        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.05, 1.0)
        self.opacity.setSingleStep(0.05)
        self.opacity.setDecimals(2)
        self.opacity.setValue(self.config.opacity)
        self.opacity.setFixedWidth(92)

        self.margin_x = QSpinBox()
        self.margin_x.setRange(0, 500)
        self.margin_x.setValue(self.config.margin_left)
        self.margin_x.setFixedWidth(92)

        self.margin_y = QSpinBox()
        self.margin_y.setRange(0, 500)
        self.margin_y.setValue(self.config.margin_bottom)
        self.margin_y.setFixedWidth(92)

        self.typing = QDoubleSpinBox()
        self.typing.setRange(0.1, 20.0)
        self.typing.setSingleStep(0.1)
        self.typing.setDecimals(1)
        self.typing.setValue(self.config.typing_duration)
        self.typing.setSuffix(" s")
        self.typing.setFixedWidth(92)

        self.erasing = QDoubleSpinBox()
        self.erasing.setRange(0.1, 20.0)
        self.erasing.setSingleStep(0.1)
        self.erasing.setDecimals(1)
        self.erasing.setValue(self.config.erasing_duration)
        self.erasing.setSuffix(" s")
        self.erasing.setFixedWidth(92)

        grid.addWidget(QLabel("Fonte do sistema"), 0, 0)
        grid.addWidget(self.font_combo, 0, 1, 1, 3)
        grid.addWidget(QLabel("Posição"), 1, 0)
        grid.addWidget(self.position, 1, 1)
        grid.addWidget(QLabel("Tamanho"), 1, 2)
        grid.addWidget(self.size, 1, 3)
        grid.addWidget(QLabel("Cor"), 2, 0)
        cor_row = QHBoxLayout()
        cor_row.setSpacing(6)
        cor_row.addWidget(self.color)
        cor_row.addWidget(self.color_btn)
        cor_row.addStretch(1)
        grid.addLayout(cor_row, 2, 1)
        grid.addWidget(QLabel("Opacidade"), 2, 2)
        grid.addWidget(self.opacity, 2, 3)
        grid.addWidget(QLabel("Margem horiz."), 3, 0)
        grid.addWidget(self.margin_x, 3, 1)
        grid.addWidget(QLabel("Margem vert."), 3, 2)
        grid.addWidget(self.margin_y, 3, 3)
        grid.addWidget(QLabel("Digitando"), 4, 0)
        grid.addWidget(self.typing, 4, 1)
        grid.addWidget(QLabel("Apagando"), 4, 2)
        grid.addWidget(self.erasing, 4, 3)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        cancelar = PillButton("Cancelar", "normal")
        salvar = PillButton("Salvar", "primary")
        cancelar.clicked.connect(self.reject)
        salvar.clicked.connect(self.accept)
        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        layout.addLayout(botoes)

        self.setStyleSheet(STYLE_DARK)
        aplicar_visual_campos_numericos(self)

    def escolher_cor(self):
        cor = QColorDialog.getColor(QColor(limpar_hex(self.color.text())), self, "Escolher cor")
        if cor.isValid():
            self.color.setText(cor.name().upper())

    def resultado(self) -> FonteTextoConfig:
        return FonteTextoConfig(
            font_family=self.font_combo.currentFont().family(),
            font_file="",
            font_size=self.size.value(),
            color=limpar_hex(self.color.text()),
            opacity=self.opacity.value(),
            position=self.position.currentData(),
            margin_left=self.margin_x.value(),
            margin_bottom=self.margin_y.value(),
            typing_duration=self.typing.value(),
            erasing_duration=self.erasing.value(),
            shadow_opacity=self.config.shadow_opacity,
        )


class WatermarkDialog(QDialog):
    def __init__(self, config: WatermarkConfig, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.config = WatermarkConfig(**config.__dict__)
        self.setMinimumWidth(720)
        self._build()

    def _build(self):
        layout = criar_layout_modal_frameless(self, "Configurar marca d'água")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(7)
        grid.setContentsMargins(0, 0, 0, 0)

        self.enabled = ToggleSwitch("Usar marca d'água")
        self.enabled.setChecked(self.config.enabled)
        self.enabled.stateChanged.connect(self.atualizar_modo)

        self.mode_image = ToggleSwitch("Usar imagem no lugar de texto")
        self.mode_image.setChecked(self.config.mode == "imagem")
        self.mode_image.stateChanged.connect(self.atualizar_modo)

        self.text = QLineEdit(self.config.text)

        self.image_path = QLineEdit(self.config.image_path)
        self.image_path.setReadOnly(True)
        self.image_btn = PillButton("Escolher", "normal")
        self.image_btn.setFixedWidth(82)
        self.image_btn.clicked.connect(self.escolher_imagem)
        self.clear_image_btn = PillButton("Limpar", "normal")
        self.clear_image_btn.setFixedWidth(66)
        self.clear_image_btn.clicked.connect(lambda: self.image_path.setText(""))

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.config.font_family))

        self.size = QSpinBox()
        self.size.setRange(8, 200)
        self.size.setValue(self.config.font_size)
        self.size.setFixedWidth(92)

        self.image_width = QSpinBox()
        self.image_width.setRange(0, 2000)
        self.image_width.setValue(int(getattr(self.config, "image_width", 180) or 0))
        self.image_width.setSuffix(" px")
        self.image_width.setSpecialValueText("Original")
        self.image_width.setFixedWidth(112)

        self.color = QLineEdit(limpar_hex(self.config.color))
        self.color.setFixedWidth(110)
        self.color_btn = PillButton("Cor", "normal")
        self.color_btn.setFixedWidth(62)
        self.color_btn.clicked.connect(self.escolher_cor)

        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.05, 1.0)
        self.opacity.setSingleStep(0.05)
        self.opacity.setDecimals(2)
        self.opacity.setValue(self.config.opacity)
        self.opacity.setFixedWidth(92)

        self.position = QComboBox()
        popular_combo_posicoes(self.position, self.config.position)

        self.margin_x = QSpinBox()
        self.margin_x.setRange(0, 500)
        self.margin_x.setValue(self.config.margin_x)
        self.margin_x.setFixedWidth(92)

        self.margin_y = QSpinBox()
        self.margin_y.setRange(0, 500)
        self.margin_y.setValue(self.config.margin_y)
        self.margin_y.setFixedWidth(92)

        grid.addWidget(self.enabled, 0, 0, 1, 2)
        grid.addWidget(self.mode_image, 0, 2, 1, 2)
        grid.addWidget(QLabel("Texto"), 1, 0)
        grid.addWidget(self.text, 1, 1, 1, 3)
        grid.addWidget(QLabel("Imagem"), 2, 0)
        img_row = QHBoxLayout()
        img_row.setSpacing(6)
        img_row.addWidget(self.image_path, 1)
        img_row.addWidget(self.image_btn)
        img_row.addWidget(self.clear_image_btn)
        grid.addLayout(img_row, 2, 1, 1, 3)
        grid.addWidget(QLabel("Fonte sistema"), 3, 0)
        grid.addWidget(self.font_combo, 3, 1)
        grid.addWidget(QLabel("Tam. texto"), 3, 2)
        grid.addWidget(self.size, 3, 3)
        grid.addWidget(QLabel("Largura img."), 4, 0)
        grid.addWidget(self.image_width, 4, 1)
        grid.addWidget(QLabel("Opacidade"), 4, 2)
        grid.addWidget(self.opacity, 4, 3)
        grid.addWidget(QLabel("Cor texto"), 5, 0)
        cor_row = QHBoxLayout()
        cor_row.setSpacing(6)
        cor_row.addWidget(self.color)
        cor_row.addWidget(self.color_btn)
        cor_row.addStretch(1)
        grid.addLayout(cor_row, 5, 1)
        grid.addWidget(QLabel("Posição"), 5, 2)
        grid.addWidget(self.position, 5, 3)
        grid.addWidget(QLabel("Margem horiz."), 6, 0)
        grid.addWidget(self.margin_x, 6, 1)
        grid.addWidget(QLabel("Margem vert."), 6, 2)
        grid.addWidget(self.margin_y, 6, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        layout.addLayout(grid)

        preview_label = QLabel("Prévia da marca d'água")
        preview_label.setObjectName("FieldLabel")
        layout.addWidget(preview_label)
        self.preview = WatermarkPreview()
        layout.addWidget(self.preview)

        self._conectar_preview()

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        cancelar = PillButton("Cancelar", "normal")
        salvar = PillButton("Salvar", "primary")
        cancelar.clicked.connect(self.reject)
        salvar.clicked.connect(self.accept)
        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        layout.addLayout(botoes)

        self.atualizar_modo()
        self.setStyleSheet(STYLE_DARK)
        aplicar_visual_campos_numericos(self)

    def _config_atual_para_preview(self) -> WatermarkConfig:
        modo = "imagem" if self.mode_image.isChecked() else "texto"
        return WatermarkConfig(
            enabled=self.enabled.isChecked(),
            mode=modo,
            text=self.text.text(),
            image_path=self.image_path.text().strip(),
            image_width=self.image_width.value(),
            font_family=self.font_combo.currentFont().family(),
            font_file="",
            font_size=self.size.value(),
            color=limpar_hex(self.color.text()),
            opacity=self.opacity.value(),
            position=self.position.currentData(),
            margin_x=self.margin_x.value(),
            margin_y=self.margin_y.value(),
            shadow_opacity=self.config.shadow_opacity,
        )

    def _conectar_preview(self):
        self.enabled.stateChanged.connect(self.atualizar_preview)
        self.mode_image.stateChanged.connect(self.atualizar_preview)
        self.text.textChanged.connect(self.atualizar_preview)
        self.image_path.textChanged.connect(self.atualizar_preview)
        self.font_combo.currentFontChanged.connect(self.atualizar_preview)
        self.size.valueChanged.connect(self.atualizar_preview)
        self.image_width.valueChanged.connect(self.atualizar_preview)
        self.color.textChanged.connect(self.atualizar_preview)
        self.opacity.valueChanged.connect(self.atualizar_preview)
        self.position.currentIndexChanged.connect(self.atualizar_preview)
        self.margin_x.valueChanged.connect(self.atualizar_preview)
        self.margin_y.valueChanged.connect(self.atualizar_preview)

    def atualizar_preview(self, *args):
        if hasattr(self, "preview"):
            self.preview.set_config(self._config_atual_para_preview())

    def atualizar_modo(self, *args):
        ativo = self.enabled.isChecked()
        modo_imagem = self.mode_image.isChecked()
        self.mode_image.setEnabled(ativo)
        for widget in (self.text, self.font_combo, self.size, self.color, self.color_btn):
            widget.setEnabled(ativo and not modo_imagem)
        for widget in (self.image_path, self.image_btn, self.clear_image_btn, self.image_width):
            widget.setEnabled(ativo and modo_imagem)
        for widget in (self.opacity, self.position, self.margin_x, self.margin_y):
            widget.setEnabled(ativo)
        self.atualizar_preview()

    def escolher_imagem(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher imagem da marca d'água",
            str(SCRIPT_DIR),
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;Todos (*.*)",
        )
        if caminho:
            self.image_path.setText(caminho)

    def escolher_cor(self):
        cor = QColorDialog.getColor(QColor(limpar_hex(self.color.text())), self, "Escolher cor")
        if cor.isValid():
            self.color.setText(cor.name().upper())

    def resultado(self) -> WatermarkConfig:
        modo = "imagem" if self.mode_image.isChecked() else "texto"
        return WatermarkConfig(
            enabled=self.enabled.isChecked(),
            mode=modo,
            text=self.text.text(),
            image_path=self.image_path.text().strip(),
            image_width=self.image_width.value(),
            font_family=self.font_combo.currentFont().family(),
            font_file="",
            font_size=self.size.value(),
            color=limpar_hex(self.color.text()),
            opacity=self.opacity.value(),
            position=self.position.currentData(),
            margin_x=self.margin_x.value(),
            margin_y=self.margin_y.value(),
            shadow_opacity=self.config.shadow_opacity,
        )


class IntroDialog(QDialog):
    def __init__(self, config: IntroTextConfig, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.config = intro_config_from_dict(intro_config_to_dict(config))
        self.setMinimumWidth(880)
        self.setMinimumHeight(620)
        self._build()

    def _build(self):
        layout = criar_layout_modal_frameless(self, "Configurar frases de intro")

        self.enabled = ToggleSwitch("Usar frases no começo do vídeo")
        self.enabled.setChecked(self.config.enabled)
        layout.addWidget(self.enabled)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Início", "Duração", "Frase"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setMinimumHeight(150)
        layout.addWidget(self.table)
        for frase in self.config.phrases:
            self.adicionar_linha(frase)

        row_table = QHBoxLayout()
        add_btn = PillButton("Adicionar frase", "normal")
        remove_btn = PillButton("Remover selecionada", "normal")
        clear_btn = PillButton("Limpar frases", "normal")
        sample_btn = PillButton("Exemplo lo-fi", "normal")
        add_btn.clicked.connect(lambda: self.adicionar_linha(IntroFraseConfig(0.0, 4.0, "")))
        remove_btn.clicked.connect(self.remover_linha)
        clear_btn.clicked.connect(lambda: self.table.setRowCount(0))
        sample_btn.clicked.connect(self.preencher_exemplo)
        row_table.addWidget(add_btn)
        row_table.addWidget(remove_btn)
        row_table.addWidget(clear_btn)
        row_table.addWidget(sample_btn)
        row_table.addStretch(1)
        layout.addLayout(row_table)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(7)

        self.effect = QComboBox()
        self.effect.addItem("Máquina de escrever", "typewriter")
        self.effect.addItem("Fade simples", "fade")
        self.effect.addItem("Aparecer direto", "direct")
        self.effect.addItem("Fade + máquina de escrever", "typewriter_fade")
        idx = self.effect.findData(self.config.effect)
        self.effect.setCurrentIndex(max(0, idx))

        self.typing_cps = QDoubleSpinBox()
        self.typing_cps.setRange(1.0, 80.0)
        self.typing_cps.setValue(self.config.typing_cps)
        self.typing_cps.setSingleStep(1.0)
        self.typing_cps.setSuffix(" car/s")
        self.typing_cps.setFixedWidth(120)

        self.backspace_cps = QDoubleSpinBox()
        self.backspace_cps.setRange(1.0, 120.0)
        self.backspace_cps.setValue(self.config.backspace_cps)
        self.backspace_cps.setSingleStep(1.0)
        self.backspace_cps.setSuffix(" car/s")
        self.backspace_cps.setFixedWidth(120)

        self.backspace_audio = ToggleSwitch("Som no backspace")
        self.backspace_audio.setChecked(self.config.backspace_audio_enabled)

        self.show_cursor = ToggleSwitch("Cursor piscando")
        self.show_cursor.setChecked(self.config.show_cursor)

        self.randomize = ToggleSwitch("Frases aleatórias")
        self.randomize.setChecked(self.config.randomize_phrases)
        self.random_count = QSpinBox()
        self.random_count.setRange(1, 50)
        self.random_count.setValue(self.config.random_count)
        self.random_count.setFixedWidth(90)

        self.delay_music = QDoubleSpinBox()
        self.delay_music.setRange(0.0, 120.0)
        self.delay_music.setValue(self.config.delay_music_seconds)
        self.delay_music.setSingleStep(0.5)
        self.delay_music.setSuffix(" s")
        self.delay_music.setFixedWidth(100)

        self.typing_audio = QLineEdit(self.config.typing_audio_path)
        self.typing_audio.setReadOnly(True)
        typing_btn = PillButton("Escolher", "normal")
        typing_btn.clicked.connect(self.escolher_typing_audio)
        clear_typing = PillButton("Limpar", "normal")
        clear_typing.clicked.connect(lambda: self.typing_audio.setText(""))
        self.typing_volume = QDoubleSpinBox()
        self.typing_volume.setRange(0.0, 2.0)
        self.typing_volume.setSingleStep(0.05)
        self.typing_volume.setDecimals(2)
        self.typing_volume.setValue(self.config.typing_volume)
        self.typing_volume.setFixedWidth(90)

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.config.font_family))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 180)
        self.font_size.setValue(self.config.font_size)
        self.font_size.setFixedWidth(90)
        self.font_weight = QSpinBox()
        self.font_weight.setRange(100, 900)
        self.font_weight.setSingleStep(100)
        self.font_weight.setValue(int(getattr(self.config, "font_weight", 700)))
        self.font_weight.setFixedWidth(90)
        self.shadow_size = QDoubleSpinBox()
        self.shadow_size.setRange(0.0, 10.0)
        self.shadow_size.setSingleStep(0.1)
        self.shadow_size.setDecimals(1)
        self.shadow_size.setValue(float(getattr(self.config, "shadow_size", 1.4)))
        self.shadow_size.setFixedWidth(90)
        self.shadow_opacity = QDoubleSpinBox()
        self.shadow_opacity.setRange(0.0, 1.0)
        self.shadow_opacity.setSingleStep(0.05)
        self.shadow_opacity.setDecimals(2)
        self.shadow_opacity.setValue(float(getattr(self.config, "shadow_opacity", 0.65)))
        self.shadow_opacity.setFixedWidth(90)
        self.color = QLineEdit(limpar_hex(self.config.color))
        self.color.setFixedWidth(110)
        color_btn = PillButton("Cor", "normal")
        color_btn.clicked.connect(self.escolher_cor)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.05, 1.0)
        self.opacity.setDecimals(2)
        self.opacity.setSingleStep(0.05)
        self.opacity.setValue(self.config.opacity)
        self.opacity.setFixedWidth(90)

        self.position = QComboBox()
        popular_combo_posicoes(self.position, self.config.position)
        self.margin_x = QSpinBox()
        self.margin_x.setRange(0, 800)
        self.margin_x.setValue(self.config.margin_x)
        self.margin_x.setFixedWidth(90)
        self.margin_y = QSpinBox()
        self.margin_y.setRange(0, 800)
        self.margin_y.setValue(self.config.margin_y)
        self.margin_y.setFixedWidth(90)

        self.background_box = ToggleSwitch("Fundo preto transparente atrás do texto")
        self.background_box.setChecked(self.config.background_box)
        self.box_opacity = QDoubleSpinBox()
        self.box_opacity.setRange(0.05, 1.0)
        self.box_opacity.setSingleStep(0.05)
        self.box_opacity.setDecimals(2)
        self.box_opacity.setValue(self.config.box_opacity)
        self.box_opacity.setFixedWidth(90)

        grid.addWidget(QLabel("Efeito"), 0, 0)
        grid.addWidget(self.effect, 0, 1)
        grid.addWidget(QLabel("Vel. digitação"), 0, 2)
        grid.addWidget(self.typing_cps, 0, 3)
        grid.addWidget(self.show_cursor, 0, 4)

        grid.addWidget(QLabel("Vel. backspace"), 1, 0)
        grid.addWidget(self.backspace_cps, 1, 1)
        grid.addWidget(self.backspace_audio, 1, 2, 1, 2)

        grid.addWidget(QLabel("Som de digitação"), 2, 0)
        audio_row = QHBoxLayout()
        audio_row.addWidget(self.typing_audio, 1)
        audio_row.addWidget(typing_btn)
        audio_row.addWidget(clear_typing)
        grid.addLayout(audio_row, 2, 1, 1, 3)
        grid.addWidget(QLabel("Volume"), 2, 4)
        grid.addWidget(self.typing_volume, 2, 5)

        grid.addWidget(QLabel("Fonte"), 3, 0)
        grid.addWidget(self.font_combo, 3, 1)
        grid.addWidget(QLabel("Tamanho"), 3, 2)
        grid.addWidget(self.font_size, 3, 3)
        grid.addWidget(QLabel("Opacidade"), 3, 4)
        grid.addWidget(self.opacity, 3, 5)

        grid.addWidget(QLabel("Cor"), 4, 0)
        cor_row = QHBoxLayout()
        cor_row.addWidget(self.color)
        cor_row.addWidget(color_btn)
        cor_row.addStretch(1)
        grid.addLayout(cor_row, 4, 1)
        grid.addWidget(QLabel("Posição"), 4, 2)
        grid.addWidget(self.position, 4, 3)
        grid.addWidget(QLabel("Margem X/Y"), 4, 4)
        xy = QHBoxLayout()
        xy.addWidget(self.margin_x)
        xy.addWidget(self.margin_y)
        grid.addLayout(xy, 4, 5)

        grid.addWidget(QLabel("Peso letra"), 5, 0)
        grid.addWidget(self.font_weight, 5, 1)
        grid.addWidget(QLabel("Grossura sombra"), 5, 2)
        grid.addWidget(self.shadow_size, 5, 3)
        grid.addWidget(QLabel("Opac. sombra"), 5, 4)
        grid.addWidget(self.shadow_opacity, 5, 5)

        grid.addWidget(self.background_box, 6, 0, 1, 3)
        grid.addWidget(QLabel("Opacidade fundo"), 6, 3)
        grid.addWidget(self.box_opacity, 6, 4)
        grid.addWidget(QLabel("Delay música"), 7, 0)
        grid.addWidget(self.delay_music, 7, 1)
        grid.addWidget(self.randomize, 7, 2)
        grid.addWidget(QLabel("Qtd. aleatórias"), 7, 3)
        grid.addWidget(self.random_count, 7, 4)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        presets = QHBoxLayout()
        save_preset = PillButton("Salvar preset", "normal")
        load_preset = PillButton("Carregar preset", "normal")
        save_preset.clicked.connect(self.salvar_preset)
        load_preset.clicked.connect(self.carregar_preset)
        presets.addWidget(save_preset)
        presets.addWidget(load_preset)
        presets.addStretch(1)
        layout.addLayout(presets)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        cancelar = PillButton("Cancelar", "normal")
        salvar = PillButton("Salvar", "primary")
        cancelar.clicked.connect(self.reject)
        salvar.clicked.connect(self.accept)
        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        layout.addLayout(botoes)
        self.setStyleSheet(STYLE_DARK)
        aplicar_visual_campos_numericos(self)

    def adicionar_linha(self, frase: IntroFraseConfig):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(segundos_para_legivel(frase.inicio)))
        self.table.setItem(row, 1, QTableWidgetItem(f"{frase.duracao:.1f}"))
        self.table.setItem(row, 2, QTableWidgetItem(frase.texto))

    def remover_linha(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def preencher_exemplo(self):
        self.table.setRowCount(0)
        exemplos = [
            IntroFraseConfig(0.0, 4.0, "take a slow breath..."),
            IntroFraseConfig(5.0, 4.0, "the record starts turning..."),
            IntroFraseConfig(10.0, 5.0, "outside, the rain forgets the time."),
        ]
        for frase in exemplos:
            self.adicionar_linha(frase)

    def escolher_typing_audio(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher som de digitação",
            str(SCRIPT_DIR),
            "Áudios (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma);;Todos (*.*)",
        )
        if caminho:
            self.typing_audio.setText(caminho)

    def escolher_cor(self):
        cor = QColorDialog.getColor(QColor(limpar_hex(self.color.text())), self, "Escolher cor")
        if cor.isValid():
            self.color.setText(cor.name().upper())

    def _parse_tempo(self, texto: str) -> float:
        texto = (texto or "").strip().replace(",", ".")
        if ":" not in texto:
            return max(0.0, float(texto or 0))
        partes = [float(p) for p in texto.split(":")]
        if len(partes) == 2:
            return max(0.0, partes[0] * 60 + partes[1])
        if len(partes) == 3:
            return max(0.0, partes[0] * 3600 + partes[1] * 60 + partes[2])
        return 0.0

    def resultado(self) -> IntroTextConfig:
        frases: list[IntroFraseConfig] = []
        for row in range(self.table.rowCount()):
            inicio_txt = self.table.item(row, 0).text() if self.table.item(row, 0) else "0"
            dur_txt = self.table.item(row, 1).text() if self.table.item(row, 1) else "4"
            texto = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            if texto.strip():
                frases.append(IntroFraseConfig(self._parse_tempo(inicio_txt), self._parse_tempo(dur_txt), texto.strip()))
        return IntroTextConfig(
            enabled=self.enabled.isChecked(),
            phrases=frases,
            effect=self.effect.currentData(),
            typing_audio_path=self.typing_audio.text().strip(),
            typing_volume=self.typing_volume.value(),
            typing_cps=self.typing_cps.value(),
            backspace_cps=self.backspace_cps.value(),
            backspace_audio_enabled=self.backspace_audio.isChecked(),
            show_cursor=self.show_cursor.isChecked(),
            randomize_phrases=self.randomize.isChecked(),
            random_count=self.random_count.value(),
            delay_music_seconds=self.delay_music.value(),
            font_family=self.font_combo.currentFont().family(),
            font_file="",
            font_size=self.font_size.value(),
            font_weight=self.font_weight.value(),
            color=limpar_hex(self.color.text()),
            opacity=self.opacity.value(),
            position=self.position.currentData(),
            margin_x=self.margin_x.value(),
            margin_y=self.margin_y.value(),
            shadow_opacity=self.shadow_opacity.value(),
            shadow_size=self.shadow_size.value(),
            background_box=self.background_box.isChecked(),
            box_opacity=self.box_opacity.value(),
        )

    def salvar_preset(self):
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar preset de intro", str(SCRIPT_DIR / "intro_preset.json"), "JSON (*.json)")
        if caminho:
            Path(caminho).write_text(json.dumps(intro_config_to_dict(self.resultado()), ensure_ascii=False, indent=2), encoding="utf-8")

    def carregar_preset(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Carregar preset de intro", str(SCRIPT_DIR), "JSON (*.json);;Todos (*.*)")
        if caminho:
            cfg = intro_config_from_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))
            self.config = cfg
            self.close()
            novo = IntroDialog(cfg, self.parent())
            if novo.exec() == QDialog.Accepted:
                self.config = novo.resultado()
                self.accept()



# ---------- Worker ----------

class WorkerRender(QThread):
    log = Signal(str)
    progresso = Signal(int)
    etapa = Signal(str)
    terminado = Signal(bool, str, str)

    def __init__(self, config: RenderConfig, modo: str = "final"):
        super().__init__()
        self.config = config
        self.modo = modo

    def run(self):
        CONTROLE_EXECUCAO.resetar()
        try:
            engine = RenderEngine(
                config=self.config,
                log_cb=self.log.emit,
                progress_cb=self.progresso.emit,
                stage_cb=self.etapa.emit,
            )
            if self.modo == "teste_30s":
                saida = engine.gerar_teste_30s()
                self.terminado.emit(True, "Teste de 30 segundos criado com sucesso.", str(saida))
            else:
                saida = engine.run()
                self.terminado.emit(True, "Vídeo criado com sucesso.", str(saida))
        except RenderCancelado:
            CONTROLE_EXECUCAO.excluir_arquivos_cancelados()
            self.progresso.emit(0)
            self.etapa.emit("Cancelado")
            self.terminado.emit(False, "Renderização cancelada. Arquivos incompletos removidos.", "")
        except Exception as erro:
            CONTROLE_EXECUCAO.excluir_arquivos_cancelados()
            self.etapa.emit("Erro")
            self.log.emit(f"\nERRO:\n{erro}\n")
            self.terminado.emit(False, str(erro), "")

    def cancelar(self):
        CONTROLE_EXECUCAO.solicitar_cancelamento()

    def alternar_pausa(self):
        return CONTROLE_EXECUCAO.alternar_pausa()


# ---------- Janela principal ----------

STYLE_DARK = """
QWidget {
    color: #E6E6E6;
    font-family: "Segoe UI";
    font-size: 12px;
}
QLabel, QCheckBox {
    background: transparent;
}
QWidget#ScrollContent, QScrollArea#MainScroll, QScrollArea#MainScroll > QWidget, QScrollArea#MainScroll > QWidget > QWidget {
    background: transparent;
}
QFrame#RootFrame, QFrame#DialogFrame {
    background: #242527;
    border: 1px solid #3B3D40;
    border-radius: 16px;
}
QFrame#Card {
    background: #2B2C2F;
    border: 1px solid #414348;
    border-radius: 12px;
}
QFrame#SubCard {
    background: #242528;
    border: 1px solid #3A3D42;
    border-radius: 10px;
}
QFrame#WatermarkPreview {
    background: #191A1C;
    border: 1px solid #414348;
    border-radius: 12px;
}
QFrame#TitleBar, QFrame#DialogTitleBar {
    background: #242527;
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
}
QLabel#AppTitle {
    color: #F2F2F2;
    font-size: 16px;
    font-weight: 800;
}
QLabel#Subtitle {
    color: #A5A7AA;
}
QLabel#CardTitle, QLabel#DialogTitle, QLabel#DialogTitleText {
    color: #F1F1F1;
    font-size: 13px;
    font-weight: 800;
}
QLabel#FieldLabel {
    color: #C0C2C5;
    font-weight: 700;
}
QLabel#SubCardTitle {
    color: #E8EAEE;
    font-weight: 800;
}
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox {
    background: #1B1C1E;
    color: #F0F0F0;
    border: 1px solid #4A4D52;
    border-radius: 8px;
    padding: 4px 8px;
    min-height: 24px;
    selection-background-color: #6C727A;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QFontComboBox:focus {
    border: 1px solid #858B94;
}
QSpinBox, QDoubleSpinBox {
    padding-right: 8px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    border: none;
    padding: 0;
    margin: 0;
    background: transparent;
}
QSpinBox::up-arrow, QSpinBox::down-arrow,
QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {
    width: 0px;
    height: 0px;
    image: none;
}
QComboBox, QFontComboBox {
    padding-right: 22px;
}
QComboBox::drop-down, QFontComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    background: transparent;
}
QLineEdit[readOnly="true"] {
    color: #CDD1D6;
    background: #1E2023;
}
QProgressBar {
    background: #1B1C1E;
    border: 1px solid #4A4D52;
    border-radius: 9px;
    min-height: 18px;
    text-align: center;
    color: #F0F0F0;
    font-weight: 700;
}
QProgressBar::chunk {
    background: #6C727A;
    border-radius: 8px;
}
QSlider {
    min-height: 20px;
    max-height: 20px;
}
QSlider::groove:horizontal {
    background: #1E2023;
    border: 1px solid #4A4D52;
    border-radius: 5px;
    height: 10px;
}
QSlider::sub-page:horizontal {
    background: #5EA0FF;
    border: 1px solid #5EA0FF;
    border-radius: 5px;
}
QSlider::add-page:horizontal {
    background: #1E2023;
    border: 1px solid #4A4D52;
    border-radius: 5px;
}
QSlider::handle:horizontal {
    background: #5EA0FF;
    border: 1px solid #DDEBFF;
    border-radius: 8px;
    width: 16px;
    height: 16px;
    margin: -3px 0;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #242527;
    width: 9px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #55595F;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QMessageBox {
    background: #242527;
}
QColorDialog, QFileDialog {
    background: #242527;
}
"""


class TitleBar(QFrame):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.drag_position: QPoint | None = None
        self.setObjectName("TitleBar")
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 10, 5)
        layout.setSpacing(10)

        title = QLabel("Criador de Vídeo Lo-fi")
        title.setObjectName("AppTitle")
        subtitle = QLabel(f"Versão {APP_VERSION} • PySide6 • FFmpeg • autosave JSON")
        subtitle.setObjectName("Subtitle")

        stack = QVBoxLayout()
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)
        stack.addWidget(title)
        stack.addWidget(subtitle)

        self.min_btn = PillButton("—", "title")
        self.min_btn.setFixedSize(34, 26)
        self.min_btn.clicked.connect(parent_window.showMinimized)

        self.close_btn = PillButton("×", "danger")
        self.close_btn.setFixedSize(34, 26)
        self.close_btn.clicked.connect(parent_window.close)

        layout.addLayout(stack)
        layout.addStretch(1)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() & Qt.LeftButton:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.worker: WorkerRender | None = None
        self.inicio_tempo: float | None = None
        self.ultimo_video: Path | None = None
        self.fonte_config = FonteTextoConfig()
        self.watermark_config = WatermarkConfig()
        self.intro_config = IntroTextConfig()
        self._config_carregada = False
        self._carregando_config = False
        self.autosave_timer: QTimer | None = None

        self.setWindowTitle(f"Criador de Vídeo Lo-fi {APP_VERSION}")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1120, 720)
        self._build()
        self._timer()
        self._setup_autosave()
        self.carregar_config_inicial()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        root = QFrame()
        root.setObjectName("RootFrame")
        root.setAttribute(Qt.WA_StyledBackground, True)
        root_layout = QVBoxLayout(root)
        # Margem interna mínima evita que o conteúdo retangular invada
        # os cantos arredondados da janela sem barra nativa.
        root_layout.setContentsMargins(1, 0, 1, 1)
        root_layout.setSpacing(0)

        root_layout.addWidget(TitleBar(self))

        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        content = QWidget()
        content.setObjectName("ScrollContent")
        content.setAttribute(Qt.WA_TranslucentBackground, True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 6, 10, 8)
        content_layout.setSpacing(6)

        # Arquivos
        card_arquivos = Card("1. Escolha os arquivos")
        grid_files = QGridLayout()
        grid_files.setHorizontalSpacing(10)
        grid_files.setVerticalSpacing(6)

        self.video_picker = PathPicker(
            "Vídeo ou GIF base",
            "file",
            "Vídeos/GIF (*.mp4 *.mov *.mkv *.avi *.webm *.gif);;Todos (*.*)",
        )
        self.music_folder_picker = PathPicker("Pasta onde estão as músicas", "folder")
        self.bg_audio_picker = PathPicker(
            "Som de fundo opcional",
            "file",
            "Áudios (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma);;Todos (*.*)",
        )
        self.bg_audio_picker.ocultar_rotulo()
        self.output_picker = PathPicker("Pasta de saída", "folder")
        self.output_picker.line.setPlaceholderText("Automática: render_AAAA-MM-DD_HH-MM-SS")

        clear_bg = PillButton("Limpar", "normal")
        clear_bg.setFixedWidth(76)
        clear_bg.clicked.connect(lambda: self.bg_audio_picker.set_path(None))
        self.btn_open = PillButton("Abrir pasta de saída", "normal")
        self.btn_open.clicked.connect(self.abrir_pasta_saida)

        audio_title = QLabel("Som de fundo opcional")
        audio_title.setObjectName("SubCardTitle")
        self.bg_volume_title = QLabel("Volume")
        self.bg_volume_title.setObjectName("FieldLabel")
        self.bg_volume = QSlider(Qt.Horizontal)
        self.bg_volume.setRange(0, 20)
        self.bg_volume.setSingleStep(1)
        self.bg_volume.setPageStep(1)
        self.bg_volume.setTickPosition(QSlider.NoTicks)
        self.bg_volume.setTickInterval(1)
        self.bg_volume.setValue(3)
        self.bg_volume.setFixedWidth(170)
        self.bg_volume_value = QLabel("30%")
        self.bg_volume_value.setObjectName("FieldLabel")
        self.bg_volume_value.setFixedWidth(38)
        self.bg_volume_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        audio_subcard = QFrame()
        audio_subcard.setObjectName("SubCard")
        audio_layout = QGridLayout(audio_subcard)
        audio_layout.setContentsMargins(10, 8, 10, 8)
        audio_layout.setHorizontalSpacing(8)
        audio_layout.setVerticalSpacing(6)

        volume_row = QHBoxLayout()
        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.setSpacing(8)
        volume_row.addWidget(self.bg_volume_title)
        volume_row.addWidget(self.bg_volume)
        volume_row.addWidget(self.bg_volume_value)

        audio_path_row = QHBoxLayout()
        audio_path_row.setContentsMargins(0, 0, 0, 0)
        audio_path_row.setSpacing(8)
        audio_path_row.addWidget(self.bg_audio_picker, 1)
        audio_path_row.addWidget(clear_bg)

        audio_layout.addWidget(audio_title, 0, 0)
        audio_layout.addLayout(volume_row, 0, 1, alignment=Qt.AlignRight)
        audio_layout.addLayout(audio_path_row, 1, 0, 1, 2)
        audio_layout.setColumnStretch(0, 1)

        grid_files.addWidget(self.video_picker, 0, 0, 1, 2)
        grid_files.addWidget(self.music_folder_picker, 1, 0, 1, 2)
        grid_files.addWidget(audio_subcard, 2, 0, 1, 2)
        grid_files.addWidget(self.output_picker, 3, 0, 1, 2)
        grid_files.addWidget(self.btn_open, 4, 0, alignment=Qt.AlignLeft)
        grid_files.setColumnStretch(0, 1)
        card_arquivos.addLayout(grid_files)
        card_arquivos.setMinimumHeight(285)
        card_arquivos.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Render e áudio
        card_render = Card("2. Renderização e áudio")
        # Este card é propositalmente mais compacto para reduzir o scroll da janela.
        card_render.layout_principal.setContentsMargins(10, 0, 10, 8)
        card_render.layout_principal.setSpacing(8)

        grid_render = QGridLayout()
        grid_render.setHorizontalSpacing(10)
        grid_render.setVerticalSpacing(3)
        grid_render.setContentsMargins(0, 0, 0, 0)

        self.toggle_gpu = ToggleSwitch("Renderizar pela GPU NVIDIA / NVENC")
        self.toggle_gpu.setChecked(True)
        self.toggle_fade_in = ToggleSwitch("Usar fade in")
        self.toggle_fade_in.setChecked(True)
        self.toggle_fade_out = ToggleSwitch("Usar fade out")
        self.toggle_fade_out.setChecked(True)
        self.toggle_norm = ToggleSwitch("Normalizar áudio com loudnorm")
        self.toggle_norm.setChecked(True)

        for toggle in (self.toggle_gpu, self.toggle_fade_in, self.toggle_fade_out, self.toggle_norm):
            toggle.setFixedHeight(ToggleSwitch.HEIGHT)
            toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        compact_spin_style = """
            QDoubleSpinBox {
                background: #1B1C1E;
                color: #F0F0F0;
                border: 1px solid #4A4D52;
                border-radius: 8px;
                padding: 3px 8px;
                min-height: 22px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #858B94;
            }
        """

        def make_compact_spin(spin: QDoubleSpinBox, largura: int = 96) -> QDoubleSpinBox:
            spin.setFixedWidth(largura)
            spin.setMinimumHeight(24)
            spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            spin.setStyleSheet(compact_spin_style)
            return spin

        def compact_label(texto: str) -> QLabel:
            label = QLabel(texto)
            label.setStyleSheet("color: #C0C2C5; font-weight: 600; padding-left: 2px;")
            label.setMinimumHeight(24)
            return label

        self.fade_in_seconds = make_compact_spin(QDoubleSpinBox())
        self.fade_in_seconds.setRange(0.0, 60.0)
        self.fade_in_seconds.setSingleStep(0.5)
        self.fade_in_seconds.setValue(3.0)
        self.fade_in_seconds.setSuffix(" s")

        self.fade_out_seconds = make_compact_spin(QDoubleSpinBox())
        self.fade_out_seconds.setRange(0.0, 60.0)
        self.fade_out_seconds.setSingleStep(0.5)
        self.fade_out_seconds.setValue(3.0)
        self.fade_out_seconds.setSuffix(" s")

        def criar_subcard_fade(titulo: str, toggle: ToggleSwitch, duracao: QDoubleSpinBox) -> QFrame:
            subcard = QFrame()
            subcard.setObjectName("SubCard")
            layout = QGridLayout(subcard)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setHorizontalSpacing(8)
            layout.setVerticalSpacing(6)

            label = QLabel(titulo)
            label.setObjectName("SubCardTitle")
            duracao_label = compact_label("Duração")

            layout.addWidget(label, 0, 0, 1, 2)
            layout.addWidget(toggle, 1, 0, 1, 2)
            layout.addWidget(duracao_label, 2, 0)
            layout.addWidget(duracao, 2, 1)
            layout.setColumnStretch(0, 1)
            return subcard

        fade_in_subcard = criar_subcard_fade("Fade in", self.toggle_fade_in, self.fade_in_seconds)
        fade_out_subcard = criar_subcard_fade("Fade out", self.toggle_fade_out, self.fade_out_seconds)

        self.target_lufs = make_compact_spin(QDoubleSpinBox())
        self.target_lufs.setRange(-40.0, 0.0)
        self.target_lufs.setSingleStep(0.5)
        self.target_lufs.setValue(-14.0)

        self.true_peak = make_compact_spin(QDoubleSpinBox())
        self.true_peak.setRange(-9.0, 0.0)
        self.true_peak.setSingleStep(0.1)
        self.true_peak.setValue(-1.0)

        self.lra = make_compact_spin(QDoubleSpinBox())
        self.lra.setRange(1.0, 30.0)
        self.lra.setSingleStep(0.5)
        self.lra.setValue(11.0)

        # Layout em duas colunas para evitar 8 linhas altas uma embaixo da outra.
        grid_render.addWidget(self.toggle_gpu, 0, 0, 1, 2)
        grid_render.addWidget(self.toggle_norm, 0, 2, 1, 2)

        grid_render.addWidget(fade_in_subcard, 1, 0, 1, 2)
        grid_render.addWidget(fade_out_subcard, 1, 2, 1, 2)

        grid_render.addWidget(compact_label("Target LUFS"), 2, 0)
        grid_render.addWidget(self.target_lufs, 2, 1)
        grid_render.addWidget(compact_label("True Peak"), 2, 2)
        grid_render.addWidget(self.true_peak, 2, 3)

        grid_render.addWidget(compact_label("LRA"), 3, 0)
        grid_render.addWidget(self.lra, 3, 1)

        grid_render.setColumnStretch(0, 1)
        grid_render.setColumnStretch(1, 0)
        grid_render.setColumnStretch(2, 1)
        grid_render.setColumnStretch(3, 0)

        for toggle in (self.toggle_fade_in, self.toggle_fade_out, self.toggle_norm):
            toggle.stateChanged.connect(self._atualizar_estado_controles)
        self._atualizar_estado_controles()

        card_render.addLayout(grid_render)
        card_render.setMinimumHeight(285)
        card_render.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        steps_top_row = QHBoxLayout()
        steps_top_row.setSpacing(6)
        steps_top_row.addWidget(card_arquivos, 1)
        steps_top_row.addWidget(card_render, 1)
        content_layout.addLayout(steps_top_row)

        # Aparência
        card_visual = Card("3. Aparência, marca d'água e prévias")
        visual_grid = QGridLayout()
        visual_grid.setHorizontalSpacing(8)
        visual_grid.setVerticalSpacing(5)
        self.btn_fonte = PillButton("Fonte dos nomes", "normal")
        self.btn_watermark = PillButton("Marca d'água", "normal")
        self.btn_intro = PillButton("Frases de intro", "normal")
        self.btn_preview = PillButton("Prévia músicas", "normal")
        self.btn_preview_intro = PillButton("Prévia intro", "normal")
        self.btn_render_teste = PillButton("Renderizar teste 30s", "primary")
        self.btn_fonte.clicked.connect(self.abrir_modal_fonte)
        self.btn_watermark.clicked.connect(self.abrir_modal_watermark)
        self.btn_intro.clicked.connect(self.abrir_modal_intro)
        self.btn_preview.clicked.connect(self.preview_musicas)
        self.btn_preview_intro.clicked.connect(self.preview_intro)
        self.btn_render_teste.clicked.connect(self.iniciar_teste_30s)

        edit_subcard = QFrame()
        edit_subcard.setObjectName("SubCard")
        edit_layout = QGridLayout(edit_subcard)
        edit_layout.setContentsMargins(10, 8, 10, 8)
        edit_layout.setHorizontalSpacing(8)
        edit_layout.setVerticalSpacing(6)
        label_editar = QLabel("Editar")
        label_editar.setObjectName("SubCardTitle")
        edit_layout.addWidget(label_editar, 0, 0, 1, 3)
        edit_layout.addWidget(self.btn_fonte, 1, 0)
        edit_layout.addWidget(self.btn_watermark, 1, 1)
        edit_layout.addWidget(self.btn_intro, 1, 2)

        test_subcard = QFrame()
        test_subcard.setObjectName("SubCard")
        test_layout = QGridLayout(test_subcard)
        test_layout.setContentsMargins(10, 8, 10, 8)
        test_layout.setHorizontalSpacing(8)
        test_layout.setVerticalSpacing(6)
        label_testar = QLabel("Testar antes de renderizar")
        label_testar.setObjectName("SubCardTitle")
        test_layout.addWidget(label_testar, 0, 0, 1, 3)
        test_layout.addWidget(self.btn_preview, 1, 0)
        test_layout.addWidget(self.btn_preview_intro, 1, 1)
        test_layout.addWidget(self.btn_render_teste, 1, 2)

        visual_grid.addWidget(edit_subcard, 0, 0)
        visual_grid.addWidget(test_subcard, 0, 1)
        visual_grid.setColumnStretch(0, 1)
        visual_grid.setColumnStretch(1, 1)
        card_visual.addLayout(visual_grid)
        content_layout.addWidget(card_visual)

        # Log
        self.log_texto = QTextEdit()
        self.log_texto.setReadOnly(True)
        self.log_texto.setMinimumHeight(110)
        self.log_texto.setPlaceholderText("Logs do FFmpeg aparecerão aqui...")
        content_layout.addWidget(self.log_texto)

        # Progresso
        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(10)
        status_grid.setVerticalSpacing(4)
        self.label_etapa = QLabel("Aguardando configuração")
        self.label_etapa.setObjectName("FieldLabel")
        self.label_tempo = QLabel("Tempo decorrido: 00:00:00")
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        self.barra.setFormat("%p% concluído")

        status_grid.addWidget(QLabel("Etapa:"), 0, 0)
        status_grid.addWidget(self.label_etapa, 0, 1)
        status_grid.addWidget(QLabel("Tempo:"), 0, 2)
        status_grid.addWidget(self.label_tempo, 0, 3)
        status_grid.addWidget(self.barra, 1, 0, 1, 4)
        status_grid.setColumnStretch(1, 1)
        content_layout.addLayout(status_grid)

        # Botões principais
        row_buttons = QHBoxLayout()
        row_buttons.setSpacing(8)
        self.btn_start = PillButton("Iniciar renderização", "primary")
        self.btn_cancel = PillButton("Cancelar", "danger")
        self.btn_clear = PillButton("Limpar log", "normal")
        self.btn_toggle_log = PillButton("Esconder log", "normal")
        self.btn_save_config = PillButton("Salvar configs JSON", "normal")

        self.btn_cancel.setEnabled(False)

        self.btn_start.clicked.connect(self.iniciar_ou_pausar)
        self.btn_cancel.clicked.connect(self.cancelar)
        self.btn_clear.clicked.connect(self.log_texto.clear)
        self.btn_toggle_log.clicked.connect(self.alternar_log)
        self.btn_save_config.clicked.connect(lambda: self.salvar_config(mostrar_alerta=True))

        row_buttons.addWidget(self.btn_toggle_log)
        row_buttons.addWidget(self.btn_clear)
        row_buttons.addWidget(self.btn_save_config)
        row_buttons.addStretch(1)
        row_buttons.addWidget(self.btn_start)
        row_buttons.addWidget(self.btn_cancel)
        content_layout.addLayout(row_buttons)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)
        outer.addWidget(root)

        self.setStyleSheet(STYLE_DARK)
        aplicar_visual_campos_numericos(self)

    def _timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._atualizar_tempo)

    def _valor_volume_fundo(self) -> float:
        return self.bg_volume.value() / 10.0

    def _definir_volume_fundo(self, valor: float):
        try:
            valor_numerico = float(valor)
        except (TypeError, ValueError):
            valor_numerico = 0.30
        percentual = valor_numerico if valor_numerico > 2.0 else valor_numerico * 100
        indice = int(round(percentual / 10))
        self.bg_volume.setValue(max(0, min(20, indice)))
        self._atualizar_label_volume_fundo()

    def _atualizar_label_volume_fundo(self, *args):
        self.bg_volume_value.setText(f"{self.bg_volume.value() * 10}%")

    def alternar_log(self):
        mostrar = not self.log_texto.isVisible()
        self.log_texto.setVisible(mostrar)
        self.btn_toggle_log.setText("Esconder log" if mostrar else "Mostrar log")

    def _atualizar_estado_controles(self, *args):
        # Deixa a interface mais clara: quando uma função está desligada,
        # os parâmetros dela ficam cinza/desativados.
        if not hasattr(self, "fade_in_seconds"):
            return
        self.fade_in_seconds.setEnabled(self.toggle_fade_in.isChecked())
        self.fade_out_seconds.setEnabled(self.toggle_fade_out.isChecked())
        normalizacao_ativa = self.toggle_norm.isChecked()
        for widget in (self.target_lufs, self.true_peak, self.lra):
            widget.setEnabled(normalizacao_ativa)
        for widget in (self.bg_volume_title, self.bg_volume, self.bg_volume_value):
            widget.setEnabled(True)

    def _setup_autosave(self):
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(600)
        self.autosave_timer.timeout.connect(self._executar_autosave)

        for picker in (
            self.video_picker,
            self.music_folder_picker,
            self.bg_audio_picker,
            self.output_picker,
        ):
            picker.line.textChanged.connect(self._agendar_autosave)

        self.bg_audio_picker.line.textChanged.connect(self._atualizar_estado_controles)
        self.bg_volume.valueChanged.connect(self._atualizar_label_volume_fundo)

        for toggle in (
            self.toggle_gpu,
            self.toggle_fade_in,
            self.toggle_fade_out,
            self.toggle_norm,
        ):
            toggle.stateChanged.connect(self._agendar_autosave)

        for spin in (
            self.fade_in_seconds,
            self.fade_out_seconds,
            self.bg_volume,
            self.target_lufs,
            self.true_peak,
            self.lra,
        ):
            spin.valueChanged.connect(self._agendar_autosave)

    def _agendar_autosave(self, *args):
        if self._carregando_config:
            return
        if self.autosave_timer is not None:
            self.autosave_timer.start()

    def _executar_autosave(self):
        self.salvar_config(mostrar_alerta=False, logar=False)

    def coletar_estado_config(self) -> dict:
        return {
            "version": 1,
            "app_version": APP_VERSION,
            "paths": {
                "video_path": caminho_ou_vazio(self.video_picker.path()),
                "music_folder": caminho_ou_vazio(self.music_folder_picker.path()),
                "background_audio_path": caminho_ou_vazio(self.bg_audio_picker.path()),
                "output_folder": caminho_ou_vazio(self.output_picker.path()),
            },
            "render": {
                "use_gpu": self.toggle_gpu.isChecked(),
                "use_fade_in": self.toggle_fade_in.isChecked(),
                "use_fade_out": self.toggle_fade_out.isChecked(),
                "fade_in_seconds": self.fade_in_seconds.value(),
                "fade_out_seconds": self.fade_out_seconds.value(),
                "background_volume": self._valor_volume_fundo(),
            },
            "normalizacao": asdict(self.normalizacao_config()),
            "fonte_texto": asdict(self.fonte_config),
            "watermark": asdict(self.watermark_config),
            "intro": intro_config_to_dict(self.intro_config),
        }

    def salvar_config(self, mostrar_alerta: bool = False, logar: bool = True):
        try:
            salvar_json_config(self.coletar_estado_config())
            mensagem = f"Configurações salvas em: {CONFIG_JSON_PATH}"
            if logar:
                self.adicionar_log(f"\n{mensagem}\n")
            if mostrar_alerta:
                QMessageBox.information(self, "Configurações salvas", mensagem)
        except Exception as erro:
            if mostrar_alerta:
                QMessageBox.warning(self, "Erro ao salvar configurações", str(erro))
            elif logar:
                self.adicionar_log(f"\nNão foi possível salvar as configurações: {erro}\n")

    def carregar_config_inicial(self):
        dados = carregar_json_config()
        if not dados:
            return

        self._carregando_config = True
        try:
            paths = dados.get("paths", {})
            self.video_picker.set_path(texto_para_path_ou_none(paths.get("video_path")))
            self.music_folder_picker.set_path(texto_para_path_ou_none(paths.get("music_folder")))
            self.bg_audio_picker.set_path(texto_para_path_ou_none(paths.get("background_audio_path")))
            self.output_picker.set_path(texto_para_path_ou_none(paths.get("output_folder")))

            render = dados.get("render", {})
            self.toggle_gpu.setChecked(bool(render.get("use_gpu", self.toggle_gpu.isChecked())))
            self.toggle_fade_in.setChecked(bool(render.get("use_fade_in", self.toggle_fade_in.isChecked())))
            self.toggle_fade_out.setChecked(bool(render.get("use_fade_out", self.toggle_fade_out.isChecked())))
            self.fade_in_seconds.setValue(float(render.get("fade_in_seconds", self.fade_in_seconds.value())))
            self.fade_out_seconds.setValue(float(render.get("fade_out_seconds", self.fade_out_seconds.value())))
            self._definir_volume_fundo(float(render.get("background_volume", self._valor_volume_fundo())))

            normalizacao = dataclass_from_dict(NormalizacaoConfig, dados.get("normalizacao"))
            self.toggle_norm.setChecked(normalizacao.enabled)
            self.target_lufs.setValue(float(normalizacao.target_lufs))
            self.true_peak.setValue(float(normalizacao.true_peak))
            self.lra.setValue(float(normalizacao.loudness_range))

            self.fonte_config = dataclass_from_dict(FonteTextoConfig, dados.get("fonte_texto"))
            self.watermark_config = dataclass_from_dict(WatermarkConfig, dados.get("watermark"))
            self.intro_config = intro_config_from_dict(dados.get("intro"))
            self._config_carregada = True
            self.adicionar_log(f"Configurações carregadas de: {CONFIG_JSON_PATH}\n")
        except Exception as erro:
            self.adicionar_log(f"Não foi possível carregar o JSON de configurações: {erro}\n")
        finally:
            self._carregando_config = False
            self._atualizar_estado_controles()

    def normalizacao_config(self) -> NormalizacaoConfig:
        return NormalizacaoConfig(
            enabled=self.toggle_norm.isChecked(),
            target_lufs=self.target_lufs.value(),
            true_peak=self.true_peak.value(),
            loudness_range=self.lra.value(),
        )

    def criar_config(self) -> RenderConfig:
        video = self.video_picker.path()
        music_folder = self.music_folder_picker.path()
        bg_audio = self.bg_audio_picker.path()
        output = self.output_picker.path() or gerar_pasta_saida_padrao()

        if video is None:
            raise ErroRender("Escolha o vídeo ou GIF base.")
        if music_folder is None:
            raise ErroRender("Escolha a pasta onde estão as músicas.")

        return RenderConfig(
            video_path=video,
            music_folder=music_folder,
            background_audio_path=bg_audio,
            output_folder=output,
            use_gpu=self.toggle_gpu.isChecked(),
            use_fade_in=self.toggle_fade_in.isChecked(),
            use_fade_out=self.toggle_fade_out.isChecked(),
            fade_in_seconds=self.fade_in_seconds.value(),
            fade_out_seconds=self.fade_out_seconds.value(),
            background_volume=self._valor_volume_fundo(),
            normalizacao=self.normalizacao_config(),
            fonte_texto=self.fonte_config,
            watermark=self.watermark_config,
            intro=self.intro_config,
        )

    def abrir_modal_fonte(self):
        dialog = FonteDialog(self.fonte_config, self)
        if dialog.exec() == QDialog.Accepted:
            self.fonte_config = dialog.resultado()
            self.adicionar_log("\nConfiguração de fonte atualizada.\n")
            self.salvar_config(mostrar_alerta=False, logar=False)

    def abrir_modal_watermark(self):
        dialog = WatermarkDialog(self.watermark_config, self)
        if dialog.exec() == QDialog.Accepted:
            self.watermark_config = dialog.resultado()
            self.adicionar_log("\nConfiguração de marca d'água atualizada.\n")
            self.salvar_config(mostrar_alerta=False, logar=False)

    def abrir_modal_intro(self):
        try:
            dialog = IntroDialog(self.intro_config, self)
            if dialog.exec() == QDialog.Accepted:
                self.intro_config = dialog.resultado()
                self.adicionar_log("\nConfiguração de frases de intro atualizada.\n")
                self.salvar_config(mostrar_alerta=False, logar=False)
        except Exception as erro:
            self.adicionar_log(f"\nERRO ao abrir configuração da intro:\n{erro}\n")
            QMessageBox.warning(self, "Configurar frases de intro", str(erro))

    def preview_intro(self):
        try:
            cfg = self.criar_config()
            engine = RenderEngine(cfg, self.adicionar_log, self.barra.setValue, self.label_etapa.setText)
            saida = engine.gerar_preview_intro()
            self.adicionar_log(f"\nPrévia da intro criada em: {saida}\n")
            QMessageBox.information(self, "Prévia da intro", f"Prévia criada em:\n{saida}")
        except Exception as erro:
            QMessageBox.warning(self, "Prévia da intro", str(erro))

    def preview_musicas(self):
        try:
            cfg = self.criar_config()
            engine = RenderEngine(cfg, self.adicionar_log, self.barra.setValue, self.label_etapa.setText)
            engine.validar()
            tracks = engine.detectar_tracks()
            self.adicionar_log("\n=== Prévia das músicas detectadas ===\n")
            for i, track in enumerate(tracks, start=1):
                self.adicionar_log(
                    f"{i:02d}. {track.titulo} | "
                    f"{segundos_para_legivel(track.inicio)} - {segundos_para_legivel(track.fim)}\n"
                )
        except Exception as erro:
            QMessageBox.warning(self, "Prévia", str(erro))

    def iniciar_teste_30s(self):
        if self.worker and self.worker.isRunning():
            return

        try:
            config = self.criar_config()
            self.salvar_config(mostrar_alerta=False, logar=False)
        except Exception as erro:
            QMessageBox.warning(self, "Configuração incompleta", str(erro))
            return

        self.log_texto.clear()
        self.barra.setValue(0)
        self.label_etapa.setText("Iniciando teste de 30s")
        self.inicio_tempo = time.time()
        self.timer.start(1000)
        self.ultimo_video = None

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Pausar")
        self.btn_render_teste.setEnabled(False)
        self.btn_render_teste.setText("Renderizando teste...")
        self.btn_cancel.setEnabled(True)

        self.worker = WorkerRender(config, modo="teste_30s")
        self.worker.log.connect(self.adicionar_log)
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.etapa.connect(self.label_etapa.setText)
        self.worker.terminado.connect(self.finalizar)
        self.worker.start()

    def iniciar_ou_pausar(self):
        if self.worker and self.worker.isRunning():
            self.alternar_pausa()
        else:
            self.iniciar()

    def iniciar(self):
        if self.worker and self.worker.isRunning():
            return

        try:
            config = self.criar_config()
            self.salvar_config(mostrar_alerta=False, logar=False)
        except Exception as erro:
            QMessageBox.warning(self, "Configuração incompleta", str(erro))
            return

        self.log_texto.clear()
        self.barra.setValue(0)
        self.label_etapa.setText("Iniciando renderização")
        self.inicio_tempo = time.time()
        self.timer.start(1000)
        self.ultimo_video = None

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Pausar")
        if hasattr(self, "btn_render_teste"):
            self.btn_render_teste.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.worker = WorkerRender(config)
        self.worker.log.connect(self.adicionar_log)
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.etapa.connect(self.label_etapa.setText)
        self.worker.terminado.connect(self.finalizar)
        self.worker.start()

    def alternar_pausa(self):
        if not self.worker or not self.worker.isRunning():
            return
        pausado = self.worker.alternar_pausa()
        if pausado:
            self.btn_start.setText("Retomar")
            self.label_etapa.setText("Pausado")
            self.adicionar_log("\nProcesso pausado.\n")
        else:
            self.btn_start.setText("Pausar")
            self.label_etapa.setText("Retomando")
            self.adicionar_log("\nProcesso retomado.\n")

    def cancelar(self):
        if not self.worker or not self.worker.isRunning():
            return
        self.label_etapa.setText("Cancelando")
        self.btn_cancel.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.adicionar_log("\nCancelamento solicitado. Encerrando FFmpeg e removendo arquivo incompleto...\n")
        self.worker.cancelar()

    def adicionar_log(self, texto: str):
        self.log_texto.moveCursor(QTextCursor.End)
        self.log_texto.insertPlainText(texto)
        self.log_texto.moveCursor(QTextCursor.End)

    def atualizar_progresso(self, valor: int):
        self.barra.setValue(max(0, min(100, int(valor))))

    def _atualizar_tempo(self):
        if not self.inicio_tempo:
            return
        segundos = int(time.time() - self.inicio_tempo)
        h = segundos // 3600
        m = (segundos % 3600) // 60
        s = segundos % 60
        self.label_tempo.setText(f"Tempo decorrido: {h:02d}:{m:02d}:{s:02d}")

    def finalizar(self, sucesso: bool, mensagem: str, caminho_saida: str):
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Iniciar renderização")
        if hasattr(self, "btn_render_teste"):
            self.btn_render_teste.setEnabled(True)
            self.btn_render_teste.setText("Renderizar teste 30s")
        self.btn_cancel.setEnabled(False)

        if sucesso:
            self.ultimo_video = Path(caminho_saida)
            self.barra.setValue(100)
            self.label_etapa.setText("Finalizado com sucesso")
            QMessageBox.information(self, "Finalizado", f"{mensagem}\n\n{caminho_saida}")
        else:
            self.barra.setValue(0)
            self.label_etapa.setText("Cancelado" if "cancel" in mensagem.lower() else "Erro")
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
                msg.setInformativeText(
                    f"O log foi salvo em:\n{log_path}\n\n"
                    "Abaixo aparece só o final do erro para a janela não ficar gigante."
                )
                msg.setDetailedText(mensagem)
                msg.exec()

    def abrir_pasta_saida(self):
        pasta = self.output_picker.path()
        if pasta is None and self.ultimo_video and self.ultimo_video.exists():
            pasta = self.ultimo_video.parent
        if pasta is None:
            pasta = SCRIPT_DIR
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(pasta))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(pasta)])
            else:
                subprocess.Popen(["xdg-open", str(pasta)])
        except Exception:
            QMessageBox.information(self, "Pasta de saída", str(pasta))

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
                self.salvar_config(mostrar_alerta=False, logar=False)
                self.cancelar()
                event.accept()
            else:
                event.ignore()
        else:
            self.salvar_config(mostrar_alerta=False, logar=False)
            event.accept()


# ==========================
# ENTRADA
# ==========================

def iniciar_ui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    iniciar_ui()
