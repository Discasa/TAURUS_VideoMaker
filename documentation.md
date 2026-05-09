# LoFi VideoMaker Documentation

## Purpose

LoFi VideoMaker creates rendered lo-fi videos by combining visual media, music tracks, optional background audio, text overlays, watermark settings, and intro text effects through FFmpeg.

## Running the Application

1. Open PowerShell in the project folder.
2. Create and activate a virtual environment if one does not already exist.
3. Install dependencies with `pip install -r requirements.txt`.
4. Start the app with `python lofi_videomaker_v8.py` or `start.bat`.

## FFmpeg Runtime

The script is configured to use the local runtime first:

```text
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

Keep both files together. `ffprobe.exe` is required because the app measures media durations before rendering.

The FFmpeg binaries are intentionally not tracked in Git. If the project is cloned on another machine, copy a Windows FFmpeg build into `ffmpeg/bin/` before running renders.

## Inputs

- Base visual media: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.gif`, or supported image files.
- Music folder: audio tracks such as `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.opus`, or `.wma`.
- Optional background audio: mixed under the main music track at the configured volume.

## Rendering

The app can render with CPU/libx264 or NVIDIA NVENC when supported by the local FFmpeg build and GPU driver. If `h264_nvenc` is unavailable, the script falls back to CPU rendering.

Temporary audio files are written to `_temp_audio_processado/`. Failed FFmpeg logs are written to `erro_ffmpeg_log.txt`.

## Configuration

User choices are persisted in `video_creator_config.json` beside the script. This file is local machine state and should not be committed.

## Maintenance

- Keep generated renders outside source control.
- Keep FFmpeg binaries local unless a release packaging workflow is added.
- After changing FFmpeg command generation, run a short test render and confirm `ffmpeg/bin/ffmpeg.exe` appears in the log path or process command.
- After UI or config changes, run:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\lofi_videomaker_v8.py
```

