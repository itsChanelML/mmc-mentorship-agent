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

    from utils import load_prompt, format_list, format_log

    prompt = load_prompt("escalation_brief", {
        "name": name,
        "lifecycle_state": lifecycle_state,
        "path": path,
        "risk_score": risk_score,
        "flags": format_list(flags),
        "days_since_response": days_since_meeting,
        "why_mmc": application.get("why_mmc", "Not provided"),
        "career_vision": application.get("career_vision", "Not provided"),
        "anticipated_challenges": application.get(
            "anticipated_challenges", "Not provided"
        ),
        "agent_actions_log": format_log(actions_log)
    })

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