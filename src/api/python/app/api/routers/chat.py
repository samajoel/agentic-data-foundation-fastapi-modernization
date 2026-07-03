"""
Chat API module for handling chat interactions and responses.
"""

import asyncio
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Azure Auth
from app.core.auth.auth_utils import get_authenticated_user_details
from app.core.auth.azure_credential_utils import get_azure_credential_async

# Agent orchestration
from app.agents.chat_orchestrator import stream_chat_request, track_event_if_configured

# Constants
HOST_NAME = "Agentic Applications for Unified Data Foundation"
HOST_INSTRUCTIONS = "Answer questions about Sales, Products and Orders data."

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/fetch-azure-search-content")
async def fetch_azure_search_content(request: Request):
    """Fetch document content from Azure AI Search by citation URL."""
    try:
        request_json = await request.json()
        citation_url = request_json.get("url")
        fallback_label = request_json.get("source") or request_json.get("title", "")
        logger.info(
            "POST /fetch-azure-search-content called: url=%s",
            citation_url,
        )

        if not citation_url:
            return JSONResponse(
                content={"error": "URL is required"}, status_code=400
            )

        # --- SSRF protection: only allow requests to the configured search endpoint ---
        from urllib.parse import urlparse, parse_qs, quote

        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") or os.getenv(
            "AZURE_AI_SEARCH_ENDPOINT", ""
        )
        if not search_endpoint:
            return JSONResponse(
                content={"error": "Search endpoint not configured"},
                status_code=500,
            )

        allowed_host = urlparse(search_endpoint).netloc.lower()
        parsed = urlparse(citation_url)
        if parsed.netloc.lower() != allowed_host:
            logger.warning(
                "Blocked fetch to non-allowed host: %s (allowed: %s)",
                parsed.netloc,
                allowed_host,
            )
            return JSONResponse(
                content={"error": "URL host not allowed"}, status_code=403
            )

        # Parse the doc id from the URL: .../docs/{doc_id}?api-version=...
        path_parts = parsed.path.rstrip("/").split("/")
        doc_id = None
        for i, part in enumerate(path_parts):
            if part == "docs" and i + 1 < len(path_parts):
                doc_id = path_parts[i + 1]
                break

        if not doc_id:
            return JSONResponse(
                content={"error": "Could not parse document ID from URL"},
                status_code=400,
            )

        # Reconstruct URL using OData key lookup (no $select — causes 400)
        idx = parsed.path.find("/docs/")
        base_path = parsed.path[:idx]
        qs = parse_qs(parsed.query)
        api_version = qs.get("api-version", ["2024-07-01"])[0]

        from urllib.parse import unquote
        decoded_doc_id = unquote(doc_id)
        encoded_key = quote(decoded_doc_id, safe="")
        lookup_url = (
            f"{parsed.scheme}://{parsed.netloc}{base_path}"
            f"/docs('{encoded_key}')?api-version={api_version}"
        )

        credential = await get_azure_credential_async()
        try:
            token = await credential.get_token(
                "https://search.azure.com/.default"
            )
            access_token = token.token
        finally:
            await credential.close()

        def fetch_content():
            try:
                import requests as req

                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                response = req.get(
                    lookup_url, headers=headers, timeout=10
                )
                logger.info(
                    "Azure Search lookup: status=%d, url=%s",
                    response.status_code,
                    lookup_url,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    source = data.get("source", fallback_label)
                    return {"content": content, "title": source}
                logger.warning(
                    "Azure Search fetch failed: status=%d, body=%s",
                    response.status_code,
                    response.text[:500],
                )
                return {"error": f"HTTP {response.status_code}"}
            except Exception:
                logger.exception("Exception fetching search content")
                return {"error": "Unable to fetch content"}

        result = await asyncio.to_thread(fetch_content)
        return JSONResponse(content=result)

    except Exception:
        logger.exception("Error in fetch_azure_search_content")
        return JSONResponse(
            content={"error": "Internal server error"}, status_code=500
        )


@router.post("/chat")
async def conversation(request: Request):
    """Handle chat requests - streaming text or chart generation based on query keywords."""
    try:
        # Get the request JSON with optimized payload (only conversation_id and query)
        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user.get("user_principal_id", "")

        # Get user's access token for OBO flow (needed for Work IQ Teams)
        user_assertion = authenticated_user.get("aad_access_token")

        # Validate required parameters
        if not query:
            return JSONResponse(
                content={"error": "Query is required"},
                status_code=400
            )

        if not conversation_id:
            return JSONResponse(
                content={"error": "Conversation ID is required"},
                status_code=400
            )

        logger.info(
            "POST /chat called: conversation_id=%s, query_length=%d, has_user_token=%s",
            conversation_id, len(query) if query else 0, bool(user_assertion),
        )

        # Track chat request initiation
        track_event_if_configured("ChatRequestReceived", {
            "conversation_id": conversation_id,
            "user_id": user_id
        })

        result = await stream_chat_request(conversation_id, query, user_id=user_id, user_assertion=user_assertion)
        track_event_if_configured(
            "ChatStreamSuccess",
            {"conversation_id": conversation_id, "user_id": user_id, "query": query}
        )
        return StreamingResponse(result, media_type="application/json-lines")

    except Exception as ex:
        logger.exception("Error in conversation endpoint: %s", str(ex))

        # Track specific error type
        track_event_if_configured("ChatRequestError", {
            "conversation_id": request_json.get("conversation_id") if 'request_json' in locals() else "",
            "user_id": locals().get("user_id", ""),
            "error": str(ex),
            "error_type": type(ex).__name__
        })

        span = trace.get_current_span()
        if span is not None:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR, str(ex)))
        return JSONResponse(content={"error": "An internal error occurred while processing the conversation."}, status_code=500)
