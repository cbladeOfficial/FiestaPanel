@echo off
setlocal DisableDelayedExpansion

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

REM 4. Virtual environment and dependencies
echo.
echo [1/4] Setting up Python virtual environment...
if not exist "venv\Scripts\python.exe" %PY_CMD% -m venv venv
if errorlevel 1 exit /b 1

echo [2/4] Installing Python requirements...
venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 exit /b 1

echo [3/4] Setting up the owner account and configuration...
venv\Scripts\python.exe setup_admin.py
if errorlevel 1 exit /b 1
if not exist "config.json" (
    set "FIESTA_SETUP_MC_PATH=%MC_PATH%"
    set "FIESTA_SETUP_PORT=%PORT%"
    venv\Scripts\python.exe -c "import os,json; cfg={'admin_user':'admin','server_dir':os.path.abspath(os.environ['FIESTA_SETUP_MC_PATH']),'service_name':'','screen_session':'','host':'0.0.0.0','port':int(os.environ['FIESTA_SETUP_PORT'])}; f=open('config.json','x',encoding='utf-8'); json.dump(cfg,f,indent=2); f.close()"
    if errorlevel 1 exit /b 1
)

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
echo Admin Password:     Use the password you selected during setup.
echo Minecraft Folder:   %MC_PATH%
echo.
echo You can start FiestaPanel anytime by double-clicking: start.bat
echo ==============================================================================
echo.

set /p START_NOW="Do you want to start FiestaPanel now? (Y/N) [Y]: "
if /i "%START_NOW%"=="N" exit /b 0

start http://localhost:%PORT%
venv\Scripts\python.exe app.py
