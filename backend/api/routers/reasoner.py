"""
JARVIS-MKIV — reasoner_router.py

Add to backend/api/routers/ and include in main.py:
    from .routers.reasoner import router as reasoner_router
    app.include_router(reasoner_router, prefix="/reasoner", tags=["reasoner"])

This gives the Watchdog an HTTP endpoint to monitor the Goal Reasoner's health,
and exposes the audit trail to the HUD MISSIONS tab.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

AUDIT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "reasoner_audit"

# ── /reasoner/status ───────────────────────────────────────────────────────────

@router.get("/status")
async def reasoner_status() -> dict[str, Any]:
    """
    Health check for the Goal Reasoner — monitored by Watchdog.
    Returns the last cycle timestamp and decision summary.
    """
    if not AUDIT_DIR.exists():
        return {
            "status": "no_cycles_yet",
            "last_cycle": None,
            "message": "Reasoner has not completed a cycle yet.",
        }

    audit_files = sorted(AUDIT_DIR.glob("cycle_*.json"), reverse=True)

    if not audit_files:
        return {
            "status": "no_cycles_yet",
            "last_cycle": None,
        }

    latest_file = audit_files[0]
    try:
        data = json.loads(latest_file.read_text())
        last_ts = data.get("timestamp", "")

        # Stale check: if last cycle > 20 minutes ago, report degraded
        if last_ts:
            last_dt = datetime.fromisoformat(last_ts)
            minutes_ago = (datetime.now() - last_dt).total_seconds() / 60
            status = "healthy" if minutes_ago < 20 else "degraded"
        else:
            minutes_ago = None
            status = "unknown"

        output = data.get("output") or {}

        return {
            "status": status,
            "last_cycle": last_ts,
            "minutes_ago": round(minutes_ago, 1) if minutes_ago else None,
            "last_decision": output.get("decision"),
            "last_action":   output.get("action_type"),
            "last_confidence": output.get("confidence"),
            "total_cycles":  len(audit_files),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit read failed: {e}")


# ── /reasoner/history ──────────────────────────────────────────────────────────

@router.get("/history")
async def reasoner_history(limit: int = 20) -> dict[str, Any]:
    """
    Return the last N reasoner cycles — for the HUD MISSIONS tab.
    """
    if not AUDIT_DIR.exists():
        return {"cycles": [], "total": 0}

    audit_files = sorted(AUDIT_DIR.glob("cycle_*.json"), reverse=True)[:limit]
    cycles = []

    for f in audit_files:
        try:
            data = json.loads(f.read_text())
            output = data.get("output") or {}
            cycles.append({
                "timestamp":  data.get("timestamp"),
                "emotion":    data.get("context", {}).get("emotion_state"),
                "decision":   output.get("decision"),
                "action":     output.get("action_type"),
                "confidence": output.get("confidence"),
                "reasoning":  output.get("reasoning", "")[:200],
                "executed":   data.get("executed"),
            })
        except Exception:
            continue

    return {
        "cycles": cycles,
        "total":  len(audit_files),
    }


# ── /reasoner/audit/{filename} ─────────────────────────────────────────────────

@router.get("/audit/{filename}")
async def get_audit_file(filename: str) -> dict[str, Any]:
    """
    Return a full audit record by filename — for deep inspection from HUD.
    """
    # Sanitize — only allow cycle_*.json filenames
    if not filename.startswith("cycle_") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    target = AUDIT_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Audit file not found.")

    try:
        return json.loads(target.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")
