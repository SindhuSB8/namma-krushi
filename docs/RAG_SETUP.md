# Namma Krushi – RAG Pipeline Setup

## Overview
This RAG (Retrieval-Augmented Generation) pipeline provides agricultural
advisory retrieval for the Namma Krushi greenhouse tomato cultivation system.

## Components
| Module | Purpose |
|--------|---------|
| `rag/config.py` | Constants, paths, logging |
| `rag/schemas.py` | Pydantic data models |
| `rag/document_loader.py` | Load & classify KB markdown files |
| `rag/chunker.py` | Token-aware markdown chunking (BGE-M3 tokenizer) |
| `rag/embeddings.py` | BAAI/bge-m3 dense embeddings |
| `rag/faiss_store.py` | Build / load FAISS IndexFlatIP |
| `rag/router.py` | Keyword-based query routing |
| `rag/retriever.py` | High-level retrieval API |
| `rag/helpers.py` | Disease & greenhouse feature helpers |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build both indexes
python scripts/build_faiss.py

# Test retrieval
python scripts/test_retrieval.py

# Inspect indexes
python scripts/inspect_faiss.py
```

## Indexes
- **agriculture** – agriculture, diseases, pests, farmer advisory
- **schemes** – government schemes and subsidies

## Embedding Model
- Model: `BAAI/bge-m3`
- Vectors are L2-normalised; FAISS uses `IndexFlatIP` (cosine similarity)

## Chunking
- Target: 600 tokens, Overlap: 100 tokens
- Tokenizer: BGE-M3 tokenizer (via HuggingFace transformers)
- Markdown heading-aware splitting
