# Tasks: Data Access Layer Extraction

**Input**: Design documents from `specs/003-data-access-layer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested in spec. Existing tests are updated as part of the extraction tasks (patch target migration).

**Organization**: Tasks grouped by user story (US2→US3→US1→US4). US2 and US3 are independent and can be executed in parallel by separate developers. US1 and US4 are validation phases that run after US2 and US3.

---

## Phase 1: Setup

**Purpose**: Confirm baseline before any changes.

- [X] T001 Record baseline pytest pass count — run `pytest src/test/api/python/ --ignore=src/test/api/python/e2e-test -q 2>&1 | tail -5` from repo root and note the numbers
- [X] T002 Verify `src/api/python/app/data/__init__.py` exists and is empty (0 bytes, from Spec 002)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirm the Spec 002 package structure is in place before writing new data modules.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Verify `src/api/python/app/data/` directory exists — run `ls src/api/python/app/data/` and confirm only `__init__.py` is present
- [X] T004 Verify `app/core/auth/azure_credential_utils.py` exports `get_azure_credential_async` — run `grep -n "def get_azure_credential_async" src/api/python/app/core/auth/azure_credential_utils.py`

**Checkpoint**: Foundation confirmed — user story implementation can now begin.

---

## Phase 3: User Story 2 — Fabric SQL Data Access Isolated (Priority: P2)

**Goal**: Extract connection management and query execution from `history_sql.py` into `app/data/fabric_sql.py`. The router becomes a thin orchestration layer that calls into the data module.

**Independent Test**: `python -c "import app.data.fabric_sql as f; print(f.run_query_params, f.get_fabric_db_connection, f.SqlQueryTool)"` runs without error and without Azure credentials.

### Implementation for User Story 2

- [X] T005 [US2] Create `src/api/python/app/data/fabric_sql.py` with these extracted symbols from `history_sql.py`: `get_azure_sql_connection`, `get_fabric_db_connection`, `get_db_connection`, `run_nonquery_params`, `run_query_params`, `SqlQueryTool`. Copy the full implementations verbatim. Include all required imports: `import json, logging, os, struct, uuid` / `from datetime import datetime, date` / `from decimal import Decimal` / `from typing import Tuple, Any` / `import pyodbc` / `from azure.identity.aio import AzureCliCredential` / `from pydantic import BaseModel, ConfigDict` / `from app.core.auth.azure_credential_utils import get_azure_credential_async`. No module-level constants are needed.

- [X] T006 [US2] Update `src/api/python/app/api/routers/history_sql.py` — remove the definitions of `get_azure_sql_connection`, `get_fabric_db_connection`, `get_db_connection`, `run_nonquery_params`, `run_query_params`, and `SqlQueryTool`. Remove their now-exclusive imports: `import struct`, `import pyodbc`, `from azure.identity.aio import AzureCliCredential`, `from pydantic import BaseModel, ConfigDict`, `from decimal import Decimal`, `from typing import Tuple, Any`. Add at the top of the local imports block: `from app.data.fabric_sql import (get_azure_sql_connection, get_fabric_db_connection, get_db_connection, run_nonquery_params, run_query_params, SqlQueryTool)`. Keep all route handlers, business logic functions, and remaining imports (`json, logging, os, uuid, datetime, date, AIProjectClient, etc.`).

- [X] T007 [US2] Update `src/api/python/app/api/routers/chat.py` — find the import around line 373: `from app.api.routers.history_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection` and change it to `from app.data.fabric_sql import SqlQueryTool, get_azure_sql_connection, get_fabric_db_connection`. No other changes.

- [X] T008 [US2] Update `src/test/api/python/test_history_sql.py` — update the following patch target categories that break after the hard move: (A) Replace all `patch('app.api.routers.history_sql.AzureCliCredential'` with `patch('app.data.fabric_sql.AzureCliCredential'`; (B) Replace all `patch('app.api.routers.history_sql.pyodbc.connect'` with `patch('app.data.fabric_sql.pyodbc.connect'`; (C) Replace all `patch('app.api.routers.history_sql.pyodbc'` with `patch('app.data.fabric_sql.pyodbc'`; (D) Replace all `from app.api.routers.history_sql import get_fabric_db_connection` in isolation test methods with `from app.data.fabric_sql import get_fabric_db_connection`; (E) Replace all `from app.api.routers.history_sql import run_nonquery_params` isolation imports with `from app.data.fabric_sql import run_nonquery_params`; (F) Replace all `from app.api.routers.history_sql import run_query_params` isolation imports with `from app.data.fabric_sql import run_query_params`. Do NOT update patches like `patch('app.api.routers.history_sql.get_fabric_db_connection'` used in router-level tests (those remain valid because the router imports the name into its namespace).

- [X] T009 [US2] Verify US2 extraction — run `cd src/api/python && python -c "import sys, types; sys.modules['pyodbc'] = types.ModuleType('pyodbc'); setattr(sys.modules['pyodbc'], 'Connection', object); setattr(sys.modules['pyodbc'], 'Error', Exception); import app.data.fabric_sql as f; assert hasattr(f, 'run_query_params'); assert hasattr(f, 'SqlQueryTool'); print('fabric_sql OK')"` — should print `fabric_sql OK`

- [X] T010 [US2] Run flake8 on modified Fabric SQL files — `flake8 src/api/python/app/data/fabric_sql.py src/api/python/app/api/routers/history_sql.py src/api/python/app/api/routers/chat.py` from repo root — fix any violations before proceeding

**Checkpoint**: US2 complete — Fabric SQL data functions live in `app/data/fabric_sql.py`; routers delegate to it; chat.py imports from the data module.

---

## Phase 4: User Story 3 — Cosmos DB Data Access Isolated (Priority: P3)

**Goal**: Extract `CosmosConversationClient`, `init_cosmosdb_client`, and all Cosmos-specific configuration constants from `history.py` into `app/data/cosmos_history.py`.

**Independent Test**: `python -c "import app.data.cosmos_history as c; print(c.CosmosConversationClient, c.init_cosmosdb_client, c.CHAT_HISTORY_ENABLED)"` runs without error and without Azure credentials.

### Implementation for User Story 3

- [X] T011 [US3] Create `src/api/python/app/data/cosmos_history.py` with these extracted symbols from `history.py`: `USE_CHAT_HISTORY_ENABLED`, `AZURE_COSMOSDB_DATABASE`, `AZURE_COSMOSDB_ACCOUNT`, `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER`, `AZURE_COSMOSDB_ENABLE_FEEDBACK`, `CHAT_HISTORY_ENABLED`, `CosmosConversationClient`, `init_cosmosdb_client`. Copy all implementations verbatim. Include all required imports: `from datetime import datetime` / `import logging, os, uuid` / `from azure.cosmos.aio import CosmosClient` / `from azure.cosmos import exceptions` / `from app.core.auth.azure_credential_utils import get_azure_credential_async`. The six module-level constants use `os.getenv()` (safe at import time — no network calls). `CosmosClient` is only instantiated inside `CosmosConversationClient.__init__()` which is only called per-request.

- [X] T012 [US3] Update `src/api/python/app/api/routers/history.py` — remove the definitions of `CosmosConversationClient` (the entire class), `init_cosmosdb_client`, and the six module-level constants (`USE_CHAT_HISTORY_ENABLED`, `AZURE_COSMOSDB_DATABASE`, `AZURE_COSMOSDB_ACCOUNT`, `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER`, `AZURE_COSMOSDB_ENABLE_FEEDBACK`, `CHAT_HISTORY_ENABLED`). Remove their now-exclusive imports: `from azure.cosmos.aio import CosmosClient` and `from azure.cosmos import exceptions`. Add to the local imports block: `from app.data.cosmos_history import CosmosConversationClient, init_cosmosdb_client`. Keep all route handlers, service-helper functions, `generate_title`, `generate_fallback_title`, `track_event_if_configured`, and AI-related constants (`AZURE_AI_AGENT_ENDPOINT`, `AGENT_NAME_TITLE`).

- [X] T013 [US3] Update `src/test/api/python/test_history.py` — update the following categories: (A) Replace all `patch('app.api.routers.history.CosmosClient'` with `patch('app.data.cosmos_history.CosmosClient'`; (B) Replace all `from app.api.routers.history import init_cosmosdb_client` isolation imports with `from app.data.cosmos_history import init_cosmosdb_client`; (C) Replace all `from app.api.routers.history import USE_CHAT_HISTORY_ENABLED` isolation imports with `from app.data.cosmos_history import USE_CHAT_HISTORY_ENABLED`. Do NOT change `from app.api.routers.history import CosmosConversationClient` (still valid — the router imports it into its namespace) or `patch('app.api.routers.history.init_cosmosdb_client'` used in router-level tests.

- [X] T014 [US3] Verify US3 extraction — run `cd src/api/python && python -c "import app.data.cosmos_history as c; assert hasattr(c, 'CosmosConversationClient'); assert hasattr(c, 'init_cosmosdb_client'); assert hasattr(c, 'CHAT_HISTORY_ENABLED'); print('cosmos_history OK')"` — should print `cosmos_history OK`

- [X] T015 [US3] Run flake8 on modified Cosmos DB files — `flake8 src/api/python/app/data/cosmos_history.py src/api/python/app/api/routers/history.py` from repo root — fix any violations before proceeding

**Checkpoint**: US3 complete — Cosmos DB client and factory live in `app/data/cosmos_history.py`; history.py delegates to the data module.

---

## Phase 5: User Story 1 — API Contract Is Fully Preserved (Priority: P1)

**Goal**: Verify that all four API endpoints behave identically after extraction. This phase runs the quickstart validation checks that can be done without Azure credentials.

**Independent Test**: All quickstart Steps 1–4 and 7 pass; endpoints respond correctly under local testing (Step 8 is Azure-gated).

### Implementation for User Story 1

- [X] T016 [US1] Run quickstart Step 1 — `cd src/api/python && python -c "import app.data.fabric_sql; print('fabric_sql OK'); import app.data.cosmos_history; print('cosmos_history OK')"` (mock pyodbc first with `import sys, types; sys.modules['pyodbc'] = types.ModuleType('pyodbc'); ...`) — both print OK

- [X] T017 [US1] Run quickstart Step 2 — verify routers import after extraction and hard-move assertion passes: `cd src/api/python && python -c "<mock pyodbc>; from app.api.routers import history_sql, history, chat; assert history_sql.run_query_params.__module__ == 'app.data.fabric_sql'; print('routers import OK')"` — confirm no ImportError and assertion passes

- [X] T018 [US1] Run quickstart Step 3 — `grep -n 'from app.api.routers.history_sql import' src/api/python/app/api/routers/chat.py` — should return no output (import moved to app.data.fabric_sql)

- [X] T019 [US1] Run quickstart Step 7 spot-check — (A) `grep -n 'app.api.routers.history.CosmosClient' src/test/api/python/test_history.py` returns no output; (B) `grep -n 'app.api.routers.history_sql.AzureCliCredential' src/test/api/python/test_history_sql.py` returns no output; (C) `grep -n 'app.api.routers.history_sql.pyodbc' src/test/api/python/test_history_sql.py` returns no output

**Checkpoint**: US1 verified — extraction is structurally correct; external API contract preserved.

---

## Phase 6: User Story 4 — Tests Pass With No New Failures (Priority: P4)

**Goal**: Confirm the automated test suite shows no new failures compared to the Spec 002 baseline (268 passing; failures confined to pyodbc/Azure environment gates).

**Independent Test**: `pytest` output shows same pass count as Phase 1 baseline; `flake8` shows zero violations.

### Implementation for User Story 4

- [X] T020 [US4] Run full pytest suite — `pytest src/test/api/python/ --ignore=src/test/api/python/e2e-test -q 2>&1 | tail -10` from repo root — compare pass/fail count against T001 baseline; new failures indicate a broken patch target or import error to fix

- [X] T021 [US4] Run flake8 on full app package — `flake8 src/api/python/app/` from repo root — confirm zero violations

- [X] T022 [US4] If pytest shows new failures: diagnose root cause — most likely a patch target still pointing to old module path; re-read the failing test and apply the correct fix from the Test Patch Target Migration table in plan.md

**Checkpoint**: US4 verified — test suite stable; flake8 clean.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T023 [P] Verify `src/api/python/app/data/__init__.py` remains empty (0 bytes) — no accidental re-exports were added
- [X] T024 [P] Confirm no references to old data-symbol definitions remain in router files — `grep -n "class CosmosConversationClient\|def get_fabric_db_connection\|def run_query_params\|def run_nonquery_params" src/api/python/app/api/routers/history_sql.py src/api/python/app/api/routers/history.py` — should return no output
- [X] T025 Run complete quickstart validation sequence (Steps 1–7) as a final end-to-end check per `specs/003-data-access-layer/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — confirms Spec 002 foundation
- **US2 (Phase 3)** and **US3 (Phase 4)**: Both depend on Foundational — can run in parallel with each other
- **US1 (Phase 5)**: Depends on US2 AND US3 completion
- **US4 (Phase 6)**: Depends on US1 completion
- **Polish (Phase 7)**: Depends on US4 completion

### User Story Dependencies

- **US2 (P2)**: Can start after Foundational — independent of US3
- **US3 (P3)**: Can start after Foundational — independent of US2
- **US1 (P1)**: Requires US2 AND US3 complete (validates the combined result)
- **US4 (P4)**: Requires US1 complete (validates the full extraction)

### Within Each User Story

- Create data module file FIRST (T005 before T006; T011 before T012)
- Update router SECOND (removes the definitions the data module now owns)
- Update tests THIRD (patch targets must match where symbols are now defined)
- Verify and flake8 LAST (confirms correctness before moving on)

### Parallel Opportunities

- Phase 3 (US2) and Phase 4 (US3) can run in parallel on separate branches/developers
- T009 (US2 verify) and T014 (US3 verify) can run in parallel
- T023 and T024 in Phase 7 can run in parallel

---

## Parallel Example: US2 + US3 (if two developers)

```bash
# Developer A: Fabric SQL extraction
Task T005: Create src/api/python/app/data/fabric_sql.py
Task T006: Update src/api/python/app/api/routers/history_sql.py
Task T007: Update src/api/python/app/api/routers/chat.py
Task T008: Update src/test/api/python/test_history_sql.py
Task T009: Verify fabric_sql import
Task T010: flake8 on Fabric SQL files

# Developer B: Cosmos DB extraction (in parallel)
Task T011: Create src/api/python/app/data/cosmos_history.py
Task T012: Update src/api/python/app/api/routers/history.py
Task T013: Update src/test/api/python/test_history.py
Task T014: Verify cosmos_history import
Task T015: flake8 on Cosmos DB files

# Then merge and continue with US1 (T016-T019)
```

---

## Implementation Strategy

### MVP First (US2 Only — Fabric SQL Isolation)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: US2 (T005–T010)
4. **STOP and VALIDATE**: `flake8 src/api/python/app/data/fabric_sql.py` + verify T009 passes
5. Proceed to US3 (Phase 4)

### Full Delivery

1. Setup + Foundational → Foundation confirmed
2. US2 (Fabric SQL) → Verify independently → T009 and T010 pass
3. US3 (Cosmos DB) → Verify independently → T014 and T015 pass
4. US1 (Contract) → Verify T016–T019 all pass
5. US4 (Tests) → T020 shows no new failures; T021 shows zero flake8 violations
6. Polish (Phase 7) → T023–T025 confirm clean state

---

## Notes

- **Hard move, no re-exports**: `app/data/__init__.py` MUST remain empty after this spec. Never add re-export aliases there.
- **Lazy init invariant**: Do not add any `CosmosClient(...)` or `pyodbc.connect(...)` calls at module scope in the new data files. All connections are created inside async functions.
- **Patch target rule**: `AzureCliCredential` and `pyodbc` are NOT re-imported in `history_sql.py` after extraction — patches of `app.api.routers.history_sql.AzureCliCredential` will silently no-op. Update those to `app.data.fabric_sql.AzureCliCredential`.
- **`AZURE_COSMOSDB_ENABLE_FEEDBACK`** is used inside `CosmosConversationClient.create_message()` — it MUST move with the class to `cosmos_history.py` (already accounted for in T011).
- **T022 fallback**: If any new test failure appears in T020, the most likely cause is a patch target still pointing to the old path. Cross-reference the failing test against the Test Patch Target Migration table in `specs/003-data-access-layer/plan.md`.
