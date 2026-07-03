# Implementation Plan: Agent Orchestration Layer Extraction

**Branch**: `modernization-fastapi-speckit` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-agent-orchestration-extraction/spec.md`

## Summary

Extract non-HTTP agent orchestration logic from `app/api/routers/chat.py` (766 lines) into
a new `app/agents/chat_orchestrator.py` module. The chat router shrinks to ~235 lines and
retains only FastAPI route definitions, request/response handling, and authentication
delegation. The orchestrator module takes ownership of `ExpCache`, thread-cache management,
`stream_openai_text`, `stream_openai_text_workshop`, `stream_chat_request`,
`track_event_if_configured`, and all supporting helpers.

All POST /api/chat behavior is preserved exactly. Test patch targets in `test_chat.py` are
migrated to the new module path following the Spec 003 precedent: patch where the name is
looked up at call time.

No new dependencies, no schema changes, no frontend or infrastructure changes.

## Technical Context

**Language/Version**: Python — version pinned in `src/api/python/requirements.txt`

**Primary Dependencies**:
- FastAPI 0.136.0
- agent-framework-foundry 1.3.0, agent-framework-core 1.3.0
- azure-ai-projects 2.1.0, azure-ai-agents 1.2.0b5
- azure-identity 1.25.3
- cachetools 7.0.6
- opentelemetry-api/sdk 1.40.0, azure-monitor-events-extension 0.1.0
- pytest 9.0.3, pytest-asyncio 1.3.0

**Storage**: No new storage. Existing layers:
- Cosmos DB — `app/data/cosmos_history.py`
- Fabric SQL — `app/data/fabric_sql.py`

**Testing**: pytest via `.venv/bin/pytest` from repo root; flake8 per `.flake8`

**Target Platform**: Azure Container Apps (as defined in `azure.yaml` / `infra/`)

**Project Type**: web-service (FastAPI backend)

**Performance Goals**: Identical to pre-refactor — pure structural move, no algorithmic
changes.

**Constraints**: flake8 zero violations on `app/`, 268+ passing tests (Spec 003 baseline),
no new imports or packages introduced.

**Scale/Scope**: Single module extraction; one test file patch-target migration.

## Constitution Check

*GATE: All 12 principles verified before Phase 0. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python FastAPI Is System of Record | ✓ PASS | All changes target `src/api/python/` |
| II. .NET Backend Is Retired | ✓ PASS | Not touched |
| III. External API Contract Is Stable | ✓ PASS | POST /api/chat behavior identical |
| IV. React Frontend Is Out of Scope | ✓ PASS | Not touched |
| V. Brownfield — Preserve Existing Behavior | ✓ PASS | Behavior-preserving structural move |
| VI. No Hardcoded Credentials | ✓ PASS | Existing azure-identity pattern preserved |
| VII. Agent Orchestration Via MS Agent Framework | ✓ PASS | FoundryAgent + azure-ai-projects intact |
| VIII. Data Access Behind Dedicated Layer | ✓ PASS | app/data/fabric_sql.py and app/data/cosmos_history.py; orchestrator never opens direct connections |
| IX. Testing Via Existing pytest Config | ✓ PASS | pytest 9.0.3, .flake8, .coveragerc unchanged |
| X. Layered Architecture | ✓ PASS | Orchestration moves to agent layer; router stays in api layer |
| XI. Spec Kit Workflow Mandatory | ✓ PASS | This plan is the Spec Kit artifact for Spec 004 |
| XII. Reference Verified Versions Only | ✓ PASS | All versions from requirements.txt |

**Gate result**: PASS — no violations, no Complexity Tracking entries needed.

**Post-Phase 1 re-check**: All principles remain satisfied. The internal
`chat_orchestrator.py` module has no FastAPI imports at top level (Constitution Principle X)
and does not bypass the data layer (Principle VIII). See `contracts/` for the module
interface.

## Project Structure

### Documentation (this feature)

```text
specs/004-agent-orchestration-extraction/
├── plan.md               # This file
├── research.md           # Phase 0 — decision log
├── quickstart.md         # Phase 1 — validation guide
├── contracts/
│   └── chat_orchestrator_interface.md   # Phase 1 — orchestrator public API
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

No `data-model.md` — this spec introduces no new data entities.

### Source Code (changed files only)

```text
src/api/python/
├── app/
│   ├── agents/
│   │   ├── __init__.py               # UNCHANGED (remains empty)
│   │   └── chat_orchestrator.py      # NEW — extracted orchestration logic
│   └── api/
│       └── routers/
│           └── chat.py               # MODIFIED — HTTP concerns only (~235 lines)
└── (no other app/ changes)

src/test/api/python/
└── test_chat.py                      # MODIFIED — patch targets updated
```

## Extraction Boundary

### Symbols that move to `app/agents/chat_orchestrator.py`

| Symbol | Type | Notes |
|--------|------|-------|
| `load_dotenv()` call | module init | loads .env at import time |
| `IS_WORKSHOP` | module constant | used by `stream_chat_request` |
| `AZURE_ENV_ONLY` | module constant | used by `stream_openai_text_workshop` |
| `USE_USER_ACCESS_TOKEN` | module constant | used by both stream functions |
| `agent_log_level` + `logging.getLogger("agent_framework_foundry").setLevel(...)` | module init | agent framework log level config |
| `ExpCache` | class | Azure AI thread lifecycle cache (inherits TTLCache) |
| `track_event_if_configured` | function | App Insights telemetry helper |
| `thread_cache` | module global | `None` init, populated lazily |
| `get_thread_cache` | function | lazy init of `thread_cache` |
| `stream_openai_text` | async generator | non-workshop OpenAI Responses API orchestration |
| `_MARKER_RE` | compiled regex | MCP citation marker pattern |
| `_parse_mcp_docs` | function | parse JSON blocks from MCP output |
| `_extract_mcp_from_raw` | function | traverse raw_representation for MCP docs |
| `stream_openai_text_workshop` | async generator | workshop FoundryAgent orchestration |
| `stream_chat_request` | async function | dispatcher — workshop vs non-workshop |

### Symbols that stay in `app/api/routers/chat.py`

| Symbol | Type | Notes |
|--------|------|-------|
| `HOST_NAME` | constant | not used in any logic; test imports it from here |
| `HOST_INSTRUCTIONS` | constant | not used in any logic; test imports it from here |
| `router` | APIRouter | all route definitions |
| `logger` | logger | router-level logger |
| `fetch_azure_search_content` | route handler | pure HTTP; SSRF-protected Azure Search fetch |
| `conversation` | route handler | pure HTTP; delegates to `stream_chat_request` |

### What `chat.py` imports from the orchestrator (new)

```python
from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured
```

### What `chat.py` removes (no longer needed after extraction)

These imports are removed from `chat.py` because the symbols that used them have moved:

- `import json` — only used in orchestration
- `import random` — only used in orchestration
- `import re` — only used in orchestration
- `from cachetools import TTLCache`
- `from dotenv import load_dotenv`
- `from azure.core.exceptions import HttpResponseError`
- `from azure.monitor.events.extension import track_event`
- `from azure.ai.projects.aio import AIProjectClient`
- `from agent_framework_foundry import FoundryAgent`

These STAY in `chat.py` because they are used by the remaining route handlers:

- `import asyncio` — used by `fetch_azure_search_content` (`asyncio.to_thread`)
- `import os` — used by `fetch_azure_search_content` (os.getenv)
- `import logging` — used by the router-level `logger`
- `from fastapi import APIRouter, Request, HTTPException, status`
- `from fastapi.responses import JSONResponse, StreamingResponse`
- `from opentelemetry import trace` + `from opentelemetry.trace import Status, StatusCode`
- `from app.core.auth.auth_utils import get_authenticated_user_details`
- `from app.core.auth.azure_credential_utils import get_azure_credential_async`

## Test Patch Target Migration

**Rule** (from Spec 003 precedent): Patch where the name is looked up at call time, not
where it was originally defined. Functions in `chat_orchestrator.py` look up their
dependencies in the orchestrator's module namespace.

### Patch targets that change to `app.agents.chat_orchestrator.*`

| Old target | New target | Reason |
|-----------|-----------|--------|
| `app.api.routers.chat.asyncio.create_task` | `app.agents.chat_orchestrator.asyncio.create_task` | `ExpCache.expire/popitem` uses asyncio from orchestrator |
| `app.api.routers.chat.get_azure_credential_async` *(stream/ExpCache tests only)* | `app.agents.chat_orchestrator.get_azure_credential_async` | `stream_openai_text`, `stream_openai_text_workshop`, `ExpCache._delete_thread_async` |
| `app.api.routers.chat.AIProjectClient` | `app.agents.chat_orchestrator.AIProjectClient` | all stream functions and `_delete_thread_async` |
| `app.api.routers.chat.FoundryAgent` | `app.agents.chat_orchestrator.FoundryAgent` | `stream_openai_text_workshop` |
| `app.api.routers.chat.get_thread_cache` | `app.agents.chat_orchestrator.get_thread_cache` | `stream_openai_text`, `stream_openai_text_workshop` |
| `app.api.routers.chat.track_event` | `app.agents.chat_orchestrator.track_event` | `track_event_if_configured` in orchestrator |
| `app.api.routers.chat.logging.warning` *(in track_event tests)* | `app.agents.chat_orchestrator.logging.warning` | `track_event_if_configured` uses `logging` from orchestrator |
| `app.api.routers.chat.stream_openai_text` *(in stream_chat_request tests)* | `app.agents.chat_orchestrator.stream_openai_text` | `stream_chat_request` calls it from orchestrator namespace |
| `app.api.routers.chat.stream_openai_text_workshop` *(in stream_chat_request tests)* | `app.agents.chat_orchestrator.stream_openai_text_workshop` | `stream_chat_request` calls it from orchestrator namespace |
| `app.api.routers.chat.IS_WORKSHOP` | `app.agents.chat_orchestrator.IS_WORKSHOP` | `stream_chat_request` reads it from orchestrator namespace |

### Patch targets that stay as `app.api.routers.chat.*` (no change)

| Target | Reason |
|--------|--------|
| `app.api.routers.chat.stream_chat_request` | `chat.py` re-imports it; binding exists in router namespace |
| `app.api.routers.chat.track_event_if_configured` *(in `conversation` route tests)* | `chat.py` re-imports it; binding exists in router namespace |
| `app.api.routers.chat.get_azure_credential_async` *(fetch_azure_search_content tests)* | `get_azure_credential_async` stays in `chat.py` for the fetch route |
| `app.api.routers.chat.asyncio.to_thread` | `asyncio` stays in `chat.py` for `fetch_azure_search_content` |
| `app.api.routers.chat.get_authenticated_user_details` | stays in `chat.py` |

### Direct `from app.api.routers.chat import X` test imports that must change

| Symbol | New import |
|--------|-----------|
| `ExpCache` | `from app.agents.chat_orchestrator import ExpCache` |
| `track_event_if_configured` *(direct call tests)* | `from app.agents.chat_orchestrator import track_event_if_configured` |
| `get_thread_cache` | `from app.agents.chat_orchestrator import get_thread_cache` |
| `stream_openai_text` | `from app.agents.chat_orchestrator import stream_openai_text` |
| `stream_openai_text_workshop` | `from app.agents.chat_orchestrator import stream_openai_text_workshop` |
| `_parse_mcp_docs` | `from app.agents.chat_orchestrator import _parse_mcp_docs` |
| `_extract_mcp_from_raw` | `from app.agents.chat_orchestrator import _extract_mcp_from_raw` |
| `_MARKER_RE` | `from app.agents.chat_orchestrator import _MARKER_RE` |

### Direct imports that stay as `from app.api.routers.chat import X` (no change)

| Symbol | Reason |
|--------|--------|
| `HOST_NAME`, `HOST_INSTRUCTIONS` | stays in `chat.py` |
| `router` | stays in `chat.py` |
| `stream_chat_request` *(direct call tests)* | `chat.py` re-imports it; binding valid |
| `conversation` | stays in `chat.py` |
| `fetch_azure_search_content` | stays in `chat.py` |

## Validation Notes

- **Streaming generator ownership**: `stream_openai_text` and `stream_openai_text_workshop`
  are async generators that yield text chunks. They are called by `stream_chat_request`,
  which is called by the `conversation` route handler. The `StreamingResponse` wrapper
  stays in the route handler. The yield chain is unchanged.

- **Logging placement**: Logging calls that are currently inline in orchestration functions
  (e.g., `logger.info` inside `stream_openai_text`) move with those functions to the
  orchestrator. The orchestrator module will have its own `logger = logging.getLogger(__name__)`.
  The router retains its own logger. This is not an observability overhaul — it preserves
  existing logging behavior.

- **`load_dotenv()` placement**: Moves to `chat_orchestrator.py` since all the env vars it
  loads are consumed there. The router no longer calls `load_dotenv()` directly, but since
  the orchestrator is imported at startup, `load_dotenv()` still fires before any request
  is processed.

- **Flake8 check scope**: Run `flake8 app/` with the existing `.flake8` configuration.
  Watch for: unused imports in the modified `chat.py`, line-length issues in long
  conditional expressions, and E303/E305 blank-line issues after large blocks are removed.

## Complexity Tracking

No constitution violations. Not applicable.
