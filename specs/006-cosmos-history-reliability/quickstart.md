# Quickstart: Cosmos DB Chat History Reliability

**Feature**: Cosmos DB Chat History Reliability Fixes
**Date**: 2026-08-07

This guide documents runnable validation scenarios that prove the three bug fixes work correctly. All scenarios use the existing pytest suite; no live Azure resources are required.

---

## Prerequisites

- Python virtual environment at `.venv/` (repo root)
- `cd` to repo root before running any commands
- No Azure credentials required for validation

---

## Validation Scenarios

### V-001 — Test baseline (before making any changes)

Record the starting counts so you can confirm no regressions after the fixes:

```bash
.venv/bin/pytest src/test/api/python/ -q --tb=no
# Record: X passed, Y failed, Z errors
```

---

### V-002 — Confirm Bug 1 location

Verify the ownership field mismatch exists in the current code:

```bash
grep -n "conversation\[.user_id.\]" src/api/python/app/api/routers/history.py
# Expected: line 433 contains conversation["user_id"] != user_id
```

Verify the correct field name in the Cosmos document write:

```bash
grep -n '"userId"' src/api/python/app/data/cosmos_history.py | head -5
# Expected: lines writing "userId": user_id into the document dict
```

---

### V-003 — Confirm Bug 2 location

Verify the mutable default argument exists in the current code:

```bash
grep -n "conversation_id=str(uuid" src/api/python/app/data/cosmos_history.py
# Expected: line 93 — conversation_id=str(uuid.uuid4()) as a default argument
```

---

### V-004 — Confirm Bug 3 location

Verify the duplicate assignment exists:

```bash
grep -n 'messages = request_json\["messages"\]' src/api/python/app/api/routers/history.py
# Expected: two matches at lines 161 and 188
```

---

### V-005 — Run clear-messages tests (Bug 1)

After applying the Fix 1 code change and updating the mock:

```bash
.venv/bin/pytest src/test/api/python/test_history.py -k "clear_messages" -v
# Expected: all clear_messages tests pass, including:
#   - test_clear_messages_success (mock updated to use "userId")
#   - test_clear_messages_rejects_different_user (new regression test)
#   - test_clear_messages_disabled
#   - test_clear_messages_exception
```

---

### V-006 — Run create-conversation tests (Bug 2)

After applying the Fix 2 code change:

```bash
.venv/bin/pytest src/test/api/python/test_history.py -k "create_conversation" -v
# Expected: all create_conversation tests pass, including:
#   - test_create_conversation (existing — explicit ID path)
#   - test_create_conversation_fails (existing)
#   - test_create_conversation_generates_unique_ids (new regression test)
```

---

### V-007 — Run update-conversation tests (Bug 3)

After applying the Fix 3 code change:

```bash
.venv/bin/pytest src/test/api/python/test_history.py -k "update_conversation" -v
# Expected: all update_conversation tests pass, including:
#   - test_update_conversation_success
#   - test_update_conversation_no_assistant
#   - test_update_conversation_creates_new
```

---

### V-008 — Full test suite (regression check)

After all three fixes:

```bash
.venv/bin/pytest src/test/api/python/ -q --tb=short
# Expected:
#   - Passing count ≥ baseline from V-001 (plus new regression tests)
#   - No previously passing test newly failing
#   - The two new regression tests added in T004 now pass
```

---

### V-009 — Lint check

```bash
.venv/bin/flake8 src/api/python/app/
# Expected: exit code 0, no output
```

---

### V-010 — Verify field name consistency after Fix 1

Confirm no remaining snake_case `user_id` field lookups on Cosmos documents in history.py:

```bash
grep -n "conversation\[.user_id.\]" src/api/python/app/api/routers/history.py
# Expected: no output (zero matches)
```

---

### V-011 — Verify Bug 2 fix

Confirm the None sentinel pattern is in place:

```bash
grep -n "conversation_id=None\|if conversation_id is None" src/api/python/app/data/cosmos_history.py
# Expected: two lines — the None default and the in-body guard
```

---

### V-012 — Verify Bug 3 fix

Confirm the duplicate assignments are removed:

```bash
grep -n 'messages = request_json\["messages"\]' src/api/python/app/api/routers/history.py
# Expected: no output (zero matches — only the safe .get() assignment at line 146 remains)
```

---

## Security Notes

- No credentials are introduced by these fixes.
- The ownership validation fix (`userId` field name correction) strengthens security by ensuring the authorization check is actually evaluated.
- All Azure resource access continues to use `DefaultAzureCredential` via the existing `get_azure_credential_async()` pattern (Constitution Principle VI).
