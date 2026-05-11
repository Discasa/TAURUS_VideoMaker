# -*- coding: utf-8 -*-
from __future__ import annotations

"""Perfis de render para preview e exportacao final."""

from dataclasses import dataclass

from .constants import (
    FINAL_RENDER_SIZE,
    NVENC_BUFSIZE,
    NVENC_CQ,
    NVENC_MAXRATE,
    NVENC_PRESET,
    PRE_RENDER_SIZE,
    PRE_RENDER_VISUAL_SCALE,
)


@dataclass(frozen=True)
class RenderProfile:
    mode: str
    label: str
    output_prefix: str
    output_size: tuple[int, int]
    render_scale: float
    streamable: bool
    audio_enabled: bool
    audio_bitrate: str
    gpu_video_args: tuple[str, ...]
    cpu_video_args: tuple[str, ...]


PREVIEW_RENDER_PROFILE = RenderProfile(
    mode="pre_render",
    label="Preview 540p sem audio",
    output_prefix="preview",
    output_size=PRE_RENDER_SIZE,
    render_scale=PRE_RENDER_VISUAL_SCALE,
    streamable=True,
    audio_enabled=False,
    audio_bitrate="128k",
    gpu_video_args=(
        "-c:v", "h264_nvenc",
        "-preset", "p1",
        "-rc", "vbr",
        "-cq", "28",
        "-b:v", "0",
        "-maxrate", "6M",
        "-bufsize", "12M",
    ),
    cpu_video_args=("-c:v", "libx264", "-preset", "veryfast", "-crf", "30"),
)


FINAL_RENDER_PROFILE = RenderProfile(
    mode="final",
    label="Exportacao final 1080p",
    output_prefix="video_final",
    output_size=FINAL_RENDER_SIZE,
    render_scale=1.0,
    streamable=False,
    audio_enabled=True,
    audio_bitrate="192k",
    gpu_video_args=(
        "-c:v", "h264_nvenc",
        "-preset", NVENC_PRESET,
        "-rc", "vbr",
        "-cq", NVENC_CQ,
        "-b:v", "0",
        "-maxrate", NVENC_MAXRATE,
        "-bufsize", NVENC_BUFSIZE,
    ),
    cpu_video_args=("-c:v", "libx264", "-preset", "medium", "-crf", "20"),
)
