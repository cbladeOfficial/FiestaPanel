@echo off
rem ==============================================================================
rem FiestaPanel Windows CLI Wrapper (backward compatibility for fiestapanel)
rem ==============================================================================

set SCRIPT_DIR=%~dp0
call "%SCRIPT_DIR%fiestapanel.bat" %*
