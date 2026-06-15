"""ModelRouter — role-based model selection over config/models.yaml.

Resolves a task role (drafting / extraction / reasoning / multimodal_edge) to a
concrete model + tier per the registry, and returns a role-bound LLMGateway.
Implements the cost-tiered mix (Haiku for extraction, Sonnet for drafting,
Opus for reasoning) and the outage-fallback policy (RTE-001): if the managed
tier errors, the same request is retried on the self-host tier when one is
configured. Every gateway carries its resolved model id, so audit logging in
the use cases is unchanged.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

from app.adapters.llm_claude import ClaudeGateway
from app.domain.ports import LLMGateway, ModelRouter, T

# Role → which Claude model the managed tier uses when the registry can't be
# read (defensive default mirroring config/models.yaml).
_MANAGED_DEFAULTS = {
    "drafting": "claude-sonnet-4-6",
    "extraction": "claude-haiku-4-5",
    "reasoning": "claude-opus-4-8",
    "multimodal_edge": "claude-opus-4-8",
}
_FALLBACK_MODEL = "claude-opus-4-8"


@lru_cache
def load_registry() -> dict:
    env = os.environ.get("MODELS_CONFIG", "").strip()
    path = Path(env) if env else Path(__file__).resolve().parents[3] / "config/models.yaml"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def resolve_managed_model(role: str) -> str:
    """The managed-tier model id for a role, from the registry (config-driven)."""
    roles = load_registry().get("roles", {})
    spec = roles.get(role) or {}
    managed = spec.get("managed") or {}
    return managed.get("primary") or _MANAGED_DEFAULTS.get(role, _FALLBACK_MODEL)


class _FallbackGateway(LLMGateway):
    """Wraps a primary gateway; on error delegates to a fallback gateway
    (RTE-001 outage/rate-limit fallback). Fallback is optional."""

    def __init__(self, primary: LLMGateway, fallback: LLMGateway | None):
        self._primary = primary
        self._fallback = fallback

    @property
    def model(self) -> str:
        return self._primary.model

    async def parse(self, *, system: str, prompt: str, output_type: type[T],
                    max_tokens: int = 8192) -> T:
        try:
            return await self._primary.parse(
                system=system, prompt=prompt, output_type=output_type, max_tokens=max_tokens)
        except Exception:
            if self._fallback is None:
                raise
            return await self._fallback.parse(
                system=system, prompt=prompt, output_type=output_type, max_tokens=max_tokens)

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2048) -> str:
        try:
            return await self._primary.complete(system=system, prompt=prompt, max_tokens=max_tokens)
        except Exception:
            if self._fallback is None:
                raise
            return await self._fallback.complete(system=system, prompt=prompt, max_tokens=max_tokens)


class ConfiguredModelRouter(ModelRouter):
    """Managed-tier router (Claude). Self-host tier is attached only when a
    SELF_HOST_LLM_ENDPOINT is configured; otherwise calls run managed-only."""

    def __init__(self, api_key: str | None, *, self_host_factory=None):
        self._api_key = api_key
        self._self_host_factory = self_host_factory  # callable(role) -> LLMGateway | None
        self._cache: dict[str, LLMGateway] = {}

    def gateway(self, role: str) -> LLMGateway:
        if role not in self._cache:
            model = resolve_managed_model(role)
            primary = ClaudeGateway(self._api_key, model)
            fallback = self._self_host_factory(role) if self._self_host_factory else None
            self._cache[role] = _FallbackGateway(primary, fallback)
        return self._cache[role]
