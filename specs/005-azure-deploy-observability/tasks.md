# Tasks: Azure Deployment and Observability Validation

**Input**: Design documents from `specs/005-azure-deploy-observability/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, contracts/ ✓, quickstart.md ✓

**Note**: This is a validation-only spec. Tasks are verification passes, not new feature implementation. Each task confirms an existing deployment artifact is correct after the Specs 001–004 restructuring. If a verification step finds a discrepancy, the fix is made within the same task.

**Organization**: Tasks are grouped by user story to enable independent verification and sign-off on each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (no file write dependencies, no shared process requirements)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm the starting baseline before any verification steps.

- [ ] T001 Run `.venv/bin/pytest src/test/api/python/ -q --tb=no` from repo root and record counts (expected: 268 passed, 178 failed, 41 errors, 2 skipped); if counts differ, note the deviation and investigate before proceeding

---

## Phase 3: User Story 1 — Deployment Compatibility Confirmed (Priority: P1) 🎯 MVP

**Goal**: Verify all six deployment artifacts correctly target the Python FastAPI backend with no .NET references after Specs 001–004.

**Independent Test**: `python3 -c "import sys; sys.path.insert(0,'src/api/python'); import app; print(type(app.app))"` from repo root prints `<class 'fastapi.applications.FastAPI'>` with no errors.

### Verification for User Story 1

- [ ] T002 [P] [US1] Verify `src/api/python/app.py` shim imports cleanly — run `python3 -c "import sys; sys.path.insert(0,'src/api/python'); import app; print(type(app.app))"` from repo root; expected output `<class 'fastapi.applications.FastAPI'>`; if import fails, fix the `from app.main import app, build_app` line in `src/api/python/app.py`

- [ ] T003 [P] [US1] Verify `ApiApp.Dockerfile` CMD targets `app:app` — run `grep "^CMD" src/api/python/ApiApp.Dockerfile`; expected: `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]`; if wrong target, update CMD in `src/api/python/ApiApp.Dockerfile`

- [ ] T004 [P] [US1] Verify zero .NET references in deployment scripts — run `grep -rn "dotnet\|api/dotnet" infra/scripts/docker-build.sh infra/scripts/docker-build.ps1 src/start.sh azure.yaml`; expected: no output (zero matches); if matches found, remove or replace with Python equivalents

- [ ] T005 [P] [US1] Verify `appCommandLine` in `infra/deploy_backend_custom.bicep` targets `app:app` — run `grep "appCommandLine" infra/deploy_backend_custom.bicep`; expected line contains `uvicorn app:app`; if wrong target, update `appCommandLine` in `infra/deploy_backend_custom.bicep`

- [ ] T006 [P] [US1] Verify Python 3.11 runtime in `infra/deploy_backend_custom.bicep` — run `grep "linuxFxVersion" infra/deploy_backend_custom.bicep`; expected: `'PYTHON|3.11'`; if wrong version, update `linuxFxVersion` in `infra/deploy_backend_custom.bicep`

- [ ] T007 [P] [US1] Verify `src/start.sh` starts the Python backend — run `grep "python app.py" src/start.sh`; expected: match on the backend start line containing `python app.py --port=8000`; if missing or wrong, fix the backend start command in `src/start.sh`

**Checkpoint**: All deployment artifact paths point to the Python FastAPI backend. No .NET references remain. US1 complete.

---

## Phase 4: User Story 2 — Health Check Is Reliable (Priority: P2)

**Goal**: Verify `GET /health` is dependency-free, excluded from OTel tracing, and covered by tests.

**Independent Test**: `curl -s http://127.0.0.1:8000/health` against a locally running backend with no Azure credentials returns HTTP 200 `{"status":"healthy"}` in under 500 ms.

### Verification for User Story 2

- [ ] T008 [P] [US2] Verify OTel health exclusion in `src/api/python/app/main.py` — run `grep "excluded_urls" src/api/python/app/main.py`; expected: `excluded_urls="health"`; if missing, add it to the `FastAPIInstrumentor.instrument_app()` call in `src/api/python/app/main.py`

- [ ] T009 [P] [US2] Run health check tests via pytest — run `.venv/bin/pytest src/test/api/python/test_app.py -k health -v` from repo root; expected: all health-related test cases pass; if any fail, fix the health endpoint in `src/api/python/app/main.py` or the test expectations in `src/test/api/python/test_app.py`

- [ ] T010 [US2] Start backend locally without Azure credentials and verify live health check — run `cd src/api/python && IS_WORKSHOP=true .venv/bin/uvicorn app:app --port 8000` in one terminal, then `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health` in another; expected HTTP 200; also run `curl -s http://127.0.0.1:8000/health` and confirm body is `{"status":"healthy"}`; if health route is missing or returns non-200, fix the inline health route in `build_app()` in `src/api/python/app/main.py`

**Checkpoint**: Health endpoint returns 200 without Azure credentials, is excluded from OTel tracing, and all health tests pass. US2 complete.

---

## Phase 5: User Story 3 — Observability Pipeline Documented and Wired (Priority: P3)

**Goal**: Verify Application Insights telemetry wiring, trace enrichment middleware, and confirm the env var registry is complete in `quickstart.md`.

**Independent Test**: Start backend locally with `APPLICATIONINSIGHTS_CONNECTION_STRING` unset; confirm `WARNING` log about missing connection string appears and the process continues to serve requests.

### Verification for User Story 3

- [ ] T011 [P] [US3] Verify conditional App Insights init in `src/api/python/app/core/logging.py` — run `grep -n "configure_azure_monitor\|APPLICATIONINSIGHTS_CONNECTION_STRING" src/api/python/app/core/logging.py`; expected: lines showing a conditional block that reads `APPLICATIONINSIGHTS_CONNECTION_STRING` and calls `configure_azure_monitor()`; if absent or unconditional, fix `configure_logging()` to gate on the env var in `src/api/python/app/core/logging.py`

- [ ] T012 [P] [US3] Verify trace enrichment middleware in `src/api/python/app/core/middleware.py` — run `grep "attach_trace_attributes\|conversation_id_var\|user_id_var" src/api/python/app/core/middleware.py`; expected: all three identifiers present; if any are missing, restore the trace attribute middleware in `src/api/python/app/core/middleware.py` and ensure it is registered in `build_app()` in `src/api/python/app/main.py`

- [ ] T013 [US3] Verify graceful degradation when App Insights connection string is absent — unset `APPLICATIONINSIGHTS_CONNECTION_STRING` and start the backend (`cd src/api/python && unset APPLICATIONINSIGHTS_CONNECTION_STRING && IS_WORKSHOP=true .venv/bin/uvicorn app:app --port 8000 2>&1 | head -30`); expected: WARNING log containing "Application Insights" or "connection string" and no startup failure; if backend crashes on missing connection string, fix `configure_logging()` in `src/api/python/app/core/logging.py` to degrade gracefully

- [ ] T014 [US3] Confirm env var registry in `specs/005-azure-deploy-observability/quickstart.md` is complete — read `specs/005-azure-deploy-observability/quickstart.md` and verify: (a) ≥35 variables documented, (b) all 7 domains present (Azure AI Foundry/Agent, Fabric SQL/Azure SQL, Cosmos DB, Azure AI Search, Application Insights/Telemetry, Behavior Flags, OAuth2/OBO Flow), (c) each variable has environment classification (local/azure/both) and required/optional/conditional status, (d) security constraints section present; if any domain is missing variables or classifications, update `specs/005-azure-deploy-observability/quickstart.md`

**Checkpoint**: Observability pipeline is wired correctly. Env var registry is complete. US3 complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gate confirmation across all user stories.

- [ ] T015 Run `.venv/bin/pytest src/test/api/python/ -q --tb=short` from repo root and confirm: (a) passing count ≥268, (b) no test that previously passed is now failing; if new failures appear, diagnose with `.venv/bin/pytest src/test/api/python/ -v --tb=long` and fix any regression introduced during verification fixes

- [ ] T016 [P] Run `.venv/bin/flake8 src/api/python/app/` from repo root and confirm exit code 0; if violations exist, fix them in the relevant file (likely `app/main.py`, `app/core/logging.py`, or `app/core/middleware.py` if any fixes were made during verification tasks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run immediately
- **Phase 3 (US1)**: Depends on Phase 1; all T002–T007 are parallel and can run simultaneously after T001
- **Phase 4 (US2)**: Independent of Phase 3 completion — T008 and T009 can run as soon as Phase 1 is done; T010 requires a running backend process (no code dependency on US1)
- **Phase 5 (US3)**: Independent of Phase 3 and Phase 4 completion — T011 and T012 can run immediately after Phase 1; T013 requires a running backend; T014 depends on quickstart.md being on disk (already created by `/speckit-plan`)
- **Phase 6 (Polish)**: Depends on all prior phases completing without open fixes

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 1 baseline
- **US2 (P2)**: Depends only on Phase 1 baseline (independent of US1)
- **US3 (P3)**: Depends only on Phase 1 baseline (independent of US1 and US2)

### Parallel Opportunities

```bash
# After T001 completes, all of these can run simultaneously:
T002: Verify app.py shim
T003: Verify Dockerfile CMD
T004: Verify no .NET references
T005: Verify appCommandLine in bicep
T006: Verify linuxFxVersion in bicep
T007: Verify start.sh command
T008: Verify OTel excluded_urls
T009: Run health pytest tests
T011: Verify configure_logging() conditional
T012: Verify middleware presence

# T010 and T013 require a running backend — do not run simultaneously with each other
# (same port 8000; start, verify, stop, repeat for the second)
```

---

## Parallel Example: User Story 1

```bash
# Step 1 — Sequential (must complete first):
Task T001: Record pytest baseline counts

# Step 2 — Fully parallel (all independent verification checks):
Task T002: python3 import check for app.py shim
Task T003: grep Dockerfile CMD
Task T004: grep .NET references in deployment scripts
Task T005: grep appCommandLine in bicep
Task T006: grep linuxFxVersion in bicep
Task T007: grep start.sh backend command
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Record baseline
2. Complete T002–T007 in parallel: US1 deployment checks
3. **STOP and VALIDATE**: Confirm all 6 deployment artifact checks pass
4. If all pass with no fixes needed → US1 complete, deployment is confirmed clean

### Incremental Delivery

1. Phase 1 (baseline) → all US1 checks in parallel → **Deployment compatibility confirmed (MVP)**
2. Phase 4 US2 checks (T008–T010) → **Health check reliability confirmed**
3. Phase 5 US3 checks (T011–T014) → **Observability wiring confirmed + env var registry complete**
4. Phase 6 quality gates (T015–T016) → **Full suite and lint confirmed clean**

---

## Notes

- **Validation-only**: All tasks are verification passes. The fix action in each task description is only executed if the verification step fails.
- **No new files**: Unless a fix is required by a failing verification step, no source files are created or modified.
- **Backend-running tasks**: T010 and T013 both require a locally running backend process on port 8000. Do not run them concurrently (port conflict). Start, verify, stop, then proceed to the next one.
- **T014 is documentation verification**: `quickstart.md` was produced by `/speckit-plan`; this task confirms it is complete and accurate. If variables are missing, update `specs/005-azure-deploy-observability/quickstart.md`, not source code.
- **Port nuance**: Do not "fix" the port discrepancy between `ApiApp.Dockerfile` (port 80) and `deploy_backend_custom.bicep` (port 8000) — this is intentional and documented in `research.md` Decision 3.
- **App Insights key nuance**: Do not remove or consolidate `APPINSIGHTS_INSTRUMENTATIONKEY` from bicep — it is used as a secondary fallback by the Azure Monitor SDK. Both env vars are intentional as documented in `research.md` Decision 4.
