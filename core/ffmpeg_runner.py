# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .constants import FFMPEG, LOG_DIR
from .ffmpeg_env import criar_env_ffmpeg
from .process_control import CONTROLE_EXECUCAO, ErroRender, RenderCancelado, criar_kwargs_subprocess_controlado


class FfmpegRunnerMixin:

    def salvar_log_ffmpeg(self, log_completo: str) -> Path:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / "erro_ffmpeg_log.txt"
        try:
            log_path.write_text(log_completo, encoding="utf-8", errors="ignore")
        except OSError as exc:
            self.log(f"\nAviso: não foi possível salvar o log completo em {log_path}: {exc}\n")
        return log_path

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
            log_completo = (
                "COMANDO EXECUTADO:\n" + " ".join(str(c) for c in comando) + "\n\n"
                f"RETURNCODE: {processo.returncode}\n\n"
                "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr
            )
            log_path = self.salvar_log_ffmpeg(log_completo)
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
            if processo.stdout is None:
                raise ErroRender("Não foi possível ler o progresso do FFmpeg.")
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
                    except (IndexError, ValueError) as exc:
                        self.log(f"\nAviso: progresso FFmpeg inválido ignorado: {linha} ({exc})\n")
                elif linha.startswith("progress=end"):
                    self.emitir_progresso_por_peso(progresso_inicio_peso + peso_etapa)

            processo.wait()
        finally:
            CONTROLE_EXECUCAO.limpar_processo(processo)

        if CONTROLE_EXECUCAO.cancelado:
            raise RenderCancelado("Renderização cancelada pelo usuário.")

        if processo.returncode != 0:
            log_completo = (
                "COMANDO EXECUTADO:\n" + " ".join(str(c) for c in comando) + "\n\n"
                f"RETURNCODE: {processo.returncode}\n\n"
                "LOG FFmpeg:\n" + "\n".join(linhas_erro)
            )
            log_path = self.salvar_log_ffmpeg(log_completo)
            raise ErroRender(
                "Erro ao executar FFmpeg.\n"
                f"Log completo salvo em: {log_path}\n"
                f"Returncode: {processo.returncode}\n\n"
                + "\n".join(linhas_erro[-80:])
            )

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

        destino_nulo = "NUL" if os.name == "nt" else "/dev/null"
        smoke = subprocess.run(
            [
                str(FFMPEG),
                "-hide_banner",
                "-loglevel", "error",
                "-f", "lavfi",
                "-i", "color=c=black:s=16x16:d=0.1",
                "-frames:v", "1",
                "-c:v", "h264_nvenc",
                "-f", "null",
                destino_nulo,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            **criar_kwargs_subprocess_controlado(),
        )
        if smoke.returncode != 0:
            self.log("\nAviso: h264_nvenc existe, mas falhou no teste real. Usando CPU/libx264.\n")
            if smoke.stderr:
                self.log(smoke.stderr[-1200:] + "\n")
            return False

        self.log("\nNVENC encontrado e validado: GPU ativada.\n")
        return True
