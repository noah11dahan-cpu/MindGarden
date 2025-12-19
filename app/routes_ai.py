from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from .security import get_current_user

from app.services.ai_suggestions import (
    fetch_last_7_checkins,
    build_features,
    rule_based_suggestion,
    maybe_ollama_polish,
)

# Day 8 (RAG)
from .embedding_model import get_embedder
from .rag_store import get_rag_store

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/suggestions")
async def get_ai_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    checkins = fetch_last_7_checkins(db, user.id)
    features = build_features(checkins)
    suggestion, tone, ctx = rule_based_suggestion(features)

    # Day 8: Retrieve relevant past reflections (per-user) and inject into context
    try:
        embedder = get_embedder()
        rag = get_rag_store(embedder) if embedder is not None else None

        if rag is not None:
            # Use the latest note as the query if available; otherwise fall back to a generic query.
            latest_note = ""
            if checkins:
                latest_note = (checkins[0].note or "").strip()

            query_text = latest_note if latest_note else "recent mood and habits"

            retrieved = rag.query_reflections(
                db=db,
                user_id=user.id,
                query_text=query_text,
                k=5,
            )

            memories = [
                {
                    "score": r.score,
                    "checkin_date": r.checkin_date,
                    "text": r.text,
                    "reflection_id": r.reflection_id,
                }
                for r in retrieved
            ]

            # Make the memories available to the suggestion generator/polisher
            ctx["retrieved_reflections"] = memories
    except Exception:
        # RAG is optional; suggestions must still work if model/FAISS aren't available.
        pass

    suggestion = await maybe_ollama_polish(suggestion, tone, ctx)

    return {"suggestion": suggestion, "tone": tone, "context": ctx}
