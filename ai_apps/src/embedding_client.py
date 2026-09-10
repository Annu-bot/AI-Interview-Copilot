"""
Vector Embedding Client supporting dual routing:
1. Cloud API (Google Gemini models/gemini-embedding-001 / models/gemini-embedding-2) - Default
2. Local Embedding Engine (Ollama / Local Embeddings) when LOCAL_EMBED=True
"""

import logging
import hashlib
import numpy as np
from typing import List
import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Unified Vector Embedding Client for RAG pipeline with automatic cloud model fallback.
    """

    def __init__(self):
        self.use_local = settings.is_local_embed
        self.gemini_model = settings.GEMINI_EMBEDDING_MODEL
        self.local_base_url = settings.LOCAL_EMBEDDING_BASE_URL
        self.local_model = settings.LOCAL_EMBEDDING_MODEL
        self._active_cloud_model = None
        self._init_client()

    def _init_client(self):
        """Initializes the active embedding backend."""
        if not self.use_local and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._active_cloud_model = self.gemini_model
                logger.info(f"Initialized Cloud Gemini Embedding Client ({self._active_cloud_model})")
            except Exception as e:
                logger.warning(f"Could not configure google.generativeai for embeddings: {e}")
        else:
            logger.info(f"Initialized Local Embedding Client ({self.local_model} at {self.local_base_url})")

    def get_embedding(self, text: str) -> List[float]:
        """Generates a vector embedding for a single text chunk."""
        if not text or not text.strip():
            return [0.0] * 768

        if self.use_local:
            return self._get_local_embedding(text)
        else:
            return self._get_cloud_embedding(text)

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates vector embeddings for a list of text chunks."""
        if not texts:
            return []

        embeddings = []
        for text in texts:
            emb = self.get_embedding(text)
            embeddings.append(emb)
        return embeddings

    def _get_cloud_embedding(self, text: str) -> List[float]:
        """
        Calls Google Gemini Embeddings API with graceful multi-model fallback.
        Tries active model first, then known supported models.
        """
        candidate_models = [
            self._active_cloud_model or self.gemini_model,
            "models/gemini-embedding-001",
            "models/gemini-embedding-2",
            "models/gemini-embedding-2-preview"
        ]
        # Remove duplicates while preserving order
        unique_models = list(dict.fromkeys(m for m in candidate_models if m))

        import google.generativeai as genai

        for model_name in unique_models:
            try:
                result = genai.embed_content(
                    model=model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                if "embedding" in result and result["embedding"]:
                    self._active_cloud_model = model_name
                    return result["embedding"]
            except Exception as e:
                logger.debug(f"Gemini embedding model '{model_name}' failed ({e}), trying next candidate...")

        logger.warning("All Cloud Gemini embedding candidates failed, falling back to deterministic local embedding")
        return self._generate_deterministic_embedding(text)

    def _get_local_embedding(self, text: str) -> List[float]:
        """
        Calls local Ollama embeddings endpoint (e.g. nomic-embed-text)
        or falls back to fast local vector generation.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(
                    f"{self.local_base_url}/api/embeddings",
                    json={"model": self.local_model, "prompt": text}
                )
                if res.status_code == 200:
                    data = res.json()
                    if "embedding" in data:
                        return data["embedding"]
        except Exception as e:
            logger.debug(f"Local Ollama embedding endpoint unreachable: {e}")

        # Fallback to local semantic vector
        return self._generate_deterministic_embedding(text)

    def _generate_deterministic_embedding(self, text: str, dim: int = 768) -> List[float]:
        """
        Generates a normalized deterministic dense vector from text tokens
        for robust offline fallback without breaking the RAG pipeline.
        """
        tokens = text.lower().split()
        vec = np.zeros(dim, dtype=np.float32)

        if not tokens:
            return vec.tolist()

        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 1000) / 1000.0 - 0.5
            vec[idx] += float(val)

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()


# Global Singleton Instance
embedding_client = EmbeddingClient()
