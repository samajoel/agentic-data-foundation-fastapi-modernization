# API Contract: FastAPI Service Restructuring

**Status**: Frozen — this spec MUST NOT alter any contract detail
**Inherited from**: `specs/001-single-backend-consolidation/contracts/api-contract.md`
**Date**: 2026-06-28

The API surface defined in Spec 001 is reproduced here for reference only. The restructuring
does not change any route, method, request shape, response shape, or HTTP status code. The
primary validation of this contract is done by the quickstart validation guide
([quickstart.md](../quickstart.md)).

All route handlers continue to live in the same logical modules (`chat`, `history`,
`history_sql`); only the file system paths change. The router prefix assignments in
`app/main.py` are identical to those previously in `app.py`:

| Router module | Prefix | Tag |
|---------------|--------|-----|
| `app/api/routers/chat.py` | `/api` | chat |
| `app/api/routers/history.py` | `/history` | history |
| `app/api/routers/history_sql.py` | `/historyfab` | historyfab |

---

## Full Contract Reference

For the complete route inventory (all HTTP methods, paths, request/response shapes, and the
stability guarantee), see:

**`specs/001-single-backend-consolidation/contracts/api-contract.md`**

That document is authoritative. Any discrepancy between that document and this one means
that document governs.

---

## Contract Stability Verdict for This Spec

**Type**: Non-breaking (internal reorganization only)

No routes added, removed, or modified. No request or response shapes changed. No HTTP
status codes changed. No streaming behavior changed. No authentication behavior changed.

The React frontend requires zero changes.
