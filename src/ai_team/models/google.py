"""Google Gemini generateContent API via HTTP. Optional in V1."""

from __future__ import annotations

import httpx
from pydantic import BaseModel

from ai_team.models.base import ChatMessage, GenerateResult, ModelProvider, parse_json_model, schema_instruction


class GoogleProvider(ModelProvider):
    name = "google"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for the Google provider")
        self.api_key = api_key

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> GenerateResult:
        contents = []
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        if response_schema is not None:
            system = (system + "\n\n" + schema_instruction(response_schema)).strip()
        for message in messages:
            if message.role == "system":
                continue
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        body: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        parsed = parse_json_model(text, response_schema) if response_schema else None
        usage = data.get("usageMetadata") or {}
        return GenerateResult(
            text=text,
            parsed=parsed,
            tokens_in=int(usage.get("promptTokenCount") or 0),
            tokens_out=int(usage.get("candidatesTokenCount") or 0),
            raw={"model": self.model},
        )
