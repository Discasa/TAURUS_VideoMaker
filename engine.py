# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Backend do TAURUS Video Maker.

Este módulo concentra configurações, persistência, controle de processo,
integração com FFmpeg, RenderEngine e WorkerRender. A interface gráfica fica em
VideoMaker.py.
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
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    print("PySide6 não está instalado. Instale com: pip install PySide6")
    sys.exit(1)
# ==========================
# CONFIGURAÇÕES BASE
# ==========================

APP_VERSION = "8.0.44"


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
    shadow_color: str = "#000000"
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
    shadow_color: str = "#000000"
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
    shadow_color: str = "#000000"
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
    track_titles: dict[str, str] = field(default_factory=dict)
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
        extensoes_visuais = EXTENSOES_VIDEO + EXTENSOES_IMAGEM
        if not video or not video.exists() or video.suffix.lower() not in extensoes_visuais:
            raise ErroRender("Escolha um vídeo, GIF ou imagem base válido.")

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
        self.log(f"Mídia visual base: {self.config.video_path}\n")
        self.log(f"Pasta das músicas: {self.config.music_folder}\n")
        self.log(f"Som de fundo: {self.config.background_audio_path or 'não usado'}\n")
        self.log(f"Pasta de saída: {self.config.output_folder}\n")
        self.log(f"Renderização: {'GPU NVIDIA / NVENC' if self.config.use_gpu else 'CPU / libx264'}\n")

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
            titulo_manual = str(self.config.track_titles.get(arquivo.name, "")).strip()
            tracks.append(
                TrackInfo(
                    arquivo=arquivo,
                    titulo=titulo_manual or limpar_titulo_musica(arquivo),
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
            f"shadowcolor={cor_drawtext(cfg.shadow_color, cfg.shadow_opacity)}",
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
        shadow_color = getattr(cfg, "shadow_color", "#000000")
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
            f"shadowcolor={cor_drawtext(shadow_color, shadow_opacity)}",
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

    def argumentos_entrada_visual_base(self) -> list[str]:
        caminho = self.config.video_path
        if caminho.suffix.lower() in EXTENSOES_IMAGEM:
            return ["-loop", "1", "-framerate", "30", "-i", str(caminho)]
        return ["-stream_loop", "-1", "-i", str(caminho)]

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
        ]
        comando += self.argumentos_entrada_visual_base()
        comando += ["-i", str(audio_final)]

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
            "-filter_complex_script", str(arquivo_filtro),
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
