# Tasks: Cosmos DB Chat History Reliability

**Input**: Design documents from `specs/006-cosmos-history-reliability/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, quickstart.md ✓

**Note**: This is a three-bug fix spec. Each user story maps to one identified defect. Tasks are surgical — no new files, no new modules, no schema changes. The fix for each story is confined to one or two files and includes updating any existing tests that were coded around the bug.

**Organization**: Tasks are grouped by user story to allow each fix to be applied, tested, and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Record the starting test baseline before any changes.

- [x] T001 Run `.venv/bin/pytest src/test/api/python/ -q --tb=no` from repo root and record exact counts (passed, failed, errors, skipped); if counts differ from the known baseline (268 passed, 178 failed, 41 errors, 2 skipped), investigate before proceeding
  - **Result**: 467 passed, 20 failed, 2 skipped (489 total — same as prior baseline total; prior 178 failures + 41 errors resolved; 20 remaining failures are in test_history_sql.py, all environment-gated SQL/ODBC tests) ✅

---

## Phase 3: User Story 1 — Conversation Message Clearing Works Correctly (Priority: P1) 🎯 MVP

**Goal**: Fix the ownership field name mismatch so that `clear_messages()` correctly validates whether the requesting user owns the conversation, enabling the operation to succeed for valid requests and reject invalid ones.

**Independent Test**: Run `.venv/bin/pytest src/test/api/python/test_history.py -k "clear_messages" -v` — all 4+ clear-messages tests pass, including the new rejection test.

### Implementation for User Story 1

- [x] T002 [P] [US1] In `src/api/python/app/api/routers/history.py` at line 433, change `conversation["user_id"]` to `conversation["userId"]` to match the field name written by `cosmos_history.py:101`
  - **Result**: One-line change applied ✅
- [x] T003 [P] [US1] In `src/test/api/python/test_history.py` at line 947, update the mock return value from `{"id": "conv123", "user_id": "user123"}` to `{"id": "conv123", "userId": "user123"}` so the test reflects the real Cosmos document shape
  - **Result**: Mock field updated; "Note: code checks..." comment removed ✅
- [x] T004 [US1] In `src/test/api/python/test_history.py`, add a new async test `test_clear_messages_rejects_different_user` in the existing history test class: mock `get_conversation` to return `{"id": "conv123", "userId": "other_user"}`, call `clear_messages("user123", "conv123")`, and assert the result is `False`
  - **Result**: Test added; also asserts `delete_messages` was NOT called ✅
- [x] T005 [US1] Run `.venv/bin/pytest src/test/api/python/test_history.py -k "clear_messages" -v` and confirm all clear-messages tests pass; if any fail, diagnose and fix before proceeding
  - **Result**: 11/11 passed (including new `test_clear_messages_rejects_different_user`) ✅

**Checkpoint**: `clear_messages()` correctly validates ownership. Requesting user can clear their own conversation; other users are rejected. US1 complete.

---

## Phase 4: User Story 2 — Conversation IDs Are Always Unique (Priority: P2)

**Goal**: Fix the mutable default argument so that each call to `create_conversation()` without an explicit ID generates a fresh unique identifier, eliminating the latent ID-collision defect.

**Independent Test**: Run `.venv/bin/pytest src/test/api/python/test_history.py -k "create_conversation" -v` — all create-conversation tests pass, including the new uniqueness test.

### Implementation for User Story 2

- [x] T006 [P] [US2] In `src/api/python/app/data/cosmos_history.py` at line 93, change the method signature from `conversation_id=str(uuid.uuid4())` to `conversation_id=None`; add a guard as the first line of the method body: `if conversation_id is None: conversation_id = str(uuid.uuid4())`
  - **Result**: Signature changed to `None` default; in-body guard added ✅
- [x] T007 [P] [US2] In `src/test/api/python/test_history.py`, add a new async test `test_create_conversation_generates_unique_ids` in the `TestCosmosClient` class: call `create_conversation` twice on the same client instance without providing `conversation_id`; mock `container_client.upsert_item` to return the input dict; assert the two resulting `"id"` values are different strings
  - **Result**: Test added with side_effect capture; asserts `result1["id"] != result2["id"]` ✅
- [x] T008 [US2] Run `.venv/bin/pytest src/test/api/python/test_history.py -k "create_conversation" -v` and confirm all create-conversation tests pass; if any fail, diagnose and fix before proceeding
  - **Result**: 3/3 passed (existing two + new uniqueness test) ✅

**Checkpoint**: `create_conversation()` generates a unique identifier on each call when none is provided. Existing call sites that pass an explicit ID are unaffected. US2 complete.

---

## Phase 5: User Story 3 — History Update Processes Messages Consistently (Priority: P3)

**Goal**: Remove the two redundant `messages = request_json["messages"]` assignments from `update_conversation()`, leaving the single safe `.get()` assignment at line 146 as the only source for the messages list.

**Independent Test**: Run `.venv/bin/pytest src/test/api/python/test_history.py -k "update_conversation" -v` — all update-conversation tests pass with no mock changes.

### Implementation for User Story 3

- [x] T009 [US3] In `src/api/python/app/api/routers/history.py`, remove the assignment `messages = request_json["messages"]` at line 161 (the line immediately before the `if len(messages) > 0 and messages[0]["role"] == "user":` block); remove the identical assignment at line 188 (immediately before `if len(messages) > 0 and messages[-1]["role"] in ("assistant", "error"):`); verify line 146 (`messages = request_json.get("messages", [])`) remains as the sole assignment
  - **Result**: Both redundant assignments removed (with their preceding comment blocks); `.get()` at line 146 is the sole source ✅
- [x] T010 [US3] Run `.venv/bin/pytest src/test/api/python/test_history.py -k "update_conversation" -v` and confirm all update-conversation tests pass; no mock changes are required for this fix
  - **Result**: 4/4 passed — no mock changes needed ✅

**Checkpoint**: `update_conversation()` reads the message list exactly once from the request payload via the safe `.get()` call. No duplicate or shadowing assignments remain. US3 complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm no regressions across the full test suite, lint remains clean, and all three fixes are verifiably in place.

- [x] T011 [P] Run `.venv/bin/pytest src/test/api/python/ -q --tb=short` from repo root; confirm (a) passing count ≥ baseline from T001 plus the two new tests added in T004 and T007, (b) no previously passing test is now failing; if new failures appear, diagnose with `-v --tb=long` and fix the regression before proceeding
  - **Result**: 469 passed (baseline 467 + 2 new regression tests), 20 failed (unchanged SQL environment-gated tests), 2 skipped — no regressions ✅
- [x] T012 [P] Run `.venv/bin/flake8 src/api/python/app/` from repo root and confirm exit code 0; if violations exist, fix them in the relevant file
  - **Result**: Exit code 0, no violations ✅
- [x] T013 [P] Run `grep -n "conversation\[.user_id.\]" src/api/python/app/api/routers/history.py` and confirm zero matches (Bug 1 fix verified — no remaining snake_case ownership lookups)
  - **Result**: Zero matches ✅
- [x] T014 [P] Run `grep -n "conversation_id=None\|if conversation_id is None" src/api/python/app/data/cosmos_history.py` and confirm two matches (Bug 2 fix verified — None sentinel and in-body guard both present)
  - **Result**: Two matches — line 93 (`conversation_id=None`) and line 96 (`if conversation_id is None:`) ✅
- [x] T015 [P] Run `grep -n 'messages = request_json\["messages"\]' src/api/python/app/api/routers/history.py` and confirm zero matches (Bug 3 fix verified — both redundant assignments removed)
  - **Result**: Zero matches ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run T001 immediately
- **Phase 3 (US1)**: Depends on Phase 1 baseline; T002 and T003 are parallel (different files); T004 depends on T003 (same file); T005 depends on T002, T003, T004
- **Phase 4 (US2)**: Independent of Phase 3 — can start after T001; T006 and T007 are parallel (different files); T008 depends on T006 and T007
- **Phase 5 (US3)**: Independent of Phases 3 and 4 — can start after T001; T010 depends on T009
- **Phase 6 (Polish)**: Depends on all user story phases completing; T011–T015 are all parallel

### User Story Dependencies

- **US1 (P1)**: Depends only on T001 baseline
- **US2 (P2)**: Depends only on T001 baseline (independent of US1)
- **US3 (P3)**: Depends only on T001 baseline (independent of US1 and US2)

### ⚠️ Shared File Caution

Both US1 (T002) and US3 (T009) modify `src/api/python/app/api/routers/history.py`. If implementing both stories in the same session, complete and verify US1 first (including T005), then apply US3. Do not modify the file for both fixes simultaneously.

### Parallel Opportunities

```bash
# After T001 completes, all of these can start immediately:
T002: Fix history.py line 433 (US1 code fix)
T003: Fix test_history.py line 947 mock (US1 test fix)
T006: Fix cosmos_history.py line 93 signature (US2 code fix)
T007: Add uniqueness test in test_history.py (US2 test addition)

# T004 after T003 completes (same file):
T004: Add clear_messages rejection test

# T009 after T005 confirms US1 is clean (avoids simultaneous history.py edits):
T009: Remove duplicate assignments from history.py (US3 fix)
```

---

## Parallel Example: User Story 1

```bash
# Step 1 — Sequential baseline:
T001: Record pytest baseline counts

# Step 2 — Parallel (different files, no dependencies):
T002: Fix history.py ownership field (src/api/python/app/api/routers/history.py)
T003: Fix test mock field name (src/test/api/python/test_history.py)

# Step 3 — Sequential (same file as T003):
T004: Add rejection regression test (src/test/api/python/test_history.py)

# Step 4 — Verification:
T005: Run clear_messages tests and confirm all pass
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001: Record baseline
2. Complete T002 and T003 in parallel: Apply fix + update mock
3. Complete T004: Add rejection regression test
4. Complete T005: Confirm all clear-messages tests pass
5. **STOP and VALIDATE**: `clear_messages()` now correctly enforces ownership — US1 complete
6. Run T011 and T012 immediately after US1 to confirm no regressions before moving to US2

### Incremental Delivery

1. T001 (baseline) → T002+T003 (parallel) → T004 → T005 → **MVP: ownership fix confirmed**
2. T006+T007 (parallel) → T008 → **US2: unique ID generation confirmed**
3. T009 → T010 → **US3: duplicate assignment removed**
4. T011–T015 (all parallel) → **Full quality gate passed**

---

## Notes

- **No new files**: All changes are in-place edits to existing files. No new source files or test files are created.
- **Shared file risk**: `history.py` is modified by both US1 (T002) and US3 (T009). Serialize these edits — complete and verify US1 before touching the file again for US3.
- **Mock field name**: The existing `test_clear_messages_success` mock at `test_history.py:947` uses `"user_id"` by design, matching the bug. After T002 (fix) and T003 (mock update), the test will correctly verify the fixed behavior.
- **Fallback ID in practice**: The `create_conversation()` fallback path (Bug 2) is never triggered in production today — all call sites pass an explicit ID. The fix is correctness hardening. The new test added in T007 exercises this path for the first time.
- **No SQL history changes**: `src/api/python/app/api/routers/history_sql.py` and `src/test/api/python/test_history_sql.py` are not touched by any task.
