"""Pure text helpers: Arabic normalisation, wake-word matching and
parsing of LLM replies. No audio or model dependencies, so it is
fully unit-testable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_arabic(text: str) -> str:
    """Lower-case and normalise Arabic spelling variants so that
    different transcriptions of the same word compare equal."""
    text = _DIACRITICS.sub("", text or "")
    text = re.sub("[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    text = _NON_WORD.sub(" ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def contains_wake_word(transcript: str, wake_words: Iterable[str]) -> bool:
    """True if any wake word appears as a whole word in *transcript*."""
    words = set(normalize_arabic(transcript).split())
    return any(normalize_arabic(w) in words for w in wake_words)


def strip_think(text: str) -> str:
    """Remove reasoning blocks emitted by models like DeepSeek-R1.

    Handles a closed ``<think>…</think>`` block and also a dangling
    ``</think>`` (some Ollama versions drop the opening tag)."""
    text = _THINK_BLOCK.sub("", text or "")
    if "</think>" in text.lower():
        text = re.split(r"</think>", text, flags=re.IGNORECASE)[-1]
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


@dataclass
class ParsedReply:
    """Either something to say, or a tool to call."""
    speech: str = ""
    tool: Optional[str] = None
    args: dict = field(default_factory=dict)

    @property
    def is_tool_call(self) -> bool:
        return self.tool is not None


def parse_reply(raw: str) -> ParsedReply:
    """Turn a raw LLM reply into a :class:`ParsedReply`.

    The system prompt asks the model to answer with either plain Arabic
    or a single line ``TOOL: {"name": ..., "args": {...}}``. Anything
    that is not a well-formed tool line is treated as speech, so a
    malformed reply can never trigger an action.
    """
    text = strip_think(raw)
    for line in text.splitlines():
        line = line.strip()
        if not line.upper().startswith("TOOL:"):
            continue
        payload = line[5:].strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            break
        name = data.get("name") if isinstance(data, dict) else None
        args = data.get("args", {}) if isinstance(data, dict) else {}
        if isinstance(name, str) and isinstance(args, dict):
            return ParsedReply(tool=name, args=args)
        break
    # Not a valid tool call: speak it, minus any stray TOOL: line.
    speech = "\n".join(l for l in text.splitlines() if not l.strip().upper().startswith("TOOL:"))
    return ParsedReply(speech=speech.strip())
