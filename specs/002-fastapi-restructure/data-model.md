# Data Model: FastAPI Service Restructuring

**Feature**: 002-fastapi-restructure
**Date**: 2026-06-28

This spec introduces no new data entities, database schemas, or persistence changes.
The "entities" in this restructuring are the source modules and packages that move or are
created. This document serves as the authoritative module movement map.

---

## Module Movement Map

### Files Moved (content unchanged except import path updates)

| Source path | Target path | Import changes inside the file |
|-------------|-------------|-------------------------------|
| `src/api/python/chat.py` | `src/api/python/app/api/routers/chat.py` | `from auth.auth_utils import …` → `from app.core.auth.auth_utils import …`; `from auth.azure_credential_utils import …` → `from app.core.auth.azure_credential_utils import …` |
| `src/api/python/history.py` | `src/api/python/app/api/routers/history.py` | Same auth import updates as above |
| `src/api/python/history_sql.py` | `src/api/python/app/api/routers/history_sql.py` | Same auth import updates as above |
| `src/api/python/auth/auth_utils.py` | `src/api/python/app/core/auth/auth_utils.py` | None — relative imports (`from . import sample_user`) continue to work unchanged |
| `src/api/python/auth/azure_credential_utils.py` | `src/api/python/app/core/auth/azure_credential_utils.py` | None |
| `src/api/python/auth/sample_user.py` | `src/api/python/app/core/auth/sample_user.py` | None |

### Content Extracted from `app.py` into New Files

| Content | Extracted to | Notes |
|---------|-------------|-------|
| `conversation_id_var`, `user_id_var` ContextVars | `app/core/logging.py` | Used by log record factory and middleware |
| `_configure_logging()` function + call | `app/core/logging.py` as `configure_logging()` | Call moves to top of `app/main.py` |
| `attach_trace_attributes` middleware | `app/core/middleware.py` as `attach_trace_attributes(request, call_next)` | Imports context vars from `app.core.logging` |
| `build_app()`, CORS, router includes, health endpoint | `app/main.py` | Imports middleware from `app.core.middleware`, routers from `app.api.routers.*` |
| `app = build_app()`, `FastAPIInstrumentor.instrument_app(…)` | `app/main.py` (module-level) | |
| `if __name__ == "__main__": uvicorn.run(…)` | Stays in `app.py` shim | |

### Files Modified in Place

| File | Change |
|------|--------|
| `src/api/python/app.py` | Replace full content with shim: `from app.main import app, build_app` + uvicorn `__main__` block |

### New Files Created

| File | Purpose |
|------|---------|
| `src/api/python/app/__init__.py` | Re-exports `app`, `build_app` from `app.main` — makes `uvicorn app:app` resolve correctly |
| `src/api/python/app/main.py` | Canonical application initializer |
| `src/api/python/app/api/__init__.py` | Package marker |
| `src/api/python/app/api/routers/__init__.py` | Package marker |
| `src/api/python/app/core/__init__.py` | Package marker |
| `src/api/python/app/core/logging.py` | Logging configuration + context vars |
| `src/api/python/app/core/middleware.py` | `attach_trace_attributes` middleware |
| `src/api/python/app/core/auth/__init__.py` | Package marker |
| `src/api/python/app/services/__init__.py` | Placeholder — empty |
| `src/api/python/app/agents/__init__.py` | Placeholder — empty |
| `src/api/python/app/data/__init__.py` | Placeholder — empty |

### Files Deleted

| File | Reason |
|------|--------|
| `src/api/python/chat.py` | Moved to `app/api/routers/chat.py` |
| `src/api/python/history.py` | Moved to `app/api/routers/history.py` |
| `src/api/python/history_sql.py` | Moved to `app/api/routers/history_sql.py` |
| `src/api/python/auth/auth_utils.py` | Moved to `app/core/auth/auth_utils.py` |
| `src/api/python/auth/azure_credential_utils.py` | Moved to `app/core/auth/azure_credential_utils.py` |
| `src/api/python/auth/sample_user.py` | Moved to `app/core/auth/sample_user.py` |
| `src/api/python/auth/` (directory) | Empty after files moved |

---

## Test File Import Changes

### `src/test/api/python/conftest.py`

| Before | After |
|--------|-------|
| `sys.modules['chat'] = MagicMock()` | `sys.modules['app.api.routers.chat'] = MagicMock()` |
| `sys.modules['history'] = MagicMock()` | `sys.modules['app.api.routers.history'] = MagicMock()` |
| `sys.modules['history_sql'] = MagicMock()` | `sys.modules['app.api.routers.history_sql'] = MagicMock()` |
| `sys.modules['chat'].router = …` | `sys.modules['app.api.routers.chat'].router = …` |
| `sys.modules['history'].router = …` | `sys.modules['app.api.routers.history'].router = …` |
| `sys.modules['history_sql'].router = …` | `sys.modules['app.api.routers.history_sql'].router = …` |

The `should_mock_modules()` and `setup_test_environment()` fixtures also reference these
keys and must be updated consistently.

### `src/test/api/python/test_app.py`

No import changes needed. `from app import build_app` resolves through `app/__init__.py`
which re-exports `build_app` from `app.main`.

### `src/test/api/python/test_chat.py`

All `from chat import …` statements → `from app.api.routers.chat import …`

### `src/test/api/python/test_history.py`

All `import history` / `from history import …` → `from app.api.routers import history` /
`from app.api.routers.history import …`

### `src/test/api/python/test_history_sql.py`

All `import history_sql` / `from history_sql import …` → `from app.api.routers import history_sql` /
`from app.api.routers.history_sql import …`. Any `importlib`-based dynamic imports must
update the module path string accordingly (e.g., `importlib.import_module('app.api.routers.history_sql')`).

### `src/test/api/python/test_logging_middleware.py`

`from app import build_app` — no change; resolves via `app/__init__.py`.

### `src/test/api/python/auth/test_auth_utils.py`

`from auth.auth_utils import …` → `from app.core.auth.auth_utils import …`

### `src/test/api/python/auth/test_azure_credential_utils.py`

`from auth.azure_credential_utils import …` → `from app.core.auth.azure_credential_utils import …`

### `src/test/api/python/auth/test_sample_user.py`

`from auth.sample_user import …` → `from app.core.auth.sample_user import …`

---

## Layer Architecture (post-restructuring)

```text
app/
├── api/         routing   — FastAPI routers, request/response handling
├── core/        shared    — logging, middleware, auth utilities, config
├── services/    (placeholder) — business logic (future spec)
├── agents/      (placeholder) — agent framework interaction (future spec)
└── data/        (placeholder) — data access (Fabric SQL, Cosmos DB) (future spec)
```

Principle VIII compliance path: once a subsequent spec populates `app/data/`, the data
access code currently embedded in `chat.py`, `history.py`, and `history_sql.py` will
move there, completing the layered architecture.
