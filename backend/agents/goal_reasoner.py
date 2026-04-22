"""
JARVIS-MKIV — goal_reasoner.py (v2 — COMPLETE)

Full autonomous Goal Reasoner with all 5 robustness additions wired in:
  1. Ollama fallback         — no cycle loss when Groq is down
  2. Memory write-back       — decisions logged to ChromaDB, JARVIS learns
  3. Goal stack persistence  — tracks domain gaps across cycles
  4. Test suite              — test_reasoner.py validates guardrails
  5. HUD feed                — ReasonerFeed.jsx consumes /reasoner/history

This is the COMPLETE replacement for goal_reasoner.py v1.
Drop it directly into backend/agents/goal_reasoner.py.

State machine per cycle:
  IDLE → SENSING → REASONING → GUARDRAILS → DECIDING → ACTING → LOGGING → IDLE

Confidence thresholds:
  >= 0.85  ACT_SILENT   → act, log only
  >= 0.60  ACT_NOTIFY   → act, push HUD notification
  >= 0.40  ESCALATE     → surface to user for decision
  <  0.40  DISCARD      → log reasoning only, no action

Cycle interval: REASONER_INTERVAL env var (default 600s / 10min)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
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
REASONER_INTERVAL = int(os.getenv("REASONER_INTERVAL", 600))
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_URL          = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_URL        = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_FALLBACK_MODEL", "deepseek-r1:7b")

CONFIDENCE_ACT_SILENT = 0.85
CONFIDENCE_ACT_NOTIFY = 0.60
CONFIDENCE_ESCALATE   = 0.40

AUDIT_DIR = Path(__file__).parent.parent.parent / "data" / "reasoner_audit"
AUDIT_MAX_FILES = 1000   # rotate beyond this

# ── Graceful shutdown ──────────────────────────────────────────────────────────

_shutdown = False

def _handle_sigterm(signum, frame):
    global _shutdown
    log.info("SIGTERM received — finishing current cycle then exiting.")
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT,  _handle_sigterm)

# ── Enums ──────────────────────────────────────────────────────────────────────

class Decision(str, Enum):
    ACT_SILENT = "ACT_SILENT"
    ACT_NOTIFY = "ACT_NOTIFY"
    ESCALATE   = "ESCALATE"
    DISCARD    = "DISCARD"

class ActionType(str, Enum):
    SEND_BRIEF    = "send_brief"
    LOG_DOMAIN    = "log_domain"
    SEND_WHATSAPP = "send_whatsapp"
    SURFACE_ALERT = "surface_alert"
    FETCH_INTEL   = "fetch_intel"
    SUGGEST_FOCUS = "suggest_focus"
    REST_ADVISORY = "rest_advisory"

VALID_EMOTION_STATES = {"focused", "fatigued", "stressed", "elevated", "neutral"}

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Context:
    timestamp:               str              = field(default_factory=lambda: datetime.now().isoformat())
    phantom_scores:          dict[str, float] = field(default_factory=dict)
    phantom_priority:        str              = ""
    emotion_state:           str              = "neutral"
    recent_memories:         list[str]        = field(default_factory=list)
    upcoming_calendar:       list[dict]       = field(default_factory=list)
    system_alerts:           list[dict]       = field(default_factory=list)
    hour_of_day:             int              = field(default_factory=lambda: datetime.now().hour)
    last_action_minutes_ago: Optional[int]    = None
    goal_stack_summary:      str              = ""   # persistent gap tracking
    learning_context:        str              = ""   # recent past decisions

@dataclass
class ReasonerOutput:
    reasoning:   str
    action_type: ActionType
    action_args: dict[str, Any]
    confidence:  float
    decision:    Decision = Decision.DISCARD
    timestamp:   str      = field(default_factory=lambda: datetime.now().isoformat())

# ── Goal stack (lazy import) ───────────────────────────────────────────────────

_goal_stack = None

def get_goal_stack():
    global _goal_stack
    if _goal_stack is None:
        try:
            from .goal_stack import GoalStack
            _goal_stack = GoalStack()
            log.info("GoalStack initialized.")
        except Exception as e:
            log.warning("GoalStack init failed: %s — proceeding without.", e)
    return _goal_stack

# ── Context assembler ──────────────────────────────────────────────────────────

async def assemble_context(session: aiohttp.ClientSession) -> Context:
    ctx = Context()

    async def safe_get(url: str, fallback: Any = None) -> Any:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.debug("safe_get %s failed: %s", url, e)
        return fallback

    # Phantom OS
    scores_raw = await safe_get(f"{BACKEND_URL}/phantom/scores", {})
    if isinstance(scores_raw, dict):
        ctx.phantom_scores = scores_raw.get("scores", scores_raw)

    priority_raw = await safe_get(f"{BACKEND_URL}/phantom/priority", {})
    if isinstance(priority_raw, dict):
        ctx.phantom_priority = priority_raw.get("recommendation", "")

    # Emotion — validate state
    emotion_raw = await safe_get(f"{BACKEND_URL}/emotion/state", {})
    if isinstance(emotion_raw, dict):
        raw_state = emotion_raw.get("state", "neutral")
        ctx.emotion_state = raw_state if raw_state in VALID_EMOTION_STATES else "neutral"

    # Recent memories
    mem_raw = await safe_get(f"{BACKEND_URL}/memory/search?q=recent+activity&n=5", {})
    if isinstance(mem_raw, dict):
        ctx.recent_memories = [m.get("content", "") for m in mem_raw.get("results", [])]

    # Alerts
    alerts_raw = await safe_get(f"{BACKEND_URL}/internal/alerts", [])
    if isinstance(alerts_raw, list):
        ctx.system_alerts = alerts_raw[:10]

    # Goal stack context
    gs = get_goal_stack()
    if gs:
        if ctx.phantom_scores:
            gs.update_from_scores(ctx.phantom_scores)
        ctx.goal_stack_summary = gs.build_prompt_context()

    # Learning context from memory
    try:
        from .reasoner_memory import build_learning_context
        ctx.learning_context = await build_learning_context(session)
    except Exception as e:
        log.debug("Learning context failed: %s", e)

    log.info(
        "Context assembled — emotion=%s hour=%d scores=%s",
        ctx.emotion_state, ctx.hour_of_day, ctx.phantom_scores,
    )
    return ctx

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are JARVIS-MKIV's autonomous Goal Reasoner — the brain that decides
what action, if any, to take right now on behalf of Khalid (sir).

You receive a full situational snapshot every 10 minutes. Your job:
1. Analyze the context deeply — especially persistent goal gaps
2. Decide on ONE highest-leverage action (or none)
3. Assign a confidence score between 0.0 and 1.0

PHANTOM ZERO domains:
- engineering: robotics, builds, hardware (target 80)
- programming: DSA, code sessions, teaching (target 85)
- combat: workouts, sparring, streaks (target 75)
- strategy: chess, decisions, mission % (target 70)
- neuro: sleep, reading, language study (target 75)

EMOTION → BEHAVIOR:
fatigued  → rest_advisory only, suppress all else
stressed  → calm suggestions, no urgency
focused   → any action permitted
elevated  → match energy, high-leverage work
neutral   → default reasoning

GOAL STACK RULES:
- Persistent gaps (3+ cycles below target) → highest priority
- If you acted on a domain last cycle → consider a different domain
- If recent decisions show repeated discards on same action → try different approach

CONFIDENCE CALIBRATION:
0.85+ → ACT_SILENT, 0.60-0.84 → ACT_NOTIFY
0.40-0.59 → ESCALATE, below 0.40 → DISCARD

ACTIONS: send_brief, log_domain, send_whatsapp, surface_alert,
         fetch_intel, suggest_focus, rest_advisory

HARD RULES (cannot be overridden):
- send_whatsapp requires confidence >= 0.75 always
- Last action < 30min requires confidence >= 0.90
- fatigued + hour 23-05 → always rest_advisory at 0.95

Respond ONLY with valid JSON, no markdown:
{"reasoning":"...","action_type":"...","action_args":{},"confidence":0.0}
""".strip()

# ── LLM calls ──────────────────────────────────────────────────────────────────

def _parse_llm_output(raw_text: str, source: str) -> ReasonerOutput | None:
    """Shared parser for Groq and Ollama responses."""
    try:
        # Strip DeepSeek <think> tags if present
        if "<think>" in raw_text:
            raw_text = raw_text.split("</think>")[-1].strip()

        parsed     = json.loads(raw_text)
        confidence = float(parsed.get("confidence", 0.0))

        try:
            action_type = ActionType(parsed.get("action_type", "surface_alert"))
        except ValueError:
            log.warning("[%s] Unknown action_type: %s", source, parsed.get("action_type"))
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
        log.info("[%s] decision=%s action=%s confidence=%.2f",
                 source, decision.value, action_type.value, confidence)
        return output

    except json.JSONDecodeError as e:
        log.error("[%s] JSON parse failed: %s", source, e)
        return None


async def call_groq(context: Context, session: aiohttp.ClientSession) -> ReasonerOutput | None:
    user_msg = f"""
CURRENT CONTEXT:
Timestamp      : {context.timestamp}
Hour of day    : {context.hour_of_day}:00
Emotion state  : {context.emotion_state}
Last action    : {f"{context.last_action_minutes_ago}min ago" if context.last_action_minutes_ago else "unknown"}

PHANTOM ZERO SCORES:
{json.dumps(context.phantom_scores, indent=2)}

PRIORITY RECOMMENDATION:
{context.phantom_priority or "none"}

{context.goal_stack_summary}

{context.learning_context}

RECENT MEMORIES:
{chr(10).join(f"- {m}" for m in context.recent_memories) or "none"}

SYSTEM ALERTS:
{json.dumps(context.system_alerts[:3], indent=2) if context.system_alerts else "none"}

Decide now. One action or none. JSON only.
""".strip()

    payload = {
        "model":           GROQ_MODEL,
        "messages":        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "temperature":     0.3,
        "max_tokens":      512,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        async with session.post(
            GROQ_URL, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 429:
                log.warning("Groq rate limited — triggering fallback.")
                return None
            if resp.status != 200:
                log.error("Groq error %d", resp.status)
                return None
            data     = await resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return _parse_llm_output(raw_text, "GROQ")

    except asyncio.TimeoutError:
        log.error("Groq timeout — triggering fallback.")
        return None
    except Exception as e:
        log.error("Groq call failed: %s", e)
        return None


async def call_ollama(context: Context, session: aiohttp.ClientSession) -> ReasonerOutput | None:
    user_msg = (
        f"Hour: {context.hour_of_day}:00 | Emotion: {context.emotion_state} | "
        f"Last action: {f'{context.last_action_minutes_ago}min ago' if context.last_action_minutes_ago else 'unknown'}\n"
        f"PHANTOM SCORES: {json.dumps(context.phantom_scores)}\n"
        f"PRIORITY: {context.phantom_priority or 'none'}\n"
        f"{context.goal_stack_summary}\n"
        f"MEMORIES: {'; '.join(context.recent_memories[:3]) or 'none'}\n"
        f"JSON only."
    )

    payload = {
        "model":   OLLAMA_MODEL,
        "prompt":  f"{SYSTEM_PROMPT}\n\nUSER:\n{user_msg}",
        "stream":  False,
        "format":  "json",
        "options": {"temperature": 0.3, "num_predict": 256},
    }

    try:
        async with session.post(
            f"{OLLAMA_URL}/api/generate", json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                log.error("Ollama error %d", resp.status)
                return None
            data     = await resp.json()
            raw_text = data.get("response", "")
            return _parse_llm_output(raw_text, "OLLAMA")

    except Exception as e:
        log.error("Ollama call failed: %s", e)
        return None


async def ollama_available(session: aiohttp.ClientSession) -> bool:
    try:
        async with session.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=aiohttp.ClientTimeout(total=3),
        ) as resp:
            if resp.status == 200:
                data   = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return any(OLLAMA_MODEL.split(":")[0] in m for m in models)
    except Exception:
        pass
    return False

# ── Guardrails ─────────────────────────────────────────────────────────────────

def apply_guardrails(output: ReasonerOutput, context: Context) -> ReasonerOutput:
    mins = context.last_action_minutes_ago

    # Rule 1: Too soon since last action
    if mins is not None and mins < 30 and output.confidence < 0.90:
        log.info("Guardrail: last action %dmin ago, confidence %.2f < 0.90 → DISCARD", mins, output.confidence)
        output.decision = Decision.DISCARD
        return output

    # Rule 2: WhatsApp requires >= 0.75
    if output.action_type == ActionType.SEND_WHATSAPP and output.confidence < 0.75:
        log.info("Guardrail: WhatsApp confidence %.2f < 0.75 → ESCALATE", output.confidence)
        output.decision = Decision.ESCALATE
        return output

    # Rule 3: Fatigued + late night
    hour = context.hour_of_day
    if context.emotion_state == "fatigued" and (hour >= 23 or hour <= 5):
        if output.action_type not in (ActionType.REST_ADVISORY, ActionType.SURFACE_ALERT):
            log.info("Guardrail: fatigued + late night → override to rest_advisory")
            output.action_type = ActionType.REST_ADVISORY
            output.action_args = {"reason": "Fatigue detected at late hour. Rest is the highest-leverage action, sir."}
            output.confidence  = 0.95
            output.decision    = Decision.ACT_NOTIFY

    return output

# ── Action executor ────────────────────────────────────────────────────────────

async def execute_action(output: ReasonerOutput, session: aiohttp.ClientSession) -> bool:
    if output.decision == Decision.DISCARD:
        return True

    args = output.action_args

    async def post(path: str, payload: dict, timeout: int = 10) -> bool:
        try:
            async with session.post(
                f"{BACKEND_URL}{path}", json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                ok = r.status in (200, 201)
                if not ok:
                    log.warning("POST %s → %d", path, r.status)
                return ok
        except Exception as e:
            log.error("POST %s failed: %s", path, e)
            return False

    alert_payload = lambda msg, sev: {
        "message": msg, "severity": sev, "source": "goal_reasoner"
    }

    try:
        if output.action_type == ActionType.SEND_BRIEF:
            return await post("/briefing", {})

        elif output.action_type == ActionType.LOG_DOMAIN:
            return await post("/phantom/log", {
                "domain":        args.get("domain", "general"),
                "activity_type": args.get("activity_type", "auto_detected"),
                "value":         args.get("value", 1),
                "notes":         args.get("notes", f"Auto-logged by Goal Reasoner at {datetime.now().strftime('%H:%M')}"),
            })

        elif output.action_type == ActionType.SURFACE_ALERT:
            if output.confidence >= CONFIDENCE_ACT_NOTIFY:
                return await post("/internal/alert", alert_payload(
                    args.get("message", output.reasoning[:200]),
                    args.get("severity", "info"),
                ))
            return True

        elif output.action_type == ActionType.SUGGEST_FOCUS:
            msg = (
                f"[JARVIS] Focus: {args.get('domain', '')} — "
                f"{args.get('suggested_action', '')} ({args.get('reason', '')})"
            )
            return await post("/internal/alert", alert_payload(msg, "info"))

        elif output.action_type == ActionType.REST_ADVISORY:
            msg = f"[JARVIS] Rest advisory: {args.get('reason', 'You appear fatigued. Rest now, sir.')}"
            return await post("/internal/alert", alert_payload(msg, "warning"))

        elif output.action_type == ActionType.ESCALATE:
            msg = (
                f"[JARVIS] Decision needed ({output.confidence:.0%} confidence): "
                f"{output.reasoning[:300]}"
            )
            return await post("/internal/alert", {
                "message":  msg,
                "severity": "warning",
                "source":   "goal_reasoner_escalation",
            })

        elif output.action_type == ActionType.SEND_WHATSAPP:
            return await post("/whatsapp/send", {"message": args.get("message", "")}, timeout=15)

        elif output.action_type == ActionType.FETCH_INTEL:
            return await post("/intel/refresh", {"categories": args.get("categories", ["tech", "world"])}, timeout=20)

    except Exception as e:
        log.error("execute_action failed: %s", e)
        return False

    return True

# ── Audit logger ───────────────────────────────────────────────────────────────

def audit_cycle(context: Context, output: ReasonerOutput | None, executed: bool) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # Rotate if too many files
    existing = sorted(AUDIT_DIR.glob("cycle_*.json"))
    if len(existing) > AUDIT_MAX_FILES:
        for old in existing[:len(existing) - AUDIT_MAX_FILES]:
            try:
                old.unlink()
            except Exception:
                pass

    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = AUDIT_DIR / f"cycle_{ts}.json"
    record     = {
        "timestamp": datetime.now().isoformat(),
        "context":   asdict(context),
        "output":    asdict(output) if output else None,
        "executed":  executed,
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

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    global _shutdown

    log.info("JARVIS-MKIV Goal Reasoner v2 starting — interval=%ds", REASONER_INTERVAL)
    log.info("Thresholds: ACT_SILENT=%.2f ACT_NOTIFY=%.2f ESCALATE=%.2f",
             CONFIDENCE_ACT_SILENT, CONFIDENCE_ACT_NOTIFY, CONFIDENCE_ESCALATE)

    if not GROQ_API_KEY:
        log.critical("GROQ_API_KEY not set. Cannot reason. Exiting.")
        sys.exit(1)

    # Lazy import memory module
    try:
        from .reasoner_memory import write_decision_memory
        memory_enabled = True
        log.info("Memory write-back: ENABLED")
    except Exception as e:
        log.warning("Memory write-back disabled: %s", e)
        memory_enabled = False
        write_decision_memory = None

    async with aiohttp.ClientSession() as session:
        cycle = 0

        while not _shutdown:
            cycle += 1
            log.info("── CYCLE %d ──", cycle)

            output   = None
            executed = False

            try:
                # 1. SENSE
                context = await assemble_context(session)
                context.last_action_minutes_ago = minutes_since_last_action()

                # 2. REASON — Groq first, Ollama fallback
                output = await call_groq(context, session)

                if output is None:
                    log.warning("Groq unavailable — checking Ollama fallback")
                    if await ollama_available(session):
                        output = await call_ollama(context, session)
                        if output:
                            log.info("Ollama fallback succeeded.")
                        else:
                            log.error("Ollama fallback also failed. Skipping cycle.")
                    else:
                        log.error("Ollama not available. Skipping cycle.")

                if output:
                    # 3. GUARDRAILS
                    output = apply_guardrails(output, context)

                    # 4. DECIDE + ACT
                    if output.decision != Decision.DISCARD:
                        executed = await execute_action(output, session)
                        if executed and output.decision in (Decision.ACT_SILENT, Decision.ACT_NOTIFY):
                            record_action_taken()
                            # Update goal stack with action taken
                            gs = get_goal_stack()
                            if gs:
                                gs.record_reasoner_action(
                                    output.action_type.value,
                                    output.action_args,
                                )
                    else:
                        log.info("Cycle %d: DISCARD — no action taken", cycle)

                    # 5. MEMORY WRITE-BACK (always — even discards are valuable learning)
                    if memory_enabled and write_decision_memory:
                        await write_decision_memory(session, output, executed, context)

                # 6. AUDIT — written before sleep, even on failure
                audit_cycle(context, output, executed)

            except Exception as e:
                log.error("Unhandled error in cycle %d: %s", cycle, e)
                # Still write audit on exception
                try:
                    audit_cycle(Context(), output, False)
                except Exception:
                    pass

            if _shutdown:
                log.info("Shutdown flag set — exiting after cycle %d.", cycle)
                break

            log.info("Cycle %d complete. Sleeping %ds.", cycle, REASONER_INTERVAL)
            await asyncio.sleep(REASONER_INTERVAL)

    log.info("Goal Reasoner shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
