---

description: "Task list for Single Backend Consolidation"
---

# Tasks: Single Backend Consolidation

**Input**: Design documents from `specs/001-single-backend-consolidation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contract.md, quickstart.md

**Tests**: Not explicitly requested. Validation tasks confirm existing pytest suite still passes; no new test files are written.

**Organization**: Tasks are grouped by user story. Implementation ordering departs from
pure priority ordering because US1 (P1) is an acceptance validation story that can only
be executed after US2 (P2) and US3 (P3) removal work is complete. US1 remains P1 because
it is the non-negotiable outcome gate — if it fails, the consolidation is not done.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Establish a passing baseline before any file is changed.

- [X] T001 Run `pytest -m unittest` from repo root and record the passing test count as the baseline that must be matched at T018

**Checkpoint**: Baseline recorded. Proceed to removal phases.

---

## Phase 3: User Story 2 — Repository Contains Single Backend Runtime (Priority: P2)

**Goal**: Delete all .NET backend source code and remove all .NET deployment branches
from the infrastructure templates so the repository contains only the Python FastAPI
runtime.

**Independent Test**: `grep -r "dotnet\|CsApi\|csapi\|backendRuntimeStack" infra/ src/`
returns zero results.

### Source removal for User Story 2

- [X] T002 [P] [US2] Delete the entire `src/api/dotnet/` directory and all its contents (~30 source, test, and build files)

### Infrastructure file deletion for User Story 2

- [X] T003 [P] [US2] Delete `infra/deploy_backend_csapi_docker.bicep` (Container App deployment module for .NET image `da-api-dotnet`)
- [X] T004 [P] [US2] Delete `infra/deploy_csapi_app_service.bicep` (App Service deployment module for .NET backend)
- [X] T005 [P] [US2] Delete `infra/csapi.parameters.json` (parameter file for .NET App Service deployment)

### Infrastructure file edits for User Story 2

- [X] T006 [P] [US2] Edit `infra/main.bicep`: remove the `backendRuntimeStack` allowed-values parameter (~line 25–27), remove the `backend_csapi_docker` conditional module block (~line 307–370), replace the `APP_API_BASE_URL` ternary expression (~line 368) with a direct reference to `backend_docker!.outputs.appUrl`, replace the `API_APP_NAME` ternary output (~line 425) with a direct reference to `backend_docker!.outputs.appName`, and remove the `BACKEND_RUNTIME_STACK` output (~line 475–476)
- [X] T007 [P] [US2] Edit `infra/main_custom.bicep`: apply the same changes as T006 targeting `backend_custom` (not `backend_docker`) — remove `backendRuntimeStack` parameter, `backend_csapi_docker` module block, ternary expressions for `APP_API_BASE_URL` (~line 351) and `API_APP_NAME` (~line 406), and `BACKEND_RUNTIME_STACK` output (~line 453–454)
- [X] T008 [P] [US2] Edit `infra/main.parameters.json`: remove the `backendRuntimeStack` parameter entry (~line 38)
- [X] T009 [US2] Regenerate `infra/main.json` after T006, T007, and T008 are complete: run `az bicep build --file infra/main.bicep --outfile infra/main.json` from repo root; if `az bicep` CLI is unavailable, manually remove the `dotnet` conditional resource block (~lines 3765–3919) and the `backendRuntimeStack` parameter from `infra/main.json`
- [X] T010 [US2] Verify: run `grep -r "dotnet\|CsApi\|csapi\|backendRuntimeStack" infra/ src/` from repo root and confirm zero results

**Checkpoint**: User Story 2 complete — repository contains no .NET backend artifacts. US2 acceptance test passes.

---

## Phase 4: User Story 3 — Single Architecture Path: Fabric and Foundry (Priority: P3)

**Goal**: Delete `documents/CopilotStudioDeployment.md` and all CPS image assets, then
remove every Copilot Studio and Teams reference from `README.md`,
`documents/TechnicalArchitecture.md`, and `documents/DeploymentGuide.md`.

**Independent Test**: `grep -ri "copilot\|CopilotStudio\|cps\|solution-architecture-cps" documents/ README.md`
returns zero results.

### Documentation deletion for User Story 3

- [X] T011 [P] [US3] Delete `documents/CopilotStudioDeployment.md`
- [X] T012 [P] [US3] Delete the entire `documents/Images/cps/` directory and all 16 image files it contains (create-data-agent.png and 15 microsoft-copilot-studio-*.png files)
- [X] T013 [P] [US3] Delete `documents/Images/ReadMe/solution-architecture-cps.png`

### Documentation edits for User Story 3

- [X] T014 [P] [US3] Edit `README.md`: remove the "Microsoft Fabric and Microsoft Copilot Studio:" section heading, its architecture diagram (`![image](./documents/Images/ReadMe/solution-architecture-cps.png)`), and any surrounding prose specific to that architecture path (~line 29)
- [X] T015 [P] [US3] Edit `documents/TechnicalArchitecture.md`: remove the CPS architecture diagram section — the heading and `![image](./Images/ReadMe/solution-architecture-cps.png)` reference (~line 7) and any associated prose
- [X] T016 [P] [US3] Edit `documents/DeploymentGuide.md`: (a) remove the "Backend Programming Language" table row that mentions `python` or `dotnet` (~line 150); (b) remove the prose and command `azd env set BACKEND_RUNTIME_STACK dotnet` and its surrounding section (~lines 216–219); (c) remove the `.NET (dotnet)` deployment option section (~line 243); (d) remove the `CopilotStudioDeployment` link and its deployment step reference (~line 374)
- [X] T017 [US3] Verify: run `grep -ri "copilot\|CopilotStudio\|cps\|solution-architecture-cps" documents/ README.md` from repo root and confirm zero results

**Checkpoint**: User Story 3 complete — repository describes only the Fabric and Foundry architecture path. US3 acceptance test passes.

---

## Phase 5: User Story 1 — Frontend Continues to Work After Consolidation (Priority: P1)

**Goal**: Confirm the Python FastAPI backend serves the full API contract intact and
the existing test suite passes with no regressions.

**Depends on**: US2 (Phase 3) and US3 (Phase 4) must both be complete.

**Independent Test**: Start the Python backend, submit a request to `POST /api/chat`,
retrieve `/history/list`, and confirm both respond without errors. Existing pytest
baseline from T001 must match.

### Validation for User Story 1

- [X] T018 [US1] Run `pytest -m unittest` from repo root and confirm all tests that passed in T001 still pass with no new failures
- [X] T019 [US1] Run `flake8 src/api/python/` and confirm no new linting violations beyond any that pre-existed before this consolidation
- [ ] T020 [US1] Start the Python backend locally: `cd src/api/python && python app.py`; confirm the server starts on port 8000 with no startup errors
- [ ] T021 [US1] Smoke test `GET /health`: run `curl http://127.0.0.1:8000/health` and confirm response is `{"status":"healthy"}`
- [ ] T022 [US1] Smoke test `POST /api/chat`: run `curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d '{"conversation_id":"test-001","messages":[{"role":"user","content":"Hello"}]}'` and confirm a streaming response is returned (no 404, 500, or connection error)
- [ ] T023 [US1] Smoke test `/history/list`: run `curl "http://127.0.0.1:8000/history/list?user_id=test-user&limit=5"` and confirm a JSON response is returned (no 404 or 500)

**Checkpoint**: User Story 1 acceptance gate passed — frontend API contract is intact and existing tests show no regressions. Consolidation is functionally complete.

---

## Final Phase: Polish and Cross-Cutting Concerns

**Purpose**: Catch any orphaned references or broken links introduced by the removals.

- [X] T024 [P] Scan all remaining Markdown files in `documents/` for broken image links: `grep -r "!\[" documents/ README.md | grep "cps\|solution-architecture-cps"` must return zero results
- [X] T025 [P] Confirm `documents/DeploymentGuide.md` has no broken section cross-references after edits: read the file and confirm all remaining internal links resolve to sections that still exist
- [ ] T026 Run full quickstart validation from `specs/001-single-backend-consolidation/quickstart.md` as a final end-to-end check

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately.
- **US2 (Phase 3)**: Depends only on Phase 1 baseline being recorded. Source deletion and infrastructure file deletion/editing tasks can all run in parallel. T009 depends on T006, T007, T008.
- **US3 (Phase 4)**: Independent of US2 — can start concurrently with Phase 3 once Phase 1 is done.
- **US1 (Phase 5)**: Depends on BOTH Phase 3 AND Phase 4 being complete.
- **Polish (Final Phase)**: Depends on all user story phases being complete.

### Within Phase 3 (US2)

```bash
# All of these can run in parallel (different files):
Task T002: Delete src/api/dotnet/
Task T003: Delete infra/deploy_backend_csapi_docker.bicep
Task T004: Delete infra/deploy_csapi_app_service.bicep
Task T005: Delete infra/csapi.parameters.json
Task T006: Edit infra/main.bicep
Task T007: Edit infra/main_custom.bicep
Task T008: Edit infra/main.parameters.json

# Then sequentially (depends on T006, T007, T008):
Task T009: Regenerate infra/main.json
Task T010: Verify grep returns zero results
```

### Within Phase 4 (US3)

```bash
# All of these can run in parallel (different files):
Task T011: Delete documents/CopilotStudioDeployment.md
Task T012: Delete documents/Images/cps/
Task T013: Delete documents/Images/ReadMe/solution-architecture-cps.png
Task T014: Edit README.md
Task T015: Edit documents/TechnicalArchitecture.md
Task T016: Edit documents/DeploymentGuide.md

# Then:
Task T017: Verify grep returns zero results
```

---

## Implementation Strategy

### MVP Scope (US1 Acceptance Gate Only)

The entire consolidation must be treated as a single atomic change — there is no
partial MVP because a half-removed .NET backend leaves ambiguity. All three user
stories must be completed before the acceptance gate (US1, Phase 5) can pass.

### Recommended Execution Order

1. **Phase 1**: Run T001 baseline — takes under 1 minute.
2. **Phases 3 and 4 in parallel** (if two contributors): One works US2 removals, one works US3 doc removals.
3. **Phase 5**: Run all validation tasks (T018–T023).
4. **Final Phase**: Scan and quickstart check (T024–T026).

### Single Contributor Order

1. Phase 1: T001
2. Phase 3 (US2): T002–T005 (delete files), T006–T008 (edit Bicep), T009 (regenerate JSON), T010 (verify)
3. Phase 4 (US3): T011–T013 (delete docs), T014–T016 (edit docs), T017 (verify)
4. Phase 5 (US1): T018–T023 (validation)
5. Final Phase: T024–T026

---

## Notes

- [P] tasks operate on different files with no cross-dependencies — safe to run simultaneously.
- T009 (`az bicep build`) requires the Azure CLI with Bicep extension installed. If unavailable, the ARM JSON can be patched manually but the Bicep sources are always authoritative.
- T001 baseline must be compared directly against T018 results. Any new failure introduced by the removal tasks must be investigated before proceeding.
- Do not remove any files not listed in this task list. If additional .NET or Copilot Studio references are discovered during execution, add them as sub-tasks to the relevant phase before deleting.
- Commit after each phase checkpoint to make rollback straightforward.
