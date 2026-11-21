"""Central, movable-path configuration for Namma Krushi."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
DATABASE_PATH = ROOT / "database" / "namma_krushi.db"
UPLOADS = ROOT / "uploads" / "disease_images"
FAISS_ROOT = ARTIFACTS / "faiss"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
# Fast lexical search uses the persisted RAG metadata and does not load a
# multi-gigabyte Torch embedding model during a farmer chat. Set to
# ``semantic`` only on machines provisioned for BGE-M3 inference.
RAG_RETRIEVAL_MODE = os.getenv("RAG_RETRIEVAL_MODE", "lexical").lower()
ENABLE_OLLAMA = os.getenv("ENABLE_OLLAMA", "0") == "1"

GREENHOUSE_FEATURES = ["temperature", "humidity", "soil_moisture", "light_intensity", "co2"]

# Render-safe flags: do not eagerly load heavy models on 512 MB Render dynos.
IS_RENDER = bool(os.getenv("RENDER"))
ENABLE_WHISPER = os.getenv("ENABLE_WHISPER", "0" if IS_RENDER else "1") == "1"
