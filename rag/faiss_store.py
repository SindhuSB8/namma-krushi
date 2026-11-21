"""
faiss_store.py – Build, save, and load FAISS IndexFlatIP indexes.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import faiss
import numpy as np

from .config import FAISS_ROOT, EMBEDDING_MODEL, TARGET_TOKENS, OVERLAP_TOKENS, logger
from .schemas import ChunkMetadata, Manifest


def build_index(chunks: List[ChunkMetadata], embeddings: np.ndarray,
                index_name: str, source_doc_count: int) -> None:
    """Build a FAISS IndexFlatIP and persist index + metadata + manifest."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    out_dir = FAISS_ROOT / index_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save FAISS index
    index_path = str(out_dir / "index.faiss")
    faiss.write_index(index, index_path)
    logger.info(f"Wrote FAISS index ({index.ntotal} vectors) -> {index_path}")

    # Save metadata JSONL
    meta_path = out_dir / "metadata.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")
    logger.info(f"Wrote metadata ({len(chunks)} rows) -> {meta_path}")

    # Save manifest
    manifest = Manifest(
        index_name=index_name,
        embedding_model=EMBEDDING_MODEL,
        embedding_dimension=dim,
        chunk_count=len(chunks),
        source_document_count=source_doc_count,
        created_at=datetime.now(timezone.utc).isoformat(),
        chunk_size_target=TARGET_TOKENS,
        chunk_overlap_target=OVERLAP_TOKENS,
    )
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))
    logger.info(f"Wrote manifest -> {manifest_path}")


def load_index(index_name: str):
    """Load a persisted FAISS index and its metadata rows."""
    idx_dir = FAISS_ROOT / index_name
    index = faiss.read_index(str(idx_dir / "index.faiss"))
    metadata: List[ChunkMetadata] = []
    with open(idx_dir / "metadata.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                metadata.append(ChunkMetadata.model_validate_json(line))
    return index, metadata
