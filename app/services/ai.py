"""AI helpers for the Reading Studio. Every call uses gpt-6-luna through Portkey.

Four helpers ("agents"), each with its own prompt in prompts/:
  word_help   -> Word Coach: meaning in context, syllables, synonyms
  explain     -> Explainer: simpler / example / step-by-step for a selected passage
  summarize   -> Comprehension Coach: big idea, key points, words, check questions
  tutor_reply -> AI Tutor: free-form chat, optionally about the current reading

Every call is logged to output/usage_log.jsonl with input, cached input, and
output tokens plus cost, and a daily spending cap stops runaway costs.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date
from functools import lru_cache
from threading import Lock

from openai import OpenAI
from pydantic import BaseModel

from config import DATA_DIR, MODEL_NAME, OUTPUT_DIR, PORTKEY_API_KEY, PROJECT_ROOT
from services.schemas import Explanation, Summary, WordHelp

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
USAGE_LOG = OUTPUT_DIR / "usage_log.jsonl"
PRICES = json.loads((DATA_DIR / "prices.json").read_text(encoding="utf-8"))[MODEL_NAME]

DAILY_BUDGET_USD = float(os.getenv("WORDWISE_DAILY_BUDGET_USD", "2.00"))
MAX_SELECTION_CHARS = 3_000
MAX_SUMMARY_CHARS = 40_000  # about 10k tokens

LEVELS = {"5-8": "Ages 5–8", "9-12": "Ages 9–12", "13-17": "Ages 13–17", "18+": "Ages 18+"}
EXPLAIN_MODES = {"simpler": "simpler", "example": "example", "steps": "steps"}


class AIError(RuntimeError):
    """A friendly, user-facing AI problem."""


# ---------- setup ----------

@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not PORTKEY_API_KEY:
        raise AIError("AI help is off because no PORTKEY_API_KEY was found. See the README to add one.")
    return OpenAI(api_key=PORTKEY_API_KEY, base_url=PORTKEY_BASE_URL, timeout=60, max_retries=2)


@lru_cache(maxsize=None)
def _instructions(role: str) -> str:
    """Static system prompt (shared rules + role). Identical every call, so it can be cached."""
    shared = (PROMPTS_DIR / "shared_rules.md").read_text(encoding="utf-8")
    return shared + "\n\n" + (PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8")


# ---------- spending guard + logging ----------

_lock = Lock()
_spent = {"day": None, "usd": 0.0}


def _spent_today() -> float:
    today = date.today().isoformat()
    if _spent["day"] != today:
        total = 0.0
        if USAGE_LOG.exists():
            for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec.get("time", "").startswith(today):
                    total += rec["cost_usd"]
        _spent.update(day=today, usd=total)
    return _spent["usd"]


def _cost(inp: int, cached: int, written: int, out: int) -> float:
    uncached = max(inp - cached - written, 0)
    return (
        uncached * PRICES["input_per_1m"]
        + cached * PRICES["cached_input_per_1m"]
        + written * PRICES["cache_write_per_1m"]
        + out * PRICES["output_per_1m"]
    ) / 1e6


def _log(feature: str, resp, seconds: float) -> None:
    u = resp.usage
    details = u.input_tokens_details
    cached = getattr(details, "cached_tokens", 0) or 0
    written = getattr(details, "cache_write_tokens", 0) or 0
    reasoning = getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0
    cost = _cost(u.input_tokens, cached, written, u.output_tokens)
    rec = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "feature": feature,
        "model": resp.model,
        "input_tokens": u.input_tokens,
        "cached_input_tokens": cached,
        "cache_write_tokens": written,
        "output_tokens": u.output_tokens,
        "reasoning_tokens": reasoning,
        "cost_usd": round(cost, 8),
        "seconds": round(seconds, 2),
    }
    with _lock:
        OUTPUT_DIR.mkdir(exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        _spent_today()
        _spent["usd"] += cost


def _guarded(feature: str, request):
    """Run one model request with the budget check, model check, and usage log."""
    if _spent_today() >= DAILY_BUDGET_USD:
        raise AIError("WordWise has reached today's AI limit. Reading tools still work. AI help will be back tomorrow.")
    start = time.perf_counter()
    try:
        resp = request(_client())
    except AIError:
        raise
    except Exception as exc:  # noqa: BLE001 - network/API problems become a friendly message
        raise AIError("We couldn't reach the AI helper just now. Please try again in a moment.") from exc
    if not (resp.model or "").startswith(MODEL_NAME):
        raise AIError("An unexpected AI model answered, so we stopped.")
    _log(feature, resp, time.perf_counter() - start)
    return resp


def _call(feature: str, role: str, user_input: str, schema: type[BaseModel], max_tokens: int) -> BaseModel:
    resp = _guarded(
        feature,
        lambda c: c.responses.parse(
            model=MODEL_NAME,
            instructions=_instructions(role),
            input=user_input,
            text_format=schema,
            max_output_tokens=max_tokens,
            reasoning={"effort": "low"},
        ),
    )
    if resp.output_parsed is None:
        raise AIError("The AI helper's answer came back incomplete. Please try again.")
    return resp.output_parsed


def _reading(text: str) -> str:
    # Strip anything that could close our tag early.
    return "<reading>\n" + text.replace("</reading>", "") + "\n</reading>"


# ---------- public helpers (results cached so repeat clicks are free) ----------

@lru_cache(maxsize=512)
def word_help(word: str, sentence: str, level: str) -> WordHelp:
    prompt = (
        f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}\n"
        f"Word: {word[:60]}\n"
        f"Sentence it appears in:\n{_reading(sentence[:600])}"
    )
    return _call("word_help", "word_coach", prompt, WordHelp, 1200)


@lru_cache(maxsize=256)
def explain(passage: str, mode: str, level: str) -> Explanation:
    mode = EXPLAIN_MODES.get(mode, "simpler")
    prompt = (
        f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}\n"
        f"Mode: {mode}\n"
        f"Passage:\n{_reading(passage[:MAX_SELECTION_CHARS])}"
    )
    return _call(f"explain_{mode}", "explainer", prompt, Explanation, 1600)


def summarize(text: str, scope_label: str, level: str) -> tuple[Summary, bool]:
    """Returns (summary, was_trimmed)."""
    trimmed = len(text) > MAX_SUMMARY_CHARS
    return _summarize_cached(text[:MAX_SUMMARY_CHARS], scope_label, level), trimmed


MAX_CHAT_MESSAGE = 1_000
MAX_CHAT_TURNS = 12  # most recent messages sent to the model
MAX_CHAT_READING = 12_000


def tutor_reply(history: list[dict], level: str, reading: str | None = None) -> str:
    """AI Tutor chat. history = [{"role": "user"|"assistant", "content": str}, ...] ending with the student's turn."""
    context = f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}."
    if reading:
        trimmed = reading[:MAX_CHAT_READING]
        context += "\nThe student is reading this right now:\n" + _reading(trimmed)
        if len(reading) > MAX_CHAT_READING:
            context += "\n(Only the first part of the reading is shown.)"
    messages = [{"role": "developer", "content": context}] + [
        {"role": m["role"], "content": str(m["content"])[:MAX_CHAT_MESSAGE]}
        for m in history[-MAX_CHAT_TURNS:]
        if m.get("role") in ("user", "assistant") and m.get("content") and not m.get("error")
    ]
    resp = _guarded(
        "tutor_chat",
        lambda c: c.responses.create(
            model=MODEL_NAME,
            instructions=_instructions("ai_tutor"),
            input=messages,
            max_output_tokens=1200,
            reasoning={"effort": "low"},
        ),
    )
    text = (resp.output_text or "").strip()
    if not text:
        raise AIError("The AI Tutor's answer came back empty. Please try again.")
    return text


@lru_cache(maxsize=64)
def _summarize_cached(text: str, scope_label: str, level: str) -> Summary:
    prompt = (
        f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}\n"
        f"Part of the reading: {scope_label}\n"
        f"{_reading(text)}"
    )
    return _call("summarize", "comprehension_coach", prompt, Summary, 3000)
