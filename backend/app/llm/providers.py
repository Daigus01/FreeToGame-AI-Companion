"""LLM provider abstraction. The orchestrator talks ONLY to `LLMProvider`.

Messages use the OpenAI chat format internally (D-02). Other providers must translate.
STATUS:
  - Protocol + dataclasses: done
  - OpenAIProvider: implemented, NOT verified against the live API (TODO P2-01)
  - AnthropicProvider: stub (TODO P2-07)
"""
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

from app.config import Settings
from app.llm.tools import to_openai_tools


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ProviderEvent:
    type: Literal["text", "tool_call"]
    text: str = ""
    tool_call: ToolCall | None = None


class LLMProvider(Protocol):
    def stream(self, messages: list[dict]) -> AsyncIterator[ProviderEvent]:
        """Yield text deltas as they arrive and a `tool_call` event per requested tool call."""
        ...


class OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI  # lazy import so tests don't need credentials

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def stream(self, messages: list[dict]) -> AsyncIterator[ProviderEvent]:
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, tools=to_openai_tools(), stream=True
        )
        acc: dict[int, dict] = {}
        async for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield ProviderEvent("text", text=delta.content)
            for tc in delta.tool_calls or []:
                slot = acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function.arguments:
                        slot["args"] += tc.function.arguments
        for slot in acc.values():
            try:
                args = json.loads(slot["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            yield ProviderEvent("tool_call", tool_call=ToolCall(slot["id"], slot["name"], args))


class AnthropicProvider:
    """TODO(P2-07): implement with the Anthropic SDK; translate OpenAI-format messages and use to_anthropic_tools()."""

    def __init__(self, api_key: str, model: str):
        raise NotImplementedError("AnthropicProvider is not implemented yet (P2-07)")


def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    raise ValueError(f"unknown LLM_PROVIDER {settings.llm_provider!r}")
