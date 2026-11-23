"""Verify a repeated synthetic assessment gives the same findings with zero model tokens."""

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
    os.environ["AZPU_PROMPT_MODE"] = "short"
    os.environ["AZPU_SYNTHETIC_CACHE"] = "1"
    os.environ.pop("AZPU_TRACE_SYNTHETIC_PAYLOADS", None)
    resume = json.loads((HERE / "lab4-cases.json").read_text(encoding="utf-8"))[0]["resume"]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "trace.jsonl"
        os.environ["AZPU_TRACE_FILE"] = str(path)
        first = assess("cache-demo-first", REQUIREMENTS, resume)
        repeated = assess("cache-demo-repeat", REQUIREMENTS, resume)
        assert first == repeated and first[1] is None
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["status"] for row in rows] == ["ok", "cache_hit"]
    assert rows[1]["input_tokens"] == rows[1]["output_tokens"] == 0
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    print(json.dumps(probe(parser.parse_args().model), indent=2))
