"""
JARVIS-MKIII — wake_word.py
Always-on wake word detection using openWakeWord (hey_jarvis_v0.1.onnx).

Flow:
  Mic (16kHz) → openwakeword Model.predict() → on_detected() callback

Runs in a background thread, fully independent of the STT pipeline.
"""

from __future__ import annotations
import importlib.util
import logging
import os
import sys
import threading
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

def _resolve_wake_model_path() -> str:
    """Resolve hey_jarvis_v0.1.onnx cross-platform — checks package dir then walks venv."""
    try:
        spec = importlib.util.find_spec("openwakeword")
        if spec and spec.origin:
            pkg_dir = os.path.dirname(spec.origin)
            model_path = os.path.join(pkg_dir, "resources", "models", "hey_jarvis_v0.1.onnx")
            if os.path.exists(model_path):
                return model_path
    except Exception:
        pass
    # Fallback: search venv
    for root, dirs, files in os.walk(sys.prefix):
        for f in files:
            if f == "hey_jarvis_v0.1.onnx":
                return os.path.join(root, f)
    raise FileNotFoundError("hey_jarvis_v0.1.onnx not found in venv")

WAKE_MODEL_PATH = _resolve_wake_model_path()
SAMPLE_RATE   = 16000
CHUNK_SAMPLES = 1280          # 80 ms — required by openWakeWord
MODEL_KEY     = "hey_jarvis_v0.1"

try:
    from config.settings import WAKE_CFG as _WAKE_CFG
    THRESHOLD    = _WAKE_CFG.sensitivity
    COOLDOWN_SEC = _WAKE_CFG.cooldown_ms / 1000.0
except Exception:
    THRESHOLD    = 0.5
    COOLDOWN_SEC = 1.5


class WakeWordDetector:
    def __init__(self, on_detected=None):
        self._on_detected = on_detected or (lambda: None)
        self._running     = False
        self._thread      = None
        self._model       = None
        self._last_fired  = 0.0

    def start(self) -> None:
        logger.info("[WAKE] Loading hey_jarvis_v0.1 model...")
        try:
            from openwakeword.model import Model
            self._model = Model(wakeword_models=[WAKE_MODEL_PATH])
            logger.info(f"[WAKE] Model loaded (threshold={THRESHOLD}, cooldown={COOLDOWN_SEC}s). Listening for 'Hey JARVIS'...")
        except Exception as e:
            logger.error(f"[WAKE] Failed to load model: {e}")
            return

        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="wake-word")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("[WAKE] Stopped.")

    def _loop(self) -> None:
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SAMPLES,
            ) as stream:
                while self._running:
                    audio_chunk, _ = stream.read(CHUNK_SAMPLES)
                    # openwakeword expects float32 in [-1, 1]
                    audio_f32 = audio_chunk[:, 0].astype(np.float32) / 32768.0
                    try:
                        preds = self._model.predict(audio_f32)
                    except Exception as e:
                        logger.error(f"[WAKE] Predict error: {e}")
                        continue

                    score = preds.get(MODEL_KEY, 0.0)
                    import time
                    now = time.monotonic()
                    fired = score >= THRESHOLD and now - self._last_fired >= COOLDOWN_SEC
                    logger.debug(f"[WAKE] score={score:.3f} threshold={THRESHOLD} fired={fired}")
                    if fired:
                        self._last_fired = now
                        logger.info(f"[WAKE] 'Hey JARVIS' detected (score={score:.3f})")
                        try:
                            self._on_detected()
                        except Exception as e:
                            logger.error(f"[WAKE] Callback error: {e}")
        except Exception as e:
            logger.error(f"[WAKE] Microphone error: {e}")
