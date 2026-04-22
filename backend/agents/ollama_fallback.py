"""
JARVIS-MKIV — ollama_fallback.py

Drop-in fallback for goal_reasoner.py when Groq is unavailable.
Uses DeepSeek-R1:7b via Ollama (already installed in MKIII).

Usage in goal_reasoner.py:
    from .ollama_fallback import call_ollama

    output = await call_groq(context, session)
    if output is None:
        log.warning("Groq unavailable — falling back to Ollama")
        output = await call_ollama(context, session)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp

log = logging.getLogger("goal_reasoner")

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "deepseek-r1:7b")

# Import shared types from goal_reasoner
# (when placed in same package, use relative import)
# from .goal_reasoner import Context, ReasonerOutput, ActionType, Decision,
#     CONFIDENCE_ACT_SILENT, CONFIDENCE_ACT_NOTIFY, CONFIDENCE_ESCALATE,
#     SYSTEM_PROMPT

# ── Standalone imports for when used as module ─────────────────────────────────
# These mirror goal_reasoner.py — keep in sync.

from enum import Enum

class Decision(str, Enum):
    ACT_SILENT  = "ACT_SILENT"
    ACT_NOTIFY  = "ACT_NOTIFY"
    ESCALATE    = "ESCALATE"
    DISCARD     = "DISCARD"

class ActionType(str, Enum):
    SEND_BRIEF    = "send_brief"
    LOG_DOMAIN    = "log_domain"
    SEND_WHATSAPP = "send_whatsapp"
    SURFACE_ALERT = "surface_alert"
    FETCH_INTEL   = "fetch_intel"
    SUGGEST_FOCUS = "suggest_focus"
    REST_ADVISORY = "rest_advisory"

CONFIDENCE_ACT_SILENT = 0.85
CONFIDENCE_ACT_NOTIFY = 0.60
CONFIDENCE_ESCALATE   = 0.40

@dataclass
class ReasonerOutput:
    reasoning:   str
    action_type: ActionType
    action_args: dict[str, Any]
    confidence:  float
    decision:    Decision = Decision.DISCARD
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())

# ── Ollama system prompt ───────────────────────────────────────────────────────
# Slightly shorter than Groq version — DeepSeek-R1:7b has smaller context.
# Core rules preserved. Confidence calibration preserved.

OLLAMA_SYSTEM = """
You are JARVIS-MKIV Goal Reasoner. Decide ONE action for Khalid (sir) or none.

DOMAINS: engineering(t:80), programming(t:85), combat(t:75), strategy(t:70), neuro(t:75)

EMOTION RULES:
fatigued → rest_advisory only
stressed → calm suggestions, no urgency
focused/elevated → any action permitted
neutral → default

CONFIDENCE:
0.85+ → ACT_SILENT, 0.60-0.84 → ACT_NOTIFY, 0.40-0.59 → ESCALATE, <0.40 → DISCARD

ACTIONS: send_brief, log_domain, send_whatsapp, surface_alert,
         fetch_intel, suggest_focus, rest_advisory

HARD RULES:
- send_whatsapp needs confidence >= 0.75
- last action < 30min needs confidence >= 0.90
- fatigued + hour 23-05 → always rest_advisory at 0.95

Respond ONLY with JSON, no markdown:
{"reasoning":"...","action_type":"...","action_args":{},"confidence":0.0}
""".strip()

# ── Ollama caller ──────────────────────────────────────────────────────────────

async def call_ollama(context: Any, session: aiohttp.ClientSession) -> "ReasonerOutput | None":
    """
    Call local Ollama DeepSeek-R1:7b as fallback when Groq is unavailable.
    Returns ReasonerOutput or None on failure.
    """

    user_msg = f"""
Hour: {context.hour_of_day}:00 | Emotion: {context.emotion_state}
Last action: {f"{context.last_action_minutes_ago}min ago" if context.last_action_minutes_ago else "unknown"}

PHANTOM SCORES: {json.dumps(context.phantom_scores)}
PRIORITY: {context.phantom_priority or "none"}
MEMORIES: {"; ".join(context.recent_memories[:3]) or "none"}
ALERTS: {len(context.system_alerts)} active

JSON only. One action or none.
""".strip()

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": f"{OLLAMA_SYSTEM}\n\nUSER:\n{user_msg}",
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.3,
            "num_predict": 256,
        },
    }

    try:
        async with session.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),  # local model is slower
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                log.error("Ollama fallback error %d: %s", resp.status, body[:200])
                return None

            data = await resp.json()
            raw_text = data.get("response", "")

            # DeepSeek-R1 sometimes wraps in <think> tags — strip them
            if "<think>" in raw_text:
                raw_text = raw_text.split("</think>")[-1].strip()

            parsed = json.loads(raw_text)
            confidence = float(parsed.get("confidence", 0.0))
            action_type_str = parsed.get("action_type", "surface_alert")

            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                log.warning("Ollama unknown action_type: %s", action_type_str)
                action_type = ActionType.SURFACE_ALERT

            if confidence >= CONFIDENCE_ACT_SILENT:
                decision = Decision.ACT_SILENT
            elif confidence >= CONFIDENCE_ACT_NOTIFY:
                decision = Decision.ACT_NOTIFY
            elif confidence >= CONFIDENCE_ESCALATE:
                decision = Decision.ESCALATE
            else:
                decision = Decision.DISCARD

            output = ReasonerOutput(
                reasoning=parsed.get("reasoning", ""),
                action_type=action_type,
                action_args=parsed.get("action_args", {}),
                confidence=confidence,
                decision=decision,
            )

            log.info(
                "[OLLAMA FALLBACK] decision=%s action=%s confidence=%.2f",
                decision.value, action_type.value, confidence,
            )
            return output

    except json.JSONDecodeError as e:
        log.error("Ollama JSON parse failed: %s", e)
        return None
    except Exception as e:
        log.error("Ollama fallback failed: %s", e)
        return None


# ── Availability check ─────────────────────────────────────────────────────────

async def ollama_available(session: aiohttp.ClientSession) -> bool:
    """Quick ping to check if Ollama is running."""
    try:
        async with session.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=aiohttp.ClientTimeout(total=3),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                available = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
                if not available:
                    log.warning(
                        "Ollama running but %s not found. Available: %s",
                        OLLAMA_MODEL, models,
                    )
                return available
    except Exception:
        pass
    return False
