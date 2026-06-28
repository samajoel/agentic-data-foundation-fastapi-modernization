# Implementation Plan: Data Access Layer Extraction

**Branch**: `003-data-access-layer` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-data-access-layer/spec.md`

---

## Summary

Brownfield extraction of Cosmos DB and Fabric SQL data-access logic from router modules into dedicated `app/data/` modules. The existing `history_sql.py` router embeds connection management and query primitives; `history.py` embeds `CosmosConversationClient` and its factory. Both are moved to `app/data/fabric_sql.py` and `app/data/cosmos_history.py` respectively using a hard-move strategy (no re-exports). The `chat.py` router also imports Fabric SQL symbols and must be updated. Test patch targets for `CosmosClient`, `AzureCliCredential`, and `pyodbc` must update to the new data-module paths. All existing external API behavior, authentication patterns, and test results are preserved.

---

## Technical Context

**Language/Version**: Python 3.14.3 (local dev); target runtime is Azure App Service, version per `azure.yaml`

**Primary Dependencies** (versions from `src/api/python/requirements.txt`):
- FastAPI 0.136.0
- Pydantic 2.13.3
- azure-cosmos 4.15.0
- azure-identity 1.25.3
- pyodbc 5.3.0 (system lib `unixodbc` required; env-gated on dev Mac)
- azure-ai-projects 2.1.0

**Storage**:
- Cosmos DB via `azure-cosmos` async SDK (`CosmosClient` from `azure.cosmos.aio`)
- Fabric SQL / Azure SQL via `pyodbc` + azure-identity token authentication

**Testing**: pytest (existing `pytest.ini`); flake8 (`.flake8` / `src/.flake8`); coverage (`.coveragerc`)

**Target Platform**: Azure App Service (Linux) + local macOS dev

**Project Type**: Brownfield backend refactor / web-service

**Performance Goals**: Identical to pre-refactor — this is a pure code reorganization with no logic changes

**Constraints**:
- pyodbc requires `unixodbc` system library (not installed on dev Mac — env-gated tests)
- Azure credentials required for integration tests (env-gated)
- All module-level code must be import-safe without Azure credentials (lazy init per FR-006)

---

## Constitution Check

*Pre-implementation gate. All principles assessed; no violations.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python FastAPI Backend Is the System of Record | PASS | All changes target `src/api/python/` |
| II. .NET Backend Is Retired | PASS | Not touched |
| III. External API Contract Is Stable | PASS | No endpoint changes; request/response shapes identical |
| IV. React Frontend Is Out of Scope | PASS | No frontend changes |
| V. Brownfield — Preserve Existing Behavior | PASS | Code moves, logic does not change |
| VI. No Hardcoded Credentials | PASS | Existing azure-identity patterns preserved in data modules |
| VII. Agent Orchestration Via Microsoft Agent Framework | PASS | generate_title() and Agent Framework code untouched |
| VIII. Data Access Behind a Dedicated Layer | SATISFIES | This spec directly implements Principle VIII |
| IX. Testing Via Existing pytest Configuration | PASS | pytest.ini / .flake8 / .coveragerc unchanged |
| X. New Backend Code Follows Layered Architecture | PASS | app/data/ layer populated per Principle X |
| XI. Spec Kit Workflow Is Mandatory | PASS | Implemented via spec/plan/tasks/branch workflow |
| XII. Reference Only Verified Tool Versions | PASS | All versions from requirements.txt |

*Re-check post-design: no new violations introduced by the data model or module structure.*

---

## Project Structure

### Documentation (this feature)

```text
specs/003-data-access-layer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist (all pass)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code Changes

```text
src/api/python/app/
├── data/
│   ├── __init__.py                  (empty — no change)
│   ├── fabric_sql.py                (NEW — extracted from history_sql.py)
│   └── cosmos_history.py            (NEW — extracted from history.py)
├── api/
│   └── routers/
│       ├── history_sql.py           (MODIFIED — remove data defs, add import from app.data.fabric_sql)
│       ├── history.py               (MODIFIED — remove CosmosConversationClient + factory, add import from app.data.cosmos_history)
│       └── chat.py                  (MODIFIED — update 1 import line to app.data.fabric_sql)

src/test/api/python/
├── test_history.py                  (MODIFIED — update CosmosClient patch targets + data symbol imports)
└── test_history_sql.py              (MODIFIED — update AzureCliCredential / pyodbc patch targets + direct function imports)
```

---

## Extraction Boundary

### What moves to `app/data/fabric_sql.py`

From `app/api/routers/history_sql.py`:

| Symbol | Type |
|--------|------|
| `get_azure_sql_connection()` | async function |
| `get_fabric_db_connection()` | async function |
| `get_db_connection()` | async function |
| `run_nonquery_params(sql_query, params)` | async function |
| `run_query_params(sql_query, params)` | async function |
| `SqlQueryTool` | Pydantic BaseModel |

Associated imports that move with the functions: `struct, pyodbc, AzureCliCredential, get_azure_credential_async, BaseModel, ConfigDict, Decimal, Tuple, Any, datetime, date`.

Stays in `history_sql.py`: all route handlers, `get_conversations()`, `get_conversation_messages()`, `create_conversation()`, `create_message()`, `delete_conversation()`, `delete_all_conversations()`, `rename_conversation()`, `update_conversation()`, `generate_title()`, `generate_fallback_title()`, `_generate_fallback_title_from_message()`, `track_event_if_configured()`, module-level AI/config constants.

### What moves to `app/data/cosmos_history.py`

From `app/api/routers/history.py`:

| Symbol | Type |
|--------|------|
| `CosmosConversationClient` | class |
| `init_cosmosdb_client()` | async function |
| `USE_CHAT_HISTORY_ENABLED` | module-level constant |
| `AZURE_COSMOSDB_DATABASE` | module-level constant |
| `AZURE_COSMOSDB_ACCOUNT` | module-level constant |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | module-level constant |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | module-level constant |
| `CHAT_HISTORY_ENABLED` | module-level constant |

Associated imports that move: `CosmosClient`, `azure.cosmos.exceptions`.

Stays in `history.py`: all route handlers, all service-helper functions (`add_conversation`, `update_conversation`, `rename_conversation`, `update_message_feedback`, `delete_conversation`, `get_conversations`, `get_messages`, `get_conversation_messages`, `clear_messages`, `ensure_cosmos`), `generate_title()`, `generate_fallback_title()`, `track_event_if_configured()`, AI-related constants (`AZURE_AI_AGENT_ENDPOINT`, `AGENT_NAME_TITLE`).

### What changes in `app/api/routers/chat.py`

One import line updated (around line 373):

```python
# Before:
from app.api.routers.history_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
# After:
from app.data.fabric_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
```

---

## Test Patch Target Migration

**Symbols requiring update to `app.data.cosmos_history` paths** (in `test_history.py`):

| Old patch target | New patch target | Reason |
|-----------------|-----------------|--------|
| `app.api.routers.history.CosmosClient` | `app.data.cosmos_history.CosmosClient` | CosmosClient only imported in data module after move |
| `from app.api.routers.history import init_cosmosdb_client` | `from app.data.cosmos_history import init_cosmosdb_client` | Direct isolation test |
| `from app.api.routers.history import USE_CHAT_HISTORY_ENABLED` | `from app.data.cosmos_history import USE_CHAT_HISTORY_ENABLED` | Constant moves |

Stays valid after move (router imports data symbol into its namespace):
- `from app.api.routers.history import CosmosConversationClient` — valid (router imports it)
- `patch('app.api.routers.history.init_cosmosdb_client', ...)` — valid for router-level tests

**Symbols requiring update to `app.data.fabric_sql` paths** (in `test_history_sql.py`):

| Old patch target | New patch target | Reason |
|-----------------|-----------------|--------|
| `app.api.routers.history_sql.AzureCliCredential` | `app.data.fabric_sql.AzureCliCredential` | Only imported in data module |
| `app.api.routers.history_sql.pyodbc.connect` | `app.data.fabric_sql.pyodbc.connect` | Only imported in data module |
| `from app.api.routers.history_sql import get_fabric_db_connection` (isolation tests) | `from app.data.fabric_sql import get_fabric_db_connection` | Direct function test |

Stays valid (router imports these into its namespace after extraction):
- `patch('app.api.routers.history_sql.run_query_params', ...)` — valid for router-level tests
- `patch('app.api.routers.history_sql.run_nonquery_params', ...)` — valid
- `patch('app.api.routers.history_sql.get_db_connection', ...)` — valid
- `patch('app.api.routers.history_sql.get_fabric_db_connection', ...)` — valid

---

## Implementation Phases

> Full task breakdown generated by `/speckit-tasks`. High-level phases:

**Phase 1 — Setup**: Verify baseline test pass count; confirm `app/data/__init__.py` is empty.

**Phase 2 — Create `app/data/fabric_sql.py`**: Extract the six symbols and their imports; verify clean import.

**Phase 3 — Create `app/data/cosmos_history.py`**: Extract `CosmosConversationClient`, `init_cosmosdb_client`, and the eight constants with their imports; verify clean import.

**Phase 4 — Update `history_sql.py`**: Remove moved definitions; add import from `app.data.fabric_sql`; flake8 clean.

**Phase 5 — Update `history.py`**: Remove moved definitions; add import from `app.data.cosmos_history`; flake8 clean.

**Phase 6 — Update `chat.py`**: Update one import line; flake8 clean.

**Phase 7 — Update test patch targets**: Update `test_history.py` (CosmosClient paths) and `test_history_sql.py` (AzureCliCredential, pyodbc paths, direct isolation imports).

**Phase 8 — Validate**: Run quickstart Steps 1–7; run `pytest`; confirm no new failures.

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` left behind in `history.py` after class moves | Medium | Explicit check: grep for remaining references during Phase 5 |
| Test imports `CosmosConversationClient` directly from router path — fails after move | Low | Router imports and re-exports the class via `from app.data.cosmos_history import CosmosConversationClient` — test import stays valid |
| Patch at `app.api.routers.history_sql.AzureCliCredential` silently no-ops after move | High (certain if not fixed) | quickstart Step 7 grep verifies no old paths remain |
| flake8 E501 on long import lines in data modules | Low | Split imports with parentheses if needed |
