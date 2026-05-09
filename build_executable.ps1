$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    py -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller .\packaging\TAURUS_Video_Maker.spec --clean --noconfirm

Write-Host "Executável gerado em: dist\TAURUS Video Maker.exe"
