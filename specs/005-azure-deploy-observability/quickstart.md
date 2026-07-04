# Quickstart: Azure Deployment and Observability Validation

**Feature**: Azure Deployment and Observability Validation
**Date**: 2026-07-03

This guide documents how to validate deployment artifacts locally and provides the complete environment variable registry for configuring the Python FastAPI backend.

---

## Prerequisites

- Python 3.11 virtual environment at `src/api/python/.venv/`
- Repo cloned and `cd` to repo root
- No live Azure resources required for local validation (V-001 through V-006, V-008 through V-010, V-012 through V-015)
- A running local backend process is required only for V-007 and V-011

---

## Validation Scenarios

### US1: Deployment Compatibility

**V-001 — Application shim imports cleanly**
```bash
cd /path/to/repo
.venv/bin/python3 -c "import sys; sys.path.insert(0,'src/api/python'); import app; print(type(app.app))"
# Expected: <class 'fastapi.applications.FastAPI'>
```

**V-002 — Dockerfile CMD targets `app:app`**
```bash
grep "^CMD" src/api/python/ApiApp.Dockerfile
# Expected: CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
```

**V-003 — No .NET references in deployment scripts**
```bash
grep -rn "dotnet\|api/dotnet" \
  infra/scripts/docker-build.sh \
  infra/scripts/docker-build.ps1 \
  src/start.sh \
  azure.yaml
# Expected: no output (zero matches)
```

**V-004 — App Service startup targets `app:app`**
```bash
grep "appCommandLine" infra/deploy_backend_custom.bicep
# Expected line contains: uvicorn app:app
```

**V-005 — App Service runtime is Python 3.11**
```bash
grep "linuxFxVersion" infra/deploy_backend_custom.bicep
# Expected: 'PYTHON|3.11'
```

**V-006 — `start.sh` runs Python backend**
```bash
grep "python app.py" src/start.sh
# Expected: match on the backend start line
```

---

### US2: Health Check

**V-007 — Health endpoint returns 200 (requires running backend)**
```bash
# Terminal 1: start backend (minimal env, no Azure creds needed)
cd src/api/python
IS_WORKSHOP=true .venv/bin/uvicorn app:app --port 8000

# Terminal 2: check health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health
# Expected: 200

curl -s http://127.0.0.1:8000/health
# Expected: {"status":"healthy"}
```

**V-008 — OTel health exclusion is configured**
```bash
grep "excluded_urls" src/api/python/app/main.py
# Expected: excluded_urls="health"
```

**V-009 — Health tests pass**
```bash
.venv/bin/pytest src/test/api/python/test_app.py -k health -v
# Expected: all health-related tests pass
```

---

### US3: Observability

**V-010 — App Insights init is conditional**
```bash
grep -n "configure_azure_monitor\|APPLICATIONINSIGHTS" src/api/python/app/core/logging.py
# Expected: conditional block reading APPLICATIONINSIGHTS_CONNECTION_STRING
```

**V-011 — Graceful degradation (requires running backend, no connection string)**
```bash
cd src/api/python
# Start without App Insights connection string
unset APPLICATIONINSIGHTS_CONNECTION_STRING
IS_WORKSHOP=true .venv/bin/uvicorn app:app --port 8000 2>&1 | grep -i "insight\|telemetry\|monitor"
# Expected: warning about missing connection string; process continues
```

**V-012 — Trace enrichment middleware is present**
```bash
grep "attach_trace_attributes\|conversation_id_var\|user_id_var" src/api/python/app/core/middleware.py
# Expected: all three identifiers present
```

---

### Quality Gates

**V-014 — Test baseline maintained**
```bash
.venv/bin/pytest src/test/api/python/ -q --tb=short
# Expected: ≥ 268 passed, no newly failing tests
```

**V-015 — Lint clean**
```bash
.venv/bin/flake8 src/api/python/app/
# Expected: exit code 0, no output
```

---

## Environment Variable Registry

All environment variables consumed by the Python FastAPI backend. Variables are classified by:
- **Environment**: `local` (`.env` only), `azure` (Azure App Service only), `both`
- **Required**: `required`, `optional`, `conditional`

### Domain 1: Azure AI Foundry / Agent Framework / OpenAI

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `AZURE_AI_AGENT_ENDPOINT` | both | required | Azure AI Foundry project endpoint URL for the agent |
| `AZURE_AI_AGENT_API_VERSION` | both | optional | Azure AI Agent API version; defaults to SDK default |
| `AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME` | both | required | Model deployment name for the agent (e.g., `gpt-4o`) |
| `AZURE_OPENAI_ENDPOINT` | both | required | Azure OpenAI service endpoint URL |
| `AZURE_OPENAI_RESOURCE` | both | required | Azure OpenAI resource name |
| `AZURE_ENV_GPT_MODEL_NAME` | both | required | GPT model deployment name (e.g., `gpt-4o`) |
| `AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME` | both | required | Embedding model deployment name |
| `AZURE_ENV_OPENAI_API_VERSION` | both | optional | OpenAI API version string; defaults to SDK default |

**Local setup**: Set all required vars in `.env`. Managed Identity handles auth in Azure; `DefaultAzureCredential` with local credentials (e.g., `az login`) handles auth locally.

---

### Domain 2: Fabric SQL / Azure SQL

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `FABRIC_SQL_SERVER` | local | conditional | Fabric SQL server hostname (FQDN) for local/non-Azure-SQL mode |
| `FABRIC_SQL_DATABASE` | local | conditional | Database name on the Fabric SQL server |
| `FABRIC_SQL_CONNECTION_STRING` | local | conditional | Full ODBC connection string (alternative to SERVER+DATABASE+USER) |
| `FABRIC_SQL_USERNAME` | local | conditional | SQL auth username (local dev only; Managed Identity used in Azure) |
| `FABRIC_SQL_PASSWORD` | local | conditional | SQL auth password (local dev only; use `.env`, never commit) |
| `FABRIC_SQL_DRIVER` | local | optional | ODBC driver string; defaults to `ODBC Driver 18 for SQL Server` |
| `AZURE_SQLDB_SERVER` | azure | conditional | Azure SQL server hostname; used when `IS_WORKSHOP=true` and `AZURE_ENV_ONLY=true` |
| `AZURE_SQLDB_DATABASE` | azure | conditional | Azure SQL database name; used when `IS_WORKSHOP=true` and `AZURE_ENV_ONLY=true` |
| `AZURE_SQLDB_USER_MID` | azure | conditional | Managed Identity client ID for Azure SQL access (Azure-only) |

**Conditional**: Fabric SQL / Azure SQL variables are only required when `IS_WORKSHOP=false` or when `AZURE_ENV_ONLY=true`. When `IS_WORKSHOP=true` and `AZURE_ENV_ONLY=false`, the data layer uses Cosmos DB only with local Fabric SQL.

---

### Domain 3: Cosmos DB

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `AZURE_COSMOSDB_ACCOUNT` | both | required | Cosmos DB account name (used to build endpoint URL) |
| `AZURE_COSMOSDB_DATABASE` | both | required | Database name within the Cosmos DB account |
| `AZURE_COSMOSDB_CONVERSATIONS_CONTAINER` | both | required | Container name for chat conversation history |
| `AZURE_COSMOSDB_ENABLE_FEEDBACK` | both | optional | `true` = enable feedback storage; default `false` |

**Auth**: Cosmos DB uses Managed Identity in Azure (`DefaultAzureCredential`). For local development, use `az login` with a principal that has Cosmos DB Data Contributor role.

---

### Domain 4: Azure AI Search

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `AZURE_AI_SEARCH_ENDPOINT` | both | conditional | Azure AI Search service endpoint URL (bicep-canonical name) |
| `AZURE_AI_SEARCH_INDEX` | both | conditional | Index name to query for document retrieval |
| `AZURE_AI_SEARCH_CONNECTION_NAME` | azure | conditional | AI Foundry connection name for Azure AI Search (Azure-only) |

**Note**: Some older `.env` templates use `AZURE_SEARCH_ENDPOINT` and `AZURE_SEARCH_INDEX` (without the `AI_` prefix). Both forms are accepted by the application. The bicep-canonical names use the `AZURE_AI_` prefix. Key-based auth (`AZURE_SEARCH_KEY`) is deprecated; Managed Identity is the approved pattern. If the endpoint and index are absent, `GET /fetch-azure-search-content` returns a 500 configuration error at request time (not a startup failure).

---

### Domain 5: Application Insights / Telemetry

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | both | optional | Azure Monitor connection string; telemetry is disabled (with warning) if absent |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | azure | optional | Legacy instrumentation key; injected by `deploy_backend_custom.bicep`; secondary fallback for Azure Monitor SDK |
| `AZURE_BASIC_LOGGING_LEVEL` | both | optional | Python root log level (e.g., `INFO`, `DEBUG`, `WARNING`); default `INFO` |
| `AZURE_PACKAGE_LOGGING_LEVEL` | both | optional | Log level for noisy Azure SDK / third-party packages; default `WARNING` |
| `AZURE_LOGGING_PACKAGES` | both | optional | Comma-separated list of additional package loggers to suppress; default empty |

**Behavior when absent**: Backend starts and serves all requests normally. A single `WARNING` log is emitted at startup. No telemetry is sent to Azure.

**Security**: `APPLICATIONINSIGHTS_CONNECTION_STRING` contains credentials. In local dev, set it in `.env` (git-ignored). In Azure, it is injected via App Settings from Bicep — never hardcode it in source files.

---

### Domain 6: Behavior Flags

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `IS_WORKSHOP` | both | optional | `true` = use Cosmos DB-only mode; skip Fabric SQL; default `false` |
| `AZURE_ENV_ONLY` | both | optional | `true` = disable Fabric SQL connection even when `IS_WORKSHOP=false`; default `false` |
| `USE_USER_ACCESS_TOKEN` | both | optional | `true` = enable OAuth2 OBO flow for user-delegated Azure access; requires OBO vars; default `false` |
| `AZURE_CLIENT_ID` | azure | optional | Client ID of the user-assigned managed identity; injected by Bicep |
| `AZURE_TENANT_ID` | both | optional | Azure AD tenant ID; used by `DefaultAzureCredential` in local dev |

---

### Domain 7: OAuth2 / OBO Flow

These variables are only required when `USE_USER_ACCESS_TOKEN=true`.

| Variable | Environment | Required | Description |
|----------|------------|----------|-------------|
| `OBO_CLIENT_ID` | local | conditional | App registration client ID for the OBO service principal |
| `OBO_CLIENT_SECRET` | local | conditional | Client secret for the OBO service principal (local dev `.env` only; never commit) |
| `OBO_TENANT_ID` | local | conditional | Azure AD tenant ID for OBO token exchange |

**Security**: `OBO_CLIENT_SECRET` is a credential. It MUST be stored in `.env` (git-ignored) for local development and injected via Azure Key Vault reference or App Settings secret for Azure deployments. Never hardcode.

---

## Minimum Local `.env` for Workshop Mode

The minimal configuration to start the backend locally without live Azure resources:

```bash
# src/api/python/.env

IS_WORKSHOP=true
AZURE_ENV_ONLY=true
AZURE_BASIC_LOGGING_LEVEL=INFO

# Agent framework (required even in workshop mode — use placeholder values if no live agent)
AZURE_AI_AGENT_ENDPOINT=https://placeholder.openai.azure.com
AZURE_AI_AGENT_PROJECT_NAME=placeholder
AZURE_AI_AGENT_ID=placeholder
AZURE_AI_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
AZURE_AI_RESOURCE_GROUP=placeholder

# Cosmos DB (required for /history/* endpoints)
AZURE_COSMOSDB_ACCOUNT=placeholder
AZURE_COSMOSDB_DATABASE=placeholder
AZURE_COSMOSDB_CONVERSATIONS_CONTAINER=placeholder
```

Health check (`GET /health`) works with zero environment variables. It has no env var dependencies.

---

## Security Constraints (Non-Negotiable)

Per the project constitution and SC-006:

1. **Managed Identity is the required auth pattern** for all Azure resources in Azure-deployed environments.
2. **`DefaultAzureCredential`** is the approved pattern for local development (uses `az login` credentials).
3. **No secrets in source code**. `FABRIC_SQL_PASSWORD`, `OBO_CLIENT_SECRET`, and `APPLICATIONINSIGHTS_CONNECTION_STRING` are credentials — `.env` only, git-ignored.
4. **No secrets in committed files**. `.env` is excluded from version control by `.gitignore`. Never commit `.env`.
5. **`AZURE_SEARCH_KEY` is deprecated**. Use Managed Identity for Azure AI Search.
