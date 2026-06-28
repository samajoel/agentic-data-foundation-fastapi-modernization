# Research: FastAPI Service Restructuring

**Feature**: 002-fastapi-restructure
**Date**: 2026-06-28
**Status**: Complete — no NEEDS CLARIFICATION items remain

---

## Decision 1: Python Package vs Module Naming — `app/` and `app.py` Coexistence

**Decision**: Keep both `app.py` (shim) and the `app/` package in `src/api/python/`. Add
`app/__init__.py` that re-exports `app` and `build_app` from `app.main`.

**Rationale**: Python 3 resolves `import app` by finding the `app/` regular package (a
directory with `__init__.py`) before `app.py` when both exist in the same directory.
This means:

- `uvicorn app:app` does `import app` → gets `app/` package → finds `app` attribute in
  `app/__init__.py` (which imports it from `app.main`) ✓
- `python app.py` executes `app.py` as `__main__`; `app/` package does not interfere with
  direct script execution ✓
- Inside `app.py`, `from app.main import app, build_app` imports from `app/main.py` because
  the interpreter finds the `app/` package for the `app.` prefix ✓

This design satisfies FR-003 (compatibility entrypoint preserved) and FR-007 (no changes to
Dockerfile or start scripts) without compromise.

**Alternatives considered**:
- Rename `app.py` shim to `server.py` — rejected: breaks `python app.py` documented startup
  and `uvicorn app:app` Dockerfile CMD, both prohibited by FR-003 and FR-007.
- Use `app/` package only, with `app/__init__.py` as the sole entrypoint — rejected: makes
  `python app.py` fail (no `app.py` file to run directly), breaking the documented startup.
- Rename the new package to `backend/` — rejected: the spec explicitly names the package `app/`
  and the constitution targets a layered package structure under `app/`.

---

## Decision 2: Content Split from `app.py` into `app/main.py` and `app/core/`

**Decision**:

| Content | Current location | New location |
|---------|-----------------|-------------|
| `_configure_logging()`, `conversation_id_var`, `user_id_var` | `app.py` top level | `app/core/logging.py` |
| `attach_trace_attributes` middleware | inline in `build_app()` in `app.py` | `app/core/middleware.py` |
| `build_app()`, CORS, router registration, health endpoint, `app = build_app()`, `FastAPIInstrumentor` | `app.py` | `app/main.py` |
| `if __name__ == "__main__": uvicorn.run(...)` | `app.py` | Stays in `app.py` shim |
| `app = build_app()` (module-level) | `app.py` | `app/main.py` AND re-exported via `app/__init__.py` |

**Rationale**: The split follows the constitution's core layer definition (configuration,
middleware, logging) and separates the application initializer (`main.py`) from utilities
(`core/`). The middleware depends on `conversation_id_var` and `user_id_var`, so both live
in `app/core/logging.py` to avoid a secondary import dependency.

**Alternatives considered**:
- Keep all content in `app/main.py` (no `core/` split) — rejected: contradicts FR-002
  which defines `app/core/` as the location for shared middleware and logging setup.
- Create a separate `app/core/context.py` for context vars — rejected: adds a file purely
  for two `ContextVar` objects that are already tightly coupled to the logging record factory;
  keeping them in `logging.py` avoids a needless cross-module dependency.

---

## Decision 3: `auth/` Package Move to `app/core/auth/`

**Decision**: Move `auth/auth_utils.py`, `auth/azure_credential_utils.py`, and
`auth/sample_user.py` as complete units to `app/core/auth/`. Update all import references
in router modules and test files from `auth.*` → `app.core.auth.*`.

**Rationale**: `auth/` is shared utility code (used by all three router modules) and belongs
in the core layer per FR-002. Moving it as-is preserves all behavior. All three router
modules import from `auth.auth_utils` and `auth.azure_credential_utils`; these imports are
updated in the moved files (now `app/api/routers/*.py`) to `app.core.auth.*`.

**Note on relative imports**: The auth package uses one relative import internally
(`from . import sample_user` in `auth_utils.py`). After moving to `app/core/auth/`, this
relative import continues to work unchanged because the relative package structure is preserved.

**Alternatives considered**:
- Keep `auth/` at the flat `src/api/python/auth/` level (not inside `app/`) — rejected:
  this would mean shared utilities live outside the `app/` package boundary, creating an
  inconsistent package structure and leaving an `auth/` directory alongside the new `app/`
  package.

---

## Decision 4: Router Module Import Updates

**Decision**: Update intra-module imports in the moved router files:
- `from auth.auth_utils import ...` → `from app.core.auth.auth_utils import ...`
- `from auth.azure_credential_utils import ...` → `from app.core.auth.azure_credential_utils import ...`

No other logic changes are made inside the router modules.

**Rationale**: When `chat.py`, `history.py`, and `history_sql.py` move to
`app/api/routers/`, their existing imports `from auth.*` would break because `auth/` no
longer exists at the top level of `src/api/python/`. Updating these imports to the new
`app.core.auth.*` path restores them. This is the minimum change required.

**Alternatives considered**:
- Keep `auth/` at the flat level as a shim that re-exports from `app/core/auth/` — rejected:
  Clarification Q3 explicitly decided against shim files at original paths.

---

## Decision 5: Test Import Update Strategy

**Decision**: Update all test file imports mechanically:

| Test file | Import before | Import after |
|-----------|--------------|-------------|
| `conftest.py` | `sys.modules['chat']`, `['history']`, `['history_sql']` | `sys.modules['app.api.routers.chat']`, `['app.api.routers.history']`, `['app.api.routers.history_sql']` |
| `test_app.py` | `from app import build_app` | **No change** — `app/__init__.py` re-exports `build_app` |
| `test_chat.py` | `from chat import …` | `from app.api.routers.chat import …` |
| `test_history.py` | `from history import …` | `from app.api.routers.history import …` |
| `test_history_sql.py` | `from history_sql import …` | `from app.api.routers.history_sql import …` |
| `test_logging_middleware.py` | `from app import build_app` | **No change** — resolves via `app/__init__.py` |
| `auth/test_auth_utils.py` | `from auth.auth_utils import …` | `from app.core.auth.auth_utils import …` |
| `auth/test_azure_credential_utils.py` | `from auth.azure_credential_utils import …` | `from app.core.auth.azure_credential_utils import …` |
| `auth/test_sample_user.py` | `from auth.sample_user import …` | `from app.core.auth.sample_user import …` |

No test logic (assertions, fixtures, mocked behavior) changes in any file.

**Rationale**: FR-004 and Clarification Q3 mandate updating all import references; no shim
files at original paths. The `conftest.py` sys.modules mock keys must match the paths
`app/main.py` uses to import the routers — otherwise the mock won't intercept the import.

---

## Decision 6: `pytest.ini` `pythonpath` — No Change Required

**Decision**: `pythonpath = ./src/api/python` requires no modification.

**Rationale**: With `src/api/python` on `sys.path`:
- `import app` → `app/` package at `src/api/python/app/` ✓
- `from app.main import …` → `src/api/python/app/main.py` ✓
- `from app.api.routers.chat import …` → `src/api/python/app/api/routers/chat.py` ✓
- `from app.core.auth.auth_utils import …` → `src/api/python/app/core/auth/auth_utils.py` ✓

The existing `pythonpath` setting continues to be the only path needed.

---

## Decision 7: `__init__.py` Content for Placeholder Layers

**Decision**: `app/services/__init__.py`, `app/agents/__init__.py`, and `app/data/__init__.py`
are empty files (no content).

**Rationale**: These are structural placeholders only. No import re-exports are needed until
a subsequent spec populates each layer. An empty `__init__.py` is sufficient to make the
directory a Python package and make it discoverable.

---

## Deferred Topics

These were identified as lower-priority during clarification and are appropriately handled
by subsequent specs:

- **Intra-module concern separation** (extracting service/agent/data logic from router
  modules) — deferred to Spec 003.
- **Circular import risk audit** — will surface during implementation; resolution strategy
  is to adjust import order or use lazy imports within the moved module if needed.
- **OpenTelemetry FastAPIInstrumentor placement** — kept in `app/main.py` post-`build_app()`
  call; moving it to core is deferred (scope creep for this spec).
