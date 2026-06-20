"""Static API list-price estimates per model (USD per token)."""

from __future__ import annotations

# (input_per_token, output_per_token, cache_read_per_token, cache_write_per_token)
MODEL_RATES: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-4-6": (5.0 / 1_000_000, 25.0 / 1_000_000, 0.5 / 1_000_000, 6.25 / 1_000_000),
    "claude-opus-4-8": (5.0 / 1_000_000, 25.0 / 1_000_000, 0.5 / 1_000_000, 6.25 / 1_000_000),
    "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000, 0.3 / 1_000_000, 3.75 / 1_000_000),
    "claude-haiku-4-5": (1.0 / 1_000_000, 5.0 / 1_000_000, 0.1 / 1_000_000, 1.25 / 1_000_000),
}

DEFAULT_RATES = MODEL_RATES["claude-sonnet-4-6"]


def normalize_model_id(model: str) -> str:
    return model.strip().lower()


def estimate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    rates = MODEL_RATES.get(normalize_model_id(model), DEFAULT_RATES)
    inp, out, cache_read, cache_write = rates
    return (
        input_tokens * inp
        + output_tokens * out
        + cache_read_tokens * cache_read
        + cache_creation_tokens * cache_write
    )
