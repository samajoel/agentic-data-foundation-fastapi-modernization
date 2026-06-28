# Feature Specification: FastAPI Service Restructuring

**Feature Branch**: `002-fastapi-restructure`

**Created**: 2026-06-28

**Status**: Draft

**Input**: Brownfield refactor — restructure `src/api/python/` into a layered package structure while preserving all existing external behavior.

---

## Clarifications

### Session 2026-06-28

- Q: For modules that currently mix routing with business logic and agent calls (e.g., `chat.py`), does this spec require separating concerns into distinct layer files, or moving the entire module as-is to the routing layer? → A: Move whole file — `chat.py`, `history.py`, and `history_sql.py` move as complete units to `app/api/routers/`. Intra-module concern extraction (service, agent layers) is deferred to a subsequent spec.
- Q: Should `app/services/`, `app/agents/`, and `app/data/` layer directories be created as structural placeholders in this spec, or deferred until a spec that populates them? → A: Create all three placeholder directories now with empty `__init__.py` files, establishing the full five-layer architecture skeleton (api, services, agents, data, core) immediately.
- Q: When router modules move to `app/api/routers/`, should broken imports be fixed by updating every import reference, or by keeping shim files at the original flat paths? → A: Update all imports — every file (production source and tests) that imported from the old flat paths is updated to the new `app.api.routers.*` paths. No shim files are left at the original router module locations (only `app.py` entrypoint shim is retained, per FR-003).

---

## User Scenarios & Testing *(mandatory)*

This spec is a brownfield refactor targeting the developer experience and internal code organization of the Python backend. The primary "users" are developers maintaining and extending the backend, and the acceptance gate is that end users of the application experience zero change. User stories are ordered so that the external acceptance gate (US1) governs the whole spec, followed by the direct value delivered by the restructuring (US2), with operational continuity (US3) as the supporting story.

### User Story 1 — API Contract Is Fully Preserved (Priority: P1)

As a frontend developer or API consumer, I want all API endpoints to continue responding exactly as they did before the restructuring so that I experience zero disruption and am not required to make any changes on my side.

**Why this priority**: This is the non-negotiable acceptance gate. If any endpoint changes behavior, shape, status code, streaming mode, or authentication behavior, the restructuring has introduced a regression and is not done.

**Independent Test**: Start the restructured backend and submit representative requests to each of the four API surface areas; confirm each responds with the same status code, the same response shape, and the same streaming behavior as before restructuring.

**Acceptance Scenarios**:

1. **Given** the restructured backend is running, **When** a valid `POST /api/chat` request is submitted, **Then** the response is a streaming reply with the same shape and status code as before restructuring, with no errors.
2. **Given** the restructured backend is running, **When** any `/history/*` request is submitted, **Then** the response has the same status code, shape, and behavior as before restructuring.
3. **Given** the restructured backend is running, **When** any `/historyfab/*` request is submitted, **Then** the response has the same status code, shape, and behavior as before restructuring.
4. **Given** the restructured backend is running, **When** `GET /health` is called, **Then** the response is `{"status":"healthy"}` with HTTP 200.
5. **Given** a request that previously required authentication headers, **When** the same request is submitted to the restructured backend, **Then** authentication behavior is identical — no new prompts, no new failures, no changed error messages.
6. **Given** the restructured backend is running, **When** cross-origin requests are submitted matching the previous CORS policy, **Then** they succeed as before.

---

### User Story 2 — Backend Is Organized Into Predictable Layers (Priority: P2)

As a developer contributing to or maintaining the Python backend, I want each functional concern (routing, configuration, shared utilities, application initialization) to live in a clearly designated location so that I can locate and modify any behavior without tracing import chains across a flat module list.

**Why this priority**: The direct value of this restructuring. A predictable layer structure reduces the time to locate code, reduces the risk of accidental coupling, and provides the foundation for future modernization specs that add new capabilities per the layered architecture principle.

**Independent Test**: After restructuring, a developer new to the codebase can locate any named functional concern (e.g., "the chat route handler", "the CORS middleware setup", "the Cosmos DB connection") by navigating at most two package levels without consulting external documentation.

**Acceptance Scenarios**:

1. **Given** the restructured codebase, **When** a developer looks for route-handling code, **Then** it is located under a designated routing layer with no business logic mixed in.
2. **Given** the restructured codebase, **When** a developer looks for configuration, middleware, or shared utility code, **Then** it is located under a designated core layer.
3. **Given** the restructured codebase, **When** a developer looks for the application initialization and startup entry point, **Then** it is located in a clearly named, top-level module.
4. **Given** the restructured codebase, **When** a developer looks for data access code (Fabric SQL, Cosmos DB), **Then** it is located in or clearly associated with a designated data-access layer (even if data access logic itself is not changed in this spec).
5. **Given** the restructured codebase, **When** a developer looks for agent orchestration code, **Then** it is located in or clearly associated with a designated agent layer.

---

### User Story 3 — Startup and Deployment Path Is Unchanged (Priority: P3)

As a deployment engineer or developer running the application locally, I want the existing startup command documented in the deployment and development guides to start the backend without any modification to scripts, configuration files, or container definitions so that operational knowledge and documentation remain valid.

**Why this priority**: Operational continuity. The restructuring must not require changes to `src/start.sh`, `src/start.cmd`, `azure.yaml`, Dockerfile targets, or any documented startup instructions.

**Independent Test**: Execute the existing documented startup command (`python app.py --port=8000` from `src/api/python/`) against the restructured codebase; confirm the server starts, binds to port 8000, and the health endpoint responds.

**Acceptance Scenarios**:

1. **Given** the restructured codebase, **When** the existing documented startup command is executed from `src/api/python/`, **Then** the backend starts successfully on port 8000 with no errors.
2. **Given** the existing `src/start.sh` and `src/start.cmd` scripts, **When** they are run without modification, **Then** the backend starts and the frontend can reach all API endpoints.
3. **Given** the existing `azure.yaml` and container deployment configuration, **When** no changes are made to those files, **Then** the deployment still works correctly.

---

### Edge Cases

- What happens if a module import path changes and an existing test hard-codes the old path? All import references to the moved router modules (`chat`, `history`, `history_sql`) MUST be updated to the new `app.api.routers.*` paths in both production source and test files. No shim files are left at the original flat paths (the only retained shim is `app.py`, the startup entrypoint).
- What if a circular import arises when modules are reorganized into sub-packages? The restructuring MUST resolve any circular imports without changing the behavioral semantics of the affected modules.
- What if the `pythonpath` setting in `pytest.ini` (`./src/api/python`) no longer resolves imports correctly after restructuring? The `pytest.ini` path setting MAY be adjusted to maintain test discoverability, but no other test configuration changes are permitted.
- What if the existing entrypoint file (`app.py`) is referenced by absolute path in a Dockerfile or container startup command? A compatibility shim at the original `app.py` path MUST remain to preserve those references.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The restructured backend MUST serve all four API surface areas — `POST /api/chat`, `/history/*`, `/historyfab/*`, and `GET /health` — with request shapes, response shapes, HTTP status codes, streaming behavior, and authentication behavior identical to the pre-restructuring state.
- **FR-002**: The Python backend source MUST be reorganized into a five-layer package hierarchy: `app/api/routers/` (routing), `app/services/` (service logic placeholder), `app/agents/` (agent interaction placeholder), `app/data/` (data access placeholder), and `app/core/` (configuration, middleware, shared utilities). Existing mixed-concern modules (`chat.py`, `history.py`, `history_sql.py`) move as complete units to the routing layer; the `services/`, `agents/`, and `data/` directories are established as structural placeholders with empty `__init__.py` files. Intra-module concern separation is explicitly out of scope for this spec and deferred to a subsequent spec.
- **FR-003**: A compatibility entrypoint MUST be maintained at the existing `app.py` path so that all existing startup commands, deployment scripts, and container definitions continue to work without modification.
- **FR-004**: All existing automated tests MUST pass after restructuring. Test logic MUST NOT change. Import paths in test files MUST be updated to the new `app.api.routers.*` module paths wherever the moved router modules are referenced. No other test changes are permitted.
- **FR-005**: The `pytest.ini` configuration MUST remain compatible with the restructured module layout. The `pythonpath` setting MAY be adjusted to a single additional path if necessary, but no new test markers, plugins, or configuration sections may be added.
- **FR-006**: The existing `.flake8` and `src/.flake8` linting configuration MUST produce no new violations against the restructured codebase.
- **FR-007**: No changes MUST be made to Azure infrastructure configuration (`azure.yaml`, `infra/`), Fabric SQL logic, Cosmos DB logic, agent orchestration behavior, or the React frontend as part of this restructuring.
- **FR-008**: The restructured codebase MUST maintain the existing Managed Identity / `azure-identity` authentication pattern with no hardcoded credentials introduced.

### Key Entities

- **Application Package** (`app/`): The top-level package containing all backend source modules organized by layer.
- **Routing Layer** (`app/api/routers/`): Contains FastAPI routers. In this spec, existing router modules (`chat.py`, `history.py`, `history_sql.py`) move here as complete units — business logic, agent calls, and utilities included — because intra-module concern separation is deferred. A subsequent spec will extract service and agent logic from these modules.
- **Core Layer** (`app/core/`): Contains application configuration, shared middleware, CORS setup, logging, OpenTelemetry setup, and reusable utilities. The `auth/` package moves here.
- **Application Initializer** (`app/main.py`): Creates the FastAPI application instance, registers routers, and applies middleware. This is the canonical startup module.
- **Placeholder Layers** (`app/services/`, `app/agents/`, `app/data/`): Empty packages (with `__init__.py`) establishing the full five-layer skeleton per the architecture principle. Content deferred to subsequent specs.
- **Compatibility Entrypoint** (`app.py` at `src/api/python/`): A thin wrapper that imports the application from the package and exposes it to the existing startup command.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The automated test suite passes with zero new failures after restructuring. The number of passing tests is equal to or greater than the pre-restructuring baseline.
- **SC-002**: All four API surface areas (`POST /api/chat`, `/history/*`, `/historyfab/*`, `GET /health`) return responses with identical status codes and shapes to pre-restructuring behavior, verified by running the quickstart validation from Spec 001.
- **SC-003**: The backend starts successfully via the existing startup command (`python app.py --port=8000` from `src/api/python/`) with no changes to any start script, Dockerfile, or `azure.yaml`.
- **SC-004**: The React frontend requires zero changes and continues to operate without modification.
- **SC-005**: Linting passes with zero new violations, confirming the restructured code meets existing style standards.
- **SC-006**: Any developer reading the restructured repository can identify the correct layer for any named concern (routing, configuration, initialization, data access, agent interaction) without consulting documentation beyond the directory structure itself.

---

## Assumptions

1. The current backend entrypoint is `src/api/python/app.py`, which the existing `start.sh`, `start.cmd`, and documented local development instructions reference. This file path MUST be preserved as a compatibility shim.
2. The existing test suite under `src/test/` imports from `src/api/python/` module paths. All import references to the moved router modules are updated to their new `app.api.routers.*` paths. Import references to `app/core/` modules (such as `auth/`) are similarly updated. This is the only permitted change to test files.
3. This spec does not introduce new service, agent, or data-access logic, and does not separate mixed concerns within existing modules. Existing modules (`chat.py`, `history.py`, `history_sql.py`) move as complete units to the routing layer. Intra-module concern extraction is explicitly deferred to a subsequent spec.
4. The `services/`, `agents/`, and `data/` layers are established as empty structural placeholders in this spec. The data-access layer (Fabric SQL, Cosmos DB connection management), service layer (business logic extraction), and agent layer (agent framework interaction) will be fully realized by subsequent specs per the layered architecture principle.
5. The `pytest.ini` `pythonpath = ./src/api/python` setting is the authoritative test path root. Adjustments to this setting are permissible only if required to maintain test discoverability after restructuring.
6. Azure deployment infrastructure (`azure.yaml`, Bicep templates, container image build) points to the `app.py` entrypoint. No changes to infrastructure files are in scope.
7. Streaming responses from `POST /api/chat` are implemented at the FastAPI route handler level; moving the handler to a router module preserves this behavior without modification.

---

## Clarifications

*(No clarification session conducted for this spec — user description was unambiguous and complete.)*
