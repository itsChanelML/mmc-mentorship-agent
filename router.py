# router.py
# The decision engine — reads signal results and decides what action to take
# Maps directly to MMC's Phase Highlights table from the engineering document

"""
router.py — The Decision Engine

Maps signal results to agent actions.
Implements the automation boundary defined in MMC's engineering doc:

AUTOMATED (this file handles):
- State tracking
- Signal-based routing
- Action type determination

HUMAN-GOVERNED (escalations/ and outputs/ folders):
- Readiness interpretation
- Relationship judgment  
- Final send decision on all outreach

No message is ever sent automatically. The agent drafts.
The coordinator decides.
"""

def decide_action(state, signal_result):
    """
    Takes a scholar's state and signal results.
    Returns the action the agent should take next.
    
    Action types:
    - NO_ACTION: Scholar is on track, monitor only
    - SEND_REMINDER: Gentle nudge for minor gaps
    - SEND_ONBOARDING_PROMPT: Orange path — push toward completion
    - GENERATE_DRIFT_ALERT: Active scholar drifting — draft outreach
    - GENERATE_ESCALATION: High risk — write escalation brief for coordinator
    """
    
    path = state.get("path")
    lifecycle_state = state.get("lifecycle_state")
    flags = signal_result.get("flags", [])
    risk_score = signal_result.get("score", 0)
    escalation_required = signal_result.get("escalation_required", False)
    cycle_count = state.get("cycle_count", 0)

    # ── ESCALATION — highest priority ─────────────────────────────
    if escalation_required:
        return {
            "action": "GENERATE_ESCALATION",
            "reason": f"Risk score {risk_score} with flags: {flags}",
            "priority": "HIGH",
            "nemotron_task": "escalation_brief"
        }

    # ── ORANGE PATH — onboarding support ──────────────────────────
    if path == "Orange":
        if "ONBOARDING_INCOMPLETE" in flags:
            return {
                "action": "SEND_ONBOARDING_PROMPT",
                "reason": "Scholar has not completed onboarding",
                "priority": "MEDIUM",
                "nemotron_task": "onboarding_reminder"
            }
        if "NO_MEETING_SCHEDULED" in flags:
            return {
                "action": "SEND_REMINDER",
                "reason": "No mentor meeting scheduled yet",
                "priority": "MEDIUM",
                "nemotron_task": "meeting_reminder"
            }

    # ── GREEN PATH ACTIVE — drift detection ───────────────────────
    if path == "Green" and lifecycle_state == "Active":
        
        if "CADENCE_BREACH" in flags or "RESPONSE_GAP" in flags:
            return {
                "action": "GENERATE_DRIFT_ALERT",
                "reason": f"Participation drift detected: {flags}",
                "priority": "HIGH",
                "nemotron_task": "drift_alert"
            }

        if "ARTIFACT_GAP" in flags:
            return {
                "action": "SEND_REMINDER",
                "reason": "No artifact submitted in 7+ days",
                "priority": "MEDIUM",
                "nemotron_task": "artifact_reminder"
            }

        if "STALLED_PROGRESSION" in flags:
            return {
                "action": "SEND_REMINDER",
                "reason": "Scholar stalled — reflection not submitted",
                "priority": "MEDIUM",
                "nemotron_task": "progress_reminder"
            }

    # ── NO ACTION NEEDED ──────────────────────────────────────────
    return {
        "action": "NO_ACTION",
        "reason": "Scholar is on track — monitor only",
        "priority": "LOW",
        "nemotron_task": None
    }


def run_router(participants_with_signals):
    """
    Takes signal results and returns routing decisions for all scholars.
    """
    print("\n" + "="*50)
    print("MMC ROUTER — DECISIONS")
    print("="*50)

    decisions = []

    for participant in participants_with_signals:
        state = participant["state"]
        signal_result = participant["signal_result"]
        
        decision = decide_action(state, signal_result)

        print(f"\nScholar: {state['name']}")
        print(f"  Action:   {decision['action']}")
        print(f"  Priority: {decision['priority']}")
        print(f"  Reason:   {decision['reason']}")

        decisions.append({
            "id": state["id"],
            "name": state["name"],
            "decision": decision
        })

    print("\n" + "="*50)
    print(f"ROUTING COMPLETE — {len(decisions)} decisions made")
    print("="*50 + "\n")

    return decisions