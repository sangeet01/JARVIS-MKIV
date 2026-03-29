@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0..
set JARVIS_DIR=%CD%

REM ── Vault password ──────────────────────────────────────────────────────────
REM Change this to your vault master password, or delete this line and use
REM the password-file method (see windows\SETUP_WINDOWS.md §3).
set JARVIS_VAULT_PASSWORD=17112004

REM ── Paths ───────────────────────────────────────────────────────────────────
set PYTHON=venv\Scripts\python.exe
set NPM=npm

REM ── Preflight checks ────────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment not found.
    echo         Run: python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r windows\requirements_windows.txt
    pause & exit /b 1
)

if not exist "backend\api\main.py" (
    echo [ERROR] backend\api\main.py not found. Are you in the JARVIS-MKIII root directory?
    pause & exit /b 1
)

REM ── Start backend ───────────────────────────────────────────────────────────
echo [JARVIS] Clearing port 8000 if in use...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F 2>nul
echo [JARVIS] Starting backend on http://localhost:8000 ...
start "JARVIS Backend" cmd /k "set JARVIS_VAULT_PASSWORD=%JARVIS_VAULT_PASSWORD% && cd backend && ..\%PYTHON% -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

REM Wait and verify backend is up before launching voice pipeline
echo [JARVIS] Waiting for backend to start...
timeout /t 8 /nobreak >nul

REM Quick health check — curl is built into Windows 10/11
curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | findstr "200" >nul
if errorlevel 1 (
    echo [WARN]  Backend health check failed — it may still be loading.
    echo         Check the "JARVIS Backend" window for errors.
    echo         Proceeding anyway...
    timeout /t 5 /nobreak >nul
) else (
    echo [OK]    Backend is up.
)

REM ── Start voice pipeline ─────────────────────────────────────────────────────
echo [JARVIS] Starting voice pipeline...
start "JARVIS Voice" cmd /k "cd /d %JARVIS_DIR%\backend && set PYTHONPATH=%JARVIS_DIR%\backend && set JARVIS_VAULT_PASSWORD=%JARVIS_VAULT_PASSWORD% && %JARVIS_DIR%\%PYTHON% voice\voice_orchestrator.py"
timeout /t 5 /nobreak >nul

REM ── Start HUD ────────────────────────────────────────────────────────────────
if exist "hud\package.json" (
    echo [JARVIS] Starting HUD...
    start "JARVIS HUD" cmd /k "cd hud && %NPM% start"
) else (
    echo [SKIP]  hud\package.json not found — skipping HUD.
)

REM ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  JARVIS-MKIII is starting up.
echo  Backend : http://localhost:8000
echo  API docs: http://localhost:8000/docs
echo  HUD     : check "JARVIS HUD" window
echo.
echo  Run windows\stop_jarvis.bat to shut everything down.
echo.
pause
endlocal
