"""Replay the ten synthetic resume cases through the in-process HTTP API."""

import argparse
import asyncio
import csv
import json
import math
import os
import statistics
import sys
import tempfile
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import app
from lab1 import CASES, evaluate

REQUIREMENTS = [
    {"id": "python", "text": "Самостоятельная разработка на Python"},
    {"id": "fastapi", "text": "Самостоятельная разработка HTTP API на FastAPI"},
    {"id": "postgresql", "text": "Практическая работа с PostgreSQL"},
]


async def run(path, output, cases=CASES):
    os.environ["AZPU_MODEL_PATH"] = str(path)
    with tempfile.TemporaryDirectory() as directory:
        trace = Path(directory) / "trace.jsonl"
        os.environ["AZPU_TRACE_FILE"] = str(trace)
        os.environ.pop("AZPU_TRACE_SYNTHETIC_PAYLOADS", None)
        os.environ.pop("AZPU_SYNTHETIC_CACHE", None)
        calls = []
        predictions = {}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for case in cases:
                reply = await client.post("/v1/ai/assessments", json={
                    "vacancy_revision": "backend-v1", "requirements": REQUIREMENTS, "resume_text": case["resume"],
                })
                reply.raise_for_status()
                result = reply.json()
                predictions[case["id"]] = {f["requirement_id"] for f in result["findings"] if f["status"] == "evidenced"}
                calls.append({"case": case["id"], "assessment_id": result["assessment_id"], "state": result["state"]})
        events = {row["assessment_id"]: row for row in map(json.loads, trace.read_text().splitlines())}
    rows = [{**call, **events[call["assessment_id"]], "predicted": ",".join(sorted(predictions[call["case"]]))} for call in calls]
    fields = ["case", "assessment_id", "model", "prompt_version", "state", "status", "latency_ms",
              "input_tokens", "output_tokens", "validated_count", "error_type", "predicted"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    times = sorted(row["latency_ms"] for row in rows)
    if cases is CASES:
        metrics = evaluate(predictions)
    else:
        gold = {c["id"]: set(c["gold"]) for c in cases}
        tp = sum(len(predictions[k] & expected) for k, expected in gold.items())
        fp = sum(len(predictions[k] - expected) for k, expected in gold.items())
        fn = sum(len(expected - predictions[k]) for k, expected in gold.items())
        metrics = {"n": len(cases), "tp": tp, "fp": fp, "fn": fn,
                   "f1": round(2 * tp / max(2 * tp + fp + fn, 1), 3),
                   "exact": sum(predictions[k] == expected for k, expected in gold.items())}
    return {
        "model": path.name, **metrics, "p50_ms": round(statistics.median(times), 2),
        "p95_ms": times[math.ceil(0.95 * len(times)) - 1],
        "mean_input_tokens": statistics.mean(row["input_tokens"] for row in rows),
        "mean_output_tokens": statistics.mean(row["output_tokens"] for row in rows),
        "model_errors": sum(row["status"] != "ok" for row in rows),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ["AZPU_PROMPT_MODE"] = "quote"
    print(json.dumps(asyncio.run(run(args.model, args.output)), ensure_ascii=False, indent=2))
