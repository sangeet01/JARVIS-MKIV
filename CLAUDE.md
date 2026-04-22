# JARVIS-MKIV — CLAUDE.md

> Personal AI Operating System — Autonomous upgrade of MKIII.
> Built by AGENT17 under the PHANTOM ZERO framework.

---

## What This Project Is

JARVIS-MKIV upgrades MKIII from a reactive assistant to a proactive autonomous operator.
The core addition is `backend/agents/goal_reasoner.py` — an autonomous loop that reads
all MKIII systems, reasons about the highest-leverage action, and acts without being asked.

**MKIII already has:** Memory (ChromaDB), Emotion engine, Phantom OS scoring,
Watchdog, HUD (Electron/React), Voice pipeline (Whisper → Groq → ElevenLabs),
WhatsApp (Baileys), Google Calendar, GitHub monitoring.

**MKIV adds:** Goal Reasoner, confidence-gated autonomous action, full audit trail.

---

## Stack

```
Backend          FastAPI 0.111 + Uvicorn + Python 3.12
Reasoner LLM     Groq — Llama 3.3 70B (fast, structured JSON output)
Fallback LLM     Ollama — DeepSeek-R1:7b (local, no API cost)
Memory           ChromaDB + sentence-transformers/all-MiniLM-L6-v2
Phantom OS       backend/phantom/phantom_os.py — 5 domain scoring
Emotion          backend/emotion/voice_state.py — prosody analysis
Watchdog         watchdog.py — self-healing state machine
HUD              Electron 41 + React 19 + Vite 7 + Three.js
Infrastructure   systemd user services
OS               Ubuntu 24.04 LTS
```

---

## Project Structure

```
JARVIS-MKIV/
├── backend/
│   ├── agents/
│   │   ├── goal_reasoner.py        ← NEW: autonomous agent loop (MKIV core)
│   │   └── proactive_agent.py      ← MKIII: timer-based (being replaced)
│   ├── api/
│   │   ├── main.py                 ← FastAPI app
│   │   └── routers/
│   │       ├── memory.py
│   │       ├── phantom.py
│   │       └── emotion.py
│   ├── memory/chroma_store.py
│   ├── phantom/phantom_os.py
│   ├── emotion/voice_state.py
│   └── voice/voice_orchestrator.py
├── hud/src/
│   ├── App.jsx
│   └── tabs/
│       ├── IntelTab.jsx
│       ├── MissionBoardTab.jsx
│       └── LifeOSTab.jsx
├── data/
│   ├── chromadb/                   ← persistent vector store
│   └── reasoner_audit/             ← NEW: full decision audit trail
├── watchdog.py
├── jarvis-reasoner.service         ← NEW: systemd unit for goal reasoner
└── CLAUDE.md                       ← this file
```

---

## gstack Skills Available

```
/plan-ceo-review        — challenge architecture decisions before coding
/plan-eng-review        — lock architecture, produce diagrams, edge cases
/review                 — paranoid production safety check
/qa                     — end-to-end browser testing
/ship                   — PR with test coverage audit
/document-release       — keep docs in sync after shipping
/retro                  — weekly velocity and shipping data
/jarvis-agent-review    — CUSTOM: agent-specific safety audit (see below)
```

---

## JARVIS-Specific Review Rules

When running `/review` or `/jarvis-agent-review`, enforce these rules:

### Autonomous Agent Rules (CRITICAL)
- Every autonomous action MUST have a confidence score between 0.0 and 1.0
- WhatsApp sends MUST require confidence >= 0.75 — irreversible external action
- Actions < 30 minutes after last action MUST require confidence >= 0.90
- All decisions MUST be written to `data/reasoner_audit/` before execution
- The guardrail `apply_guardrails()` MUST run before EVERY execution

### Async / Pipeline Rules
- ZERO blocking calls in the voice pipeline — everything async
- All ChromaDB writes MUST be in background threads (not blocking event loop)
- Groq API calls MUST have timeout=30s max
- Every external API call MUST have a try/except with graceful fallback

### Memory Rules
- Every ChromaDB write MUST include a domain tag
  (engineering / combat / strategy / language / programming / general)
- Memory searches MUST be async
- Never write raw LLM output to memory without sanitizing markdown/emoji

### Watchdog Rules
- Adding a new long-running service MUST add it to SERVICES list in watchdog.py
- The Goal Reasoner service MUST be monitored via HTTP check on a /reasoner/status endpoint
- State machine: UNKNOWN→HEALTHY→DEGRADED→FAILED→RECOVERING→CRITICAL

### HUD Rules
- WebSocket alerts from Goal Reasoner MUST include source="goal_reasoner"
- BRIDGE tab MUST visually distinguish reasoner alerts from watchdog alerts
- Audit trail decisions MUST be viewable from MISSIONS tab

---

## Confidence & Escalation System

```
>= 0.85  ACT_SILENT   → act, log only, no HUD notification
>= 0.60  ACT_NOTIFY   → act, push HUD notification after
>= 0.40  ESCALATE     → surface to user via HUD for decision
<  0.40  DISCARD      → do nothing, log reasoning only
```

GUARDRAIL OVERRIDES (hard rules, LLM cannot override):
1. Last action < 30min ago → require 0.90+ to act
2. WhatsApp → always require 0.75+ regardless of LLM output
3. Emotion=fatigued + hour 23-05 → force rest_advisory at 0.95

---

## PHANTOM ZERO Domain Targets

```
engineering   → target 80   (GitHub commits, builds, hardware)
programming   → target 85   (DSA, code sessions, Claude Code hours)
combat        → target 75   (workouts, sparring, streak bonus)
strategy      → target 70   (chess, missions %, decisions logged)
neuro         → target 75   (sleep, reading, language study)
```

---

## Key API Endpoints (MKIII + MKIV)

```
POST /chat                  — main chat pipeline
GET  /health                — system health
GET  /phantom/scores        — today's domain scores
GET  /phantom/priority      — highest-leverage recommendation
POST /phantom/log           — log domain activity
GET  /emotion/state         — current voice state
GET  /memory/search?q=&n=   — semantic memory search
POST /internal/alert        — push alert to HUD via WebSocket
GET  /internal/alerts       — last 50 alerts
POST /briefing              — trigger morning briefing
GET  /reasoner/status       — NEW: goal reasoner health (for watchdog)
```

---

## Anti-Patterns to Flag in Review

- LLM output trusted without confidence gate → BLOCK
- Action executed without audit log write → BLOCK
- Blocking I/O inside async voice pipeline → BLOCK
- ChromaDB write without domain tag → WARN
- New systemd service not added to watchdog → WARN
- HUD alert without source field → WARN
- Groq API call without timeout → WARN
- WhatsApp send without 0.75+ confidence check → BLOCK

---

## Personality Anchor

JARVIS identifies as built by **Khalid** (sir).
References to Tony Stark or Iron Man in system prompts → test failure.
See `test_personality.py` — must pass 6/6 before any PR merges.

---

## Commands

```bash
# Start full MKIV stack
systemctl --user start jarvis-backend jarvis-voice jarvis-proactive jarvis-reasoner jarvis-watchdog
cd hud && npm run start

# Check reasoner
systemctl --user status jarvis-reasoner
journalctl --user -u jarvis-reasoner -f
ls data/reasoner_audit/

# Run personality test
python test_personality.py

# Tail all logs
journalctl --user -u jarvis-backend -u jarvis-reasoner -f
```
