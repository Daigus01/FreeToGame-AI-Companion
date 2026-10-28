"""LLM provider abstraction. The orchestrator talks ONLY to `LLMProvider`.

Messages use the OpenAI chat format internally (D-02). Other providers must translate.
STATUS:
  - Protocol + dataclasses: done
  - OpenAIProvider: implemented, NOT verified against the live API (TODO P2-01)
  - AnthropicProvider: implemented (P2-07), message translation + streaming unit-tested with fakes; NOT verified live (P2-01)
  - MockProvider (LLM_PROVIDER=mock, app/llm/mock.py): deterministic, key-less, for dev/tests (D-14)
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


def to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """OpenAI-format messages (D-02) -> (system, anthropic messages).
    assistant.tool_calls -> tool_use blocks; role=tool -> tool_result blocks inside a *user* message.
    Consecutive same-role messages are merged (Anthropic expects alternating roles)."""
    system = "\n".join(m["content"] for m in messages if m["role"] == "system" and m.get("content"))
    out: list[dict] = []

    def push(role: str, blocks: list[dict]) -> None:
        if out and out[-1]["role"] == role:
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": role, "content": list(blocks)})

    for m in messages:
        role = m["role"]
        if role == "user":
            push("user", [{"type": "text", "text": m.get("content") or " "}])
        elif role == "assistant":
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": args})
            if blocks:
                push("assistant", blocks)
        elif role == "tool":
            push("user", [{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m.get("content") or ""}])
    return system, out


class AnthropicProvider:
    MAX_TOKENS = 1024

    def __init__(self, api_key: str, model: str, client=None):
        if client is None:
            from anthropic import AsyncAnthropic  # lazy import so tests don't need credentials

            client = AsyncAnthropic(api_key=api_key)
        self._client = client
        self._model = model

    async def stream(self, messages: list[dict]) -> AsyncIterator[ProviderEvent]:
        from app.llm.tools import to_anthropic_tools

        system, msgs = to_anthropic_messages(messages)
        kwargs = {"system": system} if system else {}  # an empty system prompt is not sent
        async with self._client.messages.stream(
            model=self._model, max_tokens=self.MAX_TOKENS, messages=msgs, tools=to_anthropic_tools(), **kwargs
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield ProviderEvent("text", text=text)
            final = await stream.get_final_message()
        for block in final.content:
            if getattr(block, "type", None) == "tool_use":
                yield ProviderEvent("tool_call", tool_call=ToolCall(block.id, block.name, dict(block.input or {})))


def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        from app.llm.mock import MockProvider

        return MockProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    raise ValueError(f"unknown LLM_PROVIDER {settings.llm_provider!r}")
