# Quickstart Validation Guide: Single Backend Consolidation

**Feature**: 001-single-backend-consolidation
**Date**: 2026-06-27

Use this guide to verify the consolidation is complete and correct after all tasks
in `tasks.md` have been executed.

---

## Prerequisites

- Python dependencies installed: `pip install -r src/api/python/requirements.txt`
- A `.env` file present in `src/api/python/` with valid Azure credentials for your
  local development environment (see `documents/LocalDevelopmentSetup.md`)
- `az` CLI available and authenticated if regenerating `infra/main.json` from Bicep

---

## Step 1: Confirm .NET Artifacts Are Gone

Run from the repository root:

```bash
find src/api/dotnet -type f 2>/dev/null | wc -l
```

**Expected**: `0` (directory does not exist or is empty)

```bash
grep -r "dotnet\|CsApi\|csapi\|backendRuntimeStack" infra/ src/ 2>/dev/null
```

**Expected**: No output (zero matches)

---

## Step 2: Confirm Copilot Studio Artifacts Are Gone

```bash
find documents/Images/cps -type f 2>/dev/null | wc -l
```

**Expected**: `0`

```bash
test -f documents/CopilotStudioDeployment.md && echo "EXISTS" || echo "GONE"
```

**Expected**: `GONE`

```bash
grep -ri "copilot\|CopilotStudio\|cps\|solution-architecture-cps" documents/ README.md 2>/dev/null
```

**Expected**: No output

---

## Step 3: Run the Python Test Suite

```bash
pytest -m unittest
```

**Expected**: All tests pass. No new failures compared to pre-consolidation baseline.

Check linting:

```bash
flake8 src/api/python/
```

**Expected**: No violations beyond any that pre-existed before this consolidation.

---

## Step 4: Start the Python Backend Locally

```bash
cd src/api/python
python app.py
```

**Expected**: Server starts on `http://127.0.0.1:8000` with no errors.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

**Expected**: `{"status":"healthy"}`

---

## Step 5: Smoke Test the Stable API Contract

Verify `POST /api/chat` responds (streaming):

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test-001","messages":[{"role":"user","content":"Hello"}]}' \
  --no-buffer
```

**Expected**: A streaming response is returned. No 404, 500, or connection errors.

Verify history list responds:

```bash
curl "http://127.0.0.1:8000/history/list?user_id=test-user&limit=5"
```

**Expected**: A JSON response (empty array or list of conversations). No 404 or 500.

---

## Step 6: Confirm Infrastructure Is Clean

Open `infra/main.bicep` in a text editor or run:

```bash
grep "backendRuntimeStack\|deploy_backend_csapi_docker\|dotnet" infra/main.bicep
```

**Expected**: No output

Confirm deleted Bicep files are gone:

```bash
test -f infra/deploy_backend_csapi_docker.bicep && echo "EXISTS" || echo "GONE"
test -f infra/deploy_csapi_app_service.bicep && echo "EXISTS" || echo "GONE"
test -f infra/csapi.parameters.json && echo "EXISTS" || echo "GONE"
```

**Expected**: All three print `GONE`

---

## Step 7: Review Deployment Documentation

Open `documents/DeploymentGuide.md` and confirm:
- No mention of `dotnet` runtime as a deployment option
- No `azd env set BACKEND_RUNTIME_STACK dotnet` command
- No link to `CopilotStudioDeployment.md`

Open `README.md` and confirm:
- No "Microsoft Fabric and Microsoft Copilot Studio" architecture section
- No `solution-architecture-cps.png` image reference

---

## Consolidation Complete

When all steps above pass, the consolidation is verified. The repository is now
unambiguously a single-backend, single-architecture-path project.

Proceed to the next spec per the Spec Kit workflow.
