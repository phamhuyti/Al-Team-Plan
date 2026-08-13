"""Approximate USD cost from token usage. Rates are per 1M tokens."""

from __future__ import annotations

# input_per_mtok, output_per_mtok
_MODEL_RATES: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "o1": (15.00, 60.00),
    "o1-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "mock": (0.0, 0.0),
}

_PREFIX_RATES: tuple[tuple[str, tuple[float, float]], ...] = (
    ("gpt-4o-mini", (0.15, 0.60)),
    ("gpt-4o", (2.50, 10.00)),
    ("gpt-4.1-nano", (0.10, 0.40)),
    ("gpt-4.1-mini", (0.40, 1.60)),
    ("gpt-4.1", (2.00, 8.00)),
    ("claude-sonnet-4", (3.00, 15.00)),
    ("claude-opus-4", (15.00, 75.00)),
    ("claude-3-5-sonnet", (3.00, 15.00)),
    ("claude-3-5-haiku", (0.80, 4.00)),
    ("claude-3-opus", (15.00, 75.00)),
    ("claude-3-haiku", (0.25, 1.25)),
    ("gemini-2.0-flash", (0.10, 0.40)),
    ("gemini-2.5-flash", (0.15, 0.60)),
    ("gemini-2.5-pro", (1.25, 10.00)),
    ("gemini-1.5-flash", (0.075, 0.30)),
    ("gemini-1.5-pro", (1.25, 5.00)),
    ("o1-mini", (1.10, 4.40)),
    ("o3-mini", (1.10, 4.40)),
    ("o1", (15.00, 60.00)),
)

# Conservative fallback when model is unknown.
_DEFAULT_RATE = (1.00, 3.00)


def rates_for_model(model: str) -> tuple[float, float]:
    key = (model or "").strip().lower()
    if not key or key == "mock":
        return (0.0, 0.0)
    if key in _MODEL_RATES:
        return _MODEL_RATES[key]
    # OpenRouter-style "vendor/model"
    if "/" in key:
        key = key.rsplit("/", 1)[-1]
        if key in _MODEL_RATES:
            return _MODEL_RATES[key]
    for prefix, rates in _PREFIX_RATES:
        if key.startswith(prefix):
            return rates
    return _DEFAULT_RATE


def estimate_cost_usd(model: str, tokens_in: int = 0, tokens_out: int = 0) -> float:
    inp, out = rates_for_model(model)
    cost = (max(tokens_in, 0) / 1_000_000.0) * inp + (max(tokens_out, 0) / 1_000_000.0) * out
    return round(cost, 8)
