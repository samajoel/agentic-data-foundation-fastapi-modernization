# Research: Single Backend Consolidation

**Feature**: 001-single-backend-consolidation
**Phase**: 0 — Removal Inventory
**Date**: 2026-06-27

## Decision: Consolidation Approach

**Decision**: Full removal of all .NET artifacts and Copilot Studio documentation.
No toggle, no archive branch, no parameter default change.

**Rationale**: Constitution Principle II requires the .NET backend to be retired such that
it cannot be reintroduced. Leaving any stub (commented-out Bicep, unreachable parameters,
archived directory) creates the ambiguity the consolidation is meant to eliminate.
The clarification session confirmed Option A: remove entirely.

**Alternatives considered**:
- Default `backendRuntimeStack` to `python` and leave dotnet branch unreachable — rejected
  because the parameter itself signals that dotnet is a valid choice to future contributors.
- Move `src/api/dotnet/` to an archive branch — rejected because git history already
  preserves the code; a separate branch adds confusion without value.

---

## Removal Inventory

### A. Source Code

| Item | Path | Action |
|------|------|--------|
| .NET application source | `src/api/dotnet/` | Delete entire directory |
| .NET solution file | `src/api/dotnet/CsApi.sln` | Included in above |
| .NET project file | `src/api/dotnet/CsApi.csproj` | Included in above |
| .NET Dockerfile | `src/api/dotnet/CsApi.Dockerfile` | Included in above |
| .NET test suite | `src/api/dotnet/tests/` | Included in above |
| .NET test results | `src/api/dotnet/tests/CsApi.Tests/TestResults/` | Included in above |

**File count**: ~30 files across Auth, Controllers, Converters, Interfaces, Middleware,
Models, Repositories, Services, Utils, tests.

---

### B. Infrastructure — Files to Modify

#### `infra/main.bicep` and `infra/main_custom.bicep`

Both files share the same pattern. Changes required in each:

| Item | Location | Change |
|------|----------|--------|
| `backendRuntimeStack` parameter definition | Line ~25–38 | Remove parameter and `'dotnet'` allowed value |
| `backend_csapi_docker` module declaration | Line ~293–370 | Remove conditional module block |
| Ternary `backendRuntimeStack == 'python' ? ... : backend_csapi_docker!.outputs.*` | Line ~368, ~425 | Replace with direct Python module output reference |
| `BACKEND_RUNTIME_STACK` output | Line ~453–476 | Remove output |

After changes, the Python deployment module (`backend_docker` / `backend_custom`) is
unconditional; no runtime selection logic remains.

#### `infra/main.parameters.json`

Remove the `backendRuntimeStack` parameter entry (line ~38).

#### `infra/main.json` (compiled ARM template)

This file is generated from the Bicep source. Options:
- Preferred: regenerate with `az bicep build` after modifying the `.bicep` sources.
- Fallback: manually patch the ARM JSON to remove the `dotnet` condition resources and
  parameter (higher risk of inconsistency; only use if `az bicep build` is unavailable).

---

### C. Infrastructure — Files to Delete

| File | Purpose | Disposition |
|------|---------|-------------|
| `infra/deploy_backend_csapi_docker.bicep` | Deploys .NET backend as Docker container app | Delete |
| `infra/deploy_csapi_app_service.bicep` | Deploys .NET backend as App Service (legacy) | Delete |
| `infra/csapi.parameters.json` | Parameters for .NET App Service deployment | Delete |

---

### D. Documentation — Files to Delete

| File | Purpose | Disposition |
|------|---------|-------------|
| `documents/CopilotStudioDeployment.md` | Full Copilot Studio deployment guide | Delete |
| `documents/Images/cps/` | 16 screenshot images for Copilot Studio guide | Delete entire directory |

**CPS image list** (16 files in `documents/Images/cps/`):
`create-data-agent.png`, `microsoft-copilot-studio-add-fabric-data-agent.png`,
`microsoft-copilot-studio-add-fabric.png`, `microsoft-copilot-studio-agents.png`,
`microsoft-copilot-studio-channels.png`, `microsoft-copilot-studio-connector.png`,
`microsoft-copilot-studio-create-agent.png`, `microsoft-copilot-studio-data-agents.png`,
`microsoft-copilot-studio-disable_knowledge.png`, `microsoft-copilot-studio-environments.png`,
`microsoft-copilot-studio-fabric-added.png`, `microsoft-copilot-studio-fabric-authentication.png`,
`microsoft-copilot-studio-main.png`, `microsoft-copilot-studio-orchestrator.png`,
`microsoft-copilot-studio-publish.png`, `microsoft-copilot-studio-teams-channels.png`

---

### E. Documentation — Files to Modify

#### `documents/DeploymentGuide.md`

| Location | Content to remove |
|----------|------------------|
| Line ~150 | "Backend Programming Language" table row mentioning `python` or `dotnet` |
| Line ~216–219 | `azd env set BACKEND_RUNTIME_STACK dotnet` section and surrounding prose |
| Line ~243 | `.NET (dotnet)` deployment option section |
| Line ~374 | `CopilotStudioDeployment` link / step reference |

#### `documents/TechnicalArchitecture.md`

| Location | Content to remove |
|----------|------------------|
| Line ~7 | CPS architecture diagram: `![image](./Images/ReadMe/solution-architecture-cps.png)` and surrounding heading/prose |

#### `README.md`

| Location | Content to remove |
|----------|------------------|
| Line ~29 | "Microsoft Fabric and Microsoft Copilot Studio:" section heading and architecture diagram |

The `documents/Images/ReadMe/solution-architecture-cps.png` image file itself should
also be deleted once all references are removed.

---

## Verification Approach

After each deletion/modification, the following checks confirm correctness:

1. `grep -r "dotnet\|CsApi\|csapi\|backendRuntimeStack" infra/ src/` — must return zero
   results except within git history.
2. `grep -ri "copilot\|CopilotStudio\|cps" documents/ README.md` — must return zero results.
3. `pytest -m unittest` from repo root — all existing Python tests must pass.
4. Manual smoke test of `POST /api/chat` and `/history/list` against a locally running
   Python backend confirms the API contract is intact.
