<div align="center">

```
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗    ███╗   ███╗██╗  ██╗██╗██╗   ██╗
   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝    ████╗ ████║██║ ██╔╝██║██║   ██║
   ██║███████║██████╔╝██║   ██║██║███████╗    ██╔████╔██║█████╔╝ ██║██║   ██║
██ ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║    ██║╚██╔╝██║██╔═██╗ ██║╚██╗ ██╔╝
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║    ██║ ╚═╝ ██║██║  ██╗██║ ╚████╔╝ 
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  
```

**Just A Rather Very Intelligent System — Mark IV**

*Personal AI Operating System built by AGENT17-tech under the PHANTOM ZERO framework*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Electron](https://img.shields.io/badge/Electron-41-47848F?style=flat-square&logo=electron&logoColor=white)](https://electronjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=flat-square&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![License](https://img.shields.io/badge/License-MIT-00ffc8?style=flat-square)](LICENSE)

---

*"Most AI assistants wait to be asked. JARVIS-MKIII acts."*

</div>

---

## What This Is

JARVIS-MKIV is a fully local, voice-first AI operating system running on bare metal Ubuntu. It is not just a reactive assistant; it is a proactive autonomous agent. It independently pursues goals, reasons about your PHANTOM ZERO performance in the background, and acts without needing a human trigger. It remembers every conversation, monitors and heals its own infrastructure, tracks your performance across five operational domains, reads your emotional state, and presents everything through a cinematic Electron HUD.

Built from scratch across March 2026. Upgraded to MKIV Autonomous Agency in April 2026. Every component battle-tested.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ELECTRON HUD (React 19)                      │
│  BRIDGE │ INTEL │ STRATEGY │ MISSIONS │ LIFE OS │ COMMS             │
│  Globe  │ News  │ Projects │ Phantom  │ Habits  │ Calendar          │
│  Reasoning Feed (Live autonomous thought stream)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ WebSocket + REST
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FASTAPI BACKEND :8000                          │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  Chat Router│  │ Memory Router│  │Phantom  OS │  │ Emotion  │  │
│  │  /chat      │  │ /memory/*    │  │ /phantom/* │  │ /emotion │  │
│  └──────┬──────┘  └──────────────┘  └────────────┘  └──────────┘  │
│         │                                                           │
│  ┌──────▼──────────────────────────────────────────────────────┐   │
│  │                    INTELLIGENCE PIPELINE                    │   │
│  │                                                             │   │
│  │  Voice Input → Whisper STT → Emotion Analysis              │   │
│  │       ↓                           ↓                        │   │
│  │  ChromaDB RAG ──────────────→ Context Builder              │   │
│  │       ↓                           ↓                        │   │
│  │  Tier Router → Groq T1 (Llama 3.3 70B) [Fast]              │   │
│  │             → Ollama T2 (DeepSeek-R1:7b) [Reasoning]       │   │
│  │       ↓                                                     │   │
│  │  TTS Router → ElevenLabs (Premium) → Kokoro-82M (Fallback) │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────── ┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                     AUTONOMOUS NERVOUS SYSTEM                       │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────────────────────────┐  │
│  │  Goal Reasoner   │    │           WATCHDOG SENTINEL          │  │
│  │  (SENSE-ACT)     │    │                                      │  │
│  │  10min Cycles    │    │  Monitors 6 services                 │  │
│  │  Ollama Fallback │    │  Self-Healing / Restart              │  │
│  │  Guardrail Gated │    │  Critical Failure Alerts             │  │
│  └──────────────────┘    └──────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    PHANTOM ZERO OS                           │  │
│  │  5 Domains: Engineering │ Programming │ Combat               │  │
│  │             Strategy    │ Neuro-Performance                  │  │
│  │  Goal Stack Tracking, Learning Loops, Priority Recommendations│  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Feature Matrix

### Core Intelligence

| Feature | Status | Details |
|---|---|---|
| Dual-tier LLM routing | ✅ Operational | Groq T1 (speed) + Ollama T2 (reasoning) |
| Voice STT | ✅ Operational | faster-whisper CUDA, EN/AR auto-detect |
| Dual TTS | ✅ Operational | ElevenLabs premium → Kokoro-82M fallback |
| TTS sanitizer | ✅ Operational | Strips markdown, emoji, symbols before speech |
| Vision (LLaVA:7b) | ✅ Operational | Screen reading, image analysis |
| Bilingual EN/AR | ✅ Operational | Auto-detected, responds in kind |

### Memory Layer (Mission 01)

| Feature | Status | Details |
|---|---|---|
| ChromaDB RAG | ✅ Operational | Persistent semantic memory, all-MiniLM-L6-v2 |
| Domain tagging | ✅ Operational | engineering / combat / strategy / language / general |
| Background embedding | ✅ Operational | Zero latency impact, async thread |
| Memory persistence | ✅ Operational | Survives restarts, stored in `data/chromadb` |
| Memory search API | ✅ Operational | `GET /memory/search?q=&n=` |

### Self-Healing Infrastructure (Mission 02)

| Feature | Status | Details |
|---|---|---|
| Watchdog daemon | ✅ Operational | systemd user service, 30s check interval |
| State machine | ✅ Operational | UNKNOWN→HEALTHY→DEGRADED→FAILED→CRITICAL |
| Auto-restart | ✅ Operational | Max 3 attempts/hour, 60s cooldown |
| Failure logging | ✅ Operational | `failures/{service}_{timestamp}.log` + journalctl |
| HUD alert broadcast | ✅ Operational | WebSocket push to BRIDGE tab |

### PHANTOM ZERO OS (Mission 03)

| Feature | Status | Details |
|---|---|---|
| Domain scoring | ✅ Operational | 5 domains, 0-100 scale, daily persistence |
| Chat keyword detection | ✅ Operational | Passive, background, zero friction |
| GitHub auto-logging | ✅ Operational | New commits → engineering score |
| Morning briefing injection | ✅ Operational | Domain status appended to daily brief |
| Priority recommendation | ✅ Operational | Single highest-leverage action surfaced |
| Weekly trend | ✅ Operational | 7-day rolling history per domain |

### Emotion Engine (Mission 04)

| Feature | Status | Details |
|---|---|---|
| Voice state detection | ✅ Operational | pyAudioAnalysis + librosa.yin |
| States | ✅ Operational | focused / fatigued / stressed / elevated / neutral |
| System prompt adaptation | ✅ Operational | Tone/brevity modifies per state |
| Async analysis | ✅ Operational | 11ms overhead, fully non-blocking |
| Calibration | ✅ Operational | `POST /emotion/calibrate`, baseline.json |
| HUD indicator | ✅ Operational | Colored dot in BRIDGE chat panel |

### Autonomous Agency (MKIV Upgrade)

| Feature | Status | Details |
|---|---|---|
| Goal Reasoner Loop | ✅ Operational | SENSE → REASON → GUARDRAILS → ACT cycle every 10m |
| Goal Stack Persistence | ✅ Operational | Persistent `goals.json` tracks long-horizon progress |
| Memory Learning Loop | ✅ Operational | Reasoner writes to ChromaDB, feeds back into next cycle |
| Resilience (Ollama Fallback) | ✅ Operational | Auto-switches to local DeepSeek-R1 if Groq is down |
| Decision Audit Trail | ✅ Operational | Full JSON audit per cycle in `data/reasoner_audit/` |
| Guardrail Overrides | ✅ Operational | Rapid-fire/Fatigue/Confidence safety gates |
| HUD Reasoning Feed | ✅ Operational | Live thought stream in MISSIONS tab |

### HUD (Electron + React)

| Tab | Status | Contents |
|---|---|---|
| BRIDGE | ✅ Operational | Globe, network links, chat interface, system stats |
| INTEL | ✅ Operational | Daily brief, news feed by category, AI summary |
| STRATEGY | ✅ Operational | Idea evaluator, project tracker, decision engine |
| MISSIONS | ✅ Operational | PHANTOM ZERO board, fitness, IEEE, Enactus |
| LIFE OS | ✅ Operational | Morning briefing, domain scores, habit tracker |
| COMMS | ✅ Operational | Inbox, Discord, Google Calendar |

---

## Stack

```
Backend          FastAPI 0.111 + Uvicorn + Python 3.12
LLM T1           Groq API — Llama 3.3 70B (voice + fast responses)
LLM T2           Ollama — DeepSeek-R1:7b (local reasoning)
STT              faster-whisper (CUDA) — EN/AR bilingual
TTS              ElevenLabs API → Kokoro-82M (local fallback)
Vision           LLaVA:7b via Ollama
Memory           ChromaDB + sentence-transformers/all-MiniLM-L6-v2
Emotion          pyAudioAnalysis + librosa
Automation       PyAutoGUI + BeautifulSoup + Selenium
Frontend         Electron 41 + React 19 + Vite 7 + Three.js
Tunnel           Cloudflare Tunnel (persistent public URL)
Infrastructure   systemd user services + self-healing watchdog
OS               Ubuntu 24.04 LTS — kernel 6.x
Hardware         HP ZBook 15 G6
```

---

## Prerequisites

```bash
# System
Ubuntu 24.04 LTS
Python 3.12+
Node.js 20+
CUDA-capable GPU (recommended, not required)

# External services (API keys required)
Groq API key          — https://console.groq.com
ElevenLabs API key    — https://elevenlabs.io (optional, Kokoro fallback active)
OpenWeatherMap key    — https://openweathermap.org/api
GitHub token          — https://github.com/settings/tokens

# Local services (installed during setup)
Ollama                — https://ollama.ai
Cloudflare Tunnel     — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AGENT17-tech/JARVIS-MKIII.git
cd JARVIS-MKIII
```

### 2. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM
GROQ_API_KEY=your_groq_key_here

# TTS
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=bm_george

# Weather
OPENWEATHER_API_KEY=your_openweather_key_here
OPENWEATHER_CITY=Cairo

# GitHub
GITHUB_TOKEN=your_github_token_here
GITHUB_USERNAME=AGENT17-tech

# Cloudflare
CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here

# System
DISPLAY=:0
XAUTHORITY=/home/k/.Xauthority
```

### 4. Install Ollama models

```bash
ollama pull deepseek-r1:7b
ollama pull llava:7b
```

### 5. HUD dependencies

```bash
cd hud
npm install
cd ..
```

### 6. Google Calendar (optional)

Place `credentials.json` in `backend/config/` following the [Google Calendar Python Quickstart](https://developers.google.com/calendar/api/quickstart/python).

### 7. Register systemd services

```bash
# Copy service files
cp systemd/*.service ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable jarvis-backend
systemctl --user enable jarvis-voice
systemctl --user enable jarvis-proactive
systemctl --user enable jarvis-watchdog

# Enable linger (services survive logout)
loginctl enable-linger $USER

# Start everything
systemctl --user start jarvis-backend
systemctl --user start jarvis-voice
systemctl --user start jarvis-proactive
systemctl --user start jarvis-watchdog
```

---

## Running JARVIS

### Full system start

```bash
# All backend services (if using systemd)
systemctl --user start jarvis-backend jarvis-voice jarvis-reasoner jarvis-watchdog

# Launch HUD
cd hud && npm run start
```

### Manual start (development)

```bash
# Terminal 1 — Backend
source venv/bin/activate
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Voice pipeline
source venv/bin/activate
python voice/voice_orchestrator.py

# Terminal 3 — Goal Reasoner (Autonomous Agent)
source venv/bin/activate
cd backend
python agents/goal_reasoner.py

# Terminal 4 — Watchdog
source venv/bin/activate
python watchdog.py

# Terminal 5 — HUD
cd hud && npm run start
```

### Alias setup

```bash
echo 'alias jarvis-url="cat ~/JARVIS-MKIII/.cloudflare-url"' >> ~/.bashrc
echo 'alias jarvis-start="systemctl --user start jarvis-backend jarvis-voice jarvis-reasoner jarvis-watchdog && cd ~/JARVIS-MKIII/hud && npm run start"' >> ~/.bashrc
echo 'alias jarvis-stop="systemctl --user stop jarvis-backend jarvis-voice jarvis-reasoner jarvis-watchdog"' >> ~/.bashrc
echo 'alias jarvis-status="systemctl --user status jarvis-backend jarvis-voice jarvis-reasoner jarvis-watchdog"' >> ~/.bashrc
echo 'alias jarvis-logs="journalctl --user -u jarvis-reasoner -f"' >> ~/.bashrc
source ~/.bashrc
```

---

## API Reference

### Core

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send message, receive response |
| `GET` | `/health` | System health check |
| `GET` | `/status` | Full status with version and tools |
| `POST` | `/briefing` | Trigger morning briefing |

### Memory

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/memory/stats` | Total memories, domain breakdown |
| `GET` | `/memory/search?q=&n=` | Semantic search over memory |
| `POST` | `/memory/store` | Add a memory entry (content + metadata) |
| `DELETE` | `/memory/clear?confirm=true` | Wipe all memories |

### PHANTOM ZERO

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/phantom/scores` | Today's domain scores |
| `GET` | `/phantom/weekly` | 7-day trend per domain |
| `POST` | `/phantom/log` | Log a domain activity |
| `GET` | `/phantom/priority` | Single highest-leverage recommendation |
| `GET` | `/phantom/brief` | Domain summary for briefing injection |

### Emotion

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/emotion/state` | Current detected voice state |
| `GET` | `/emotion/history` | Last 20 state readings |
| `POST` | `/emotion/calibrate` | Record 10s baseline |

### Goal Reasoner (MKIV Autonomous Agency)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/reasoner/status` | Current cycle status and health |
| `GET` | `/reasoner/history` | Recent decision log (confidence, act, reason) |
| `GET` | `/reasoner/audit/{file}` | Read raw JSON audit log |

### Infrastructure

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/internal/alert` | Watchdog pushes alerts here |
| `GET` | `/internal/alerts` | Last 50 system alerts |
| `GET` | `/diagnostic` | Full system diagnostic payload |

---

## PHANTOM ZERO Domain Scoring

JARVIS tracks performance across five domains defined by the PHANTOM ZERO framework. Scores update throughout the day based on detected activities — passively from chat, from GitHub commits, and from manual logs.

| Domain | Signals | Target |
|---|---|---|
| **Engineering & Robotics** | GitHub commits, build runs, code sessions | 80 |
| **Programming & Cyber** | DSA problems, teaching sessions, Claude Code hours | 85 |
| **Combat & Physical** | Workouts logged, sparring sessions, streak bonus | 75 |
| **Strategic Thinking** | Chess games, missions completed %, decisions logged | 70 |
| **Neuro-Performance** | Sleep hours, reading time, language study minutes | 75 |

Log an activity manually:

```bash
curl -X POST http://localhost:8000/phantom/log \
  -H "Content-Type: application/json" \
  -d '{"domain":"combat","activity_type":"workout","value":1,"notes":"kickboxing 60min"}'
```

Or just tell JARVIS naturally — keyword detection handles the rest.

---

## Self-Healing Watchdog

The watchdog runs as a separate systemd service and manages the entire JARVIS process ecosystem.

```
Services monitored:
  jarvis-backend    → HTTP check :8000/health
  jarvis-voice      → Process match: voice_orchestrator
  jarvis-reasoner   → Process match: goal_reasoner
  jarvis-whatsapp   → Process match: whatsapp
  ollama            → HTTP check :11434

State machine per service:
  UNKNOWN → HEALTHY → DEGRADED (1 fail) → FAILED (2+ fails)
          → RECOVERING (restart issued) → CRITICAL (3 restarts exhausted)

On failure:
  1. Logs last 50 journalctl lines to failures/{service}_{timestamp}.log
  2. Issues systemctl --user restart
  3. Notifies HUD via WebSocket if backend is still alive
  4. After 3 failed restarts: CRITICAL alert, stops retrying
```

Check watchdog status:

```bash
systemctl --user status jarvis-watchdog
journalctl --user -u jarvis-watchdog -f
ls ~/JARVIS-MKIII/failures/
```

---

## Emotion Engine

JARVIS analyzes prosodic features from your voice in real time and adapts its behavior accordingly. Analysis is fully async — zero impact on response latency.

```
Features extracted:
  - RMS energy (volume/intensity)
  - Zero crossing rate (speech rate proxy)
  - Pitch variance via librosa.yin

State → Behavior:
  focused   → Concise, fast, no preamble
  fatigued  → Short responses, rest advisory surfaced
  stressed  → Calm tone, non-critical alerts suppressed
  elevated  → Dynamic, matches energy
  neutral   → Default behavior
```

Calibrate to your voice:

```bash
# Via HUD chat panel
> calibrate

# Or via API
curl -X POST http://localhost:8000/emotion/calibrate
```

---

## Project Structure

```
JARVIS-MKIII/
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI app, /chat pipeline
│   │   └── routers/
│   │       ├── memory.py           # /memory endpoints
│   │       ├── phantom.py          # /phantom endpoints
│   │       └── emotion.py          # /emotion endpoints
│   ├── memory/
│   │   └── chroma_store.py         # ChromaDB RAG module
│   ├── phantom/
│   │   └── phantom_os.py           # PHANTOM ZERO domain scoring
│   ├── emotion/
│   │   └── voice_state.py          # Voice prosody analysis
│   ├── voice/
│   │   ├── voice_orchestrator.py   # STT → LLM → TTS pipeline
│   │   └── tts_router.py           # ElevenLabs → Kokoro fallback
│   ├── agents/
│   │   └── proactive_agent.py      # Background mission executor
│   └── briefing/
│       └── morning_briefing.py     # Daily brief generator
├── hud/
│   ├── electron/
│   │   ├── main.js                 # Electron main process
│   │   └── preload.js              # IPC bridge
│   └── src/
│       ├── App.jsx                 # HUD root, BRIDGE tab
│       ├── components/
│       │   └── GlobeNetwork.jsx    # Three.js globe + overlays
│       └── tabs/
│           ├── IntelTab.jsx
│           ├── StrategyTab.jsx
│           ├── MissionBoardTab.jsx
│           ├── LifeOSTab.jsx
│           └── CommsTab.jsx
├── memory/
│   └── chroma_store.py             # (legacy, see backend/memory)
├── emotion/
│   └── baseline.json               # Voice calibration baseline
├── phantom/
│   └── scores.json                 # Domain activity log
├── failures/                       # Watchdog failure logs
├── data/
│   └── chromadb/                   # Persistent vector store
├── systemd/                        # Service unit files
├── watchdog.py                     # Self-healing watchdog
├── requirements.txt
├── .env.example
└── README.md
```

---

## Voice Commands

| Command | Action |
|---|---|
| `shutdown` / `power down` | Graceful shutdown sequence with animation |
| `calibrate` | Run 10-second voice baseline calibration |
| `jarvis status` | Full system status report |
| `morning brief` | Trigger morning briefing |
| Any natural speech | Auto-routed to appropriate LLM tier |

---

## Troubleshooting

**HUD won't launch (shared memory error)**

```bash
# Check kernel setting
sysctl kernel.unprivileged_userns_clone
# If 0:
sudo sysctl -w kernel.unprivileged_userns_clone=1

# Launch with sandbox disabled
cd hud && npm run start
```

**Backend not responding**

```bash
systemctl --user restart jarvis-backend
journalctl --user -u jarvis-backend -n 50
curl http://localhost:8000/health
```

**Voice not transcribing**

```bash
# Check DISPLAY and audio
echo $DISPLAY
arecord -d 3 /tmp/test.wav && aplay /tmp/test.wav

# Check Whisper
python3 -c "from faster_whisper import WhisperModel; print('OK')"
```

**Ollama timeout**

```bash
ollama list
ollama run deepseek-r1:7b "test"
systemctl restart ollama
```

**Memory not persisting**

```bash
curl http://localhost:8000/memory/stats
ls ~/JARVIS-MKIII/data/chromadb/
```

---

## Roadmap — JARVIS-MKIV

MKIII is feature-complete. MKIV shifts the paradigm from reactive assistant to autonomous operator.

- **Autonomous agent loop** — JARVIS executes background missions without being asked
- **Face + presence detection** — OpenCV webcam trigger, screen context awareness via LLaVA
- **Full Arabic-first persona** — Complete character switch, not just language translation
- **JARVIS Codex engine** — Every session auto-appended to a living operational PDF
- **Notion / Obsidian sync** — Second brain integration, JARVIS indexes your knowledge base
- **Predictive briefing** — Cross-references sleep, calendar, deadlines, and domain scores

---

## Built By

**AGENT17** — Engineering student, IEEE Vice Technical Director, PHANTOM ZERO operator.

*"Build things that matter. Ship constantly."*

---

<div align="center">

**JARVIS-MKIII** · Built March 2026 · Ubuntu 24.04 · AGENT17-tech

*PHANTOM ZERO — MISSION: COMPLETE*

</div>
