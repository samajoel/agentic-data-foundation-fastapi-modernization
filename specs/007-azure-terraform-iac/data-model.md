# Data Model: Azure Infrastructure as Code

**Feature**: `specs/007-azure-terraform-iac/spec.md`
**Date**: 2026-08-10
**Phase**: 1 — Design

This document maps the spec entities to their Terraform configuration representations. Each entity
becomes one or more HCL resource blocks in the Terraform project. The "data model" here is the
shape of the Terraform configuration objects — their arguments, attribute references, and dependency
relationships.

---

## Entity Map

### Resource Group

**Spec entity**: Resource Group (`AI-103-Study-Lab`)
**Terraform resource type**: `azurerm_resource_group`
**Logical file**: `resource_group.tf`
**Parent**: None (root entity)

**Key attributes**:
- `name` — `"AI-103-Study-Lab"` (hardcoded; fixed identifier)
- `location` — `var.location` (e.g., `"eastus"`)

**Dependencies**: None. All other resources depend on this via `resource_group_name`.

**Known gap risk**: Low. `azurerm_resource_group` is a stable, well-supported resource type.

---

### Azure AI Hub

**Spec entity**: Azure AI Hub (`ai-brain-openai`)
**Terraform resource type**: `azurerm_ai_foundry` OR `azurerm_machine_learning_workspace`
(determined by aztfexport; see Research R-002)
**Logical file**: `ai_foundry.tf`
**Parent**: Resource Group

**Key attributes** (if `azurerm_ai_foundry`):
- `name` — `"ai-brain-openai"`
- `resource_group_name` — `azurerm_resource_group.rg.name`
- `location` — `var.location`
- `storage_account_id`, `key_vault_id`, `application_insights_id` — dependency references (may
  reference resources not owned by this application; treat as `data` sources if not in config)

**Known gap risk**: HIGH. The `azurerm_ai_foundry` type is newer; aztfexport may generate
`azurerm_machine_learning_workspace` or may not export all properties. Cross-resource dependencies
(storage, key vault, app insights) may reference shared resources not captured in this config —
these become `data` source references (read-only lookups, not managed resources).

---

### Azure AI Project

**Spec entity**: Azure AI Project (`proj-default`)
**Terraform resource type**: `azurerm_ai_foundry_project` OR nested within workspace
(determined by aztfexport)
**Logical file**: `ai_foundry.tf`
**Parent**: Azure AI Hub

**Key attributes** (if `azurerm_ai_foundry_project`):
- `name` — `"proj-default"`
- `ai_services_hub_id` — reference to AI Hub resource

**Known gap risk**: HIGH. Parent/child relationship between hub and project must be expressed
correctly. If aztfexport cannot represent this relationship, a manual representation must be
verified against the zero-change plan.

---

### Cosmos DB Account

**Spec entity**: Cosmos DB Account (`cosmos-agentic-joel-dev`)
**Terraform resource type**: `azurerm_cosmosdb_account`
**Logical file**: `cosmos_db.tf`
**Parent**: Resource Group

**Key attributes**:
- `name` — `"cosmos-agentic-joel-dev"`
- `resource_group_name` — `azurerm_resource_group.rg.name`
- `location` — `var.location`
- `offer_type` — `"Standard"`
- `kind` — `"GlobalDocumentDB"` (for SQL API)
- `consistency_policy` block — session, bounded staleness, or eventual; actual value from live env
- `geo_location` block — primary location and failover regions
- `capabilities` block — `EnableServerless` (indicated by Bicep template: `EnableServerless`)

**Known gap risk**: LOW. `azurerm_cosmosdb_account` is a mature, well-supported resource.
Serverless capability, consistency policy, and geo-location must be exported accurately.

---

### Cosmos DB SQL Database

**Spec entity**: Cosmos DB SQL Database (`chat-history`)
**Terraform resource type**: `azurerm_cosmosdb_sql_database`
**Logical file**: `cosmos_db.tf`
**Parent**: Cosmos DB Account

**Key attributes**:
- `name` — `"chat-history"`
- `resource_group_name` — `azurerm_resource_group.rg.name`
- `account_name` — `azurerm_cosmosdb_account.cosmos.name`

**Note**: The Bicep template uses database name `db_conversation_history` — the live environment
may use `chat-history` as confirmed by the spec. The live environment name governs.

**Known gap risk**: LOW.

---

### Cosmos DB SQL Container

**Spec entity**: Cosmos DB SQL Container (`conversations`)
**Terraform resource type**: `azurerm_cosmosdb_sql_container`
**Logical file**: `cosmos_db.tf`
**Parent**: Cosmos DB SQL Database

**Key attributes**:
- `name` — `"conversations"`
- `resource_group_name` — `azurerm_resource_group.rg.name`
- `account_name` — `azurerm_cosmosdb_account.cosmos.name`
- `database_name` — `azurerm_cosmosdb_sql_database.chat_history.name`
- `partition_key_paths` — `["/userId"]` (application-defined; verify against live env)
- `throughput` — omitted for serverless accounts (serverless does not use provisioned throughput)
- `indexing_policy` block — automatic indexing; verify against live env

**Known gap risk**: MEDIUM. Partition key path and indexing policy must match exactly for zero
planned changes. If the account uses serverless capacity mode, throughput is not a property —
omit the `throughput` argument entirely.

---

### Azure SQL Server

**Spec entity**: Azure SQL Server (`sql-agentic-joel-dev`)
**Terraform resource type**: `azurerm_mssql_server`
**Logical file**: `sql.tf`
**Parent**: Resource Group

**Key attributes**:
- `name` — `"sql-agentic-joel-dev"`
- `resource_group_name` — `azurerm_resource_group.rg.name`
- `location` — `var.location`
- `version` — `"12.0"` (standard Azure SQL Server version string)
- `administrator_login` — value from live environment (sensitive; do not hardcode; managed via
  Azure AD / Microsoft Entra admin or placeholder if not applicable)
- `azuread_administrator` block — if Azure AD admin is configured on the live server

**Known gap risk**: MEDIUM. Administrator credentials are sensitive; if the server uses Azure AD
admin only, the `administrator_login` / `administrator_login_password` may be set to placeholder
values in the Terraform config (the live environment accepts them without change since the
password is managed separately). This must be verified in the zero-change plan.

---

### Azure SQL Database

**Spec entity**: Azure SQL Database (`agentic-data-db`)
**Terraform resource type**: `azurerm_mssql_database`
**Logical file**: `sql.tf`
**Parent**: Azure SQL Server

**Key attributes**:
- `name` — `"agentic-data-db"`
- `server_id` — `azurerm_mssql_server.sql.id`
- `sku_name` — matches live environment (e.g., `"GP_S_Gen5_2"` as indicated by Bicep template)
- `collation` — verify against live environment
- `max_size_gb` — verify against live environment

**Known gap risk**: LOW. `azurerm_mssql_database` is a stable, well-supported resource.

---

## Resource Dependency Graph

```
azurerm_resource_group.rg
├── azurerm_ai_foundry.hub (or azurerm_machine_learning_workspace.hub)
│   └── azurerm_ai_foundry_project.project (or sub-resource)
├── azurerm_cosmosdb_account.cosmos
│   └── azurerm_cosmosdb_sql_database.chat_history
│       └── azurerm_cosmosdb_sql_container.conversations
└── azurerm_mssql_server.sql
    └── azurerm_mssql_database.agentic_data_db
```

**Cross-resource dependencies** (read via `data` sources, not managed):
- AI Hub references: storage account, key vault, application insights (shared resources not in
  scope of this spec; referenced via `data "azurerm_storage_account"` etc. if aztfexport includes
  them, or via hardcoded IDs if not)

---

## Infrastructure State Entity

**Not a Terraform resource** — the Terraform state file (`terraform.tfstate`) is the runtime
artifact that maps configuration declarations to live Azure resource identifiers. It is excluded
from version control (`.gitignore`). Each developer maintains their own local state file produced
by `terraform init` + state population.

---

## Known Gap Entity

**Not a Terraform resource** — documented in `terraform/known-gaps.md`. Format:

```markdown
## Known Gap: <resource name>

- **Resource**: <Terraform resource type and name>
- **Gap**: <What property or relationship aztfexport could not represent>
- **Manual representation**: <What was written manually to fill the gap>
- **Verification**: <Output of terraform plan for this resource — expected: zero changes>
- **Status**: VERIFIED | UNVERIFIED
```
