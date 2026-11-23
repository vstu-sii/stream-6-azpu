"""Local Qwen inference and evidence validation for one assessment."""

import json
import os
import re
import threading
import time
from collections import OrderedDict
from functools import lru_cache

from ml.prompts_v2 import PROMPTS, QUOTE_TEMPLATE, TEMPLATE, choose_segments, split_segments
from ml.tools.evidence import read_segment
from ml.tracing import record

PROMPT_VERSION = "azpu-extract-v2"
MAX_INPUT = 2000
MAX_OUTPUT = 256
EVIDENCE_ROW = {
    "anyOf": [
        {"type": "null"},
        {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["segment_id", "quote"],
            "additionalProperties": False,
        },
    ],
}
CONTACT = re.compile(
    r"(?im)^\s*(?:имя|фио|телефон|e-?mail|пол|возраст|дата рождения|адрес)\s*:.*$"
    r"|\b[\w.+-]+@[\w.-]+\.[a-zа-я]{2,}\b|(?<!\w)\+?[0-9][0-9() -]{8,}[0-9](?!\w)"
    r"|\b\d{2}\s*(?:лет|год(?:а)?)\s*\."
)
_LOCK = threading.Lock()
_CACHE = OrderedDict()
_CACHE_SIZE = 32


@lru_cache(maxsize=1)
def _engine(path):
    from llama_cpp import Llama

    return Llama(model_path=path, n_ctx=2304, n_threads=4, seed=42, verbose=False)


@lru_cache(maxsize=32)
def _grammar(ids, method):
    from llama_cpp import LlamaGrammar

    schema = {
        "type": "object",
        "properties": {
            key: EVIDENCE_ROW if method == "quote" else {"type": ["string", "null"]}
            for key in ids
        },
        "required": list(ids),
        "additionalProperties": False,
    }
    return LlamaGrammar.from_json_schema(json.dumps(schema), verbose=False)


def prepare_segments(resume_text):
    clean = CONTACT.sub("[скрыто]", resume_text)
    return {
        f"s{i}": piece for i, piece in enumerate(
            (part.strip() for part in clean.splitlines() if part.strip()), 1
        )
    }


def build_prompt(requirements, segments, method="quote"):
    payload = json.dumps({"requirements": requirements, "segments": segments}, ensure_ascii=False)
    instruction = TEMPLATE if method != "quote" else QUOTE_TEMPLATE
    return f"<|im_start|>user\n{instruction}{payload}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def validate(raw, requirements, segments, method="quote"):
    parsed = json.loads(raw)
    ids = {item["id"] for item in requirements}
    if not isinstance(parsed, dict) or set(parsed) != ids:
        raise ValueError("Invalid model envelope")
    if method != "quote":
        return {
            key: row for key, value in parsed.items()
            if (row := read_segment(segments, value)) is not None
        }
    accepted = {}
    for key, item in parsed.items():
        if not isinstance(item, dict):
            continue
        segment, quote = item.get("segment_id"), item.get("quote")
        if not all(isinstance(value, str) for value in (key, segment, quote)):
            continue
        if key not in ids or segment not in segments or not quote.strip() or len(quote) > 350:
            continue
        start = segments[segment].find(quote)
        if start != -1:
            accepted.setdefault(key, {
                "segment_id": segment, "start": start, "end": start + len(quote), "quote": quote,
            })
    return accepted


def assess(assessment_id, requirements, resume_text):
    method = os.getenv("AZPU_PROMPT_MODE", "segment")
    if method != "quote" and method not in PROMPTS:
        method = "segment"
    segments = prepare_segments(resume_text)
    if method in PROMPTS:
        segments = split_segments(segments)
    if method == "short":
        segments = choose_segments(requirements, segments)
    prompt = build_prompt(requirements, segments, method)
    path = os.getenv("AZPU_MODEL_PATH")
    reason = "model_unavailable" if not path else None
    citations = {}
    raw = ""
    if path:
        with _LOCK:
            started = time.perf_counter()
            event = {
                "assessment_id": assessment_id, "model": os.path.basename(path), "prompt_version": PROMPTS.get(method, PROMPT_VERSION),
                "input_tokens": None, "output_tokens": None, "status": "error",
            }
            cache_key = (path, event["prompt_version"], prompt)
            cache_enabled = os.getenv("AZPU_SYNTHETIC_CACHE") == "1"
            if cache_enabled and cache_key in _CACHE:
                citations = _CACHE[cache_key]
                _CACHE.move_to_end(cache_key)
                record({**event, "status": "cache_hit", "input_tokens": 0, "output_tokens": 0,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "validated_count": len(citations)}, prompt=prompt, response="")
                return citations, None
            attempt = False
            try:
                engine = _engine(path)
                grammar = _grammar(tuple(item["id"] for item in requirements), method)
                event["input_tokens"] = len(engine.tokenize(prompt.encode(), special=True))
                if event["input_tokens"] > MAX_INPUT:
                    reason = "context_limit"
                else:
                    attempt = True
                    reply = engine(prompt, max_tokens=MAX_OUTPUT, temperature=0.0, grammar=grammar)
                    raw = reply["choices"][0]["text"]
                    event["input_tokens"] = reply["usage"]["prompt_tokens"]
                    event["output_tokens"] = reply["usage"]["completion_tokens"]
                    citations = validate(raw, requirements, segments, method)
                    event["status"] = "ok"
                    event["validated_count"] = len(citations)
                    if cache_enabled:
                        _CACHE[cache_key] = citations
                        if len(_CACHE) > _CACHE_SIZE:
                            _CACHE.popitem(last=False)
            except (OSError, RuntimeError, ValueError, ImportError) as exc:
                reason = "invalid_model_output" if raw else "model_unavailable"
                event["error_type"] = type(exc).__name__
            finally:
                if attempt:
                    event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
                    record(event, prompt=prompt, response=raw)
    return citations, reason
