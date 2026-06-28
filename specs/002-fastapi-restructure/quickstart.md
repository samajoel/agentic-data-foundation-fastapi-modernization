# Quickstart Validation Guide: FastAPI Service Restructuring

**Feature**: 002-fastapi-restructure
**Date**: 2026-06-28

This guide documents how to validate that the restructuring is complete and correct.
All steps use the existing tooling — no new tools are introduced.

---

## Prerequisites

- Python virtual environment at `src/api/python/.venv` (created by `start.sh` or manually)
- `src/api/python/requirements.txt` installed in the virtual environment
- Working directory: repository root unless noted otherwise

---

## Step 1: Verify Package Structure

Confirm the new package structure exists and original flat modules are removed:

```bash
# New package exists
ls src/api/python/app/
# Expected: __init__.py  api/  core/  services/  agents/  data/  main.py

# All layer directories exist
ls src/api/python/app/api/routers/
# Expected: __init__.py  chat.py  history.py  history_sql.py

ls src/api/python/app/core/
# Expected: __init__.py  auth/  logging.py  middleware.py

ls src/api/python/app/core/auth/
# Expected: __init__.py  auth_utils.py  azure_credential_utils.py  sample_user.py

# Placeholder layers exist
ls src/api/python/app/services/ src/api/python/app/agents/ src/api/python/app/data/
# Expected: each contains only __init__.py

# Original flat modules are gone
ls src/api/python/chat.py src/api/python/history.py src/api/python/history_sql.py 2>&1
# Expected: No such file or directory

ls src/api/python/auth/ 2>&1
# Expected: No such file or directory

# Compatibility shim exists
ls src/api/python/app.py
# Expected: the file exists
```

---

## Step 2: Run the Automated Test Suite

This is the primary regression gate. The test count must equal or exceed the pre-restructuring
baseline (90 tests passing as of Spec 001 completion).

```bash
# From repository root
cd src/api/python && source .venv/bin/activate && cd -

.venv/bin/pytest -m unittest \
  src/test/api/python/ \
  --ignore=src/test/api/python/e2e-test \
  -v

# Expected: All tests pass; zero new failures; count >= 90
```

Alternatively, use the virtualenv under `src/api/python/`:

```bash
src/api/python/.venv/bin/pytest -m unittest \
  src/test/api/python/ \
  --ignore=src/test/api/python/e2e-test \
  -v
```

---

## Step 3: Linting — Zero New Violations

```bash
src/api/python/.venv/bin/flake8 src/api/python/app/ src/api/python/app.py

# Expected: No output (zero violations)
```

Also verify the existing flake8 scope passes cleanly:

```bash
src/api/python/.venv/bin/flake8 src/api/python/
# Expected: zero violations (or only pre-existing ones documented before restructuring)
```

---

## Step 4: Python Import Sanity Check

Confirm the key import paths resolve without errors (requires the venv to be active):

```bash
cd src/api/python

# App package and main module
.venv/bin/python -c "from app.main import build_app, app; print('app.main OK')"

# Compatibility shim (via package __init__.py)
.venv/bin/python -c "from app import build_app, app; print('app.__init__ re-export OK')"

# Router modules
.venv/bin/python -c "from app.api.routers import chat, history, history_sql; print('routers OK')"

# Core auth
.venv/bin/python -c "from app.core.auth import auth_utils; print('core.auth OK')"

# Placeholders
.venv/bin/python -c "from app import services, agents, data; print('placeholders OK')"
```

All commands must print their success message with no import errors.

---

## Step 5: Startup Path Validation

**Requires**: A configured `.env` file with valid Azure credentials (Azure dev environment).
If not available, this step is environment-gated (same constraint as Spec 001 T020-T023).

```bash
cd src/api/python

# Method A — documented startup command
.venv/bin/python app.py
# or: python app.py
# Expected: uvicorn starts on port 8000; no startup errors

# Method B — uvicorn direct (matches Dockerfile CMD)
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
# Expected: starts; log shows four route registrations (/api, /history, /historyfab, /health)
```

---

## Step 6: API Smoke Tests (environment-gated)

When the backend is running (Step 5), verify the four API surface areas:

```bash
# Health check — always runs
curl http://127.0.0.1:8000/health
# Expected: {"status":"healthy"}

# Chat endpoint (requires Azure AI Foundry credential)
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test-001","messages":[{"role":"user","content":"Hello"}]}'
# Expected: streaming response (no 404, 500, or connection error)

# History list (requires Cosmos DB credential)
curl "http://127.0.0.1:8000/history/list?user_id=test-user&limit=5"
# Expected: JSON response (no 404 or 500)

# History Fabric list (requires Fabric SQL credential)
curl "http://127.0.0.1:8000/historyfab/list?user_id=test-user&limit=5"
# Expected: JSON response (no 404 or 500)
```

For the full route inventory, see
[`specs/001-single-backend-consolidation/contracts/api-contract.md`](../../001-single-backend-consolidation/contracts/api-contract.md).

---

## Step 7: Frontend Validation

No frontend changes are required or expected. Confirm by checking for any modification
to `src/App/`:

```bash
git diff --name-only HEAD src/App/
# Expected: no output (zero frontend files changed)
```

---

## Success Criteria Mapping

| Quickstart step | Spec success criterion |
|-----------------|----------------------|
| Step 1 (structure) | SC-006 (layer discoverability) |
| Step 2 (tests) | SC-001 (no test regressions) |
| Step 3 (linting) | SC-005 (zero new violations) |
| Step 4 (imports) | SC-003 (startup path works) |
| Step 5 (startup) | SC-003 (startup path works) |
| Step 6 (smoke tests) | SC-002 (API contract preserved) |
| Step 7 (frontend diff) | SC-004 (zero frontend changes) |
