"""LLMGateway adapter for the enterprise Claude API.

All model traffic flows through this one class — the enforcement point for
the secure-sandbox guarantees (single audited entry, adaptive thinking where
supported, no data leaves except to the enterprise endpoint).
"""
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.domain.ports import LLMGateway, T


def _supports_adaptive_thinking(model: str) -> bool:
    """Adaptive thinking is supported on Fable 5, Opus 4.6+/4.7/4.8, and
    Sonnet 4.6 — but NOT on Haiku or Sonnet 4.5 (sending it 400s). The router's
    cost-tiered mix runs extraction on Haiku, so this guard matters."""
    m = model.lower()
    if "haiku" in m:
        return False
    if "sonnet-4-5" in m or "sonnet-4-0" in m:
        return False
    return True


class ClaudeGateway(LLMGateway):
    def __init__(self, api_key: str | None, model: str):
        self._client = AsyncAnthropic(api_key=api_key or None)
        self._model = model
        self._thinking = {"type": "adaptive"} if _supports_adaptive_thinking(model) else None

    @property
    def model(self) -> str:
        return self._model

    async def parse(self, *, system: str, prompt: str, output_type: type[T],
                    max_tokens: int = 8192) -> T:
        kwargs = {}
        if self._thinking:
            kwargs["thinking"] = self._thinking
        response = await self._client.messages.parse(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_type,
            **kwargs,
        )
        parsed: BaseModel | None = response.parsed_output
        if parsed is None:
            raise ValueError("model returned no parseable structured output")
        return parsed  # type: ignore[return-value]

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2048) -> str:
        kwargs = {}
        if self._thinking:
            kwargs["thinking"] = self._thinking
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return next((b.text for b in response.content if b.type == "text"), "")
