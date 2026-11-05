@echo off
rem ==============================================================================
rem FiestaPanel Windows CLI Wrapper
rem ==============================================================================

set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    "%SCRIPT_DIR%venv\Scripts\python.exe" "%SCRIPT_DIR%fiestapanel.py" %*
) else (
    python "%SCRIPT_DIR%fiestapanel.py" %*
)
