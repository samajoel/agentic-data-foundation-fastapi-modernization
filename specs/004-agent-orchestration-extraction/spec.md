# Feature Specification: Agent Orchestration Layer Extraction

**Feature Branch**: `modernization-fastapi-speckit`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "Create Spec 004: Agent Orchestration Layer Extraction. Brownfield refactor extracting non-HTTP agent orchestration logic from app/api/routers/chat.py into app/agents/, preserving all POST /api/chat behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat Orchestration Extracted to Agent Layer (Priority: P1)

As a backend developer on this project, I need the non-HTTP orchestration logic currently
buried in `chat.py` to live in a clearly named agent module so that the router is focused
on HTTP concerns and the orchestration logic can be understood, tested, and modified
independently of FastAPI.

**Why this priority**: This is the core goal of Spec 004. All other work depends on this
extraction being correct, behavior-preserving, and importable without a running app server.

**Independent Test**: The extracted agent module can be imported in a test file without
starting FastAPI; its public functions can be called with mock dependencies and return the
same streaming or non-streaming response content that `chat.py` currently produces.

**Acceptance Scenarios**:

1. **Given** the chat router receives a POST /api/chat request, **When** it delegates
   orchestration to the agent layer, **Then** the response content, shape, and status code
   are identical to the pre-refactor behavior.

2. **Given** the agent module is imported directly in a Python test, **When** the import
   is executed, **Then** no FastAPI application startup, database connection, or network
   call is triggered.

3. **Given** a valid POST /api/chat request with an existing conversation ID,
   **When** the agent orchestration runs, **Then** Cosmos DB history is retrieved and
   updated through `app/data/cosmos_history.py` exactly as it was before the refactor.

4. **Given** a valid POST /api/chat request that invokes the SqlQueryTool,
   **When** the agent orchestration runs, **Then** Fabric SQL queries are issued through
   `app/data/fabric_sql.py` exactly as they were before the refactor.

---

### User Story 2 - Chat Router Reduced to HTTP Concerns (Priority: P2)

As a developer reading `chat.py`, I want the file to contain only FastAPI route
definitions, request validation, and response formatting so that I can understand the
HTTP contract without wading through orchestration logic.

**Why this priority**: Once the extraction is correct (US1), this shape concern confirms
the refactor achieved its structural goal. It can be verified independently of runtime
behavior.

**Independent Test**: The line count and logical structure of `chat.py` after the refactor
is demonstrably smaller and contains only FastAPI-idiomatic code (route decorators,
dependency injection, request/response handling); no orchestration flow control, no
direct agent calls to external services, no inline prompt construction.

**Acceptance Scenarios**:

1. **Given** the refactored `chat.py`, **When** reviewed, **Then** it contains FastAPI
   route handlers, Pydantic request/response types, and calls into `app/agents/` — but no
   inline agent loop, prompt assembly, or direct Azure service calls.

2. **Given** the refactored `app/agents/` directory, **When** reviewed, **Then** it
   contains at least one new module holding the extracted orchestration logic, and that
   module has no FastAPI imports at its top level.

---

### User Story 3 - Existing Chat Tests Pass Without New Failures (Priority: P3)

As a CI maintainer, I need all existing chat-related tests to continue passing after the
refactor so that no behavioral regression is introduced.

**Why this priority**: This is a quality gate, not a functional deliverable. It validates
US1 and US2 without adding new test infrastructure.

**Independent Test**: Running the existing pytest suite after the refactor produces the
same pass/fail/skip counts as the Spec 003 baseline (268 passed, 178 failed due to
environment-gated Azure/ODBC issues, 41 errors for the same root cause, 2 skipped).
No previously passing test becomes failing.

**Acceptance Scenarios**:

1. **Given** the pytest suite is run after the refactor, **When** results are compared
   to the Spec 003 baseline, **Then** the number of passing tests is equal to or greater
   than 268 with no new failures.

2. **Given** any test that previously patched a symbol from `app.api.routers.chat`,
   **When** that symbol has been moved to `app.agents.*`, **Then** the test patch target
   is updated to the new location so the test continues to work correctly.

---

### Edge Cases

- What happens when the agent orchestration raises an unhandled exception mid-stream?
  The router must propagate or convert it to the same HTTP error response currently
  returned by `chat.py`.

- What happens when Cosmos DB history is disabled (CHAT_HISTORY_ENABLED = False)?
  The agent module must respect this flag exactly as the current `chat.py` does.

- What happens when the SqlQueryTool is not needed for a given request?
  The agent module must skip Fabric SQL connection acquisition just as the current
  `chat.py` does, to avoid unnecessary connection overhead.

- What happens if an import of `app.agents.*` is attempted without a running server?
  The import must succeed with no side effects (no network calls, no DB connections,
  no required environment variables at import time).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extract non-HTTP agent orchestration logic from
  `app/api/routers/chat.py` into one or more modules under `app/agents/`.

- **FR-002**: The extracted agent modules MUST be importable without starting the
  FastAPI application (no module-level network calls, connections, or mandatory env vars).

- **FR-003**: `app/api/routers/chat.py` MUST remain the owner of all FastAPI route
  definitions for the `/api/chat` endpoint; none of the route definitions may move to
  `app/agents/`.

- **FR-004**: The POST /api/chat endpoint MUST produce identical external behavior after
  the refactor: same request shape, same response shape, same HTTP status codes, same
  streaming behavior, same error responses.

- **FR-005**: Agent orchestration MUST continue to use the Microsoft Agent Framework
  (`agent-framework-core`, `agent-framework-foundry`) already present in the project;
  no alternative orchestration library may be introduced.

- **FR-006**: All Fabric SQL access in the extracted orchestration code MUST go through
  `app/data/fabric_sql.py`; the agent modules MUST NOT open direct database connections.

- **FR-007**: All Cosmos DB history access in the extracted orchestration code MUST go
  through `app/data/cosmos_history.py`; the agent modules MUST NOT instantiate
  `CosmosClient` directly.

- **FR-008**: All Azure resource access within the extracted code MUST use Managed
  Identity or the existing `azure-identity` credential pattern; no hardcoded credentials,
  API keys, or connection strings may be introduced.

- **FR-009**: The `app/agents/__init__.py` MUST remain present (it may be empty or expose
  a minimal public interface); it MUST NOT eagerly import any symbol that triggers
  network, database, or heavy I/O at import time.

- **FR-010**: All existing pytest tests that previously passed MUST continue to pass after
  the refactor. Any test that patches a symbol must be updated to patch the symbol at its
  new module path if the symbol has moved.

- **FR-011**: `flake8` MUST report zero violations on `app/` after the refactor, using
  the existing `.flake8` configuration.

- **FR-012**: No frontend files, Bicep files, azure.yaml, or deployment scripts may be
  modified by this spec unless strictly required by Spec Kit metadata conventions.

### Key Entities

- **ChatOrchestrator / agent module**: The extracted logic responsible for constructing
  the agent run context, invoking the Agent Framework, managing conversation turns, and
  yielding streamed response tokens. Exists in `app/agents/`; has no FastAPI dependency
  at module level.

- **Chat Router** (`app/api/routers/chat.py`): The FastAPI router that owns `/api/chat`
  route definitions, validates incoming requests, calls into the agent module, and returns
  HTTP responses. After this spec, it is a thin HTTP adapter only.

- **Fabric SQL data layer** (`app/data/fabric_sql.py`): Existing module. The agent module
  MUST import from here, not reimplement connection logic.

- **Cosmos DB history layer** (`app/data/cosmos_history.py`): Existing module. The agent
  module MUST import from here, not reimplement client initialization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The POST /api/chat endpoint passes all pre-existing tests with no new
  failures relative to the Spec 003 baseline (268 passing tests maintained or exceeded).

- **SC-002**: `app/api/routers/chat.py` is measurably smaller after the refactor; it
  delegates orchestration work to `app/agents/` rather than implementing it inline.

- **SC-003**: The extracted agent modules can be imported in a standalone Python script
  or test file without any FastAPI application setup and without raising ImportError or
  triggering any network or database I/O.

- **SC-004**: `flake8 app/` reports zero violations after the refactor under the existing
  `.flake8` configuration.

- **SC-005**: No previously passing test becomes a failure. Any patch-target update
  required by the move is applied in the same PR as the move itself.

- **SC-006**: The implementation modifies no files outside of `src/api/python/app/`,
  `src/test/api/python/`, and Spec Kit spec artifacts, except for Spec Kit metadata files
  (`.specify/feature.json`, `CLAUDE.md`).

## Assumptions

- The Spec 003 baseline test state (268 passing, 178 environment-gated failures, 41
  environment-gated errors, 2 skipped) is the starting point for this spec's quality gate.

- `app/agents/` already exists as a package (created in Spec 002); the spec adds modules
  to it rather than creating the package from scratch.

- The Agent Framework / Foundry SDK is already installed and pinned in
  `src/api/python/requirements.txt`; no new dependencies are introduced.

- Streaming behavior from the agent layer to the HTTP layer is implemented by having the
  agent module yield response chunks (generator / async generator pattern) that the
  router forwards to the `StreamingResponse`; no new streaming transport mechanism is
  introduced.

- Test patch targets must be updated to reflect where symbols live after the move.
  The same rule that applied in Spec 003 (patch at the module that owns the symbol)
  applies here.

- Environment-gated test failures (pyodbc, Azure) are pre-existing and expected; they are
  not introduced by this spec and do not count as regressions.

- The refactor does not change any Azure resource configuration, deployment topology, or
  environment variable names consumed by the application.
