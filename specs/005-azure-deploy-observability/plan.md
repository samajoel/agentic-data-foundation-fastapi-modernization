# Implementation Plan: Azure Deployment and Observability Validation

**Branch**: `modernization-fastapi-speckit` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-azure-deploy-observability/spec.md`

## Summary

Verify and document that the Python FastAPI backend's deployment configuration, startup paths, health check endpoint, and observability pipeline remain correctly wired after the Specs 001–004 restructuring. No behavioral changes are introduced. The primary deliverables are formal verification of existing deployment artifacts plus an environment variable registry in `quickstart.md`. Any deployment artifact found to be incorrect during verification is fixed in-place as part of the same task.

## Technical Context

**Language/Version**: Python 3.11 (pinned via `linuxFxVersion: 'PYTHON|3.11'` in `deploy_backend_custom.bicep`)

**Primary Dependencies**:
- FastAPI 0.136.0, uvicorn 0.44.0 (from `requirements.txt`)
- azure-monitor-opentelemetry 1.8.7 (Application Insights telemetry)
- opentelemetry-instrumentation-fastapi 0.61b0 (FastAPI tracing, `excluded_urls="health"`)
- python-dotenv 1.2.2 (`.env` loading in `app/main.py`)

**Storage**: Cosmos DB (chat history, workshop mode only), Fabric SQL / Azure SQL (data access layer)

**Testing**: pytest 9.0.3 via `.venv/bin/pytest`; flake8 via `.venv/bin/flake8` (config: `.flake8`, `src/.flake8`)

**Target Platform**: Azure App Service (Linux, Python 3.11) via `deploy_backend_custom.bicep`; local Docker via `ApiApp.Dockerfile`

**Project Type**: Validation-only — deployment verification and documentation; no new web service code introduced

**Performance Goals**: `GET /health` under 500 ms; backend local startup under 15 s (SC-001, SC-002)

**Constraints**: No behavioral changes; no new env vars, startup scripts, or dependencies; must not break 268-test baseline

**Scale/Scope**: Single backend service; existing Azure App Service topology unchanged

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python FastAPI Is System of Record | ✅ PASS | Validates Python backend paths only |
| II. .NET Backend Is Retired | ✅ PASS | Verifies no .NET references remain in deployment artifacts |
| III. External API Contract Is Stable | ✅ PASS | No API behavior changes; all endpoints unchanged |
| IV. React Frontend Is Out of Scope | ✅ PASS | Frontend not touched |
| V. Preserve Existing Behavior | ✅ PASS | Pure verification; no behavioral changes introduced |
| VI. No Hardcoded Credentials | ✅ PASS | Managed Identity in bicep; OBO secrets via local `.env` only |
| VII. Agent Orchestration Via Microsoft Agent Framework | ✅ PASS | Not modified |
| VIII. Data Access Behind Dedicated Layer | ✅ PASS | Not modified |
| IX. Testing Via Existing pytest Configuration | ✅ PASS | Uses existing `pytest.ini` and `.venv/bin/pytest` |
| X. Layered Architecture | ✅ PASS | No new layers or files introduced |
| XI. Spec Kit Workflow Mandatory | ✅ PASS | This plan satisfies the workflow requirement |
| XII. Reference Only Verified Tool Versions | ✅ PASS | All versions from `requirements.txt` |

**No violations.** Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/005-azure-deploy-observability/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── quickstart.md        ← Phase 1 output (includes env var registry)
├── contracts/
│   └── health_check_interface.md   ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks command)
```

### Source Files Verified (read-only unless a fix is required)

```text
src/api/python/
├── app.py                              # Compatibility shim — verify imports
├── app/
│   ├── main.py                         # App factory + OTel config — verify wiring
│   ├── core/
│   │   ├── logging.py                  # configure_logging() — verify App Insights path
│   │   └── middleware.py               # attach_trace_attributes — verify enrichment
│   └── api/routers/                    # Not modified
├── ApiApp.Dockerfile                   # Container build — verify CMD
└── requirements.txt                    # Version reference (read-only)

infra/
├── deploy_backend_custom.bicep         # App Service startup — verify appCommandLine
└── deploy_backend_docker.bicep         # Docker variant — verify startup config

infra/scripts/
├── docker-build.sh                     # Build script — verify Python-only paths
└── docker-build.ps1                    # PowerShell variant — read-only check

src/start.sh                            # Local launcher — verify Python-only paths

src/test/api/python/
└── test_app.py                         # Health check tests — verify coverage
```

**Structure Decision**: Validation-only. No new source files created or modified unless a discrepancy is found. All spec artifacts land in `specs/005-azure-deploy-observability/`.

## Complexity Tracking

No Constitution violations. Table not required.

---

## Phase 0: Research Findings

All unknowns resolved by direct codebase inspection. See [research.md](research.md) for the full decision log.

**Pre-verified state of deployment artifacts**:

| Artifact | Current State | Status |
|----------|--------------|--------|
| `src/api/python/app.py` | `from app.main import app, build_app` | ✅ Shim intact |
| `ApiApp.Dockerfile` CMD | `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]` | ✅ Targets `app:app` |
| `deploy_backend_custom.bicep` appCommandLine | `uvicorn app:app --host 0.0.0.0 --port 8000` | ✅ Targets `app:app` |
| `deploy_backend_custom.bicep` linuxFxVersion | `PYTHON\|3.11` | ✅ Python runtime |
| `docker-build.sh` Dockerfile path | `src/api/python/ApiApp.Dockerfile` | ✅ Python-only |
| `start.sh` backend start | `python app.py --port=8000` | ✅ Python-only |
| .NET references in deployment files | `grep "dotnet\|api/dotnet"` result | ✅ Zero matches |
| `app/main.py` health route | `@fastapi_app.get("/health")` inline in `build_app()` | ✅ Present |
| OTel health exclusion | `FastAPIInstrumentor.instrument_app(app, excluded_urls="health")` | ✅ Present |
| `app/core/logging.py` App Insights wiring | Conditional on `APPLICATIONINSIGHTS_CONNECTION_STRING` | ✅ Graceful degradation |
| `app/core/middleware.py` trace enrichment | `attach_trace_attributes` registered in `build_app()` | ✅ Present |

**Key nuance — port 80 vs 8000**:
`ApiApp.Dockerfile` uses `--port 80` (standard Docker HTTP). `deploy_backend_custom.bicep` uses `--port 8000` (Azure App Service Oryx build path). Pre-existing intentional behavior, not a post-restructuring regression.

**Key nuance — APPINSIGHTS_INSTRUMENTATIONKEY vs APPLICATIONINSIGHTS_CONNECTION_STRING**:
`deploy_backend_custom.bicep` injects the legacy `APPINSIGHTS_INSTRUMENTATIONKEY`. `infra/main.bicep:278` injects `APPLICATIONINSIGHTS_CONNECTION_STRING` (modern SDK). `app/core/logging.py` reads the modern connection string; the legacy key is used automatically by the Azure Monitor SDK as a secondary fallback. Both are documented in the env var registry.

**Environment variables**: 35 env vars identified across 7 domains. Full registry in [quickstart.md](quickstart.md).

---

## Phase 1: Design & Contracts

### Validation Task Table

| ID | User Story | Verification Step | Pass Condition | Fix If Failing |
|----|-----------|-------------------|----------------|----------------|
| V-001 | US1 | `.venv/bin/python3 -c "import sys; sys.path.insert(0,'src/api/python'); import app; print('OK')"` | Prints `OK`, no errors | Fix import in `app.py` |
| V-002 | US1 | `grep "^CMD" src/api/python/ApiApp.Dockerfile` | `app:app` present | Fix CMD in Dockerfile |
| V-003 | US1 | `grep -rn "dotnet\|api/dotnet" infra/scripts/docker-build.sh infra/scripts/docker-build.ps1 src/start.sh azure.yaml` | Zero matches | Remove .NET references |
| V-004 | US1 | `grep "appCommandLine" infra/deploy_backend_custom.bicep` | `uvicorn app:app` | Fix appCommandLine |
| V-005 | US1 | `grep "linuxFxVersion" infra/deploy_backend_custom.bicep` | `PYTHON\|3.11` | Update runtime |
| V-006 | US1 | `grep "python app.py" src/start.sh` | Match on `python app.py` line | Fix start.sh path |
| V-007 | US2 | `curl -s http://127.0.0.1:8000/health` (backend running locally, no Azure creds) | HTTP 200, `{"status":"healthy"}` | Fix health endpoint |
| V-008 | US2 | `grep "excluded_urls" src/api/python/app/main.py` | `excluded_urls="health"` | Add exclusion |
| V-009 | US2 | `.venv/bin/pytest src/test/api/python/test_app.py -k health -v` | All health tests pass | Fix test or endpoint |
| V-010 | US3 | `grep -n "configure_azure_monitor\|APPLICATIONINSIGHTS" src/api/python/app/core/logging.py` | Conditional init + warning on absence | Fix configure_logging() |
| V-011 | US3 | Start backend with no `APPLICATIONINSIGHTS_CONNECTION_STRING`; inspect log output | Warning: "No Application Insights connection string found" | Fix configure_logging() |
| V-012 | US3 | `grep "attach_trace_attributes\|conversation_id_var\|user_id_var" src/api/python/app/core/middleware.py` | All three present | Fix middleware |
| V-013 | US3 | Env var registry produced in `quickstart.md` | 35+ vars documented and categorized | Write documentation |
| V-014 | Quality | `.venv/bin/pytest src/test/api/python/ -q --tb=short` | ≥ 268 passed; no new failures | Fix regressions |
| V-015 | Quality | `.venv/bin/flake8 src/api/python/app/` | Exit code 0 | Fix violations |

### Interface Contracts

`GET /health` is the only externally consumed interface validated by this spec. Contract: [contracts/health_check_interface.md](contracts/health_check_interface.md).

No `data-model.md` generated — this spec introduces no new data entities or schema changes.

---

## Post-Phase 1 Constitution Re-check

All 12 principles remain satisfied after Phase 1 design. No new dependencies, patterns, or files introduced. Verification confirmed:
- Deployment artifacts use Python 3.11 runtime only
- No hardcoded credentials (Managed Identity via `userassignedIdentityId` + `enableSystemAssignedIdentity: true`)
- Health endpoint is dependency-free and excluded from trace sampling
- All existing tests continue to pass at ≥ 268 baseline
