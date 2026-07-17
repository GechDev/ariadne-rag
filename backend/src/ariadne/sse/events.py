"""SSE event protocol for ARIADNE streaming.

The stream endpoint emits a stable set of named events so clients can render
retrieval, sources, tokens and errors incrementally. Every event is a
``text/event-stream`` message with a machine-readable ``event`` name and a
JSON ``data`` payload.

Event sequence for a successful query::

    retrieval_started
    retrieval_completed
    sources_found
    generation_started
    token  (repeated)
    generation_completed
    done
"""

from __future__ import annotations

import json

RETRIEVAL_STARTED = "retrieval_started"
RETRIEVAL_COMPLETED = "retrieval_completed"
SOURCES_FOUND = "sources_found"
GENERATION_STARTED = "generation_started"
TOKEN = "token"
GENERATION_COMPLETED = "generation_completed"
ERROR = "error"
DONE = "done"


def format_event(event: str, data: dict) -> str:
    """Render one SSE message with an ``event`` name and JSON payload."""
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"
