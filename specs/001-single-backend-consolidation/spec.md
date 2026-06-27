# Feature Specification: Single Backend Consolidation

**Feature Branch**: `001-single-backend-consolidation`

**Created**: 2026-06-27

**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Frontend Continues to Work After Consolidation (Priority: P1)

A user (sales analyst or account manager) opens the chat interface, submits a natural-language question, and receives an AI-generated answer drawn from Fabric-connected enterprise data. The user can also retrieve past conversation history. Both workflows are fully functional after the backend consolidation; the user experience is unchanged.

**Why this priority**: Preserving the end-user experience is the non-negotiable baseline for this consolidation. Any regression here makes the work a failure regardless of what was removed.

**Independent Test**: Open the React frontend against a deployment that runs only the Python FastAPI backend. Submit a chat message and confirm a valid response is received. Navigate to conversation history and confirm prior messages appear.

**Acceptance Scenarios**:

1. **Given** a deployed instance backed only by the Python FastAPI service, **When** a user submits a chat message through the frontend, **Then** a valid response is returned and the conversation is persisted to history.
2. **Given** a deployed instance backed only by the Python FastAPI service, **When** a user opens the history view, **Then** past conversations are displayed correctly and completely.

---

### User Story 2 - Repository Contains a Single Backend Runtime (Priority: P2)

A developer or contributor cloning the repository finds exactly one deployable backend: the Python FastAPI application. No .NET backend source code, project files, solution files, or .NET-specific container and build configuration exist anywhere in the repository tree.

**Why this priority**: Eliminating the .NET backend is the primary goal of this spec. Backend runtime ambiguity is the problem being solved.

**Independent Test**: Clone the repository and search for .NET project files, solution files, and .NET Docker assets. Zero results confirm the criterion is met.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the consolidated repository, **When** a developer searches for .NET backend artifacts, **Then** none are found in the repository.
2. **Given** the consolidated repository, **When** a developer reads the deployment documentation, **Then** only the Python FastAPI backend is described as a deployable runtime.

---

### User Story 3 - One Supported Architecture Path: Fabric and Foundry (Priority: P3)

A deployment engineer following the project documentation can deploy the solution using one architecture path: Microsoft Fabric and Microsoft Foundry. There are no Copilot Studio or Microsoft Teams deployment steps, documentation sections, or configuration files to navigate or skip.

**Why this priority**: Removing the alternative architecture path eliminates confusion about what is supported in this fork and shrinks the maintenance surface.

**Independent Test**: Read all deployment documentation from start to finish. Confirm no Copilot Studio or Teams deployment steps, screenshots, or configuration references appear.

**Acceptance Scenarios**:

1. **Given** the updated deployment documentation, **When** a deployment engineer follows the guide end-to-end, **Then** the guide describes only the Fabric and Foundry architecture path.
2. **Given** the consolidated repository, **When** a contributor searches for Copilot Studio or Teams deployment configuration or documentation, **Then** no such artifacts are present.

---

### Edge Cases

- What if some infrastructure files reference both backends? Each such file must be updated or removed so only the Python FastAPI runtime is referenced.
- What if Copilot Studio documentation is embedded in sections that also contain Fabric and Foundry content? Only the Copilot Studio–specific portions are removed; shared content remains.
- What if test configuration references the .NET backend? All test fixtures, CI configuration, and environment files must be updated to reference only the Python FastAPI backend.

## Requirements

### Functional Requirements

- **FR-001**: The Python FastAPI backend MUST serve `POST /chat` with behavior identical to the current implementation.
- **FR-002**: The Python FastAPI backend MUST serve `GET /history` with behavior identical to the current implementation.
- **FR-003**: All .NET backend source code, project files, solution files, and .NET-specific Docker and build configuration MUST be removed from the repository.
- **FR-004**: Deployment infrastructure configuration MUST NOT reference the .NET backend runtime after consolidation.
- **FR-005**: The React frontend MUST continue to function without any modification to its source code or build configuration.
- **FR-006**: The repository MUST support only the Microsoft Fabric and Microsoft Foundry deployment architecture after consolidation.
- **FR-007**: Documentation and configuration artifacts specific to Copilot Studio and Microsoft Teams deployment paths MUST be removed from this fork.
- **FR-008**: No new backend runtime, framework, or alternative architecture path MUST be introduced by this consolidation.

### Key Entities

- **Active backend**: The Python FastAPI application at `src/api/python/`, which owns `POST /chat` and `GET /history`.
- **Retired backend**: The .NET application at `src/api/dotnet/`, to be fully removed.
- **External API contract**: The endpoints `POST /chat` and `GET /history` consumed by the React frontend. These are stable and must not change.
- **Supported architecture**: Microsoft Fabric and Microsoft Foundry — the only deployment architecture in scope for this fork.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing frontend chat and history workflows pass end-to-end acceptance testing against the Python FastAPI backend without the .NET backend present.
- **SC-002**: Zero .NET backend files (source, project, build, or container configuration) remain in the repository after consolidation.
- **SC-003**: A new contributor can reach a working deployment by following a single, unambiguous architecture path documented in the repository.
- **SC-004**: The deployment documentation contains no references to Copilot Studio or Microsoft Teams deployment steps or configuration.
- **SC-005**: The `POST /chat` and `GET /history` endpoints return responses identical in structure and behavior to those served before consolidation.

## Assumptions

- The React frontend calls only `POST /chat` and `GET /history` and has no direct dependency on the .NET backend.
- No active production environment in this fork depends on the .NET backend runtime at the time of consolidation.
- The Copilot Studio and Teams deployment paths in the upstream Microsoft repository are not in use in this fork and carry no active user dependency.
- The Azure deployment infrastructure in `infra/` already targets the Python FastAPI container; any .NET references there are vestigial.
- The Python FastAPI backend is fully functional and passes existing tests before this consolidation begins.
