"""
JARVIS-MKIV — goal_stack.py

Persistent goal stack for the Goal Reasoner.
Survives restarts. Persists to data/goals.json.

Without this, the Reasoner reasons from scratch every 10 minutes.
With this, it knows: "combat score has been below target for 3 days —
this is a persistent gap, not a one-cycle anomaly."

Usage in goal_reasoner.py:
    from .goal_stack import GoalStack

    goal_stack = GoalStack()

    # In assemble_context():
    context.active_goals = goal_stack.get_active()

    # After execute_action():
    goal_stack.update_from_scores(context.phantom_scores)
    goal_stack.record_reasoner_action(output.action_type, output.action_args)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger("goal_reasoner")

GOALS_FILE = Path(__file__).parent.parent.parent / "data" / "goals.json"

# Domain targets — mirrors PHANTOM ZERO
DOMAIN_TARGETS: dict[str, float] = {
    "engineering": 80.0,
    "programming": 85.0,
    "combat":      75.0,
    "strategy":    70.0,
    "neuro":       75.0,
}

# How many consecutive cycles below target before flagging as persistent gap
PERSISTENT_GAP_CYCLES = 3

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Goal:
    id:               str
    domain:           str
    description:      str
    target_score:     float
    current_score:    float
    cycles_below:     int       = 0    # consecutive cycles below target
    cycles_above:     int       = 0    # consecutive cycles above target
    status:           str       = "active"   # active | achieved | paused
    created_at:       str       = field(default_factory=lambda: datetime.now().isoformat())
    last_updated:     str       = field(default_factory=lambda: datetime.now().isoformat())
    last_action:      str | None = None
    last_action_time: str | None = None
    notes:            str       = ""

    @property
    def gap(self) -> float:
        return max(0.0, self.target_score - self.current_score)

    @property
    def is_persistent_gap(self) -> bool:
        return self.cycles_below >= PERSISTENT_GAP_CYCLES

    @property
    def priority_score(self) -> float:
        """Higher = more urgent. Factors: gap size + persistence."""
        return self.gap * (1 + self.cycles_below * 0.1)


# ── GoalStack ──────────────────────────────────────────────────────────────────

class GoalStack:
    """
    Manages persistent goals across Reasoner cycles.
    Auto-generates goals from PHANTOM ZERO domain gaps.
    Persists to disk — survives service restarts.
    """

    def __init__(self) -> None:
        self.goals: dict[str, Goal] = {}
        self._load()
        self._ensure_domain_goals()

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if GOALS_FILE.exists():
            try:
                raw = json.loads(GOALS_FILE.read_text())
                for gid, gdata in raw.items():
                    self.goals[gid] = Goal(**gdata)
                log.info("GoalStack loaded %d goals from disk.", len(self.goals))
            except Exception as e:
                log.warning("GoalStack load failed: %s — starting fresh.", e)
                self.goals = {}

    def _save(self) -> None:
        try:
            data = {gid: asdict(g) for gid, g in self.goals.items()}
            GOALS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            log.error("GoalStack save failed: %s", e)

    # ── Goal management ────────────────────────────────────────────────────────

    def _ensure_domain_goals(self) -> None:
        """Create a goal for each PHANTOM ZERO domain if not already present."""
        for domain, target in DOMAIN_TARGETS.items():
            gid = f"phantom_{domain}"
            if gid not in self.goals:
                self.goals[gid] = Goal(
                    id=gid,
                    domain=domain,
                    description=f"Maintain {domain} score at or above {target}",
                    target_score=target,
                    current_score=0.0,
                )
        self._save()

    def get_active(self) -> list[dict[str, Any]]:
        """Return active goals sorted by priority (highest gap first)."""
        active = [g for g in self.goals.values() if g.status == "active"]
        active.sort(key=lambda g: g.priority_score, reverse=True)
        return [asdict(g) for g in active]

    def get_top_priority(self) -> Goal | None:
        """Return the single most urgent active goal."""
        active = [g for g in self.goals.values() if g.status == "active"]
        if not active:
            return None
        return max(active, key=lambda g: g.priority_score)

    def get_persistent_gaps(self) -> list[Goal]:
        """Return goals that have been below target for PERSISTENT_GAP_CYCLES+."""
        return [
            g for g in self.goals.values()
            if g.status == "active" and g.is_persistent_gap
        ]

    # ── Update from Phantom OS scores ──────────────────────────────────────────

    def update_from_scores(self, scores: dict[str, float]) -> None:
        """
        Called every Reasoner cycle with fresh Phantom OS scores.
        Updates current_score and tracks consecutive cycles above/below target.
        """
        for domain, target in DOMAIN_TARGETS.items():
            gid = f"phantom_{domain}"
            if gid not in self.goals:
                continue

            goal = self.goals[gid]
            score = scores.get(domain, 0.0)
            goal.current_score = score
            goal.last_updated  = datetime.now().isoformat()

            if score < target:
                goal.cycles_below += 1
                goal.cycles_above  = 0
                if goal.is_persistent_gap:
                    log.warning(
                        "GoalStack: %s persistent gap — %d cycles below %.0f (current: %.0f)",
                        domain, goal.cycles_below, target, score,
                    )
            else:
                goal.cycles_above += 1
                goal.cycles_below  = 0
                if goal.cycles_above >= 5:
                    goal.status = "achieved"
                    log.info("GoalStack: %s goal ACHIEVED (score %.0f >= %.0f)", domain, score, target)

        self._save()

    # ── Record what Reasoner did ───────────────────────────────────────────────

    def record_reasoner_action(self, action_type: str, action_args: dict) -> None:
        """
        Log what action the Reasoner took so goal history is complete.
        Matches action to domain goal if possible.
        """
        domain = action_args.get("domain")
        if domain:
            gid = f"phantom_{domain}"
            if gid in self.goals:
                self.goals[gid].last_action      = action_type
                self.goals[gid].last_action_time = datetime.now().isoformat()
                self._save()

    # ── Summary for LLM prompt ─────────────────────────────────────────────────

    def build_prompt_context(self) -> str:
        """
        Returns a formatted string for injection into the Reasoner's LLM prompt.
        Gives the LLM awareness of persistent gaps and goal history.

        Example:
            GOAL STACK (persistent gaps first):
            ⚠ combat: 3 cycles below target (current=58, target=75, gap=17) — last action: suggest_focus
              neuro: 1 cycle below target (current=70, target=75, gap=5)
            ✓ engineering: ON TARGET (current=82, target=80)
        """
        lines = ["GOAL STACK:"]

        # Persistent gaps first
        persistent = self.get_persistent_gaps()
        for g in persistent:
            lines.append(
                f"  ⚠ {g.domain}: {g.cycles_below} cycles below target "
                f"(current={g.current_score:.0f}, target={g.target_score:.0f}, gap={g.gap:.0f})"
                + (f" — last action: {g.last_action}" if g.last_action else "")
            )

        # Normal gaps
        normal_gaps = [
            g for g in self.goals.values()
            if g.status == "active" and g.gap > 0 and not g.is_persistent_gap
        ]
        for g in sorted(normal_gaps, key=lambda x: x.gap, reverse=True):
            lines.append(
                f"  → {g.domain}: {g.cycles_below} cycle(s) below target "
                f"(current={g.current_score:.0f}, target={g.target_score:.0f})"
            )

        # On target
        on_target = [
            g for g in self.goals.values()
            if g.status == "active" and g.gap == 0
        ]
        for g in on_target:
            lines.append(f"  ✓ {g.domain}: ON TARGET (current={g.current_score:.0f})")

        # Achieved
        achieved = [g for g in self.goals.values() if g.status == "achieved"]
        for g in achieved:
            lines.append(f"  ★ {g.domain}: ACHIEVED")

        return "\n".join(lines)
