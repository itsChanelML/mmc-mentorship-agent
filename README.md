# MMC Long-Horizon Mentorship Agent

**Program Manager + Program Coordinator AI for Mentor Me Collective**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM-76B900.svg)](https://build.nvidia.com)
[![Nemotron](https://img.shields.io/badge/Model-Nemotron--Super--49b-76B900.svg)](https://build.nvidia.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Built on `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM.
Implements the Long-Horizon Agent architecture presented by Kay Zhu
(CTO, Genspark) at GTC 2026 — Track S82413.
Built as a Genspark Builder Grant recipient — 1 of 300 selected globally.

---

## The Problem

Mentor Me Collective runs a mentorship program for first-generation
professionals across 120+ countries. At scale, program continuity
depends entirely on human memory:

- Did this scholar complete onboarding?
- Has this mentor-mentee pair met this week?
- Which scholars are silently drifting toward dropout?
- Which mentor is the best match for this applicant?

**When progression depends on human memory, people fall through the cracks.**

14,000+ qualified applicants are turned away every year — not because they aren't ready, but because human-constrained capacity can't serve them. This agent replaces reliance on human memory with persistent, signal-driven lifecycle management running continuously across hours and days.

---

## The Architecture

This project implements Kay Zhu's three Long-Horizon Agent bottleneck solutions from GTC 2026 (Track S82413):

### 1. Memory — Context is RAM. Files are your Hard Disk.

Every scholar and mentor has a persistent JSON file on disk. The agent reads it at the start of every cycle, acts on it, and writes results back immediately. No state lives only in context. The agent can crash, restart, and continue exactly where it left off.

```
participants/
├── scholar_green.json    # Maya Chen — Active, on track
├── scholar_orange.json   # Jara Banana-Seed — Orange path, onboarding incomplete
└── scholar_risk.json     # Sofia Torres — Active, participation drift detected
mentors/
├── mentor_042.json       # David Park — Civic tech, engineering
└── mentor_017.json       # Priya Sharma — Data science, healthcare
```

### 2. Action — Composable Tools, Not Monolithic Prompts

Each coordinator responsibility is a composable tool that does one thing and returns structured output. The LLM orchestrates. It does not carry all the data.

```
tools/
├── escalation_writer.py  # Nemotron generates coordinator briefs
├── drift_detector.py     # Nemotron generates re-engagement messages
├── intake_monitor.py     # Dual-stream mentee + mentor intake monitoring
└── matching_engine.py    # Intelligent mentor-mentee matching with intro letters
```

### 3. Continuity — External Loop with Checkpoint

The agent runs in an external loop. Every cycle: read all participant files → detect signals → decide action → execute tool → write state back to disk → checkpoint.

```python
# The continuity solution
# "Tight loops beat big plans." — Kay Zhu, GTC 2026
while True:
    results = run_cycle(cycle_number)
    checkpoint(cycle_number, results)
    sleep(86400)  # 24 hours in production
```

---

## The Full System

```
┌─────────────────────────────────────────────────────────┐
│                MMC LONG-HORIZON AGENT                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INTAKE MONITOR          SIGNAL MONITOR                 │
│  ─────────────           ──────────────                 │
│  Mentee applications     Progress signals               │
│  Mentor applications     Engagement signals             │
│  Completeness scoring    Risk signals                   │
│  Completion reminders    Risk scoring (0.0–1.0)         │
│                                                         │
│  DECISION ROUTER         MATCHING ENGINE                │
│  ───────────────         ────────────────               │
│  NO_ACTION               Hard compatibility checks      │
│  SEND_REMINDER           Nemotron deep analysis         │
│  SEND_ONBOARDING_PROMPT  Compatibility score 0–100      │
│  GENERATE_DRIFT_ALERT    Introduction letters           │
│  GENERATE_ESCALATION     Coordinator recommendation     │
│                                                         │
│  NEMOTRON via NIM        HARD DISK                      │
│  ────────────────        ─────────                      │
│  Escalation briefs       Participant JSON files         │
│  Onboarding prompts      Mentor JSON files              │
│  Drift alerts            Checkpoint file                │
│  Match reports           outputs/ folder                │
│  Intro letters           escalations/ folder            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## The Signal Monitor

Three signal categories mirror MMC's program engineering document:

| Signal Type | Indicators | Threshold |
|-------------|------------|-----------|
| **Progress** | Onboarding completion, artifact submission, goals documented | 7+ days gap |
| **Engagement** | Meeting cadence, response behavior, session prep | 3–5 days gap |
| **Risk** | Stalled progression, silent disengagement, repeated non-response | Score ≥ 0.75 |

---

## The Decision Engine

The router maps signal results to agent actions:

| Risk Score | Path | Action |
|------------|------|--------|
| 0.0–0.3 | Any | `NO_ACTION` — monitor only |
| 0.3–0.7 | Orange | `SEND_ONBOARDING_PROMPT` |
| 0.7–1.0 | Green Active | `GENERATE_DRIFT_ALERT` |
| ≥ 0.75 | Green Active | `GENERATE_ESCALATION` |

---

## The Matching Engine

Hard compatibility checks run first — fast, deterministic, no AI needed:

- Availability overlap (days + time slots)
- Mentoring style compatibility
- Cadence alignment
- Industry overlap
- Expertise coverage

Then Nemotron performs deep compatibility analysis across both full profiles and generates:

- Compatibility score (0–100)
- Match reasoning with specific profile references
- Shared foundation — the human connection
- Potential challenges — honest, not alarming
- Coordinator recommendation
- Personalized introduction letter to the mentee
- Personalized introduction letter to the mentor

**In a recent run: Jara matched to Priya Sharma at 88/100 over David Park at 85/100 — Nemotron identified their shared experience as first-gen professionals navigating non-traditional paths into technical fields as the decisive factor.**

---

## What Nemotron Does

Rules detect. Nemotron communicates.

**Escalation Brief** — for scholars showing participation drift:
```
SITUATION SUMMARY
RISK SIGNALS DETECTED
SCHOLAR CONTEXT
RECOMMENDED COORDINATOR ACTIONS
SUGGESTED OUTREACH MESSAGE — ready to copy and send
```

**Onboarding Prompt** — for Orange path scholars:
- References specific details from their application
- Acknowledges their career vision personally
- Names exactly what sections still need completion
- Gives one specific, low-friction next step

**Drift Alert** — for Active scholars going quiet:
- Opens with genuine care, not a warning
- References their career vision so they feel remembered
- Offers a low-pressure next step
- Reminds them their mentor is still there

**Match Report** — for scholars ready for pairing:
- Full compatibility analysis
- Introduction letters for both parties
- All mentor evaluations logged for transparency

All outputs go to `escalations/` or `outputs/` for coordinator review. **No message is ever sent automatically.** The agent drafts. The coordinator decides.

---

## The Automation Boundary

Based on MMC's End-to-End Experience Summary:

**Agent governs:**
- State tracking across the full lifecycle
- Signal detection and risk scoring (0.0–1.0)
- Action routing and document generation
- Checkpoint and continuity management
- Mentor-mentee compatibility scoring

**Humans govern:**
- Readiness interpretation
- Relationship judgment
- Conflict resolution
- Final send decision on all outreach
- Final match approval

*"The program team guides people. Engineering guides progression."*

---

## Demo

```bash
# Clone the repo
git clone https://github.com/itsChanelML/mmc-mentorship-agent.git
cd mmc-mentorship-agent

# Install dependencies
pip install openai python-dotenv

# Add your NVIDIA NIM API key
cp .env.example .env
# Edit .env: NVIDIA_API_KEY=nvapi-your-key-here

# Run the full agent cycle
python3 agent.py

# Run intake monitoring across mentees and mentors
python3 tools/intake_monitor.py

# Run the matching engine
python3 tools/matching_engine.py
```

**Expected agent output:**
```
MMC LONG-HORIZON MENTORSHIP AGENT
Powered by Nemotron via NVIDIA NIM
Genspark Builder Grant — GTC 2026

Resuming from checkpoint — last run: 2026-04-16T21:26:56

── Processing: Maya Chen ──────────────────────
Signal Score: 0.0
Action: NO_ACTION — Scholar on track

── Processing: Sofia Torres ──────────────────────
Signal Score: 0.9
Flags: ARTIFACT_GAP, CADENCE_BREACH, RESPONSE_GAP, STALLED_PROGRESSION
Action: GENERATE_ESCALATION
→ Escalation brief written to escalations/

── Processing: Jara Banana-Seed ──────────────────────
Signal Score: 0.95
Flags: ONBOARDING_INCOMPLETE, NO_MEETING_SCHEDULED
Action: SEND_ONBOARDING_PROMPT
→ Personalized prompt written to outputs/

CYCLE 3 COMPLETE
Scholars processed: 3
Escalations: 1
Prompts generated: 1
No action needed: 1
```

---

## Stack

| Layer | Tool |
|-------|------|
| Intelligence | nvidia/llama-3.3-nemotron-super-49b-v1.5 |
| Inference | NVIDIA NIM API |
| Agent Runtime | Python 3.9+ |
| Memory | JSON file system — hard disk pattern |
| Orchestration | Custom external loop with checkpoint |
| Prompt Management | File-based templates with format_map |
| Deployment | Local / Cloud Run ready |

---

## Project Structure

```
mmc-mentorship-agent/
├── agent.py                    # Main orchestrator + external loop
├── signals.py                  # Signal monitor — the nervous system
├── router.py                   # Decision engine
├── utils.py                    # Prompt loader + formatting utilities
│
├── tools/
│   ├── escalation_writer.py    # Coordinator escalation briefs
│   ├── drift_detector.py       # Re-engagement + onboarding prompts
│   ├── intake_monitor.py       # Dual-stream intake monitoring
│   └── matching_engine.py      # Mentor-mentee matching engine
│
├── prompts/
│   ├── escalation_brief.txt    # Escalation brief template
│   ├── drift_alert.txt         # Drift alert template
│   ├── onboarding_reminder.txt # Onboarding reminder template
│   ├── matching_report.txt     # Match analysis template
│   └── completion_reminder.txt # Application completion template
│
├── participants/               # Scholar hard disk (JSON files)
├── mentors/                    # Mentor hard disk (JSON files)
├── escalations/                # Human review queue — escalations
├── outputs/                    # Human review queue — all other outputs
│
├── .env.example                # API key template
├── .gitignore                  # Protects .env and runtime files
└── README.md
```

---

## What's Next — V2 on Google Cloud

V1 demonstrates the full Long-Horizon architecture. V2 (production on GCP with $25K in credits) adds:

- Real scholar data with privacy handling
- Google Meet + Calendar API for live session scheduling
- BigQuery telemetry for NYC government compliance reporting
- Vertex AI risk prediction model trained on cohort data
- Cloud Scheduler for automated 24-hour cycles
- MMC 2.0 portal integration across all seven portals

---

## The Story Behind This

I attended Kay Zhu's GTC 2026 session on Long-Horizon Agents and recognized every bottleneck he described in my own system. I came home and built this.

MMC has run mentorship programs for 40,000+ scholars across 120+ countries for five years. The hardest problem was never finding talent. It was maintaining continuity at scale without burning out the humans coordinating it.

**The program team guides people.**  
**Engineering guides progression.**  
**This agent is the infrastructure answer.**

---

## Built By

**Chanel Power**  
Senior ML Engineer · Founder & CEO, Mentor Me Collective  
Genspark Builder Grant Recipient · GTC 2026  
GitHub: [@itsChanelML](https://github.com/itsChanelML)  
LinkedIn: [linkedin.com/in/powerc1](https://linkedin.com/in/powerc1)