# Research: Azure Infrastructure as Code

**Feature**: `specs/007-azure-terraform-iac/spec.md`
**Date**: 2026-08-10
**Phase**: 0 — Research

---

## R-001: aztfexport Invocation Approach

**Decision**: Use `aztfexport resource-group AI-103-Study-Lab` with the interactive TUI to select
only the 8 confirmed application-owned resources during the export run.

**Rationale**: The resource group `AI-103-Study-Lab` is shared and contains resources not owned by
this application (Assumption 2 in spec). The aztfexport interactive TUI allows deselecting
unrelated resources in one pass. This is more efficient than per-resource `aztfexport resource-id`
invocations (which would require knowing 8 ARM resource IDs upfront and running 8 separate commands)
and more accurate than resource-group mode without filtering (which would pull unrelated resources).

**Alternatives Considered**:
- `aztfexport resource-id <ARM_ID>` per resource — more precise but requires 8 separate runs and
  pre-existing knowledge of ARM resource IDs; viable fallback if TUI selection is insufficient.
- `aztfexport resource-group --include-resource-type <type>` — resource-type filtering doesn't work
  when two resources of the same type exist (one owned, one not); TUI is safer.
- Full resource-group export without filtering — rejected: would include unrelated shared resources,
  violating FR-002.

**Verification**: After export, confirm the generated `.tf` files reference only the 8 confirmed
resources. `terraform plan` will detect any extras as resources not in state, requiring
destructive actions or removal from config.

---

## R-002: Terraform Provider Resource Types for the 8 Resources

**Decision**: Use the following azurerm resource type mappings. If aztfexport generates a different
type (e.g., a legacy alias), use the generated type and document the discrepancy in `known-gaps.md`.

| Spec Entity | Confirmed Name | Expected Terraform Resource Type |
|-------------|---------------|----------------------------------|
| Resource Group | `AI-103-Study-Lab` | `azurerm_resource_group` |
| Azure AI Hub | `ai-brain-openai` | `azurerm_ai_foundry` ⚠ see below |
| Azure AI Project | `proj-default` | `azurerm_ai_foundry_project` ⚠ see below |
| Cosmos DB Account | `cosmos-agentic-joel-dev` | `azurerm_cosmosdb_account` |
| Cosmos DB SQL Database | `chat-history` | `azurerm_cosmosdb_sql_database` |
| Cosmos DB SQL Container | `conversations` | `azurerm_cosmosdb_sql_container` |
| Azure SQL Server | `sql-agentic-joel-dev` | `azurerm_mssql_server` |
| Azure SQL Database | `agentic-data-db` | `azurerm_mssql_database` |

**Azure AI Foundry Known Gap (⚠)**:
`azurerm_ai_foundry` and `azurerm_ai_foundry_project` are relatively new resource types in the
azurerm provider (introduced in provider v4.x). The behavior of aztfexport depends on the installed
version:
- Older aztfexport / older azurerm provider: may export as `azurerm_machine_learning_workspace`
  (legacy alias still functional for management).
- Newer aztfexport (v0.15+) with azurerm v4+: likely exports as `azurerm_ai_foundry` and
  `azurerm_ai_foundry_project`.
- If aztfexport cannot export these resources at all: write manual Terraform blocks and document
  as known gaps per FR-008.

**Strategy**: Accept whatever type aztfexport generates; do not rename unless the zero-change plan
fails. Document the generated type in `known-gaps.md` alongside the expected type. Verify the plan
shows zero changes for those resources regardless of which type is used.

**Rationale**: The acceptance gate is behavioral (`terraform plan` shows zero changes), not
syntactic (exact resource type name). Using the generated type reduces the risk of drift between
the type aztfexport maps internally and what the live environment reports.

**Alternatives Considered**:
- Force manual conversion to `azurerm_ai_foundry` after export — risky because the provider may
  not have a zero-change import for the new type without a targeted `terraform import` step.
- Skip AI Foundry resources entirely — rejected: FR-001 requires all 8 resources.

---

## R-003: Terraform Project Directory Location

**Decision**: Place the Terraform project at `terraform/` in the repository root.

**Rationale**:
- `infra/` is tightly coupled to the AZD workflow (`azure.yaml`) and contains Bicep/ARM templates
  that drive `azd provision` / `azd deploy`. Mixing Terraform into that directory would create
  ambiguity about which provisioning system is authoritative.
- `terraform/` at root is a widely recognized convention for repositories that add Terraform
  alongside an existing provisioning system.
- The Terraform configuration is a read-only capture for documentation and drift detection, not a
  replacement for the AZD provisioning workflow. Physical separation reinforces this distinction.
- No collision with existing `.gitignore` patterns (Terraform patterns must be added).

**Alternatives Considered**:
- `infra/terraform/` — rejected: would suggest Terraform is part of the AZD deployment pipeline;
  creates risk of confusion about which system is authoritative.
- `iac/` — non-standard; would require explanation for new contributors.
- `ops/terraform/` — added indirection without benefit for a single-tool IaC directory.

---

## R-004: Secret Handling and Authentication

**Decision**: Use Azure CLI authentication (`az login`) as the primary credential mechanism.
Non-interactive environments use ARM_ environment variables. No sensitive values in committed files.

**Rationale**:
- `az login` populates a local token cache; the azurerm provider picks this up automatically via
  its default authentication chain (CLI → managed identity → environment). No configuration needed
  for local development beyond `az login`.
- Constitution Principle VI forbids hardcoded credentials. Environment variables are the
  Constitution-compliant secret mechanism for local development.
- Subscription ID and tenant ID (non-sensitive identifiers) can go in `terraform.tfvars.example`
  as placeholders; the actual `terraform.tfvars` is excluded from git.

**Sensitive value boundary**:
- `terraform.tfvars` — excluded from git (contains real subscription_id, tenant_id)
- `terraform.tfvars.example` — committed with placeholder values (e.g., `subscription_id = "your-subscription-id"`)
- No access keys, connection strings, or passwords in any Terraform file

**Non-interactive authentication (CI or non-developer use)**:
```bash
export ARM_SUBSCRIPTION_ID="..."   # non-sensitive identifier
export ARM_TENANT_ID="..."         # non-sensitive identifier
export ARM_USE_CLI=true            # instructs provider to use az login token
```

**Alternatives Considered**:
- Service principal + `ARM_CLIENT_SECRET` — requires secret rotation management and a committed
  tfvars structure that invites leakage; rejected in favor of CLI auth.
- Managed Identity — correct for Azure-hosted environments but not applicable for local developer
  workstation runs; left as a future remote-backend option.

---

## R-005: Terraform State Backend

**Decision**: Local state (default Terraform behavior) for initial validation. `terraform.tfstate`
and `terraform.tfstate.backup` excluded from git via `terraform/.gitignore`.

**Rationale**: Per spec Assumption 4 and FR-010, local state is acceptable for the validation
phase. Remote state migration (to Azure Storage or Terraform Cloud) is explicitly out of scope for
this spec. The zero-change plan can be verified locally without a shared remote backend.

**Local state implications**:
- Each developer must run `terraform init` and re-import resources to validate independently (or
  share the state file out-of-band — not recommended).
- The `.gitignore` exclusion prevents accidental state commits containing sensitive resource
  identifiers.

**Migration path (future spec)**:
```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "AI-103-Study-Lab"
    storage_account_name = "<future-tfstate-storage>"
    container_name       = "tfstate"
    key                  = "agentic-data-foundation.tfstate"
  }
}
```

**Alternatives Considered**:
- Azure Storage backend from the start — rejected: out of scope per Assumption 4; requires
  creating a new storage resource (out of spec's non-destructive constraint).
- Terraform Cloud backend — rejected: requires external account setup; deferred.

---

## R-006: Post-Export File Organization

**Decision**: After aztfexport generates per-resource `.tf` files, reorganize into 4 domain-grouped
files: `resource_group.tf`, `ai_foundry.tf`, `cosmos_db.tf`, `sql.tf`.

**Rationale**: aztfexport generates one file per resource (e.g., `azurerm_cosmosdb_account.tf`,
`azurerm_cosmosdb_sql_database.tf`). For 8 resources, this produces 8 `.tf` files that are harder
to navigate than a logically grouped layout. SC-006 requires that a developer can understand all
resource relationships from the configuration alone — logical grouping serves this goal better.

**Grouping**:
- `resource_group.tf` — `azurerm_resource_group` (1 resource)
- `ai_foundry.tf` — AI Hub + AI Project (2 resources; co-located because they have a parent/child
  dependency that must be expressed as a reference)
- `cosmos_db.tf` — Cosmos DB account + SQL database + SQL container (3 resources; hierarchically
  dependent)
- `sql.tf` — SQL server + SQL database (2 resources; hierarchically dependent)

**Process**:
1. Run aztfexport — accept generated per-resource files.
2. Run `terraform fmt` on generated output.
3. Run `terraform validate` to confirm structural correctness.
4. Run `terraform plan` to confirm zero changes.
5. If plan is zero-change, reorganize into domain files (copy+paste, delete originals).
6. Re-run `terraform fmt`, `terraform validate`, `terraform plan` to confirm reorganization was lossless.

**Alternatives Considered**:
- Single `resources.tf` — too flat; hides relationships.
- Keep per-resource files as aztfexport generates — acceptable for initial output but harder to
  read; rejected for the committed result.
- Separate directory per resource type — over-engineered for 8 resources.

---

## R-007: Variables and Outputs Scope

**Decision**: Parameterize only non-sensitive resource identifiers (subscription_id, tenant_id,
location). Resource names are hardcoded as they are fixed identifiers for this environment.
Outputs expose resource IDs and primary endpoints for reference.

**Rationale**: The Terraform configuration is a capture of a specific, named environment — not a
reusable module. Parameterizing resource names would falsely imply this configuration deploys to
different environments. Only subscription and tenant identifiers vary by developer workstation and
belong in variables.

**Variables declared**:
- `subscription_id` — Azure subscription identifier (supplied via tfvars or ARM_SUBSCRIPTION_ID)
- `tenant_id` — Azure Active Directory tenant identifier
- `location` — Azure region (e.g., `eastus`) — fixed for this environment but declared for
  documentation clarity

**Outputs declared** (reference values, not secrets):
- Cosmos DB account endpoint
- SQL server FQDN
- Resource group ID
- AI Hub resource ID
- AI Project resource ID

**Alternatives Considered**:
- Parameterize all resource names — rejected: makes the configuration look like a reusable module,
  which it is not; the names are invariants for this captured environment.
- No outputs at all — rejected: outputs document the resulting resource identifiers, serving SC-006.
