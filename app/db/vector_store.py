"""FAISS-backed vector store with on-disk persistence.

Uses ``IndexIDMap`` over ``IndexFlatIP`` keyed by ``message_id`` so vectors map
directly back to message rows. Inner-product on normalized vectors == cosine
similarity. The index is small (flat) which is correct and fast for the
thousands-of-messages scale in scope.
"""
from __future__ import annotations

import os
import threading

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class FaissVectorStore:
    def __init__(self, dim: int, index_path: str | None = None) -> None:
        import faiss

        self._faiss = faiss
        self.dim = dim
        self.index_path = index_path
        self._lock = threading.Lock()
        self._index = self._load_or_create()

    def _load_or_create(self):
        if self.index_path and os.path.exists(self.index_path):
            try:
                logger.info("Loading FAISS index from %s", self.index_path)
                return self._faiss.read_index(self.index_path)
            except Exception as exc:  # pragma: no cover - corrupt index
                logger.warning("Failed to read index (%s); recreating", exc)
        base = self._faiss.IndexFlatIP(self.dim)
        return self._faiss.IndexIDMap2(base)

    def _normalize(self, vecs: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    def add(self, ids: list[int], vectors: list[list[float]]) -> None:
        if not ids:
            return
        with self._lock:
            arr = self._normalize(np.asarray(vectors, dtype="float32"))
            id_arr = np.asarray(ids, dtype="int64")
            self._index.add_with_ids(arr, id_arr)
            self._persist()

    def remove_ids(self, ids: list[int]) -> int:
        if not ids:
            return 0
        with self._lock:
            sel = self._faiss.IDSelectorBatch(np.asarray(ids, dtype="int64"))
            removed = self._index.remove_ids(sel)
            self._persist()
            return int(removed)

    def search(self, vector: list[float], k: int) -> list[tuple[int, float]]:
        with self._lock:
            if self._index.ntotal == 0:
                return []
            q = self._normalize(np.asarray([vector], dtype="float32"))
            k = min(k, self._index.ntotal)
            scores, ids = self._index.search(q, k)
        out: list[tuple[int, float]] = []
        for idx, score in zip(ids[0], scores[0]):
            if idx != -1:
                out.append((int(idx), float(score)))
        return out

    def _persist(self) -> None:
        if not self.index_path:
            return
        parent = os.path.dirname(self.index_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._faiss.write_index(self._index, self.index_path)

    @property
    def size(self) -> int:
        return int(self._index.ntotal)
