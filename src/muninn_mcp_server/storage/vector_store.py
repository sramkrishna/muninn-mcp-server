"""ChromaDB-based vector storage for semantic search."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from muninn_mcp_server.embeddings.local_embedder import LocalEmbedder


class VectorStore:
    """ChromaDB-based vector storage with local embeddings."""

    def __init__(self, storage_path: Optional[Path] = None, embedder: Optional[LocalEmbedder] = None):
        """Initialize vector store.

        Args:
            storage_path: Path to ChromaDB storage. Defaults to ~/.local/share/muninn/chroma
            embedder: LocalEmbedder instance. If None, creates default embedder.
        """
        if storage_path is None:
            storage_path = Path.home() / ".local" / "share" / "muninn" / "chroma"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.embedder = embedder or LocalEmbedder()

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.storage_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Create collections
        self.events_collection = self.client.get_or_create_collection(
            name="events",
            metadata={"description": "Desktop events with semantic search"}
        )

        self.decisions_collection = self.client.get_or_create_collection(
            name="decisions",
            metadata={"description": "Agent decisions with reasoning"}
        )

        self.interactions_collection = self.client.get_or_create_collection(
            name="interactions",
            metadata={"description": "Contact interactions for CRM"}
        )

    def store_event_embedding(
        self,
        event_id: int,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store event embedding.

        Args:
            event_id: SQLite event ID
            description: Event description to embed
            metadata: Additional metadata

        Returns:
            Embedding ID (UUID)
        """
        embedding_id = str(uuid.uuid4())
        embedding = self.embedder.embed(description)

        metadata = metadata or {}
        metadata['event_id'] = event_id

        self.events_collection.add(
            embeddings=[embedding],
            documents=[description],
            metadatas=[metadata],
            ids=[embedding_id]
        )

        return embedding_id

    def store_decision_embedding(
        self,
        decision_id: int,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store decision embedding.

        Args:
            decision_id: SQLite decision ID
            reasoning: Decision reasoning to embed
            metadata: Additional metadata

        Returns:
            Embedding ID (UUID)
        """
        embedding_id = str(uuid.uuid4())
        embedding = self.embedder.embed(reasoning)

        metadata = metadata or {}
        metadata['decision_id'] = decision_id

        self.decisions_collection.add(
            embeddings=[embedding],
            documents=[reasoning],
            metadatas=[metadata],
            ids=[embedding_id]
        )

        return embedding_id

    def semantic_search_events(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search over events.

        Args:
            query: Search query
            limit: Maximum results
            where: Optional metadata filters

        Returns:
            List of matching events with similarity scores
        """
        query_embedding = self.embedder.embed(query)

        results = self.events_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )

        # Format results
        matches = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                matches.append({
                    'embedding_id': results['ids'][0][i],
                    'description': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })

        return matches

    def semantic_search_decisions(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search over decisions.

        Args:
            query: Search query
            limit: Maximum results
            where: Optional metadata filters

        Returns:
            List of matching decisions with similarity scores
        """
        query_embedding = self.embedder.embed(query)

        results = self.decisions_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )

        # Format results
        matches = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                matches.append({
                    'embedding_id': results['ids'][0][i],
                    'reasoning': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })

        return matches

    def get_event_by_embedding_id(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        """Get event by embedding ID.

        Args:
            embedding_id: Embedding UUID

        Returns:
            Event data or None if not found
        """
        results = self.events_collection.get(ids=[embedding_id])

        if results['ids']:
            return {
                'embedding_id': results['ids'][0],
                'description': results['documents'][0],
                'metadata': results['metadatas'][0]
            }

        return None

    def delete_event_embedding(self, embedding_id: str):
        """Delete event embedding.

        Args:
            embedding_id: Embedding UUID to delete
        """
        self.events_collection.delete(ids=[embedding_id])

    def delete_decision_embedding(self, embedding_id: str):
        """Delete decision embedding.

        Args:
            embedding_id: Embedding UUID to delete
        """
        self.decisions_collection.delete(ids=[embedding_id])

    def store_interaction_embedding(
        self,
        interaction_id: int,
        summary: str,
        subject: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store interaction embedding.

        Args:
            interaction_id: SQLite interaction ID
            summary: Interaction summary to embed
            subject: Optional subject line (combined with summary for better context)
            metadata: Additional metadata

        Returns:
            Embedding ID (UUID)
        """
        embedding_id = str(uuid.uuid4())

        # Combine subject and summary for richer embedding
        text_to_embed = f"{subject}: {summary}" if subject else summary
        embedding = self.embedder.embed(text_to_embed)

        metadata = metadata or {}
        metadata['interaction_id'] = interaction_id

        self.interactions_collection.add(
            embeddings=[embedding],
            documents=[text_to_embed],
            metadatas=[metadata],
            ids=[embedding_id]
        )

        return embedding_id

    def semantic_search_interactions(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search over interactions.

        Args:
            query: Search query
            limit: Maximum results
            where: Optional metadata filters

        Returns:
            List of matching interactions with similarity scores
        """
        query_embedding = self.embedder.embed(query)

        results = self.interactions_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )

        # Format results
        matches = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                matches.append({
                    'embedding_id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })

        return matches

    def delete_interaction_embedding(self, embedding_id: str):
        """Delete interaction embedding.

        Args:
            embedding_id: Embedding UUID to delete
        """
        self.interactions_collection.delete(ids=[embedding_id])

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings.

        Returns:
            Dictionary with collection statistics
        """
        return {
            'events_count': self.events_collection.count(),
            'decisions_count': self.decisions_collection.count(),
            'interactions_count': self.interactions_collection.count(),
            'embedding_dimension': self.embedder.get_dimension(),
            'model': self.embedder.model_name
        }
