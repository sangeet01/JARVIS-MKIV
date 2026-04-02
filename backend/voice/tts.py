from __future__ import annotations
import threading, queue, subprocess, re, os, platform, tempfile
import numpy as np
import sounddevice as sd
import logging


logger = logging.getLogger(__name__)
try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

SAMPLE_RATE   = 24000
PLAYBACK_RATE = 48000
VOICE         = "bm_daniel"
SPEED         = 1.2
OUTPUT_DEVICE = None
_TEMP_DIR     = tempfile.gettempdir()


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate:
        return audio
    n_out = int(len(audio) * dst_rate / src_rate)
    x_old = np.linspace(0, 1, len(audio))
    x_new = np.linspace(0, 1, n_out)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    result, buf = [], ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        buf = (buf + " " + part).strip() if buf else part
        if len(buf) > 20:
            result.append(buf)
            buf = ""
    if buf:
        result.append(buf)
    return result if result else [text]


def _set_mic_mute(mute: bool) -> None:
    """Mute or unmute the default microphone — cross-platform."""
    if platform.system() == "Linux":
        action = "1" if mute else "0"
        subprocess.run(
            ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", action],
            capture_output=True,
        )
    elif platform.system() == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            mic = AudioUtilities.GetMicrophone()
            if mic:
                interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                volume.SetMute(1 if mute else 0, None)
        except Exception as e:
            logger.error(f"[TTS] Windows mic mute failed: {e}")
    # macOS and others: skip silently


class TTSEngine:
    def __init__(self, on_start=None, on_stop=None):
        self.on_start  = on_start or (lambda: None)
        self.on_stop   = on_stop  or (lambda: None)
        self._queue    = queue.Queue()
        self._running  = False
        self._pipeline = None
        self._ready    = threading.Event()

    def start(self):
        self._running = True
        if KOKORO_AVAILABLE:
            logger.info("[TTS] Loading Kokoro-82M (British, CPU)...")
            self._pipeline = KPipeline(lang_code="b", device="cpu")
            logger.info("[TTS] Kokoro ready on CPU.")
            logger.info("[TTS] Running warm-up inference...")
            try:
                _ = list(self._pipeline("hello", voice=VOICE, speed=SPEED))
                logger.info("[TTS] Warm-up complete.")
            except Exception as e:
                logger.error(f"[TTS] Warm-up failed (non-fatal): {e}")
        else:
            logger.warning("[TTS] WARNING: Kokoro not available.")

        self._ready.set()
        threading.Thread(target=self._worker, daemon=True).start()

    def stop(self):
        self._running = False
        self._queue.put(None)

    def wait_until_ready(self, timeout: float = 60.0) -> bool:
        return self._ready.wait(timeout=timeout)

    def speak(self, text: str):
        try:
            from core.text_sanitizer import sanitize_for_tts
            text = sanitize_for_tts(text)
        except Exception:
            text = text.strip()
        if text:
            self._queue.put(text)

    def interrupt(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self):
        while self._running:
            text = self._queue.get()
            if text is None:
                break
            self._stream_speak(text)

    def _speak_arabic(self, text: str) -> None:
        try:
            import time
            import pygame
            from gtts import gTTS
            _ar_mp3 = os.path.join(_TEMP_DIR, "jarvis_ar.mp3")
            tts = gTTS(text=text, lang="ar", tld="com")
            tts.save(_ar_mp3)
            pygame.mixer.init()
            pygame.mixer.music.load(_ar_mp3)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        except Exception as e:
            logger.error(f"[TTS] Arabic gTTS failed: {e}")

    def _stream_speak(self, text: str):
        self.on_start()
        try:
            from integrations.touchdesigner_bridge import on_speaking_start
            on_speaking_start(text)
        except Exception:
            pass
        _set_mic_mute(True)
        try:
            from core.language_detector import detect_language
            if detect_language(text) == "ar":
                self._speak_arabic(text)
            else:
                sentences = _split_sentences(text)
                # Pre-synthesize all sentences before playing any
                audio_chunks = []
                for sentence in sentences:
                    if not KOKORO_AVAILABLE or not self._pipeline:
                        continue
                    try:
                        chunks = [a for _, _, a in self._pipeline(sentence, voice=VOICE, speed=SPEED) if a is not None]
                        if chunks:
                            audio = _resample(np.concatenate(chunks), SAMPLE_RATE, PLAYBACK_RATE)
                            audio_chunks.append(audio)
                    except Exception as e:
                        logger.error(f"[TTS] Synthesis error: {e}")
                # Play all chunks sequentially with no gap
                for audio in audio_chunks:
                    sd.play(audio, samplerate=PLAYBACK_RATE, device=OUTPUT_DEVICE)
                    sd.wait()
        except Exception as e:
            logger.error(f"[TTS] Speak error: {e}")
        finally:
            _set_mic_mute(False)
            self.on_stop()
            try:
                from integrations.touchdesigner_bridge import on_speaking_stop
                on_speaking_stop()
            except Exception:
                pass
