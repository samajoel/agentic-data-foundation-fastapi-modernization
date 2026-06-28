# Quickstart Validation Guide: Data Access Layer Extraction

**Feature**: 003-data-access-layer
**Date**: 2026-06-28

This guide documents how to validate the data access extraction without requiring Azure credentials or a live Cosmos DB / Fabric SQL instance. All checks run in the existing local dev environment after Spec 002.

---

## Prerequisites

```bash
cd src/api/python
pip install -r requirements.txt   # already installed from Spec 002
```

Environment: no `.env` file or Azure credentials required for Steps 1–4.

---

## Step 1 — Data Modules Are Importable Without Azure Credentials

Verify FR-006: both data modules import cleanly without any network calls.

```bash
cd src/api/python
python -c "
import app.data.fabric_sql as fs
print('fabric_sql OK')
print('  functions:', [x for x in dir(fs) if not x.startswith('_')])

import app.data.cosmos_history as ch
print('cosmos_history OK')
print('  CosmosConversationClient:', ch.CosmosConversationClient)
print('  init_cosmosdb_client:', ch.init_cosmosdb_client)
"
```

**Expected output**: Both modules print without error. No `ImportError`, no `AttributeError`. Functions and classes listed.

---

## Step 2 — Router Modules Still Import After Extraction

Verify hard-move is complete and routers import cleanly from new paths.

```bash
cd src/api/python
python -c "
# Patch pyodbc so import doesn't fail on missing system library
import sys, types
sys.modules['pyodbc'] = types.ModuleType('pyodbc')
sys.modules['pyodbc'].Connection = object
sys.modules['pyodbc'].Error = Exception

from app.api.routers import history_sql, history, chat
print('history_sql router OK')
print('history router OK')
print('chat router OK')

# Verify data symbols are not defined in old locations
import inspect
assert not any(
    x.__module__ == 'app.api.routers.history_sql'
    for x in [history_sql.run_query_params, history_sql.get_fabric_db_connection]
), 'Functions still defined in router — hard move incomplete'
print('Hard move verified: data functions not defined in router namespace')
"
```

**Expected output**: All three routers import. The assertion confirming functions are NOT defined in the router module passes.

---

## Step 3 — chat.py Uses New Data Module Paths

Verify chat.py no longer imports from `app.api.routers.history_sql`.

```bash
cd src/api/python
grep -n "from app.api.routers.history_sql import" app/api/routers/chat.py
```

**Expected output**: No lines printed. (The import moved to `from app.data.fabric_sql import ...`)

```bash
grep -n "from app.data.fabric_sql import" app/api/routers/chat.py
```

**Expected output**: One line showing the updated import.

---

## Step 4 — No Old Data Symbols Defined in Router Files

Verify the hard-move boundary for both routers.

```bash
cd src/api/python
python -c "
import sys, types
sys.modules['pyodbc'] = types.ModuleType('pyodbc')
sys.modules['pyodbc'].Connection = object
sys.modules['pyodbc'].Error = Exception

import app.data.fabric_sql as fs
import app.data.cosmos_history as ch
from app.api.routers import history_sql, history

# fabric_sql data symbols should not be DEFINED in history_sql router
import inspect
for sym in ['get_fabric_db_connection', 'get_db_connection', 'run_query_params', 'run_nonquery_params']:
    obj = getattr(history_sql, sym)
    mod = getattr(obj, '__module__', None)
    assert mod == 'app.data.fabric_sql', f'{sym}.__module__ is {mod!r}, expected app.data.fabric_sql'
    print(f'{sym}: defined in app.data.fabric_sql ✓')

# cosmos symbols should not be DEFINED in history router
for sym in ['CosmosConversationClient', 'init_cosmosdb_client']:
    obj = getattr(history, sym)
    mod = getattr(obj, '__module__', None)
    assert mod == 'app.data.cosmos_history', f'{sym}.__module__ is {mod!r}, expected app.data.cosmos_history'
    print(f'{sym}: defined in app.data.cosmos_history ✓')
"
```

**Expected output**: Each symbol prints with `✓` and no assertion error.

---

## Step 5 — Existing Unit Tests Pass (No New Failures)

Run the unit test suite against the refactored code. The environment-gated failures (pyodbc system library, Azure connectivity) are expected; no NEW failures should appear.

```bash
cd /path/to/repo/root
pytest src/test/api/python/ \
  --ignore=src/test/api/python/e2e-test \
  -x -v \
  2>&1 | tail -30
```

**Expected outcome**: Same pass/fail breakdown as after Spec 002 (268 passing; failures confined to `libodbc.2.dylib` or Azure credential errors). No `ImportError` or `ModuleNotFoundError` in output.

---

## Step 6 — flake8 Passes on `app/` Package

```bash
cd src/api/python
flake8 app/
```

**Expected output**: No output (zero violations).

---

## Step 7 — Verify Test Patch Targets Are Updated (Spot Check)

Confirm that `CosmosClient` is no longer patched at the old router path.

```bash
grep -n "app.api.routers.history.CosmosClient" src/test/api/python/test_history.py
```

**Expected output**: No lines printed.

```bash
grep -n "app.data.cosmos_history.CosmosClient" src/test/api/python/test_history.py
```

**Expected output**: Multiple lines showing updated patch targets.

Similarly for fabric SQL:

```bash
grep -n "app.api.routers.history_sql.pyodbc" src/test/api/python/test_history_sql.py
grep -n "app.api.routers.history_sql.AzureCliCredential" src/test/api/python/test_history_sql.py
```

**Expected output**: No lines (patching at data module path now).

---

## Step 8 — Integration Smoke Test (Azure-Gated)

> **Requires**: Azure credentials, unixodbc system library, configured `.env` file with `AZURE_COSMOSDB_ACCOUNT`, `FABRIC_SQL_SERVER`, etc.

```bash
cd /path/to/repo/root
uvicorn app.main:app --reload
# Submit: POST /api/chat, GET /history/list, GET /historyfab/list, GET /health
```

**Expected outcome**: All four endpoints respond identically to their pre-Spec 003 behavior. No change in status codes or response shapes.
