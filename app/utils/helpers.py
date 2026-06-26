import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BANGLA_RANGE = re.compile(r"[\u0980-\u09FF]")


def detect_language(text: str) -> str:
    """Detect language: en, bn, or mixed."""
    has_bangla = bool(BANGLA_RANGE.search(text))
    has_latin = bool(re.search(r"[a-zA-Z]{3,}", text))
    if has_bangla and has_latin:
        return "mixed"
    if has_bangla:
        return "bn"
    return "en"


def normalize_text(text: str) -> str:
    return text.lower().strip()


def parse_json_safe(text: str) -> Optional[dict]:
    """Strip markdown fences and parse JSON robustly, handling multi-line Gemini output."""
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip("`\n ")

    # Direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object by brace matching
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end != -1:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try to clean common Gemini issues: trailing commas, single quotes
            cleaned = re.sub(r",\s*}", "}", candidate)
            cleaned = re.sub(r",\s*]", "]", cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    logger.warning("Could not parse JSON from Gemini response: %.200s", text)
    return None

