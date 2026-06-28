import logging
import os
from contextvars import ContextVar

from azure.monitor.opentelemetry import configure_azure_monitor

conversation_id_var: ContextVar[str] = ContextVar("conversation_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def configure_logging():
    """Set up logging levels, Application Insights, and log-record enrichment."""
    basic_level = getattr(logging, os.getenv("AZURE_BASIC_LOGGING_LEVEL", "INFO").upper(), logging.INFO)
    package_level = getattr(logging, os.getenv("AZURE_PACKAGE_LOGGING_LEVEL", "WARNING").upper(), logging.WARNING)
    extra_suppressed = [p.strip() for p in os.getenv("AZURE_LOGGING_PACKAGES", "").split(",") if p.strip()]

    logging.basicConfig(level=basic_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if conn_str:
        configure_azure_monitor(connection_string=conn_str)
        logging.getLogger().setLevel(basic_level)
        logging.info("Application Insights configured")
    else:
        logging.warning("No Application Insights connection string found")

    # Must be set AFTER configure_azure_monitor(); individual attrs map to customDimensions keys
    original_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        if record.funcName == "track_event":
            return record
        cid = conversation_id_var.get("")
        uid = user_id_var.get("")
        if cid:
            record.conversation_id = cid
        if uid:
            record.user_id = uid
        return record

    logging.setLogRecordFactory(record_factory)

    # Suppress noisy Azure SDK / third-party loggers
    for name in set([
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.identity",
        "azure.ai",
        "azure.monitor.opentelemetry",
        "opentelemetry",
        "urllib3",
        "httpx",
        "httpcore",
    ] + extra_suppressed):
        logging.getLogger(name).setLevel(package_level)
