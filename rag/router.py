"""
router.py – Deterministic keyword-based router.
Routes a query to either the 'agriculture' or 'schemes' FAISS index.
"""
from .config import SCHEME_KEYWORDS, logger


def route_query(query: str) -> str:
    """Return the index name ('agriculture' or 'schemes') for a query."""
    q_lower = query.lower()
    for kw in SCHEME_KEYWORDS:
        if kw in q_lower:
            logger.debug(f"Routed to 'schemes' (matched keyword '{kw}')")
            return "schemes"
    logger.debug("Routed to 'agriculture' (no scheme keywords matched)")
    return "agriculture"
