@echo off
title Open Source Food Truckin' - Install
cd /d "%~dp0"
if not exist "%~dp0install.ps1" (
  echo.
  echo   Unzip first: right-click the downloaded zip, choose "Extract All...",
  echo   then open the extracted folder and double-click Install.bat.
  echo.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 pause
