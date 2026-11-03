# ==============================================================================
# FiestaPanel - Windows PowerShell Installer
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
# ==============================================================================

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "     FiestaPanel - Windows PowerShell Installer   " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# 1. Check Python
$PythonExe = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonExe) {
    $PythonExe = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Python 3 was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/"
    Exit 1
}

Write-Host "[OK] Using Python: $($PythonExe.Source)" -ForegroundColor Green

# 2. Virtual Environment
$VenvDir = Join-Path $ScriptDir "venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPy)) {
    Write-Host "[1/3] Creating virtual environment..." -ForegroundColor Yellow
    & $PythonExe.Source -m venv $VenvDir
}

Write-Host "[2/3] Installing dependencies..." -ForegroundColor Yellow
& $VenvPy -m pip install --upgrade pip -q
& $VenvPy -m pip install -r requirements.txt -q

# 3. Config initialization
$ConfigFile = Join-Path $ScriptDir "config.json"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "[3/3] Generating config.json and users.json..." -ForegroundColor Yellow
    $DefaultMC = Join-Path $ScriptDir "minecraft_server"
    if (-not (Test-Path $DefaultMC)) { New-Item -ItemType Directory -Path $DefaultMC -Force | Out-Null }
    
    $AdminPass = "FiestaAdmin2026"
    & $VenvPy -c @"
import json, hashlib, time, os
cfg = {
    'admin_user': 'admin',
    'admin_pass': '$AdminPass',
    'server_dir': r'$DefaultMC',
    'service_name': '',
    'screen_session': '',
    'host': '0.0.0.0',
    'port': 8080
}
with open(r'$ConfigFile', 'w') as f:
    json.dump(cfg, f, indent=2)

p_hash = hashlib.sha256(b'$AdminPass').hexdigest()
users = {
    'admin': {
        'username': 'admin',
        'password_hash': p_hash,
        'role': 'owner',
        'permissions': ['all'],
        'status': 'active',
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
}
with open(os.path.join(r'$ScriptDir', 'users.json'), 'w') as f:
    json.dump(users, f, indent=2)
"@
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  FiestaPanel is ready to run on Windows!         " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Run .\start.bat or 'python app.py' to launch."
Write-Host "Default URL: http://localhost:8080"
Write-Host "Admin User:  admin"
Write-Host "Admin Pass:  FiestaAdmin2026"
