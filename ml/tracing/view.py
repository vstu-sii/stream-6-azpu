"""Export an offline HTML view of local JSONL model traces."""

import argparse
import html
import json
from pathlib import Path


def render(events):
    fields = ("assessment_id", "model", "prompt_version", "status", "latency_ms", "input_tokens", "output_tokens")
    rows = []
    for event in events:
        widget = ""
        for key in ("prompt", "response"):
            if key in event:
                widget += f"<details><summary>{key}</summary><pre>{html.escape(str(event[key]))}</pre></details>"
        cells = "".join(f"<td>{html.escape(str(event.get(key, '')))}</td>" for key in fields)
        rows.append(f"<tr>{cells}<td>{widget}</td></tr>")
    header = "".join(f"<th>{field}</th>" for field in fields)
    return ("<!doctype html><meta charset='utf-8'><title>AZPU model traces</title>"
            "<style>td,th{padding:.5rem;border-bottom:1px solid #ddd} pre{white-space:pre-wrap}</style>"
            "<h1>AZPU model traces</h1><table>"
            f"<thead><tr>{header}<th>Synthetic payload</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    events = [json.loads(line) for line in args.trace.read_text(encoding="utf-8").splitlines()]
    args.output.write_text(render(events), encoding="utf-8")
