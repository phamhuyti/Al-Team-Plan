"""Anthropic Messages API via HTTP. Optional in V1."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from ai_team.models.base import ChatMessage, GenerateResult, ModelProvider, parse_json_model, schema_instruction


class AnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        self.api_key = api_key

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> GenerateResult:
        system_parts = [m.content for m in messages if m.role == "system"]
        if response_schema is not None:
            system_parts.append(schema_instruction(response_schema))
        chat = [{"role": m.role, "content": m.content} for m in messages if m.role in {"user", "assistant"}]
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                content=json.dumps(
                    {
                        "model": self.model,
                        "max_tokens": 4096,
                        "temperature": temperature,
                        "system": "\n\n".join(system_parts),
                        "messages": chat,
                    }
                ),
            )
            response.raise_for_status()
            data = response.json()
        text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
        parsed = parse_json_model(text, response_schema) if response_schema else None
        usage = data.get("usage") or {}
        return GenerateResult(
            text=text,
            parsed=parsed,
            tokens_in=int(usage.get("input_tokens") or 0),
            tokens_out=int(usage.get("output_tokens") or 0),
            raw={"id": data.get("id"), "model": data.get("model")},
        )
