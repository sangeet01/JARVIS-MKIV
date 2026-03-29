@echo off
cd /d %~dp0..

REM Set vault password — change this or use a .env file
set JARVIS_VAULT_PASSWORD=17112004

echo [JARVIS] Starting backend...
start "JARVIS Backend" cmd /k "cd backend && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
timeout /t 8 /nobreak >nul

echo [JARVIS] Starting voice pipeline...
start "JARVIS Voice" cmd /k "cd backend && python voice/voice_orchestrator.py"
timeout /t 5 /nobreak >nul

echo [JARVIS] Starting HUD...
start "JARVIS HUD" cmd /k "cd hud && npm start"

echo.
echo JARVIS-MKIII started. Close this window to leave services running.
pause
