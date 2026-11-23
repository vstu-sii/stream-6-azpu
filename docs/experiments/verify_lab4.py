"""Verify stored Lab 4 measurements and their inputs without loading model weights."""

import csv
import json
import math
import statistics
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSIONS = {
    "quote": ("azpu-extract-v2", "quote-2.txt"),
    "segment": ("azpu-segments-1", "segments-1.txt"),
    "short": ("azpu-segments-short-1", "segments-1.txt"),
}


def price(input_tokens, output_tokens):
    """Estimate USD for the observed volume at the documented reference rates."""
    return (Decimal(str(input_tokens)) * Decimal("0.40") +
            Decimal(str(output_tokens)) * Decimal("1.60")) / 1_000_000


def verify():
    summary = json.loads((HERE / "lab4-summary.json").read_text(encoding="utf-8"))
    cases = json.loads((HERE / "lab4-cases.json").read_text(encoding="utf-8"))
    gold = {case["id"]: set(case["gold"]) for case in cases}
    for variant, (version, template) in VERSIONS.items():
        run = summary[variant]
        prompt_path = ROOT / "ml" / "prompts_v2" / template
        csv_path = HERE / f"lab4-{variant}.csv"
        assert run["prompt_file"] == prompt_path.relative_to(ROOT).as_posix()
        assert run["prompt_sha256"] == sha256(prompt_path.read_bytes()).hexdigest()
        assert run["trace_sha256"] == sha256(csv_path.read_bytes()).hexdigest()
        with csv_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(gold) == run["n"]
        assert {r["case"] for r in rows} == gold.keys()
        assert {r["prompt_version"] for r in rows} == {version}
        assert {r["status"] for r in rows} == {"ok"}
        assert len({r["assessment_id"] for r in rows}) == len(rows)
        predictions = {r["case"]: set(filter(None, r["predicted"].split(","))) for r in rows}
        tp = sum(len(predictions[k] & g) for k, g in gold.items())
        fp = sum(len(predictions[k] - g) for k, g in gold.items())
        fn = sum(len(g - predictions[k]) for k, g in gold.items())
        assert (tp, fp, fn) == (run["tp"], run["fp"], run["fn"])
        assert round(2 * tp / (2 * tp + fp + fn), 3) == run["f1"]
        assert sum(predictions[k] == g for k, g in gold.items()) == run["exact"]
        for field in ("input_tokens", "output_tokens"):
            assert statistics.mean(int(r[field]) for r in rows) == run[f"mean_{field}"]
        timings = sorted(float(r["latency_ms"]) for r in rows)
        assert round(statistics.median(timings), 2) == run["p50_ms"]
        assert timings[math.ceil(0.95 * len(rows)) - 1] == run["p95_ms"]
        print(f"{version}: {len(rows)} traces, F1 {run['f1']:.3f}, hashes and metrics verified")

    cache = json.loads((HERE / "lab4-cache.json").read_text(encoding="utf-8"))
    for phase, statuses in (("before", ["ok", "ok"]), ("after", ["ok", "cache_hit"])):
        block = cache[phase]
        assert [row["status"] for row in block["calls"]] == statuses
        for field in ("input_tokens", "output_tokens"):
            assert block[field] == sum(row[field] for row in block["calls"])
    assert cache["after"]["calls"][-1]["input_tokens"] == cache["after"]["calls"][-1]["output_tokens"] == 0
    for phase, variant in (("before", "quote"), ("after", "segment")):
        run = summary[variant]
        print(f"{phase}: USD {price(run['mean_input_tokens'], run['mean_output_tokens']):.7f} per assessment")
    print(f"same two requests: USD {price(cache['before']['input_tokens'], cache['before']['output_tokens']):.7f}"
          f" -> {price(cache['after']['input_tokens'], cache['after']['output_tokens']):.7f}")


if __name__ == "__main__":
    verify()
