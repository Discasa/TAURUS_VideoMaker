# LoFi VideoMaker

LoFi VideoMaker is a Windows desktop tool for building long lo-fi videos from a base video/GIF/image and a folder of music tracks. It provides a PySide6 interface, FFmpeg-based rendering, optional NVIDIA NVENC acceleration, loudness normalization, fade controls, background audio mixing, title overlays, watermark controls, and intro text effects.

## Requirements

- Windows 10 or newer.
- Python 3.10 or newer.
- Python dependency: `PySide6`.
- Local FFmpeg runtime in `ffmpeg/bin/` beside the script:
  - `ffmpeg/bin/ffmpeg.exe`
  - `ffmpeg/bin/ffprobe.exe`

This workspace already has a local FFmpeg copy in that folder. The binaries are ignored by Git because they are large.

## Quick Start

```powershell
cd F:\scripts\GitHub\LoFi_VideoMaker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\lofi_videomaker_v8.py
```

Or run:

```powershell
.\start.bat
```

## Repository Layout

```text
LoFi_VideoMaker/
  lofi_videomaker_v8.py       Main PySide6 application
  start.bat                   Windows launcher
  requirements.txt            Python runtime dependencies
  ffmpeg/bin/                 Local FFmpeg runtime used by the app
  README.md                   Project overview
  documentation.md            Detailed usage and maintenance notes
  CHANGELOG.md                Project history
  LICENSE                     Project license
  THIRD_PARTY_NOTICES.md      FFmpeg notice
```

## Notes

The application saves its UI settings to `video_creator_config.json` beside the script and writes FFmpeg error details to `erro_ffmpeg_log.txt` when a render fails. Those files are local runtime artifacts and are ignored by Git.

