"""Remove knowledge-base authoring notes from text shown to farmers.

The scheme articles contain sections written for the RAG builders (for example
"Namma Krushi chatbot response pattern" and "Source note") and sentences such
as "The chatbot should ...". Farmers must only see the scheme information.
"""
import re

INTERNAL_HEADINGS = (
    "chatbot", "source note", "response pattern", "rag answer", "rag ",
    "ml integration", "advisory behavior", "history data in namma krushi",
    "chat-history integration",
)
INTERNAL_SENTENCE = re.compile(
    r"\bchatbot\b|\bRAG\b|\bsource ids?\b|for the namma krushi prototype|internal prompt",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _is_internal_heading(line):
    heading = line.lstrip("# ").strip().lower() + " "
    return any(marker in heading for marker in INTERNAL_HEADINGS)


def clean_farmer_text(text, style_headings=False):
    """Return ``text`` without internal sections/sentences.

    ``style_headings`` turns Markdown headings into bold lines for display; the
    retrieval layer leaves headings untouched because other code reads them.
    """
    kept, skipping = [], False
    for line in (text or "").splitlines():
        if line.lstrip().startswith("#"):
            skipping = _is_internal_heading(line)
            if skipping:
                continue
            kept.append(f"**{line.lstrip('# ').strip()}**" if style_headings else line)
            continue
        if skipping:
            continue
        if line.strip():
            sentences = [s for s in _SENTENCE_SPLIT.split(line.strip()) if not INTERNAL_SENTENCE.search(s)]
            line = " ".join(sentences)
            if not line:
                continue
        kept.append(line)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    # A heading with no body left is not information.
    if not any(not part.strip().startswith(("#", "**")) for part in cleaned.splitlines() if part.strip()):
        return ""
    return cleaned
