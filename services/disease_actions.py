"""Plain-language "what should I do?" text for a saved disease scan.

English text comes from the project's own disease knowledge base
(``namma_krushi_master_kb/diseases/*.md``). Kannada text comes from the
reviewed Kannada advice already used by the AI Advisory page. Nothing is
generated or invented here.
"""
import re
from functools import lru_cache

from config import ROOT
from services.localization import localize_disease_advice

KB_DIR = ROOT / "namma_krushi_master_kb" / "diseases"

# punctuation-insensitive fragment of the CNN class name -> knowledge-base file
_FILES = (
    ("bacterialspot", "02_bacterial_spot.md"),
    ("earlyblight", "03_early_blight.md"),
    ("lateblight", "04_late_blight.md"),
    ("leafmold", "05_leaf_mold.md"),
    ("septoria", "06_septoria_leaf_spot.md"),
    ("yellowleafcurl", "07_tomato_yellow_leaf_curl_virus.md"),
    ("mosaic", "08_tomato_mosaic_virus.md"),
    ("powderymildew", "09_powdery_mildew.md"),
    ("targetspot", "10_target_spot.md"),
    ("spidermite", "11_spider_mites_two_spotted.md"),
    ("healthy", "01_healthy_tomato.md"),
)


def _kb_file(disease):
    key = re.sub(r"[^a-z0-9]+", "", (disease or "").lower())
    for fragment, filename in _FILES:
        if fragment in key:
            return KB_DIR / filename
    return None


@lru_cache(maxsize=32)
def _read_sections(path_str):
    """Return (about, actions) from one knowledge-base article."""
    try:
        text = open(path_str, encoding="utf-8").read()
    except OSError:
        return None, None
    text = re.sub(r"\A---.*?---\s*", "", text, count=1, flags=re.S)       # front matter
    text = re.split(r"^## Source note", text, maxsplit=1, flags=re.M)[0]   # boilerplate
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    intro = parts[0]
    sections = {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    paragraphs = [p.strip() for p in intro.split("\n\n") if p.strip() and not p.startswith("#")]
    about = paragraphs[0] if paragraphs else None
    actions = sections.get("management principles")
    if not actions:  # e.g. the "healthy" article has no management section
        actions = "\n\n".join(paragraphs[1:]) or None
    return about, actions


def disease_action_plan(disease, language):
    """``{"about": str|None, "actions": str|None}`` for a CNN class name."""
    if language == "Kannada":
        return {"about": None, "actions": localize_disease_advice(disease, "Kannada")}
    path = _kb_file(disease)
    if path is None:
        return {"about": None, "actions": None}
    about, actions = _read_sections(str(path))
    return {"about": about, "actions": actions}
