"""Embedding provider interfaces and implementations for Text-to-SQL Agent."""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import List, Optional
import requests
from config import AppConfig, get_config


class EmbeddingServiceUnavailableError(Exception):
    """Raised when an external embedding service (e.g. Ollama) cannot be reached."""
    pass


class BaseEmbeddingProvider(ABC):
    """Abstract base class for text embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single text query."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple document chunks."""
        pass


class DeterministicTestEmbeddingProvider(BaseEmbeddingProvider):
    """High-fidelity, deterministic vectorizer for offline and CI testing.
    
    Uses n-gram character hashing with vocabulary projection and L2 normalization
    to produce stable, cosine-similarity preserving vectors without external models.
    """

    STOP_WORDS = {"the", "a", "an", "is", "in", "of", "and", "or", "did", "we", "do", "how", "many", "what", "was", "for", "with", "at", "by", "from", "on", "to"}

    def __init__(self, dimension: int = 256):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "deterministic-test"

    def _hash_token(self, token: str, dim: int) -> int:
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        return h % dim

    def embed_text(self, text: str) -> List[float]:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        for token in tokens:
            idx = self._hash_token(token, self._dim)
            if token in self.STOP_WORDS:
                vec[idx] += 0.2
            else:
                # Key domain words get strong weight
                vec[idx] += 5.0

        # Light character bi-grams for subword morphology
        clean_text = text.lower()
        for i in range(len(clean_text) - 2):
            gram = clean_text[i : i + 3]
            idx = self._hash_token(gram, self._dim)
            vec[idx] += 0.1

        # L2 normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider connecting to a local Ollama instance running nomic-embed-text."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._dimension = 768  # Standard nomic-embed-text dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def provider_name(self) -> str:
        return f"ollama/{self.model_name}"

    def embed_text(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model_name, "prompt": text}
        try:
            resp = requests.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                raise EmbeddingServiceUnavailableError(
                    f"Ollama returned HTTP {resp.status_code}: {resp.text}. "
                    f"Ensure Ollama is running and model '{self.model_name}' is pulled (`ollama pull {self.model_name}`)."
                )
            data = resp.json()
            embedding = data.get("embedding")
            if not embedding:
                raise EmbeddingServiceUnavailableError(f"Malformed response from Ollama: {data}")
            return embedding
        except requests.exceptions.RequestException as exc:
            raise EmbeddingServiceUnavailableError(
                f"Could not connect to Ollama at {self.base_url}: {exc}. "
                f"Setup instructions: 1. Install Ollama from https://ollama.com. 2. Run `ollama run {self.model_name}`."
            ) from exc

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_provider(config: Optional[AppConfig] = None) -> BaseEmbeddingProvider:
    """Factory function returning the configured embedding provider."""
    cfg = config or get_config()
    provider_type = cfg.embedding_provider.lower()

    if provider_type == "deterministic":
        return DeterministicTestEmbeddingProvider()
    elif provider_type == "ollama":
        return OllamaEmbeddingProvider(
            base_url=cfg.ollama_base_url,
            model_name=cfg.embedding_model,
        )
    else:
        # Default fallback for unknown or cloud placeholders
        return DeterministicTestEmbeddingProvider()
