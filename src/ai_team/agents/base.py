"""Shared agent runtime: prompt + contract JSON + tracing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ai_team.context.engine import ContextBundle
from ai_team.models.base import ChatMessage, ModelProvider
from ai_team.models.pricing import estimate_cost_usd
from ai_team.paths import load_prompt
from ai_team.tracing.audit import Tracer


class BaseAgent:
    role: str = "agent"
    prompt_file: str = "manager"
    output_schema: type[BaseModel] | None = None

    def __init__(self, model: ModelProvider, extra_instructions: str = "") -> None:
        self.model = model
        self.extra_instructions = extra_instructions

    def system_prompt(self) -> str:
        prompt = load_prompt(self.prompt_file)
        if self.extra_instructions:
            prompt += "\n\n# Project-specific notes\n" + self.extra_instructions
        prompt += (
            "\n\nYou MUST return a single JSON object matching the required contract. "
            "Do not include markdown fences."
        )
        return prompt

    async def run(
        self,
        user_message: str,
        context: ContextBundle | None = None,
        tracer: Tracer | None = None,
        extra: dict[str, Any] | None = None,
    ) -> BaseModel:
        parts = [user_message]
        if extra:
            parts.append("Additional input:\n" + str(extra))
        if context is not None:
            parts.append(context.render())
        messages = [
            ChatMessage(role="system", content=self.system_prompt()),
            ChatMessage(role="user", content="\n\n".join(parts)),
        ]
        if tracer:
            tracer.emit("agent_prompt", actor=self.role, payload={"message": user_message[:2000]})
        result = await self.model.generate(messages, response_schema=self.output_schema)
        if tracer:
            cost = estimate_cost_usd(self.model.model, result.tokens_in, result.tokens_out)
            tracer.emit(
                "agent_response",
                actor=self.role,
                payload={
                    "text": result.text[:4000],
                    "provider": getattr(self.model, "name", ""),
                    "model": self.model.model,
                },
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_usd=cost,
            )
        if result.parsed is None:
            raise RuntimeError(f"{self.role} returned unparseable output")
        return result.parsed
