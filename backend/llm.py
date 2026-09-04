"""
Shared LLM access for every agent - one ChatGroq instance, reused everywhere,
plus a small helper for getting clean JSON back out of the model.

Also handles Groq's per-minute token rate limits (common on the free tier):
when a call hits a 429, we parse the "try again in Xs" hint Groq returns
and sleep that long before retrying, instead of failing the whole pipeline
on the first paper that happens to land after the quota is used up.
"""
import json
import logging
import re
import time

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE

logger = logging.getLogger("llm")

_llm = None

MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 5.0


def get_llm():
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file before "
                "starting the server."
            )
        _llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=GROQ_TEMPERATURE)
    return _llm


def _extract_retry_seconds(error_text: str) -> float:
    """Groq's 429 body includes e.g. 'Please try again in 1.08s'."""
    match = re.search(r"try again in ([\d.]+)s", error_text)
    if match:
        try:
            return float(match.group(1)) + 0.5  # small buffer
        except ValueError:
            pass
    return DEFAULT_BACKOFF_SECONDS


def ask(system_prompt: str, user_prompt: str) -> str:
    """Plain text completion, with automatic retry on Groq rate limits."""
    llm = get_llm()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = llm.invoke(messages)
            return resp.content
        except Exception as e:
            error_text = str(e)
            is_rate_limit = "rate_limit_exceeded" in error_text or "429" in error_text
            if not is_rate_limit or attempt == MAX_RETRIES:
                raise
            wait_seconds = _extract_retry_seconds(error_text)
            logger.warning(
                "Groq rate limit hit (attempt %d/%d) - waiting %.1fs before retrying",
                attempt, MAX_RETRIES, wait_seconds,
            )
            time.sleep(wait_seconds)
            last_error = e
    raise last_error


class LLMJsonParseError(RuntimeError):
    """
    Raised by ask_json when raise_on_failure=True and the model's response
    couldn't be parsed as JSON (e.g. wrapped in reasoning/prose the model
    added despite being told not to, or output got cut off mid-structure).
    Distinguishes "the model actually failed" from "the model legitimately
    returned an empty result" - a silent default=[] can't tell those apart,
    which is what let a broken Gap/Hypothesis/Experiment step look like a
    normal "0 found" instead of a real error.
    """


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)


def ask_json(system_prompt: str, user_prompt: str, default=None, raise_on_failure: bool = False):
    """
    Completion where we expect strict JSON back. Strips markdown code fences
    and any <think>...</think> reasoning block some models add despite being
    told not to, then tries to parse - first the whole cleaned response,
    then (if that fails) the first {...}/[...] structure found inside it.

    On failure: if raise_on_failure is True, raises LLMJsonParseError so the
    caller can surface a real error instead of silently treating "the model
    broke" the same as "the model found nothing". Otherwise falls back to
    `default` (the original behavior) - still useful where a per-item
    failure (e.g. one paper out of many in Analysis) shouldn't abort the
    whole step.
    """
    raw = ask(
        system_prompt + "\n\nRespond with ONLY valid JSON. No prose, no markdown fences.",
        user_prompt,
    )
    cleaned = _THINK_BLOCK_RE.sub("", raw).strip()
    cleaned = re.sub(r"^```(json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from LLM output: %.200s", cleaned)
        if raise_on_failure:
            raise LLMJsonParseError(
                f"Model did not return valid JSON. Raw output started with: {cleaned[:200]!r}"
            )
        return default
