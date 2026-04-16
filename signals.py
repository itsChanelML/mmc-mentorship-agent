"""
signals.py — The Nervous System

Monitors three signal categories across all participant files:
- Progress signals: forward movement through the lifecycle
- Engagement signals: active participation indicators  
- Risk signals: early warning of potential disengagement

Based on MMC's End-to-End Experience Summary engineering document.
Signal thresholds are derived from real program data:
- Cadence breach: > 5 days without meeting (MMC minimum standard)
- Response gap: > 3 days without response
- Stalled progression: > 14 days in Active state without reflection

Architecture note: This module is rules-based and deterministic.
Nemotron is only called downstream when human-centered content
generation is required. Rules for detection, AI for communication.
"""

# signals.py
# The nervous system — reads every participant file and scores their risk
# Based on MMC's three signal categories: Progress, Engagement, Risk

import json
import os
from datetime import datetime, timezone


def load_participant(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def save_participant(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def days_since(timestamp_str):
    if timestamp_str is None:
        return 999  # null = never happened = maximum risk
    dt = datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - dt).days


def monitor_signals(state):
    """
    Reads a participant's state and returns a risk assessment.
    Three signal categories mirror MMC's engineering document exactly:
    - Progress signals: forward movement
    - Engagement signals: active participation
    - Risk signals: potential disengagement
    """
    flags = []
    progress = state["signals"]["progress"]
    engagement = state["signals"]["engagement"]
    lifecycle_state = state["lifecycle_state"]

    # ── PROGRESS SIGNALS ──────────────────────────────────────────

    # Onboarding incomplete
    if not progress["onboarding_complete"]:
        onboarding_percent = progress.get("onboarding_percent", 0)
        if onboarding_percent < 100:
            flags.append("ONBOARDING_INCOMPLETE")

    # No artifact submitted in 7+ days (Active scholars only)
    if lifecycle_state == "Active":
        days_since_artifact = days_since(progress.get("last_artifact_submitted"))
        if days_since_artifact > 7:
            flags.append("ARTIFACT_GAP")

    # Goals not documented after 5+ days in program
    if not progress["goals_documented"]:
        days_in_state = days_since(state["entered_state_at"])
        if days_in_state > 5:
            flags.append("GOALS_NOT_DOCUMENTED")

    # ── ENGAGEMENT SIGNALS ────────────────────────────────────────

    # Cadence breach — no meeting in 5+ days (Active scholars only)
    if lifecycle_state == "Active":
        days_since_meeting = days_since(engagement.get("last_meeting_at"))
        if days_since_meeting > 5:
            flags.append("CADENCE_BREACH")

    # Response gap — no response in 3+ days
    days_no_response = engagement.get("days_since_last_response", 0)
    if days_no_response > 3:
        flags.append("RESPONSE_GAP")

    # No meeting scheduled (Path Assigned scholars)
    if lifecycle_state == "Path Assigned":
        if engagement.get("meetings_this_month", 0) == 0:
            flags.append("NO_MEETING_SCHEDULED")

    # ── RISK SCORING ──────────────────────────────────────────────

    # Stalled progression — in same state too long
    days_in_state = days_since(state["entered_state_at"])

    if lifecycle_state == "Active" and days_in_state > 14:
        if not state["milestones"].get("reflection_submitted"):
            flags.append("STALLED_PROGRESSION")

    if lifecycle_state == "Path Assigned" and days_in_state > 7:
        if not progress["onboarding_complete"]:
            flags.append("STALLED_IN_ONBOARDING")

    # Calculate risk score — each flag adds weight
    flag_weights = {
        "ONBOARDING_INCOMPLETE": 0.2,
        "ARTIFACT_GAP": 0.2,
        "GOALS_NOT_DOCUMENTED": 0.15,
        "CADENCE_BREACH": 0.25,
        "RESPONSE_GAP": 0.2,
        "NO_MEETING_SCHEDULED": 0.2,
        "STALLED_PROGRESSION": 0.25,
        "STALLED_IN_ONBOARDING": 0.2,
    }

    risk_score = min(sum(flag_weights.get(f, 0.1) for f in flags), 1.0)  # cap at 1.0

    escalation_required = (risk_score >= 0.75 and state.get("path") != "Orange")

    return {
        "flags": flags,
        "score": round(risk_score, 2),
        "escalation_required": escalation_required,
    }


def run_signal_monitor():
    """
    Runs signal monitoring across all participants.
    Reads each file, scores risk, writes results back to hard disk.
    """
    participants_dir = "participants"
    results = []

    print("\n" + "=" * 50)
    print("MMC SIGNAL MONITOR — CYCLE RUNNING")
    print("=" * 50)

    for filename in os.listdir(participants_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(participants_dir, filename)
        state = load_participant(filepath)

        # Run signal detection
        signal_result = monitor_signals(state)

        # Write results back to hard disk immediately
        state["signals"]["risk"]["score"] = signal_result["score"]
        state["signals"]["risk"]["flags"] = signal_result["flags"]
        state["signals"]["risk"]["escalation_required"] = signal_result[
            "escalation_required"
        ]
        save_participant(filepath, state)

        # Report
        print(f"\nScholar: {state['name']}")
        print(f"  Path:          {state['path']}")
        print(f"  State:         {state['lifecycle_state']}")
        print(f"  Risk Score:    {signal_result['score']}")
        print(f"  Flags:         {signal_result['flags']}")
        print(f"  Escalate:      {signal_result['escalation_required']}")

        results.append(
            {
                "id": state["id"],
                "name": state["name"],
                "risk_score": signal_result["score"],
                "flags": signal_result["flags"],
                "escalation_required": signal_result["escalation_required"],
            }
        )

    print("\n" + "=" * 50)
    print(f"MONITOR COMPLETE — {len(results)} scholars scanned")
    print("=" * 50 + "\n")

    return results


if __name__ == "__main__":
    run_signal_monitor()
