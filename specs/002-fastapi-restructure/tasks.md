---

description: "Task list for FastAPI Service Restructuring"
---

# Tasks: FastAPI Service Restructuring

**Input**: Design documents from `specs/002-fastapi-restructure/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contract.md, quickstart.md

**Tests**: No new tests are written. Existing pytest suite is the validation gate (FR-004).
Test import paths are updated as part of the structural work (US2); no test logic changes.

**Organization**: Tasks follow execution dependency order. US2 (P2) is the structural
implementation work; US3 (P3) verifies startup continuity; US1 (P1) is the acceptance gate
that can only execute after US2 and US3 are complete.

**Key design decisions** (from research.md):
- Both `app/` package and `app.py` shim coexist; Python 3 package-takes-precedence rule
  is intentional — see research.md Decision 1
- `app/__init__.py` re-exports `app` and `build_app` from `app.main` so `uvicorn app:app`
  (Dockerfile CMD) resolves correctly without script changes
- Test import mock keys in conftest.py must change from `chat`/`history`/`history_sql` to
  `app.api.routers.chat` etc. — see data-model.md for the full import change table
- `pytest.ini pythonpath = ./src/api/python` requires no modification

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Establish a passing baseline before any file is changed.

- [ ] T001 Run `pytest -m unittest src/test/api/python/ --ignore=src/test/api/python/e2e-test -v` from repo root (using `src/api/python/.venv/bin/pytest`) and record the passing test count as the baseline that must be matched at T028

**Checkpoint**: Baseline recorded. Proceed to creating the package skeleton.

---

## Phase 2: Foundational — Package Directory Skeleton

**Purpose**: Create all `__init__.py` markers and placeholder files before any source code
moves. The skeleton must exist before router or core files are written into it.

- [ ] T002 [P] Create routing layer directories — write empty `src/api/python/app/__init__.py`, `src/api/python/app/api/__init__.py`, and `src/api/python/app/api/routers/__init__.py` (each with no content, just a newline)
- [ ] T003 [P] Create core layer directories — write empty `src/api/python/app/core/__init__.py` and `src/api/python/app/core/auth/__init__.py`
- [ ] T004 [P] Create placeholder layer `__init__.py` files — write empty `src/api/python/app/services/__init__.py`, `src/api/python/app/agents/__init__.py`, and `src/api/python/app/data/__init__.py`

**Checkpoint**: Package skeleton complete. All `__init__.py` files exist; directories discoverable as Python packages.

---

## Phase 3: User Story 2 — Backend Is Organized Into Predictable Layers (Priority: P2)

**Goal**: Move all source modules to their designated layer, extract core infrastructure from
`app.py`, update all import references, and clean up the original flat module paths.

**Independent Test**: After all tasks in this phase complete, running
`grep -r "^from chat import\|^from history import\|^from history_sql import\|^from auth\." src/test/` returns zero results.

### Group A — Create Core Layer Files (parallel; no inter-dependencies)

- [ ] T005 [P] [US2] Create `src/api/python/app/core/logging.py` — extract from `src/api/python/app.py`: the `conversation_id_var` and `user_id_var` ContextVar declarations, the `_configure_logging()` function (renamed to `configure_logging()`), and the `_configure_logging()` call at module level (also renamed). Preserve all existing logic: basicConfig, azure-monitor setup, log record factory, logger suppression loop.
- [ ] T006 [P] [US2] Create `src/api/python/app/core/middleware.py` — extract from `src/api/python/app.py`: the `attach_trace_attributes(request, call_next)` inner function (convert to a top-level `async def`). Add import `from app.core.logging import conversation_id_var, user_id_var` at the top. Preserve all existing logic: span extraction, user_id_var/conversation_id_var setting, body parsing, fail-open exception handling.
- [ ] T007 [P] [US2] Create `src/api/python/app/core/auth/auth_utils.py` — copy `src/api/python/auth/auth_utils.py` verbatim; no import changes needed (relative import `from . import sample_user` continues to work in the new package location)
- [ ] T008 [P] [US2] Create `src/api/python/app/core/auth/azure_credential_utils.py` — copy `src/api/python/auth/azure_credential_utils.py` verbatim
- [ ] T009 [P] [US2] Create `src/api/python/app/core/auth/sample_user.py` — copy `src/api/python/auth/sample_user.py` verbatim

### Group B — Create Router Layer Files (parallel with each other; depends on Group A)

In each router file, update the two auth imports:
- `from auth.auth_utils import …` → `from app.core.auth.auth_utils import …`
- `from auth.azure_credential_utils import …` → `from app.core.auth.azure_credential_utils import …`
All other content is copied verbatim.

- [ ] T010 [P] [US2] Create `src/api/python/app/api/routers/chat.py` — copy `src/api/python/chat.py` and apply the two auth import updates above. Verify `from agent_framework_foundry import FoundryAgent` and all other non-auth imports are unchanged.
- [ ] T011 [P] [US2] Create `src/api/python/app/api/routers/history.py` — copy `src/api/python/history.py` and apply the two auth import updates above. The commented-out line `# from chat import adjust_processed_data_dates` stays as-is (commented).
- [ ] T012 [P] [US2] Create `src/api/python/app/api/routers/history_sql.py` — copy `src/api/python/history_sql.py` and apply the two auth import updates above.

### Group C — Create Application Initializer

- [ ] T013 [US2] Create `src/api/python/app/main.py` with the following content:
  1. Imports: `from app.core.logging import configure_logging`; `from app.core.middleware import attach_trace_attributes`; `from app.api.routers.chat import router as chat_router`; `from app.api.routers.history import router as history_router`; `from app.api.routers.history_sql import router as history_sql_router`; plus all other imports currently at the top of `app.py` (`FastAPI`, `CORSMiddleware`, `FastAPIInstrumentor`, `uvicorn`, `Request`, `json`, `os`, `logging`).
  2. Call `configure_logging()` at module level (before `build_app()`).
  3. Define `build_app() -> FastAPI` — identical to the current `build_app()` in `app.py` except: replace the inline `attach_trace_attributes` definition with `fastapi_app.middleware("http")(attach_trace_attributes)` to register the extracted middleware.
  4. Module-level: `app = build_app()` and `FastAPIInstrumentor.instrument_app(app, excluded_urls="health")`.

### Group D — Write Compatibility Entrypoints (parallel; depends on Group C)

- [ ] T014 [P] [US2] Write `src/api/python/app/__init__.py` — replace the empty placeholder written in T002 with: `from app.main import app, build_app  # noqa: F401`. This makes `uvicorn app:app` resolve the `app` attribute from the package without Dockerfile changes.
- [ ] T015 [P] [US2] Update `src/api/python/app.py` — replace its current content with the thin shim: import `from app.main import app, build_app  # noqa: F401`, then keep the `import uvicorn` and the `if __name__ == "__main__": uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)` block. Remove all other content (imports, `_configure_logging`, `build_app`, `app = build_app()`, `FastAPIInstrumentor` call — these are now in `app/main.py`).

### Group E — Delete Old Flat Modules (parallel; depends on Group D)

- [ ] T016 [P] [US2] Delete the original flat router files: `src/api/python/chat.py`, `src/api/python/history.py`, and `src/api/python/history_sql.py`
- [ ] T017 [P] [US2] Delete the original `src/api/python/auth/` directory and its three files (`auth_utils.py`, `azure_credential_utils.py`, `sample_user.py`)

### Group F — Update Test Import Paths (parallel; depends on Group E)

All changes are import path updates only. No test assertions, fixture logic, or mock behavior changes.

- [ ] T018 [P] [US2] Update `src/test/api/python/conftest.py` — in `should_mock_modules()` and `setup_test_environment()`, change every occurrence of `sys.modules['chat']` → `sys.modules['app.api.routers.chat']`, `sys.modules['history']` → `sys.modules['app.api.routers.history']`, `sys.modules['history_sql']` → `sys.modules['app.api.routers.history_sql']`. Also update the corresponding `.router` assignments.
- [ ] T019 [P] [US2] Update `src/test/api/python/test_chat.py` — change all `from chat import …` statements to `from app.api.routers.chat import …`. The `sys.path.insert` line at the top is unchanged (`src/api/python` stays on path).
- [ ] T020 [P] [US2] Update `src/test/api/python/test_history.py` — change all `from history import …` and `import history` statements to `from app.api.routers.history import …` and `from app.api.routers import history` respectively. `sys.path.insert` unchanged.
- [ ] T021 [P] [US2] Update `src/test/api/python/test_history_sql.py` — change all `from history_sql import …` and `import history_sql` statements to use `app.api.routers.history_sql`. Update any `importlib.import_module('history_sql')` calls to `importlib.import_module('app.api.routers.history_sql')`. `sys.path.insert` unchanged.
- [ ] T022 [P] [US2] Update `src/test/api/python/auth/test_auth_utils.py` — change `from auth.auth_utils import …` → `from app.core.auth.auth_utils import …`
- [ ] T023 [P] [US2] Update `src/test/api/python/auth/test_azure_credential_utils.py` — change `from auth.azure_credential_utils import …` → `from app.core.auth.azure_credential_utils import …`
- [ ] T024 [P] [US2] Update `src/test/api/python/auth/test_sample_user.py` — change `from auth.sample_user import …` → `from app.core.auth.sample_user import …`
- [ ] T025 [US2] Review `src/test/api/python/test_app.py` and `src/test/api/python/test_logging_middleware.py` — confirm that all `from app import build_app` usages resolve correctly via the new `app/__init__.py` re-export; make any import corrections if needed. No logic changes permitted.

**Checkpoint**: User Story 2 complete — new layer structure is in place, old flat modules deleted, all import references updated. Run `grep -r "^from chat import\|^from history import\|^from history_sql import\|^from auth\." src/test/` to confirm zero results.

---

## Phase 4: User Story 3 — Startup and Deployment Path Is Unchanged (Priority: P3)

**Goal**: Verify that both documented startup paths resolve correctly with the new structure.

**Independent Test**: `python -c "from app import app, build_app; print('OK')"` from `src/api/python/` prints OK with no import errors.

- [ ] T026 [US3] From `src/api/python/`, run these import sanity checks (using `.venv/bin/python` or activated venv):
  ```
  python -c "from app.main import app, build_app; print('app.main OK')"
  python -c "from app import app, build_app; print('app package OK')"
  python -c "from app.api.routers import chat, history, history_sql; print('routers OK')"
  python -c "from app.core.auth import auth_utils; print('core.auth OK')"
  python -c "from app import services, agents, data; print('placeholders OK')"
  ```
  All commands must complete with their success message. Fix any import error before proceeding.

- [ ] T027 [US3] Start the backend using the existing startup command from `src/api/python/`: `.venv/bin/python app.py` (or `python app.py`). Confirm uvicorn starts on port 8000 with no startup errors and `/health` responds with `{"status":"healthy"}`. **Environment-gated**: requires `.env` with Azure credentials; if unavailable, document as pending (same constraint as Spec 001 T020).

**Checkpoint**: User Story 3 complete — startup paths verified unchanged. Proceed to US1 acceptance gate.

---

## Phase 5: User Story 1 — API Contract Is Fully Preserved (Priority: P1)

**Goal**: Confirm zero regressions in the automated test suite and that all four API surface
areas continue to respond correctly.

**Depends on**: US2 (Phase 3) and US3 (Phase 4) must both be complete.

**Independent Test**: `pytest -m unittest` passes with count ≥ baseline from T001.

### Automated Test Validation

- [ ] T028 [US1] Run `pytest -m unittest src/test/api/python/ --ignore=src/test/api/python/e2e-test -v` from repo root and confirm all tests that passed in T001 still pass with no new failures. Count must equal or exceed T001 baseline.

### API Smoke Tests (environment-gated)

The following three tasks require the backend to be running (T027 must be complete):

- [ ] T029 [US1] Smoke test `GET /health`: `curl http://127.0.0.1:8000/health` — confirm response is `{"status":"healthy"}` with HTTP 200. **Environment-gated**.
- [ ] T030 [US1] Smoke test `POST /api/chat`: submit a minimal chat request and confirm a streaming response is returned with no 404, 500, or connection error. **Environment-gated**.
- [ ] T031 [US1] Smoke test history routes: `curl "http://127.0.0.1:8000/history/list?user_id=test-user&limit=5"` and `curl "http://127.0.0.1:8000/historyfab/list?user_id=test-user&limit=5"` — confirm JSON responses with no 404 or 500. **Environment-gated**.

**Checkpoint**: User Story 1 acceptance gate passed — API contract is intact and automated test suite shows no regressions.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Confirm linting, structure completeness, and frontend isolation.

- [ ] T032 [P] Run `flake8 src/api/python/app/ src/api/python/app.py` using the venv's flake8; confirm zero violations. Run full scope `flake8 src/api/python/` to confirm no regressions beyond any pre-existing baseline.
- [ ] T033 [P] Verify the React frontend is untouched: `git diff --name-only HEAD src/App/` must return zero results.
- [ ] T034 [P] Verify package structure completeness per quickstart.md Step 1 — confirm all expected directories exist (`app/api/routers/`, `app/core/auth/`, `app/services/`, `app/agents/`, `app/data/`), all required files are present, and all original flat files are absent (`chat.py`, `history.py`, `history_sql.py`, `auth/`).
- [ ] T035 Run full quickstart validation from `specs/002-fastapi-restructure/quickstart.md` as the final end-to-end check.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately.
- **Foundational (Phase 2)**: Depends on Phase 1. T002, T003, T004 can run in parallel.
- **US2 (Phase 3)**: Depends on Phase 2.
  - Group A (T005–T009): parallel; no inter-dependencies within the group.
  - Group B (T010–T012): parallel with each other; each depends on Group A (auth files must exist at new paths before updating router import references).
  - Group C (T013): depends on Group B.
  - Group D (T014–T015): parallel; depends on Group C.
  - Group E (T016–T017): parallel; depends on Group D.
  - Group F (T018–T025): parallel within the group; depends on Group E.
- **US3 (Phase 4)**: Depends on US2 Phase 3 being complete.
- **US1 (Phase 5)**: Depends on both US2 and US3 being complete.
- **Polish (Final)**: Depends on US1 complete.

### Within Phase 3 (US2)

```bash
# Group A — parallel (all different files, no cross-deps):
T005: app/core/logging.py
T006: app/core/middleware.py
T007: app/core/auth/auth_utils.py
T008: app/core/auth/azure_credential_utils.py
T009: app/core/auth/sample_user.py

# Group B — parallel with each other, after Group A:
T010: app/api/routers/chat.py
T011: app/api/routers/history.py
T012: app/api/routers/history_sql.py

# Group C — sequential after Group B:
T013: app/main.py

# Group D — parallel, after Group C:
T014: app/__init__.py
T015: app.py (shim update)

# Group E — parallel, after Group D:
T016: delete old router files
T017: delete auth/ directory

# Group F — parallel within group, after Group E:
T018: conftest.py
T019: test_chat.py
T020: test_history.py
T021: test_history_sql.py
T022: auth/test_auth_utils.py
T023: auth/test_azure_credential_utils.py
T024: auth/test_sample_user.py
T025: test_app.py + test_logging_middleware.py (review)
```

---

## Parallel Execution Examples

### Group A (US2 core files — 5 simultaneous tasks)

```bash
Task: Create src/api/python/app/core/logging.py
Task: Create src/api/python/app/core/middleware.py
Task: Create src/api/python/app/core/auth/auth_utils.py
Task: Create src/api/python/app/core/auth/azure_credential_utils.py
Task: Create src/api/python/app/core/auth/sample_user.py
```

### Group B (US2 router files — 3 simultaneous tasks)

```bash
Task: Create src/api/python/app/api/routers/chat.py
Task: Create src/api/python/app/api/routers/history.py
Task: Create src/api/python/app/api/routers/history_sql.py
```

### Group F (US2 test imports — 7 simultaneous tasks)

```bash
Task: Update conftest.py sys.modules keys
Task: Update test_chat.py imports
Task: Update test_history.py imports
Task: Update test_history_sql.py imports
Task: Update auth/test_auth_utils.py imports
Task: Update auth/test_azure_credential_utils.py imports
Task: Update auth/test_sample_user.py imports
```

---

## Implementation Strategy

### MVP Scope (US1 Acceptance Gate Only)

All three user stories are interdependent in a brownfield restructuring: US2 creates the
new structure, US3 verifies startup, US1 validates the result. There is no partial MVP —
the restructuring must be completed atomically. Execute phases 1–5 in sequence.

### Recommended Execution Order (single contributor)

1. **Phase 1 (T001)**: Record baseline — under 1 minute.
2. **Phase 2 (T002–T004)**: Create skeleton — under 5 minutes.
3. **Phase 3 Group A (T005–T009)**: Core + auth files — can be done in parallel by an agent.
4. **Phase 3 Group B (T010–T012)**: Router files — parallel.
5. **Phase 3 Group C (T013)**: `app/main.py` — most complex task; allow 15 minutes.
6. **Phase 3 Group D (T014–T015)**: Shim files — quick.
7. **Phase 3 Group E (T016–T017)**: Delete originals — quick.
8. **Phase 3 Group F (T018–T025)**: Test import updates — parallel.
9. **Phase 4 (T026–T027)**: Startup verification.
10. **Phase 5 (T028–T031)**: Acceptance gate.
11. **Final Phase (T032–T035)**: Polish.

### Rollback Strategy

If verification fails at any checkpoint:
- Before deleting old files (before T016–T017): old modules still exist; revert new files only.
- After deleting old files: restore from git (`git checkout HEAD -- src/api/python/chat.py ...`).
- After all changes: `git diff --stat` shows full change set; revert the branch to discard all.

---

## Notes

- [P] tasks operate on different files with no cross-dependencies — safe to run in parallel.
- T013 (`app/main.py`) is the most complex task. Read the current `app.py` and the `build_app()`
  function carefully before writing. The middleware registration changes from an inline
  definition to using the extracted `attach_trace_attributes` from `app.core.middleware`.
- T025 (test_app.py / test_logging_middleware.py review) is expected to find no changes needed.
  If any imports are broken, fix them and document what changed.
- T027, T029–T031 (environment-gated) require an Azure dev environment with `.env` configured.
  If unavailable, document as pending — same constraint as Spec 001 T020–T023.
- Do not introduce any new assertions, test markers, or test logic. FR-004 permits only
  import path updates in test files.
- `pytest.ini pythonpath = ./src/api/python` remains unchanged (research.md Decision 6).
