@echo off
echo JARVIS-MKIII Launcher Build Script
echo ====================================

pip install pyinstaller pystray pillow psutil requests

if not exist jarvis.ico (
    echo WARNING: jarvis.ico not found. Build will use default icon.
    echo See ICON_NOTE.txt for instructions.
    pyinstaller --onefile --windowed ^
      --name "JARVIS-MKIII" ^
      --add-data "config;config" ^
      jarvis_launcher.py
) else (
    pyinstaller --onefile --windowed ^
      --icon=jarvis.ico ^
      --name "JARVIS-MKIII" ^
      --add-data "config;config" ^
      jarvis_launcher.py
)

echo.
echo Build complete.
echo Executable: dist\JARVIS-MKIII.exe
echo.
pause
