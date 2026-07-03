# Tasks: Agent Orchestration Layer Extraction

**Input**: Design documents from `specs/004-agent-orchestration-extraction/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, contracts/ ✓, quickstart.md ✓

**Note**: Tests are NOT generated as new tasks — test file updates are implementation tasks
(migrating patch targets) required to keep the existing suite green.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story. The entire implementation is a single brownfield structural refactor;
all user stories are satisfied by the same set of file changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm starting state before any code changes.

- [ ] T001 Run `.venv/bin/pytest src/test/api/python/ -q` from repo root and record baseline counts (expected: ≥268 passed, 178 failed, 41 errors, 2 skipped); note any deviations in a comment in `specs/004-agent-orchestration-extraction/tasks.md`

---

## Phase 3: User Story 1 — Chat Orchestration Extracted to Agent Layer (Priority: P1) 🎯 MVP

**Goal**: Move all non-HTTP orchestration logic from `chat.py` into a new
`app/agents/chat_orchestrator.py` so the router is a thin HTTP adapter and the
orchestrator is independently importable.

**Independent Test**: `python3 -c "import sys; sys.path.insert(0,'src/api/python'); from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured, ExpCache, get_thread_cache, stream_openai_text, stream_openai_text_workshop, _parse_mcp_docs, _extract_mcp_from_raw, _MARKER_RE; print('OK')"` exits cleanly from repo root.

### Implementation for User Story 1

- [ ] T002 [US1] Create `src/api/python/app/agents/chat_orchestrator.py` — move all symbols listed in plan.md "Symbols that move" table: `load_dotenv()` call, `IS_WORKSHOP`, `AZURE_ENV_ONLY`, `USE_USER_ACCESS_TOKEN`, `agent_log_level` + foundry logger config, `ExpCache` class, `track_event_if_configured`, `thread_cache` global, `get_thread_cache`, `stream_openai_text`, `_MARKER_RE`, `_parse_mcp_docs`, `_extract_mcp_from_raw`, `stream_openai_text_workshop`, `stream_chat_request`; add `logger = logging.getLogger(__name__)` at module level; imports needed: `asyncio`, `json`, `logging`, `os`, `random`, `re`, `from cachetools import TTLCache`, `from dotenv import load_dotenv`, `from fastapi import HTTPException, status`, `from azure.core.exceptions import HttpResponseError`, `from azure.monitor.events.extension import track_event`, `from azure.ai.projects.aio import AIProjectClient`, `from agent_framework_foundry import FoundryAgent`, `from app.core.auth.azure_credential_utils import get_azure_credential_async`

- [ ] T003 [P] [US1] Update `src/api/python/app/api/routers/chat.py` — remove all symbols per plan.md "Symbols that move" table; remove imports no longer needed (`json`, `random`, `re`, `cachetools`, `dotenv`, `azure.core.exceptions.HttpResponseError`, `azure.monitor.events.extension.track_event`, `azure.ai.projects.aio.AIProjectClient`, `agent_framework_foundry.FoundryAgent`); add `from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured`; keep `HOST_NAME`, `HOST_INSTRUCTIONS`, `router`, `logger`, `fetch_azure_search_content`, `conversation`; keep `asyncio`, `os`, `logging`, `urllib.parse`, `get_azure_credential_async`, `get_authenticated_user_details`, `opentelemetry` imports

- [ ] T004 [P] [US1] Update direct imports in `src/test/api/python/test_chat.py` — change `from app.api.routers.chat import X` to `from app.agents.chat_orchestrator import X` for all symbols that moved: `ExpCache`, `track_event_if_configured` (direct-call tests), `get_thread_cache`, `stream_openai_text`, `stream_openai_text_workshop`, `_parse_mcp_docs`, `_extract_mcp_from_raw`, `_MARKER_RE`; leave unchanged: `from app.api.routers.chat import HOST_NAME`, `HOST_INSTRUCTIONS`, `router`, `stream_chat_request`, `conversation`, `fetch_azure_search_content`

- [ ] T005 [US1] Update patch targets in `src/test/api/python/test_chat.py` — change 10 patch target prefixes per plan.md "Patch targets that change" table: `app.api.routers.chat.asyncio.create_task` → `app.agents.chat_orchestrator.asyncio.create_task`; `app.api.routers.chat.get_azure_credential_async` (stream/ExpCache tests) → `app.agents.chat_orchestrator.get_azure_credential_async`; `app.api.routers.chat.AIProjectClient` → `app.agents.chat_orchestrator.AIProjectClient`; `app.api.routers.chat.FoundryAgent` → `app.agents.chat_orchestrator.FoundryAgent`; `app.api.routers.chat.get_thread_cache` → `app.agents.chat_orchestrator.get_thread_cache`; `app.api.routers.chat.track_event` → `app.agents.chat_orchestrator.track_event`; `app.api.routers.chat.logging.warning` (track_event_if_configured tests) → `app.agents.chat_orchestrator.logging.warning`; `app.api.routers.chat.stream_openai_text` (stream_chat_request tests) → `app.agents.chat_orchestrator.stream_openai_text`; `app.api.routers.chat.stream_openai_text_workshop` (stream_chat_request tests) → `app.agents.chat_orchestrator.stream_openai_text_workshop`; `app.api.routers.chat.IS_WORKSHOP` → `app.agents.chat_orchestrator.IS_WORKSHOP`; leave unchanged: `app.api.routers.chat.stream_chat_request`, `app.api.routers.chat.track_event_if_configured` (route tests), `app.api.routers.chat.get_azure_credential_async` (fetch_azure_search_content test line ~981), `app.api.routers.chat.asyncio.to_thread`, `app.api.routers.chat.get_authenticated_user_details`

- [ ] T006 [US1] Verify `app/agents/chat_orchestrator.py` is importable without FastAPI startup — run `python3 -c "import sys; sys.path.insert(0,'src/api/python'); from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured, ExpCache, get_thread_cache, stream_openai_text, stream_openai_text_workshop, _parse_mcp_docs, _extract_mcp_from_raw, _MARKER_RE; print('OK')"` from repo root and confirm clean exit with "OK" printed

**Checkpoint**: Chat orchestration is fully extracted and the orchestrator module is independently importable. Proceed to US2 verification.

---

## Phase 4: User Story 2 — Chat Router Reduced to HTTP Concerns (Priority: P2)

**Goal**: Confirm `chat.py` contains only FastAPI route definitions and HTTP handling; confirm `chat_orchestrator.py` has no FastAPI route-binding imports at top level.

**Independent Test**: `grep -n "^from fastapi import\|^import fastapi" src/api/python/app/agents/chat_orchestrator.py` returns no lines; `grep -n "ExpCache\|stream_openai_text\|stream_openai_text_workshop\|FoundryAgent\|TTLCache" src/api/python/app/api/routers/chat.py` returns no lines.

### Implementation for User Story 2

- [ ] T007 [US2] Verify `src/api/python/app/api/routers/chat.py` contains no orchestration symbols — run `grep -n "ExpCache\|stream_openai_text\|stream_openai_text_workshop\|FoundryAgent\|TTLCache\|_MARKER_RE\|_parse_mcp_docs\|_extract_mcp_from_raw\|get_thread_cache\|thread_cache\|IS_WORKSHOP\|AZURE_ENV_ONLY\|USE_USER_ACCESS_TOKEN" src/api/python/app/api/routers/chat.py`; any matches that are not inside a comment indicate a missed removal — fix accordingly

- [ ] T008 [US2] Verify `src/api/python/app/agents/chat_orchestrator.py` has no top-level FastAPI route imports — run `grep -n "^from fastapi import APIRouter\|^from fastapi import.*Depends\|^import fastapi\|@router\." src/api/python/app/agents/chat_orchestrator.py`; result must be empty; note: `from fastapi import HTTPException, status` at top level is acceptable (exception classes, not route binding)

**Checkpoint**: Router is confirmed as HTTP-only; orchestrator is confirmed as FastAPI-agnostic at module level.

---

## Phase 5: User Story 3 — Existing Chat Tests Pass Without New Failures (Priority: P3)

**Goal**: Confirm the pytest suite passes with ≥268 tests (Spec 003 baseline) and no previously passing test is now failing.

**Independent Test**: `.venv/bin/pytest src/test/api/python/ -q` from repo root; passing count ≥268.

### Implementation for User Story 3

- [ ] T009 [US3] Run `.venv/bin/pytest src/test/api/python/ -q --tb=short` from repo root and confirm: (a) passing count ≥268, (b) no test that previously passed is now failing; if new failures appear, diagnose by running `.venv/bin/pytest src/test/api/python/test_chat.py -v --tb=long` and fix any remaining incorrect patch targets or missed import updates in `src/test/api/python/test_chat.py`

**Checkpoint**: Test suite passes at or above Spec 003 baseline. All user stories validated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint verification and spec metadata update.

- [ ] T010 Run `flake8 src/api/python/app/` from repo root and fix any violations in `src/api/python/app/agents/chat_orchestrator.py` or `src/api/python/app/api/routers/chat.py`; common issues to watch: unused imports after extraction, E303/E305 blank-line spacing after large removed blocks, line-length on long string literals

- [ ] T011 Update `specs/004-agent-orchestration-extraction/checklists/requirements.md` — mark all checklist items `[x]` to confirm the implementation satisfies all quality criteria from the spec; note any items that cannot be confirmed and document why

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run immediately
- **Phase 3 (US1)**: Depends on Phase 1; T002 must complete before T003/T004/T005/T006
- **Phase 4 (US2)**: Depends on T002 + T003 (both files must exist in final form)
- **Phase 5 (US3)**: Depends on T002, T003, T004, T005 (all code + test updates)
- **Phase 6 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 1 (baseline recorded)
- **US2 (P2)**: Depends on US1 implementation (T002, T003)
- **US3 (P3)**: Depends on full US1 implementation including test updates (T002-T005)

### Within Phase 3 (US1)

- **T002 first**: Must complete before any other US1 task
- **T003 and T004 in parallel [P]**: Different files; can proceed simultaneously after T002
- **T005 after T004**: Same file as T004 (test_chat.py); cleaner to separate import changes from patch-target changes
- **T006 after T002**: Verification depends only on the new file existing

### Parallel Opportunities

```bash
# After T002 completes, these can run in parallel:
Task T003: Update src/api/python/app/api/routers/chat.py
Task T004: Update direct imports in src/test/api/python/test_chat.py
```

---

## Parallel Example: User Story 1

```bash
# Step 1 — Sequential (must complete first):
Task T002: Create src/api/python/app/agents/chat_orchestrator.py

# Step 2 — Parallel (different files, both unblock after T002):
Task T003: Update src/api/python/app/api/routers/chat.py
Task T004: Update direct imports in src/test/api/python/test_chat.py

# Step 3 — Sequential (same file as T004, needs T003 state for correctness):
Task T005: Update patch targets in src/test/api/python/test_chat.py

# Step 4 — Verification (independent of T003/T004/T005):
Task T006: Verify orchestrator importability
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Record baseline
2. Complete T002: Create chat_orchestrator.py
3. Complete T003: Strip chat.py to HTTP-only
4. Complete T004 + T005: Fix test imports and patch targets
5. Complete T006: Verify import
6. **STOP and VALIDATE**: Run `.venv/bin/pytest src/test/api/python/test_chat.py -v`
7. All chat tests pass → US1 complete

### Incremental Delivery

1. Phase 1 (baseline) → Phase 3 US1 (extraction + test fixes) → **MVP**
2. Phase 4 US2 (structural verification) → confirms shape goal
3. Phase 5 US3 (full suite) → confirms no regression
4. Phase 6 (flake8 + checklist) → confirms quality gates

---

## Notes

- **Single-file extraction**: All orchestration logic goes into ONE new file. Do not create multiple files in `app/agents/` for this spec.
- **Hard move, no re-exports**: The plan intentionally does NOT re-export moved symbols from `chat.py` (except `stream_chat_request` and `track_event_if_configured` which the route handler calls). All test direct imports of moved symbols must update to `app.agents.chat_orchestrator`.
- **Patch target rule**: Patch where the name is looked up at call time. Functions defined in `chat_orchestrator.py` look up dependencies in the orchestrator's module namespace.
- **`HOST_NAME` / `HOST_INSTRUCTIONS`**: Stay in `chat.py` — they are unused by any extracted function and avoiding their move prevents test churn.
- **`asyncio` stays in `chat.py`**: `fetch_azure_search_content` uses `asyncio.to_thread` — do not remove the `import asyncio` from the router.
- **`get_azure_credential_async` stays in `chat.py`**: Also used by `fetch_azure_search_content`.
- **Flake8 watch**: After removing ~530 lines from chat.py, check for E303 (too many blank lines) and F401 (unused imports). After adding chat_orchestrator.py, check E501 (long lines already ignored by config).
