"""
NightBite AI — Anthropic Claude Service

Production-safe Claude wrapper:
- Real timeout enforcement via concurrent.futures
- Strict JSON-only responses with schema validation
- Retry with stricter prompt on parse failure
- Full fallback if Claude unavailable
- Never crashes the caller
- Detailed logging so failures are visible
- Modular and swappable for future model upgrades
"""
from __future__ import annotations

import json
import logging
import concurrent.futures
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="claude")
_client = None  # Lazy singleton


def _get_client():
    """Lazily initialize and cache the Anthropic client. Returns None if unavailable."""
    global _client
    if _client is not None:
        return _client

    try:
        import anthropic
        from app.core.config import settings

        if not settings.CLAUDE_API_KEY:
            logger.warning("CLAUDE_API_KEY is not set — Claude AI disabled.")
            return None

        _client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        logger.info(f"✅ Anthropic Claude client initialized (model: {settings.CLAUDE_MODEL})")
        return _client

    except ImportError:
        logger.error("❌ 'anthropic' package not installed. Run: pip install anthropic")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to initialise Anthropic Claude client: {e}")
        return None


def _reset_client():
    """Reset the cached client so it gets re-initialized on next call."""
    global _client
    _client = None


def call_claude_text(
    prompt: str,
    system: str = "You are NightBite Coach, a supportive late-night food health advisor for Indian users.",
    max_tokens: int = 400,
    temperature: float = 0.75,
    timeout_seconds: float = 25.0,
) -> Optional[str]:
    """
    Call Claude for a free-form text response with REAL timeout enforcement.

    Args:
        prompt: User message / main prompt.
        system: System prompt for Claude.
        max_tokens: Max tokens in response.
        temperature: 0.0 (deterministic) to 1.0 (creative).
        timeout_seconds: Hard wall-clock timeout.

    Returns:
        Text reply string, or None on any failure.
    """
    client = _get_client()
    if client is None:
        logger.error("Claude client is None — cannot call API")
        return None

    from app.core.config import settings
    model = settings.CLAUDE_MODEL

    def _do_call() -> str:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    try:
        future = _executor.submit(_do_call)
        result = future.result(timeout=timeout_seconds)
        logger.info(f"✅ Claude text reply ({len(result)} chars): {result[:80]}...")
        return result
    except concurrent.futures.TimeoutError:
        logger.warning(f"⏱️ Claude text call timed out after {timeout_seconds}s")
        future.cancel()
        return None
    except Exception as e:
        logger.error(f"❌ Claude text call failed: {type(e).__name__}: {e}")
        _handle_client_error(e)
        return None


def call_claude_json(
    prompt: str,
    expected_keys: list[str],
    system: str = "You are a JSON-only classification API. Return only valid JSON, no other text.",
    max_tokens: int = 600,
    timeout_seconds: float = 20.0,
) -> Optional[Dict[str, Any]]:
    """
    Call Claude and expect a strict JSON response.

    Args:
        prompt: Full prompt text telling Claude to return JSON only.
        expected_keys: Keys that MUST be present in the response.
        system: Override system prompt.
        max_tokens: Max tokens.
        timeout_seconds: Hard wall-clock timeout.

    Returns:
        Parsed dict if valid, None on any failure.
    """
    client = _get_client()
    if client is None:
        return None

    from app.core.config import settings
    model = settings.CLAUDE_MODEL

    def _do_call() -> str:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,   # Low temp = deterministic JSON
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    try:
        future = _executor.submit(_do_call)
        raw = future.result(timeout=timeout_seconds)
        return _parse_and_validate_json(raw, expected_keys)
    except concurrent.futures.TimeoutError:
        logger.warning(f"⏱️ Claude JSON call timed out after {timeout_seconds}s")
        future.cancel()
        return None
    except Exception as e:
        logger.warning(f"❌ Claude JSON call failed: {type(e).__name__}: {e}")
        _handle_client_error(e)
        return None


def call_claude_json_with_retry(
    prompt: str,
    strict_prompt: str,
    expected_keys: list[str],
    timeout_seconds: float = 20.0,
) -> Optional[Dict[str, Any]]:
    """
    Try Claude with prompt first, then retry with strict_prompt if parsing fails.
    Returns parsed dict if valid on either attempt, None if both fail.
    """
    result = call_claude_json(prompt, expected_keys, timeout_seconds=timeout_seconds)
    if result is not None:
        return result

    logger.info("First Claude attempt failed — retrying with strict prompt.")
    result = call_claude_json(strict_prompt, expected_keys, timeout_seconds=timeout_seconds)
    return result


def call_claude_structured(
    system: str,
    user_message: str,
    expected_keys: list[str],
    max_tokens: int = 800,
    timeout_seconds: float = 30.0,
) -> Optional[Dict[str, Any]]:
    """
    Call Claude with explicit system + user roles and expect JSON.
    Best for complex structured generation like AI Coach responses.
    """
    client = _get_client()
    if client is None:
        return None

    from app.core.config import settings
    model = settings.CLAUDE_MODEL

    def _do_call() -> str:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text.strip()

    try:
        future = _executor.submit(_do_call)
        raw = future.result(timeout=timeout_seconds)
        parsed = _parse_and_validate_json(raw, expected_keys)
        if parsed:
            logger.info(f"✅ Claude structured response OK (keys: {list(parsed.keys())})")
        return parsed
    except concurrent.futures.TimeoutError:
        logger.warning(f"⏱️ Claude structured call timed out after {timeout_seconds}s")
        future.cancel()
        return None
    except Exception as e:
        logger.error(f"❌ Claude structured call failed: {type(e).__name__}: {e}")
        _handle_client_error(e)
        return None


# ── Internal helpers ───────────────────────────────────────────────────────────

def _handle_client_error(e: Exception) -> None:
    """Reset client on auth/config errors so it reinitialises next time."""
    err_str = str(e)
    if any(sig in err_str for sig in ["auth", "API_KEY", "authentication", "401", "403", "404", "not_found", "model_not_found"]):
        logger.warning("Resetting Claude client cache due to auth/model error.")
        _reset_client()


def _parse_and_validate_json(
    raw: str,
    required_keys: list[str],
) -> Optional[Dict[str, Any]]:
    """
    Extract and validate JSON from Claude response.
    Handles markdown fences, leading text, etc.
    """
    if not raw:
        return None

    # Strip markdown code fences
    if "```json" in raw:
        raw = raw.split("```json", 1)[1]
        raw = raw.split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1]
        raw = raw.split("```", 1)[0]

    raw = raw.strip()

    # Find JSON object boundaries
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning(f"No JSON object found in Claude response: {raw[:200]}")
        return None

    json_str = raw[start:end]

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e} | raw: {json_str[:200]}")
        return None

    # Validate required keys
    missing = [k for k in required_keys if k not in parsed]
    if missing:
        logger.warning(f"Claude response missing keys {missing}: {parsed}")
        return None

    return parsed


def health_check(timeout_seconds: float = 10.0) -> dict:
    """Check Claude API connectivity. Returns status dict."""
    from app.core.config import settings

    if not settings.CLAUDE_API_KEY:
        return {"status": "disabled", "reason": "CLAUDE_API_KEY not set"}
    if not settings.ENABLE_LLM_ENHANCEMENT:
        return {"status": "disabled", "reason": "ENABLE_LLM_ENHANCEMENT=false"}

    try:
        result = call_claude_json(
            prompt='Return ONLY this JSON: {"ok": true}',
            expected_keys=["ok"],
            timeout_seconds=timeout_seconds,
        )
        if result and result.get("ok"):
            return {"status": "healthy", "model": settings.CLAUDE_MODEL}
        return {"status": "degraded", "model": settings.CLAUDE_MODEL, "detail": "Unexpected response"}
    except Exception as e:
        return {"status": "unhealthy", "detail": str(e)}
