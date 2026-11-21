import os
import logging
from pathlib import Path

# Movable: defaults to the project folder, override with NAMMA_KRUSHI_ROOT.
PROJECT_ROOT = Path(os.getenv("NAMMA_KRUSHI_ROOT") or Path(__file__).resolve().parents[1]).resolve()
KB_ROOT = PROJECT_ROOT / "namma_krushi_master_kb"
FAISS_ROOT = PROJECT_ROOT / "artifacts" / "faiss"

EMBEDDING_MODEL = "BAAI/bge-m3"
TARGET_TOKENS = 600
OVERLAP_TOKENS = 100

EXCLUDED_FILES = [
    "README.md",
    "00_rag_answering_policy.md",
    "rag_build_guide.md",
]

EXCLUDED_DIRS = [
    "evaluation",
    "metadata",
]

SCHEME_KEYWORDS = [
    "scheme", "subsidy", "benefit", "eligibility", "apply",
    "loan", "credit", "insurance", "pm-kisan", "pmfby",
    "kcc", "midh", "nhb", "polyhouse", "greenhouse subsidy",
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("namma_krushi_rag")
