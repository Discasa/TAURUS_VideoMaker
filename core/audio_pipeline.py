# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .constants import (
    EXTENSOES_AUDIO,
    FFMPEG,
    FFPROBE,
    PESO_CONCATENAR,
    PESO_NORMALIZAR_ANALISE,
    PESO_NORMALIZAR_APLICAR,
    PESO_PROCESSAR_AUDIOS,
    TEMP_DIR,
)
from .models import TrackInfo
from .process_control import CONTROLE_EXECUCAO, ErroRender, criar_kwargs_subprocess_controlado
from .text_utils import limpar_titulo_musica, natural_key, segundos_para_ffmpeg


class AudioPipelineMixin:

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

        ordem = [str(nome) for nome in getattr(self.config, "track_order", []) if str(nome).strip()]
        if ordem:
            posicao = {nome: indice for indice, nome in enumerate(ordem)}
            arquivos = sorted(arquivos, key=lambda p: (posicao.get(p.name, len(posicao)), natural_key(p)))

        entradas: list[tuple[Path, str, float]] = []
        for arquivo in arquivos:
            CONTROLE_EXECUCAO.verificar_cancelamento()
            duracao = self.obter_duracao(arquivo)
            if duracao <= 0:
                self.log(f"Aviso: ignorando arquivo sem duração válida: {arquivo.name}\n")
                continue
            titulo_manual = str(self.config.track_titles.get(arquivo.name, "")).strip()
            entradas.append((arquivo, titulo_manual or limpar_titulo_musica(arquivo), duracao))

        if not entradas:
            raise ErroRender("Nenhuma música válida foi encontrada após leitura das durações.")

        crossfade = max(0.0, float(getattr(self.config, "crossfade_seconds", 0.0)))
        silencio = max(0.0, float(getattr(self.config, "silence_seconds", 0.0)))
        if crossfade > 0 and silencio > 0:
            self.log("\nAviso: crossfade e silêncio estão ativos. O silêncio entre faixas será ignorado durante o crossfade.\n")

        tracks: list[TrackInfo] = []
        cursor = 0.0
        for indice, (arquivo, titulo, duracao) in enumerate(entradas):
            inicio = cursor
            fim = cursor + duracao
            tracks.append(
                TrackInfo(
                    arquivo=arquivo,
                    titulo=titulo,
                    inicio=inicio,
                    fim=fim,
                    duracao=duracao,
                )
            )
            if indice < len(entradas) - 1:
                proxima_duracao = entradas[indice + 1][2]
                if crossfade > 0:
                    transicao = min(crossfade, duracao * 0.45, proxima_duracao * 0.45)
                    cursor = fim - transicao
                else:
                    cursor = fim + silencio

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

    def processar_audios_generico(
        self,
        tracks: list[TrackInfo],
        duracao_total: float,
        prefixo_saida: str,
        etapa: str,
        descricao_log: str,
        filtro_fade_cb,
        cortar_segmento: bool = False,
    ) -> list[Path]:
        self.stage(etapa)
        arquivos_processados: list[Path] = []
        duracao_processada = 0.0
        inicio_bloco = self.progresso_peso

        for i, track in enumerate(tracks, start=1):
            CONTROLE_EXECUCAO.verificar_cancelamento()
            self.stage(f"{etapa} {i}/{len(tracks)}: {track.titulo}")
            self.log(f"\n{descricao_log} {i}/{len(tracks)}: {track.arquivo.name}\n")

            saida = TEMP_DIR / f"{prefixo_saida}_{i:03d}.wav"
            CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida)

            comando = [
                str(FFMPEG),
                "-y",
                "-i", str(track.arquivo),
            ]
            if cortar_segmento:
                comando += ["-t", segundos_para_ffmpeg(track.duracao)]
            comando += [
                "-vn",
                "-ar", "48000",
                "-ac", "2",
            ]

            filtro = filtro_fade_cb(track)
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

    def processar_audios(self, tracks: list[TrackInfo], duracao_total: float) -> list[Path]:
        return self.processar_audios_generico(
            tracks=tracks,
            duracao_total=duracao_total,
            prefixo_saida="audio",
            etapa="Processando músicas com fade",
            descricao_log="Processando música",
            filtro_fade_cb=lambda track: self.criar_filtro_fade(track.duracao),
        )

    def crossfades_entre_tracks(self, tracks: list[TrackInfo]) -> list[float]:
        valores = []
        for atual, proxima in zip(tracks, tracks[1:]):
            valores.append(max(0.0, atual.fim - proxima.inicio))
        return valores

    def criar_silencio(self, indice: int, duracao: float) -> Path:
        saida = TEMP_DIR / f"silencio_{indice:03d}.wav"
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(saida)
        comando = [
            str(FFMPEG),
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=48000:cl=stereo",
            "-t", segundos_para_ffmpeg(duracao),
            "-c:a", "pcm_s16le",
            str(saida),
        ]
        self.rodar_comando(comando)
        return saida

    def combinar_audios(self, arquivos_processados: list[Path], tracks: list[TrackInfo]) -> Path:
        crossfades = self.crossfades_entre_tracks(tracks)
        if any(valor > 0 for valor in crossfades):
            return self.crossfade_audios(arquivos_processados, crossfades)

        silencio = max(0.0, float(getattr(self.config, "silence_seconds", 0.0)))
        if silencio > 0 and len(arquivos_processados) > 1:
            lista_com_silencio: list[Path] = []
            for indice, arquivo in enumerate(arquivos_processados):
                lista_com_silencio.append(arquivo)
                if indice < len(arquivos_processados) - 1:
                    lista_com_silencio.append(self.criar_silencio(indice + 1, silencio))
            return self.concatenar_audios(lista_com_silencio)

        return self.concatenar_audios(arquivos_processados)

    def crossfade_audios(self, arquivos_processados: list[Path], crossfades: list[float]) -> Path:
        self.stage("Aplicando crossfade entre músicas")
        self.log("\nAplicando crossfade entre músicas...\n")

        audio_final = TEMP_DIR / "audio_final.wav"
        CONTROLE_EXECUCAO.registrar_arquivo_temporario(audio_final)
        comando = [str(FFMPEG), "-y"]
        for arquivo in arquivos_processados:
            comando += ["-i", str(arquivo)]

        filtros = []
        entrada_atual = "0:a"
        for indice, duracao in enumerate(crossfades, start=1):
            saida = "aout" if indice == len(arquivos_processados) - 1 else f"xf{indice}"
            duracao = max(0.01, float(duracao))
            filtros.append(f"[{entrada_atual}][{indice}:a]acrossfade=d={segundos_para_ffmpeg(duracao)}:c1=tri:c2=tri[{saida}]")
            entrada_atual = saida

        comando += [
            "-filter_complex", ";".join(filtros),
            "-map", "[aout]",
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(audio_final),
        ]
        self.rodar_comando(comando)
        self.adicionar_peso(PESO_CONCATENAR)
        return audio_final

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
