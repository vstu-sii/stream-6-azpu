"""Segment experiments for the local evaluation pipeline."""

import re
from pathlib import Path

PROMPTS = {"segment": "azpu-segments-1", "short": "azpu-segments-short-1"}
TEMPLATE = Path(__file__).with_name("segments-1.txt").read_text(encoding="utf-8")
WORDS = re.compile(r"[a-zа-я][a-zа-я0-9]+", re.I)
ALIASES = {"python": {"питон", "fastapi"}, "postgresql": {"postgres"}, "fastapi": {"fastapi"}}


def split_segments(text_by_line):
    sentences = (
        sentence.strip() for line in text_by_line.values()
        for sentence in re.split(r"(?<=[.!?])\s+", line) if sentence.strip()
    )
    return {f"s{i}": item for i, item in enumerate(sentences, 1)}


def choose_segments(requirements, segments):
    terms = set()
    for requirement in requirements:
        terms.update(WORDS.findall(requirement["id"].lower()))
        terms.update(WORDS.findall(requirement["text"].lower()))
        terms.update(ALIASES.get(requirement["id"], ()))
    matching = {
        key: text for key, text in segments.items()
        if set(WORDS.findall(text.lower())) & terms
    }
    return matching or segments
