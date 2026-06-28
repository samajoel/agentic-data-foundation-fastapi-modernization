# Feature Specification: Data Access Layer Extraction

**Feature Branch**: `003-data-access-layer`

**Created**: 2026-06-28

**Status**: Draft

**Input**: Brownfield refactor — extract and organize existing Cosmos DB and Fabric SQL data-access logic from router modules into the `app/data/` layer established in Spec 002, preserving all existing external API behavior.

---

## Clarifications

### Session 2026-06-28

- Q: Should Fabric SQL connections and the Cosmos DB client be initialized at module import time (eager) or on first use (lazy)? → A: Lazy — connections created on first call; module imports cleanly without Azure credentials.
- Q: When symbols are moved to `app/data/`, should the original router files retain re-export aliases or should all callers be updated to the new paths with nothing left behind? → A: Hard move — symbols removed from router files entirely; all references updated to `app/data.*`; no re-exports left behind.

---

## User Scenarios & Testing *(mandatory)*

This spec is a brownfield refactor targeting the internal organization of the Python backend. The primary "users" are developers maintaining and extending the backend. The acceptance gate is that end users and API consumers experience zero change. User stories are ordered so that the external contract gate (US1) governs the whole spec, followed by isolation of each data store's access (US2 for Fabric SQL, US3 for Cosmos DB), and finally developer discoverability (US4).

### User Story 1 — API Contract Is Fully Preserved (Priority: P1)

As a frontend developer or API consumer, I want all API endpoints to continue responding exactly as they did before the data-access extraction so that I experience zero disruption and am not required to make any changes.

**Why this priority**: This is the non-negotiable acceptance gate. Any behavioral change to an endpoint — status code, response shape, streaming mode, authentication behavior — constitutes a regression regardless of the internal refactoring quality.

**Independent Test**: Start the refactored backend and submit representative requests to each of the four API surface areas; confirm each responds with the same status code, the same response shape, and the same behavior as before.

**Acceptance Scenarios**:

1. **Given** the refactored backend is running, **When** a valid `POST /api/chat` request is submitted, **Then** the response is a streaming reply with the same shape and status code as before.
2. **Given** the refactored backend is running, **When** any `/history/*` request is submitted (list, read, update, delete, generate-title), **Then** the response has the same status code, shape, and behavior as before.
3. **Given** the refactored backend is running, **When** any `/historyfab/*` request is submitted, **Then** the response has the same status code, shape, and behavior as before.
4. **Given** the refactored backend is running, **When** `GET /health` is called, **Then** the response is `{"status":"healthy"}` with HTTP 200.
5. **Given** a request that previously required authentication headers, **When** the same request is submitted, **Then** authentication behavior is identical — no new prompts, no new failures, no changed error messages.
6. **Given** the refactored backend is running, **When** a Cosmos DB or Fabric SQL operation is triggered, **Then** Managed Identity credentials are used and no hardcoded credentials appear.

---

### User Story 2 — Fabric SQL Data Access Is Isolated in the Data Layer (Priority: P2)

As a backend developer, I want all Fabric SQL connection management and query execution logic to be located in a designated data module so that I can find, test, and modify SQL data access without opening router files.

**Why this priority**: Fabric SQL access is directly mandated by constitution Principle VIII to not appear in route handlers. Isolating it is the primary deliverable of this spec alongside Cosmos DB isolation.

**Independent Test**: After refactoring, a developer can import and call Fabric SQL data functions from a standalone Python script or unit test without importing any FastAPI router module.

**Acceptance Scenarios**:

1. **Given** the refactored codebase, **When** a developer searches for Fabric SQL connection creation, query execution, or non-query execution logic, **Then** they find it exclusively in the designated Fabric SQL data module — not in any router file.
2. **Given** the Fabric SQL data module exists, **When** it is imported directly (outside of any FastAPI context), **Then** the import succeeds and the data functions are accessible.
3. **Given** the `/historyfab/*` routes are called at runtime, **When** Fabric SQL operations are performed, **Then** they execute via the data module, not inline within the router.
4. **Given** the Fabric SQL data module, **When** inspected, **Then** it uses the Managed Identity / azure-identity authentication pattern — not hardcoded credentials or connection strings.

---

### User Story 3 — Cosmos DB Data Access Is Isolated in the Data Layer (Priority: P3)

As a backend developer, I want the Cosmos DB client class and all Cosmos DB configuration to be located in a designated data module so that I can find, test, and modify conversation-history persistence without opening router files.

**Why this priority**: Cosmos DB access currently lives in the history router, making the file responsible for both HTTP concerns and persistence. Isolating it into `app/data/` completes the data layer for both persistence stores.

**Independent Test**: After refactoring, a developer can import and instantiate the Cosmos DB client class from a standalone Python script or unit test without importing any FastAPI router module.

**Acceptance Scenarios**:

1. **Given** the refactored codebase, **When** a developer searches for Cosmos DB client creation, Cosmos DB account configuration, or conversation-history persistence logic, **Then** they find it exclusively in the designated Cosmos DB data module.
2. **Given** the Cosmos DB data module exists, **When** it is imported directly (outside of any FastAPI context), **Then** the import succeeds and the client class is accessible.
3. **Given** the `/history/*` routes are called at runtime, **When** Cosmos DB operations are performed, **Then** they execute via the data module, not inline within the router.
4. **Given** the Cosmos DB data module, **When** inspected, **Then** it uses the Managed Identity / azure-identity credential pattern — not hardcoded credentials.

---

### User Story 4 — Backend Tests Pass With No New Failures (Priority: P4)

As a developer integrating or reviewing this change, I want the existing automated test suite to pass with no new failures beyond the known environment-gated Azure and ODBC issues so that I can merge with confidence.

**Why this priority**: The test suite is the automated evidence of contract stability. No new failures means no regressions.

**Independent Test**: Running the full pytest suite against the refactored codebase produces the same pass/failure breakdown as after Spec 002 (268 passing, with failures confined to environment-gated pyodbc/Azure connectivity issues).

**Acceptance Scenarios**:

1. **Given** the refactored codebase, **When** `pytest src/test/api/python/ --ignore=src/test/api/python/e2e-test` is run, **Then** all tests that passed after Spec 002 still pass.
2. **Given** the refactored codebase, **When** `flake8 src/api/python/app/` is run, **Then** zero violations are reported.
3. **Given** the refactored codebase, **When** tests that previously tested Cosmos DB or Fabric SQL operations are run, **Then** they pass or fail for the same reasons as before (Azure/ODBC environment gates), not due to import errors introduced by this refactoring.
4. **Given** test files that patch data-access functions, **When** the patch targets are updated to the new module paths, **Then** all affected tests continue to execute the same mock assertions.

---

### Edge Cases

- What happens when the Cosmos DB account environment variable is absent or empty? The same behavior as before must be preserved — the module loads without error but operations return appropriate not-configured responses.
- What happens when the Fabric SQL connection string components are missing? Same behavior as before — connection attempt fails with the same error/response path.
- What if a router module uses a Cosmos DB or Fabric SQL symbol via wildcard import or dynamic attribute access? All such usages must be identified and updated to the new data-module import path.
- What if a test patches a symbol at its old router-level path? The patch target must be updated to the new data-module path to remain effective.
- What if `app/data/` imports trigger a circular import with `app/api/routers/`? Data modules must import only from `app/core/` or standard library, never from router modules.
- What if a test imports a data module without Azure credentials present? Because initialization is lazy, the import MUST succeed; only the first actual connection call will fail, and that failure can be mocked.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a Fabric SQL data module at a stable, importable path within `app/data/` that encapsulates connection creation, parameterized query execution, and parameterized non-query execution.
- **FR-002**: The system MUST expose a Cosmos DB data module at a stable, importable path within `app/data/` that encapsulates the Cosmos DB client class and all Cosmos DB account configuration reading.
- **FR-003**: The `app/api/routers/history_sql.py` router MUST import its Fabric SQL data functions from `app/data/` rather than defining them inline. The moved symbols MUST NOT be re-exported from `history_sql.py`; the data module is the sole canonical location.
- **FR-004**: The `app/api/routers/history.py` router MUST import its Cosmos DB client class from `app/data/` rather than defining it inline. The moved symbols MUST NOT be re-exported from `history.py`; the data module is the sole canonical location.
- **FR-005**: Data modules in `app/data/` MUST use only the Managed Identity / azure-identity authentication pattern already established in the project. No hardcoded credentials, connection strings, API keys, or secrets may be introduced.
- **FR-006**: Data modules in `app/data/` MUST be importable independently of the FastAPI application (i.e., no FastAPI-specific imports at module level that would require an application context to load). All database connections and client objects MUST be initialized lazily — created on first call, not at module import time — so that importing a data module in a test environment without Azure credentials succeeds without error.
- **FR-007**: The existing pytest suite MUST pass with no new test failures beyond the known environment-gated Azure connectivity and ODBC system-library issues documented after Spec 002.
- **FR-008**: All test files that patch data-access functions by module path MUST have their patch targets updated to the new `app/data.*` paths. Because the migration is a hard move with no re-exports, patching the old router-module paths will silently fail after extraction; every affected patch target MUST be updated.
- **FR-009**: The external API contract (POST /api/chat, /history/*, /historyfab/*, GET /health) MUST remain behaviorally identical — same status codes, same response shapes, same streaming behavior, same authentication behavior.
- **FR-010**: `flake8` MUST report zero new violations on `src/api/python/app/` after the refactoring.
- **FR-011**: The `app/api/routers/chat.py` router MUST NOT be modified by this spec unless a Fabric SQL or Cosmos DB import is found to exist there.

### Key Entities

- **FabricSQLData module** (`app/data/fabric_sql.py`): Contains Fabric SQL connection creation (using azure-identity token authentication via pyodbc), parameterized query execution, and parameterized non-query execution. All logic currently in `history_sql.py` related to database connectivity and raw SQL execution moves here.
- **CosmosHistoryData module** (`app/data/cosmos_history.py`): Contains the `CosmosConversationClient` class and all Cosmos DB account, database, and container configuration reading. All persistence logic currently in `history.py` related to Cosmos DB moves here.
- **Fabric SQL router** (`app/api/routers/history_sql.py`): Retains HTTP route definitions and request/response orchestration; delegates data operations to `app/data/fabric_sql`.
- **Cosmos DB history router** (`app/api/routers/history.py`): Retains HTTP route definitions and request/response orchestration; delegates persistence to `app/data/cosmos_history`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `/history/*` and `/historyfab/*` endpoint returns the same response status code, body shape, and headers after refactoring as it did before.
- **SC-002**: `POST /api/chat` produces the same streaming behavior and response shape after refactoring as before.
- **SC-003**: The automated test suite produces no new failures beyond the 178 known environment-gated failures (pyodbc system library / Azure connectivity) documented in Spec 002's completion record.
- **SC-004**: `flake8 src/api/python/app/` reports zero violations after refactoring.
- **SC-005**: Both `app/data/fabric_sql` and `app/data/cosmos_history` are importable from a Python session without starting a FastAPI application or connecting to any Azure service.
- **SC-006**: A developer new to the codebase can locate Fabric SQL data access logic and Cosmos DB data access logic by navigating to `app/data/` with no need to search router files.

---

## Assumptions

- Spec 002 is complete: the `app/` package structure exists with `app/api/routers/`, `app/core/`, `app/data/` (empty placeholder), `app/services/`, `app/agents/`.
- The Fabric SQL data-access logic to be extracted is the set of functions in `app/api/routers/history_sql.py` that manage pyodbc connections and execute SQL — specifically connection creation, parameterized query, and parameterized non-query helpers. Higher-level route handlers remain in the router.
- The Cosmos DB data-access logic to be extracted is `CosmosConversationClient` and any Cosmos-specific configuration constants read from environment variables in `app/api/routers/history.py`.
- The `app/api/routers/chat.py` router contains no direct Fabric SQL or Cosmos DB access (it uses the Agent Framework); if this assumption is wrong, chat.py is also in scope.
- No new test files are written as part of this spec. Existing tests are updated to reflect the new import paths.
- The `.env`-based credential pattern for local development is unchanged; only the module location changes.
- Performance characteristics of data operations are unchanged — this is a location move, not a behavior change.
- Python import-time side effects (environment variable reads, logging configuration) in the extracted modules must behave identically in the new location.
