# Quickstart: Azure Infrastructure as Code

**Feature**: `specs/007-azure-terraform-iac/spec.md`
**Date**: 2026-08-10

This document describes how to validate that the Terraform configuration accurately represents the
live Azure environment. These are the end-to-end validation scenarios that prove the feature works.

---

## Prerequisites

1. **Azure CLI** installed and authenticated:
   ```bash
   az login
   az account set --subscription <YOUR_SUBSCRIPTION_ID>
   az account show  # confirm the correct subscription is active
   ```

2. **Terraform CLI** installed:
   ```bash
   terraform version  # confirms CLI is available
   ```

3. **aztfexport** installed:
   ```bash
   aztfexport version  # confirms aztfexport is available
   ```

4. **Repository cloned** and the `terraform/` directory exists (created during implementation).

5. **`terraform.tfvars` created** from the example (never committed):
   ```bash
   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
   # Edit terraform.tfvars to supply your subscription_id and tenant_id
   ```

---

## Validation Scenario V-001: Terraform Initializes Successfully

**Purpose**: Confirm the Terraform project is structurally valid and provider plugins download.

**Command**:
```bash
cd terraform
terraform init
```

**Expected outcome**:
- Terraform downloads the `azurerm` provider.
- Prints: `Terraform has been successfully initialized!`
- No errors.

---

## Validation Scenario V-002: Structural Validation Passes

**Purpose**: Confirm all HCL syntax is valid and resource references resolve.

**Command**:
```bash
cd terraform
terraform validate
```

**Expected outcome**:
- `Success! The configuration is valid.`
- Exit code 0.
- No warnings about deprecated attributes or missing required arguments.

---

## Validation Scenario V-003: Zero Planned Changes for All 8 Resources

**Purpose**: Confirm the captured configuration exactly matches the live Azure environment. This is
the primary acceptance gate (SC-002).

**Command**:
```bash
cd terraform
terraform plan -detailed-exitcode
```

**Expected outcome**:
- All 8 resources appear as: `# <resource_type>.<name> will be read during apply` (for data sources)
  or `No changes. Your infrastructure matches the configuration.`
- Exit code 0 (or exit code 2 if plan has changes — that is a FAIL).
- Zero additions, zero modifications, zero destructions, zero replacements.
- The final plan summary line reads: `Plan: 0 to add, 0 to change, 0 to destroy.`

**Interpreting the output**:
- `+ resource` — FAIL: resource will be created (not in live environment or not captured)
- `~ resource` — FAIL: resource will be modified (captured config does not match live state)
- `- resource` — FAIL: resource will be deleted (in config but not found in live environment)
- `# will be replaced (forces replacement)` — FAIL: blocking; must resolve before accepting

---

## Validation Scenario V-004: Configuration Is Consistently Formatted

**Purpose**: Confirm the Terraform configuration follows standard formatting conventions.

**Command**:
```bash
cd terraform
terraform fmt -check -recursive
```

**Expected outcome**:
- No output and exit code 0 (meaning all files are already formatted).
- If files need formatting: `terraform fmt` (without `-check`) will reformat them; re-run to confirm.

---

## Validation Scenario V-005: All 8 Resources Appear in the Configuration

**Purpose**: Confirm SC-001 — every confirmed resource has a named declaration. (Manual inspection)

**How to verify**:
```bash
cd terraform
grep -r "azurerm_resource_group\|azurerm_cosmosdb_account\|azurerm_cosmosdb_sql_database\|azurerm_cosmosdb_sql_container\|azurerm_mssql_server\|azurerm_mssql_database" *.tf | grep "^[^#]*resource\s"
grep -r "azurerm_ai_foundry\|azurerm_machine_learning_workspace" *.tf | grep "^[^#]*resource\s"
```

**Expected outcome**: Each of the 8 confirmed resources has exactly one `resource` block with a
recognizable name in the configuration files.

---

## Validation Scenario V-006: No Secrets Appear in Committed Files

**Purpose**: Confirm SC-004 — zero credentials, access keys, or connection strings in committed files.

**How to verify**:
```bash
# From repo root — scan committed Terraform files
git ls-files terraform/ | xargs grep -iE "AccountKey=|SharedAccessKey|password\s*=\s*\".+\"|client_secret\s*=\s*\".+\"" 2>/dev/null
```

**Expected outcome**: No output (zero matches).

Also verify:
```bash
git ls-files terraform/ | grep -E "\.tfstate|\.terraform/"
```
**Expected outcome**: No output (state files and provider cache not tracked).

---

## Validation Scenario V-007: Known Gaps Are Documented

**Purpose**: Confirm SC-005 — export gaps are documented with manual workarounds.

**How to verify**:
1. Open `terraform/known-gaps.md`.
2. Confirm each resource that could not be automatically exported appears with:
   - A description of the gap
   - The manual representation written to fill the gap
   - A "Status: VERIFIED" line (meaning the zero-change plan confirmed the manual representation)

**Expected outcome**: If no gaps, `known-gaps.md` states: `No known gaps identified for this
capture. All 8 resources were exported automatically and validated.`

---

## Validation Scenario V-008: Developer Readability (SC-006)

**Purpose**: Confirm a developer unfamiliar with the Azure environment can identify all resources
from the configuration and documentation alone.

**How to verify** (manual):
1. Open `terraform/known-gaps.md` and each `*.tf` file.
2. Without Azure portal access, answer: "What are the 8 application resources, their types, and
   how do they relate to each other?"
3. The answer should be derivable from the configuration + `known-gaps.md` + the `outputs.tf` values.

**Expected outcome**: All 8 resource names, types, and relationships are readable from the committed
configuration files.

---

## Re-running Validation After Changes

If the live Azure environment changes and you need to re-validate:

```bash
cd terraform
terraform plan -detailed-exitcode
```

- Exit code 0: no changes detected — configuration still accurate.
- Exit code 2: changes detected — update the Terraform configuration to match, then re-run until
  exit code is 0 or document the drift in `known-gaps.md`.
- Exit code 1: Terraform encountered an error — check Azure CLI authentication and resource
  accessibility.

---

## References

- `specs/007-azure-terraform-iac/data-model.md` — Terraform resource types and dependency graph
- `specs/007-azure-terraform-iac/research.md` — Key planning decisions (aztfexport approach,
  secret handling, file organization)
- `specs/007-azure-terraform-iac/spec.md` — Functional requirements and success criteria
