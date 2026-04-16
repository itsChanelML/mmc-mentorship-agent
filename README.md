# MMC Long-Horizon Mentorship Agent

**Program Manager + Program Coordinator AI for Mentor Me Collective**

Built on `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM.  
Implements the Long-Horizon Agent architecture presented by Kay Zhu (CTO, Genspark) at GTC 2026.  
Built as a Genspark Builder Grant recipient — 1 of 300 selected globally.

---

## The Problem

Mentor Me Collective runs a mentorship program for first-generation 
professionals across 120+ countries. At scale, program continuity 
depends on human memory:

- Did this scholar complete onboarding?
- Has this mentor-mentee pair met this week?
- Which scholars are silently drifting toward dropout?

**When progression depends on human memory, people fall through the cracks.**

This agent replaces reliance on human memory with persistent, 
signal-driven lifecycle management — running continuously across 
hours and days, not just when someone is logged in.

---

## The Architecture

This project implements Kay Zhu's three Long-Horizon Agent 
bottleneck solutions from GTC 2026 (Track S82413):

### 1. Memory — Context is RAM. Files are your Hard Disk.

Every scholar has a persistent JSON file. The agent reads it at 
the start of every cycle, acts on it, and writes results back 
immediately. No state lives only in context. The agent can crash, 
restart, and continue exactly where it left off.
participants/
├── scholar_green.json    # Active, on track
├── scholar_orange.json   # Orange path, onboarding incomplete
└── scholar_risk.json     # Active, participation drift detected

### 2. Action — Composable Tools, Not Monolithic Prompts

Each coordinator responsibility is a composable tool that does 
one thing and returns structured output. The LLM orchestrates. 
It does not carry all the data.
tools/
├── escalation_writer.py  # Nemotron generates coordinator briefs
├── drift_detector.py     # Nemotron generates re-engagement messages
└── intake_monitor.py     # Tracks submissions, detects incomplete applications

### 3. Continuity — External Loop with Checkpoint

The agent runs in an external loop. Every cycle: read all 
participant files → detect signals → decide action → execute 
tool → write state back to disk → checkpoint.

```python
# The continuity solution
# "Tight loops beat big plans." — Kay Zhu, GTC 2026
while True:
    results = run_cycle(cycle_number)
    checkpoint(cycle_number, results)
    sleep(86400)  # 24 hours in production
```

---

## The Signal Monitor

Three signal categories mirror MMC's program engineering document:

| Signal Type | Examples | Threshold |
|-------------|----------|-----------|
| Progress | Onboarding completion, artifact submission | 7+ days gap |
| Engagement | Meeting cadence, response behavior | 3-5 days gap |
| Risk | Stalled progression, silent disengagement | Composite score ≥ 0.75 |

---

## The Decision Engine

The router maps signal results to agent actions:

| Risk Score | Path | Action |
|------------|------|--------|
| 0.0 - 0.3 | Any | NO_ACTION — monitor only |
| 0.3 - 0.7 | Orange | SEND_ONBOARDING_PROMPT |
| 0.7 - 1.0 | Green Active | GENERATE_DRIFT_ALERT |
| ≥ 0.75 | Green Active | GENERATE_ESCALATION |

---

## What Nemotron Does

Rules detect signals. Nemotron generates human-centered content.

**Escalation Brief** — for scholars showing participation drift:
- Situation summary
- Risk signals detected
- Scholar context from their application
- Three specific coordinator actions
- Personalized outreach message the coordinator can send

**Onboarding Prompt** — for Orange path scholars:
- References specific details from their application
- Acknowledges their career vision personally
- Gives one specific, low-friction next step
- Closes with genuine encouragement

All outputs go to `escalations/` or `outputs/` for coordinator 
review. **No message is ever sent automatically.**  
The agent drafts. The coordinator decides.

---

## The Automation Boundary

Based on MMC's End-to-End Experience Summary engineering document:

**Agent governs:**
- State tracking across the full lifecycle
- Signal detection and risk scoring
- Action routing and document generation
- Checkpoint and continuity management

**Humans govern:**
- Readiness interpretation
- Relationship judgment
- Conflict resolution
- Final send decision on all outreach

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
# Edit .env and add: NVIDIA_API_KEY=nvapi-your-key-here

# Run one cycle
python3 agent.py
```

**Expected output:**
MMC LONG-HORIZON MENTORSHIP AGENT
Powered by Nemotron via NVIDIA NIM
Genspark Builder Grant — GTC 2026
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
CYCLE 1 COMPLETE
Scholars processed: 3
Escalations: 1
Prompts generated: 1
No action needed: 1

---

## Stack

| Layer | Tool |
|-------|------|
| Intelligence | nvidia/llama-3.3-nemotron-super-49b-v1.5 |
| Inference | NVIDIA NIM API |
| Agent Runtime | Python |
| Memory | JSON file system (hard disk pattern) |
| Orchestration | Custom external loop with checkpoint |
| Deployment | Local / Cloud Run ready |

---

## What's Next

This is V1 — a working prototype demonstrating the full 
Long-Horizon architecture. V2 (production on Google Cloud) adds:

- Real scholar data with privacy handling
- Google Meet and Calendar API integration for live scheduling
- BigQuery telemetry for government compliance reporting
- Vertex AI for at-risk prediction model
- Cloud Scheduler for automated 24-hour cycles
- MMC 2.0 portal integration

---

## The Story Behind This

I attended Kay Zhu's GTC 2026 session on Long-Horizon Agents 
and recognized every bottleneck he described in my own system. 
I came home and built this.

MMC has run mentorship programs for 40,000+ scholars across 
120+ countries for five years. The hardest problem was never 
finding talent. It was maintaining continuity at scale without 
burning out the humans coordinating it.

This agent is the infrastructure answer to that problem.

---

## Built By

**Chanel Power**  
Senior ML Engineer · Founder & CEO, Mentor Me Collective  
Genspark Builder Grant Recipient · GTC 2026  
GitHub: [@itsChanelML](https://github.com/itsChanelML)  
LinkedIn: [linkedin.com/in/powerc1](https://linkedin.com/in/powerc1)