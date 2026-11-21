"""
embeddings.py – Wrapper around BAAI/bge-m3 via sentence-transformers.
Produces L2-normalised dense vectors for use with FAISS IndexFlatIP.
"""
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL, logger


class EmbeddingModel:
    _instance = None  # singleton so the model is loaded only once

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading embedding model {model_name} on {device}")
        self.model = SentenceTransformer(model_name, device=device)
        self.dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.dim}")

    @classmethod
    def get(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, texts: list, batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """Encode a list of texts into L2-normalised float32 vectors."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )
        arr = np.asarray(embeddings, dtype="float32")
        if arr.ndim == 1:
            arr = arr[np.newaxis, :]
        return arr
