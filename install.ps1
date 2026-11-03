# ==============================================================================
# FiestaPanel - Windows 1-Line Turnkey Installer & Setup Script
#
# One-Line Install from PowerShell (Run as Administrator or regular user):
#   irm https://fiesta.debarkak.xyz/install.ps1 | iex
#
# Alternative (GitHub Raw):
#   irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex
#
# From Windows Command Prompt (CMD):
#   powershell -ExecutionPolicy Bypass -Command "irm https://fiesta.debarkak.xyz/install.ps1 | iex"
#
# Local Execution:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ========================================================" -ForegroundColor Cyan
Write-Host "       F I E S T A P A N E L   W I N D O W S   S E T U P  " -ForegroundColor Cyan
Write-Host "       Turnkey Minecraft Server Management Suite         " -ForegroundColor DarkCyan
Write-Host "  ========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Determine Installation Directory
$IsLocal = $false
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "app.py"))) {
    $InstallDir = $PSScriptRoot
    $IsLocal = $true
} else {
    if ($env:FIESTA_DIR) {
        $InstallDir = $env:FIESTA_DIR
    } else {
        $InstallDir = "C:\FiestaPanel"
    }
}

Write-Host "[*] Target Installation Directory: $InstallDir" -ForegroundColor White

# 2. Verify / Auto-Install Python
$PythonExe = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonExe) {
    $PythonExe = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $PythonExe) {
    Write-Host "[!] Python 3 not detected in system PATH." -ForegroundColor Yellow
    $WingetExe = Get-Command winget -ErrorAction SilentlyContinue
    if ($WingetExe) {
        Write-Host "[*] Windows Package Manager (winget) found! Installing Python 3.12..." -ForegroundColor Cyan
        try {
            & winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            $PythonExe = Get-Command python -ErrorAction SilentlyContinue
            if (-not $PythonExe) { $PythonExe = Get-Command py -ErrorAction SilentlyContinue }
        } catch {
            Write-Host "[!] Winget installation could not complete automatically." -ForegroundColor Yellow
        }
    }
}

if (-not $PythonExe) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "  ERROR: Python 3.10+ is required to run FiestaPanel.     " -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "Please download and install Python from:"
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "CRITICAL: Check 'Add python.exe to PATH' during installation!" -ForegroundColor Yellow
    Write-Host "After installing Python, re-run this command."
    return
}

Write-Host "[✓] Python Runtime Detected: $($PythonExe.Source)" -ForegroundColor Green

# 3. Download & Deploy Codebase (if remote 1-line installation)
if (-not $IsLocal) {
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    Write-Host "[1/4] Downloading FiestaPanel application package..." -ForegroundColor Cyan
    $TempZip = Join-Path $env:TEMP "fiestapanel_dl_$(Get-Random).zip"
    $TempExtract = Join-Path $env:TEMP "fiestapanel_ext_$(Get-Random)"

    $Downloaded = $false
    $DownloadUrls = @(
        "https://fiesta.debarkak.xyz/static/fiestapanel-latest.zip",
        "https://github.com/open-fiestasmp/FiestaPanel/archive/refs/heads/main.zip"
    )

    foreach ($url in $DownloadUrls) {
        try {
            Write-Host "      Fetching package from $url..." -ForegroundColor DarkGray
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
            Invoke-WebRequest -Uri $url -OutFile $TempZip -UseBasicParsing -TimeoutSec 60
            if ((Test-Path $TempZip) -and ((Get-Item $TempZip).Length -gt 10000)) {
                $Downloaded = $true
                break
            }
        } catch {
            Write-Host "      Fetch from $url failed, trying alternate..." -ForegroundColor DarkYellow
        }
    }

    if (-not $Downloaded) {
        Write-Host "[ERROR] Could not download FiestaPanel distribution archive." -ForegroundColor Red
        return
    }

    Write-Host "      Extracting files into $InstallDir..." -ForegroundColor DarkGray
    Expand-Archive -Path $TempZip -DestinationPath $TempExtract -Force

    # If GitHub archive has subfolder FiestaPanel-main, move contents up
    $GithubSubdir = Join-Path $TempExtract "FiestaPanel-main"
    if (Test-Path $GithubSubdir) {
        Get-ChildItem -Path $GithubSubdir | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $InstallDir -Recurse -Force
        }
    } else {
        Get-ChildItem -Path $TempExtract | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $InstallDir -Recurse -Force
        }
    }

    # Cleanup temp files
    Remove-Item -Path $TempZip -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $TempExtract -Recurse -Force -ErrorAction SilentlyContinue
}

# 4. Setup Virtual Environment
Set-Location $InstallDir
$VenvDir = Join-Path $InstallDir "venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPy)) {
    Write-Host "[2/4] Initializing Python virtual environment in $VenvDir..." -ForegroundColor Cyan
    & $PythonExe.Source -m venv $VenvDir
} else {
    Write-Host "[2/4] Python virtual environment already present." -ForegroundColor Green
}

# 5. Install Dependencies
Write-Host "[3/4] Installing / updating dependencies..." -ForegroundColor Cyan
& $VenvPip install --upgrade pip -q
& $VenvPip install flask requests psutil Pillow nbtlib -q

# 6. Initialize Config & Admin User
Write-Host "[4/4] Validating configuration & storage paths..." -ForegroundColor Cyan
$ConfigFile = Join-Path $InstallDir "config.json"
$UsersFile = Join-Path $InstallDir "users.json"
$DefaultMC = Join-Path $InstallDir "minecraft_server"

if (-not (Test-Path $DefaultMC)) {
    New-Item -ItemType Directory -Path $DefaultMC -Force | Out-Null
}

if (-not (Test-Path $ConfigFile)) {
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
with open(r'$UsersFile', 'w') as f:
    json.dump(users, f, indent=2)
"@
    Write-Host "[✓] Initial config and owner user created." -ForegroundColor Green
}

# 7. Create Windows Desktop Shortcut (Optional convenience)
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [System.Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "FiestaPanel.lnk"
    $StartBat = Join-Path $InstallDir "start.bat"
    if (Test-Path $StartBat) {
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $StartBat
        $Shortcut.WorkingDirectory = $InstallDir
        $Shortcut.Description = "Launch FiestaPanel Minecraft Server Portal"
        $Shortcut.Save()
        Write-Host "[✓] Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
    }
} catch {
    # Non-critical, ignore if COM fails
}

# 8. Success Output Banner
Write-Host ""
Write-Host "  ========================================================" -ForegroundColor Green
Write-Host "    F I E S T A P A N E L   I N S T A L L E D   O K !     " -ForegroundColor Green
Write-Host "  ========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location:   $InstallDir" -ForegroundColor White
Write-Host "  Portal URL: http://localhost:8080" -ForegroundColor Yellow
Write-Host "  Admin User: admin" -ForegroundColor Yellow
Write-Host "  Admin Pass: FiestaAdmin2026" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Quick Launch:" -ForegroundColor Cyan
Write-Host "    cd `"$InstallDir`"" -ForegroundColor White
Write-Host "    .\start.bat" -ForegroundColor White
Write-Host ""
Write-Host "  Command Line Management:" -ForegroundColor Cyan
Write-Host "    .\panelctl.bat status" -ForegroundColor White
Write-Host "    .\panelctl.bat reset-admin" -ForegroundColor White
Write-Host ""
