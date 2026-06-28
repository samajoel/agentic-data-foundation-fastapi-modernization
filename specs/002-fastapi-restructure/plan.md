# Implementation Plan: FastAPI Service Restructuring

**Branch**: `modernization-fastapi-speckit` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-fastapi-restructure/spec.md`

---

## Summary

Reorganize the Python FastAPI backend flat module structure (`src/api/python/`) into a
five-layer package hierarchy under `app/` while preserving all external behavior, test
baselines, and startup paths. Router modules (`chat.py`, `history.py`, `history_sql.py`)
move as complete units to `app/api/routers/`. The `auth/` package moves to `app/core/auth/`.
Application initialization, logging, and middleware split from the current monolithic `app.py`
into `app/main.py` and `app/core/`. A compatibility entrypoint is maintained via both
`app.py` (for `python app.py`) and `app/__init__.py` (for `uvicorn app:app`). All import
references in source and test files are updated to the new paths.

---

## Technical Context

**Language/Version**: Python 3.11 (per `ApiApp.Dockerfile`: `FROM python:3.11-alpine`)

**Primary Dependencies** (from `src/api/python/requirements.txt`):
- FastAPI 0.136.0
- uvicorn[standard] 0.44.0
- Pydantic[email] 2.13.3
- azure-identity 1.25.3
- azure-monitor-opentelemetry 1.8.7
- opentelemetry-instrumentation-fastapi 0.61b0
- agent-framework-core 1.3.0 / agent-framework-foundry 1.3.0

**Testing** (from `src/api/python/requirements.txt` and `pytest.ini`):
- pytest 9.0.3, pytest-cov 7.1.0, pytest-asyncio 1.3.0
- `pythonpath = ./src/api/python`

**Target Platform**: Linux Alpine container; local macOS dev

**Project Type**: web-service (FastAPI)

**Storage**: N/A — no schema or persistence changes in this spec

**Performance Goals**: N/A — no behavior or performance changes in this spec

**Constraints**:
- All existing routes, status codes, response shapes, streaming behavior must remain identical
- `python app.py` and `uvicorn app:app` startup paths must work without script changes
- No new test markers, plugins, or configuration sections in `pytest.ini`
- No flake8 violations per `.flake8` and `src/.flake8`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python FastAPI is system of record | ✅ PASS | All changes target `src/api/python/` exclusively |
| II. .NET backend retired | ✅ PASS | Not touched |
| III. External API contract stable | ✅ PASS | Modules move as-is; no route or behavior changes |
| IV. React frontend out of scope | ✅ PASS | Not touched |
| V. Brownfield — preserve behavior | ✅ PASS | Move-as-is strategy for all router modules |
| VI. No hardcoded credentials | ✅ PASS | `azure-identity` pattern preserved in moved modules |
| VII. Agent Framework via Microsoft | ✅ PASS | Agent framework imports move with the module, unchanged |
| VIII. Data behind dedicated layer | ⚠️ PARTIAL | `chat.py`, `history.py`, `history_sql.py` still mix routing with direct data access. Intra-module concern separation is **explicitly out of scope** per Spec 002 and deferred to a subsequent spec. The `app/data/` placeholder layer is created now to establish the architecture skeleton. |
| IX. pytest configuration | ✅ PASS | `pytest.ini`, `.coveragerc`, `.flake8` unchanged; `pythonpath` adjustment permitted only if needed |
| X. Layered architecture | ✅ PASS | This spec establishes the five-layer skeleton (`api`, `services`, `agents`, `data`, `core`) |
| XI. Spec Kit workflow | ✅ PASS | This plan is produced per the mandated workflow |
| XII. Verified tool versions | ✅ PASS | All versions sourced from `requirements.txt` and existing config files |

**Gate decision**: PASS — one partial (Principle VIII) is explicitly justified by the spec's
out-of-scope declaration. No compliance blockers.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-fastapi-restructure/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions
├── data-model.md        # Phase 1 — module movement map
├── quickstart.md        # Phase 1 — validation guide
├── contracts/
│   └── api-contract.md  # Phase 1 — contract (unchanged; documents new source paths)
└── tasks.md             # Phase 2 — task list (/speckit-tasks output)
```

### Source Code — Current (before restructuring)

```text
src/api/python/
├── app.py                  # entry point, CORS, middleware, telemetry, router registration
├── chat.py                 # FastAPI router + business logic + agent calls (mixed)
├── history.py              # FastAPI router + Cosmos DB access (mixed)
├── history_sql.py          # FastAPI router + Fabric SQL access (mixed)
├── auth/
│   ├── auth_utils.py
│   ├── azure_credential_utils.py
│   └── sample_user.py
└── requirements.txt

src/test/api/python/
├── conftest.py             # sys.path + Azure SDK mocks
├── test_app.py
├── test_chat.py
├── test_history.py
├── test_history_sql.py
├── test_logging_middleware.py
└── auth/
    ├── test_auth_utils.py
    ├── test_azure_credential_utils.py
    └── test_sample_user.py
```

### Source Code — Target (after restructuring)

```text
src/api/python/
├── app.py                  # COMPATIBILITY SHIM (kept); re-exports from app.main; has uvicorn __main__
├── app/                    # application package (new)
│   ├── __init__.py         # re-exports app + build_app from app.main (for uvicorn app:app)
│   ├── main.py             # build_app(), CORS, middleware wiring, router registration, health
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── chat.py         # moved from src/api/python/chat.py (as-is)
│   │       ├── history.py      # moved from src/api/python/history.py (as-is)
│   │       └── history_sql.py  # moved from src/api/python/history_sql.py (as-is)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── logging.py      # _configure_logging() + conversation_id_var, user_id_var (from app.py)
│   │   ├── middleware.py   # attach_trace_attributes middleware (from app.py)
│   │   └── auth/
│   │       ├── __init__.py
│   │       ├── auth_utils.py           # moved from auth/auth_utils.py (as-is)
│   │       ├── azure_credential_utils.py  # moved from auth/azure_credential_utils.py (as-is)
│   │       └── sample_user.py          # moved from auth/sample_user.py (as-is)
│   ├── services/
│   │   └── __init__.py     # placeholder
│   ├── agents/
│   │   └── __init__.py     # placeholder
│   └── data/
│       └── __init__.py     # placeholder
└── requirements.txt        # unchanged

src/test/api/python/
├── conftest.py             # UPDATED: sys.modules mock keys → app.api.routers.*
├── test_app.py             # UNCHANGED: from app import build_app still works via __init__.py
├── test_chat.py            # UPDATED: from chat import … → from app.api.routers.chat import …
├── test_history.py         # UPDATED: from history import … → from app.api.routers.history import …
├── test_history_sql.py     # UPDATED: from history_sql import … → from app.api.routers.history_sql import …
├── test_logging_middleware.py  # UPDATED: imports from app (package now) — verify still resolves
└── auth/
    ├── test_auth_utils.py           # UPDATED: from auth.* → from app.core.auth.*
    ├── test_azure_credential_utils.py  # UPDATED: from auth.* → from app.core.auth.*
    └── test_sample_user.py             # UPDATED: from auth.* → from app.core.auth.*
```

**Structure Decision**: Single-project, package-oriented FastAPI structure. The `app/`
package is introduced alongside the existing `app.py` shim. Python 3 package resolution
gives `app/` precedence over `app.py` for `import app` calls (including `uvicorn app:app`),
while `python app.py` executes the shim directly as `__main__` — both startup paths work
without script changes. See research.md for full analysis.

---

## Complexity Tracking

| Situation | Why Acceptable | Simpler Alternative Rejected Because |
|-----------|---------------|-------------------------------------|
| Principle VIII partial — data access not yet behind dedicated layer | Spec 002 explicitly scopes this as deferred; `app/data/` placeholder created | Extracting data access from 3 mixed-concern modules in the same spec would double scope and risk |
| Both `app.py` and `app/` coexist | Python 3 package-takes-precedence rule makes this safe; both startup paths verified in research.md | Renaming `app.py` to a different shim name would require Dockerfile and start script changes — FR-003 and FR-007 prohibit that |
