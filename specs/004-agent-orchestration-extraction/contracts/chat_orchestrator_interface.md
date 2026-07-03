# Interface Contract: `app/agents/chat_orchestrator`

**Spec**: 004 — Agent Orchestration Layer Extraction
**Date**: 2026-06-28
**Status**: Internal module interface (not a public HTTP API)

This document defines the public interface of the `app/agents/chat_orchestrator` module.
The only external caller is `app/api/routers/chat.py`.

---

## Module Import Contract

```python
from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured
```

The module MUST be importable without:
- Starting the FastAPI application
- Opening database or network connections
- Requiring environment variables to be set

All connection and credential acquisition happens lazily inside function bodies (async
functions), not at module import time.

---

## Public Functions

### `stream_chat_request`

**Signature**:
```
async stream_chat_request(
    conversation_id: str,
    query: str,
    user_id: str = "",
    user_assertion: str | None = None,
) -> AsyncGenerator
```

**Returns**: An async generator that yields JSON-encoded `str` lines (newline-separated).

**Line format — workshop mode** (`IS_WORKSHOP = True`):
```json
{"choices": [{"delta": {"role": "assistant"|"tool", "content": "<text>"}}]}
```
Followed by a tool-role line with JSON-encoded citation list.

**Line format — non-workshop mode** (`IS_WORKSHOP = False`):
```json
{"choices": [{"messages": [{"role": "assistant", "content": "<accumulated_text>"}]}]}
```

**Error lines** (both modes, on `HTTPException`):
```json
{"error": "<human-readable message>"}
```

**Behavior**:
- Selects `stream_openai_text_workshop` when `IS_WORKSHOP` is true, `stream_openai_text`
  otherwise.
- Catches `HTTPException` (rate limit, bad gateway) and converts to JSON error lines.
- Catches all other exceptions and yields a generic error JSON line.

**Caller contract**: The router wraps the returned generator in `StreamingResponse` with
`media_type="application/json-lines"`.

---

### `track_event_if_configured`

**Signature**:
```
track_event_if_configured(event_name: str, event_data: dict) -> None
```

**Behavior**:
- If `APPLICATIONINSIGHTS_CONNECTION_STRING` env var is set and non-empty, calls
  `azure.monitor.events.extension.track_event(event_name, event_data)`.
- Otherwise logs a warning and returns without error.

**Caller contract**: The router calls this directly for three lifecycle events:
`ChatRequestReceived`, `ChatStreamSuccess`, `ChatRequestError`.

---

## Internal-Only Symbols (not imported by the router)

These are internal to the orchestrator and MUST NOT be imported by callers outside
`app/agents/`:

| Symbol | Type | Purpose |
|--------|------|---------|
| `ExpCache` | class | Azure AI thread lifecycle TTL cache |
| `get_thread_cache` | function | Lazy global cache initializer |
| `stream_openai_text` | async generator | Non-workshop OpenAI Responses API path |
| `stream_openai_text_workshop` | async generator | Workshop FoundryAgent path |
| `_parse_mcp_docs` | function | MCP citation document parser |
| `_extract_mcp_from_raw` | function | MCP raw representation traversal |
| `_MARKER_RE` | compiled regex | MCP citation marker pattern |

These symbols are considered private implementation details. Tests that directly unit-test
these symbols import them from `app.agents.chat_orchestrator` explicitly — this is
acceptable for test coverage purposes.

---

## Dependencies of `chat_orchestrator`

The module imports from these allowed layers:

| Module | Layer | Used by |
|--------|-------|---------|
| `app.core.auth.azure_credential_utils` | core | `stream_openai_text`, `stream_openai_text_workshop`, `ExpCache._delete_thread_async` |
| `app.data.fabric_sql` | data | `stream_openai_text` (SqlQueryTool, get_db_connection), `stream_openai_text_workshop` (SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection) |

The module does NOT import from:
- `app.api.*` — no FastAPI dependency at module level
- `app.data.cosmos_history` — Cosmos history is managed by `app/api/routers/history.py`
  and `app/api/routers/history_sql.py`, not by the chat orchestrator directly
