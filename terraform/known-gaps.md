# Known Gaps: Azure Infrastructure as Code

This document records every export limitation, provider constraint, or manually handled
property discovered during the aztfexport capture of the Agentic Data Foundation Azure
infrastructure. Each entry describes what the gap is, how it was handled, and its
verification status against the zero-change plan.

---

## Gap 1: Azure AI Foundry Resource Type Mapping

**Resource**: `ai-brain-openai` (Azure AI Hub) and `proj-default` (Azure AI Project)

**Gap**: The Azure AI Foundry hub (`Microsoft.CognitiveServices/accounts` with kind "AIServices")
is not exported as `azurerm_ai_foundry` or `azurerm_ai_foundry_project` (newer resource types
added in azurerm v4.x). Instead, aztfexport v0.20.0 with azurerm provider v4.80.0 maps them to:
- Hub → `azurerm_cognitive_account` (kind = "AIServices")
- Project → `azurerm_cognitive_account_project`

These are the correct functional resource types for the installed provider version. The newer
`azurerm_ai_foundry` and `azurerm_ai_foundry_project` resource types were not used because
aztfexport maps resources based on the provider schema it knows.

**Manual representation**: None required — aztfexport generated the correct representation
using the available resource types. The configuration is functionally complete.

**Verification status**: VERIFIED — zero-change plan confirmed on 2026-08-10 (`terraform plan -detailed-exitcode` exit 0, "No changes."). The `azurerm_cognitive_account` representation is functionally accurate for the installed provider version.

---

## Gap 2: RAI Content Policies Not Importable

**Resource**: `ai-brain-openai/raiPolicies/Microsoft.Default` and `ai-brain-openai/raiPolicies/Microsoft.DefaultV2`

**Gap**: The `azurerm_cognitive_account_rai_policy` resource type was discovered by aztfexport
(Microsoft.CognitiveServices/accounts/raiPolicies), but the Terraform provider reported
"Cannot import non-existent remote object" when attempting to import these resources. These
are system-managed default Responsible AI policies that cannot be independently imported or
managed via Terraform.

**Manual representation**: Excluded from the configuration entirely. These policies are
system-managed defaults that Azure creates and manages automatically. Attempting to manage them
via Terraform would cause errors.

**Verification status**: EXCLUDED — not included in the configuration; therefore no planned
changes for these resources. This is correct behavior.

---

## Gap 3: SQL Server Vulnerability Assessment — Cannot Be Managed by Terraform

**Resource**: `Microsoft.Sql/servers/sql-agentic-joel-dev/vulnerabilityAssessments/Default`

**Gap**: The `azurerm_mssql_server_vulnerability_assessment` resource requires a non-empty
`storage_container_path` attribute (provider validation error: "expected storage_container_path
to not be an empty string"). The live Azure resource has no storage container configured —
confirmed via ARM REST API: the `properties` object contains only `recurringScans`, with no
`storageContainerPath`. The provider schema and the live configuration are irreconcilable.

**Manual representation**: This resource has been **excluded** from the Terraform configuration
entirely. It was imported into state during Phase 4, then removed from state with
`terraform state rm` after the validation failure was confirmed. The vulnerability assessment
resource continues to exist in Azure and is unaffected by this exclusion.

**Verification status**: EXCLUDED — removed from both configuration and state due to provider
validation constraint. The live resource remains unchanged. No planned changes for this
resource (it is not managed by Terraform).

---

## Gap 4: SQL Server — No administrator_login_password in Configuration

**Resource**: `azurerm_mssql_server.res-25`

**Gap**: The `administrator_login` is captured (`CloudSA1c02efbc`), but `administrator_login_password`
is absent from the configuration. This is correct because `azuread_authentication_only = true`
is set in the `azuread_administrator` block, meaning SQL password authentication is disabled.
The Terraform provider does not require `administrator_login_password` when Azure AD-only
authentication is configured.

**Manual representation**: No manual representation needed — the generated configuration is
correct as-is. No password is in the configuration, which is both correct and secure.

**Verification status**: VERIFIED — zero-change plan confirmed on 2026-08-10. Azure AD-only authentication is correctly represented without a password attribute.

---

## Final Verification

- **Validation date**: 2026-08-10
- **Terraform version**: v1.15.8
- **aztfexport version**: v0.20.0
- **azurerm provider version**: 4.80.0
- **Final plan result**: `No changes. Your infrastructure matches the configuration.` (`terraform plan -detailed-exitcode` exit code 0)
- **Resources in state**: 19 (all application-owned resources except the unmanageable vulnerability assessment)
- **SC-002 acceptance gate**: PASSED
