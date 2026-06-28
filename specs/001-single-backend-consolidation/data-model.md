# Data Model: Single Backend Consolidation

**Feature**: 001-single-backend-consolidation
**Date**: 2026-06-27

This consolidation introduces no new data entities and modifies no existing ones.
This document records the stable entities that remain after consolidation for reference
by downstream specs.

---

## Entities That Persist After Consolidation

### Conversation

Represents a chat session between a user and the AI agent.

| Attribute | Description |
|-----------|-------------|
| conversation_id | Unique identifier for the conversation |
| user_id | Identity of the user who owns the conversation |
| title | Display name for the conversation (auto-generated or user-renamed) |
| messages | Ordered list of message turns in the conversation |
| created_at | Timestamp of conversation creation |

**Storage backends** (selected by environment configuration):
- Cosmos DB (`history.py` router)
- SQL Database in Microsoft Fabric (`history_sql.py` router)

### Message

A single turn within a Conversation.

| Attribute | Description |
|-----------|-------------|
| message_id | Unique identifier |
| conversation_id | Parent conversation reference |
| role | `user` or `assistant` |
| content | Text content of the message turn |
| feedback | Optional user feedback value (thumbs-up/down) |

---

## Entities Removed by This Consolidation

None. The .NET backend mirrored the same Conversation and Message entities against the
same Fabric SQL and Cosmos DB stores. Removing the .NET runtime does not alter the
underlying data schema.

---

## Note on Data Access

As of this consolidation, data access continues to be handled directly within
`history.py` and `history_sql.py`. A future spec (data-access layer extraction) will
isolate this into a dedicated `data/` layer per constitution Principle VIII.
