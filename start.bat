@echo off
setlocal enabledelayedexpansion

title FiestaPanel - Modern ^& Retro Minecraft Server Manager
echo ==============================================================================
echo                 FiestaPanel - Windows Starter
echo ==============================================================================
echo.

cd /d "%~dp0"

REM 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3 was not found in your PATH.
        echo Please download and install Python 3.10+ from:
        echo   https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

REM 2. Check Java installation (optional warning)
where java >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Java was not detected in PATH.
    echo Minecraft requires Java 21+ for version 1.20.5 and newer.
    echo You can download Java from: https://adoptium.net/
    echo You can still start the panel and install server software.
    echo.
)

REM 3. Setup Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating Python virtual environment...
    %PY_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM 4. Install Dependencies
echo [2/3] Checking dependencies...
venv\Scripts\pip.exe install -r requirements.txt -q

REM 5. Initialize config if missing
if not exist "config.json" (
    echo [3/3] Generating initial config.json...
    copy config.example.json config.json >nul
)

if not exist "minecraft_server" (
    mkdir "minecraft_server" 2>nul
)

echo.
echo ==============================================================================
echo [SUCCESS] Starting FiestaPanel...
echo Access the web interface at: http://localhost:8080
echo Press Ctrl+C in this window to stop the panel.
echo ==============================================================================
echo.

start http://localhost:8080
venv\Scripts\python.exe app.py
pause
