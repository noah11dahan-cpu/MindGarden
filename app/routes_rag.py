# app/routes_rag.py
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .db import get_db
from .security import get_current_user
from .embedding_model import get_embedder
from .rag_store import get_rag_store

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/reflections")
def query_reflections(
    q: str = Query(..., min_length=1, max_length=500, description="Free-text query for retrieving relevant reflections"),
    k: int = Query(5, ge=1, le=10, description="Number of results to return"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve up to k reflections (check-in notes) most relevant to the query for the current user.

    Behavior:
      - If RAG is disabled/unavailable (no embedder or no FAISS), returns empty results with rag_enabled=False.
      - Per-user only: only returns reflections stored for current_user.id.
    """
    embedder = get_embedder()
    rag = get_rag_store(embedder) if embedder is not None else None

    if rag is None:
        return {"query": q, "k": k, "rag_enabled": False, "results": []}

    results = rag.query_reflections(db=db, user_id=current_user.id, query_text=q, k=k)

    return {
        "query": q,
        "k": k,
        "rag_enabled": True,
        "results": [
            {
                "score": r.score,
                "checkin_date": r.checkin_date,
                "text": r.text,
                "reflection_id": r.reflection_id,
            }
            for r in results
        ],
    }
