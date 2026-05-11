# -*- coding: utf-8 -*-
from __future__ import annotations

"""Controle de processo, pausa e cancelamento do FFmpeg."""

import ctypes
import logging
import os
import signal
import subprocess
import threading
from pathlib import Path

LOGGER = logging.getLogger(__name__)

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
            except OSError as exc:
                LOGGER.debug("Falha ao excluir arquivo cancelado %s: %s", arquivo, exc)

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
                except OSError as exc:
                    LOGGER.debug("Falha ao encerrar grupo do processo %s: %s", processo.pid, exc)
                    processo.terminate()
        except (OSError, subprocess.SubprocessError, AttributeError) as exc:
            LOGGER.debug("Falha ao encerrar processo %s: %s", getattr(processo, "pid", None), exc)
            try:
                processo.kill()
            except (OSError, AttributeError) as kill_exc:
                LOGGER.debug("Falha ao forcar encerramento do processo %s: %s", getattr(processo, "pid", None), kill_exc)

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
        except (OSError, AttributeError, ValueError) as exc:
            LOGGER.debug("Falha ao pausar processo %s: %s", pid, exc)

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
        except (OSError, AttributeError, ValueError) as exc:
            LOGGER.debug("Falha ao retomar processo %s: %s", pid, exc)


CONTROLE_EXECUCAO = ControleExecucao()

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
