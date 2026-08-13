"""OpenAI chat completions with JSON object responses."""

from __future__ import annotations

from pydantic import BaseModel

from ai_team.models.base import ChatMessage, GenerateResult, ModelProvider, parse_json_model, schema_instruction


class OpenAIProvider(ModelProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> GenerateResult:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        if response_schema is not None:
            payload = [
                {
                    "role": "system",
                    "content": schema_instruction(response_schema),
                },
                *payload,
            ]
        kwargs: dict = {
            "model": self.model,
            "messages": payload,
            "temperature": temperature,
        }
        if response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
        completion = await self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0].message
        text = choice.content or "{}"
        parsed = parse_json_model(text, response_schema) if response_schema else None
        usage = completion.usage
        return GenerateResult(
            text=text,
            parsed=parsed,
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
            raw={"id": completion.id, "model": completion.model},
        )
