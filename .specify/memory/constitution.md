<!--
SYNC IMPACT REPORT
==================
Version change: TEMPLATE (unversioned) → 1.0.0 (initial ratification)

Added sections:
  Core Principles (12 principles), Architecture Constraints,
  Development Workflow, Quality Gates, Governance

Removed sections:
  All template placeholder sections replaced with project-specific content

Templates reviewed:
  .specify/templates/plan-template.md  — Constitution Check gate present; aligns with
                                         principles below. No changes required.
  .specify/templates/spec-template.md  — User story + acceptance scenario structure
                                         compatible. No changes required.
  .specify/templates/tasks-template.md — Phase structure compatible. No changes required.
  .specify/templates/commands/         — Directory not present; nothing to review.

Deferred items: None. All content derived from project facts supplied by the user.
-->

# Agentic Data Foundation FastAPI Modernization Constitution

## Core Principles

### I. Python FastAPI Backend Is the System of Record

The Python FastAPI backend at `src/api/python/` is the authoritative implementation.
All new feature work, bug fixes, and modernization tasks MUST target this backend only.

### II. .NET Backend Is Retired

The .NET backend under `src/api/dotnet/` MUST NOT be modified, extended, or reintroduced
in any form. Any PR that adds code to or routes through the .NET backend will be rejected.

### III. External API Contract Is Stable

The following endpoints MUST remain behaviorally stable across all modernization work:

- `POST /chat`
- `GET /history`

Field names, response shapes, and HTTP status codes MUST NOT change unless a dedicated
spec explicitly approves and versions the change. Additive changes such as new optional
response fields are permitted without versioning.

### IV. React Frontend Is Out of Scope

The React frontend MUST NOT be modified by any modernization task unless a separate,
explicitly approved spec scopes frontend changes. Backend changes MUST NOT require
frontend updates to keep the application functional.

### V. Brownfield Modernization — Preserve Existing Behavior

Existing behavior MUST be preserved unless a spec explicitly states otherwise.
Do not remove, replace, or silently change behavior as a side effect of refactoring.

### VI. No Hardcoded Credentials

All Azure resource access MUST use Managed Identity or the existing `azure-identity`
pattern already established in `src/api/python/`. Hardcoded credentials, API keys,
connection strings, or secrets in code or committed files are forbidden. Secrets needed
for local development MUST use `.env` files that are excluded from version control.

### VII. Agent Orchestration Via Microsoft Agent Framework

Agent orchestration MUST use the Microsoft Agent Framework (`agent-framework-core`,
`agent-framework-foundry`) already present in the project. No parallel custom agent loop
or alternative orchestration library may be introduced without an explicit spec that
justifies and approves it.

### VIII. Data Access Behind a Dedicated Layer

FastAPI route handlers MUST NOT directly query Fabric SQL, Cosmos DB, or any persistence
store. All structured data access MUST go through a dedicated data-access layer that
encapsulates queries and connection management.

### IX. Testing Via Existing pytest Configuration

All tests MUST use the existing pytest configuration in `pytest.ini`. Coverage MUST
respect `.coveragerc`. Linting MUST respect `.flake8` and `src/.flake8`. No alternative
test runners, coverage tools, or linters may be introduced.

### X. New Backend Code Follows Layered Architecture

New backend code MUST be organized into these layers:

- **api** — FastAPI routers and Pydantic request/response schemas
- **service** — business logic and orchestration calls
- **agent** — Agent Framework interaction and prompt construction
- **data** — all persistence store access (Fabric SQL, Cosmos DB, etc.)
- **core** — shared utilities, configuration, logging, middleware

Route handlers MUST NOT contain business logic. Business logic MUST NOT contain direct
data queries.

### XI. Spec Kit Workflow Is Mandatory for Each Modernization Unit

Each major modernization unit MUST be implemented through a Spec Kit specification,
implementation plan, task list, and a dedicated Git branch and reviewable PR.
Ad-hoc changes that bypass this workflow are not permitted for non-trivial work.

### XII. Reference Only Verified Tool Versions

Plans, specs, and tasks MUST reference only tool versions and configurations already
present in the repository. When a version is needed, consult `src/api/python/requirements.txt`,
`pytest.ini`, `.flake8`, or `.coveragerc`. Do not invent versions, CI tools, or runtime
targets.

## Architecture Constraints

These constraints are fixed for the scope of this modernization. Changing any of them
requires a constitution amendment.

- **Web framework**: FastAPI, version pinned in `src/api/python/requirements.txt`
- **Data validation**: Pydantic v2, version pinned in `src/api/python/requirements.txt`
- **Azure SDK**: `azure-identity`, `azure-ai-projects`, `azure-ai-agents` — versions
  pinned in `src/api/python/requirements.txt`
- **Agent orchestration**: `agent-framework-core`, `agent-framework-foundry`
- **Telemetry**: `azure-monitor-opentelemetry` and the OpenTelemetry SDK
- **Deployment topology**: As defined in `azure.yaml` and `infra/`; no topology changes
  without an explicit spec
- **Frontend**: React app under `src/App/`; read-only for all backend modernization work

## Development Workflow

1. Create a feature branch named after the spec (e.g., `001-data-access-layer`). Never
   commit modernization work directly to `main`.
2. The spec.md MUST be approved before implementation begins.
3. Run `/speckit-plan` to produce plan.md before running `/speckit-tasks`. Both MUST
   reference this constitution.
4. Every plan.md MUST include a Constitution Check section confirming compliance before
   Phase 0 research proceeds.
5. For any existing behavior being modified, a passing test covering that behavior MUST
   exist before the modification is made.
6. Every PR MUST state which spec it implements and confirm API contract stability:
   breaking, non-breaking, or not applicable.

## Quality Gates

A PR is complete only when all of the following pass:

- `pytest -m unittest` passes with no new failures.
- `flake8` reports no new violations per `.flake8` and `src/.flake8`.
- Coverage does not decrease below the threshold set in `.coveragerc`.
- No secrets, hardcoded credentials, or connection strings introduced.
- `POST /chat` and `GET /history` behave identically to pre-change behavior unless the
  governing spec explicitly approves a change.
- PR description references the governing spec and states the contract stability verdict.

`pytest -m functional` and `pytest -m azure` MUST pass before any merge to `main`.
They may be deferred to a pre-merge CI step with documented rationale.

## Governance

This constitution supersedes all other development practices in this repository. When any
practice conflicts with a principle above, the principle governs or an amendment is
required before the conflicting practice proceeds.

**Amendment process**:

1. Open a PR modifying `.specify/memory/constitution.md` with an updated Sync Impact
   Report as an HTML comment at the top of the file.
2. Bump the version per semantic versioning: MAJOR for principle removals or redefinitions;
   MINOR for new principles or sections added; PATCH for clarifications or wording fixes.
3. Update the Last Amended date to the merge date.
4. Re-run `/speckit-constitution` after merge to propagate changes to templates.

Violations that cannot be avoided MUST be documented in the plan's Complexity Tracking
table and approved before implementation begins.

**Version**: 1.0.0 | **Ratified**: 2026-06-23 | **Last Amended**: 2026-06-23
