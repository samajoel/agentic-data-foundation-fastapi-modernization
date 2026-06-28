# API Contract: Python FastAPI Backend

**Status**: Stable — must not change as part of this consolidation
**Source**: `src/api/python/app.py`, `chat.py`, `history.py`, `history_sql.py`
**Date documented**: 2026-06-27

This document records the existing Python FastAPI API surface that the React frontend
depends on. All routes listed here MUST continue to function identically after the
.NET backend and Copilot Studio artifacts are removed.

---

## Router Prefixes

| Router module | Prefix | Tag |
|---------------|--------|-----|
| `chat.py` | `/api` | chat |
| `history.py` | `/history` | history |
| `history_sql.py` | `/historyfab` | historyfab |

---

## Chat Routes (`/api`)

### POST /api/chat

Primary conversational endpoint consumed by the React frontend.

**Request**: JSON body containing `conversation_id`, user query, and optional user
assertion fields.

**Response**: Server-sent event stream (streaming response) delivering agent-generated
answer chunks drawn from Fabric-connected enterprise data.

### POST /api/fetch-azure-search-content

Internal search content fetch used by the chat flow.

---

## History Routes (`/history`)

Cosmos DB–backed conversation history (used when Cosmos DB is configured).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/history/generate` | Create a new conversation |
| POST | `/history/update` | Append a message to an existing conversation |
| POST | `/history/message_feedback` | Record thumbs-up/down feedback on a message |
| DELETE | `/history/delete` | Delete a specific conversation |
| GET | `/history/list` | List conversations for a user |
| GET | `/history/read` | Read messages in a conversation |
| POST | `/history/rename` | Rename a conversation |
| DELETE | `/history/delete_all` | Delete all conversations for a user |
| POST | `/history/clear` | Clear messages in a conversation |
| GET | `/history/ensure` | Ensure the Cosmos DB container is initialised |

---

## History Fabric Routes (`/historyfab`)

SQL Database in Fabric–backed conversation history (used when Fabric SQL is configured).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/historyfab/list` | List conversations for a user |
| GET | `/historyfab/read` | Read messages in a conversation |
| DELETE | `/historyfab/delete` | Delete a specific conversation |
| DELETE | `/historyfab/delete_all` | Delete all conversations for a user |
| POST | `/historyfab/rename` | Rename a conversation |
| POST | `/historyfab/update` | Append a message to a conversation |

---

## System Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check; returns `{"status": "healthy"}` |

---

## Stability Guarantee

This consolidation MUST NOT alter any of the above routes, their HTTP methods, request
shapes, response shapes, or HTTP status codes. The React frontend is not being modified;
any change here would silently break the UI.

Changes to this contract require a separate spec with explicit versioning approval.
