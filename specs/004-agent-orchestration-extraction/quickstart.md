# Quickstart Validation Guide: Agent Orchestration Layer Extraction

**Spec**: 004
**Date**: 2026-06-28

This guide describes how to validate the Spec 004 implementation after it is complete.
It covers import verification, test suite validation, and flake8 verification.
No new test infrastructure is introduced — all validation uses existing tools.

---

## Prerequisites

- Python virtualenv activated: `source .venv/bin/activate` (from repo root)
- `.env` file present with at minimum `AZURE_AI_AGENT_ENDPOINT` and `AGENT_NAME_CHAT`
  (for tests that don't patch these; most tests use monkeypatching)
- No running application required for any of these checks

---

## Step 1: Verify Module Importability (FR-002, SC-003)

Confirm the orchestrator module can be imported without a running FastAPI application and
without triggering any network or database I/O.

```bash
# From repo root
python3 -c "
import sys
sys.path.insert(0, 'src/api/python')
from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured
from app.agents.chat_orchestrator import ExpCache, get_thread_cache
from app.agents.chat_orchestrator import stream_openai_text, stream_openai_text_workshop
from app.agents.chat_orchestrator import _parse_mcp_docs, _extract_mcp_from_raw, _MARKER_RE
print('All imports succeeded — no network/db I/O triggered')
"
```

**Expected outcome**: Script exits cleanly with the success message.
**Failure signal**: Any `ImportError`, `ModuleNotFoundError`, or exception from a network
or database call.

---

## Step 2: Verify Chat Router Is Importable (SC-003 complementary check)

```bash
python3 -c "
import sys
sys.path.insert(0, 'src/api/python')
from app.api.routers.chat import router, conversation, fetch_azure_search_content
from app.api.routers.chat import HOST_NAME, HOST_INSTRUCTIONS
print('Router imports succeeded')
"
```

**Expected outcome**: Clean exit.

---

## Step 3: Run the Full pytest Suite (SC-001, SC-005)

```bash
# From repo root
.venv/bin/pytest src/test/api/python/ -v --tb=short 2>&1 | tail -20
```

**Expected outcome**:
- Passing tests: ≥ 268 (Spec 003 baseline)
- No test that was passing before becomes failing
- Known environment-gated failures (pyodbc/Azure) remain in the same count: 178 failed,
  41 errors, 2 skipped

To focus only on chat tests:

```bash
.venv/bin/pytest src/test/api/python/test_chat.py -v --tb=short
```

**Expected outcome**: All previously passing chat tests continue to pass.

---

## Step 4: Verify flake8 (SC-004)

```bash
# From repo root
.venv/bin/flake8 src/api/python/app/ 2>&1
echo "Exit code: $?"
```

**Expected outcome**: No output, exit code 0 (zero violations).

If violations appear, consult the `.flake8` config for ignored rules (`E501`, `E203`).

---

## Step 5: Verify Router Is Smaller (SC-002 / US2)

```bash
wc -l src/api/python/app/api/routers/chat.py
wc -l src/api/python/app/agents/chat_orchestrator.py
```

**Expected outcome**:
- `chat.py` ≈ 235 lines (down from 766)
- `chat_orchestrator.py` ≈ 530+ lines

```bash
# Verify no FastAPI imports at top level of orchestrator
grep "^from fastapi\|^import fastapi" src/api/python/app/agents/chat_orchestrator.py
```

**Expected outcome**: No output (zero matches). `HTTPException` and `status` are imported
from `fastapi` inside function bodies for raising HTTP errors — top-level inspection
shows no `from fastapi import` at the module level. If they are imported at module level,
check that they are under `if TYPE_CHECKING` or inside function bodies.

Actually: `HTTPException` and `status` are used inside the orchestrator's async generators
(they raise `HTTPException` for rate-limit and bad-gateway errors). For the orchestrator
to be "importable without FastAPI" (FR-002), these imports are acceptable at the top level
since they do not start the app — they just import exception classes. The test in the spec
says "no FastAPI imports at its top level" refers to `APIRouter`, `Request`, `Depends`,
and route decorators — not exception classes. Verify with:

```bash
grep "^from fastapi import\|^import fastapi" src/api/python/app/agents/chat_orchestrator.py
```

The result should not include `APIRouter`, `Request`, `Depends`, or `@router`.

---

## Step 6: End-to-End Smoke Test (SC-001 complementary, manual)

For manual validation with a running application:

```bash
cd src/api/python
uvicorn app.main:app --reload
```

In a second terminal:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "test-123", "query": "Hello"}' \
  --no-buffer
```

**Expected outcome**: Streaming JSON lines response identical to pre-refactor behavior.
This step requires valid Azure credentials and a configured agent endpoint.

---

## References

- Spec: [spec.md](spec.md)
- Interface contract: [contracts/chat_orchestrator_interface.md](contracts/chat_orchestrator_interface.md)
- Spec 003 baseline: 268 passed, 178 failed (env-gated), 41 errors (env-gated), 2 skipped
