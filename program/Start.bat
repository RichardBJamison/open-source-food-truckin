@echo off
title Open Source Food Truckin'
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-server.ps1"
