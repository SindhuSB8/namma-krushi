import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    """Metadata for a single text chunk stored in metadata.jsonl"""
    chunk_id: str = Field(..., description="Deterministic ID, e.g., disease_early_blight_0001")
    document_id: str = Field(..., description="Identifier of source document (slug or file base)")
    category: str = Field(..., description="Top‑level KB category (agriculture, disease, scheme, etc.)")
    topic: str = Field(..., description="Human readable topic name (e.g., Early Blight)")
    section: Optional[str] = Field(None, description="Section heading within the document, if any")
    source_name: Optional[str] = Field(None, description="Human readable source name from sources.json")
    source_url: Optional[str] = Field(None, description="URL of the source document")
    language: str = Field(default="English", description="Document language")
    file_path: str = Field(..., description="Absolute path to the original markdown file")
    chunk_index: int = Field(..., description="0‑based index of the chunk within its document")
    text: str = Field(..., description="Chunk raw text content")

class Manifest(BaseModel):
    """Manifest describing a FAISS index and its generation parameters"""
    index_name: str = Field(..., description="Name of the index, e.g., 'agriculture'")
    embedding_model: str = Field(..., description="Model identifier used for embeddings")
    embedding_dimension: int = Field(..., description="Dimension of the dense vectors")
    chunk_count: int = Field(..., description="Total number of chunks indexed")
    source_document_count: int = Field(..., description="Number of source markdown files processed")
    created_at: str = Field(..., description="ISO‑8601 timestamp of index creation")
    chunk_size_target: int = Field(..., description="Target token count per chunk (approx.)")
    chunk_overlap_target: int = Field(..., description="Target token overlap between chunks (approx.)")
    faiss_metric: str = Field(default="IP", description="FAISS inner‑product metric (cosine after normalization)")
    version: str = Field(default="1.0")

class RetrievalResult(BaseModel):
    """Result returned by rag.retriever.retrieve* functions"""
    chunk_id: str
    score: float
    topic: Optional[str]
    section: Optional[str]
    source_name: Optional[str]
    source_url: Optional[str]
    text: str

def manifest_from_dict(data: dict) -> Manifest:
    """Helper to parse a manifest JSON dict into a Manifest model"""
    return Manifest(**data)

def chunk_metadata_from_jsonl_line(line: str) -> ChunkMetadata:
    """Parse a single JSONL line into ChunkMetadata"""
    return ChunkMetadata(**json.loads(line))
