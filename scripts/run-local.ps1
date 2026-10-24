# 本地跑 MusicDL Web（Windows）
#   powershell -ExecutionPolicy Bypass -File scripts\run-local.ps1
#
# 首次运行会自动建虚拟环境并安装 musicdl==2.14.1。

param(
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "创建虚拟环境…" -ForegroundColor Cyan
    python -m venv $Venv
    & $Python -m pip install --upgrade pip
    & $Python -m pip install "musicdl==2.14.1"
}

$env:MUSICDL_HOST = $HostAddress
$env:MUSICDL_PORT = "$Port"
$env:MUSICDL_OUTPUT = Join-Path $RepoRoot "downloads"
$env:MUSICDL_CACHE = Join-Path $RepoRoot ".cache"

Write-Host "启动 http://${HostAddress}:${Port}" -ForegroundColor Green
& $Python (Join-Path $RepoRoot "app\web\server.py")
