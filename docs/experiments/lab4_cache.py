"""Measure the same two identical assessments with cache off and on."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from lab4 import HERE
from lab3 import REQUIREMENTS
from ml.models.baseline import assess


def probe(model):
    os.environ["AZPU_MODEL_PATH"] = str(model)
    os.environ["AZPU_PROMPT_MODE"] = "segment"
    os.environ.pop("AZPU_TRACE_SYNTHETIC_PAYLOADS", None)
    resume = json.loads((HERE / "lab4-cases.json").read_text(encoding="utf-8"))[0]["resume"]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "trace.jsonl"
        os.environ["AZPU_TRACE_FILE"] = str(path)
        results = []
        for label, enabled in (("before", "0"), ("after", "1")):
            os.environ["AZPU_SYNTHETIC_CACHE"] = enabled
            for request in (1, 2):
                results.append(assess(f"{label}-{request}", REQUIREMENTS, resume))
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert all(result == results[0] for result in results)
    assert results[0][0] and results[0][1] is None
    assert [row["status"] for row in rows] == ["ok", "ok", "ok", "cache_hit"]
    assert rows[-1]["input_tokens"] == rows[-1]["output_tokens"] == 0
    return {label: {"calls": calls, **{
        metric: sum(row[metric] for row in calls)
        for metric in ("input_tokens", "output_tokens")
    }} for label, calls in (("before", rows[:2]), ("after", rows[2:]))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    print(json.dumps(probe(parser.parse_args().model), indent=2))
