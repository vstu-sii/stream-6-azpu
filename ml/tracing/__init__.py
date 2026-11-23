"""Per-call local traces with opt-in synthetic payload capture."""

import json
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger("azpu.model")


def record(event, *, prompt, response):
    target = os.getenv("AZPU_TRACE_FILE")
    if target is None:
        LOGGER.info("azpu_model_call %s", json.dumps(event, ensure_ascii=False))
        return
    if os.getenv("AZPU_TRACE_SYNTHETIC_PAYLOADS") == "1":
        event = {**event, "prompt": prompt, "response": response}
    with Path(target).open("a", encoding="utf-8") as log:
        log.write(json.dumps(event, ensure_ascii=False) + "\n")
