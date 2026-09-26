"""Local audio heuristics so blank/silence clips skip the LLM."""

from __future__ import annotations


def is_blank_audio(
    data: bytes,
    min_bytes: int = 2048,
    min_unique_bytes: int = 8,
) -> bool:
    """
    Return True when the clip is too small or too uniform to contain speech.

    MP3 frames still contain some entropy, so a near-constant payload is treated
    as silence / empty recording. This avoids Grok calls on dead air.
    """
    if not data or len(data) < min_bytes:
        return True
    payload = data[100:] if len(data) > 100 else data
    unique = len(set(payload[:4000]))
    return unique < min_unique_bytes
