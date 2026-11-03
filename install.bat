@echo off
setlocal enabledelayedexpansion

title FiestaPanel - Windows Installer
echo ==============================================================================
echo                 FiestaPanel - Windows Installer Suite
echo ==============================================================================
echo.

cd /d "%~dp0"

REM 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3 is not installed or not in your PATH.
        echo Please install Python 3 (3.10 or newer) from https://www.python.org/
        echo Be sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

echo [OK] Python detected.

REM 2. Port configuration
set /p PORT="Enter Web Panel HTTP Port [8080]: "
if "%PORT%"=="" set PORT=8080

REM 3. Minecraft directory
set /p MC_PATH="Enter Minecraft Server directory [.\minecraft_server]: "
if "%MC_PATH%"=="" set MC_PATH=.\minecraft_server
if not exist "%MC_PATH%" mkdir "%MC_PATH%"

REM 4. Admin password
set /p ADMIN_PASS="Enter Admin password (leave blank for default 'FiestaAdmin2026'): "
if "%ADMIN_PASS%"=="" set ADMIN_PASS=FiestaAdmin2026

REM 5. Virtual environment setup
echo.
echo [1/4] Setting up Python virtual environment...
if not exist "venv\Scripts\python.exe" (
    %PY_CMD% -m venv venv
)

echo [2/4] Installing Python requirements...
venv\Scripts\pip.exe install -r requirements.txt -q

echo [3/4] Writing config.json and users.json...
venv\Scripts\python.exe -c "
import json, hashlib, time, os

cfg = {
    'admin_user': 'admin',
    'admin_pass': '%ADMIN_PASS%',
    'server_dir': os.path.abspath(r'%MC_PATH%'),
    'service_name': '',
    'screen_session': '',
    'host': '0.0.0.0',
    'port': int('%PORT%')
}
with open('config.json', 'w') as f:
    json.dump(cfg, f, indent=2)

p_hash = hashlib.sha256('%ADMIN_PASS%'.encode('utf-8')).hexdigest()
users = {
    'admin': {
        'username': 'admin',
        'password_hash': p_hash,
        'role': 'owner',
        'permissions': ['all'],
        'status': 'active',
        'created_at': time.strftime('%%Y-%%m-%%d %%H:%%M:%%S')
    }
}
with open('users.json', 'w') as f:
    json.dump(users, f, indent=2)
"

echo [4/4] Creating desktop / quick launcher...
echo @echo off > "%~dp0run_fiestapanel.bat"
echo cd /d "%%~dp0" >> "%~dp0run_fiestapanel.bat"
echo start http://localhost:%PORT% >> "%~dp0run_fiestapanel.bat"
echo venv\Scripts\python.exe app.py >> "%~dp0run_fiestapanel.bat"

echo.
echo ==============================================================================
echo             🎉 FIESTAPANEL INSTALLED SUCCESSFULLY ON WINDOWS!
echo ==============================================================================
echo Web Interface URL:  http://localhost:%PORT%
echo Administrator User: admin
echo Admin Password:     %ADMIN_PASS%
echo Minecraft Folder:   %MC_PATH%
echo.
echo You can start FiestaPanel anytime by double-clicking: start.bat
echo ==============================================================================
echo.

set /p START_NOW="Do you want to start FiestaPanel now? (Y/N) [Y]: "
if /i "%START_NOW%"=="N" exit /b 0

start http://localhost:%PORT%
venv\Scripts\python.exe app.py
