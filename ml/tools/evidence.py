"""Resolve one model-selected ID within the current request's segments."""

from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

TOOL_TIMEOUT_SECONDS = 0.05
_TOOL_WORKERS = 2
_TOOL_POOL = ThreadPoolExecutor(max_workers=_TOOL_WORKERS, thread_name_prefix="azpu-evidence")
_TOOL_SLOTS = BoundedSemaphore(_TOOL_WORKERS)


def read_segment(segments, segment_id):
    """Return an evidence row, or None for a bad ID or oversized segment."""
    if not isinstance(segment_id, str):
        return None
    quote = segments.get(segment_id, "")
    if not quote.strip() or len(quote) > 350:
        return None
    return {"segment_id": segment_id, "start": 0, "end": len(quote), "quote": quote}


def read_segment_with_timeout(segments, segment_id):
    """Bound the caller's wait and reject new calls when the reader pool is full."""
    if not _TOOL_SLOTS.acquire(blocking=False):
        raise TimeoutError("Evidence reader is busy")
    try:
        pending = _TOOL_POOL.submit(read_segment, segments, segment_id)
    except RuntimeError:
        _TOOL_SLOTS.release()
        raise
    pending.add_done_callback(lambda _: _TOOL_SLOTS.release())
    try:
        return pending.result(timeout=TOOL_TIMEOUT_SECONDS)
    except TimeoutError:
        pending.cancel()
        raise
