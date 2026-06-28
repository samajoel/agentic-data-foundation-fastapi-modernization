# Implementation Plan: Single Backend Consolidation

**Branch**: `001-single-backend-consolidation` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-single-backend-consolidation/spec.md`

## Summary

Remove the .NET backend and all Copilot Studio / Teams artifacts from the repository so that
the Python FastAPI backend at `src/api/python/` is the sole runtime, `infra/` deploys only
the Python container, and all documentation describes only the Microsoft Fabric + Foundry
architecture path. No Python application code is restructured. The external API contract
(`POST /api/chat`, `/history/*`, `/historyfab/*`) is unchanged.

## Technical Context

**Language/Version**: Python (version defined by repo runtime environment)

**Primary Dependencies**: FastAPI, Azure Bicep (IaC) — versions pinned in
`src/api/python/requirements.txt` and `infra/`

**Storage**: N/A — no data-layer changes

**Testing**: pytest per `pytest.ini`; coverage via `.coveragerc`; linting via `.flake8` and
`src/.flake8`

**Target Platform**: Azure Container Apps (Consumption plan) as defined in `azure.yaml` and
`infra/`

**Project Type**: Brownfield consolidation — removal and cleanup only; no new code written

**Performance Goals**: N/A — no new performance characteristics introduced

**Constraints**: External API contract must remain stable; Python FastAPI app must not be
restructured; React frontend must require no changes

**Scale/Scope**: ~30 source files deleted, ~6 Bicep/ARM files modified, ~3 documentation
files modified, 1 documentation file deleted, 16 image assets deleted

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python FastAPI Is System of Record | PASS | This spec eliminates the competing runtime |
| II. .NET Backend Is Retired | PASS | Primary purpose of this spec |
| III. External API Contract Is Stable | PASS | No endpoint changes; contract documented in contracts/ |
| IV. React Frontend Is Out of Scope | PASS | No frontend files touched |
| V. Brownfield — Preserve Existing Behavior | PASS | Removals only; Python app unchanged |
| VI. No Hardcoded Credentials | PASS | No new credentials introduced |
| VII. Agent Orchestration Via Agent Framework | PASS | Orchestration layer untouched |
| VIII. Data Access Behind Dedicated Layer | PASS | No data-layer changes |
| IX. Testing Via Existing pytest | PASS | Existing pytest suite validates; no new test tooling |
| X. Layered Architecture | PASS | No new backend code added |
| XI. Spec Kit Workflow Mandatory | PASS | Followed throughout |
| XII. Reference Only Verified Tool Versions | PASS | No new tools referenced |

No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-single-backend-consolidation/
├── plan.md              # This file
├── research.md          # Phase 0 — complete removal inventory
├── data-model.md        # Phase 1 — stable entities after consolidation
├── quickstart.md        # Phase 1 — post-consolidation validation guide
├── contracts/
│   └── api-contract.md  # Phase 1 — stable API surface documented
└── tasks.md             # Phase 2 — created by /speckit-tasks
```

### Repository Changes (removal map)

```text
REMOVE:
  src/api/dotnet/               ← entire directory (~30 source + test files)

MODIFY (infra — remove .NET deployment branch):
  infra/main.bicep              ← remove backendRuntimeStack param, backend_csapi_docker
                                   module, all dotnet conditional branches and outputs
  infra/main_custom.bicep       ← same as main.bicep
  infra/main.json               ← regenerate from Bicep OR patch ARM conditions/resources
  infra/main.parameters.json    ← remove backendRuntimeStack parameter entry

DELETE (infra — .NET-only files):
  infra/deploy_backend_csapi_docker.bicep
  infra/deploy_csapi_app_service.bicep
  infra/csapi.parameters.json

MODIFY (docs — remove .NET runtime choice):
  documents/DeploymentGuide.md  ← remove "dotnet" runtime row, azd env set dotnet section,
                                   .NET deployment steps, CopilotStudioDeployment link

DELETE (docs — Copilot Studio):
  documents/CopilotStudioDeployment.md
  documents/Images/cps/         ← 16 image assets

MODIFY (docs — remove CPS architecture references):
  documents/TechnicalArchitecture.md ← remove CPS architecture diagram section
  README.md                          ← remove "Microsoft Fabric and Microsoft Copilot Studio"
                                        architecture section and diagram

UNCHANGED:
  src/api/python/               ← no changes
  src/App/                      ← no changes (React frontend)
  infra/deploy_backend_docker.bicep      ← Python Container App — stays
  infra/deploy_backend_custom.bicep      ← Python custom deploy — stays
  azure.yaml                    ← no .NET references; stays as-is
  scripts/                      ← no .NET references; stays as-is
  tests/                        ← no changes
```

**Structure Decision**: Brownfield removal. No new project structure is introduced. The
changes consist exclusively of deletions and targeted edits to existing files.
