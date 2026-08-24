#!/usr/bin/env python3
"""Generate TTS audio clips for each message × spray-time variant."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MESSAGES_PATH = Path("artefacts/messages.json")
AUDIO_DIR = Path("artefacts/audio")
INDEX_PATH = AUDIO_DIR / "index.json"

SPRAY_PHRASES = [
    "aaj shaam",
    "kal subah 6 baje",
    "mangalvaar subah",
    "parso subah",
]

PLACEHOLDER = "SPRAY_WINDOW"


def _slug(phrase: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", phrase.lower()).strip("_")


def _synthesise_edge(text: str, out_path: Path) -> None:
    subprocess.run(
        [
            sys.executable, "-m", "edge_tts",
            "--voice", "hi-IN-SwaraNeural",
            "--text", text,
            "--write-media", str(out_path),
        ],
        check=True,
        timeout=30,
    )


def _synthesise_bhashini(text: str, out_path: Path) -> None:
    from adapters.bhashini import synthesize
    data = synthesize(text)
    out_path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TTS audio for messages")
    parser.add_argument(
        "--backend", choices=["edge", "bhashini"], default="edge",
        help="TTS backend (default: edge)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate files even if they already exist",
    )
    args = parser.parse_args()

    messages = json.loads(MESSAGES_PATH.read_text(encoding="utf-8"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    synth = _synthesise_edge if args.backend == "edge" else _synthesise_bhashini
    index: dict[str, dict[str, str]] = {}
    generated = 0
    skipped = 0

    for key, text in messages.items():
        index[key] = {}

        if PLACEHOLDER not in text:
            # No spray-window variant — synthesise the original once
            filename = f"{key}.mp3"
            out_path = AUDIO_DIR / filename
            if out_path.exists() and not args.force:
                skipped += 1
            else:
                synth(text, out_path)
                generated += 1
            index[key]["original"] = filename
            continue

        for phrase in SPRAY_PHRASES:
            slug = _slug(phrase)
            filename = f"{key}__{slug}.mp3"
            out_path = AUDIO_DIR / filename

            if out_path.exists() and not args.force:
                skipped += 1
            else:
                filled = text.replace(PLACEHOLDER, phrase)
                synth(filled, out_path)
                generated += 1

            index[key][slug] = filename

    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    total_size = sum(f.stat().st_size for f in AUDIO_DIR.glob("*.mp3")) / (1024 * 1024)
    print(f"Generated: {generated}  Skipped: {skipped}  Total: {total_size:.2f} MB")
    print(f"Index written to {INDEX_PATH}")


if __name__ == "__main__":
    main()
