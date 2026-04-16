# tools/escalation_writer.py
# Calls Nemotron via NVIDIA NIM to generate a coordinator escalation brief
# For scholars who are drifting and need human intervention

import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

def generate_escalation_brief(state):
    """
    Takes a scholar's full state and generates a coordinator brief.
    Writes the brief to the escalations/ folder.
    This is a human-review document — the agent drafts, the human acts.
    """

    name = state["name"]
    lifecycle_state = state["lifecycle_state"]
    path = state["path"]
    flags = state["signals"]["risk"]["flags"]
    risk_score = state["signals"]["risk"]["score"]
    days_since_meeting = state["signals"]["engagement"].get(
        "days_since_last_response", "unknown"
    )
    application = state.get("application", {})
    actions_log = state.get("agent_actions_log", [])

    prompt = f"""You are the AI coordinator for Mentor Me Collective, 
a nonprofit mentorship program for first-generation professionals.

A scholar requires urgent coordinator attention. 
Generate a clear, professional escalation brief for the program coordinator.

SCHOLAR PROFILE:
- Name: {name}
- Lifecycle State: {lifecycle_state}
- Path: {path}
- Risk Score: {risk_score}/1.0
- Risk Flags: {', '.join(flags)}
- Days Since Last Response: {days_since_meeting}
- Why they joined MMC: {application.get('why_mmc', 'Not provided')}
- Career Vision: {application.get('career_vision', 'Not provided')}
- Anticipated Challenges: {application.get('anticipated_challenges', 'Not provided')}

PREVIOUS AGENT ACTIONS:
{json.dumps(actions_log, indent=2)}

Generate a coordinator escalation brief with these exact sections:

1. SITUATION SUMMARY (2-3 sentences — what is happening)
2. RISK SIGNALS DETECTED (bullet list of what triggered this)
3. SCHOLAR CONTEXT (1-2 sentences — who this person is and why they matter)
4. RECOMMENDED COORDINATOR ACTIONS (3 specific actions the coordinator should take)
5. SUGGESTED OUTREACH MESSAGE (a warm, personal message the coordinator can send directly to the scholar)

Tone: Professional but warm. This is a person, not a ticket.
Keep the entire brief under 400 words."""

    print(f"  Calling Nemotron for escalation brief — {name}...")

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        messages=[
            {
                "role": "system",
                "content": "You are an expert program coordinator assistant for a nonprofit mentorship organization. You write clear, actionable, human-centered escalation briefs."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=1024
    )

    brief = response.choices[0].message.content

    # Write to escalations folder — human review queue
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scholar_id = state["id"]
    filename = f"escalations/{scholar_id}_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"MMC ESCALATION BRIEF\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Scholar: {name}\n")
        f.write(f"Risk Score: {risk_score}\n")
        f.write(f"Flags: {', '.join(flags)}\n")
        f.write("="*50 + "\n\n")
        f.write(brief)

    # Update scholar's agent actions log
    state["agent_actions_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "ESCALATION_BRIEF_GENERATED",
        "detail": f"Brief written to {filename}"
    })

    print(f"  Escalation brief written to {filename}")
    return brief, filename