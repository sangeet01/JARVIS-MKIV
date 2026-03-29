@echo off
echo [JARVIS] Stopping all JARVIS processes...

taskkill /f /fi "WINDOWTITLE eq JARVIS Backend" /t 2>nul
taskkill /f /fi "WINDOWTITLE eq JARVIS Voice" /t 2>nul
taskkill /f /fi "WINDOWTITLE eq JARVIS HUD" /t 2>nul

REM Fallback: kill by process name
taskkill /f /im python.exe /t 2>nul
taskkill /f /im node.exe /t 2>nul

echo [JARVIS] Stopped.
pause
