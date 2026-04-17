"""
utils.py — Shared utilities for the MMC Mentorship Agent

Prompt loader: reads prompt templates from prompts/ folder
and fills in variables using Python's str.format_map()

Usage:
    from utils import load_prompt
    
    prompt = load_prompt("escalation_brief", {
        "name": "Sofia Torres",
        "risk_score": 0.9,
        ...
    })
"""

import os

PROMPTS_DIR = "prompts"

def load_prompt(template_name, variables=None):
    """
    Loads a prompt template from prompts/ folder.
    Fills in {variable} placeholders with provided values.
    
    Args:
        template_name: filename without .txt extension
        variables: dict of {placeholder: value} pairs
    
    Returns:
        Filled prompt string ready to send to Nemotron
    """
    filepath = os.path.join(PROMPTS_DIR, f"{template_name}.txt")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Prompt template not found: {filepath}\n"
            f"Available templates: {os.listdir(PROMPTS_DIR)}"
        )
    
    with open(filepath, "r") as f:
        template = f.read()
    
    if variables:
        # Use format_map so missing keys don't crash — 
        # they stay as {placeholder} in the output
        try:
            return template.format_map(variables)
        except Exception as e:
            print(f"  Warning: prompt formatting issue — {e}")
            return template
    
    return template


def format_list(items, default="Not provided"):
    """Formats a list for prompt insertion."""
    if not items:
        return default
    if isinstance(items, list):
        return ", ".join(str(i) for i in items)
    return str(items)


def format_log(log_entries, default="No previous actions"):
    """Formats agent action log for prompt insertion."""
    if not log_entries:
        return default
    lines = []
    for entry in log_entries:
        timestamp = entry.get("timestamp", "")
        action = entry.get("action", "")
        detail = entry.get("detail", "")
        lines.append(f"- [{timestamp}] {action}: {detail}")
    return "\n".join(lines)