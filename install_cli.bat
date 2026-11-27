@echo off
title Install Blamestorm CLI Globally
echo ========================================================
echo   Installing Blamestorm Executable Globally...
echo ========================================================

if not exist "%~dp0dist\blamestorm.exe" (
    echo [ERROR] dist\blamestorm.exe not found! Run 'pyinstaller blamestorm.spec' first.
    pause
    exit /b 1
)

copy /Y "%~dp0dist\blamestorm.exe" "%LOCALAPPDATA%\Microsoft\WindowsApps\blamestorm.exe" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Blamestorm CLI has been installed into:
    echo   %LOCALAPPDATA%\Microsoft\WindowsApps\blamestorm.exe
    echo.
    echo You can now open ANY command prompt, PowerShell, or terminal in ANY git repository and run:
    echo.
    echo     blamestorm            (prints repo details and starts web UI)
    echo     blamestorm --info     (prints all active repo details to terminal and exits)
    echo.
) else (
    echo [!] Could not copy directly to WindowsApps. Adding dist directory to User PATH...
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%~dp0dist', 'User')"
    echo [SUCCESS] Added %~dp0dist to User PATH. Restart your terminal to use 'blamestorm'.
)
pause
