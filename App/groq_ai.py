"""Groq LLM integration for Tree Prediction explanations and care instructions.

This module uses Groq's OpenAI-compatible Chat Completions endpoint.
"""

from __future__ import annotations

import os
import re

import requests

# Load environment variables (optional)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


def _get_setting(name: str):
    """Best-effort read from Django settings (works only when configured)."""

    try:
        from django.conf import settings as django_settings

        return getattr(django_settings, name, None)
    except Exception:
        return None


def _resolve_groq_api_url() -> str:
    return os.environ.get("GROQ_API_URL") or _get_setting("GROQ_API_URL") or DEFAULT_GROQ_API_URL


def _resolve_groq_model() -> str:
    return os.environ.get("GROQ_MODEL") or _get_setting("GROQ_MODEL") or DEFAULT_GROQ_MODEL


def _resolve_groq_api_key() -> str | None:
    # Preferred env var
    key = os.environ.get("GROQ_API_KEY")
    legacy = os.environ.get("MISTRAL_API_KEY")
    key = key or (legacy if (legacy and legacy.startswith("gsk_")) else None)

    if key:
        return key

    # Some deployments load the key inside `settings.py` from secret files.
    key = _get_setting("GROQ_API_KEY")
    if key:
        return key

    legacy = _get_setting("MISTRAL_API_KEY")
    return legacy if (legacy and str(legacy).startswith("gsk_")) else None


GROQ_API_URL = _resolve_groq_api_url()
GROQ_MODEL = _resolve_groq_model()
api_key = _resolve_groq_api_key()
client = bool(api_key)


def _groq_chat(prompt: str, *, max_tokens: int, temperature: float) -> str:
    if not api_key:
        raise RuntimeError("No GROQ_API_KEY configured")

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        # Avoid dumping full response body (could include sensitive info in some cases).
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    return data["choices"][0]["message"]["content"]


def generate_tree_explanation(context: dict) -> str:
    """Generate a short, plain-text explanation for the tree prediction."""

    if not client:
        # Fallback to enhanced static explanation when no API key
        species = context["species"]
        county = context["county"]
        season = context["season"]
        survival_rate = context["survival_rate"]
        reason = context["reason"]

        if survival_rate >= 80:
            return (
                f"{species} grows excellently in {county}'s environmental conditions. {reason}. "
                f"Your chosen season ({season}) provides optimal growing conditions with good rainfall and temperature."
            )
        if survival_rate >= 65:
            return (
                f"{species} performs well in {county} with proper care. {reason}. "
                f"Planting in {season} is suitable, though following care instructions closely will maximize success."
            )
        return (
            f"{species} faces challenges in {county} during {season}. {reason}. "
            "Consider alternative species or wait for optimal planting season for better results."
        )

    prompt = f"""
You are an expert Kenyan forestry advisor. Generate a clear, simple explanation for this tree planting prediction:

Species: {context['species']}
Location: {context['county']} County, Kenya
Planting Season: {context['season']}
Survival Rate: {context['survival_rate']:.1f}%
Risk Level: {context['risk_level']}

Base reason: {context['reason']}

Instructions:
- Explain WHY this species works well (or doesn't) in this location and season
- Use simple, practical language that farmers understand
- Focus on environmental factors (rainfall, soil, temperature)
- Keep it under 80 words
- Don't mention percentages, technical terms, or word counts
- Be encouraging but honest
- Don't use markdown formatting or quotes
- Write in plain text only

Example style: "Pine grows well in Meru's highland climate with good rainfall. March planting is ideal because it coincides with long rains when trees establish strong roots."
"""

    content = _groq_chat(prompt, max_tokens=150, temperature=0.3).strip()
    # Remove markdown formatting, quotes, and word count artifacts
    content = content.replace("**", "").replace("*", "")
    content = content.replace('"', "").replace("'", "")
    content = re.sub(r"\(Word count:.*?\)", "", content)
    content = re.sub(r"\(\d+\s*words?\)", "", content)
    return content.strip()


def generate_care_instructions(context: dict) -> list[str]:
    """Generate personalized care instructions as a list of short sentences."""

    if not client:
        base_care = context.get("base_care", [])
        survival_rate = context["survival_rate"]
        method = (context.get("planting_method") or "").strip()

        # Method-specific starter tips
        method_steps: list[str] = []
        if method.lower() in ["seeds", "direct seeding"]:
            method_steps = [
                "Protect the seedbed from birds and heavy rain.",
                "Water lightly but often until seedlings establish.",
                "Thin seedlings early to reduce competition.",
            ]
        elif method.lower() in ["transplant", "transplanting"]:
            method_steps = [
                "Water immediately after transplanting.",
                "Minimize root disturbance during planting.",
                "Provide light shade for the first week if hot.",
            ]
        elif method.lower() in ["seedling"]:
            method_steps = [
                "Mulch around the base to keep moisture.",
                "Water regularly in the first 2–4 weeks.",
                "Protect young trees from livestock.",
            ]

        if survival_rate >= 80:
            steps = method_steps + (base_care or [])
            if not steps:
                steps = [
                    "Water regularly for first month",
                    "Apply mulch around base",
                    "Protect from livestock",
                    "Monitor for pests monthly",
                ]
            return steps[:6]
        if survival_rate >= 65:
            enhanced = ["Follow the care steps closely for best results."] + method_steps + (base_care or [])
            enhanced.append("Check soil moisture weekly.")
            return enhanced[:6]
        return [
            "Consider planting a more suitable species for this period.",
            "If proceeding: water more frequently in the first month.",
            "Mulch heavily and keep weeds away from the base.",
            "Protect from livestock and strong wind.",
            "Inspect twice a week for stress or pests.",
        ][:6]

    base_care = context.get("base_care", [])
    base_care_text = "; ".join(base_care) if base_care else "Standard tree care"
    planting_method = context.get("planting_method", "Auto")

    prompt = f"""
You are an expert Kenyan forestry advisor. Generate personalized care instructions for this tree planting:

Species: {context['species']}
Location: {context['county']} County, Kenya
Planting Season: {context['season']}
Recommended Planting Method: {planting_method}
Survival Rate: {context['survival_rate']:.1f}%
Risk Level: {context['risk_level']}

Base care instructions: {base_care_text}

Instructions:
- Adapt the care instructions for the specific survival rate and risk level
- Make the steps suitable for the planting method (seedling, seeds, transplant)
- For high risk (low survival): emphasize critical care steps
- For medium risk: add extra precautions
- For low risk: provide standard care with confidence
- Use practical, actionable language
- Consider Kenyan farming conditions and resources
- Return as a list of 4-6 specific care steps
- Each step should be one clear, complete sentence
- Don't use markdown formatting or quotes
- Write in plain text only
- Keep each instruction under 100 characters
"""

    care_text = _groq_chat(prompt, max_tokens=200, temperature=0.3).strip()
    care_lines = [line.strip() for line in care_text.split("\n") if line.strip()]

    care_instructions: list[str] = []
    for line in care_lines:
        cleaned = line.lstrip("0123456789.- ").strip()
        if cleaned and len(cleaned) > 10:
            care_instructions.append(cleaned)

    cleaned_instructions: list[str] = []
    for instruction in care_instructions[:6]:
        clean = instruction.replace("**", "").replace("*", "")
        clean = clean.replace('"', "").replace("'", "")
        if len(clean) > 20 and not clean.endswith(("with", "using", "to", "for", "and", "or")):
            cleaned_instructions.append(clean)

    return cleaned_instructions if cleaned_instructions else base_care


def analyze_prediction_with_llm(context: dict) -> float:
    """Deterministic adjustment layer for the numeric prediction.

    Numeric prediction adjustments must be auditable and repeatable.
    Groq/LLMs are used for explanation text, not for changing the score.
    """

    species = context.get("species", "")
    county = context.get("county", "")
    seasonal_bonus = float(context.get("seasonal_bonus") or 0)

    adjustment = 0.0

    if seasonal_bonus > 5:
        adjustment += 5
    elif seasonal_bonus < -5:
        adjustment -= 3

    if species == "Indigenous Mix" and county in ["Meru", "Nyeri", "Kiambu"]:
        adjustment += 10
    elif species in ["Pine", "Cypress"] and county in ["Meru", "Nyeri", "Kiambu"]:
        adjustment += 7
    elif species == "Neem" and county in ["Mombasa", "Kilifi", "Garissa", "Turkana"]:
        adjustment += 8
    elif species == "Eucalyptus":
        adjustment += 2
    elif species in ["Pine", "Cypress"] and county in ["Mombasa", "Kilifi"]:
        adjustment -= 10
    elif species == "Neem" and county in ["Meru", "Nyeri"]:
        adjustment -= 7

    return float(max(-15, min(12, adjustment)))
