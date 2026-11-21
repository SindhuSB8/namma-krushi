"""Use scheme articles straight from the knowledge-base folder.

``scripts/build_faiss.py`` turns the articles in ``namma_krushi_master_kb/schemes``
into the searchable index.  Until that script is re-run, any article added
after the last build would be invisible.  This module reads such articles
directly, so a new scheme works the moment its Markdown file exists.  Once the
index is rebuilt every article is in it and nothing is added here.
"""
import json
import re
from pathlib import Path

from config import ROOT

KB_ROOT = ROOT / "namma_krushi_master_kb"
MAX_CHUNK_CHARS = 1100


def _front_matter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    meta = {}
    if match:
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
        text = text[match.end():]
    return meta, text


def _sources():
    try:
        data = json.loads((KB_ROOT / "metadata" / "sources.json").read_text(encoding="utf-8"))
        return {item["id"]: item for item in data.get("sources", [])}
    except Exception:
        return {}


def _chunks(body):
    """Split on blank lines and pack paragraphs into chunks of about MAX_CHUNK_CHARS."""
    chunks, current = [], ""
    for paragraph in re.split(r"\n\s*\n", body.strip()):
        if current and len(current) + len(paragraph) > MAX_CHUNK_CHARS:
            chunks.append(current.strip())
            current = ""
        current += paragraph + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def unindexed_scheme_chunks(indexed_document_ids):
    """Chunk records (same shape as the index metadata) for articles not yet indexed."""
    folder = KB_ROOT / "schemes"
    if not folder.is_dir():
        return []
    sources, records = _sources(), []
    for path in sorted(folder.glob("*.md")):
        if path.stem in indexed_document_ids:
            continue
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        ids = re.findall(r"S\d+", meta.get("source_ids", ""))
        source = sources.get(ids[0], {}) if ids else {}
        for number, text in enumerate(_chunks(body)):
            records.append({
                "chunk_id": f"scheme_{path.stem}_{number:04d}",
                "document_id": path.stem,
                "category": "scheme",
                "topic": meta.get("title", path.stem),
                "section": None,
                "source_name": source.get("org", ""),
                "source_url": source.get("url", ""),
                "language": "English",
                "file_path": f"schemes/{path.name}",
                "chunk_index": number,
                "text": text,
            })
    return records
