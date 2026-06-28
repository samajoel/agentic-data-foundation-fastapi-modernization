# Research: Data Access Layer Extraction

**Feature**: 003-data-access-layer
**Date**: 2026-06-28

---

## Decision 1: Lazy Connection Initialization Pattern

**Decision**: Use per-request instantiation — each async request calls `init_cosmosdb_client()` or `get_db_connection()` at runtime, creating the client/connection fresh. No module-level client objects. No `lru_cache` or singleton for connections.

**Rationale**: The existing code already follows this pattern. `init_cosmosdb_client()` is an `async def` called inside request handlers; `get_db_connection()` is an `async def` called inside query helpers. Neither runs at module import time. Preserving this pattern satisfies FR-006 (importable without Azure credentials) with zero behavior change.

**Alternatives considered**:
- Module-level singleton with lazy `_client = None` guard: adds state that is hard to reset between test runs and introduces thread-safety concerns. Rejected — not needed for correctness, would be a behavior change.
- `functools.lru_cache` or `asyncio` cache: not applicable for async factory functions without a custom async cache layer. Rejected — out of scope.
- Eager initialization at app startup: requires a startup event hook, would break the "importable without FastAPI" requirement. Rejected.

---

## Decision 2: What Moves to `app/data/fabric_sql.py`

**Decision**: Move the infrastructure and query execution layer only. Specifically:

| Symbol | Action | Reason |
|--------|--------|--------|
| `get_azure_sql_connection()` | Move | Pure infrastructure: credentials + pyodbc |
| `get_fabric_db_connection()` | Move | Pure infrastructure: credentials + pyodbc |
| `get_db_connection()` | Move | Infrastructure dispatcher |
| `run_nonquery_params()` | Move | Query execution primitive |
| `run_query_params()` | Move | Query execution primitive |
| `SqlQueryTool` (Pydantic model) | Move | Wraps pyodbc connection; used by Agent Framework via chat.py |
| `get_conversations()` | Stay in router | Builds SQL; called by route handler; services layer in router |
| `get_conversation_messages()` | Stay in router | Same |
| `create_conversation()` | Stay in router | Same |
| `create_message()` | Stay in router | Same |
| `delete_conversation()` | Stay in router | Same |
| `delete_all_conversations()` | Stay in router | Same |
| `rename_conversation()` | Stay in router | Same |
| `update_conversation()` | Stay in router | Raises HTTPException (HTTP concern) |
| `generate_title()` | Stay in router | Agent Framework orchestration, not data access |
| `generate_fallback_title()` / `_generate_fallback_title_from_message()` | Stay in router | String logic |
| `track_event_if_configured()` | Stay in router | Observability utility |

**Rationale**: FR-001 specifies "connection creation, parameterized query execution, and parameterized non-query execution" as the extraction targets. Pulling higher-level SQL-building functions is out of scope for Spec 003 (would require a service layer extraction, which the spec explicitly excludes). Keeping them in the router lets the route handlers delegate without direct SQL calls.

**Alternatives considered**:
- Extract all SQL-building functions to data module: valid but out of spec scope — would require updating many more test patch targets and blurs the line with service extraction. Deferred to a future spec.

---

## Decision 3: What Moves to `app/data/cosmos_history.py`

**Decision**: Move the Cosmos DB client class, its factory, and all Cosmos-specific configuration constants. Keep all service-helper wrapper functions in the router.

| Symbol | Action | Reason |
|--------|--------|--------|
| `CosmosConversationClient` | Move | Core data entity — wraps all CosmosDB SDK calls |
| `init_cosmosdb_client()` | Move | Factory for `CosmosConversationClient`; pure data infrastructure |
| `AZURE_COSMOSDB_DATABASE` | Move | Used only by `init_cosmosdb_client()` and `CosmosConversationClient` |
| `AZURE_COSMOSDB_ACCOUNT` | Move | Same |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | Move | Same |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | Move | Used inside `CosmosConversationClient.create_message()` |
| `CHAT_HISTORY_ENABLED` | Move | Guards `init_cosmosdb_client()` — belongs with the factory |
| `USE_CHAT_HISTORY_ENABLED` | Move | Component of `CHAT_HISTORY_ENABLED` — move together |
| `add_conversation()` | Stay in router | Orchestrates Cosmos ops + has `ValueError` logic |
| `update_conversation()` | Stay in router | Raises `HTTPException` |
| `rename_conversation()` | Stay in router | Raises `HTTPException` |
| `update_message_feedback()` | Stay in router | Service orchestration |
| `delete_conversation()` | Stay in router | Service orchestration |
| `get_conversations()` | Stay in router | Service orchestration |
| `get_messages()` | Stay in router | Service orchestration |
| `get_conversation_messages()` | Stay in router | Service orchestration |
| `clear_messages()` | Stay in router | Service orchestration |
| `ensure_cosmos()` | Stay in router | Service orchestration |
| `generate_title()` | Stay in router | Agent Framework orchestration |
| `generate_fallback_title()` | Stay in router | String logic |
| `track_event_if_configured()` | Stay in router | Observability utility |

**Rationale**: FR-002 specifies "Cosmos DB client class and all Cosmos DB account configuration reading" as the extraction target. The service-helper functions (`add_conversation`, etc.) use the data module via `init_cosmosdb_client()`, which is a clean data-layer invocation. Service extraction is explicitly out of scope.

---

## Decision 4: chat.py Is in Scope (FR-011 Triggered)

**Decision**: `chat.py` must be updated. It currently imports at line 373:
```python
from app.api.routers.history_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
```
After the hard move, these symbols will be in `app.data.fabric_sql`, not `app.api.routers.history_sql`. The import must update to:
```python
from app.data.fabric_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
```

**Rationale**: FR-011 states chat.py MUST NOT be modified unless Cosmos/SQL imports are found there. This inspection found such imports. The update is required and tightly scoped — one line, no behavior change.

---

## Decision 5: Test Patch Target Migration Strategy

**Decision**: Two categories of patch updates are needed.

**Category A — Symbols moving to `app/data/cosmos_history.py`**:
All `patch('app.api.routers.history.CosmosClient', ...)` calls must become `patch('app.data.cosmos_history.CosmosClient', ...)`. After the move, `CosmosClient` is only imported inside the data module — it is NOT re-imported into `history.py`'s namespace. There are ~20+ such patches in `test_history.py`.

Also: `from app.api.routers.history import CosmosConversationClient` in test code — after the hard move, `history.py` imports `CosmosConversationClient` from the data module, making it accessible at `app.api.routers.history.CosmosConversationClient`. These test imports remain valid.

Test imports/patches of `init_cosmosdb_client`, `USE_CHAT_HISTORY_ENABLED` at the history router path → update to `app.data.cosmos_history` path.

**Category B — Symbols moving to `app/data/fabric_sql.py`**:
After the move, `history_sql.py` will `from app.data.fabric_sql import get_fabric_db_connection, get_azure_sql_connection, get_db_connection, run_nonquery_params, run_query_params, SqlQueryTool`. This puts all of them in `history_sql.py`'s namespace. Patches at `app.api.routers.history_sql.run_query_params` (etc.) remain valid for tests that test router-level functions.

However, `AzureCliCredential` and `pyodbc` are NOT re-imported into `history_sql.py` after extraction — they are only in `app.data.fabric_sql`. So:
- `patch('app.api.routers.history_sql.AzureCliCredential', ...)` → `patch('app.data.fabric_sql.AzureCliCredential', ...)`
- `patch('app.api.routers.history_sql.pyodbc.connect', ...)` → `patch('app.data.fabric_sql.pyodbc.connect', ...)`

Direct function imports like `from app.api.routers.history_sql import get_fabric_db_connection` → update to `from app.data.fabric_sql import get_fabric_db_connection` in tests that test those functions in isolation.

**Scope**: ~245 lines in `test_history.py` and ~280 lines in `test_history_sql.py` reference old paths. The subset requiring actual changes is smaller (~20-30 lines per file) because most patches are for functions/names that remain in the router namespace.

---

## Decision 6: Circular Import Prevention

**Decision**: Both data modules import only from `app/core/` (specifically `app.core.auth.azure_credential_utils`) and external/standard-library packages. Neither imports from `app/api/routers/`.

**Verification**: `app.core.auth.azure_credential_utils` has no imports from `app.api.*` (confirmed by Spec 002 package structure). Import chain:
```
app.api.routers.history_sql → app.data.fabric_sql → app.core.auth.azure_credential_utils
app.api.routers.history     → app.data.cosmos_history → app.core.auth.azure_credential_utils
app.api.routers.chat        → app.data.fabric_sql → app.core.auth.azure_credential_utils
```
No cycles. ✅

---

## Decision 7: flake8 Import Order Compliance

**Decision**: Follow the existing flake8 import ordering convention established in Spec 002: stdlib → third-party → local (`app.*`). The `app.data.*` imports will appear in the local block after existing `app.core.*` imports in the router files.

**Rationale**: Consistent with `.flake8` config and existing router files.
