# ==============================================================================
# FiestaPanel - Windows 1-Line Turnkey Installer & Setup Script
#
# One-Line Install from PowerShell (Direct from GitHub):
#   irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex
#
# From Windows Command Prompt (CMD):
#   powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex"
#
# Mirror (Optional):
#   irm https://fiesta.debarkak.xyz/install.ps1 | iex
#
# Local Execution:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# ==============================================================================

param (
    [switch]$NoAutostart = $false,
    [string]$Autostart = ""
)

$ErrorActionPreference = "Stop"

$EnableAutostart = $true
if ($NoAutostart) {
    $EnableAutostart = $false
} elseif ($Autostart -eq "false" -or $Autostart -eq "0") {
    $EnableAutostart = $false
} elseif ($env:FIESTA_AUTOSTART -eq "0" -or $env:FIESTA_AUTOSTART -eq "false") {
    $EnableAutostart = $false
}

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
        "https://github.com/open-fiestasmp/FiestaPanel/archive/refs/heads/main.zip",
        "https://github.com/open-fiestasmp/FiestaPanel/archive/refs/heads/master.zip"
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
& $VenvPip install -r (Join-Path $InstallDir "requirements.txt") -q
if ($LASTEXITCODE -ne 0) { throw "Failed to install Python dependencies." }

# 6. Initialize Config & Admin User
Write-Host "[4/4] Validating configuration & storage paths..." -ForegroundColor Cyan
$ConfigFile = Join-Path $InstallDir "config.json"
$UsersFile = Join-Path $InstallDir "users.json"
$DefaultMC = Join-Path $InstallDir "minecraft_server"

if (-not (Test-Path $DefaultMC)) {
    New-Item -ItemType Directory -Path $DefaultMC -Force | Out-Null
}

# Create an owner only when no user store exists; existing accounts are preserved.
& $VenvPy (Join-Path $InstallDir "setup_admin.py") --data-dir $InstallDir
if ($LASTEXITCODE -ne 0) { throw "Owner account setup failed." }
if (-not (Test-Path $ConfigFile)) {
    $Config = @{
        admin_user = "admin"
        server_dir = $DefaultMC
        service_name = ""
        screen_session = ""
        host = "0.0.0.0"
        port = 8080
        autostart = $EnableAutostart
    }
    $Config | ConvertTo-Json | Set-Content -Path $ConfigFile -Encoding UTF8
}
Write-Host "[✓] Configuration and owner account are ready." -ForegroundColor Green

# 7. Configure Auto-Start & Desktop Shortcuts
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

    if ($EnableAutostart -and (Test-Path $StartBat)) {
        # Configure Windows Startup Folder
        $StartupPath = [System.Environment]::GetFolderPath("Startup")
        $StartupShortcut = Join-Path $StartupPath "FiestaPanel.lnk"
        $AutoShortcut = $WshShell.CreateShortcut($StartupShortcut)
        $AutoShortcut.TargetPath = $StartBat
        $AutoShortcut.WorkingDirectory = $InstallDir
        $AutoShortcut.Description = "Auto-start FiestaPanel on user logon"
        $AutoShortcut.Save()

        # Also register in HKCU\Software\Microsoft\Windows\CurrentVersion\Run
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "FiestaPanel" -Value "`"$StartBat`"" -Force -ErrorAction SilentlyContinue

        Write-Host "[✓] Auto-Start on Windows logon enabled (Startup folder & Run registry)" -ForegroundColor Green
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
Write-Host "  Admin Pass: Use the password you created during setup." -ForegroundColor Yellow
Write-Host "  Auto-Start: $(if ($EnableAutostart) { 'Enabled (Windows Startup & Run Registry)' } else { 'Disabled' })" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick Launch:" -ForegroundColor Cyan
Write-Host "    cd `"$InstallDir`"" -ForegroundColor White
Write-Host "    .\start.bat" -ForegroundColor White
Write-Host ""
Write-Host "  Command Line Management:" -ForegroundColor Cyan
Write-Host "    .\fiestapanel.bat status" -ForegroundColor White
Write-Host "    .\fiestapanel.bat autostart enable" -ForegroundColor White
Write-Host "    .\fiestapanel.bat autostart disable" -ForegroundColor White
Write-Host "    .\fiestapanel.bat reset-admin" -ForegroundColor White
Write-Host ""
