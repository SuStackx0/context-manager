"""Token counting helpers.

The real implementation uses the bundled model's HF tokenizer (lazy import).
A deterministic word-based fallback is used when transformers is unavailable
(e.g. test environment) so token accounting still works without torch.
"""
from __future__ import annotations

import re
from functools import lru_cache

_WORD_RE = re.compile(r"\w+|[^\w\s]")


def _heuristic_count(text: str) -> int:
    """Rough token estimate: counts word and punctuation chunks.

    Good enough for budgeting and fully deterministic for tests.
    """
    if not text:
        return 0
    return len(_WORD_RE.findall(text))


@lru_cache(maxsize=4)
def _load_hf_tokenizer(model_name: str):  # pragma: no cover - needs transformers
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_name)


def count_tokens(text: str, model_name: str | None = None) -> int:
    """Count tokens in ``text``.

    If ``model_name`` is given and transformers is importable, use the model's
    tokenizer; otherwise fall back to the deterministic heuristic.
    """
    if model_name:
        try:  # pragma: no cover - exercised only with transformers installed
            tok = _load_hf_tokenizer(model_name)
            return len(tok.encode(text))
        except Exception:
            pass
    return _heuristic_count(text)
