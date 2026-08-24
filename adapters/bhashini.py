"""Bhashini TTS adapter — wraps the Bhashini API for Hindi synthesis."""

from __future__ import annotations

import json
from pathlib import Path

import requests

BHASHINI_API_URL = "https://tts-api.bhashini.gov.in/api/v1/synthesize"
REQUEST_TIMEOUT = 30


def synthesize(text: str, voice: str = "hi-IN-SwaraNeural") -> bytes:
    """Synthesize Hindi speech from text. Returns MP3 bytes."""
    resp = requests.post(
        BHASHINI_API_URL,
        json={"text": text, "voice": voice},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Bhashini returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    return resp.content
