# Feature Specification: Azure Deployment and Observability Validation

**Feature Branch**: `modernization-fastapi-speckit`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description — Validate and harden the Azure deployment and observability configuration for the Python FastAPI backend after Specs 001–004 restructuring, without changing application behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deployment Compatibility Confirmed (Priority: P1)

A DevOps engineer or developer wants to deploy or run the Python FastAPI backend using the existing startup paths — `python app.py`, `uvicorn app:app`, the `start.sh` local launcher, and the containerized deployment via `ApiApp.Dockerfile` — and receive a running, healthy backend identical in behavior to the pre-restructuring state.

**Why this priority**: If deployment paths break, no other modernization work can reach a running system. Verifying that existing startup paths still work after Specs 001–004 is the highest-impact gate.

**Independent Test**: Run the application locally using `python app.py` (or the equivalent uvicorn command); confirm the process starts without import errors, the `/health` endpoint responds 200, and no deployment file references the removed .NET backend path.

**Acceptance Scenarios**:

1. **Given** the Python backend directory with a valid `.env` file, **When** the application is started via `python app.py` or `uvicorn app:app`, **Then** the process starts without errors and the application is ready to receive requests.
2. **Given** the `ApiApp.Dockerfile`, **When** a Docker image is built and run, **Then** the container starts without errors and the application answers requests on the expected port.
3. **Given** the `docker-build.sh` deployment script, **When** the build is triggered, **Then** the script references only Python backend paths and produces no errors related to missing .NET files.
4. **Given** the `deploy_backend_custom.bicep` infrastructure file, **When** its startup command is read, **Then** it targets the Python FastAPI application with no reference to removed backends.
5. **Given** the `start.sh` local development launcher, **When** run with a valid environment, **Then** it starts the Python backend on port 8000 without errors.

---

### User Story 2 — Health Check Is Reliable (Priority: P2)

A platform operator or Azure App Service health probe wants to confirm that `GET /health` returns a healthy status response quickly, without requiring Azure credentials or any external dependencies, so that the platform can reliably determine whether the backend process is alive.

**Why this priority**: A failing or slow health check causes Azure App Service to restart the container, causing service disruption. Verifying that the health check endpoint is dependency-free and fast is essential for stable deployments.

**Independent Test**: Issue `GET /health` against a locally running backend with all Azure credentials absent from the environment; confirm HTTP 200 with a healthy body returns in well under 500 ms.

**Acceptance Scenarios**:

1. **Given** a running backend with no Azure credentials configured, **When** `GET /health` is called, **Then** it returns HTTP 200 with a body indicating a healthy state.
2. **Given** a running backend, **When** `GET /health` is called repeatedly under normal load, **Then** response time is consistently below 500 ms.
3. **Given** a backend started without `APPLICATIONINSIGHTS_CONNECTION_STRING`, **When** `GET /health` is called, **Then** it still returns 200 (health check does not depend on telemetry availability).
4. **Given** the OpenTelemetry instrumentation configuration, **When** it is read, **Then** the `/health` path is excluded from distributed trace sampling (to avoid noise in trace data).

---

### User Story 3 — Observability Pipeline Documented and Wired (Priority: P3)

An operations engineer wants to verify that Application Insights telemetry, structured logging, and trace context enrichment are still correctly wired after the app/ package restructuring, and that all required environment variables for Azure and integration services are documented so that a new deployment can be configured without consulting source code.

**Why this priority**: Observability gaps discovered after deployment are expensive to fix. Documenting and verifying the telemetry wiring now — while the restructuring is fresh — prevents silent monitoring outages in production.

**Independent Test**: Start the application locally with `APPLICATIONINSIGHTS_CONNECTION_STRING` unset; confirm the backend logs a warning about missing telemetry but continues to start. Start again with a placeholder value; confirm Application Insights initialization is attempted. Confirm all environment variable names and their categories are captured in the spec artifacts.

**Acceptance Scenarios**:

1. **Given** `APPLICATIONINSIGHTS_CONNECTION_STRING` is absent from the environment, **When** the backend starts, **Then** a warning is logged and the application continues to run (graceful degradation, not a startup failure).
2. **Given** `APPLICATIONINSIGHTS_CONNECTION_STRING` is present, **When** the backend starts, **Then** Application Insights telemetry is initialized and an informational log confirms the configuration.
3. **Given** a structured logging configuration using `AZURE_BASIC_LOGGING_LEVEL`, **When** the backend runs, **Then** log records include trace context fields (`conversation_id`, `user_id`) on relevant requests.
4. **Given** the full set of environment variables required for Fabric SQL, Cosmos DB, and Agent/Foundry integrations, **When** documented in the spec artifacts, **Then** any new deployment environment can be configured without reading application source code.

---

### Edge Cases

- What happens when the application starts with an empty or malformed `APPLICATIONINSIGHTS_CONNECTION_STRING`? The telemetry SDK should fail gracefully and log an error without crashing the process.
- What happens when `GET /health` is called before all application routes have been fully registered? The health route is registered inline during `build_app()` and should be available immediately.
- What happens when a required integration env var (e.g., `AZURE_AI_AGENT_ENDPOINT`) is missing at startup? The application should start without error; the missing configuration will cause a runtime failure only when the affected feature is invoked.
- What happens when both `AZURE_SEARCH_ENDPOINT` and `AZURE_AI_SEARCH_ENDPOINT` are absent? The `fetch-azure-search-content` endpoint returns a 500 with a configuration error — not a startup failure.
- What happens if `docker-build.sh` is run targeting the Python Dockerfile but the Dockerfile references a path that no longer exists? The Docker build fails with a clear file-not-found error, making the misconfiguration visible immediately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deployment configuration MUST support starting the backend using the existing `app.py` compatibility entrypoint with no code changes required after the Spec 001–004 restructuring.
- **FR-002**: The `ApiApp.Dockerfile` MUST produce a runnable container that starts the Python FastAPI backend via `uvicorn app:app`.
- **FR-003**: All deployment scripts and infra templates referenced in this spec MUST reference only Python backend paths; no references to the retired .NET backend path are permitted.
- **FR-004**: The Azure App Service startup command in `deploy_backend_custom.bicep` MUST target the Python FastAPI application.
- **FR-005**: The `GET /health` endpoint MUST return HTTP 200 with a body indicating healthy status when the application process is running.
- **FR-006**: The `GET /health` endpoint MUST be dependency-free — it MUST NOT require Azure credentials, database connections, or external service availability to return 200.
- **FR-007**: The `GET /health` endpoint MUST respond in under 500 ms under normal operating conditions.
- **FR-008**: OpenTelemetry instrumentation MUST exclude `/health` from distributed trace collection to prevent health probe noise in trace data.
- **FR-009**: Application Insights telemetry initialization MUST occur in `app/main.py` via `configure_logging()`, which MUST remain the single entry point for logging and telemetry configuration.
- **FR-010**: When `APPLICATIONINSIGHTS_CONNECTION_STRING` is absent or empty, the application MUST start successfully and log a warning without failing.
- **FR-011**: Structured log records on relevant API requests MUST include `conversation_id` and `user_id` fields as contextual trace attributes when those values are present in the request.
- **FR-012**: All environment variables consumed by the Python backend MUST be documented with their purpose, whether they are required or optional, and whether they are local-only, Azure-environment-gated, or required in both environments.

### Key Entities

- **Deployment Entrypoint**: The `app.py` compatibility shim that imports `app.main.app` and `app.main.build_app`; used by `uvicorn app:app` and `python app.py`.
- **Application Factory**: `build_app()` in `app/main.py`; registers all routers, middleware, CORS, and the `/health` route; used by the deployed `app` instance.
- **Health Check Endpoint**: `GET /health`, inline in `build_app()`; returns `{"status": "healthy"}`; excluded from OTel trace sampling.
- **Telemetry Pipeline**: `configure_logging()` in `app/core/logging.py`; conditionally initializes Application Insights when `APPLICATIONINSIGHTS_CONNECTION_STRING` is present.
- **Trace Enrichment Middleware**: `attach_trace_attributes` in `app/core/middleware.py`; enriches spans and log records with `user_id` and `conversation_id` from request context.
- **Environment Variable Registry**: The set of env vars consumed by the backend, classified by integration domain (Azure AI, Cosmos DB, Fabric SQL, observability, app behavior flags).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The backend starts locally with a valid `.env` file and no live Azure resources, with zero import errors or startup failures, in under 15 seconds.
- **SC-002**: `GET /health` returns HTTP 200 with a healthy status in under 500 ms when called with no Azure credentials present.
- **SC-003**: The existing test baseline is maintained: at minimum 268 tests pass, with no previously passing test newly failing (178 failures and 41 errors remain environment-gated, 2 skipped).
- **SC-004**: `flake8` reports zero violations on `src/api/python/app/` after any deployment configuration file changes within that path.
- **SC-005**: Zero references to the retired .NET backend path (`src/api/dotnet`) remain in the deployment scripts, Dockerfile, and infra templates targeted by this spec.
- **SC-006**: All environment variables consumed by the Python backend are documented in the spec artifacts, categorized by: required for all environments, required for Azure-only, optional with defaults.
- **SC-007**: Application Insights telemetry degradation is verified: backend starts and serves requests when `APPLICATIONINSIGHTS_CONNECTION_STRING` is absent, logging a single warning at startup.

## Assumptions

- The `app.py` compatibility entrypoint was already validated to work with the `app/` package structure in Spec 002; this spec re-confirms it is still compatible after Specs 003 and 004.
- The Docker build (`ApiApp.Dockerfile`) has not been modified since Spec 001 and still correctly references `app:app`; this spec verifies that assumption.
- Verification of Azure-environment-gated behaviors (Application Insights telemetry actually reaching Azure, Cosmos DB history endpoints, Fabric SQL queries) requires a live Azure environment and is explicitly out of scope for local validation in this spec. Those behaviors are verified via environment-gated tests already in the test suite.
- The `start.sh` script handles local environment setup (`.env` discovery, agent names, Fabric SQL config, Azure login, role assignments) and is not modified by this spec; the spec only verifies it references the correct backend path.
- The `APPLICATIONINSIGHTS_CONNECTION_STRING` env var controls whether telemetry is sent to Azure Monitor; its absence causes graceful degradation, not a startup failure.
- Environment variables with `FABRIC_SQL_*` prefix are only required when `IS_WORKSHOP=false` or `AZURE_ENV_ONLY=false`; the `start.sh` script handles this conditional loading.
- The `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, and `OBO_TENANT_ID` variables support an OAuth2 On-Behalf-Of flow for specific team integrations (`USE_USER_ACCESS_TOKEN=true`) and are not required in the standard deployment.
- No new environment variables, configuration files, or startup scripts are introduced by this spec; it validates and documents existing ones only.

## Clarifications

### Session 2026-07-03

- Q: Should this spec cover validation of the Azure DevOps / GitHub Actions CI pipeline in addition to local deployment scripts? → A: No — CI pipeline changes are out of scope; this spec covers only local deployment scripts (`start.sh`, `docker-build.sh`), `ApiApp.Dockerfile`, and infra templates (`deploy_backend_custom.bicep`, `deploy_appservice-appsettings.bicep`).
- Q: Should environment variable documentation be delivered as a standalone reference file or as part of the quickstart? → A: Environment variable documentation is delivered as part of the `quickstart.md` artifact produced during planning; no separate standalone env-var reference file is created.
