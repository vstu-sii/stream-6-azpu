"""Run paired pipeline A/B/C on the held-out synthetic dataset."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from lab3 import HERE, REQUIREMENTS, run
from ml.models.baseline import prepare_segments
from ml.prompts_v2 import choose_segments, split_segments


def shortlist_metrics(cases):
    retained = total = gold_retained = gold_total = 0
    for case in cases:
        segments = split_segments(prepare_segments(case["resume"]))
        shortlist = choose_segments(REQUIREMENTS, segments)
        retained += len(shortlist)
        total += len(segments)
        gold_ids = list(case["gold_segments"].values())
        gold_total += len(gold_ids)
        gold_retained += sum(key in shortlist for key in gold_ids)
    return {"segments_retained": retained, "segments_total": total,
            "gold_pairs_retained": gold_retained, "gold_pairs_total": gold_total}


async def compare(model, destination, cases):
    destination.mkdir(parents=True, exist_ok=True)
    result = {"shortlist": shortlist_metrics(cases)}
    for variant in ("quote", "segment", "short"):
        os.environ["AZPU_PROMPT_MODE"] = variant
        result[variant] = await run(model, destination / f"lab4-{variant}.csv", cases)
        print(variant, json.dumps(result[variant]), flush=True)
    (destination / "lab4-summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output-dir", default=HERE, type=Path)
    parser.add_argument("--cases", default=HERE / "lab4-cases.json", type=Path)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    asyncio.run(compare(args.model, args.output_dir, cases))
