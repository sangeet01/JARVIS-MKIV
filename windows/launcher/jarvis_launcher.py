"""
JARVIS-MKIII Windows System Tray Launcher
Manages JARVIS backend and voice pipeline as a tray application.
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import pystray
import requests
from PIL import Image, ImageDraw
import psutil

# ── Paths ────────────────────────────────────────────────────────────────────
APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
CONFIG_DIR = APPDATA / "JARVIS"
CONFIG_FILE = CONFIG_DIR / "config.json"
JARVIS_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SCRIPT = JARVIS_ROOT / "backend" / "api" / "main.py"
VOICE_SCRIPT = JARVIS_ROOT / "backend" / "voice" / "stt.py"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "server_ip": "",          # Empty = local mode
    "server_port": 8000,
    "vault_password": "",
    "auto_start": False,
}

# ── State ─────────────────────────────────────────────────────────────────────
_procs: list[subprocess.Popen] = []
_config: dict = {}
_icon = None


# ── Config ────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        cfg = {**DEFAULT_CONFIG, **data}
    else:
        cfg = DEFAULT_CONFIG.copy()
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Icon ──────────────────────────────────────────────────────────────────────
def _make_icon(online: bool = False) -> Image.Image:
    """Generate a simple arc-reactor style tray icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 200, 255) if online else (100, 100, 120)
    draw.ellipse([4, 4, 60, 60], fill=(20, 20, 30), outline=color, width=3)
    draw.ellipse([18, 18, 46, 46], fill=color)
    draw.ellipse([26, 26, 38, 38], fill=(20, 20, 30))
    return img


# ── Backend Control ───────────────────────────────────────────────────────────
def _server_url() -> str:
    ip = _config.get("server_ip", "").strip()
    port = _config.get("server_port", 8000)
    host = ip if ip else "localhost"
    return f"http://{host}:{port}"


def _is_backend_alive() -> bool:
    try:
        r = requests.get(f"{_server_url()}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _wait_for_backend(timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_backend_alive():
            return True
        time.sleep(1)
    return False


def start_jarvis(icon=None, item=None) -> None:
    global _procs
    if _procs:
        _notify("JARVIS already running, sir.")
        return

    remote_ip = _config.get("server_ip", "").strip()
    if remote_ip:
        _notify(f"Remote mode — connecting to {remote_ip}, sir.")
        _start_voice_only()
        return

    _notify("Starting JARVIS systems, sir.")
    try:
        env = os.environ.copy()
        if _config.get("vault_password"):
            env["JARVIS_VAULT_PASSWORD"] = _config["vault_password"]

        backend = subprocess.Popen(
            [sys.executable, str(BACKEND_SCRIPT)],
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _procs.append(backend)

        threading.Thread(target=_watch_startup, daemon=True).start()
    except Exception as e:
        _notify(f"Launch failed: {e}")


def _watch_startup() -> None:
    if _wait_for_backend(timeout=30):
        _notify("JARVIS Online, sir.")
        if _icon:
            _icon.icon = _make_icon(online=True)
    else:
        _notify("Backend failed to start, sir.")


def _start_voice_only() -> None:
    try:
        proc = subprocess.Popen(
            [sys.executable, str(VOICE_SCRIPT)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _procs.append(proc)
        _notify("Voice pipeline active, sir.")
    except Exception as e:
        _notify(f"Voice pipeline failed: {e}")


def stop_jarvis(icon=None, item=None) -> None:
    global _procs
    if not _procs:
        _notify("Nothing to stop, sir.")
        return

    for proc in _procs:
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except Exception:
            pass

    _procs.clear()
    if _icon:
        _icon.icon = _make_icon(online=False)
    _notify("JARVIS systems offline, sir.")


def open_hud(icon=None, item=None) -> None:
    webbrowser.open(_server_url())


# ── Settings Dialog ───────────────────────────────────────────────────────────
def open_settings(icon=None, item=None) -> None:
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title("JARVIS Settings")
        root.geometry("380x220")
        root.resizable(False, False)
        root.configure(bg="#0a0a1a")

        style = {"bg": "#0a0a1a", "fg": "#00c8ff", "font": ("Consolas", 10)}
        entry_style = {"bg": "#111122", "fg": "#00c8ff", "insertbackground": "#00c8ff",
                       "relief": "flat", "font": ("Consolas", 10)}

        tk.Label(root, text="Server IP (blank = local):", **style).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        ip_var = tk.StringVar(value=_config.get("server_ip", ""))
        tk.Entry(root, textvariable=ip_var, width=25, **entry_style).grid(row=0, column=1, padx=10)

        tk.Label(root, text="Server Port:", **style).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        port_var = tk.StringVar(value=str(_config.get("server_port", 8000)))
        tk.Entry(root, textvariable=port_var, width=25, **entry_style).grid(row=1, column=1, padx=10)

        tk.Label(root, text="Vault Password:", **style).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        pw_var = tk.StringVar(value=_config.get("vault_password", ""))
        tk.Entry(root, textvariable=pw_var, show="*", width=25, **entry_style).grid(row=2, column=1, padx=10)

        auto_var = tk.BooleanVar(value=_config.get("auto_start", False))
        tk.Checkbutton(root, text="Auto-start on launch", variable=auto_var,
                       bg="#0a0a1a", fg="#00c8ff", selectcolor="#111122",
                       activebackground="#0a0a1a").grid(row=3, column=0, columnspan=2, pady=4)

        def save_and_close():
            _config["server_ip"] = ip_var.get().strip()
            _config["server_port"] = int(port_var.get() or 8000)
            _config["vault_password"] = pw_var.get()
            _config["auto_start"] = auto_var.get()
            save_config(_config)
            root.destroy()

        tk.Button(root, text="Save", command=save_and_close,
                  bg="#00c8ff", fg="#0a0a1a", font=("Consolas", 10, "bold"),
                  relief="flat", padx=20).grid(row=4, column=0, columnspan=2, pady=12)

        root.mainloop()
    except ImportError:
        _notify("tkinter not available for settings dialog.")


# ── Notifications ─────────────────────────────────────────────────────────────
def _notify(msg: str) -> None:
    if _icon:
        _icon.notify(msg, "JARVIS-MKIII")


# ── Tray ──────────────────────────────────────────────────────────────────────
def exit_app(icon=None, item=None) -> None:
    stop_jarvis()
    if _icon:
        _icon.stop()


def show_menu(icon, item):
    pass  # placeholder


def build_menu():
    return pystray.Menu(
        pystray.MenuItem("⚡ JARVIS Status", show_menu, default=True),
        pystray.MenuItem("▶ Start JARVIS", start_jarvis),
        pystray.MenuItem("⏹ Stop JARVIS", stop_jarvis),
        pystray.MenuItem("🌐 Open HUD", open_hud),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⚙ Settings", open_settings),
        pystray.MenuItem("✕ Exit", exit_app),
    )


def main():
    global _config, _icon

    _config = load_config()

    _icon = pystray.Icon(
        name="jarvis-mkiii",
        icon=_make_icon(online=False),
        title="JARVIS-MKIII",
        menu=build_menu(),
    )

    if _config.get("auto_start"):
        threading.Thread(target=start_jarvis, daemon=True).start()

    _icon.run_detached()
    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
