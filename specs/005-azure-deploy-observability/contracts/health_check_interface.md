# Contract: Health Check Interface

**Feature**: Azure Deployment and Observability Validation
**Date**: 2026-07-03
**User Story**: US2 — Health Check Is Reliable

---

## Endpoint

```
GET /health
```

## Location

Defined inline in `build_app()` in `src/api/python/app/main.py`.

## Authentication

None required. The endpoint is intentionally unauthenticated so that Azure App Service health probes and local container readiness checks can call it without credentials.

## Request

- **Method**: `GET`
- **Path**: `/health`
- **Headers**: None required
- **Body**: None
- **Query Parameters**: None

## Response

### Success (process is running)

```
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "healthy"}
```

### No failure response defined

The endpoint has no error path. It returns 200 whenever the FastAPI process is running and able to accept connections. It does not check external dependencies (database, Azure AI, Application Insights). If the process is not running, the health probe will receive a connection refused error rather than an HTTP response.

## Performance Requirement

Response time must be consistently below **500 ms** under normal load (SC-002).

## Observability

This endpoint is **excluded from OpenTelemetry distributed tracing** via:
```python
FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
```
Health probe calls do not appear in Application Insights trace data, preventing probe noise from polluting the request telemetry stream.

## Dependency-Free Guarantee

The handler has no dependencies on:
- Azure credentials or identity
- Cosmos DB
- Fabric SQL / Azure SQL
- Azure AI Foundry / Agent Framework
- Application Insights (telemetry availability does not affect health response)
- Environment variables (no env var read at handler invocation time)

## Test Coverage

File: `src/test/api/python/test_app.py`

Expected test scenarios:
- `GET /health` returns HTTP 200
- Response body contains `{"status": "healthy"}`
- Endpoint is accessible without authentication headers
- Endpoint responds when `APPLICATIONINSIGHTS_CONNECTION_STRING` is absent from environment

## Notes

- The port on which `/health` is served depends on the deployment context:
  - Docker local: port 80 (`ApiApp.Dockerfile` CMD `--port 80`)
  - Azure App Service / local dev: port 8000 (`deploy_backend_custom.bicep` `--port 8000`, `start.sh` `--port=8000`)
- Both deployment paths serve the same `/health` route at their respective ports.
