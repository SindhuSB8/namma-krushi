"""
document_loader.py – Load markdown documents from the KB, parse YAML frontmatter,
attach source metadata using source_ids from sources.json (with fallback to sources.csv),
and categorize them into 'agriculture' or 'schemes' index buckets.
"""
import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import KB_ROOT, EXCLUDED_FILES, EXCLUDED_DIRS, logger


def _load_sources_map() -> Dict[str, Dict[str, Any]]:
    """
    Load source metadata keyed by source_id (e.g. 'S01', 'S02').
    Primary: metadata/sources.json
    Fallback / enrichment: metadata/sources.csv
    """
    sources_map: Dict[str, Dict[str, Any]] = {}

    # 1. Primary: sources.json
    json_path = KB_ROOT / "metadata" / "sources.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("sources", [])
            for item in items:
                sid = item.get("id")
                if sid:
                    sources_map[sid] = {
                        "id": sid,
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "org": item.get("org", ""),
                        "topics": item.get("topics", []),
                    }
        except Exception as e:
            logger.warning(f"Error reading sources.json: {e}")

    # 2. Fallback / enrichment: sources.csv
    csv_path = KB_ROOT / "metadata" / "sources.csv"
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = row.get("source_id") or row.get("id")
                    if sid and sid not in sources_map:
                        sources_map[sid] = {
                            "id": sid,
                            "title": row.get("title", ""),
                            "url": row.get("url", ""),
                            "org": row.get("organization", "") or row.get("org", ""),
                            "topics": [t.strip() for t in row.get("topics", "").split(";") if t.strip()],
                        }
        except Exception as e:
            logger.warning(f"Error reading sources.csv: {e}")

    logger.info(f"Loaded {len(sources_map)} sources from metadata")
    return sources_map


def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Extract YAML frontmatter and body text from markdown.
    Uses regex to avoid strict yaml dependency issues.
    """
    meta: Dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()

            # Parse title
            m = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', fm_text, re.MULTILINE)
            if m:
                meta["title"] = m.group(1).strip()

            # Parse category
            m = re.search(r'^category:\s*["\']?(.*?)["\']?\s*$', fm_text, re.MULTILINE)
            if m:
                meta["category"] = m.group(1).strip()

            # Parse source_ids: ["S01", "S06", "S07"]
            m = re.search(r'source_ids:\s*\[(.*?)\]', fm_text)
            if m:
                raw_ids = m.group(1)
                sids = [s.strip().strip('"\'') for s in raw_ids.split(",") if s.strip()]
                meta["source_ids"] = sids

    return meta, body


def _classify_category(rel_path: str, fm_category: Optional[str] = None) -> str:
    """Determine category from frontmatter or directory structure."""
    if fm_category:
        cat = fm_category.lower()
        if cat in ("agriculture", "disease", "pest", "farmer_advisory", "scheme"):
            return cat

    parts = Path(rel_path).parts
    if parts:
        top = parts[0].lower()
        if top in ("agriculture",):
            return "agriculture"
        elif top in ("diseases",):
            return "disease"
        elif top in ("pests",):
            return "pest"
        elif top in ("farmer_advisory",):
            return "farmer_advisory"
        elif top in ("schemes",):
            return "scheme"
    return "agriculture"


def _is_excluded(rel_path: Path) -> bool:
    """Check whether a file should be excluded from indexing."""
    if rel_path.name in EXCLUDED_FILES:
        return True
    parts = rel_path.parts
    for d in EXCLUDED_DIRS:
        if d in parts:
            return True
    return False


def load_documents() -> List[Dict[str, Any]]:
    """
    Walk the KB directory, parse frontmatter, attach source metadata,
    and return document dicts.
    """
    sources_map = _load_sources_map()
    docs: List[Dict[str, Any]] = []

    for md_path in sorted(KB_ROOT.rglob("*.md")):
        rel_path = md_path.relative_to(KB_ROOT)
        if _is_excluded(rel_path):
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            continue

        fm_meta, body = _parse_frontmatter(content)
        category = _classify_category(str(rel_path), fm_meta.get("category"))
        document_id = rel_path.stem
        topic = fm_meta.get("title") or document_id

        # Attach source metadata
        source_data: Dict[str, Any] = {}
        sids = fm_meta.get("source_ids", [])
        if sids:
            # Match primary source_id
            for sid in sids:
                if sid in sources_map:
                    source_data = sources_map[sid]
                    break

        # Fallback: if no source_ids or not found, try stem match
        if not source_data:
            for sid, sinfo in sources_map.items():
                if sid == document_id or sid.lower() == document_id.lower():
                    source_data = sinfo
                    break

        docs.append({
            "text": body,  # clean body without YAML frontmatter header
            "relative_path": str(rel_path).replace("\\", "/"),
            "category": category,
            "document_id": document_id,
            "topic": topic,
            "source": source_data,
        })

    logger.info(f"Loaded {len(docs)} documents from KB")
    return docs
