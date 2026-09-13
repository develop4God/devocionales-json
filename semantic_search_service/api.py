"""Thin HTTP wrapper over search.py/embed.py — the one place a web page or
the Flutter app calls into, instead of each client shipping its own
brute-force search and its own copy of the bge-m3 model.

Run locally:
    uv run uvicorn semantic_search_service.api:app --reload

Endpoints:
    POST /search        {"query": str, "language": str|null, "top_n": int} -> [{id, score}]
    GET  /related/{id}   ?top_n=5&same_language=false                      -> [{id, score}]
    GET  /manifest/version                                                 -> {version, count}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from semantic_search_service.embed import embed
from semantic_search_service.search import SearchIndex

app = FastAPI(title="Devocionales Semantic Search")
_index = None


def get_index():
    global _index
    if _index is None:
        _index = SearchIndex()
    return _index


class SearchRequest(BaseModel):
    query: str
    language: str | None = None
    top_n: int = 10


class SearchResult(BaseModel):
    id: str
    score: float


@app.post("/search", response_model=list[SearchResult])
def search(request: SearchRequest):
    index = get_index()
    query_vector = embed(request.query)
    results = index.search(query_vector, top_n=request.top_n, language=request.language)
    return [SearchResult(id=rid, score=score) for rid, score in results]


@app.get("/related/{entry_id}", response_model=list[SearchResult])
def related(entry_id: str, top_n: int = 5, same_language: bool = False):
    index = get_index()
    try:
        results = index.related(entry_id, top_n=top_n, same_language=same_language)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"id not found: {entry_id}")
    return [SearchResult(id=rid, score=score) for rid, score in results]


@app.get("/manifest/version")
def manifest_version():
    index = get_index()
    return {"version": index.version, "count": len(index)}
