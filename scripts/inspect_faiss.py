"""
inspect_faiss.py – Inspect FAISS indexes: counts, dimensions, sample metadata.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faiss
from pathlib import Path
from rag.config import FAISS_ROOT


def inspect_index(name: str):
    idx_dir = FAISS_ROOT / name
    print(f"\n{'=' * 50}")
    print(f"INDEX: {name}")
    print(f"{'=' * 50}")

    # Load FAISS index
    index_path = idx_dir / "index.faiss"
    if not index_path.exists():
        print(f"  ERROR: {index_path} not found!")
        return
    index = faiss.read_index(str(index_path))
    print(f"  index.ntotal   = {index.ntotal}")
    print(f"  index.d        = {index.d}")

    # Count metadata rows
    meta_path = idx_dir / "metadata.jsonl"
    meta_count = 0
    sample_rows = []
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    meta_count += 1
                    if i < 3:
                        sample_rows.append(json.loads(line))
    print(f"  metadata rows  = {meta_count}")
    print(f"  MATCH: {'YES' if index.ntotal == meta_count else 'NO !!!'}")

    # Load manifest
    manifest_path = idx_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"  embedding_model     = {manifest.get('embedding_model')}")
        print(f"  embedding_dimension = {manifest.get('embedding_dimension')}")
        print(f"  chunk_count         = {manifest.get('chunk_count')}")
        print(f"  source_doc_count    = {manifest.get('source_document_count')}")
        print(f"  created_at          = {manifest.get('created_at')}")

    # Sample metadata
    if sample_rows:
        print(f"\n  Sample chunks:")
        for s in sample_rows:
            print(f"    chunk_id:   {s.get('chunk_id')}")
            print(f"    file_path:  {s.get('file_path')}")
            print(f"    topic:      {s.get('topic')}")
            print(f"    source_url: {s.get('source_url', 'N/A')}")
            print()

    # Source URL coverage
    if meta_path.exists():
        total = 0
        with_url = 0
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    total += 1
                    if row.get("source_url"):
                        with_url += 1
        pct = (with_url / total * 100) if total else 0
        print(f"  Source URL coverage: {with_url}/{total} ({pct:.1f}%)")


def main():
    for name in ["agriculture", "schemes"]:
        inspect_index(name)


if __name__ == "__main__":
    main()
