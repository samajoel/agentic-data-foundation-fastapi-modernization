import json
import logging

from fastapi import Request
from opentelemetry import trace

from app.core.logging import conversation_id_var, user_id_var


async def attach_trace_attributes(request: Request, call_next):
    """Auto-attach user_id and conversation_id to span + logging context."""
    span = trace.get_current_span()

    user_id = request.headers.get("x-ms-client-principal-id", "")
    if user_id:
        user_id_var.set(user_id)
        if span and span.is_recording():
            span.set_attribute("user_id", user_id)

    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.body()
            if body:
                data = json.loads(body)
                cid = data.get("conversation_id", "")
                if cid:
                    conversation_id_var.set(cid)
                    if span and span.is_recording():
                        span.set_attribute("conversation_id", cid)
        except Exception:
            # Intentionally fail open: trace enrichment must not break request handling.
            logging.debug(
                "Failed to parse request body for trace attribute enrichment.",
                exc_info=True,
            )
    return await call_next(request)
