"""
Shared utilities used across all agent modules.

LLM backend: Groq (primary) — fast, generous free tier, no quota issues.
Groq model: llama-3.3-70b-versatile (best quality on free tier)
"""
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Groq model ─────────────────────────────────────────────────────────────
# llama-3.3-70b-versatile: best JSON-following accuracy on Groq free tier.
# Fallback: llama-3.1-8b-instant (smaller, faster, same free tier).
GROQ_MODEL_PRIMARY  = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"


def call_gemini(prompt: str, max_tokens: int = 1_000) -> str:
    """
    Call Groq LLM and return the response text.
    Named call_gemini for backward compatibility with all agent files.

    Uses llama-3.3-70b-versatile (primary) → llama-3.1-8b-instant (fallback
    if primary is rate-limited) → raises if both fail.
    """
    from core.config import settings  # local import avoids circular deps

    api_key = settings.groq_api_key
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env as GROQ_API_KEY=gsk_..."
        )

    from groq import Groq
    client = Groq(api_key=api_key)

    for model in (GROQ_MODEL_PRIMARY, GROQ_MODEL_FALLBACK):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.2,   # low temp → deterministic JSON output
            )
            return completion.choices[0].message.content
        except Exception as exc:
            err_str = str(exc)
            # If rate-limited on primary, try fallback model
            if "429" in err_str or "rate_limit" in err_str.lower():
                logger.warning("Groq 429 on model %s — trying fallback model", model)
                if model == GROQ_MODEL_FALLBACK:
                    # Both models rate-limited, back off and retry once
                    logger.warning("Both Groq models rate-limited — sleeping 60s")
                    time.sleep(60)
                    continue
                continue
            raise  # Non-rate-limit error: propagate immediately

    raise RuntimeError("Groq API unavailable for both primary and fallback models")


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
        self.elapsed_ms = 0   # available immediately, updated on __exit__
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
