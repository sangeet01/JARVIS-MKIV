"""
JARVIS-MKIV — goal_reasoner.py

The autonomous Goal Reasoner. This is the nervous system that
connects all MKIII organs into a proactive, self-directing agent.

Architecture:
  - Runs as a persistent async loop (replaces dumb timer in proactive_agent.py)
  - Every cycle: pulls context from all sources → reasons → decides → acts or escalates
  - Three-tier confidence system: ACT / NOTIFY / ESCALATE
  - Full audit trail: every decision logged to ChromaDB memory

State machine per cycle:
  IDLE → SENSING → REASONING → DECIDING → ACTING → LOGGING → IDLE

Confidence thresholds:
  >= 0.85  → ACT silently, log it
  >= 0.60  → ACT, push HUD notification after
  >= 0.40  → ESCALATE to user via WhatsApp/HUD
  <  0.40  → DISCARD, log reasoning for inspection

Cycle interval: 10 minutes default (configurable via REASONER_INTERVAL env)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiohttp

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[REASONER] %(asctime)s %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("goal_reasoner")

# ── Config ─────────────────────────────────────────────────────────────────────

BACKEND_URL       = os.getenv("BACKEND_URL", "http://localhost:8000")
REASONER_INTERVAL = int(os.getenv("REASONER_INTERVAL", 600))   # seconds
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_URL          = "https://api.groq.com/openai/v1/chat/completions"

CONFIDENCE_ACT_SILENT   = 0.85
CONFIDENCE_ACT_NOTIFY   = 0.60
CONFIDENCE_ESCALATE     = 0.40

AUDIT_DIR = Path(__file__).parent.parent.parent / "data" / "reasoner_audit"

# ── Enums ──────────────────────────────────────────────────────────────────────

class Decision(str, Enum):
    ACT_SILENT  = "ACT_SILENT"   # act, log only
    ACT_NOTIFY  = "ACT_NOTIFY"   # act, push HUD notification
    ESCALATE    = "ESCALATE"     # surface to user for decision
    DISCARD     = "DISCARD"      # confidence too low, skip

class ActionType(str, Enum):
    SEND_BRIEF      = "send_brief"        # push a briefing to HUD
    LOG_DOMAIN      = "log_domain"        # log phantom domain activity
    SEND_WHATSAPP   = "send_whatsapp"     # send WhatsApp message
    SURFACE_ALERT   = "surface_alert"     # push HUD alert
    FETCH_INTEL     = "fetch_intel"       # pull fresh intel (news, weather)
    SUGGEST_FOCUS   = "suggest_focus"     # recommend focus area to user
    REST_ADVISORY   = "rest_advisory"     # tell user to rest (fatigued state)

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Context:
    """Full situational snapshot assembled each cycle."""
    timestamp: str                          = field(default_factory=lambda: datetime.now().isoformat())
    phantom_scores: dict[str, float]        = field(default_factory=dict)
    phantom_priority: str                   = ""
    emotion_state: str                      = "neutral"
    recent_memories: list[str]              = field(default_factory=list)
    upcoming_calendar: list[dict]           = field(default_factory=list)
    system_alerts: list[dict]              = field(default_factory=list)
    hour_of_day: int                        = field(default_factory=lambda: datetime.now().hour)
    last_action_minutes_ago: Optional[int]  = None

@dataclass
class ReasonerOutput:
    """What the LLM decided to do."""
    reasoning:   str
    action_type: ActionType
    action_args: dict[str, Any]
    confidence:  float          # 0.0 – 1.0
    decision:    Decision       = Decision.DISCARD
    timestamp:   str            = field(default_factory=lambda: datetime.now().isoformat())

# ── Context assembler ──────────────────────────────────────────────────────────

async def assemble_context(session: aiohttp.ClientSession) -> Context:
    """Pull live data from all MKIII endpoints."""
    ctx = Context()

    async def safe_get(url: str, fallback: Any = None) -> Any:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.debug("safe_get %s failed: %s", url, e)
        return fallback

    # Phantom OS domain scores
    scores_raw = await safe_get(f"{BACKEND_URL}/phantom/scores", {})
    if isinstance(scores_raw, dict):
        ctx.phantom_scores = scores_raw.get("scores", scores_raw)

    # Phantom priority recommendation
    priority_raw = await safe_get(f"{BACKEND_URL}/phantom/priority", {})
    if isinstance(priority_raw, dict):
        ctx.phantom_priority = priority_raw.get("recommendation", "")

    # Emotion state
    emotion_raw = await safe_get(f"{BACKEND_URL}/emotion/state", {})
    if isinstance(emotion_raw, dict):
        ctx.emotion_state = emotion_raw.get("state", "neutral")

    # Recent memories (last 5 relevant)
    mem_raw = await safe_get(f"{BACKEND_URL}/memory/search?q=recent+activity&n=5", {})
    if isinstance(mem_raw, dict):
        ctx.recent_memories = [m.get("content", "") for m in mem_raw.get("results", [])]

    # System alerts (last 10)
    alerts_raw = await safe_get(f"{BACKEND_URL}/internal/alerts", [])
    if isinstance(alerts_raw, list):
        ctx.system_alerts = alerts_raw[:10]

    log.info(
        "Context assembled — emotion=%s phantom_priority=%s scores=%s",
        ctx.emotion_state,
        ctx.phantom_priority[:60] if ctx.phantom_priority else "none",
        ctx.phantom_scores,
    )
    return ctx

# ── Reasoner prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are JARVIS-MKIV's autonomous Goal Reasoner — the brain that decides 
what action, if any, to take right now on behalf of Khalid (sir).

You receive a full situational snapshot every 10 minutes. Your job:
1. Analyze the context deeply
2. Decide on ONE highest-leverage action (or none)
3. Assign a confidence score between 0.0 and 1.0

PHANTOM ZERO domains you track:
- engineering: robotics, builds, hardware (target 80)
- programming: DSA, code sessions, teaching (target 85)  
- combat: workouts, sparring, streaks (target 75)
- strategy: chess, decisions, mission % (target 70)
- neuro: sleep, reading, language study (target 75)

EMOTION → BEHAVIOR rules:
- fatigued → prioritize rest_advisory, suppress non-critical actions
- stressed → calm suggestions only, no urgency
- focused → can trigger any action, user is in flow
- elevated → match energy, suggest high-leverage work
- neutral → default reasoning

CONFIDENCE CALIBRATION:
- 0.85+ → you are certain this is the right action right now
- 0.60–0.84 → good signal but notify user after
- 0.40–0.59 → uncertain, escalate to user for decision
- below 0.40 → do nothing, discard

AVAILABLE ACTIONS:
- send_brief: push a contextual briefing to HUD
- log_domain: log a phantom domain activity (args: domain, activity_type, value, notes)
- send_whatsapp: send WhatsApp message to Khalid (args: message)
- surface_alert: push HUD alert (args: message, severity)
- fetch_intel: trigger fresh intel pull (args: categories list)
- suggest_focus: recommend a focus area via HUD (args: domain, reason, suggested_action)
- rest_advisory: tell user to take a break (args: reason)

RULES:
- Never act on irreversible external things (send WhatsApp) below 0.75 confidence
- Never log phantom domain activity you haven't witnessed evidence for
- If the last action was < 30 minutes ago, require 0.90+ confidence to act again
- If emotion is fatigued and hour is 23-05, always suggest rest, confidence 0.95

Respond ONLY with a valid JSON object, no markdown, no preamble:
{
  "reasoning": "step by step reasoning in 2-3 sentences",
  "action_type": "one of the AVAILABLE ACTIONS above",
  "action_args": { ... },
  "confidence": 0.0
}
""".strip()

# ── LLM call ───────────────────────────────────────────────────────────────────

async def call_groq(context: Context, session: aiohttp.ClientSession) -> ReasonerOutput | None:
    """Send context to Groq, parse structured decision."""

    user_msg = f"""
CURRENT CONTEXT:
Timestamp      : {context.timestamp}
Hour of day    : {context.hour_of_day}:00
Emotion state  : {context.emotion_state}
Last action    : {f"{context.last_action_minutes_ago}min ago" if context.last_action_minutes_ago else "unknown"}

PHANTOM ZERO SCORES (today):
{json.dumps(context.phantom_scores, indent=2)}

PRIORITY RECOMMENDATION:
{context.phantom_priority or "none"}

RECENT MEMORIES (last 5):
{chr(10).join(f"- {m}" for m in context.recent_memories) or "none"}

SYSTEM ALERTS (last 10):
{json.dumps(context.system_alerts[:3], indent=2) if context.system_alerts else "none"}

Decide now. One action or none. JSON only.
""".strip()

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with session.post(
            GROQ_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                log.error("Groq error %d: %s", resp.status, body[:200])
                return None

            data = await resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_text)

            confidence = float(parsed.get("confidence", 0.0))
            action_type_str = parsed.get("action_type", "surface_alert")

            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                log.warning("Unknown action_type from LLM: %s", action_type_str)
                action_type = ActionType.SURFACE_ALERT

            # Assign decision tier
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
                "Reasoner decision: %s | action=%s | confidence=%.2f",
                decision.value,
                action_type.value,
                confidence,
            )
            return output

    except json.JSONDecodeError as e:
        log.error("Failed to parse LLM JSON: %s", e)
        return None
    except Exception as e:
        log.error("Groq call failed: %s", e)
        return None

# ── Action executor ────────────────────────────────────────────────────────────

async def execute_action(output: ReasonerOutput, session: aiohttp.ClientSession) -> bool:
    """Execute the decided action against MKIII endpoints."""

    if output.decision == Decision.DISCARD:
        log.info("Action discarded (low confidence %.2f)", output.confidence)
        return True

    args = output.action_args

    try:
        if output.action_type == ActionType.SEND_BRIEF:
            async with session.post(
                f"{BACKEND_URL}/briefing",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                ok = r.status in (200, 201)
                log.info("send_brief → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.LOG_DOMAIN:
            payload = {
                "domain":        args.get("domain", "general"),
                "activity_type": args.get("activity_type", "auto_detected"),
                "value":         args.get("value", 1),
                "notes":         args.get("notes", f"Auto-logged by Goal Reasoner at {datetime.now().strftime('%H:%M')}"),
            }
            async with session.post(
                f"{BACKEND_URL}/phantom/log",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                ok = r.status in (200, 201)
                log.info("log_domain %s → %s", payload["domain"], "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.SURFACE_ALERT:
            # Only push if confidence warrants a notification
            if output.confidence >= CONFIDENCE_ACT_NOTIFY:
                payload = {
                    "message":  args.get("message", output.reasoning[:200]),
                    "severity": args.get("severity", "info"),
                    "source":   "goal_reasoner",
                }
                async with session.post(
                    f"{BACKEND_URL}/internal/alert",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    ok = r.status in (200, 201)
                    log.info("surface_alert → %s", "OK" if ok else f"FAIL {r.status}")
                    return ok
            return True

        elif output.action_type == ActionType.SUGGEST_FOCUS:
            payload = {
                "message": (
                    f"[JARVIS] Focus suggestion: {args.get('domain', '')} — "
                    f"{args.get('suggested_action', '')} ({args.get('reason', '')})"
                ),
                "severity": "info",
                "source": "goal_reasoner",
            }
            async with session.post(
                f"{BACKEND_URL}/internal/alert",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                ok = r.status in (200, 201)
                log.info("suggest_focus → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.REST_ADVISORY:
            payload = {
                "message": f"[JARVIS] Rest advisory: {args.get('reason', 'You appear fatigued. Consider resting, sir.')}",
                "severity": "warning",
                "source": "goal_reasoner",
            }
            async with session.post(
                f"{BACKEND_URL}/internal/alert",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                ok = r.status in (200, 201)
                log.info("rest_advisory → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.ESCALATE:
            # Escalation: surface to HUD for human decision
            payload = {
                "message": (
                    f"[JARVIS] Decision needed (confidence {output.confidence:.0%}): "
                    f"{output.reasoning[:300]}"
                ),
                "severity": "warning",
                "source": "goal_reasoner_escalation",
            }
            async with session.post(
                f"{BACKEND_URL}/internal/alert",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                ok = r.status in (200, 201)
                log.info("escalation surfaced → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.SEND_WHATSAPP:
            # WhatsApp: only if confidence >= 0.75 (checked by caller)
            async with session.post(
                f"{BACKEND_URL}/whatsapp/send",
                json={"message": args.get("message", "")},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                ok = r.status in (200, 201)
                log.info("send_whatsapp → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

        elif output.action_type == ActionType.FETCH_INTEL:
            async with session.post(
                f"{BACKEND_URL}/intel/refresh",
                json={"categories": args.get("categories", ["tech", "world"])},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                ok = r.status in (200, 201)
                log.info("fetch_intel → %s", "OK" if ok else f"FAIL {r.status}")
                return ok

    except Exception as e:
        log.error("Action execution failed: %s", e)
        return False

    return True

# ── Audit logger ───────────────────────────────────────────────────────────────

def audit_cycle(context: Context, output: ReasonerOutput | None, executed: bool) -> None:
    """Write every cycle to audit log. Full transparency."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = AUDIT_DIR / f"cycle_{ts}.json"

    record = {
        "timestamp":    datetime.now().isoformat(),
        "context":      asdict(context) if hasattr(context, "__dataclass_fields__") else vars(context),
        "output":       asdict(output) if output else None,
        "executed":     executed,
    }

    try:
        audit_file.write_text(json.dumps(record, indent=2, default=str))
    except Exception as e:
        log.warning("Audit write failed: %s", e)

# ── Last action tracker ────────────────────────────────────────────────────────

_last_action_time: datetime | None = None

def minutes_since_last_action() -> int | None:
    if _last_action_time is None:
        return None
    return int((datetime.now() - _last_action_time).total_seconds() / 60)

def record_action_taken() -> None:
    global _last_action_time
    _last_action_time = datetime.now()

# ── Guard rails ────────────────────────────────────────────────────────────────

def apply_guardrails(output: ReasonerOutput, context: Context) -> ReasonerOutput:
    """Hard rules that override LLM confidence."""

    mins = minutes_since_last_action()

    # Rule 1: Too soon since last action — require higher confidence
    if mins is not None and mins < 30 and output.confidence < 0.90:
        log.info(
            "Guardrail: last action %dmin ago, confidence %.2f < 0.90 → DISCARD",
            mins, output.confidence,
        )
        output.decision = Decision.DISCARD
        return output

    # Rule 2: WhatsApp requires >= 0.75 confidence always
    if output.action_type == ActionType.SEND_WHATSAPP and output.confidence < 0.75:
        log.info("Guardrail: WhatsApp confidence %.2f < 0.75 → ESCALATE", output.confidence)
        output.decision = Decision.ESCALATE
        return output

    # Rule 3: Fatigued + late night → force rest advisory if not already
    hour = context.hour_of_day
    if context.emotion_state == "fatigued" and (hour >= 23 or hour <= 5):
        if output.action_type not in (ActionType.REST_ADVISORY, ActionType.SURFACE_ALERT):
            log.info("Guardrail: fatigued + late night → override to rest_advisory")
            output.action_type = ActionType.REST_ADVISORY
            output.action_args = {"reason": "Fatigue detected at late hour. Rest is the highest-leverage action."}
            output.confidence  = 0.95
            output.decision    = Decision.ACT_NOTIFY

    return output

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    log.info("JARVIS-MKIV Goal Reasoner starting — interval=%ds", REASONER_INTERVAL)
    log.info("Confidence thresholds: ACT_SILENT=%.2f ACT_NOTIFY=%.2f ESCALATE=%.2f",
             CONFIDENCE_ACT_SILENT, CONFIDENCE_ACT_NOTIFY, CONFIDENCE_ESCALATE)

    if not GROQ_API_KEY:
        log.critical("GROQ_API_KEY not set. Cannot reason. Exiting.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        cycle = 0
        while True:
            cycle += 1
            log.info("── CYCLE %d ──", cycle)

            try:
                # 1. SENSE
                context = await assemble_context(session)
                context.last_action_minutes_ago = minutes_since_last_action()

                # 2. REASON
                output = await call_groq(context, session)

                executed = False
                if output:
                    # 3. GUARDRAILS
                    output = apply_guardrails(output, context)

                    # 4. DECIDE + ACT
                    if output.decision != Decision.DISCARD:
                        executed = await execute_action(output, session)
                        if executed and output.decision in (Decision.ACT_SILENT, Decision.ACT_NOTIFY):
                            record_action_taken()
                    else:
                        log.info("Cycle %d: no action taken (DISCARD)", cycle)

                # 5. AUDIT
                audit_cycle(context, output, executed)

            except Exception as e:
                log.error("Unhandled error in cycle %d: %s", cycle, e)

            log.info("Cycle %d complete. Sleeping %ds.", cycle, REASONER_INTERVAL)
            await asyncio.sleep(REASONER_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
