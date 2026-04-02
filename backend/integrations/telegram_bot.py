"""
JARVIS-MKIII — telegram_bot.py
Telegram gateway: routes messages through the JARVIS /chat API.
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.vault import Vault

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("jarvis.telegram")

JARVIS_BASE = "http://localhost:8000"
JARVIS_TOKEN = os.environ.get("MOBILE_ACCESS_TOKEN", "phantom-zero-2026")
_AUTH_HEADERS = {"X-JARVIS-Token": JARVIS_TOKEN}

# Set AUTHORIZED_USER_ID = 0 to allow first-contact logging, then update.
# Override via env var TELEGRAM_AUTHORIZED_USER_ID for convenience.
AUTHORIZED_USER_ID: int = int(os.environ.get("TELEGRAM_AUTHORIZED_USER_ID", "0"))


def _is_authorized(user_id: int) -> bool:
    if AUTHORIZED_USER_ID == 0:
        log.warning("⚠  AUTHORIZED_USER_ID not set — first contact: user_id=%d", user_id)
        log.warning(">>> TELEGRAM FIRST CONTACT: user_id=%d <<<  "
                    "Set TELEGRAM_AUTHORIZED_USER_ID=%d in env.", user_id, user_id)
        return False
    return user_id == AUTHORIZED_USER_ID


def _session(user_id: int) -> str:
    return f"telegram-{user_id}"


async def _jarvis_chat(prompt: str, session_id: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{JARVIS_BASE}/chat",
            json={"prompt": prompt, "session_id": session_id},
            headers=_AUTH_HEADERS,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("response") or data.get("text") or str(data)


async def _jarvis_status() -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{JARVIS_BASE}/status")
        r.raise_for_status()
        data = r.json()
    lines = []
    for k, v in data.items():
        lines.append(f"• {k}: {v}")
    return "\n".join(lines) if lines else str(data)


# ─── Command handlers ────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text("JARVIS MKIII online, sir. How may I assist?")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        summary = await _jarvis_status()
        await update.message.reply_text(f"JARVIS Status:\n{summary}")
    except Exception as e:
        await update.message.reply_text(f"Status unavailable: {e}")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return
    session_id = _session(user_id)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{JARVIS_BASE}/chat",
                json={"prompt": "__clear__", "session_id": session_id},
                headers=_AUTH_HEADERS,
            )
        await update.message.reply_text("Session memory cleared.")
    except Exception as e:
        # Even if the endpoint doesn't support it, acknowledge
        await update.message.reply_text(f"Clear attempted (backend: {e})")


# ─── Message handlers ─────────────────────────────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return
    prompt = update.message.text
    session_id = _session(user_id)
    log.info("Text from %d: %r", user_id, prompt[:80])
    try:
        reply = await _jarvis_chat(prompt, session_id)
        await update.message.reply_text(reply)
    except Exception as e:
        log.error("Chat error: %s", e)
        await update.message.reply_text(f"Error reaching JARVIS: {e}")


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    log.info("Voice message from %d, duration=%s", user_id, getattr(voice, "duration", "?"))

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        await update.message.reply_text(
            "faster-whisper not installed; cannot transcribe voice."
        )
        return

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tg_file = await voice.get_file()
        await tg_file.download_to_drive(tmp_path)

        # Load small model (cached after first run)
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        transcript = " ".join(s.text for s in segments).strip()

        if not transcript:
            await update.message.reply_text("(Could not transcribe voice message)")
            return

        log.info("Transcribed: %r", transcript)
        await update.message.reply_text(f'_"{transcript}"_', parse_mode="Markdown")

        session_id = _session(user_id)
        reply = await _jarvis_chat(transcript, session_id)
        await update.message.reply_text(reply)

    except Exception as e:
        log.error("Voice handling error: %s", e)
        await update.message.reply_text(f"Voice processing failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    token = Vault().get("TELEGRAM_TOKEN")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    log.info("JARVIS Telegram bot starting (polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
