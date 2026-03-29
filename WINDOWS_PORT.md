# JARVIS-MKIII — Windows Compatibility Audit
**Date:** 2026-03-29
**Auditor:** Claude Code
**Scope:** `backend/` and `voice/` directories (all subdirectories)

---

## Executive Summary

JARVIS-MKIII is **heavily Linux-native**. It relies on PulseAudio, X11, xdotool, systemd, and Linux-specific paths throughout. A Windows port is **achievable but non-trivial**, requiring a platform abstraction layer and systematic path fixes. Estimated effort: **60–80 hours** for full Windows compatibility.

**Fastest path to Windows:** WSL2 — requires near-zero code changes.
**Native Windows port:** ~2–3 weeks of focused work.

---

## 1. Linux-Only Dependencies

### 1.1 Audio — PulseAudio / pactl

| File | Line | Code |
|------|------|------|
| `backend/voice/tts.py` | ~124 | `subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])` |
| `backend/voice/tts.py` | ~150 | `subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "0"])` |
| `backend/system/os_controller.py` | 17–25 | `def _pulse_env()` — sets `XDG_RUNTIME_DIR=/run/user/{os.getuid()}`, `PULSE_RUNTIME_PATH` |
| `backend/system/os_controller.py` | ~331 | `subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])` |
| `backend/system/os_controller.py` | ~345 | `subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])` |

### 1.2 Desktop Automation — xdotool / wmctrl

| File | Line | Code |
|------|------|------|
| `backend/system/desktop_control.py` | 29–42 | `def _xdotool(*args)` — wraps `subprocess.run(["xdotool", *args])` |
| `backend/system/desktop_control.py` | ~77 | `_xdotool("type", "--clearmodifiers", "--delay", "50", "--", text)` |
| `backend/system/desktop_control.py` | ~124 | `_xdotool("key", "--clearmodifiers", xkey)` |
| `backend/system/desktop_control.py` | ~187 | `_xdotool("search", "--name", "YouTube")` |
| `backend/system/desktop_control.py` | ~195 | `_xdotool("windowactivate", "--sync", window_id)` |
| `backend/agents/autogui_agent.py` | ~153 | `subprocess.run(["xdotool", "search", "--name", title, "windowactivate", "--sync"])` |
| `backend/agents/autogui_agent.py` | ~162 | `subprocess.run(["wmctrl", "-a", title])` |

### 1.3 Screenshot — scrot

| File | Line | Code |
|------|------|------|
| `backend/system/desktop_control.py` | ~55 | `subprocess.run(["scrot", str(path)], env=_display_env())` |

### 1.4 Display — X11 / DISPLAY env

| File | Line | Code |
|------|------|------|
| `backend/system/desktop_control.py` | 21–24 | `def _display_env()` → `{"DISPLAY": os.environ.get("DISPLAY", ":0")}` |
| `backend/tools/computer_control.py` | ~11 | `os.environ.setdefault("DISPLAY", ":0")` |
| `jarvis-mkiii.service` | 15 | `Environment=DISPLAY=:1` |

### 1.5 Service Management — systemd / systemctl

| File | Line | Code |
|------|------|------|
| `backend/system/os_controller.py` | ~386 | `subprocess.Popen(["systemctl", "suspend"])` |
| `backend/system/os_controller.py` | ~394 | `subprocess.Popen(["systemctl", "reboot"])` |
| `backend/system/os_controller.py` | ~402 | `subprocess.Popen(["systemctl", "poweroff"])` |
| `backend/system/os_controller.py` | ~410 | `subprocess.run(["systemctl", "list-unit-files", "--user", "--state=enabled"])` |
| `backend/system/os_controller.py` | ~422 | `subprocess.run(["systemctl", "--user", "enable", service])` |
| `backend/system/os_controller.py` | ~435 | `subprocess.run(["systemctl", "--user", "disable", service])` |
| `jarvis-voice.service` | — | Entire file: systemd unit |
| `jarvis-mkiii.service` | — | Entire file: systemd unit |
| `whatsapp/jarvis-whatsapp.service` | — | Entire file: systemd unit |

### 1.6 Brightness — brightnessctl

| File | Line | Code |
|------|------|------|
| `backend/system/os_controller.py` | ~361 | `subprocess.run(["brightnessctl", "set", f"{pct}%"])` |
| `backend/system/os_controller.py` | ~375 | `subprocess.run(["brightnessctl", "get"])` + `subprocess.run(["brightnessctl", "max"])` |

### 1.7 Network — ip link

| File | Line | Code |
|------|------|------|
| `backend/system/os_controller.py` | ~300 | `subprocess.run(["ip", "link", "set", interface, "down"])` |
| `backend/system/os_controller.py` | ~313 | `subprocess.run(["ip", "link", "set", interface, "up"])` |

### 1.8 Package Managers — apt / snap / flatpak

| File | Line | Code |
|------|------|------|
| `backend/system/terminal_controller.py` | ~132 | `await _run(["sudo", "/usr/bin/apt", "install", "-y", name])` |
| `backend/system/terminal_controller.py` | ~140 | `await _run(["sudo", "/usr/bin/snap", "install", name])` |
| `backend/system/terminal_controller.py` | ~148 | `await _run(["flatpak", "install", "--user", "-y", "flathub", name])` |

### 1.9 Unix-Specific APIs

| File | Line | Code | Issue |
|------|------|------|-------|
| `backend/system/os_controller.py` | ~23 | `os.getuid()` in `/run/user/{uid}` path | `os.getuid()` raises `AttributeError` on Windows |
| `backend/voice/voice_orchestrator.py` | ~276 | `signal.signal(signal.SIGINT, shutdown)` | `SIGINT` works; `SIGTERM`/`SIGKILL` do not |
| `backend/system/app_controller.py` | ~34 | `subprocess.Popen(..., start_new_session=True)` | Unix process group — no Windows equivalent |

### 1.10 Hardcoded /tmp/ Paths

| File | Path Used |
|------|-----------|
| `backend/voice/stt.py` | `/tmp/jarvis_voice_sample.wav` |
| `backend/voice/tts.py` | `/tmp/jarvis_ar.mp3` |
| `backend/api/routers/emotion.py` | `/tmp/jarvis_calibration.wav` |
| `backend/api/routers/vision.py` | `/tmp/jarvis_screen.png` |
| `backend/tools/computer_control.py` | `/tmp/jarvis_screen.png` |
| `backend/vision/vision_engine.py` | `/tmp/jarvis_screen.png`, `/tmp/jarvis_url_image.jpg` |

### 1.11 Linux-Specific Python Package

| Package | Issue |
|---------|-------|
| `python-xlib>=0.33` | X11-only; `import Xlib` will fail on Windows |

### 1.12 xdg-open

| File | Line | Code |
|------|------|------|
| `backend/tools/computer_control.py` | ~112 | `asyncio.create_subprocess_exec("xdg-open", name)` |

---

## 2. Cross-Platform Compatible (Confirmed OK)

| Component | Status | Notes |
|-----------|--------|-------|
| `fastapi` + `uvicorn` | ✅ | Pure Python, fully cross-platform |
| `sounddevice` | ✅ | Uses PortAudio; works on Windows |
| `faster-whisper` | ✅ | ONNX-based; Windows wheels available |
| `kokoro` | ✅ | TTS library; cross-platform |
| `groq` / `httpx` | ✅ | HTTP clients; no OS dependency |
| `anthropic` SDK | ✅ | Pure Python |
| `sqlite3` | ✅ | Built-in; fully cross-platform |
| `chromadb` | ✅ | Pure Python vector DB |
| `psutil` | ✅ | Has Windows backend |
| `pyautogui` | ✅ | Works on Windows (limited vs xdotool) |
| `websockets` | ✅ | Pure Python |
| `PIL` / `Pillow` | ✅ | Cross-platform |
| `numpy` | ✅ | Cross-platform |
| `webrtcvad-wheels` | ✅ | Pre-built wheels for Windows |
| `asyncio` / `threading` | ✅ | Python stdlib; cross-platform |
| `signal.SIGINT` | ✅ | Works on Windows (SIGTERM/SIGKILL do not) |
| Electron/Node HUD | ✅ | Node.js is cross-platform |
| `.env` config | ✅ | No OS dependency |
| `nmap` | ✅ | Windows binary available |

---

## 3. Windows Equivalents Needed

| Linux Component | Windows Replacement | Notes |
|----------------|---------------------|-------|
| `pactl set-source-mute` | `sounddevice` + `comtypes` / `pycaw` | `pycaw` wraps Windows Core Audio API |
| `pactl set-sink-volume` | `pycaw` (`AudioUtilities`, `IAudioEndpointVolume`) | Drop-in for volume control |
| `xdotool type` | `pyautogui.typewrite()` | Works; loses X11 focus guarantees |
| `xdotool key` | `pyautogui.hotkey()` | Equivalent |
| `xdotool search` + `windowactivate` | `pywin32` (`win32gui.FindWindow`, `SetForegroundWindow`) | Full replacement |
| `wmctrl -a` | `pywin32` (`win32gui.SetForegroundWindow`) | Equivalent |
| `scrot` | `pyautogui.screenshot()` or `PIL.ImageGrab` | Already has PyAutoGUI fallback |
| `xdg-open` | `os.startfile()` or `subprocess.run(["start", name], shell=True)` | Easy swap |
| `DISPLAY=:0` env var | Not needed on Windows | Remove/guard with `if sys.platform != "win32"` |
| `os.getuid()` | `os.getlogin()` or `Path.home()` | Replace path construction with `pathlib` |
| `systemctl suspend` | `ctypes.windll.PowrProf.SetSuspendState(0,1,0)` | One-liner |
| `systemctl reboot` | `subprocess.run(["shutdown", "/r", "/t", "0"])` | Easy |
| `systemctl poweroff` | `subprocess.run(["shutdown", "/s", "/t", "0"])` | Easy |
| `systemctl enable/disable` | NSSM (`nssm install jarvis`) or Task Scheduler | Medium complexity |
| `.service` files | NSSM service definitions OR `pywin32` service wrapper | Rewrite required |
| `brightnessctl` | `wmi` (`Win32_MonitorBrightnessMethods`) or `screen-brightness-control` PyPI | `screen-brightness-control` is easiest |
| `ip link set ... down/up` | `netsh interface set interface "Ethernet" disabled/enabled` | Subprocess call swap |
| `apt install` | `winget install` or `choco install` | Swap in terminal_controller.py |
| `snap install` | `winget install` | Swap |
| `flatpak install` | `winget install` | Swap |
| `/tmp/` paths | `tempfile.gettempdir()` → `C:\Users\<user>\AppData\Local\Temp\` | Use `pathlib.Path(tempfile.gettempdir())` |
| `python-xlib` | Remove or guard; use `pywin32` for window ops | Conditional import |
| `start_new_session=True` | `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` | Easy swap |

---

## 4. Effort Estimates

| Component | File(s) | Effort | Reason |
|-----------|---------|--------|--------|
| `/tmp/` path fixes | 6 files | **Easy** | `tempfile.gettempdir()` is a drop-in |
| `xdg-open` → `os.startfile` | `computer_control.py` | **Easy** | One-line change |
| `scrot` fallback | `desktop_control.py` | **Easy** | PyAutoGUI fallback already exists |
| `signal` handling | `voice_orchestrator.py` | **Easy** | SIGINT already works; guard others |
| `start_new_session` | `app_controller.py` | **Easy** | `CREATE_NEW_PROCESS_GROUP` swap |
| `os.getuid()` paths | `os_controller.py` | **Easy** | Replace with `Path.home()` |
| Brightness control | `os_controller.py` | **Easy** | `screen-brightness-control` PyPI package |
| `ip link` → `netsh` | `os_controller.py` | **Easy** | Subprocess command swap |
| Package manager calls | `terminal_controller.py` | **Medium** | Multi-PM dispatch; need to detect OS |
| `systemctl` power commands | `os_controller.py` | **Medium** | 3 functions; Windows `shutdown` commands |
| `systemctl` service mgmt | `os_controller.py` | **Medium** | NSSM or Task Scheduler wrapper needed |
| `.service` files | 3 `.service` files | **Medium** | Rewrite as NSSM configs or pywin32 service |
| `pactl` volume/mute | `tts.py`, `os_controller.py` | **Medium** | Replace with `pycaw`; new API to learn |
| `DISPLAY` / X11 env | `desktop_control.py`, `computer_control.py` | **Medium** | Guard all X11 refs; remove env injection |
| `python-xlib` | `requirements.txt` + any imports | **Medium** | Audit actual usage; make optional |
| `xdotool` type/key | `desktop_control.py`, `autogui_agent.py` | **Medium** | PyAutoGUI equivalents exist but differ |
| `xdotool` window focus | `desktop_control.py`, `autogui_agent.py` | **Hard** | Needs `pywin32` + significant rewrite |
| Service auto-start system | All `.service` + `os_controller.py` | **Hard** | Architecture decision: NSSM vs pywin32 service |
| Full platform abstraction | New `system/platform_*.py` | **Hard** | If aiming for clean cross-platform support |

---

## 5. Recommended Port Order

Port in this sequence for the fastest functional Windows build:

### Phase 1 — Zero-Risk Fixes (1–2 hours)
> Core services will start and run; no Linux tools called at startup.

1. **`/tmp/` → `tempfile.gettempdir()`** — fix all 6 files; nothing breaks on Linux either
2. **`xdg-open` → `os.startfile()`** — guard with `if sys.platform == "win32"`
3. **`os.getuid()` paths** — replace with `pathlib.Path.home() / ".jarvis"` style paths
4. **`start_new_session=True`** — swap to `CREATE_NEW_PROCESS_GROUP` on Windows
5. **`signal` handling** — guard `SIGTERM`/`SIGKILL` with `if sys.platform != "win32"`

### Phase 2 — Audio Pipeline (3–4 hours)
> Voice I/O works on Windows.

6. **Install `pycaw`** — add to `requirements.txt`
7. **Replace `pactl` volume calls** in `os_controller.py` with `pycaw` implementation
8. **Replace `pactl` mute calls** in `tts.py` with `pycaw` or `sounddevice`
9. **Remove `_pulse_env()`** — no longer needed on Windows (keep for Linux via platform guard)

### Phase 3 — Screen Capture (1 hour)
> Screenshots work.

10. **Remove `scrot`** — PyAutoGUI fallback already exists; just make it the primary
11. **Remove `DISPLAY` env injection** — guard with `if sys.platform != "win32"`
12. **Drop `python-xlib`** from requirements or make it optional

### Phase 4 — Basic Desktop Automation (3–4 hours)
> Typing and hotkeys work; window focus is best-effort.

13. **Replace `xdotool type`** with `pyautogui.typewrite()` / `pyautogui.write()`
14. **Replace `xdotool key`** with `pyautogui.hotkey()`
15. **Replace `wmctrl -a`** with `pywin32` (`win32gui.FindWindow` + `SetForegroundWindow`)
16. **Replace `xdotool search/windowactivate`** with `pywin32` equivalents

### Phase 5 — System Control (2–3 hours)
> Power management and brightness work.

17. **`systemctl suspend/reboot/poweroff`** → `ctypes` / `shutdown` commands
18. **`brightnessctl`** → `screen-brightness-control` package
19. **`ip link`** → `netsh` subprocess calls

### Phase 6 — Service Management (4–6 hours)
> JARVIS can be installed as a Windows service.

20. **Package manager dispatch** — add `winget`/`choco` to `terminal_controller.py`
21. **Rewrite `.service` files** as NSSM config scripts or a `pywin32` service wrapper
22. **`systemctl enable/disable`** → NSSM equivalents

### Phase 7 — Hardening (ongoing)
23. **Full `sys.platform` guards** throughout codebase
24. **Create `system/platform_linux.py` + `system/platform_windows.py`** abstraction if codebase grows
25. **CI matrix** — test both Linux and Windows in GitHub Actions

---

## Quick-Win Summary

| What | Time | Unblocks |
|------|------|---------|
| `/tmp/` → `tempfile` | 30 min | All file I/O |
| `pactl` → `pycaw` | 3 hrs | Voice on Windows |
| `scrot` → PyAutoGUI | 30 min | Screenshots |
| `xdotool` type/key → `pyautogui` | 2 hrs | Basic automation |
| Power commands | 1 hr | Sleep/reboot/shutdown |
| `os.getuid()` fix | 30 min | Prevents startup crash |

**Minimum viable Windows JARVIS (voice + basic automation): ~8 hours of work.**

---

## Alternative: WSL2 (Recommended if timeline is tight)

Run JARVIS-MKIII inside WSL2 on Windows with zero code changes:

```bash
# In WSL2 (Ubuntu):
export DISPLAY=:0  # with VcXsrv or WSLg
cd /home/k/JARVIS-MKIII
source venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

WSL2 provides: PulseAudio bridge, X11 via WSLg, full Linux syscalls. The Electron HUD runs natively on Windows and connects to the WSL2 backend via `localhost`.

**Effort: Near-zero. Tradeoff: requires WSL2 setup; not a true native Windows app.**
