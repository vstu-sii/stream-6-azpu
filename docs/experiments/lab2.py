"""Re-score saved Qwen runs with independent envelope and evidence validation."""

import json
import re
from pathlib import Path

from lab1 import CASES, KEYWORDS, evaluate, validate

HERE = Path(__file__).resolve().parent


def unwrap_json(raw):
    match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", raw.strip(), re.S | re.I)
    return match[1] if match else raw


def keep_verified_rows(raw, resume):
    try:
        parsed = json.loads(unwrap_json(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"confirmed"}:
        return None
    rows = parsed["confirmed"]
    if not isinstance(rows, dict):
        return None
    return {
        key: quote for key, quote in rows.items()
        if key in KEYWORDS and isinstance(quote, str) and quote.strip() and quote in resume
    }


def replay():
    notebook = json.loads((HERE / "lab1.ipynb").read_text(encoding="utf-8"))
    cell = next(cell for cell in notebook["cells"] if cell["id"] == "qwen")
    recorded = json.loads("".join(cell["outputs"][0]["text"]))
    resumes = {case["id"]: case["resume"] for case in CASES}
    checks = {
        "strict": lambda raw, resume: validate(raw, resume),
        "unwrap": lambda raw, resume: validate(unwrap_json(raw), resume),
        "per_row": keep_verified_rows,
    }
    result = {}
    for variant in ("brief", "evidence", "evidence_schema"):
        result[variant] = {}
        for policy, decode in checks.items():
            rows = {row["id"]: decode(row["raw"], resumes[row["id"]]) for row in recorded[variant]["rows"]}
            result[variant][policy] = {
                **evaluate({key: set(quotes or {}) for key, quotes in rows.items()}),
                "parsed": sum(quotes is not None for quotes in rows.values()),
            }
    return result


if __name__ == "__main__":
    print(json.dumps(replay(), ensure_ascii=False, indent=2))
