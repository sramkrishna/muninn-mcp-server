#!/usr/bin/env python3
"""Quick test script to verify Muninn is working."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from muninn_mcp_server.storage.sqlite_store import SQLiteStore
from muninn_mcp_server.storage.vector_store import VectorStore
from muninn_mcp_server.embeddings.local_embedder import LocalEmbedder
from muninn_mcp_server.schemas.models import Event, Pattern, Decision


def test_basic_functionality():
    """Test basic Muninn functionality."""
    print("🧪 Testing Muninn Memory Server\n")

    # Setup temporary storage
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test.db"
    chroma_path = temp_dir / "chroma"

    print("1. Initializing storage backends...")
    embedder = LocalEmbedder()
    print(f"   ✓ Embedding model: {embedder.model_name}")

    sqlite_store = SQLiteStore(db_path=db_path)
    print(f"   ✓ SQLite: {db_path}")

    vector_store = VectorStore(storage_path=chroma_path, embedder=embedder)
    print(f"   ✓ ChromaDB: {chroma_path}\n")

    # Test event storage
    print("2. Testing event storage...")
    event = Event(
        event_type="test_event",
        data={"test": "data"},
        description="This is a test event for Muninn"
    )
    event_id = sqlite_store.store_event(event)
    print(f"   ✓ Stored event with ID: {event_id}")

    embedding_id = vector_store.store_event_embedding(
        event_id=event_id,
        description=event.description,
        metadata={"event_type": event.event_type}
    )
    print(f"   ✓ Stored embedding: {embedding_id}\n")

    # Test retrieval
    print("3. Testing event retrieval...")
    events = sqlite_store.get_recent_events(limit=1)
    print(f"   ✓ Retrieved {len(events)} event(s)")
    print(f"   ✓ Event type: {events[0]['event_type']}\n")

    # Test semantic search
    print("4. Testing semantic search...")
    results = vector_store.semantic_search_events(
        query="test event",
        limit=5
    )
    print(f"   ✓ Found {len(results)} result(s)")
    if results:
        print(f"   ✓ Distance: {results[0]['distance']:.4f}\n")

    # Test pattern storage
    print("5. Testing pattern storage...")
    pattern = Pattern(
        pattern_type="test_pattern",
        description="Test pattern detection",
        confidence=0.95
    )
    pattern_id = sqlite_store.store_pattern(pattern)
    print(f"   ✓ Stored pattern with ID: {pattern_id}\n")

    # Test decision storage
    print("6. Testing decision storage...")
    decision = Decision(
        action="test_action",
        reasoning="Testing decision storage",
        context={"test": True},
        success=True
    )
    decision_id = sqlite_store.store_decision(decision)
    print(f"   ✓ Stored decision with ID: {decision_id}")

    decision_embedding_id = vector_store.store_decision_embedding(
        decision_id=decision_id,
        reasoning=decision.reasoning,
        metadata={"action": decision.action}
    )
    print(f"   ✓ Stored decision embedding: {decision_embedding_id}\n")

    # Test statistics
    print("7. Testing statistics...")
    stats = sqlite_store.get_statistics()
    print(f"   ✓ Total events: {stats['total_events']}")
    print(f"   ✓ Total patterns: {stats['total_patterns']}")
    print(f"   ✓ Total decisions: {stats['total_decisions']}")

    vector_stats = vector_store.get_collection_stats()
    print(f"   ✓ Event embeddings: {vector_stats['events_count']}")
    print(f"   ✓ Decision embeddings: {vector_stats['decisions_count']}")
    print(f"   ✓ Embedding dimension: {vector_stats['embedding_dimension']}\n")

    # Cleanup
    sqlite_store.close()
    import shutil
    shutil.rmtree(temp_dir)

    print("✅ All tests passed! Muninn is working correctly.\n")
    print("Next steps:")
    print("  1. Install: pip install -e .")
    print("  2. Add to Hugin config.toml")
    print("  3. Start using with: ./run-local.sh")


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
