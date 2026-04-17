"""
tools/intake_monitor.py — Application Intake Monitor

Handles the first phase of the MMC scholar and mentor lifecycle:
Applicant → Evaluated → Path Assigned

Monitors TWO intake streams simultaneously:
- Mentee applications: scholars seeking mentorship
- Mentor applications: professionals offering to mentor

Engineering responsibilities (from MMC End-to-End Experience Summary):
- Track submissions and detect incomplete applications
- Automate reminders within predictable timing windows
- Enforce deadlines without human memory
- Route participants to Green / Orange / No-Fit paths

Architecture note: Rules detect. Nemotron communicates.
Coordinator makes all final routing decisions.
"""

import json
import os
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

# ── INTAKE THRESHOLDS ─────────────────────────────────────────────
REMINDER_THRESHOLD_DAYS = 3
ABANDONED_THRESHOLD_DAYS = 7

# ── REQUIRED FIELDS ───────────────────────────────────────────────
# Based on actual MMC application forms
# Only hard-required fields that block a match from happening

MENTEE_REQUIRED_FIELDS = [
    # Identity
    "name",
    "email",
    "linkedin",
    # Current situation
    "application.current_status",
    "application.occupation_profile",
    "application.industries_of_interest",
    "application.years_experience",
    "application.education",
    # Mentorship needs
    "application.mentorship_areas",
    "application.preferred_mentor_experience",
    "application.commitment",
    "application.cadence",
    "application.preferred_style",
    "application.session_duration",
    # Availability
    "application.availability",
    "application.availability_time",
    # Goals — needed for matching and personalization
    "application.why_mmc",
    "application.career_vision",
    "application.expectations",
    # Goal dimensions
    "application.goals.mobility",
    "application.goals.novelty",
    "application.goals.experience",
    "application.goals.exposure",
]

MENTOR_REQUIRED_FIELDS = [
    # Identity
    "name",
    "email",
    "linkedin",
    # Professional profile
    "application.occupation_profile",
    "application.industry_profile",
    "application.years_experience",
    "application.education",
    # Mentorship offering
    "application.areas_of_expertise",
    "application.preferred_mentee_profile",
    "application.commitment",
    "application.cadence",
    "application.preferred_style",
    "application.session_duration",
    # Availability
    "application.availability",
    "application.availability_time",
    # Context — needed for matching
    "application.why_mentor",
    "application.expectations",
    # Support dimensions
    "application.how_i_support.mobility",
    "application.how_i_support.novelty",
    "application.how_i_support.experience",
    "application.how_i_support.exposure",
]

# ── FIELD CHECKING ────────────────────────────────────────────────

def check_field(state, field_path):
    """
    Check if a nested field exists and is not empty.
    Supports dot notation: 'application.goals.mobility'
    """
    parts = field_path.split(".")
    current = state
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    # Check for empty values
    if isinstance(current, list):
        return len(current) > 0
    if isinstance(current, str):
        return len(current.strip()) > 0
    return current is not None

def detect_missing_fields(state, required_fields):
    """Returns list of missing required fields."""
    return [f for f in required_fields if not check_field(state, f)]

def score_completeness(state, required_fields):
    """Returns completeness score between 0.0 and 1.0."""
    missing = detect_missing_fields(state, required_fields)
    total = len(required_fields)
    complete = total - len(missing)
    return round(complete / total, 2)

def days_since_interaction(state):
    """Returns days since last interaction. 999 if never."""
    last = state.get("last_interaction_at")
    if not last:
        return 999
    dt = datetime.fromisoformat(last)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days

# ── INTAKE DECISION ───────────────────────────────────────────────

def determine_intake_action(state, required_fields):
    """
    Determines what action the intake monitor should take.

    Actions:
    - NO_ACTION: Complete or recently active, within window
    - SEND_COMPLETION_REMINDER: Missing fields, 3+ days inactive
    - FLAG_ABANDONED: 7+ days inactive, still incomplete
    - FLAG_FOR_EVALUATION: All required fields present
    """
    missing = detect_missing_fields(state, required_fields)
    completeness = score_completeness(state, required_fields)
    days_inactive = days_since_interaction(state)

    if completeness == 1.0:
        return {
            "action": "FLAG_FOR_EVALUATION",
            "completeness": completeness,
            "missing_fields": [],
            "days_inactive": days_inactive,
            "reason": "Application complete — ready for coordinator review"
        }

    if days_inactive >= ABANDONED_THRESHOLD_DAYS:
        return {
            "action": "FLAG_ABANDONED",
            "completeness": completeness,
            "missing_fields": missing,
            "days_inactive": days_inactive,
            "reason": f"No activity for {days_inactive} days — application incomplete"
        }

    if days_inactive >= REMINDER_THRESHOLD_DAYS:
        return {
            "action": "SEND_COMPLETION_REMINDER",
            "completeness": completeness,
            "missing_fields": missing,
            "days_inactive": days_inactive,
            "reason": f"Application {int(completeness * 100)}% complete — reminder needed"
        }

    return {
        "action": "NO_ACTION",
        "completeness": completeness,
        "missing_fields": missing,
        "days_inactive": days_inactive,
        "reason": "Application in progress — within normal window"
    }

# ── NEMOTRON CONTENT GENERATION ───────────────────────────────────

def generate_completion_reminder(state, missing_fields, role_type):
    """
    Calls Nemotron to generate a personalized completion reminder.
    role_type: 'mentee' or 'mentor'
    Written to outputs/ for coordinator review. Never sent automatically.
    """
    name = state.get("name", "there")
    application = state.get("application", {})
    completeness_pct = int(score_completeness(
        state,
        MENTEE_REQUIRED_FIELDS if role_type == "mentee" 
        else MENTOR_REQUIRED_FIELDS
    ) * 100)

    missing_readable = [
        f.replace("application.", "")
         .replace("goals.", "")
         .replace("how_i_support.", "")
         .replace("_", " ")
        for f in missing_fields
    ]

    if role_type == "mentee":
        context = f"""
- Why they applied: {application.get('why_mmc', 'Not yet provided')}
- Career vision: {application.get('career_vision', 'Not yet provided')}
- What they hope to gain: {application.get('expectations', 'Not yet provided')}
"""
        waiting = "your mentor match"
        role_label = "mentee"
    else:
        context = f"""
- Why they want to mentor: {application.get('why_mentor', 'Not yet provided')}
- Their expertise: {', '.join(application.get('areas_of_expertise', []))}
- Their expectations: {application.get('expectations', 'Not yet provided')}
"""
        waiting = "your first mentee match"
        role_label = "mentor"

    prompt = f"""You are a warm program coordinator at Mentor Me Collective,
a nonprofit mentorship program for first-generation professionals.

A {role_label} has started their application but has not finished it.
Write a short, encouraging message to help them complete it.

APPLICANT INFO:
- Name: {name}
- Role: {role_label.capitalize()}
- Application completeness: {completeness_pct}%
- Missing sections: {', '.join(missing_readable)}
{context}

Write a completion reminder (under 175 words) that:
1. Addresses them by first name
2. Acknowledges something specific from what they already shared
   so they know this is personal, not automated
3. Names exactly what sections are still needed
4. Reminds them what is waiting when they finish: {waiting}
5. Gives them a direct link placeholder: [COMPLETE YOUR APPLICATION]
6. Closes with genuine warmth and encouragement

Tone: Warm, personal, never corporate or pushy.
Like a message from someone who genuinely wants them to succeed.
Do NOT mention risk scores, automation, or system flags."""

    print(f"  Calling Nemotron — completion reminder for {name} ({role_type})...")

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        messages=[
            {
                "role": "system",
                "content": f"""You are a compassionate program coordinator 
at a nonprofit mentorship organization. You write warm, encouraging 
messages that make {role_label}s feel welcomed and supported 
through the application process."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=500
    )

    message = response.choices[0].message.content
    if not message:
        message = f"[Nemotron returned empty — review {name} manually]"

    # Write to outputs for coordinator review
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scholar_id = state.get("id", "unknown")
    filename = f"outputs/{scholar_id}_{role_type}_completion_reminder_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"MMC COMPLETION REMINDER — COORDINATOR REVIEW\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Applicant: {name}\n")
        f.write(f"Role: {role_type.capitalize()}\n")
        f.write(f"Completeness: {completeness_pct}%\n")
        f.write(f"Missing: {', '.join(missing_readable)}\n")
        f.write(f"Action required: Review and send if appropriate\n")
        f.write("="*50 + "\n\n")
        f.write(message)

    print(f"  Written to {filename}")
    return message, filename

# ── MAIN MONITOR ──────────────────────────────────────────────────

def run_intake_monitor(
    participants_dir="participants",
    mentors_dir="mentors"
):
    """
    Runs intake monitoring across both mentee and mentor files.
    """
    print("\n" + "="*60)
    print("MMC INTAKE MONITOR — RUNNING")
    print("Monitoring: Mentee Applications + Mentor Applications")
    print("="*60)

    results = []

    # ── MENTEE INTAKE ─────────────────────────────────────────────
    print("\n── MENTEE APPLICATIONS ──────────────────────────────────")

    mentee_states = [
        "Applicant", "Evaluated", "Path Assigned"
    ]

    for filename in sorted(os.listdir(participants_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(participants_dir, filename)
        with open(filepath) as f:
            state = json.load(f)

        lifecycle_state = state.get("lifecycle_state", "")
        if lifecycle_state not in mentee_states:
            continue

        name = state.get("name", "Unknown")
        result = determine_intake_action(state, MENTEE_REQUIRED_FIELDS)

        print(f"\n  Scholar: {name}")
        print(f"  Completeness: {int(result['completeness'] * 100)}%")
        print(f"  Days inactive: {result['days_inactive']}")
        print(f"  Action: {result['action']}")
        print(f"  Reason: {result['reason']}")

        output_file = None
        if result["action"] == "SEND_COMPLETION_REMINDER":
            _, output_file = generate_completion_reminder(
                state, result["missing_fields"], "mentee"
            )

        results.append({
            "name": name,
            "role": "mentee",
            "action": result["action"],
            "completeness": result["completeness"],
            "output_file": output_file
        })

    if not any(r["role"] == "mentee" for r in results):
        print("\n  No mentees currently in intake phase")

    # ── MENTOR INTAKE ─────────────────────────────────────────────
    print("\n── MENTOR APPLICATIONS ──────────────────────────────────")

    if not os.path.exists(mentors_dir):
        print("\n  No mentors directory found")
    else:
        for filename in sorted(os.listdir(mentors_dir)):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(mentors_dir, filename)
            with open(filepath) as f:
                state = json.load(f)

            # Only monitor mentors not yet fully activated
            if state.get("status") == "Active":
                name = state.get("name", "Unknown")
                result = determine_intake_action(
                    state, MENTOR_REQUIRED_FIELDS
                )

                print(f"\n  Mentor: {name}")
                print(f"  Completeness: {int(result['completeness'] * 100)}%")
                print(f"  Action: {result['action']}")
                print(f"  Reason: {result['reason']}")

                output_file = None
                if result["action"] == "SEND_COMPLETION_REMINDER":
                    _, output_file = generate_completion_reminder(
                        state, result["missing_fields"], "mentor"
                    )

                results.append({
                    "name": name,
                    "role": "mentor",
                    "action": result["action"],
                    "completeness": result["completeness"],
                    "output_file": output_file
                })

        if not any(r["role"] == "mentor" for r in results):
            print("\n  No mentors currently in intake phase")

    # ── SUMMARY ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("INTAKE MONITOR COMPLETE")
    print(f"  Total scanned: {len(results)}")
    print(f"  Ready for evaluation: {sum(1 for r in results if r['action'] == 'FLAG_FOR_EVALUATION')}")
    print(f"  Reminders needed: {sum(1 for r in results if r['action'] == 'SEND_COMPLETION_REMINDER')}")
    print(f"  Flagged abandoned: {sum(1 for r in results if r['action'] == 'FLAG_ABANDONED')}")
    print("="*60 + "\n")

    return results

if __name__ == "__main__":
    run_intake_monitor()