# -*- coding: utf-8 -*-
from __future__ import annotations

"""Motor de renderizacao e worker Qt."""

from pathlib import Path

try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    raise SystemExit("PySide6 nao esta instalado. Instale com: pip install PySide6")

from .constants import (
    EXTENSOES_AUDIO,
    EXTENSOES_IMAGEM,
    EXTENSOES_VIDEO,
    FFMPEG,
    FFPROBE,
    FINAL_RENDER_SIZE,
    PESO_CONCATENAR,
    PESO_MONTAR,
    PESO_NORMALIZAR_ANALISE,
    PESO_NORMALIZAR_APLICAR,
    PESO_PROCESSAR_AUDIOS,
    TEMP_DIR,
)
from .audio_pipeline import AudioPipelineMixin
from .ffmpeg_runner import FfmpegRunnerMixin
from .files import limpar_cache_antigo, limpar_cache_render
from .models import IntroFraseConfig, RenderConfig, TrackInfo
from .process_control import (
    CONTROLE_EXECUCAO,
    ErroRender,
    RenderCancelado,
)
from .profiles import FINAL_RENDER_PROFILE, PREVIEW_RENDER_PROFILE, RenderProfile
from .text_utils import gerar_nome_video, segundos_para_legivel
from .video_filters import VideoFilterMixin


class RenderEngine(AudioPipelineMixin, VideoFilterMixin, FfmpegRunnerMixin):
    def __init__(self, config: RenderConfig, log_cb, progress_cb, stage_cb):
        self.config = config
        self.log = log_cb
        self.progress = progress_cb
        self.stage = stage_cb
        self.progresso_peso = 0.0
        self.peso_total = self._calcular_peso_total()
        self._frases_intro_ativas: list[IntroFraseConfig] | None = None
        self.profile = FINAL_RENDER_PROFILE
        self.render_scale = 1.0
        self.output_size = FINAL_RENDER_SIZE
        self.pre_render = False

    def _calcular_peso_total(self, audio_enabled: bool = True) -> float:
        total = PESO_MONTAR
        if audio_enabled:
            total += (
                PESO_PROCESSAR_AUDIOS
                + PESO_CONCATENAR
                + PESO_NORMALIZAR_ANALISE
                + PESO_NORMALIZAR_APLICAR
            )
        return total

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

        if not self.pre_render and self.config.background_audio_path:
            fundo = self.config.background_audio_path
            if not fundo.exists() or fundo.suffix.lower() not in EXTENSOES_AUDIO:
                raise ErroRender("Escolha um áudio de fundo válido ou deixe o campo vazio.")

        if not self.pre_render and self.config.intro.enabled and self.config.intro.typing_audio_path:
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
        limpar_cache_antigo()
        limpar_cache_render()
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    def run_pre_render(self) -> Path:
        return self._run_render(PREVIEW_RENDER_PROFILE)

    def run_final(self) -> Path:
        return self._run_render(FINAL_RENDER_PROFILE)

    def _run_render(self, profile: RenderProfile) -> Path:
        CONTROLE_EXECUCAO.verificar_cancelamento()
        self.profile = profile
        self.render_scale = max(0.1, float(profile.render_scale))
        self.output_size = profile.output_size
        self.pre_render = profile.mode == "pre_render"
        self.peso_total = self._calcular_peso_total(profile.audio_enabled)
        self.validar()
        self.preparar_pastas()
        self.preparar_frases_intro()

        self.progress(0)
        self.stage("Lendo arquivos")
        self.log("\n=== Configuração usada ===\n")
        self.log(f"Mídia visual base: {self.config.video_path}\n")
        self.log(f"Pasta das músicas: {self.config.music_folder}\n")
        self.log(f"Som de fundo: {self.config.background_audio_path or 'não usado'}\n")
        self.log(f"Pasta de saída: {self.config.output_folder}\n")
        self.log(f"Modo: {profile.label} ({profile.output_size[0]}x{profile.output_size[1]})\n")
        self.log(f"Renderização: {'GPU NVIDIA / NVENC' if self.config.use_gpu else 'CPU / libx264'}\n")
        if not profile.audio_enabled:
            self.log("Preview: áudio não será processado para acelerar a pré-visualização.\n")

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

        audio_final = None
        if profile.audio_enabled:
            arquivos_processados = self.processar_audios(tracks, duracao_total_musicas)
            audio_final = self.combinar_audios(arquivos_processados, tracks)
            audio_final = self.normalizar_audio(audio_final, duracao_total_musicas)

        saida_final = self.montar_video(audio_final, duracao_total, tracks, usar_gpu, profile)

        self.stage("Finalizado")
        self.progress(100)
        self.log("\nFinalizado com sucesso!\n")
        self.log(f"Vídeo criado em: {saida_final}\n")
        self.log(f"Duração total: {segundos_para_legivel(duracao_total)}\n")
        return saida_final


























    def argumentos_entrada_visual_base(self) -> list[str]:
        caminho = self.config.video_path
        if caminho.suffix.lower() in EXTENSOES_IMAGEM:
            return ["-loop", "1", "-framerate", "30", "-i", str(caminho)]
        return ["-stream_loop", "-1", "-i", str(caminho)]

    def montar_video(
        self,
        audio_final: Path | None,
        duracao_total: float,
        tracks: list[TrackInfo],
        usar_gpu: bool,
        profile: RenderProfile,
    ) -> Path:
        preview = profile.mode == "pre_render"
        self.stage("Montando preview" if preview else "Montando vídeo final")
        self.log("\nMontando preview...\n" if preview else "\nMontando vídeo final...\n")

        saida_final = self.config.output_path_override or (self.config.output_folder / gerar_nome_video(profile.output_prefix))
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida_final)

        usar_audio = bool(profile.audio_enabled and audio_final)
        usar_fundo = usar_audio and self.config.background_audio_path is not None
        usar_typing = usar_audio and bool(self.config.intro.enabled and self.config.intro.typing_audio_path)
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
        if usar_audio:
            comando += ["-i", str(audio_final)]

        proximo_indice = 2 if usar_audio else 1
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
            profile.output_size,
            include_audio=usar_audio,
        )

        comando += [
            "-filter_complex_script", str(arquivo_filtro),
            "-t", str(duracao_total),
            "-map", "[vout]",
        ]

        if usar_audio:
            comando += ["-map", "[aout]"]
        else:
            comando += ["-an"]

        if usar_gpu:
            comando += list(profile.gpu_video_args)
        else:
            comando += list(profile.cpu_video_args)

        comando += [
            "-pix_fmt", "yuv420p",
        ]
        if usar_audio:
            comando += [
                "-c:a", "aac",
                "-b:a", profile.audio_bitrate,
            ]
        if profile.streamable:
            comando += ["-movflags", "+frag_keyframe+empty_moov+default_base_moof"]
        comando += [
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
            if self.modo == "pre_render":
                saida = engine.run_pre_render()
                self.terminado.emit(True, "Preview criado com sucesso.", str(saida))
            else:
                saida = engine.run_final()
                self.terminado.emit(True, "Vídeo exportado com sucesso.", str(saida))
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
        finally:
            limpar_cache_render()
            limpar_cache_antigo()

    def cancelar(self):
        CONTROLE_EXECUCAO.solicitar_cancelamento()

    def alternar_pausa(self):
        return CONTROLE_EXECUCAO.alternar_pausa()
