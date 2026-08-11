# Feature Specification: Azure Infrastructure as Code

**Feature Branch**: `007-azure-terraform-iac`

**Created**: 2026-08-10

**Status**: Draft

**Input**: User description — Capture the existing Azure infrastructure used by the Agentic Data Foundation application as version-controlled, declarative infrastructure configuration, using export tooling where available to derive configuration from the live environment rather than designing it from scratch.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Application Infrastructure Is Version-Controlled and Readable (Priority: P1)

A platform engineer or developer wants a single, authoritative, version-controlled record of every Azure resource that belongs to the Agentic Data Foundation application, so they can understand the full infrastructure inventory without logging into the Azure portal or reading undocumented scripts. The record should be declarative — describing what exists rather than how to create it — and should be reviewable as code.

**Why this priority**: Without a version-controlled infrastructure record, the application's environment is undocumented. Any team member must manually inspect the portal, and there is no baseline to detect changes. This is the foundational deliverable that all subsequent infrastructure management depends on.

**Independent Test**: Open the infrastructure configuration files and confirm that every one of the eight confirmed application resources appears as a named declaration. A developer unfamiliar with the environment should be able to name all resources and understand their relationships from the configuration and its documentation alone, without consulting the Azure portal.

**Acceptance Scenarios**:

1. **Given** the completed infrastructure configuration, **When** a developer reads it, **Then** they can identify all eight confirmed application resources by name and understand how they relate to each other.
2. **Given** a new team member with access to the repository, **When** they read the configuration, **Then** they can answer the question "what Azure resources does this application use?" without any Azure portal access.
3. **Given** the infrastructure configuration, **When** it is reviewed, **Then** no resources from the shared resource group that are not confirmed to belong to this application are included.

---

### User Story 2 — Infrastructure Configuration Validates Against Live Environment with No Changes (Priority: P2)

A platform engineer wants to compare the version-controlled infrastructure configuration against the live Azure environment and confirm that the configuration accurately describes what exists — producing a comparison report that shows zero intended infrastructure changes for the captured resources.

**Why this priority**: A configuration file that describes infrastructure is only valuable if it accurately reflects reality. The comparison step is the proof that the captured configuration is correct and that no accidental modification is embedded in it.

**Independent Test**: Run an infrastructure comparison against the live Azure environment for the eight captured resources. The resulting plan shows zero resource additions, zero resource modifications, and zero resource deletions for those resources.

**Acceptance Scenarios**:

1. **Given** the captured infrastructure configuration and live Azure credentials, **When** an infrastructure comparison is run, **Then** the comparison reports zero planned changes to the eight confirmed application resources.
2. **Given** the captured infrastructure configuration, **When** the configuration is validated for structural correctness, **Then** zero errors are reported.
3. **Given** any resource or property that the export tooling could not automatically represent, **When** the comparison is run, **Then** the manual representation of that resource also produces no planned changes.

---

### User Story 3 — Sensitive Values Are Excluded from Version Control (Priority: P3)

A platform engineer wants to ensure that no credentials, connection strings, access keys, or secrets are committed to the repository as part of the infrastructure configuration, so the Terraform project can be reviewed, shared, and stored in version control without risk of credential exposure.

**Why this priority**: Infrastructure-as-code projects commonly leak secrets when sensitive values are embedded in configuration files. Preventing this from the start is far less costly than remediating a credential exposure after the fact.

**Independent Test**: Inspect all committed infrastructure configuration files. Confirm zero hardcoded secrets, connection strings, or access keys appear in any committed file. Confirm that any values referencing credentials are parameterized through a mechanism that is excluded from version control.

**Acceptance Scenarios**:

1. **Given** all committed infrastructure configuration files, **When** they are inspected for secrets, **Then** zero connection strings, access keys, passwords, or credentials appear in plain text.
2. **Given** the infrastructure project, **When** sensitive values are needed for local validation, **Then** they are supplied through a mechanism (such as environment variables or a local-only secrets file) that is explicitly excluded from version control.
3. **Given** the committed configuration, **When** the version control history is scanned for secrets, **Then** no credentials have been committed at any point.

---

### Edge Cases

- What happens if the export tool cannot automatically represent a resource property (e.g., a managed identity reference, a SKU restriction, or a lifecycle attribute)? The property must be documented as a known gap, and a manual representation must be written and verified by the comparison step.
- What happens if resources exist in the resource group that are not owned by this application? They must be excluded from the configuration; the boundary of "application-owned resources" is the eight confirmed resources listed in this spec.
- What happens if the comparison step discovers that the live environment has drifted from what was exported (i.e., the export produced a configuration that no longer matches reality)? This is a finding that must be documented; the configuration must be corrected until the comparison shows zero changes.
- What happens if the Terraform state file is lost or corrupted? The spec assumes the state will be stored using a durable backend; local-only state is acceptable for initial validation but must be migrated before the configuration is treated as authoritative.
- What happens if a resource that is part of the export requires a destructive replacement to reconcile with the plan? This is a blocking issue: no resource may be scheduled for replacement, recreation, or deletion as a result of the captured configuration. The configuration must be corrected before the comparison can be accepted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All eight confirmed application-owned Azure resources MUST be represented in the infrastructure configuration: the resource group, the Azure AI hub, the Azure AI project, the Cosmos DB account, the Cosmos DB SQL database, the Cosmos DB SQL container, the Azure SQL server, and the Azure SQL database.
- **FR-002**: Resources in the resource group that are not confirmed to belong to this application MUST NOT be included in the infrastructure configuration.
- **FR-003**: The infrastructure comparison against the live Azure environment MUST produce zero planned additions, modifications, or deletions for all eight captured resources.
- **FR-004**: No destructive operation (replacement, recreation, deletion) MUST appear in the comparison plan for any captured resource.
- **FR-005**: The infrastructure configuration MUST pass structural validation with zero errors before the comparison step is run.
- **FR-006**: Sensitive values — including but not limited to connection strings, access keys, passwords, and secrets — MUST NOT appear in any committed infrastructure configuration file.
- **FR-007**: Sensitive values required for local validation MUST be supplied through a mechanism (environment variables, local-only file) that is excluded from version control by the project's ignore configuration.
- **FR-008**: Any resource or property that the export tooling cannot automatically represent MUST be documented as a known gap, along with a manually written representation that satisfies FR-003.
- **FR-009**: The infrastructure project MUST document the relationships and dependencies between the eight captured resources.
- **FR-010**: The Terraform state file MUST NOT be committed to version control.
- **FR-011**: The infrastructure configuration MUST be formatted consistently using standard formatting tooling before being committed.
- **FR-012**: A comparison between the infrastructure configuration/state and the live Azure environment MUST be producible on demand by any team member with the appropriate Azure credentials.

### Key Entities

- **Resource Group** (`AI-103-Study-Lab`): The organizational boundary for all application Azure resources. Acts as the parent container for all other entities below.
- **Azure AI Hub** (`ai-brain-openai`): The Azure AI Foundry workspace resource. Parent of the Azure AI project.
- **Azure AI Project** (`proj-default`): The AI project within the hub. Hosts the agent definitions and model deployments used by the application.
- **Cosmos DB Account** (`cosmos-agentic-joel-dev`): The NoSQL database account that manages the chat history storage in workshop mode.
- **Cosmos DB SQL Database** (`chat-history`): The logical database within the Cosmos DB account that holds chat history data.
- **Cosmos DB SQL Container** (`conversations`): The collection within the SQL database where individual conversation records are stored. Partition key and throughput settings are properties of this entity.
- **Azure SQL Server** (`sql-agentic-joel-dev`): The relational database server used for Fabric SQL / non-workshop history mode.
- **Azure SQL Database** (`agentic-data-db`): The relational database on the Azure SQL server used for structured data access.
- **Infrastructure Configuration**: The set of version-controlled declarative files that describe the eight resources above, their properties, and their relationships.
- **Infrastructure State**: The file that records the mapping between infrastructure configuration declarations and live Azure resource identifiers.
- **Known Gap**: A resource or property that the export tooling cannot automatically represent, documented with a manual workaround and verified by the comparison step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All eight confirmed application resources appear as named declarations in the version-controlled infrastructure configuration.
- **SC-002**: The infrastructure comparison against the live Azure environment reports zero planned changes (zero additions, zero modifications, zero deletions, zero replacements) for all eight captured resources.
- **SC-003**: The infrastructure configuration passes structural validation with zero errors.
- **SC-004**: Zero secrets, connection strings, access keys, or credentials appear in any committed infrastructure configuration file, as verified by inspection of all committed files.
- **SC-005**: All known export gaps (resources or properties that could not be automatically exported) are documented with their manual workaround and verified to produce no planned changes.
- **SC-006**: A developer with no prior knowledge of the Azure environment can identify all eight resources, their purpose, and their relationships from the infrastructure configuration and its documentation alone — without Azure portal access.

## Assumptions

- The eight resources listed in the feature description are the complete set of application-owned resources to be captured by this spec. Additional resources may be added by a subsequent spec if they are confirmed to belong to the application.
- The resource group `AI-103-Study-Lab` is shared; it contains resources that are not owned by this application and must not be included in the configuration.
- The initial capture is non-destructive: the workflow does not create, modify, or delete any Azure resource as part of this spec. The comparison step produces a plan that is reviewed but not applied.
- The infrastructure state will initially be stored locally during the capture and validation phase. Migration to a remote state backend is out of scope for this spec and belongs to subsequent work.
- Azure CLI authentication is assumed to be available in the environment where the export and comparison steps are run. No new service principals, managed identities, or role assignments are created by this spec.
- The Azure AI Foundry hub and project are standard Azure resources that may have properties not fully supported by the current version of the Azure Terraform provider; such gaps will be treated as known gaps per FR-008.
- The Cosmos DB partition key and throughput settings for the `conversations` container are properties that must be captured; if the export tool cannot represent them, they are treated as known gaps.
- The `VIZ-LINE-02` issue is explicitly out of scope. No application code changes, production deployment steps, or CI/CD pipeline work are included in this spec.
