# Data Model: Data Access Layer Extraction

**Feature**: 003-data-access-layer
**Date**: 2026-06-28

This spec does not introduce new database schemas, tables, containers, or document shapes. The data model describes the **module entities** introduced — the Python objects and callable interfaces that form the extracted data access layer.

---

## Entities

### 1. `FabricSQLModule` (`app/data/fabric_sql.py`)

The Fabric SQL data module. Encapsulates all pyodbc-based connectivity and query execution for Fabric SQL and Azure SQL (workshop mode).

**Public interface:**

| Symbol | Type | Description |
|--------|------|-------------|
| `get_azure_sql_connection()` | `async def → pyodbc.Connection \| None` | Creates an Azure SQL Server connection using azure-identity token auth |
| `get_fabric_db_connection()` | `async def → pyodbc.Connection \| None` | Creates a Fabric SQL connection using AzureCliCredential (dev) or MSI (prod) |
| `get_db_connection()` | `async def → pyodbc.Connection \| None` | Dispatcher: routes to Azure SQL (IS_WORKSHOP=true) or Fabric SQL |
| `run_nonquery_params(sql_query, params)` | `async def → bool` | Executes INSERT/UPDATE/DELETE; returns True on success |
| `run_query_params(sql_query, params)` | `async def → list[dict] \| None` | Executes SELECT; returns rows as list of dicts with type coercion |
| `SqlQueryTool` | `pydantic.BaseModel` | Wraps a pyodbc.Connection for Agent Framework use; exposes `run_sql_query` / `execute_sql` |

**Environment variables read (inside functions, not at import time)**:

| Variable | Used by |
|----------|---------|
| `AZURE_SQLDB_SERVER` / `SQLDB_SERVER` | `get_azure_sql_connection` |
| `AZURE_SQLDB_DATABASE` / `SQLDB_DATABASE` | `get_azure_sql_connection` |
| `API_UID` | `get_azure_sql_connection`, `get_fabric_db_connection` |
| `APP_ENV` | `get_fabric_db_connection` (dev vs prod branching) |
| `FABRIC_SQL_DATABASE` | `get_fabric_db_connection` |
| `FABRIC_SQL_SERVER` | `get_fabric_db_connection` |
| `FABRIC_SQL_CONNECTION_STRING` | `get_fabric_db_connection` |
| `IS_WORKSHOP` | `get_db_connection` |
| `AZURE_ENV_ONLY` | `get_db_connection` |

**Imports (no circular risk)**:
- stdlib: `json, logging, os, struct, uuid, datetime, date, Decimal, Tuple, Any`
- third-party: `pyodbc`, `azure.identity.aio.AzureCliCredential`, `pydantic.BaseModel`, `pydantic.ConfigDict`
- local: `app.core.auth.azure_credential_utils.get_azure_credential_async`

---

### 2. `CosmosHistoryModule` (`app/data/cosmos_history.py`)

The Cosmos DB data module. Encapsulates the async Cosmos DB client class and its factory, together with all Cosmos-specific configuration.

**Public interface:**

| Symbol | Type | Description |
|--------|------|-------------|
| `CosmosConversationClient` | `class` | Async client wrapping azure-cosmos SDK; manages conversations and messages |
| `init_cosmosdb_client()` | `async def → CosmosConversationClient \| None` | Factory: reads env vars and instantiates client; returns None if Cosmos is not configured |
| `USE_CHAT_HISTORY_ENABLED` | `bool` constant | `os.getenv("USE_CHAT_HISTORY_ENABLED", "false")` |
| `AZURE_COSMOSDB_DATABASE` | `str \| None` constant | `os.getenv("AZURE_COSMOSDB_DATABASE")` |
| `AZURE_COSMOSDB_ACCOUNT` | `str \| None` constant | `os.getenv("AZURE_COSMOSDB_ACCOUNT")` |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | `str \| None` constant | `os.getenv("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER")` |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | `bool` constant | `os.getenv("AZURE_COSMOSDB_ENABLE_FEEDBACK", "false")` |
| `CHAT_HISTORY_ENABLED` | `bool` constant | Composite: all four Cosmos env vars set AND `USE_CHAT_HISTORY_ENABLED` |

**`CosmosConversationClient` methods:**

| Method | Return type | Description |
|--------|-------------|-------------|
| `__init__(cosmosdb_endpoint, credential, database_name, container_name, enable_message_feedback)` | `None` | Instantiates CosmosClient, database client, container client |
| `ensure()` | `async → (bool, str)` | Verifies connectivity and accessibility |
| `create_conversation(user_id, conversation_id, title)` | `async → dict \| False` | Upserts a conversation document |
| `upsert_conversation(conversation)` | `async → dict \| False` | Updates a conversation document |
| `delete_conversation(user_id, conversation_id)` | `async → None` | Deletes a conversation document |
| `delete_messages(conversation_id, user_id)` | `async → list` | Deletes all message documents for a conversation |
| `get_conversations(user_id, limit, sort_order, offset)` | `async → list[dict]` | Lists conversations by userId |
| `get_conversation(user_id, conversation_id)` | `async → dict \| None` | Gets a single conversation |
| `create_message(uuid, conversation_id, user_id, input_message)` | `async → dict \| False \| str` | Creates a message document; updates parent conversation |
| `update_message_feedback(user_id, message_id, feedback)` | `async → dict \| False` | Updates feedback field on a message |
| `get_messages(user_id, conversation_id)` | `async → list[dict]` | Gets all messages for a conversation |

**Environment variables read at module level** (these are `os.getenv()` calls — no network/credentials required at import time):

| Variable | Default |
|----------|---------|
| `USE_CHAT_HISTORY_ENABLED` | `"false"` |
| `AZURE_COSMOSDB_DATABASE` | `None` |
| `AZURE_COSMOSDB_ACCOUNT` | `None` |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | `None` |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | `"false"` |

**Note on lazy init**: Module-level `os.getenv()` reads are safe at import time (no network calls, no Azure credentials required). The `CosmosClient` object is only created inside `CosmosConversationClient.__init__()`, which is only called by `init_cosmosdb_client()`, which is `async` and called per-request.

**Imports (no circular risk)**:
- stdlib: `datetime, logging, os, uuid`
- third-party: `azure.cosmos.aio.CosmosClient`, `azure.cosmos.exceptions`
- local: `app.core.auth.azure_credential_utils.get_azure_credential_async`

---

## Updated Module Interfaces

### `app/api/routers/history_sql.py` (after extraction)

Adds import:
```python
from app.data.fabric_sql import (
    get_azure_sql_connection,
    get_fabric_db_connection,
    get_db_connection,
    run_nonquery_params,
    run_query_params,
    SqlQueryTool,
)
```

Removes: definitions of `get_azure_sql_connection`, `get_fabric_db_connection`, `get_db_connection`, `run_nonquery_params`, `run_query_params`, `SqlQueryTool`, and their associated stdlib/third-party imports (`struct, pyodbc, BaseModel, ConfigDict, Decimal, AzureCliCredential, get_azure_credential_async`).

---

### `app/api/routers/history.py` (after extraction)

Adds import:
```python
from app.data.cosmos_history import CosmosConversationClient, init_cosmosdb_client
```

Removes: `CosmosConversationClient` class definition, `init_cosmosdb_client()` function, all six `AZURE_COSMOSDB_*` / `CHAT_HISTORY_ENABLED` / `USE_CHAT_HISTORY_ENABLED` module-level constants, and their associated third-party imports (`CosmosClient`, `azure.cosmos.exceptions`).

---

### `app/api/routers/chat.py` (after extraction)

Updates line ~373 from:
```python
from app.api.routers.history_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
```
To:
```python
from app.data.fabric_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection
```

---

## Persistence Store Schemas (Unchanged)

These are NOT modified by Spec 003:

**Fabric SQL tables** (in Fabric workspace):
- `hst_conversations (userId, conversation_id, title, createdAt, updatedAt)`
- `hst_conversation_messages (userId, conversation_id, role, content_id, content, citations, feedback, createdAt, updatedAt)`

**Cosmos DB container** (configured via `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER`):
- Conversation document shape: `{id, type, createdAt, updatedAt, userId, title, conversation_id}`
- Message document shape: `{id, type, userId, createdAt, updatedAt, conversationId, role, content, feedback?}`
- Partition key: `userId`
