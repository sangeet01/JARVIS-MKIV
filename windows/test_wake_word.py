"""
JARVIS-MKIII — windows/test_wake_word.py
Wake word calibration tool — prints live detection scores so you can tune
WAKE_CFG.sensitivity in backend/config/settings.py.

Usage:
    cd C:\Users\w100\JARVIS-MKIII
    venv\Scripts\python windows\test_wake_word.py

Say 'Hey JARVIS' repeatedly and note the peak scores.
Say background speech and note the false-positive scores.
Set sensitivity to a value between the two.
"""
import sys
import os
import logging

# Redirect to backend so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Enable DEBUG logging so every score is printed
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

import numpy as np
import sounddevice as sd

from voice.wake_word import WAKE_MODEL_PATH, SAMPLE_RATE, CHUNK_SAMPLES, MODEL_KEY, THRESHOLD


def main():
    print(f"[CAL] Wake word calibration mode")
    print(f"[CAL] Model : {WAKE_MODEL_PATH}")
    print(f"[CAL] Current threshold : {THRESHOLD}")
    print(f"[CAL] Say 'Hey JARVIS' to see peak scores. Ctrl+C to quit.\n")

    from openwakeword.model import Model
    model = Model(wakeword_models=[WAKE_MODEL_PATH])

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK_SAMPLES) as stream:
        while True:
            audio_chunk, _ = stream.read(CHUNK_SAMPLES)
            audio_f32 = audio_chunk[:, 0].astype(np.float32) / 32768.0
            preds = model.predict(audio_f32)
            score = preds.get(MODEL_KEY, 0.0)
            bar = "#" * int(score * 40)
            marker = " <<< DETECTED" if score >= THRESHOLD else ""
            print(f"\r  score={score:.4f}  [{bar:<40}]{marker}          ", end="", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[CAL] Done.")
