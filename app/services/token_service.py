"""Token counting service — wraps the tokenizer with the configured model."""
from __future__ import annotations

from app.utils.tokenizer import count_tokens


class TokenService:
    def __init__(self, model_name: str | None = None) -> None:
        # When None (e.g. tests / fake provider), the heuristic counter is used.
        self.model_name = model_name

    def count(self, text: str) -> int:
        return count_tokens(text, self.model_name)
