# Research: Agent Orchestration Layer Extraction

**Feature**: Spec 004
**Date**: 2026-06-28
**Status**: Complete — no open unknowns; all decisions derived from existing codebase

This spec is a brownfield structural refactor with no new algorithms, dependency
introductions, or architectural patterns to research. All technical decisions are
fully determined by the existing code and the spec constraints. This document records
the key decisions and rationale for implementation guidance.

---

## Decision 1: Single orchestrator module vs. multiple files

**Decision**: Extract all orchestration logic into a single `app/agents/chat_orchestrator.py`.

**Rationale**: The orchestration code is tightly coupled — `stream_chat_request` dispatches
to `stream_openai_text` or `stream_openai_text_workshop`; both use the same `ExpCache`,
`get_thread_cache`, and `track_event_if_configured`. Splitting across multiple files would
require cross-imports within `app/agents/` without a clear cohesion boundary. A single
module is the minimal change that achieves the spec's structural goal.

**Alternatives considered**:
- Multiple files (`stream_standard.py`, `stream_workshop.py`, `cache.py`, `telemetry.py`):
  rejected — premature decomposition for a first extraction pass; no user story requires it
- Thin wrapper approach (add `app/agents/chat_orchestrator.py` that re-exports functions
  from `chat.py`): rejected — would not reduce `chat.py` or satisfy US2

---

## Decision 2: `HOST_NAME` and `HOST_INSTRUCTIONS` stay in `chat.py`

**Decision**: Do not move `HOST_NAME` and `HOST_INSTRUCTIONS` to `chat_orchestrator.py`.

**Rationale**: These constants are defined but not referenced in any function body in
`chat.py`. They appear to be vestigial application-level config. Moving them would require
updating test imports that verify module-level constants (`test_constants_defined`,
`test_module_imports_successfully`), adding churn for no functional benefit. Keeping them
in `chat.py` satisfies the "minimal change" constraint.

**Alternatives considered**:
- Move to `chat_orchestrator.py` (agent config): rejected — constants are not referenced by
  any extracted function, so the move is gratuitous
- Move to `app/core/config.py`: out of scope for this spec

---

## Decision 3: `track_event_if_configured` moves with the orchestrator

**Decision**: Move `track_event_if_configured` to `chat_orchestrator.py`. The `chat.py`
router re-imports it for the three calls in the `conversation` route handler.

**Rationale**: The function is called 8 times within the extracted orchestration code
(in `stream_openai_text` and `stream_openai_text_workshop`) and only 3 times in the route
handler. Its primary home is the orchestrator. Re-exporting it via chat.py's namespace
(`from app.agents.chat_orchestrator import track_event_if_configured`) means the three
route-level patches (`app.api.routers.chat.track_event_if_configured`) remain valid without
test changes.

**Alternatives considered**:
- Move to `app/core/telemetry.py`: would be architecturally cleaner but is an
  observability-layer change explicitly out of scope for this spec
- Duplicate the function in both modules: rejected — violates DRY, maintenance risk

---

## Decision 4: Patch target migration rule (Spec 003 precedent)

**Decision**: When a symbol moves from `app.api.routers.chat` to
`app.agents.chat_orchestrator`, patch targets in tests follow the symbol to its new home
if the function that uses it is now defined in the orchestrator. Symbols re-imported into
`chat.py` by name are patchable at both locations; prefer the router namespace for patches
that test route handler behavior, orchestrator namespace for patches that test orchestration
behavior.

**Rationale**: `unittest.mock.patch` intercepts the name in the namespace where it is
looked up at runtime. After the move, `stream_openai_text` is looked up in the orchestrator
module (where it is defined). If tests patch `app.api.routers.chat.stream_openai_text` but
the code running is in `app.agents.chat_orchestrator`, the patch is in the wrong namespace
and has no effect.

This is the same rule applied in Spec 003 for `get_fabric_db_connection` and
`get_db_connection`.

---

## Decision 5: `load_dotenv()` moves to `chat_orchestrator.py`

**Decision**: The `load_dotenv()` call at module level in `chat.py` moves to
`chat_orchestrator.py`.

**Rationale**: All environment variables loaded by `load_dotenv()` are consumed by the
orchestration code (agent endpoint, agent name, workshop flags, etc.). The orchestrator
module is imported at application startup (via chat.py importing it), so `load_dotenv()`
fires before any requests are processed — same timing as before.

---

## Decision 6: `agent_framework_foundry` log level config moves with the orchestrator

**Decision**: The `logging.getLogger("agent_framework_foundry").setLevel(...)` line moves
to `chat_orchestrator.py`.

**Rationale**: This configuration is specific to the agent framework behavior and belongs
with the code that uses FoundryAgent. Moving it does not alter the log level at runtime
since the module is imported before requests arrive.

---

## Decision 7: `app/agents/__init__.py` remains empty

**Decision**: `app/agents/__init__.py` stays as an empty package marker.

**Rationale**: FR-009 requires it to not eagerly import symbols that trigger I/O. An empty
`__init__.py` is the safest approach and requires no changes. The orchestrator is imported
explicitly by callers.

---

## Non-Issues (documented for completeness)

- **Circular imports**: No circular import risk. `chat_orchestrator.py` imports from
  `app/data/` and `app/core/`; `chat.py` imports from `chat_orchestrator.py`. No cycle.

- **Streaming generator interface compatibility**: `stream_openai_text` yields `str` chunks;
  `stream_openai_text_workshop` yields `(str, str)` tuples. These types are unchanged after
  extraction. `stream_chat_request` adapts them to JSON lines format — unchanged.

- **Thread cache state**: `thread_cache` is a module-level global in `chat_orchestrator.py`
  after the move. Since Python caches module objects after first import, the global state
  is shared across all requests exactly as before.
