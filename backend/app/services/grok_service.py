"""SpaceX AI / xAI Grok: extract severity, description, confidence, and location."""

from __future__ import annotations

import json
import logging
import re

import requests

from app.config import Config

logger = logging.getLogger(__name__)

GROK_SYSTEM_PROMPT = """You are RadioTrace, a public-safety analyst for Atlanta, Georgia police radio.
Given a radio transcript, return ONLY compact JSON with keys:
severity (one of Severe, Moderate, Minor),
description (one short sentence),
confidence (number 0-1),
location (street, intersection, or neighborhood in Atlanta, GA; empty string if unknown).
Do not include markdown. Save tokens: no preamble."""


class GrokError(RuntimeError):
    """Raised when the Grok API call or JSON parse fails."""


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            stripped = stripped[start : end + 1]
    return json.loads(stripped)


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
