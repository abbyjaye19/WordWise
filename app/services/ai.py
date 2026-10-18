"""AI helpers for the Reading Studio. Every call uses gpt-6-luna through Portkey.

Five helpers ("agents"), each with its own prompt in prompts/:
  word_help   -> Word Coach: meaning in context, syllables, synonyms
  explain     -> Explainer: simpler / example / step-by-step for a selected passage
  summarize   -> Comprehension Coach: big idea, key points, words, check questions
  rewrite     -> Reading Levels: the whole reading in simplified or detailed wording
  tutor_reply -> AI Tutor: chat, optionally about the current reading, and it can
                 suggest reading-setting changes the student applies with one tap

Every helper also gets the student's self-reported profile (what they find hard) so
answers adapt to them; see services/preferences.py.

Every call is logged to output/usage_log.jsonl with input, cached input, and
output tokens plus cost, and a daily spending cap stops runaway costs.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import Lock

from openai import OpenAI
from pydantic import BaseModel

from config import DATA_DIR, MODEL_NAME, OUTPUT_DIR, PORTKEY_API_KEY, PROJECT_ROOT
from services import preferences
from services.schemas import Explanation, Rewrite, Summary, TutorReply, WordHelp

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


# Cost settings (measured in scripts/measure_tokenomics.py):
#  - USE_LEVEL_GUIDE: every helper's instructions start with the same ~1,300-token block
#    (shared rules + reader-level guide). The provider only caches a repeated prefix of
#    1,024+ tokens, and cached input costs 10x less, so this shared block is billed at the
#    cached rate on almost every call. Without it, prompts were ~650 tokens and never cached.
#  - REASONING_EFFORT: "low" keeps hidden reasoning tokens (billed as output) small.
USE_LEVEL_GUIDE = True
REASONING_EFFORT = "low"


def _instructions(role: str) -> str:
    """Static system prompt. The shared part comes first and is identical for every helper,
    so one cached prefix serves the Word Coach, Explainer, Comprehension Coach, and AI Tutor."""
    return _instructions_cached(role, USE_LEVEL_GUIDE)


@lru_cache(maxsize=None)
def _instructions_cached(role: str, level_guide: bool) -> str:
    parts = [(PROMPTS_DIR / "shared_rules.md").read_text(encoding="utf-8")]
    if level_guide:
        parts.append((PROMPTS_DIR / "reading_levels.md").read_text(encoding="utf-8"))
    parts.append((PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8"))
    if role == "ai_tutor":
        parts.append(_settings_catalog())
    return "\n\n".join(parts)


def _settings_catalog() -> str:
    """The reading settings the tutor may suggest (the same list the settings panel uses)."""
    lines = ["## Reading settings catalog (key: allowed values)"]
    for key, (label, options, default, about) in preferences.SETTINGS.items():
        values = ", ".join(f'"{v}" ({lab})' for v, lab in options)
        lines.append(f'- `{key}`: {label} ({about}). Values: {values}. Default "{default}".')
    return "\n".join(lines)


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


LOG_EXTRA: dict = {}  # extra fields added to every log record (the measurement script tags its runs)
# Extra request headers. The measurement script sets {"x-portkey-cache-force-refresh": "true"}
# so it measures the model rather than Portkey's replay cache.
EXTRA_HEADERS: dict = {}


def _log(feature: str, resp, seconds: float, gateway_cache: str | None = None) -> None:
    """gateway_cache is Portkey's x-portkey-cache-status. On a HIT, Portkey replays a stored answer
    for an identical earlier request and the model is not called, so the call costs $0."""
    u = resp.usage
    details = u.input_tokens_details
    cached = getattr(details, "cached_tokens", 0) or 0
    written = getattr(details, "cache_write_tokens", 0) or 0
    reasoning = getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0
    hit = (gateway_cache or "").upper() == "HIT"
    cost = 0.0 if hit else _cost(u.input_tokens, cached, written, u.output_tokens)
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
        "gateway_cache": gateway_cache or "",
        **LOG_EXTRA,
    }
    with _lock:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        _spent_today()
        _spent["usd"] += cost


CONTENT_FILTER_MESSAGE = (
    "WordWise's safety filter stopped this request. The text may contain instructions aimed at the AI "
    "or content that isn't safe. Try a different part of the reading, or ask a teacher for help."
)


def _is_content_filter(exc: Exception) -> bool:
    """Azure OpenAI (behind Portkey) rejects prompts its content filter flags, including jailbreak attempts."""
    body = getattr(exc, "body", None) or {}
    code = (body.get("code") if isinstance(body, dict) else None) or getattr(exc, "code", None)
    return code == "content_filter" or "content_filter" in str(exc)


def _log_blocked(feature: str, seconds: float) -> None:
    """Record a request the provider's content filter refused (no tokens billed)."""
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "feature": feature, "model": MODEL_NAME,
           "input_tokens": 0, "cached_input_tokens": 0, "cache_write_tokens": 0, "output_tokens": 0,
           "reasoning_tokens": 0, "cost_usd": 0.0, "seconds": round(seconds, 2), "gateway_cache": "",
           "blocked": "content_filter", **LOG_EXTRA}
    with _lock:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")


def _guarded(feature: str, request):
    """Run one model request with the budget check, model check, and usage log.
    `request(client)` must return a raw response (client.responses.with_raw_response.*)."""
    if _spent_today() >= DAILY_BUDGET_USD:
        raise AIError("WordWise has reached today's AI limit. Reading tools still work. AI help will be back tomorrow.")
    start = time.perf_counter()
    try:
        raw = request(_client().with_options(default_headers=EXTRA_HEADERS) if EXTRA_HEADERS else _client())
        resp = raw.parse()
    except AIError:
        raise
    except Exception as exc:  # noqa: BLE001 - network/API problems become a friendly message
        if _is_content_filter(exc):
            _log_blocked(feature, time.perf_counter() - start)
            raise AIError(CONTENT_FILTER_MESSAGE) from exc
        raise AIError("We couldn't reach the AI helper just now. Please try again in a moment.") from exc
    if not (resp.model or "").startswith(MODEL_NAME):
        raise AIError("An unexpected AI model answered, so we stopped.")
    _log(feature, resp, time.perf_counter() - start, raw.headers.get("x-portkey-cache-status"))
    return resp


def _call(feature: str, role: str, user_input: str, schema: type[BaseModel], max_tokens: int) -> BaseModel:
    resp = _guarded(
        feature,
        lambda c: c.responses.with_raw_response.parse(
            model=MODEL_NAME,
            instructions=_instructions(role),
            input=user_input,
            text_format=schema,
            max_output_tokens=max_tokens,
            reasoning={"effort": REASONING_EFFORT},
        ),
    )
    if resp.output_parsed is None:
        raise AIError("The AI helper's answer came back incomplete. Please try again.")
    return resp.output_parsed


def _reading(text: str) -> str:
    # Strip anything that could close our tag early.
    return "<reading>\n" + text.replace("</reading>", "") + "\n</reading>"


def _header(level: str, profile: str) -> str:
    """Per-request context. It goes in the input (not the instructions) so the cached prefix stays shared."""
    head = f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}\n"
    return head + (profile[:600] + "\n" if profile else "")


# ---------- public helpers (results cached so repeat clicks are free) ----------

@lru_cache(maxsize=512)
def word_help(word: str, sentence: str, level: str, profile: str = "") -> WordHelp:
    prompt = (
        _header(level, profile)
        + f"Word: {word[:60]}\n"
        f"Sentence it appears in:\n{_reading(sentence[:600])}"
    )
    return _call("word_help", "word_coach", prompt, WordHelp, 1200)


@lru_cache(maxsize=256)
def explain(passage: str, mode: str, level: str, profile: str = "") -> Explanation:
    mode = EXPLAIN_MODES.get(mode, "simpler")
    prompt = (
        _header(level, profile)
        + f"Mode: {mode}\n"
        f"Passage:\n{_reading(passage[:MAX_SELECTION_CHARS])}"
    )
    return _call(f"explain_{mode}", "explainer", prompt, Explanation, 1600)


def summarize(text: str, scope_label: str, level: str, profile: str = "") -> tuple[Summary, bool]:
    """Returns (summary, was_trimmed)."""
    trimmed = len(text) > MAX_SUMMARY_CHARS
    return _summarize_cached(text[:MAX_SUMMARY_CHARS], scope_label, level, profile), trimmed


# ---------- Reading Levels: the whole reading, simplified or explained in more detail ----------

REWRITE_MODES = ("simplified", "detailed")
MAX_REWRITE_CHARS = 12_000  # about 2,000 words; later paragraphs stay in the original wording
REWRITE_CHUNK_CHARS = 3_000  # chunks run in parallel, so a long reading isn't 4x slower


def rewrite(paragraphs: list[str], mode: str, level: str, profile: str = "") -> tuple[list[str], int]:
    """Rewrite paragraphs in order. Returns (rewritten, how many paragraphs were covered).
    A paragraph the model skipped keeps its original wording, so no meaning is lost."""
    if mode not in REWRITE_MODES:
        raise AIError("Pick Simplified or Detailed.")
    covered, total = [], 0
    for p in paragraphs:
        if covered and total + len(p) > MAX_REWRITE_CHARS:
            break
        covered.append(p[:MAX_SELECTION_CHARS])
        total += len(covered[-1])
    chunks, cur, size = [], [], 0
    for p in covered:
        if cur and size + len(p) > REWRITE_CHUNK_CHARS:
            chunks.append(tuple(cur))
            cur, size = [], 0
        cur.append(p)
        size += len(p)
    if cur:
        chunks.append(tuple(cur))
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(lambda c: _rewrite_chunk(c, mode, level, profile), chunks))
    return [t for part in parts for t in part], len(covered)


@lru_cache(maxsize=128)
def _rewrite_chunk(paras: tuple[str, ...], mode: str, level: str, profile: str) -> tuple[str, ...]:
    numbered = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(paras))
    prompt = _header(level, profile) + f"Mode: {mode}\nParagraphs:\n{_reading(numbered)}"
    chars = sum(len(p) for p in paras)
    budget = min(8000, 1000 + (chars // 2 if mode == "simplified" else chars))  # ~4 chars per token, plus reasoning
    out = _call(f"rewrite_{mode}", "rewriter", prompt, Rewrite, budget)
    by_n = {r.n: " ".join(r.text.split()) for r in out.paragraphs if r.text.strip()}
    return tuple(by_n.get(i + 1, p) for i, p in enumerate(paras))


MAX_CHAT_MESSAGE = 1_000
MAX_CHAT_TURNS = 12  # most recent messages sent to the model
MAX_CHAT_READING = 12_000


MAX_SUGGESTIONS = 3


def _suggestion_note(m: dict) -> str:
    """Remind the tutor what it suggested earlier and what the student tried, so it can adjust."""
    sugg = m.get("suggestions") or []
    if m.get("role") != "assistant" or not sugg:
        return ""
    applied = m.get("applied") or {}
    parts = [f"{s['setting']}={s['value']} ({'student applied it' if s['setting'] in applied else 'not applied'})" for s in sugg]
    return "\n[Settings suggested: " + "; ".join(parts) + "]"


def tutor_reply(history: list[dict], level: str, reading: str | None = None, profile: str = "",
                settings: dict | None = None, usage: str = "") -> TutorReply:
    """AI Tutor chat. history = [{"role": "user"|"assistant", "content": str}, ...] ending with the student's turn.
    Returns the reply plus any reading-setting suggestions, checked against the real settings list."""
    current = preferences.clean(settings)
    context = f"Reader level: {LEVELS.get(level, LEVELS['13-17'])}."
    context += "\nCurrent reading settings: " + "; ".join(f"{k}={v}" for k, v in current.items())
    if profile:
        context += "\n" + profile[:600]
    if usage:
        context += "\n" + usage[:600]
    if reading:
        trimmed = reading[:MAX_CHAT_READING]
        context += "\nThe student is reading this right now:\n" + _reading(trimmed)
        if len(reading) > MAX_CHAT_READING:
            context += "\n(Only the first part of the reading is shown.)"
    messages = [{"role": "developer", "content": context}] + [
        {"role": m["role"], "content": str(m["content"])[:MAX_CHAT_MESSAGE] + _suggestion_note(m)}
        for m in history[-MAX_CHAT_TURNS:]
        if m.get("role") in ("user", "assistant") and m.get("content") and not m.get("error")
    ]
    resp = _guarded(
        "tutor_chat",
        lambda c: c.responses.with_raw_response.parse(
            model=MODEL_NAME,
            instructions=_instructions("ai_tutor"),
            input=messages,
            text_format=TutorReply,
            max_output_tokens=1400,
            reasoning={"effort": REASONING_EFFORT},
        ),
    )
    out = resp.output_parsed
    if out is None or not out.reply.strip():
        raise AIError("The AI Tutor's answer came back empty. Please try again.")
    seen, safe = set(), []
    for sg in out.suggestions:  # only real settings, real values, and actual changes
        key, value = sg.setting.strip(), sg.value.strip()
        if value in preferences.ALLOWED.get(key, ()) and value != current[key] and key not in seen:
            seen.add(key)
            safe.append(sg.model_copy(update={"setting": key, "value": value, "reason": sg.reason.strip()[:200]}))
    return out.model_copy(update={"reply": out.reply.strip(), "suggestions": safe[:MAX_SUGGESTIONS]})


@lru_cache(maxsize=64)
def _summarize_cached(text: str, scope_label: str, level: str, profile: str = "") -> Summary:
    prompt = (
        _header(level, profile)
        + f"Part of the reading: {scope_label}\n"
        f"{_reading(text)}"
    )
    return _call("summarize", "comprehension_coach", prompt, Summary, 3000)
