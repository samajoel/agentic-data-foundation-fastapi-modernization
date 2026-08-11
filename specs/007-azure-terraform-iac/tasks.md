# Tasks: Azure Infrastructure as Code

**Input**: Design documents from `specs/007-azure-terraform-iac/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Note**: This is a brownfield IaC capture spec. No application code is written. Tasks produce
Terraform configuration files derived from the live Azure environment using `aztfexport`. Several
tasks require live Azure CLI authentication and Internet connectivity.

**Organization**: Tasks are grouped by user story to enable independent verification of each
incremental deliverable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when dependencies are satisfied.
- **[Story]**: Which user story the task belongs to.

---

## Phase 1: Setup

**Purpose**: Create the Terraform project skeleton and configure version-control hygiene before
running Azure export tooling.

- [x] T001 Create `terraform/` at the repository root and add `terraform/.gitignore` containing:
  `.terraform/`, `*.tfstate`, `*.tfstate.backup`, `terraform.tfvars`, `*.auto.tfvars`, `crash.log`,
  `override.tf`, `override.tf.json`, `*_override.tf`, and `*_override.tf.json`; do NOT ignore
  `.terraform.lock.hcl` because the provider lock file must be version-controlled.

- [x] T002 Review the repository root `.gitignore` and append any missing Terraform patterns
  (`*.tfstate`, `*.tfstate.backup`, `.terraform/`, `terraform.tfvars`, `*.auto.tfvars`) if they
  are absent; confirm the patterns are present after the update; do not add `.terraform.lock.hcl`
  to the ignore list.

- [x] T003 Confirm Azure CLI authentication and subscription context:
  run `az account show -o table`, confirm the active subscription is the expected Azure
  subscription, and record the subscription ID and tenant ID for use in local Terraform
  configuration; do not commit credentials or secrets.

---

## Phase 2: Foundational Capture

**Purpose**: Capture the existing Azure infrastructure as Terraform configuration without modifying
the live environment.

**Critical constraint**: No Azure resource may be created, modified, deleted, replaced, or
reconfigured during this phase.

**Target resources**:

1. Resource Group `AI-103-Study-Lab`
2. Azure AI / Foundry resource `ai-brain-openai`
3. Azure AI Project `proj-default`
4. Cosmos DB account `cosmos-agentic-joel-dev`
5. Cosmos DB SQL database `chat-history`
6. Cosmos DB SQL container `conversations`
7. Azure SQL server `sql-agentic-joel-dev`
8. Azure SQL database `agentic-data-db`

Resources such as `ai-foundations-lab` and `mateo-mms8qxga-eastus2` are outside the scope of this
feature unless explicitly confirmed later.

- [x] T004 From an otherwise empty `terraform/` working directory, run
  `aztfexport resource-group --hcl-only AI-103-Study-Lab`; use the interactive TUI to retain only
  the 8 confirmed application-owned resources and skip all unrelated resources; confirm the
  export; preserve the generated HCL and mapping/skipped-resource artifacts for inspection; do
  not run `terraform apply` or otherwise modify Azure.

- [x] T005 Inspect the output of T004 and record the Terraform resource type generated for each of
  the 8 target resources; explicitly verify the generated representation for `ai-brain-openai`
  and `proj-default` rather than assuming a specific AzureRM resource type; identify any resources
  that `aztfexport` could not represent automatically.

- [x] T006 From the `terraform/` directory, run `terraform init`; confirm initialization succeeds
  and inspect the generated `.terraform.lock.hcl`; record the resolved `azurerm` provider version
  and ensure `.terraform.lock.hcl` is not ignored by Git.

**Checkpoint**: `terraform/` contains the initial exported Terraform configuration, the generated
mapping/skipped-resource artifacts have been inspected, Terraform is initialized, and no Azure
resource has been modified.

---

## Phase 3: User Story 1 — Application Infrastructure Is Version-Controlled and Readable (Priority: P1)

**Goal**: All 8 confirmed resources appear as readable, named Terraform declarations and a
developer unfamiliar with the environment can understand their relationships without Azure
Portal access.

**Independent Test**: Inspect the Terraform configuration and confirm that all 8 confirmed
resources are represented by identifiable Terraform declarations or documented/manual
representations where provider limitations prevent automatic export.

### Implementation for User Story 1

- [x] T007 [US1] Verify the live configuration of the Cosmos DB container
  `conversations` using Azure CLI; retrieve and record the actual partition key path, indexing
  policy, and any other properties required to reproduce the live configuration; do not infer
  these values from application code or older Bicep/templates.

- [x] T008 [US1] Verify the live configuration of Azure SQL database `agentic-data-db` using
  Azure CLI; record the actual SKU, maximum size, collation, and relevant configuration required
  for an exact Terraform representation; use the live Azure environment as the source of truth.

- [x] T009 [US1] Verify the Azure SQL server authentication model; confirm that
  `sql-agentic-joel-dev` uses Microsoft Entra/Azure AD-only authentication and do not introduce
  a SQL administrator password or other credential into Terraform configuration; preserve the
  existing authentication model.

- [x] T010 [US1] Run `terraform plan -detailed-exitcode` as a diagnostic pass after the initial
  export and state preparation; capture the full output and identify every resource showing
  planned `+`, `~`, `-`, or replacement changes; distinguish actual configuration differences
  from computed values, provider defaults, missing state, or unsupported export properties.

- [x] T011 [US1] For each resource showing an unexpected planned change in T010, compare the
  generated Terraform configuration with the live Azure resource using Azure CLI; correct only
  the Terraform representation that is necessary to accurately describe the existing resource;
  do not use `terraform apply` to make Azure conform to Terraform.

- [x] T012 [US1] Resolve Azure AI / Foundry representation based on the actual resource types
  supported by the installed `azurerm` provider and generated by `aztfexport`; do not assume
  `azurerm_ai_foundry` or `azurerm_ai_foundry_project` exists; if a resource cannot be exported
  automatically, document the limitation and create a manual Terraform representation only
  when the provider supports it and the representation can be verified against the live resource.

- [x] T013 [US1] Reorganize the generated Terraform into the planned domain files:
  `terraform/resource_group.tf`, `terraform/ai_foundry.tf`, `terraform/cosmos_db.tf`, and
  `terraform/sql.tf`; preserve the generated resource declarations and dependencies while moving
  them; remove obsolete generated per-resource files only after confirming their contents were
  transferred.

- [x] T014 [P] [US1] Create `terraform/variables.tf` only for values that are genuinely variable
  within the captured configuration; include `subscription_id` and `tenant_id` as string
  variables if required by the provider configuration; do not create a single global `location`
  variable because the existing environment spans multiple Azure regions (`eastus` for the
  Resource Group/Cosmos/Foundry resources and `westus2` for Azure SQL) unless the generated
  configuration demonstrates a justified use.

- [x] T015 [P] [US1] Create `terraform/outputs.tf` based on the actual Terraform resource types
  successfully generated or manually established for the 8 confirmed resources; include useful
  resource IDs and endpoints where appropriate; do not assume specific Azure AI / Foundry
  resource addresses before T012 has established them.

- [x] T016 [P] [US1] Create `terraform/terraform.tfvars.example` containing only non-sensitive
  placeholder values required by the final Terraform configuration, such as
  `subscription_id = "your-subscription-id"` and `tenant_id = "your-tenant-id"`; do not include
  passwords, access keys, connection strings, or other secrets; this file is committed.

- [x] T017 [US1] Add concise inline HCL comments to `resource_group.tf`, `ai_foundry.tf`,
  `cosmos_db.tf`, and `sql.tf` describing the purpose of each resource, parent/child
  relationships, relevant regional placement, and any manual representation or known export
  limitation.

- [x] T018 [US1] Create `terraform/known-gaps.md`; document every export limitation, unsupported
  resource type, manually represented property, provider limitation, or dependency that cannot
  be fully managed; each entry must include resource, gap, manual representation/workaround,
  verification status, and whether the limitation affects the zero-change validation.

**Checkpoint**: All 8 confirmed resources are represented in the Terraform configuration or
explicitly documented with a verified manual representation where automatic export is not
possible. Configuration is readable and reflects the actual Azure topology.

---

## Phase 4: Terraform State Population

**Purpose**: Establish Terraform state for the already-existing Azure resources without applying
infrastructure changes.

**Important**: This phase MUST NOT use `terraform apply`.

- [x] T019 Populate Terraform state for the existing resources using the resource addresses and
  Azure resource IDs established during T005/T012; use `terraform import` or the appropriate
  state-population workflow supported by the generated `aztfexport` mapping information; import
  only the 8 confirmed application-owned resources and do not create, modify, or delete Azure
  resources.

- [x] T020 Verify Terraform state after population with `terraform state list`; confirm the
  expected managed resource addresses are present and correspond to the 8 confirmed resources;
  investigate any missing, duplicate, or unexpected state entries before continuing.

- [x] T021 Confirm that the local Terraform state file is excluded from Git; run `git status` and
  verify that `terraform.tfstate` and any backup state files are ignored and are not staged.

**Checkpoint**: Terraform state represents the existing application-owned resources and no
Azure resource has been changed by the state-population process.

---

## Phase 5: User Story 2 — Infrastructure Configuration Validates Against Live Environment (Priority: P2)

**Goal**: Terraform configuration is structurally valid and produces zero planned infrastructure
changes against the existing Azure environment.

**Independent Test**: `terraform validate` succeeds and `terraform plan -detailed-exitcode`
returns exit code 0 with:

`Plan: 0 to add, 0 to change, 0 to destroy.`

### Implementation for User Story 2

- [x] T022 [US2] Run `terraform fmt -recursive` from `terraform/`; then run
  `terraform fmt -check -recursive` and confirm exit code 0.

- [x] T023 [US2] Run `terraform validate` from `terraform/`; confirm the configuration is valid
  with exit code 0; if validation errors appear, fix the Terraform configuration and re-run until
  validation passes.

- [x] T024 [US2] Run `terraform plan -detailed-exitcode` from `terraform/`; treat this as the
  primary acceptance gate for SC-002; the expected result is exit code 0 and:
  `Plan: 0 to add, 0 to change, 0 to destroy.`

- [x] T025 [US2] If T024 reports changes, diagnose each difference before making any correction;
  classify it as actual drift, an incorrect declaration, a provider default/computed attribute,
  missing state, an export limitation, or an unsupported resource representation; correct the
  Terraform configuration only when appropriate, then re-run `terraform fmt`,
  `terraform validate`, and `terraform plan`.

- [x] T026 [US2] Repeat T025 until the Terraform plan reaches zero additions, zero modifications,
  zero deletions, and zero replacements, or document an unavoidable provider/export limitation
  explicitly in `terraform/known-gaps.md`; no unresolved destructive replacement may be accepted.

- [x] T027 [US2] Update `terraform/known-gaps.md` after the final zero-change validation; mark
  each manually represented or previously unresolved gap as `VERIFIED` only when the final
  Terraform validation demonstrates that the representation produces no unexpected changes.

**Checkpoint**: `terraform validate` passes and `terraform plan` reaches the zero-change acceptance
gate without modifying Azure.

---

## Phase 6: User Story 3 — Sensitive Values Are Excluded from Version Control (Priority: P3)

**Goal**: No secrets, passwords, access keys, connection strings, or credentials appear in
committed Terraform configuration.

**Independent Test**: The repository contains no tracked Terraform state, provider cache, local
variable files, passwords, access keys, or connection strings.

### Implementation for User Story 3

- [x] T028 [US3] Verify `terraform/.gitignore` is tracked by Git and contains the required local
  exclusions; run `git ls-files terraform/` and confirm `.terraform/`, `terraform.tfstate`,
  `terraform.tfstate.backup`, and `terraform.tfvars` are not tracked; confirm
  `.terraform.lock.hcl` IS tracked or is eligible to be committed.

- [x] T029 [US3] Create a local non-committed `terraform/terraform.tfvars` from
  `terraform.tfvars.example` if required by the final configuration; populate only the real
  subscription and tenant identifiers needed locally; do not place passwords, keys, tokens,
  connection strings, or other secrets in the file.

- [x] T030 [US3] Run the secret scan from `quickstart.md` V-006 against all tracked Terraform
  files; confirm zero matches for account keys, shared access keys, passwords, client secrets,
  and connection strings; investigate and remove any false positives or real secrets before
  completion.

- [x] T031 [US3] Run `git status --short` and verify that `terraform.tfvars`, Terraform state
  files, `.terraform/`, and other local/generated artifacts are not staged or tracked; confirm
  only intended Terraform source, documentation, and `.terraform.lock.hcl` are candidates for
  version control.

**Checkpoint**: No secrets or local Terraform state are present in version-controlled files.

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Execute the complete validation suite and produce final evidence that the
specification is satisfied.

- [x] T032 Run all applicable validation scenarios V-001 through V-008 from
  `specs/007-azure-terraform-iac/quickstart.md`; record PASS / FAIL / N/A and a one-line
  explanation for each scenario; every FAIL must be resolved before completion.

- [x] T033 [P] Run `terraform fmt -check -recursive` and `terraform validate` from `terraform/`;
  confirm formatting and structural validation pass.

- [x] T034 [P] Run the final `terraform plan -detailed-exitcode`; capture the exact final summary
  line and confirm:
  `Plan: 0 to add, 0 to change, 0 to destroy.`

- [x] T035 [P] Verify SC-001 manually: inspect all Terraform declarations and confirm that the
  eight confirmed resources are represented and identifiable:
  `AI-103-Study-Lab`, `ai-brain-openai`, `proj-default`, `cosmos-agentic-joel-dev`,
  `chat-history`, `conversations`, `sql-agentic-joel-dev`, and `agentic-data-db`.

- [x] T036 [P] Verify SC-004 manually and with the repository secret scan; confirm zero committed
  credentials, passwords, access keys, connection strings, Terraform state files, or provider
  cache directories.

- [x] T037 Add a `## Final Verification` section to `terraform/known-gaps.md` containing the
  validation date, Terraform version, `aztfexport` version, resolved `azurerm` provider version,
  and the final zero-change plan result; do not include credentials or sensitive values.

- [x] T038 Review the final `terraform/` directory and confirm that a developer without Azure
  Portal access can identify the eight application-owned resources, their Terraform types,
  regional placement, parent/child relationships, known gaps, and validation status from the
  committed configuration and documentation alone.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: T001–T003 must complete before Azure export.
- **Phase 2 (Foundational Capture)**: T004 → T005 → T006.
- **Phase 3 (US1)**: T007–T018 depend on the successful completion of Phase 2.
- **Phase 4 (State Population)**: T019 depends on T005, T012, and T013; T020 depends on T019;
  T021 depends on T020.
- **Phase 5 (US2)**: T022 → T023 → T024. T025–T026 repeat as necessary until the zero-change
  acceptance gate is reached. T027 depends on the final successful validation.
- **Phase 6 (US3)**: T028–T031 depend on the Terraform project existing; they can be executed
  independently of the final plan once the required files exist.
- **Phase 7 (Polish)**: T032 depends on Phases 3–6; T033–T038 run after T032 where applicable.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 and produces the readable Terraform configuration.
- **US2 (P2)**: Depends on US1 and state population.
- **US3 (P3)**: Can begin after the Terraform files and `.gitignore` exist; it does not require
  a successful zero-change plan.

### Parallel Opportunities

```text
After T001:
    T002 + T003 can proceed independently.

After T006:
    T007 + T008 + T009 can proceed independently.

After T013:
    T014 + T015 + T016 can proceed independently.

After T018:
    T019 must establish state before the final plan validation.

After state population:
    T022 → T023 → T024 → T025/T026

After Terraform files exist:
    T028 + T029 can proceed independently.

After final validation:
    T033 + T034 + T035 + T036 + T037 + T038 can proceed where their dependencies are satisfied.