# Implementation Plan: Cosmos DB Chat History Reliability

**Branch**: `006-cosmos-history-reliability` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-cosmos-history-reliability/spec.md`

## Summary

Fix three identified defects in the Cosmos DB chat history layer: a field-name mismatch in the conversation ownership check that silently breaks the clear-messages operation, a mutable default argument that prevents unique fallback ID generation, and a duplicate variable assignment in the history update path. All fixes are confined to two files (`app/data/cosmos_history.py` and `app/api/routers/history.py`) and require no API contract changes, no database migration, and no frontend changes.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI 0.136.0, azure-cosmos 4.15.0, pydantic 2.13.3, azure-identity 1.25.3

**Storage**: Azure Cosmos DB (workshop mode only); SQL/Fabric history layer is untouched

**Testing**: pytest 9.0.3, pytest-asyncio 1.3.0, unittest.mock

**Target Platform**: Linux server (Azure App Service), local development (macOS/Linux with `.env`)

**Project Type**: Brownfield web service — bug fixes only

**Performance Goals**: N/A — correctness-only changes with no performance impact

**Constraints**: No SQL history changes; no API contract changes; no frontend changes; no new dependencies; no database migration

**Scale/Scope**: Three surgical code changes across two files; test mock update in one test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Python FastAPI is system of record | ✅ PASS | All fixes target `src/api/python/` only |
| II — .NET backend retired | ✅ PASS | No .NET files touched |
| III — External API contract stable | ✅ PASS | `POST /chat` and `GET /history` behavior unchanged; `POST /history/clear` restores intended behavior with same request/response shape |
| IV — React frontend unchanged | ✅ PASS | No frontend files modified |
| V — Preserve existing behavior | ✅ PASS | Fixes restore intended behavior; the broken ownership check (always-false) is a defect, not intended behavior |
| VI — No hardcoded credentials | ✅ PASS | No credentials introduced |
| VII — Agent Framework | ✅ PASS | Not applicable to history layer |
| VIII — Data access behind dedicated layer | ✅ PASS | Bug 2 fix is in `app/data/cosmos_history.py`; Bug 1 and 3 fixes are in the router's invocation of the data layer |
| IX — Testing via existing pytest config | ✅ PASS | Existing pytest + pytest-asyncio; existing test file `test_history.py` updated; no new test framework |
| X — Layered architecture maintained | ✅ PASS | No layer boundary violations introduced |
| XI — Spec Kit workflow mandatory | ✅ PASS | This plan exists |
| XII — Reference only verified tool versions | ✅ PASS | All versions from `src/api/python/requirements.txt` |

**Gate result**: All 12 principles PASS. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-cosmos-history-reliability/
├── plan.md              # This file
├── research.md          # Phase 0 findings (pre-verified from code inspection)
├── quickstart.md        # Phase 1 validation guide
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/api/python/app/
├── data/
│   └── cosmos_history.py         # Bug 2 fix: mutable default argument in create_conversation()
└── api/
    └── routers/
        └── history.py            # Bug 1 fix: ownership field mismatch in clear_messages()
                                  # Bug 3 fix: duplicate assignment in update_conversation()

src/test/api/python/
└── test_history.py               # Update existing mock for Bug 1 (user_id → userId);
                                  # add regression tests for Bug 2 fallback uniqueness
```

**Structure Decision**: Single-file changes within the existing layered architecture. No new files in `src/`; no new modules or packages.

## Phase 0: Research Findings

All three bugs were pre-verified by direct code inspection. No unknowns remain.

See [research.md](research.md) for full decision records.

### Summary of Pre-Verified Findings

| Finding | File | Line | Status |
|---------|------|------|--------|
| `clear_messages()` checks `conversation["user_id"]` but Cosmos document field is `"userId"` | `app/api/routers/history.py` | 433 | ✅ Confirmed |
| `create_conversation()` default `conversation_id=str(uuid.uuid4())` evaluated at definition time | `app/data/cosmos_history.py` | 93 | ✅ Confirmed |
| `update_conversation()` assigns `messages = request_json["messages"]` at lines 161 and 188 | `app/api/routers/history.py` | 161, 188 | ✅ Confirmed |
| Existing test `test_clear_messages_success` mocks `"user_id"` (snake_case) matching the bug | `test_history.py` | 947 | ✅ Confirmed — mock must be updated with fix |
| `create_conversation()` called with explicit `conversation_id` at every call site in production code | `app/api/routers/history.py` | 154 | ✅ Confirmed — fallback is latent, not active |
| Line 146 assignment `messages = request_json.get("messages", [])` is sufficient for all downstream uses | `app/api/routers/history.py` | 146 | ✅ Confirmed — lines 161/188 are unreachable dead code given identical source |

## Phase 1: Design

### Data Model

No new entities. No changes to the Cosmos DB document schema. The Cosmos document already stores `"userId"` (camelCase); the fix aligns the runtime ownership check to match that stored field name. No migration required.

### Interface Contracts

No new or changed external interfaces. `POST /history/clear` already exists; its request shape (`{conversation_id: string}`) and response shape (`{message: string}` on success/failure) are unchanged. The fix corrects behavior behind the existing interface.

See [quickstart.md](quickstart.md) for validation scenarios.

### Fix Specifications

#### Fix 1 — Ownership Field Name Mismatch (`history.py:433`)

**Current (broken)**:
```python
if conversation["user_id"] != user_id:
```

**Corrected**:
```python
if conversation["userId"] != user_id:
```

**Rationale**: Cosmos documents are written with `"userId"` (camelCase) by `create_conversation()` at line 101 of `cosmos_history.py`. The ownership check must use the same key that is stored.

**Test impact**: `test_clear_messages_success` at `test_history.py:947` provides a mock with `{"id": "conv123", "user_id": "user123"}`. After the fix, the mock must use `{"id": "conv123", "userId": "user123"}` to reflect the real document shape. A new test `test_clear_messages_rejects_different_user` should be added to assert the rejection path works.

#### Fix 2 — Mutable Default Argument (`cosmos_history.py:93`)

**Current (broken)**:
```python
async def create_conversation(
    self, user_id, conversation_id=str(uuid.uuid4()), title=""
):
```

**Corrected**:
```python
async def create_conversation(
    self, user_id, conversation_id=None, title=""
):
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())
```

**Rationale**: Python evaluates default argument expressions once at function definition time, not per call. All calls omitting `conversation_id` would receive the same UUID. The fix defers generation to call time.

**Test impact**: Existing test always passes an explicit `conversation_id="conv123"` and is unaffected. A new test `test_create_conversation_generates_unique_ids` should be added to assert that two calls without an explicit ID produce distinct values.

#### Fix 3 — Duplicate Message Assignment (`history.py:161` and `history.py:188`)

**Current (broken)**:
```python
# Line 146 — safe assignment with default
messages = request_json.get("messages", [])
...
# Line 161 — redundant, re-reads same key, no default
messages = request_json["messages"]
...
# Line 188 — identical redundant re-read
messages = request_json["messages"]
```

**Corrected**: Remove lines 161 and 188. The line 146 assignment is sufficient — it reads from the same source with a safe default and the variable is in scope for all downstream uses.

**Rationale**: Lines 161 and 188 shadow the line 146 assignment without changing its value (both `request_json.get("messages", [])` and `request_json["messages"]` return the same list when the key exists). Removing the shadowing assignments eliminates ambiguity and the latent `KeyError` risk if `"messages"` is ever absent.

**Test impact**: Existing `test_update_conversation_success` remains valid. No mock changes needed since both assignments read from the same source.
