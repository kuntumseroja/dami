"""LLMGateway adapter for the enterprise Claude API.

All model traffic flows through this one class — the enforcement point for
the secure-sandbox guarantees (single audited entry, adaptive thinking, no
data leaves except to the enterprise endpoint).
"""
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.domain.ports import LLMGateway, T


class ClaudeGateway(LLMGateway):
    def __init__(self, api_key: str | None, model: str):
        self._client = AsyncAnthropic(api_key=api_key or None)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def parse(self, *, system: str, prompt: str, output_type: type[T],
                    max_tokens: int = 8192) -> T:
        response = await self._client.messages.parse(
            model=self._model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_type,
        )
        parsed: BaseModel | None = response.parsed_output
        if parsed is None:
            raise ValueError("model returned no parseable structured output")
        return parsed  # type: ignore[return-value]

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2048) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return next((b.text for b in response.content if b.type == "text"), "")
