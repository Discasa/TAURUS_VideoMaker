# -*- coding: utf-8 -*-
from __future__ import annotations

import random
from pathlib import Path

from .constants import FINAL_RENDER_SIZE, TEMP_DIR
from .ffmpeg_env import caminho_pasta_fontes_windows, preparar_pasta_fontes_ffmpeg
from .models import IntroFraseConfig, TrackInfo
from .text_utils import (
    boxborderw_texto,
    cor_drawtext,
    escape_drawtext,
    escape_fontfile,
    overlay_position_expr,
    segundos_para_ffmpeg,
    tamanho_sombra_drawtext,
)


class VideoFilterMixin:

    def preparar_frases_intro(self) -> list[IntroFraseConfig]:
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
        self._frases_intro_ativas = frases
        return frases

    def frases_intro_ativas(self) -> list[IntroFraseConfig]:
        if self._frases_intro_ativas is None:
            return self.preparar_frases_intro()
        return list(self._frases_intro_ativas)

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
        escala_render = self.render_scale
        margin_x = int(round(cfg.margin_x * escala_render))
        margin_y = int(round(cfg.margin_y * escala_render))

        opcoes = []
        fontfile = escape_fontfile(self.caminho_fontfile_drawtext(cfg.font_family, False))
        opcoes.append(f"fontfile='{fontfile}'")

        posicoes = {
            "inferior_direita": (f"w-tw-{margin_x}", f"h-th-{margin_y}"),
            "inferior_esquerda": (f"{margin_x}", f"h-th-{margin_y}"),
            "inferior_centro": ("(w-tw)/2", f"h-th-{margin_y}"),
            "superior_direita": (f"w-tw-{margin_x}", f"{margin_y}"),
            "superior_esquerda": (f"{margin_x}", f"{margin_y}"),
            "superior_centro": ("(w-tw)/2", f"{margin_y}"),
            "centro": ("(w-tw)/2", "(h-th)/2"),
        }
        x, y = posicoes.get(cfg.position, posicoes["inferior_direita"])
        shadow_size = tamanho_sombra_drawtext(getattr(cfg, "shadow_size", 2.0) * escala_render)

        opcoes += [
            f"text='{escape_drawtext(cfg.text)}'",
            f"fontcolor={cor_drawtext(cfg.color, cfg.opacity)}",
            f"fontsize={max(1, int(round(cfg.font_size * escala_render)))}",
            f"x={x}",
            f"y={y}",
            f"shadowcolor={cor_drawtext(cfg.shadow_color, cfg.shadow_opacity if cfg.shadow_enabled else 0.0)}",
            f"shadowx={shadow_size}",
            f"shadowy={shadow_size}",
        ]
        if cfg.background_box:
            opcoes += [
                "box=1",
                f"boxcolor={cor_drawtext(cfg.background_color, cfg.background_opacity)}",
                f"boxborderw={boxborderw_texto(getattr(cfg, 'background_padding', 6.0) * escala_render)}",
            ]
        return "drawtext=" + ":".join(opcoes)

    def criar_overlay_watermark_imagem(self, entrada_video: str, indice_imagem: int) -> list[str]:
        cfg = self.config.watermark
        escala_render = self.render_scale
        x, y = overlay_position_expr(
            cfg.position,
            int(round(cfg.margin_x * escala_render)),
            int(round(cfg.margin_y * escala_render)),
        )
        filtros: list[str] = []

        # Corrige a marca d'água por imagem: normaliza a imagem para RGBA,
        # preserva transparência de PNG/WebP e aplica a opacidade escolhida.
        # setsar=1 evita distorção em imagens/vídeos com sample aspect ratio estranho.
        largura = int(round((getattr(cfg, "image_width", 0) or 0) * escala_render))
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
        escala_render = self.render_scale

        font_size = max(1, int(round(int(getattr(cfg, "font_size", 34)) * escala_render)))
        color = getattr(cfg, "color", "#FFFFFF")
        opacity = float(getattr(cfg, "opacity", 0.93))
        shadow_opacity = float(getattr(cfg, "shadow_opacity", 0.60)) if getattr(cfg, "shadow_enabled", True) else 0.0
        shadow_color = getattr(cfg, "shadow_color", "#000000")
        shadow_size = tamanho_sombra_drawtext(getattr(cfg, "shadow_size", 2.0) * escala_render)
        font_family = getattr(cfg, "font_family", "Georgia")
        bold = int(getattr(cfg, "font_weight", 400)) >= 600 if intro else False
        fontfile = escape_fontfile(self.caminho_fontfile_drawtext(font_family, bold))

        if intro:
            x, y = self.posicao_drawtext_expr(
                getattr(cfg, "position", "inferior_esquerda"),
                int(round(int(getattr(cfg, "margin_x", 90)) * escala_render)),
                int(round(int(getattr(cfg, "margin_y", 120)) * escala_render)),
            )
        else:
            x, y = self.posicao_drawtext_expr(
                getattr(cfg, "position", "inferior_esquerda"),
                int(round(int(getattr(cfg, "margin_left", 45)) * escala_render)),
                int(round(int(getattr(cfg, "margin_bottom", 42)) * escala_render)),
            )

        opcoes = [
            f"fontfile='{fontfile}'",
            f"text='{texto}'",
            f"fontcolor={cor_drawtext(color, opacity)}",
            f"fontsize={font_size}",
            f"x={x}",
            f"y={y}",
            f"shadowcolor={cor_drawtext(shadow_color, shadow_opacity)}",
            f"shadowx={shadow_size}",
            f"shadowy={shadow_size}",
            f"enable='between(t,{inicio:.3f},{fim:.3f})'",
        ]

        if getattr(cfg, "background_box", False):
            opcoes += [
                "box=1",
                f"boxcolor={cor_drawtext(getattr(cfg, 'background_color', '#000000'), float(getattr(cfg, 'box_opacity', getattr(cfg, 'background_opacity', 0.35))))}",
                f"boxborderw={boxborderw_texto(getattr(cfg, 'background_padding', 6.0) * escala_render)}",
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

    def criar_filtro_video(self, tracks: list[TrackInfo], watermark_image_index: int | None = None, output_size: tuple[int, int] = FINAL_RENDER_SIZE) -> str:
        filtros: list[str] = []
        largura, altura = output_size
        filtros.append(
            f"[0:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
            f"crop={largura}:{altura},setsar=1[vbase]"
        )
        entrada_atual = "vbase"
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

    def criar_filter_complex(
        self,
        tracks: list[TrackInfo],
        usar_fundo: bool,
        watermark_image_index: int | None = None,
        typing_audio_index: int | None = None,
        duracao_total: float | None = None,
        output_size: tuple[int, int] = FINAL_RENDER_SIZE,
        include_audio: bool = True,
    ) -> Path:
        filtros = [self.criar_filtro_video(tracks, watermark_image_index, output_size)]
        if not include_audio:
            return self.salvar_filter_complex(filtros)

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

        return self.salvar_filter_complex(filtros)

    def salvar_filter_complex(self, filtros: list[str]) -> Path:
        filter_complex = ";\n".join(filtros)
        arquivo_filtro = TEMP_DIR / "filter_complex.txt"
        arquivo_filtro.write_text(filter_complex, encoding="utf-8")

        self.log("\nFiltro complex gerado:\n")
        self.log(filter_complex + "\n")
        return arquivo_filtro
