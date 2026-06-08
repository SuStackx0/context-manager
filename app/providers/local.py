"""Local model-backed providers using HF transformers / sentence-transformers.

All heavy imports (torch, transformers, sentence_transformers) are deferred to
construction time so importing this module — and the whole app — never requires
the model stack. Tests use the fake providers and never touch this code.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider, LLMProvider

logger = get_logger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str, dim: int) -> None:  # pragma: no cover
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        vecs = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return [v.tolist() for v in vecs]


class LocalLLMProvider(LLMProvider):
    def __init__(self, model_name: str) -> None:  # pragma: no cover
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Loading LLM: %s", model_name)
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype="auto"
        )
        self._torch = torch

    def generate(self, prompt: str, max_new_tokens: int = 256) -> str:  # pragma: no cover
        messages = [{"role": "user", "content": prompt}]
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text, return_tensors="pt")
        with self._torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        gen = out[0][inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(gen, skip_special_tokens=True).strip()
