# Research: Cosmos DB Chat History Reliability

**Date**: 2026-08-07
**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

All findings were derived by direct code inspection of the two affected files. No live Azure resources or external research were required. No NEEDS CLARIFICATION items existed in the spec.

---

## Decision 1: Field name for Cosmos ownership check

**Decision**: Change `conversation["user_id"]` to `conversation["userId"]` at `history.py:433`.

**Rationale**: Cosmos DB documents are written by `create_conversation()` in `cosmos_history.py:96–104` using the key `"userId"` (camelCase). The `get_conversation()` query at line 166 retrieves exactly those documents. All other field access in `clear_messages()` and throughout `history.py` uses `"userId"`. The check at line 433 is the only site that uses `"user_id"` (snake_case) — this is a typo/copy-paste error.

**Confirmation**: Line 101 of `cosmos_history.py` writes `"userId": user_id` into the document. Line 147 queries `c.userId = @userId`. Line 283 of `history.py` checks `conversation["userId"]` in a parallel delete path. Line 433 is the only exception.

**Alternatives considered**:
- Rename `"userId"` to `"user_id"` throughout storage: Rejected — would require data migration for all existing Cosmos records and would break all other field accesses that use `"userId"`.
- Add a compatibility shim that checks both keys: Rejected — unnecessary complexity; the correct key is unambiguous from the storage write path.

---

## Decision 2: Mutable default argument fix strategy

**Decision**: Replace `conversation_id=str(uuid.uuid4())` with `conversation_id=None` and generate the UUID inside the function body.

**Rationale**: Python evaluates default argument expressions at function definition time (class load time for methods). All calls that omit `conversation_id` receive the same UUID that was generated when the class was first imported. The idiomatic fix is `None` as sentinel + in-body generation.

**Confirmation**: All production call sites in `history.py` pass an explicit `conversation_id` (line 154: `conversation_id=conversation_id`). The fallback path is never exercised in practice today, making this a latent defect rather than an active incident. The existing test at `test_history.py:267` always passes `"conv123"` explicitly.

**Alternatives considered**:
- Use a `uuid.uuid4` callable as the default (e.g., `conversation_id=uuid.uuid4`): Rejected — this would pass the callable itself as the default, not a UUID string, requiring a call inside the function anyway. The `None` sentinel is cleaner and the standard Python idiom.
- Leave the default as-is and document it: Rejected — leaving a known defect undocumented and unfixed violates Constitution Principle V.

---

## Decision 3: Duplicate assignment removal strategy

**Decision**: Remove the two redundant assignments at `history.py:161` and `history.py:188`. The assignment at line 146 (`messages = request_json.get("messages", [])`) is retained as the single authoritative source.

**Rationale**: Lines 161 and 188 both perform `messages = request_json["messages"]`, which re-reads the same key from the same dict without adding a safety default. When the key exists, the value is identical to what line 146 already assigned. When the key is absent, line 146's `.get()` safely returns `[]` while lines 161 and 188 would raise `KeyError`. Removing lines 161 and 188 makes the code unambiguous and safer.

**Confirmation**: The variable `messages` is used after line 188 at line 189 (`messages[-1]["role"]`) and at line 190 (`messages[-2]`). Both usages receive the same value regardless of which assignment is in effect, since all three assignments read from `request_json["messages"]` when the key is present.

**Alternatives considered**:
- Keep line 146 as a comment-only annotation and use lines 161/188 as the primary: Rejected — this would remove the safe `.get()` default without benefit.
- Replace all three with a single assignment at the top of the function: Not needed — line 146 is already at the top of the logical flow; lines 161 and 188 are the ones that need removal.

---

## Decision 4: Test update scope

**Decision**: Update the mock in `test_clear_messages_success` from `{"user_id": "user123"}` to `{"userId": "user123"}`, and add two new regression tests: one for the ownership rejection path and one for the fallback ID uniqueness guarantee.

**Rationale**: The existing `test_clear_messages_success` at `test_history.py:947` was written to match the bug — it passes `"user_id"` in the mock so that the broken check happens to succeed. After the fix, the mock must reflect the real Cosmos document shape (`"userId"`). Without updating the mock, the test would start failing after the fix — not because the fix is wrong but because the test was coded around the bug.

**Confirmation**: The note in the test at line 946 says: `# Note: code checks conversation["user_id"] not conversation["userId"]` — explicitly acknowledging the mismatch. This confirms the test was knowingly adapted to the broken behavior.

**Alternatives considered**:
- Leave the existing test as-is and only fix the code: Rejected — the existing test would fail after the fix and would misrepresent what the code does.
- Delete the existing test and rewrite from scratch: Rejected — the test structure is fine; only the mock field name needs updating.
