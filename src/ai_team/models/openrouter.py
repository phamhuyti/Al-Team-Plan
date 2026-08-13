"""OpenRouter is OpenAI-compatible and used for later multi-model routing."""

from __future__ import annotations

import httpx
from pydantic import BaseModel

from ai_team.models.base import ChatMessage, GenerateResult, ModelProvider, parse_json_model, schema_instruction


class OpenRouterProvider(ModelProvider):
    name = "openrouter"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for the OpenRouter provider")
        self.api_key = api_key

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> GenerateResult:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        if response_schema is not None:
            payload = [{"role": "system", "content": schema_instruction(response_schema)}, *payload]
        body: dict = {"model": self.model, "messages": payload, "temperature": temperature}
        if response_schema is not None:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        parsed = parse_json_model(text, response_schema) if response_schema else None
        usage = data.get("usage") or {}
        return GenerateResult(
            text=text,
            parsed=parsed,
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
            raw={"id": data.get("id"), "model": data.get("model")},
        )
