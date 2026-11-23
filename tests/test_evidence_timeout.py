"""Exercise the tool deadline through the assessment API without loading model weights."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.app import app
from ml.models import baseline
from ml.tools import evidence


class EvidenceTimeoutTest(unittest.TestCase):
    def test_timed_out_fragment_requires_review_and_is_not_cached(self):
        allow_return = Event()
        started = Event()
        finished = Event()
        original_reader = evidence.read_segment

        def slow_reader(segments, segment_id):
            if segment_id != "s1" or allow_return.is_set():
                return original_reader(segments, segment_id)
            started.set()
            try:
                allow_return.wait(timeout=5)
                return original_reader(segments, segment_id)
            finally:
                finished.set()

        engine = Mock(return_value={
            "choices": [{"text": '{"python":"s1","sql":"s2","go":"s9"}'}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        })
        engine.tokenize.return_value = [1] * 10
        request = {
            "vacancy_revision": "v1",
            "requirements": [{"id": key, "text": key} for key in ("python", "sql", "go")],
            "resume_text": "Писал на Python. Создавал запросы SQL.",
        }
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            settings = {"AZPU_MODEL_PATH": "test-model.gguf", "AZPU_PROMPT_MODE": "segment",
                        "AZPU_TRACE_FILE": str(trace), "AZPU_SYNTHETIC_CACHE": "1"}
            with (patch.dict(os.environ, settings),
                  patch.object(baseline, "_CACHE", baseline.OrderedDict()),
                  patch.object(baseline, "_engine", return_value=engine),
                  patch.object(baseline, "_grammar", return_value=None),
                  patch.object(evidence, "read_segment", side_effect=slow_reader),
                  TestClient(app) as client):
                try:
                    response = client.post("/v1/ai/assessments", json=request)
                    self.assertTrue(started.is_set())
                    self.assertFalse(finished.is_set())
                    self.assertEqual(response.status_code, 200)
                    rows = {row["requirement_id"]: row for row in response.json()["findings"]}
                    self.assertEqual(rows["python"]["status"], "needs_review")
                    self.assertTrue(rows["python"]["question"])
                    self.assertEqual(rows["sql"]["evidence"]["quote"], "Создавал запросы SQL.")
                    self.assertEqual(rows["go"]["status"], "needs_review")
                finally:
                    allow_return.set()
                self.assertTrue(finished.wait(timeout=2))
                retried = client.post("/v1/ai/assessments", json=request)
                self.assertEqual(retried.status_code, 200)
                self.assertEqual(retried.json()["findings"][0]["status"], "evidenced")
                self.assertEqual(engine.call_count, 2)
            events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["evidence_tool_timeouts"], 1)
            self.assertNotIn("evidence_tool_timeouts", events[1])


if __name__ == "__main__":
    unittest.main()
