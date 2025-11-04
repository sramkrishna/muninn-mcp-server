"""Local embedding generation using sentence-transformers."""

from typing import List, Union
from sentence_transformers import SentenceTransformer


class LocalEmbedder:
    """Local embedding model wrapper."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize local embedder.

        Args:
            model_name: Name of sentence-transformers model to use.
                       Default is all-MiniLM-L6-v2 (fast, 80MB, good quality)
        """
        self.model_name = model_name
        self.model = None

    def _ensure_loaded(self):
        """Lazy load the model on first use."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text.

        Args:
            text: Single text string or list of strings

        Returns:
            Embedding vector(s)
        """
        self._ensure_loaded()

        # Convert single string to list for consistent processing
        is_single = isinstance(text, str)
        texts = [text] if is_single else text

        # Generate embeddings
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # Return single embedding if input was single string
        if is_single:
            return embeddings[0].tolist()

        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding vector dimension
        """
        self._ensure_loaded()
        return self.model.get_sentence_embedding_dimension()
