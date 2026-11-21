"""
retriever.py – High-level retrieval API.
"""
from typing import List, Optional

import numpy as np

from .config import logger
from .embeddings import EmbeddingModel
from .faiss_store import load_index
from .router import route_query
from .schemas import ChunkMetadata, RetrievalResult


# Cache loaded indexes
_INDEX_CACHE = {}


def _ensure_loaded(index_name: str):
    if index_name not in _INDEX_CACHE:
        idx, meta = load_index(index_name)
        _INDEX_CACHE[index_name] = (idx, meta)
    return _INDEX_CACHE[index_name]


def retrieve(query: str, index_name: Optional[str] = None, top_k: int = 5) -> List[RetrievalResult]:
    """
    Retrieve the top-k most relevant chunks for a query.
    If index_name is None, the router decides which index to search.
    """
    if index_name is None:
        index_name = route_query(query)
    logger.info(f"Retrieving from '{index_name}' index for query: {query[:80]}...")

    idx, metadata = _ensure_loaded(index_name)
    model = EmbeddingModel.get()
    q_vec = model.embed([query])  # shape (1, dim)

    k = min(top_k, idx.ntotal)
    scores, ids = idx.search(q_vec, k)

    results: List[RetrievalResult] = []
    for score, i in zip(scores[0], ids[0]):
        if i < 0:
            continue
        chunk: ChunkMetadata = metadata[i]
        results.append(RetrievalResult(
            chunk_id=chunk.chunk_id,
            score=float(score),
            topic=chunk.topic,
            section=chunk.section,
            source_name=chunk.source_name,
            source_url=chunk.source_url,
            text=chunk.text,
        ))
    return results


def clear_cache():
    """Clear the loaded index cache (useful for reload tests)."""
    _INDEX_CACHE.clear()
