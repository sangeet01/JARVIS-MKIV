@echo off
setlocal enabledelayedexpansion

set DATASET=%~dp0dataset.jsonl
set MIN_ENTRIES=200

if not exist "%DATASET%" (
    echo Error: Dataset not found at %DATASET%
    exit /b 1
)

:: Count lines
set COUNT=0
for /f %%A in ('find /c /v "" ^< "%DATASET%"') do set COUNT=%%A
echo Dataset size: %COUNT% entries

if %COUNT% LSS %MIN_ENTRIES% (
    echo Not enough data yet. Need %MIN_ENTRIES%+ entries. Currently: %COUNT%
    echo Keep using JARVIS to auto-collect more interactions.
    exit /b 1
)

echo Dataset ready for training ^(%COUNT% entries^).
echo.
echo Options:
echo   1. Google Colab ^(recommended^): Upload training\dataset.jsonl to colab_finetune.ipynb
echo   2. Local GPU training: python training\local_train.py
echo.
echo Colab notebook: training\colab_finetune.ipynb
echo.

:: Check for NVIDIA GPU
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo GPU detected. Checking VRAM...
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits') do set VRAM=%%i
    echo VRAM: !VRAM! MB
    if !VRAM! GEQ 8000 (
        echo Sufficient VRAM for local training.
        set /p choice="Run local training now? [y/N]: "
        if /i "!choice!"=="y" (
            python training\local_train.py
        )
    ) else (
        echo Insufficient VRAM for 8B model. Use Google Colab instead.
    )
) else (
    echo No GPU detected. Use Google Colab for training.
)

pause
