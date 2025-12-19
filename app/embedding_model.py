import os

_EMBEDDER = None

def get_embedder():
    enabled = os.getenv("RAG_ENABLED", "0").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return None

    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER

    model_name = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2").strip()
    try:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER = SentenceTransformer(model_name)
        return _EMBEDDER
    except Exception:
        return None
