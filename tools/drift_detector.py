# tools/drift_detector.py
# Calls Nemotron to generate personalized outreach for scholars showing drift
# or Orange path scholars who need onboarding support
# Draft is written to outputs/ for coordinator review — never sent automatically

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

    prompt = f"""You are a warm, encouraging program coordinator 
at Mentor Me Collective, a nonprofit mentorship program for 
first-generation professionals.

A scholar has started but not completed their onboarding. 
Write a personalized, encouraging message to help them 
across the finish line.

SCHOLAR PROFILE:
- Name: {name}
- Onboarding Complete: {onboarding_percent}%
- Why they joined MMC: {application.get('why_mmc', 'Not provided')}
- Career Vision: {application.get('career_vision', 'Not provided')}
- What they hope to gain: {application.get('expectations', 'Not provided')}
- Hobbies: {', '.join(application.get('hobbies', []))}
- Their anticipated challenges: {application.get('anticipated_challenges', 'Not provided')}
- Mentorship areas they selected: {', '.join(application.get('mentorship_areas', []))}

SITUATION:
Active flags: {', '.join(flags)}

Write a short, warm outreach message (under 200 words) that:
1. Addresses them by first name
2. References something specific from their application 
   so they know this is personal not automated
3. Reminds them what's waiting on the other side 
   of completing onboarding — their mentor match
4. Gives them one simple, specific next step
5. Closes with genuine encouragement

Tone: Warm, human, never corporate. 
Like a message from someone who genuinely wants them to succeed.
Do NOT mention risk scores or flags."""

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
        print(f"  Full response: {response}")
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

    # Update scholar actions log
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

    prompt = f"""You are a warm program coordinator at Mentor Me Collective,
a nonprofit mentorship program for first-generation professionals.

A scholar who was active has gone quiet. Write a genuine, 
personal re-engagement message.

SCHOLAR PROFILE:
- Name: {name}
- Days since last response: {days_silent}
- Why they joined MMC: {application.get('why_mmc', 'Not provided')}
- Career Vision: {application.get('career_vision', 'Not provided')}
- Challenges they anticipated: {application.get('anticipated_challenges', 'Not provided')}
- Success definition: {application.get('success_definition', 'Not provided')}

Write a re-engagement message (under 150 words) that:
1. Opens with genuine care — not a reminder
2. Acknowledges that life gets busy without being condescending
3. References their career vision specifically so they 
   feel remembered as a person
4. Offers a simple, low-pressure next step
5. Reminds them their mentor is still there for them

Tone: Like a friend who noticed you went quiet 
and genuinely wants to check in.
Do NOT mention risk scores, flags, or automated systems."""

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