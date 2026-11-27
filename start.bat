@echo off
title Blamestorm — AI Git Assistant
if exist "%~dp0dist\blamestorm.exe" (
    "%~dp0dist\blamestorm.exe" %*
) else (
    python "%~dp0blamestorm.py" %*
)
