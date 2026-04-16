# agent.py
# The MMC Long-Horizon Mentorship Agent
# Program Manager + Program Coordinator running as a persistent agent
# Built on Nemotron via NVIDIA NIM — Genspark Builder Grant, GTC 2026
#
# Implements Kay Zhu's three Long-Horizon bottleneck solutions:
# 1. MEMORY: Participant files = hard disk. Context = RAM.
# 2. ACTION: Composable tools called by orchestrator
# 3. CONTINUITY: External loop — restartable, checkpointable

import json
import os
import time
from datetime import datetime
from signals import load_participant, save_participant, run_signal_monitor, monitor_signals
from router import decide_action
from tools.escalation_writer import generate_escalation_brief
from tools.drift_detector import generate_onboarding_prompt, generate_drift_alert

PARTICIPANTS_DIR = "participants"
CHECKPOINT_FILE = "checkpoint.json"

def load_all_participants():
    """Load all participant files from hard disk."""
    participants = []
    for filename in os.listdir(PARTICIPANTS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(PARTICIPANTS_DIR, filename)
            state = load_participant(filepath)
            participants.append((filepath, state))
    return participants

def checkpoint(cycle_number, results):
    """
    Write cycle state to disk.
    If agent crashes or restarts, it knows exactly where it left off.
    This is the continuity solution from the Genspark GTC talk.
    """
    data = {
        "cycle_number": cycle_number,
        "last_run": datetime.now().isoformat(),
        "results": results
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Checkpoint saved — cycle {cycle_number}")

def load_checkpoint():
    """Resume from last checkpoint if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None

def run_cycle(cycle_number):
    """
    One full agent cycle:
    Read all participant files → detect signals → 
    decide action → execute tool → write back to disk
    """
    print("\n" + "="*60)
    print(f"MMC MENTORSHIP AGENT — CYCLE {cycle_number}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    participants = load_all_participants()
    cycle_results = []

    for filepath, state in participants:
        name = state["name"]
        print(f"\n── Processing: {name} ──────────────────────")

        # Step 1: Read hard disk — detect signals
        signal_result = monitor_signals(state)

        # Step 2: Write signals back to hard disk immediately
        state["signals"]["risk"]["score"] = signal_result["score"]
        state["signals"]["risk"]["flags"] = signal_result["flags"]
        state["signals"]["risk"]["escalation_required"] = (
            signal_result["escalation_required"]
        )

        # Step 3: Decide action
        decision = decide_action(state, signal_result)

        print(f"  Signal Score: {signal_result['score']}")
        print(f"  Flags: {signal_result['flags']}")
        print(f"  Action: {decision['action']}")

        # Step 4: Execute the right tool
        output_file = None

        if decision["action"] == "GENERATE_ESCALATION":
            brief, output_file = generate_escalation_brief(state)

        elif decision["action"] == "SEND_ONBOARDING_PROMPT":
            message, output_file = generate_onboarding_prompt(state)

        elif decision["action"] == "GENERATE_DRIFT_ALERT":
            message, output_file = generate_drift_alert(state)

        elif decision["action"] == "NO_ACTION":
            print(f"  Scholar on track — no intervention needed")

        # Step 5: Update cycle count and write everything back to hard disk
        state["cycle_count"] = state.get("cycle_count", 0) + 1

        save_participant(filepath, state)

        cycle_results.append({
            "name": name,
            "action": decision["action"],
            "risk_score": signal_result["score"],
            "output_file": output_file
        })

    # Step 6: Checkpoint — write cycle state to disk
    checkpoint(cycle_number, cycle_results)

    print("\n" + "="*60)
    print(f"CYCLE {cycle_number} COMPLETE")
    print(f"  Scholars processed: {len(cycle_results)}")
    print(f"  Escalations: {sum(1 for r in cycle_results if r['action'] == 'GENERATE_ESCALATION')}")
    print(f"  Prompts generated: {sum(1 for r in cycle_results if r['action'] in ['SEND_ONBOARDING_PROMPT', 'GENERATE_DRIFT_ALERT'])}")
    print(f"  No action needed: {sum(1 for r in cycle_results if r['action'] == 'NO_ACTION')}")
    print("="*60)

    return cycle_results

def run_agent(max_cycles=1, sleep_seconds=5):
    """
    The external loop — the continuity solution.
    Runs continuously, checkpoints after every cycle.
    Restartable from any point — reads hard disk on every cycle.

    max_cycles=1 for demo mode
    max_cycles=None for production (runs forever)
    sleep_seconds=5 for demo, 86400 for production (24 hours)
    """
    print("\n" + "="*60)
    print("MMC LONG-HORIZON MENTORSHIP AGENT")
    print("Powered by Nemotron via NVIDIA NIM")
    print("Genspark Builder Grant — GTC 2026")
    print("="*60)

    # Check for existing checkpoint
    existing = load_checkpoint()
    if existing:
        print(f"\nResuming from checkpoint — last run: {existing['last_run']}")
        start_cycle = existing["cycle_number"] + 1
    else:
        print("\nNo checkpoint found — starting fresh")
        start_cycle = 1

    cycle_number = start_cycle
    
# THE CONTINUITY SOLUTION
# Traditional agents fail on long tasks because a single session
# can't hold everything. This loop solves that:
# - Reads from disk at start of every cycle (not from memory)
# - Writes to disk after every action (not at end of session)
# - Checkpoint survives crashes, restarts, context overflow
# - In production: sleep_seconds=86400 runs this every 24 hours
# "Tight loops beat big plans." — Kay Zhu, GTC 2026

    while True:
        results = run_cycle(cycle_number)
        
        if max_cycles and cycle_number >= max_cycles:
            print(f"\nDemo complete — {cycle_number} cycle(s) run")
            print("In production this loop runs every 24 hours")
            print("Set max_cycles=None to run continuously")
            break

        print(f"\nNext cycle in {sleep_seconds} seconds...")
        time.sleep(sleep_seconds)
        cycle_number += 1

if __name__ == "__main__":
    run_agent(max_cycles=1)