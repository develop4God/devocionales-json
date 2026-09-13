"""Query-time embedding — loads the same bge-m3 model used to build the
committed corpus vectors, so a free-form search phrase lands in the same
vector space. Model load is lazy/cached: importing this module doesn't
pull ~2GB of weights, only the first embed() call does.
"""

from sentence_transformers import SentenceTransformer

from semantic_search_service.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.model_name, device="cpu", trust_remote_code=True)
    return _model


def embed(text):
    """Encode a single query string to a unit-normalized vector, no prefix
    (bge-m3, unlike e5-small/e5-base, needs no "query: " prefix)."""
    vector = _get_model().encode([text], normalize_embeddings=True)[0]
    return vector
