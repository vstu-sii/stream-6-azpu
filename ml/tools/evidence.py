"""Resolve one model-selected ID within the current request's segments."""


def read_segment(segments, segment_id):
    """Return an evidence row, or None for a bad ID or oversized segment."""
    if not isinstance(segment_id, str):
        return None
    quote = segments.get(segment_id, "")
    if not quote.strip() or len(quote) > 350:
        return None
    return {"segment_id": segment_id, "start": 0, "end": len(quote), "quote": quote}
