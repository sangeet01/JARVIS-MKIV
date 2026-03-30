"""
JARVIS-MKIII — wake_word.py
Always-on wake word detection using openWakeWord (hey_jarvis_v0.1.onnx).

Flow:
  Mic (16kHz) → openwakeword Model.predict() → on_detected() callback

Runs in a background thread, fully independent of the STT pipeline.
"""

from __future__ import annotations
import importlib.util
import os
import threading
import numpy as np
import sounddevice as sd

def _resolve_wake_model_path() -> str:
    """Resolve the openwakeword models directory cross-platform."""
    spec = importlib.util.find_spec("openwakeword")
    if spec is None:
        raise ImportError("openwakeword is not installed")
    models_dir = os.path.join(os.path.dirname(spec.origin), "resources", "models")
    return os.path.join(models_dir, "hey_jarvis_v0.1.onnx")

WAKE_MODEL_PATH = _resolve_wake_model_path()
SAMPLE_RATE   = 16000
CHUNK_SAMPLES = 1280          # 80 ms — required by openWakeWord
MODEL_KEY     = "hey_jarvis_v0.1"
THRESHOLD     = 0.5
COOLDOWN_SEC  = 2.0           # ignore further detections for this long after firing


class WakeWordDetector:
    def __init__(self, on_detected=None):
        self._on_detected = on_detected or (lambda: None)
        self._running     = False
        self._thread      = None
        self._model       = None
        self._last_fired  = 0.0

    def start(self) -> None:
        print("[WAKE] Loading hey_jarvis_v0.1 model...")
        try:
            from openwakeword.model import Model
            self._model = Model(wakeword_model_paths=[WAKE_MODEL_PATH])
            print("[WAKE] Model loaded. Listening for 'Hey JARVIS'...")
        except Exception as e:
            print(f"[WAKE] Failed to load model: {e}")
            return

        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="wake-word")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[WAKE] Stopped.")

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
                        print(f"[WAKE] Predict error: {e}")
                        continue

                    score = preds.get(MODEL_KEY, 0.0)
                    if score >= THRESHOLD:
                        import time
                        now = time.monotonic()
                        if now - self._last_fired >= COOLDOWN_SEC:
                            self._last_fired = now
                            print(f"[WAKE] 'Hey JARVIS' detected (score={score:.3f})")
                            try:
                                self._on_detected()
                            except Exception as e:
                                print(f"[WAKE] Callback error: {e}")
        except Exception as e:
            print(f"[WAKE] Microphone error: {e}")
