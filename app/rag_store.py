# app/rag_store.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from . import models

# RAG must never break core app behavior. If FAISS isn't available, we just disable RAG.
try:  # pragma: no cover
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


@dataclass
class RetrievedReflection:
    score: float
    checkin_date: str
    text: str
    reflection_id: int


def _normalize_rows(x: np.ndarray) -> np.ndarray:
    """L2-normalize each row for cosine similarity using inner product."""
    norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / norms


class RagStore:
    """
    SQLite-backed reflection store + in-memory FAISS retrieval.

    Storage:
      - Each check-in note embedding is stored in models.ReflectionEmbedding as float32 bytes.

    Retrieval:
      - For a given user_id, we load their stored vectors from SQL, build a temporary FAISS
        IndexFlatIP, and search with cosine similarity (via inner product on normalized vectors).

    This is MVP-simple and per-user only.
    """

    def __init__(self, embedder):
        if faiss is None:
            raise RuntimeError("faiss-cpu is not installed")
        self.embedder = embedder
        self.dim = int(embedder.get_sentence_embedding_dimension())

    def embed_text(self, text: str) -> np.ndarray:
        """Returns a (1, dim) normalized float32 vector."""
        vec = self.embedder.encode([text], normalize_embeddings=False)
        vec = np.asarray(vec, dtype="float32")
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        if vec.shape[1] != self.dim:
            raise ValueError(f"Embedding dim mismatch: expected {self.dim}, got {vec.shape[1]}")
        return _normalize_rows(vec)

    def add_reflection_for_checkin(
        self,
        *,
        db: Session,
        user_id: int,
        checkin: models.Checkin,
    ) -> Optional[int]:
        """
        If checkin.note exists, embed and persist it (once).
        Returns ReflectionEmbedding.id, or None if no note.
        """
        note = (checkin.note or "").strip()
        if not note:
            return None

        # Enforce 1 embedding row per check-in
        existing = (
            db.query(models.ReflectionEmbedding)
            .filter(models.ReflectionEmbedding.checkin_id == checkin.id)
            .first()
        )
        if existing:
            return int(existing.id)

        vec = self.embed_text(note)

        row = models.ReflectionEmbedding(
            user_id=user_id,
            checkin_id=checkin.id,
            checkin_date=checkin.date,
            text=note,
            embedding=vec.astype("float32").tobytes(),
        )
        db.add(row)
        db.flush()  # assign row.id
        return int(row.id)

    def query_reflections(
        self,
        *,
        db: Session,
        user_id: int,
        query_text: str,
        k: int = 5,
    ) -> List[RetrievedReflection]:
        """
        Return top-k reflections for this user relevant to query_text.
        """
        query_text = (query_text or "").strip()
        if not query_text:
            return []

        rows = (
            db.query(models.ReflectionEmbedding)
            .filter(models.ReflectionEmbedding.user_id == user_id)
            .order_by(models.ReflectionEmbedding.checkin_date.desc())
            .all()
        )
        if not rows:
            return []

        vectors: List[np.ndarray] = []
        kept_rows: List[models.ReflectionEmbedding] = []

        for r in rows:
            v = np.frombuffer(r.embedding, dtype="float32")
            if v.size != self.dim:
                # Skip any corrupted / old-dim vectors
                continue
            vectors.append(v)
            kept_rows.append(r)

        if not vectors:
            return []

        mat = np.vstack(vectors).astype("float32")
        mat = _normalize_rows(mat)

        index = faiss.IndexFlatIP(self.dim)
        index.add(mat)

        qv = self.embed_text(query_text)
        scores, idxs = index.search(qv, min(k, len(kept_rows)))

        out: List[RetrievedReflection] = []
        for score, i in zip(scores[0].tolist(), idxs[0].tolist()):
            if i < 0:
                continue
            r = kept_rows[int(i)]
            out.append(
                RetrievedReflection(
                    score=float(score),
                    checkin_date=str(r.checkin_date),
                    text=r.text,
                    reflection_id=int(r.id),
                )
            )
        return out


_RAG_SINGLETON: Optional[RagStore] = None


def get_rag_store(embedder) -> Optional[RagStore]:
    """
    Singleton accessor. Returns None if embedder/faiss not available.
    """
    if embedder is None:
        return None

    global _RAG_SINGLETON
    if _RAG_SINGLETON is not None:
        return _RAG_SINGLETON

    try:
        _RAG_SINGLETON = RagStore(embedder)
        return _RAG_SINGLETON
    except Exception:
        return None
