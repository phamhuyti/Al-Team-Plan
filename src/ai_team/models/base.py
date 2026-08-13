"""Model provider abstraction. Agents only call `model.generate(...)`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class GenerateResult:
    text: str
    parsed: BaseModel | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> GenerateResult:
        raise NotImplementedError


def schema_instruction(schema: type[BaseModel]) -> str:
    json_schema = schema.model_json_schema()
    return (
        "Respond with a single JSON object that matches this schema. "
        "Do not wrap it in markdown.\n\n"
        f"{json_schema}"
    )


def parse_json_model(text: str, schema: type[BaseModel]) -> BaseModel:
    import json
    import re

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    data = json.loads(candidate)
    return schema.model_validate(data)
