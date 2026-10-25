@echo off
title Stop Open Source Food Truckin'
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":5053 .*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Open Source Food Truckin' stopped. It starts again at next login, or run Start.bat.
pause
