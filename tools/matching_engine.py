"""
tools/matching_engine.py — Mentor-Mentee Matching Engine

The most relationship-critical tool in the MMC agent system.
A bad match wastes everyone's time. A great match changes a life.

Matching logic has two layers:
1. RULES: Hard compatibility checks (availability, style, industry)
   Fast, deterministic, no AI needed.
2. NEMOTRON: Deep compatibility analysis and introduction generation
   Reads both full profiles and generates a compatibility score,
   reasoning, and personalized introduction letters for both parties.

Architecture note:
The agent surfaces match recommendations. The coordinator approves.
No match is ever activated without human confirmation.
"""

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

# ── HARD COMPATIBILITY CHECKS ─────────────────────────────────────

def check_availability_overlap(mentee, mentor):
    """
    Checks if mentor and mentee share at least one availability slot.
    Returns True if compatible, False if not.
    """
    mentee_days = mentee["application"].get("availability", "")
    mentor_days = mentor["application"].get("availability", "")

    mentee_times = set(mentee["application"].get("availability_time", []))
    mentor_times = set(mentor["application"].get("availability_time", []))

    # Check day overlap
    days_compatible = (
        mentee_days == mentor_days or
        "Weekdays" in [mentee_days, mentor_days] or
        "Weekends" in [mentee_days, mentor_days]
    )

    # Check time overlap
    times_compatible = len(mentee_times & mentor_times) > 0

    return days_compatible and times_compatible

def check_style_compatibility(mentee, mentor):
    """
    Checks if preferred mentoring styles overlap.
    """
    mentee_styles = set(mentee["application"].get("preferred_style", []))
    mentor_styles = set(mentor["application"].get("preferred_style", []))
    return len(mentee_styles & mentor_styles) > 0

def check_cadence_compatibility(mentee, mentor):
    """
    Checks if preferred cadence matches.
    """
    return (
        mentee["application"].get("cadence") ==
        mentor["application"].get("cadence")
    )

def check_industry_overlap(mentee, mentor):
    """
    Checks if mentor's industry profile overlaps with mentee's interests.
    """
    mentee_industries = set(mentee["application"].get(
        "industries_of_interest", []
    ))
    mentor_industries = set(mentor["application"].get(
        "industry_profile", []
    ))
    return len(mentee_industries & mentor_industries) > 0

def check_expertise_overlap(mentee, mentor):
    """
    Checks if mentor's expertise covers mentee's areas of interest.
    """
    mentee_needs = set(mentee["application"].get("mentorship_areas", []))
    mentor_expertise = set(mentor["application"].get("areas_of_expertise", []))
    overlap = mentee_needs & mentor_expertise
    return len(overlap), list(overlap)

def check_mentor_capacity(mentor):
    """
    Checks if mentor has available slots.
    """
    return mentor.get("availability_slots", 0) > 0

def run_hard_checks(mentee, mentor):
    """
    Runs all hard compatibility checks.
    Returns a compatibility report with pass/fail for each dimension.
    """
    expertise_count, expertise_overlap = check_expertise_overlap(
        mentee, mentor
    )

    checks = {
        "availability": check_availability_overlap(mentee, mentor),
        "style": check_style_compatibility(mentee, mentor),
        "cadence": check_cadence_compatibility(mentee, mentor),
        "industry": check_industry_overlap(mentee, mentor),
        "expertise_overlap_count": expertise_count,
        "expertise_overlap_areas": expertise_overlap,
        "mentor_has_capacity": check_mentor_capacity(mentor)
    }

    # Hard blockers — if any fail, match is not viable
    hard_blockers = []
    if not checks["availability"]:
        hard_blockers.append("AVAILABILITY_MISMATCH")
    if not checks["style"]:
        hard_blockers.append("STYLE_MISMATCH")
    if not checks["mentor_has_capacity"]:
        hard_blockers.append("MENTOR_AT_CAPACITY")

    # Soft signals — reduce quality but don't block
    soft_signals = []
    if not checks["cadence"]:
        soft_signals.append("CADENCE_MISMATCH")
    if not checks["industry"]:
        soft_signals.append("INDUSTRY_GAP")
    if expertise_count == 0:
        soft_signals.append("NO_EXPERTISE_OVERLAP")

    viable = len(hard_blockers) == 0

    return {
        "viable": viable,
        "hard_blockers": hard_blockers,
        "soft_signals": soft_signals,
        "checks": checks
    }

# ── NEMOTRON DEEP MATCHING ────────────────────────────────────────

def generate_match_analysis(mentee, mentor, hard_check_result):
    """
    Calls Nemotron to perform deep compatibility analysis.
    Reads both full profiles and generates:
    1. Compatibility score (0-100)
    2. Match reasoning
    3. Potential challenges
    4. Introduction letter to mentee
    5. Introduction letter to mentor
    """

    mentee_app = mentee.get("application", {})
    mentor_app = mentor.get("application", {})

    prompt = f"""You are an expert mentorship matching coordinator 
at Mentor Me Collective, a nonprofit program for first-generation 
professionals. You are evaluating a potential mentor-mentee match.

Analyze these two profiles deeply and generate a match report.

═══════════════════════════════════════
MENTEE PROFILE: {mentee['name']}
═══════════════════════════════════════
Current Status: {mentee_app.get('current_status', 'N/A')}
Industry Interests: {', '.join(mentee_app.get('industries_of_interest', []))}
Mentorship Areas Needed: {', '.join(mentee_app.get('mentorship_areas', []))}
Career Vision: {mentee_app.get('career_vision', 'N/A')}
Why MMC: {mentee_app.get('why_mmc', 'N/A')}
Anticipated Challenges: {mentee_app.get('anticipated_challenges', 'N/A')}
Success Definition: {mentee_app.get('success_definition', 'N/A')}
Previous Mentoring: {mentee_app.get('previous_mentoring', 'N/A')}
Expectations: {mentee_app.get('expectations', 'N/A')}
Hobbies: {', '.join(mentee_app.get('hobbies', []))}

═══════════════════════════════════════
MENTOR PROFILE: {mentor['name']}
═══════════════════════════════════════
Occupation: {mentor_app.get('occupation_profile', 'N/A')}
Industries: {', '.join(mentor_app.get('industry_profile', []))}
Areas of Expertise: {', '.join(mentor_app.get('areas_of_expertise', []))}
Why They Mentor: {mentor_app.get('why_mentor', 'N/A')}
Previous Experience: {mentor_app.get('previous_experience', 'N/A')}
Expectations of Mentee: {mentor_app.get('expectations', 'N/A')}
How They Support - Mobility: {mentor_app.get('how_i_support', {}).get('mobility', 'N/A')}
How They Support - Experience: {mentor_app.get('how_i_support', {}).get('experience', 'N/A')}
Additional Context: {mentor_app.get('additional_context', 'N/A')}
Hobbies: {', '.join(mentor_app.get('hobbies', []))}

═══════════════════════════════════════
HARD CHECK RESULTS
═══════════════════════════════════════
Viable Match: {hard_check_result['viable']}
Hard Blockers: {hard_check_result['hard_blockers'] or 'None'}
Soft Signals: {hard_check_result['soft_signals'] or 'None'}
Expertise Overlap: {hard_check_result['checks']['expertise_overlap_areas']}

Generate a match report with EXACTLY these sections:

COMPATIBILITY SCORE: [0-100]

MATCH REASONING:
[3-4 sentences on why this pairing works — be specific, 
reference actual details from both profiles]

SHARED FOUNDATION:
[1-2 sentences on the human connection — shared background, 
values, or experience that will build trust quickly]

POTENTIAL CHALLENGES:
[1-2 sentences on what to watch for in this pairing]

COORDINATOR RECOMMENDATION:
[One of: STRONG MATCH / GOOD MATCH / PROCEED WITH CAUTION / DO NOT MATCH]
[One sentence explaining the recommendation]

---MENTEE INTRODUCTION LETTER---
[A warm letter from the MMC coordinator introducing this mentor 
to the mentee. Under 200 words. Personal, specific, excited. 
Reference why this mentor was chosen for THEM specifically.]

---MENTOR INTRODUCTION LETTER---
[A warm letter from the MMC coordinator introducing this mentee 
to the mentor. Under 200 words. Personal, specific. 
Reference why this mentee was selected for THEM specifically.]"""

    print(f"  Calling Nemotron — match analysis: {mentee['name']} + {mentor['name']}...")

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        messages=[
            {
                "role": "system",
                "content": """You are an expert mentorship matching coordinator 
with deep experience pairing first-generation professionals with mentors. 
You understand that a great match is about more than skills — 
it is about shared experience, trust, and human connection.
You write match reports that are specific, honest, and actionable."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,
        max_tokens=1200
    )

    return response.choices[0].message.content

def run_matching_engine(
    participants_dir="participants",
    mentors_dir="mentors"
):
    """
    Runs the full matching engine.
    Finds scholars ready for matching and evaluates all available mentors.
    Writes match reports to outputs/ for coordinator review.
    """
    print("\n" + "="*60)
    print("MMC MATCHING ENGINE — RUNNING")
    print("="*60)

    # Load all mentors
    mentors = []
    if os.path.exists(mentors_dir):
        for filename in os.listdir(mentors_dir):
            if filename.endswith(".json"):
                with open(os.path.join(mentors_dir, filename)) as f:
                    mentors.append(json.load(f))

    print(f"\n  Mentors available: {len(mentors)}")

    results = []

    # Find scholars ready for matching
    for filename in sorted(os.listdir(participants_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(participants_dir, filename)
        with open(filepath) as f:
            scholar = json.load(f)

        # Only match scholars in Path Assigned with no mentor yet
        if scholar.get("lifecycle_state") != "Path Assigned":
            continue
        if scholar.get("mentor_id"):
            continue

        name = scholar.get("name", "Unknown")
        print(f"\n── Finding match for: {name} ──────────────────")

        best_match = None
        best_score = -1
        all_reports = []

        for mentor in mentors:
            # Skip mentors at capacity
            if not check_mentor_capacity(mentor):
                continue

            print(f"\n  Evaluating: {mentor['name']}")

            # Run hard checks first
            hard_result = run_hard_checks(scholar, mentor)

            print(f"  Viable: {hard_result['viable']}")
            if hard_result['hard_blockers']:
                print(f"  Blockers: {hard_result['hard_blockers']}")
                continue

            # Run Nemotron deep analysis
            analysis = generate_match_analysis(scholar, mentor, hard_result)

            # Extract score from response
            score = 0
            for line in analysis.split('\n'):
                if 'COMPATIBILITY SCORE:' in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line)))
                    except:
                        score = 70

            all_reports.append({
                "mentor": mentor,
                "score": score,
                "analysis": analysis,
                "hard_result": hard_result
            })

            if score > best_score:
                best_score = score
                best_match = {
                    "mentor": mentor,
                    "score": score,
                    "analysis": analysis
                }

        # Write match report to outputs
        if best_match:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scholar_id = scholar.get("id", "unknown")
            filename_out = f"outputs/{scholar_id}_match_report_{timestamp}.txt"

            with open(filename_out, "w") as f:
                f.write(f"MMC MATCH REPORT — COORDINATOR REVIEW\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Scholar: {name}\n")
                f.write(f"Recommended Mentor: {best_match['mentor']['name']}\n")
                f.write(f"Compatibility Score: {best_match['score']}/100\n")
                f.write(f"Action: Review and approve match if appropriate\n")
                f.write("="*60 + "\n\n")
                f.write(best_match["analysis"])

                # Add all other evaluations for transparency
                if len(all_reports) > 1:
                    f.write("\n\n" + "="*60)
                    f.write("\nALL MENTOR EVALUATIONS\n")
                    f.write("="*60 + "\n")
                    for report in all_reports:
                        f.write(f"\n{report['mentor']['name']}: {report['score']}/100\n")

            print(f"\n  BEST MATCH: {best_match['mentor']['name']}")
            print(f"  Score: {best_match['score']}/100")
            print(f"  Report written to: {filename_out}")

            results.append({
                "scholar": name,
                "recommended_mentor": best_match["mentor"]["name"],
                "score": best_match["score"],
                "report": filename_out
            })
        else:
            print(f"\n  No viable match found for {name}")
            results.append({
                "scholar": name,
                "recommended_mentor": None,
                "score": 0,
                "report": None
            })

    print("\n" + "="*60)
    print("MATCHING ENGINE COMPLETE")
    print(f"  Scholars evaluated: {len(results)}")
    print(f"  Matches recommended: {sum(1 for r in results if r['recommended_mentor'])}")
    print("="*60 + "\n")

    return results

if __name__ == "__main__":
    run_matching_engine()