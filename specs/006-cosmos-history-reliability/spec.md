# Feature Specification: Cosmos DB Chat History Reliability

**Feature Branch**: `006-cosmos-history-reliability`

**Created**: 2026-08-07

**Status**: Draft

**Input**: User description — Fix three identified reliability defects in the Cosmos DB chat history layer: broken conversation ownership validation, non-unique fallback identifier generation, and redundant message-list assignment in the history update flow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Conversation Message Clearing Works Correctly (Priority: P1)

A user who wants to clear all messages from one of their conversations expects that action to succeed. Currently, the ownership check that guards the clear-messages operation silently fails every time because the field name used to look up the owner in the stored record does not match the field name the data store actually uses. The result is that the clear-messages call always refuses to proceed, leaving the user unable to clear their conversation history.

**Why this priority**: This is a functional regression — a user-visible operation is completely broken in workshop mode. Fixing it restores expected behavior with no interface or protocol changes.

**Independent Test**: As an authenticated user, call the clear-messages endpoint for a conversation that belongs to that user. Confirm the operation succeeds and the messages are removed. Confirm that calling the same endpoint for a conversation that belongs to a different user correctly refuses the request.

**Acceptance Scenarios**:

1. **Given** an authenticated user and a conversation they own, **When** the user requests that all messages in that conversation be cleared, **Then** the request succeeds and no messages remain in that conversation.
2. **Given** an authenticated user and a conversation owned by a different user, **When** the user attempts to clear that conversation's messages, **Then** the request is rejected with an authorization failure and no messages are removed.
3. **Given** an authenticated user, **When** the clear-messages operation runs, **Then** the ownership check uses the same field name that the data store contains — no mismatch between the stored field and the lookup field.

---

### User Story 2 — Conversation IDs Are Always Unique (Priority: P2)

When a conversation record is created without a caller-supplied identifier, the system is expected to assign a unique identifier to that record. A latent defect in the fallback identifier-generation path causes the same identifier to be reused across all calls that omit the identifier, rather than generating a fresh one each time.

**Why this priority**: Although the frontend always supplies an explicit identifier today, the fallback path is part of the public contract of the history client. A collision in that path would silently corrupt history data. The fix is low-risk and prevents a future data-integrity incident.

**Independent Test**: Invoke the conversation creation operation twice without providing an explicit identifier; confirm the two resulting records have distinct identifiers.

**Acceptance Scenarios**:

1. **Given** no caller-supplied identifier, **When** the conversation creation operation runs, **Then** the system assigns a unique identifier to the new record.
2. **Given** two calls to create a conversation without a caller-supplied identifier, **When** both calls complete, **Then** each resulting record has a different identifier.
3. **Given** a caller-supplied identifier, **When** the conversation creation operation runs, **Then** the caller-supplied identifier is used unchanged and the fallback logic is not invoked.

---

### User Story 3 — History Update Processes Messages Consistently (Priority: P3)

The operation that persists a completed chat turn reads the incoming message list from the request payload. Due to a duplicate assignment in the processing code, the message list variable is written twice from the same source. While this does not currently produce incorrect output, it is a latent defect that makes the code ambiguous — a future change to either assignment would silently diverge from the other.

**Why this priority**: This is a code-correctness and maintainability fix. The user-visible behavior is currently unaffected, making it lower priority than the functional bugs above. It is included in this spec to close all three identified reliability gaps in a single bounded change.

**Independent Test**: Submit a history update request with a set of messages; confirm the persisted conversation contains exactly the messages from the request with no duplicates, omissions, or ordering changes.

**Acceptance Scenarios**:

1. **Given** a history update request containing user and assistant messages, **When** the update is processed, **Then** all messages in the request are persisted to the conversation record in the correct order.
2. **Given** the history update processing code, **When** it is read, **Then** the message list is assigned exactly once from the request payload — there is no shadowing or duplicate assignment.

---

### Edge Cases

- What happens when `clear_messages` is called for a conversation that does not exist? The operation should return a not-found or no-op response without raising an unhandled error.
- What happens when the ownership check field is absent from the stored conversation record entirely? The operation should treat the record as unowned by the requesting user and reject the request.
- What happens when the fallback identifier generation is invoked concurrently? Each invocation must produce an independent, globally unique identifier regardless of timing.
- What happens to existing persisted conversation records after the ownership field fix? The fix must be backward-compatible — records already stored with the correct field name continue to work without migration.
- What happens to the SQL/Fabric history implementation? None of these changes touch the SQL history layer; its behavior is unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The clear-messages operation MUST validate conversation ownership using the field name that the Cosmos DB data store writes and returns — no discrepancy between the field name used for lookup and the field name present in stored records.
- **FR-002**: When conversation creation is invoked without a caller-supplied identifier, the system MUST generate a new unique identifier for each invocation — the same identifier MUST NOT be reused across multiple calls.
- **FR-003**: When conversation creation is invoked with a caller-supplied identifier, the system MUST use that identifier unchanged and MUST NOT invoke the fallback generation path.
- **FR-004**: The history update operation MUST derive the message list from the request payload exactly once, with no duplicate or shadowing assignments within the same execution path.
- **FR-005**: The ownership validation fix MUST be backward-compatible with all existing Cosmos DB conversation records — no data migration is required.
- **FR-006**: The SQL/Fabric history implementation MUST NOT be modified by any of these changes.
- **FR-007**: The existing conversation lifecycle MUST be preserved: frontend-generated conversation IDs are accepted, conversation records are upserted on first persist, and message records are created per turn.
- **FR-008**: The existing authentication and user identity flow MUST remain unchanged.

### Key Entities

- **Conversation Record**: A persisted record that groups a sequence of messages under a single identifier and associates them with an owner. The owner field name in the stored record and the field name used during ownership validation MUST be identical.
- **Conversation Message**: A single turn (user query or assistant response) within a conversation; belongs to one conversation and one owner.
- **Conversation Owner**: The authenticated user identity that created the conversation; used to authorize sensitive operations such as clearing messages.
- **Fallback Identifier**: The unique identifier assigned to a conversation record when the caller does not supply one; MUST be generated fresh on each invocation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can clear their own conversation messages with a 100% success rate (the operation no longer silently rejects all requests).
- **SC-002**: An attempt to clear another user's conversation messages is rejected 100% of the time (ownership enforcement is effective).
- **SC-003**: Two calls to create a conversation without a caller-supplied identifier produce records with distinct identifiers in 100% of cases.
- **SC-004**: The history update flow persists all messages from the request payload with no omissions or ordering changes across all observed test cases.
- **SC-005**: The existing test suite passes with no new failures; any tests previously failing due to the ownership field mismatch now pass.
- **SC-006**: The SQL/Fabric history test suite shows zero new failures or behavioral changes.

## Assumptions

- The Cosmos DB data store writes the conversation owner using a camelCase field name (`userId`). This spec assumes that field name is the authoritative form and that ownership validation must match it exactly.
- The frontend always provides an explicit conversation identifier in practice today. The fallback identifier-generation path is used defensively; fixing it is a correctness hardening, not a response to an active production incident.
- No database schema migration is required. The ownership field name fix is a code-side lookup correction, not a storage-level change.
- The SQL/Fabric history implementation has its own, separate ownership validation path that is not affected by these changes.
- All three fixes are in the Cosmos DB history layer only (`app/data/cosmos_history.py` and `app/api/routers/history.py`). No other files need to change.
- The existing test framework and test conventions (pytest, existing mocks for history routes) are sufficient to validate these fixes without introducing new test infrastructure.
