"""
Shared utilities used across all agent modules.
"""
import json
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

import google.generativeai as genai

# ── LLM model ─────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash"


def call_gemini(prompt: str, max_tokens: int = 1_000) -> str:
    """
    Call Gemini 1.5 Flash and return the response text.
    Configured lazily from settings so the key is read at call time.
    """
    from core.config import settings  # local import avoids circular deps at module load

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    )
    return response.text


# ── JSON extraction ────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    """
    Robustly extract the first JSON object from an LLM response.
    Handles markdown code fences and leading/trailing prose.
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```", "", cleaned)

    # Find outermost { … }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in text: {text[:300]}")
    return json.loads(cleaned[start : end + 1])


# ── Agent log helpers ──────────────────────────────────────────────────────

class Timer:
    """Context-manager based wall-clock timer."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)


def make_log(
    agent: str,
    status: str,
    elapsed_ms: int,
    error: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "agent": agent,
        "status": status,
        "started_at": datetime.utcnow().isoformat(),
        "duration_ms": elapsed_ms,
        "error": error,
        "details": details or {},
    }
