"""Multi-model router (Sprint 2.9) — role→model selection + outage fallback."""
import pytest

from app.adapters.model_router import (
    ConfiguredModelRouter,
    _FallbackGateway,
    resolve_managed_model,
)


def test_role_resolves_to_cost_tiered_model():
    # From config/models.yaml — the cost-optimized mix.
    assert resolve_managed_model("extraction") == "claude-haiku-4-5"
    assert resolve_managed_model("drafting") == "claude-sonnet-4-6"
    assert resolve_managed_model("reasoning") == "claude-opus-4-8"
    assert resolve_managed_model("multimodal_edge") == "claude-opus-4-8"


def test_unknown_role_falls_back_to_default():
    assert resolve_managed_model("nonexistent-role") == "claude-opus-4-8"


def test_router_returns_gateway_bound_to_role_model():
    r = ConfiguredModelRouter(api_key=None)
    assert r.gateway("extraction").model == "claude-haiku-4-5"
    assert r.gateway("drafting").model == "claude-sonnet-4-6"
    # same role returns a cached instance
    assert r.gateway("reasoning") is r.gateway("reasoning")


class _Boom:
    """Gateway whose calls always fail — to exercise RTE-001 fallback."""
    model = "primary-model"

    async def parse(self, **_):
        raise RuntimeError("managed tier down")

    async def complete(self, **_):
        raise RuntimeError("managed tier down")


class _Ok:
    model = "fallback-model"

    async def parse(self, **_):
        return "parsed-by-fallback"

    async def complete(self, **_):
        return "completed-by-fallback"


@pytest.mark.asyncio
async def test_fallback_gateway_uses_fallback_on_error():
    gw = _FallbackGateway(_Boom(), _Ok())
    assert await gw.complete(system="s", prompt="p") == "completed-by-fallback"
    assert await gw.parse(system="s", prompt="p", output_type=str) == "parsed-by-fallback"


@pytest.mark.asyncio
async def test_fallback_gateway_raises_when_no_fallback():
    gw = _FallbackGateway(_Boom(), None)
    with pytest.raises(RuntimeError):
        await gw.complete(system="s", prompt="p")
