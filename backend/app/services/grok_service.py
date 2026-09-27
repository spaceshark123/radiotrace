"""SpaceX AI / xAI Grok: extract severity, description, confidence, and location."""

from __future__ import annotations

import json
import logging
import re

import requests

from app.config import Config

logger = logging.getLogger(__name__)

GROK_SYSTEM_PROMPT = """You are RadioTrace, a public-safety analyst for Atlanta, Georgia police radio.
Given a radio transcript, extract the incident fields described by the response schema.
Do not include markdown or a preamble."""

GROK_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "radio_incident",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["Severe", "Moderate", "Minor"],
                },
                "description": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "location": {"type": "string"},
            },
            "required": ["severity", "description", "confidence", "location"],
            "additionalProperties": False,
        },
    },
}

GROK_MATCH_PROMPT = """You are an Atlanta public-safety dispatcher. 
Given a new radio transcript and a list of active recent incidents, determine if the new transcript belongs to ANY of the existing incidents.
Return ONLY compact JSON with keys:
matched_id (integer ID of the matching incident, or null if it is a brand new incident).
reason (one short sentence explaining why).
Do not include markdown."""


class GrokError(RuntimeError):
    """Raised when the Grok API call or JSON parse fails."""


def _extract_json(text: str | dict) -> dict:
    if isinstance(text, dict):
        return text
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            stripped = stripped[start : end + 1]
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Grok output must be a JSON object", stripped, 0)
    return parsed


def analyze_transcript(transcript: str) -> dict:
    """Call Grok and normalize incident fields from the model output."""
    if not Config.XAI_API_KEY:
        raise GrokError("XAI_API_KEY or SPACEX_AI_API_KEY is not configured")
    if not transcript.strip():
        raise GrokError("Refusing to call Grok with an empty transcript")

    url = f"{Config.XAI_API_BASE.rstrip('/')}/chat/completions"
    body = {
        "model": Config.GROK_MODEL,
        "temperature": 0,
        "max_tokens": 220,
        "response_format": GROK_RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": GROK_SYSTEM_PROMPT},
            {"role": "user", "content": transcript[:4000]},
        ],
    }
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {Config.XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise GrokError("Grok API timed out") from exc
    except requests.RequestException as exc:
        raise GrokError(f"Grok request failed: {exc}") from exc

    if not response.ok:
        raise GrokError(f"Grok returned {response.status_code}: {response.text[:300]}")

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GrokError("Unexpected Grok response shape") from exc

    try:
        parsed = _extract_json(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise GrokError(f"Grok output was not valid JSON: {content[:300]}") from exc

    severity = str(parsed.get("severity", "Unknown"))
    if severity not in {"Severe", "Moderate", "Minor"}:
        severity = "Unknown"
    confidence = parsed.get("confidence", 0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "severity": severity,
        "description": str(parsed.get("description", "")).strip() or "Unspecified incident",
        "confidence": confidence,
        "location": str(parsed.get("location", "")).strip(),
    }

def match_incident(transcript: str, active_incidents: list[dict]) -> int | None:
    """Call Grok to see if an incoming transcript matches any active incident."""
    if not Config.XAI_API_KEY:
        raise GrokError("XAI_API_KEY or SPACEX_AI_API_KEY is not configured")
    if not transcript.strip() or not active_incidents:
        return None

    # Format the active incidents compactly for the LLM prompt
    formatted_incidents = [
        {
            "id": inc["id"],
            "description": inc["type"][0]["description"] if inc.get("type") else "Unknown",
            "location": inc["location"][0]["google_maps"] if inc.get("location") else "Unknown"
        }
        for inc in active_incidents
    ]

    user_payload = json.dumps({
        "new_transcript": transcript[:4000],
        "active_incidents": formatted_incidents
    })

    url = f"{Config.XAI_API_BASE.rstrip('/')}/chat/completions"
    body = {
        "model": Config.GROK_MODEL,
        "temperature": 0,
        "max_tokens": 100,
        "messages": [
            {"role": "system", "content": GROK_MATCH_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    }

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {Config.XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning(f"Grok matching request failed, falling back to new incident: {exc}")
        return None

    if not response.ok:
        return None

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        matched_id = parsed.get("matched_id")
        
        # Ensure the matched ID actually exists in our active list
        if matched_id is not None:
            matched_id = int(matched_id)
            valid_ids = {inc["id"] for inc in active_incidents}
            if matched_id in valid_ids:
                return matched_id
    except Exception as exc:
        logger.warning(f"Failed to parse Grok match response: {exc}")

    return None