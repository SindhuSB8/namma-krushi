"""
chunker.py – Token-aware markdown chunker using the BGE-M3 tokenizer.
Splits on markdown headings, then applies a sliding window to stay within
TARGET_TOKENS with OVERLAP_TOKENS overlap.
"""
from typing import List, Tuple

from .config import TARGET_TOKENS, OVERLAP_TOKENS, EMBEDDING_MODEL, logger
from .schemas import ChunkMetadata


def _get_tokenizer():
    """Lazy-load the tokenizer so import time is fast."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


_tokenizer = None


def _tokenizer_instance():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = _get_tokenizer()
    return _tokenizer


def _split_into_chunks(text: str) -> List[str]:
    """
    Split text into chunks that respect markdown headings and token limits.
    Returns a list of chunk text strings.
    """
    tokenizer = _tokenizer_instance()
    lines = text.split("\n")

    # Split into sections by markdown headings
    sections: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.startswith("#") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)

    chunks: List[str] = []
    for sec in sections:
        sec_text = "\n".join(sec).strip()
        if not sec_text:
            continue
        tokens = tokenizer.encode(sec_text, add_special_tokens=False)
        if len(tokens) <= TARGET_TOKENS:
            chunks.append(sec_text)
            continue
        # Sliding window
        start = 0
        while start < len(tokens):
            end = min(start + TARGET_TOKENS, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            chunks.append(chunk_text)
            if end >= len(tokens):
                break
            start = end - OVERLAP_TOKENS
    return chunks


def chunk_document(doc: dict) -> List[ChunkMetadata]:
    """
    Chunk a single document dict (from document_loader.load_documents).
    Returns a list of ChunkMetadata with 0-based chunk_index.
    """
    text = doc["text"]
    rel_path = doc["relative_path"]
    category = doc["category"]
    document_id = doc["document_id"]
    topic = doc.get("topic") or document_id
    source = doc.get("source") or {}

    result: List[ChunkMetadata] = []
    for i, chunk_text in enumerate(_split_into_chunks(text)):
        slug = document_id.replace(" ", "_").replace("-", "_")
        chunk_id = f"{category}_{slug}_{i:04d}"
        meta = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            category=category,
            topic=topic,
            section=None,
            source_name=source.get("title"),
            source_url=source.get("url"),
            language="English",
            file_path=rel_path,
            chunk_index=i,
            text=chunk_text,
        )
        result.append(meta)

    logger.debug(f"Chunked {document_id} -> {len(result)} chunks")
    return result
