$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    py -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller .\packaging\LoFi_VideoMaker.spec --clean --noconfirm

Write-Host "Executável gerado em: dist\LoFi_VideoMaker.exe"
