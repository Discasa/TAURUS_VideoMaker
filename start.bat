@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "lofi_videomaker_v8.py"
) else (
    py "lofi_videomaker_v8.py"
)

