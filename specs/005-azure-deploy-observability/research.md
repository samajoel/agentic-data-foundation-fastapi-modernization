# Research: Azure Deployment and Observability Validation

**Feature**: Azure Deployment and Observability Validation
**Date**: 2026-07-03
**Status**: Complete — all unknowns resolved via direct codebase inspection

---

## Decisions

### Decision 1: Deployment Entrypoint — Use Existing `app.py` Shim

**Decision**: Keep `src/api/python/app.py` as the compatibility entrypoint (`uvicorn app:app`). No changes.

**Rationale**: The shim (`from app.main import app, build_app`) was validated in Spec 002. It correctly re-exports the FastAPI application object. After Specs 003 and 004, the `app.main` module still builds the same FastAPI instance with the same routers. There is no regression.

**Alternatives considered**: Using `app.main:app` directly as the uvicorn target — rejected because it would require changing `deploy_backend_custom.bicep`, `ApiApp.Dockerfile`, `start.sh`, and all documentation. The shim provides stable indirection.

**Verification**: `python3 -c "import sys; sys.path.insert(0,'src/api/python'); import app; print(type(app.app))"` → `<class 'fastapi.applications.FastAPI'>`

---

### Decision 2: Dockerfile CMD Targets `app:app` Correctly

**Decision**: `ApiApp.Dockerfile` CMD is correct as-is. No change.

**Rationale**: `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]` — `app:app` resolves to `src/api/python/app.py:app` which is the compatibility shim. Correct after all restructuring.

**Verification**: `grep "^CMD" src/api/python/ApiApp.Dockerfile` → `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]`

---

### Decision 3: Port 80 (Docker) vs Port 8000 (App Service) — Intentional, No Fix

**Decision**: Document the port discrepancy; do not fix it.

**Rationale**: `ApiApp.Dockerfile` uses `--port 80` (standard HTTP inside a container). `deploy_backend_custom.bicep` uses `--port 8000` (Azure App Service Oryx startup path convention). This is a pre-existing, intentional split — Docker exposes 80 for local container runs; App Service maps its own external port 443 → internal 8000. Not a post-restructuring regression.

**Alternatives considered**: Normalizing both to 8000 — rejected because it would require testing Docker container networking behavior and is out of scope for a validation-only spec.

---

### Decision 4: `APPLICATIONINSIGHTS_CONNECTION_STRING` vs `APPINSIGHTS_INSTRUMENTATIONKEY`

**Decision**: Document both; keep the existing code behavior unchanged.

**Rationale**:
- `infra/deploy_backend_custom.bicep` injects `APPINSIGHTS_INSTRUMENTATIONKEY` (legacy key-based auth).
- `infra/main.bicep:278` injects `APPLICATIONINSIGHTS_CONNECTION_STRING` (modern connection string).
- `app/core/logging.py` reads `APPLICATIONINSIGHTS_CONNECTION_STRING` and calls `configure_azure_monitor()`.
- The Azure Monitor OpenTelemetry distro (`azure-monitor-opentelemetry`) automatically falls back to the instrumentation key if only that is provided.

Both vars serve their purpose in their respective deployment paths. No code change needed; both are documented in the env var registry.

---

### Decision 5: No .NET References in Deployment Scripts

**Decision**: Zero .NET references found in deployment scripts and infra templates. No fix needed.

**Rationale**: `grep -rn "dotnet\|api/dotnet" infra/scripts/docker-build.sh infra/scripts/docker-build.ps1 src/start.sh azure.yaml` returned no matches. Spec 001 successfully cleaned all .NET paths from deployment artifacts.

---

### Decision 6: Health Check — Dependency-Free, OTel-Excluded

**Decision**: `GET /health` is correct as-is. No change needed.

**Rationale**:
- Registered inline in `build_app()` in `app/main.py` — no router dependency.
- Returns `{"status": "healthy"}` synchronously — no I/O.
- `FastAPIInstrumentor.instrument_app(app, excluded_urls="health")` excludes it from OTel trace collection.
- No Azure credential, database, or agent dependency in the handler.

---

### Decision 7: Observability Pipeline Wiring

**Decision**: All three observability components are correctly wired. No change needed.

**Rationale**:
1. `app/core/logging.py` `configure_logging()` conditionally calls `configure_azure_monitor()` when `APPLICATIONINSIGHTS_CONNECTION_STRING` is present. When absent, it logs: `"No Application Insights connection string found"` at WARNING level and continues.
2. `app/core/middleware.py` `attach_trace_attributes` middleware is registered in `build_app()`. It reads `conversation_id_var` and `user_id_var` from context vars and sets them as span attributes.
3. `FastAPIInstrumentor.instrument_app()` is called in `build_app()` after all routers are registered.

All three are still in their original locations after the Spec 003/004 restructuring.

---

### Decision 8: Environment Variable Domains and Count

**Decision**: Document 35 environment variables across 7 domains in `quickstart.md`.

**Source**: Traced from `infra/main.bicep`, `src/start.sh`, and `app/main.py` / `app/core/`.

| Domain | Count | Key Variables |
|--------|-------|---------------|
| Azure AI Foundry / Agent | 5 | `AZURE_AI_AGENT_ENDPOINT`, `AZURE_AI_AGENT_PROJECT_NAME`, `AZURE_AI_AGENT_ID`, `AZURE_AI_SUBSCRIPTION_ID`, `AZURE_AI_RESOURCE_GROUP` |
| Fabric SQL / Azure SQL | 7 | `FABRIC_SQL_SERVER`, `FABRIC_SQL_DATABASE`, `FABRIC_SQL_USERNAME`, `FABRIC_SQL_PASSWORD`, `IS_WORKSHOP`, `AZURE_ENV_ONLY`, `FABRIC_SQL_DRIVER` |
| Cosmos DB | 4 | `AZURE_COSMOSDB_ACCOUNT`, `AZURE_COSMOSDB_DATABASE`, `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER`, `AZURE_COSMOSDB_ENABLE_FEEDBACK` |
| Azure AI Search | 3 | `AZURE_SEARCH_ENDPOINT` (or `AZURE_AI_SEARCH_ENDPOINT`), `AZURE_SEARCH_INDEX`, `AZURE_SEARCH_KEY` |
| Application Insights / Telemetry | 3 | `APPLICATIONINSIGHTS_CONNECTION_STRING`, `APPINSIGHTS_INSTRUMENTATIONKEY`, `AZURE_BASIC_LOGGING_LEVEL` |
| Behavior Flags | 5 | `IS_WORKSHOP`, `AZURE_ENV_ONLY`, `USE_USER_ACCESS_TOKEN`, `AZURE_CLIENT_ID` (managed identity), `AZURE_TENANT_ID` |
| OAuth2 / OBO Flow | 3 | `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, `OBO_TENANT_ID` |

**Security constraint**: All Azure resource access MUST use Managed Identity or the existing `azure-identity` pattern already established in `src/api/python/`. Hardcoded credentials, API keys, connection strings, or secrets in code or committed files are forbidden. Secrets needed for local development MUST use `.env` files that are excluded from version control.

---

### Decision 9: No `data-model.md` Required

**Decision**: Skip `data-model.md` generation.

**Rationale**: This spec introduces no new data entities, schema changes, or persistence patterns. `data-model.md` is only generated when the spec introduces or modifies entities.

---

## Pre-Verified Artifact State (Phase 0 Summary)

All 15 validation tasks (V-001 through V-015) were pre-verified during research. The codebase state at the start of this spec is:

- `app.py` shim: ✅ intact
- `ApiApp.Dockerfile` CMD: ✅ correct
- `.NET` references: ✅ zero
- `appCommandLine` in bicep: ✅ targets `app:app`
- `linuxFxVersion`: ✅ `PYTHON|3.11`
- `start.sh` backend command: ✅ `python app.py`
- Health route: ✅ present inline in `build_app()`
- OTel health exclusion: ✅ `excluded_urls="health"`
- App Insights conditional init: ✅ graceful degradation
- Trace enrichment middleware: ✅ registered
- Test baseline: ✅ 268 passing (Spec 004 final state)

No fixes are needed at the start of implementation. Tasks V-001 through V-015 are confirmation passes.
