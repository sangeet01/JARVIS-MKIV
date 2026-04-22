"""
JARVIS-MKIV — reasoner_memory.py

Writes Goal Reasoner decisions into ChromaDB so JARVIS accumulates
a learning history. Over time the LLM prompt is enriched with past
decisions and outcomes — what worked, what was discarded, patterns.

Place in: backend/agents/reasoner_memory.py

Usage in goal_reasoner.py — after execute_action():
    from .reasoner_memory import write_decision_memory, get_recent_decisions

    # Write outcome
    await write_decision_memory(session, output, executed, context)

    # Read past decisions into context (enrich the prompt)
    past = await get_recent_decisions(session, limit=5)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import aiohttp

log = logging.getLogger("goal_reasoner")

BACKEND_URL = "http://localhost:8000"

# ── Write decision to ChromaDB via MKIII memory API ───────────────────────────

async def write_decision_memory(
    session:   aiohttp.ClientSession,
    output:    Any,   # ReasonerOutput
    executed:  bool,
    context:   Any,   # Context
) -> bool:
    """
    Write a Reasoner decision into ChromaDB memory.

    Domain tag: "reasoner" — keeps these separate from user-generated memories.
    Content is structured so future RAG searches find relevant past decisions.
    """

    if output is None:
        return False

    # Build a human-readable memory string
    outcome = "executed" if executed else "skipped"
    content = (
        f"[REASONER DECISION] {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"action={output.action_type} | decision={output.decision} | "
        f"confidence={output.confidence:.2f} | outcome={outcome} | "
        f"emotion={context.emotion_state} | "
        f"phantom_priority={context.phantom_priority[:80] if context.phantom_priority else 'none'} | "
        f"reasoning={output.reasoning[:200]}"
    )

    payload = {
        "content":  content,
        "metadata": {
            "domain":      "reasoner",
            "action_type": output.action_type if isinstance(output.action_type, str) else output.action_type.value,
            "decision":    output.decision if isinstance(output.decision, str) else output.decision.value,
            "confidence":  output.confidence,
            "executed":    executed,
            "emotion":     context.emotion_state,
            "timestamp":   datetime.now().isoformat(),
        },
    }

    try:
        async with session.post(
            f"{BACKEND_URL}/memory/store",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status in (200, 201):
                log.info("Decision written to ChromaDB memory.")
                return True
            else:
                body = await resp.text()
                log.warning("Memory write failed %d: %s", resp.status, body[:100])
                return False

    except Exception as e:
        log.error("Memory write exception: %s", e)
        return False


# ── Read recent reasoner decisions (for prompt enrichment) ────────────────────

async def get_recent_decisions(
    session: aiohttp.ClientSession,
    limit:   int = 5,
) -> list[str]:
    """
    Fetch recent Reasoner decisions from ChromaDB.
    Used to enrich the LLM prompt with learning context:
    'In the past 5 cycles you did X, Y, Z — avoid repeating if ineffective.'
    """
    try:
        async with session.get(
            f"{BACKEND_URL}/memory/search",
            params={"q": "REASONER DECISION action", "n": limit, "domain": "reasoner"},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                return [r.get("content", "") for r in results]
    except Exception as e:
        log.debug("get_recent_decisions failed: %s", e)
    return []


# ── Build learning context string for LLM prompt ──────────────────────────────

async def build_learning_context(session: aiohttp.ClientSession) -> str:
    """
    Returns a formatted string of recent decisions to inject into
    the Groq/Ollama system prompt for learning-aware reasoning.

    Example output:
        RECENT DECISIONS (last 5 cycles):
        - 2026-04-22 02:10 | suggest_focus | confidence=0.82 | executed | emotion=focused
        - 2026-04-22 01:00 | rest_advisory | confidence=0.95 | executed | emotion=fatigued
        - 2026-04-21 23:50 | log_domain | confidence=0.71 | skipped  | emotion=stressed
    """
    decisions = await get_recent_decisions(session, limit=5)

    if not decisions:
        return "RECENT DECISIONS: none yet"

    lines = ["RECENT DECISIONS (last 5 cycles):"]
    for d in decisions:
        # Extract key fields from the stored string
        # Format: [REASONER DECISION] timestamp | action=X | decision=Y | ...
        summary = d.replace("[REASONER DECISION] ", "")
        lines.append(f"  - {summary[:180]}")

    return "\n".join(lines)


# ── Outcome tracker — detect if recent actions are working ───────────────────

async def assess_action_effectiveness(
    session:     aiohttp.ClientSession,
    action_type: str,
    domain:      str | None = None,
) -> dict[str, Any]:
    """
    Check if a given action type has been effective recently.
    Used by Reasoner to avoid repeating actions that aren't working.

    Returns:
        {
          "times_used": int,
          "times_executed": int,
          "last_used": str | None,
          "recommendation": "use" | "avoid" | "neutral"
        }
    """
    query = f"REASONER DECISION action={action_type}"
    if domain:
        query += f" domain={domain}"

    try:
        async with session.get(
            f"{BACKEND_URL}/memory/search",
            params={"q": query, "n": 10},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status != 200:
                return {"times_used": 0, "times_executed": 0, "last_used": None, "recommendation": "neutral"}

            data = await resp.json()
            results = data.get("results", [])

            times_used     = len(results)
            times_executed = sum(1 for r in results if "outcome=executed" in r.get("content", ""))
            last_used      = results[0].get("metadata", {}).get("timestamp") if results else None

            # Simple heuristic: if used 3+ times and never executed → avoid
            if times_used >= 3 and times_executed == 0:
                recommendation = "avoid"
            elif times_executed > times_used * 0.5:
                recommendation = "use"
            else:
                recommendation = "neutral"

            return {
                "times_used":     times_used,
                "times_executed": times_executed,
                "last_used":      last_used,
                "recommendation": recommendation,
            }

    except Exception as e:
        log.debug("assess_action_effectiveness failed: %s", e)
        return {"times_used": 0, "times_executed": 0, "last_used": None, "recommendation": "neutral"}
