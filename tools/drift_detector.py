# tools/drift_detector.py
# Calls Nemotron to generate personalized outreach for scholars showing drift
# or Orange path scholars who need onboarding support
# Draft is written to outputs/ for coordinator review — never sent automatically

import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from utils import load_prompt, format_list

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

def generate_onboarding_prompt(state):
    """
    For Orange path scholars who haven't completed onboarding.
    Generates a warm, personalized nudge based on their application.
    """

    name = state["name"]
    application = state.get("application", {})
    onboarding_percent = state["signals"]["progress"].get(
        "onboarding_percent", 0
    )
    flags = state["signals"]["risk"]["flags"]

    prompt = load_prompt("onboarding_reminder", {
        "name": name,
        "onboarding_percent": onboarding_percent,
        "missing_sections": format_list(
            [f.replace("application.", "").replace("_", " ") for f in flags]
        ),
        "why_mmc": application.get("why_mmc", "Not provided"),
        "career_vision": application.get("career_vision", "Not provided"),
        "expectations": application.get("expectations", "Not provided"),
        "hobbies": format_list(application.get("hobbies", [])),
        "anticipated_challenges": application.get(
            "anticipated_challenges", "Not provided"
        ),
        "mentorship_areas": format_list(
            application.get("mentorship_areas", [])
        )
    })

    print(f"  Calling Nemotron for onboarding prompt — {name}...")

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        messages=[
            {
                "role": "system",
                "content": """You are a compassionate program coordinator 
at a nonprofit mentorship organization serving first-generation 
professionals. You write warm, personal messages that make 
scholars feel seen and supported."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=800
    )

    message = response.choices[0].message.content

    if not message:
        print(f"  WARNING: Nemotron returned empty response")
        message = f"[Nemotron returned empty response — please review scholar {state['name']} manually]"

    # Write to outputs folder for coordinator review
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scholar_id = state["id"]
    filename = f"outputs/{scholar_id}_onboarding_prompt_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"MMC ONBOARDING PROMPT — COORDINATOR REVIEW\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Scholar: {name}\n")
        f.write(f"Onboarding: {onboarding_percent}% complete\n")
        f.write(f"Action: Review and send if appropriate\n")
        f.write("="*50 + "\n\n")
        f.write(message)

    state["agent_actions_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "ONBOARDING_PROMPT_GENERATED",
        "detail": f"Draft written to {filename} — awaiting coordinator review"
    })

    print(f"  Onboarding prompt written to {filename}")
    return message, filename


def generate_drift_alert(state):
    """
    For Active Green path scholars showing participation drift.
    Generates a re-engagement message based on their full profile.
    """

    name = state["name"]
    application = state.get("application", {})
    flags = state["signals"]["risk"]["flags"]
    days_silent = state["signals"]["engagement"].get(
        "days_since_last_response", 0
    )

    prompt = load_prompt("drift_alert", {
        "name": name,
        "days_since_response": days_silent,
        "why_mmc": application.get("why_mmc", "Not provided"),
        "career_vision": application.get("career_vision", "Not provided"),
        "anticipated_challenges": application.get(
            "anticipated_challenges", "Not provided"
        ),
        "success_definition": application.get(
            "success_definition", "Not provided"
        )
    })

    print(f"  Calling Nemotron for drift alert — {name}...")

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        messages=[
            {
                "role": "system",
                "content": """You are a compassionate program coordinator 
who writes re-engagement messages that feel genuinely human, 
never automated or corporate."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=400
    )

    message = response.choices[0].message.content

    # Write to outputs folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scholar_id = state["id"]
    filename = f"outputs/{scholar_id}_drift_alert_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"MMC DRIFT ALERT — COORDINATOR REVIEW\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Scholar: {name}\n")
        f.write(f"Days Silent: {days_silent}\n")
        f.write(f"Flags: {', '.join(flags)}\n")
        f.write(f"Action: Review and send if appropriate\n")
        f.write("="*50 + "\n\n")
        f.write(message)

    state["agent_actions_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "DRIFT_ALERT_GENERATED",
        "detail": f"Draft written to {filename} — awaiting coordinator review"
    })

    print(f"  Drift alert written to {filename}")
    return message, filename