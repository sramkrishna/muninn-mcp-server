"""Tests for vector storage backend."""

import pytest
import tempfile
from pathlib import Path

from muninn_mcp_server.storage.vector_store import VectorStore
from muninn_mcp_server.embeddings.local_embedder import LocalEmbedder


@pytest.fixture
def temp_vector_store():
    """Create a temporary vector store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "chroma"
        embedder = LocalEmbedder()
        store = VectorStore(storage_path=storage_path, embedder=embedder)
        yield store


def test_store_and_search_event(temp_vector_store):
    """Test storing and searching events."""
    embedding_id = temp_vector_store.store_event_embedding(
        event_id=1,
        description="GNOME Shell crashed due to extension error",
        metadata={"event_type": "error"}
    )

    assert embedding_id is not None

    # Search for similar events
    results = temp_vector_store.semantic_search_events(
        query="extension causing crashes",
        limit=5
    )

    assert len(results) > 0
    assert results[0]["embedding_id"] == embedding_id


def test_store_and_search_decision(temp_vector_store):
    """Test storing and searching decisions."""
    embedding_id = temp_vector_store.store_decision_embedding(
        decision_id=1,
        reasoning="Disabled problematic extension to prevent further crashes",
        metadata={"action": "disable_extension"}
    )

    assert embedding_id is not None

    # Search for similar decisions
    results = temp_vector_store.semantic_search_decisions(
        query="preventing crashes",
        limit=5
    )

    assert len(results) > 0
    assert results[0]["embedding_id"] == embedding_id


def test_semantic_similarity(temp_vector_store):
    """Test that semantically similar items are found."""
    # Store related events
    temp_vector_store.store_event_embedding(
        event_id=1,
        description="Application froze and became unresponsive",
        metadata={"event_type": "error"}
    )
    temp_vector_store.store_event_embedding(
        event_id=2,
        description="System crashed unexpectedly",
        metadata={"event_type": "error"}
    )
    temp_vector_store.store_event_embedding(
        event_id=3,
        description="Opened Firefox browser",
        metadata={"event_type": "app_launch"}
    )

    # Search for stability issues
    results = temp_vector_store.semantic_search_events(
        query="stability problems and crashes",
        limit=3
    )

    # The two crash-related events should be more similar than the app launch
    assert len(results) == 3
    # First two results should have smaller distances (more similar)
    assert results[0]["distance"] < results[2]["distance"]
    assert results[1]["distance"] < results[2]["distance"]


def test_get_collection_stats(temp_vector_store):
    """Test getting collection statistics."""
    temp_vector_store.store_event_embedding(
        event_id=1,
        description="Test event",
        metadata={}
    )
    temp_vector_store.store_decision_embedding(
        decision_id=1,
        reasoning="Test decision",
        metadata={}
    )

    stats = temp_vector_store.get_collection_stats()
    assert stats["events_count"] == 1
    assert stats["decisions_count"] == 1
    assert stats["embedding_dimension"] > 0
    assert "MiniLM" in stats["model"]


def test_delete_embedding(temp_vector_store):
    """Test deleting embeddings."""
    embedding_id = temp_vector_store.store_event_embedding(
        event_id=1,
        description="Test event to delete",
        metadata={}
    )

    # Verify it exists
    results = temp_vector_store.semantic_search_events(
        query="test event",
        limit=1
    )
    assert len(results) == 1

    # Delete it
    temp_vector_store.delete_event_embedding(embedding_id)

    # Verify it's gone
    stats = temp_vector_store.get_collection_stats()
    assert stats["events_count"] == 0
