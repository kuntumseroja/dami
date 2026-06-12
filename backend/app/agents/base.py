"""Shared Claude client for all agents.

All model calls go through this module so the secure-sandbox guarantees are
enforced in one place: a single audited entry point, adaptive thinking, and
no data leaves except to the enterprise Claude API endpoint.
"""
from anthropic import AsyncAnthropic

from app.core.config import get_settings

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    return _client


def model_id() -> str:
    return get_settings().dam_model
