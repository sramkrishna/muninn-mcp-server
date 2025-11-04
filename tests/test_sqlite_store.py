"""Tests for SQLite storage backend."""

import pytest
import tempfile
from pathlib import Path

from muninn_mcp_server.storage.sqlite_store import SQLiteStore
from muninn_mcp_server.schemas.models import Event, Pattern, Decision


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = SQLiteStore(db_path=db_path)
    yield store

    store.close()
    db_path.unlink()


def test_store_and_retrieve_event(temp_db):
    """Test storing and retrieving an event."""
    event = Event(
        event_type="extension_change",
        data={"extension": "dash-to-panel", "action": "disabled"},
        description="Disabled dash-to-panel extension"
    )

    event_id = temp_db.store_event(event)
    assert event_id > 0

    events = temp_db.get_recent_events(limit=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "extension_change"


def test_query_events_by_type(temp_db):
    """Test querying events by type."""
    # Store multiple events
    temp_db.store_event(Event(
        event_type="app_launch",
        data={"app": "firefox"},
        description="Launched Firefox"
    ))
    temp_db.store_event(Event(
        event_type="app_launch",
        data={"app": "terminal"},
        description="Launched Terminal"
    ))
    temp_db.store_event(Event(
        event_type="extension_change",
        data={"extension": "test"},
        description="Changed extension"
    ))

    app_events = temp_db.query_events(event_type="app_launch")
    assert len(app_events) == 2


def test_store_and_retrieve_pattern(temp_db):
    """Test storing and retrieving patterns."""
    pattern = Pattern(
        pattern_type="morning_workflow",
        description="User opens terminal, browser, and code editor every morning",
        confidence=0.85,
        occurrence_count=5
    )

    pattern_id = temp_db.store_pattern(pattern)
    assert pattern_id > 0

    patterns = temp_db.get_patterns()
    assert len(patterns) == 1
    assert patterns[0]["confidence"] == 0.85


def test_store_and_retrieve_decision(temp_db):
    """Test storing and retrieving decisions."""
    decision = Decision(
        action="disable_extension",
        reasoning="Extension causing repeated crashes",
        context={"extension": "test-extension", "crash_count": 5},
        outcome="Success",
        success=True
    )

    decision_id = temp_db.store_decision(decision)
    assert decision_id > 0

    decisions = temp_db.get_recent_decisions(limit=1)
    assert len(decisions) == 1
    assert decisions[0]["action"] == "disable_extension"
    assert decisions[0]["success"] == 1  # SQLite stores as integer


def test_get_statistics(temp_db):
    """Test statistics aggregation."""
    # Store some data
    temp_db.store_event(Event(
        event_type="test",
        data={},
        description="Test event"
    ))
    temp_db.store_pattern(Pattern(
        pattern_type="test",
        description="Test pattern",
        confidence=0.9
    ))
    temp_db.store_decision(Decision(
        action="test",
        reasoning="Test decision",
        context={},
        success=True
    ))

    stats = temp_db.get_statistics()
    assert stats["total_events"] == 1
    assert stats["total_patterns"] == 1
    assert stats["total_decisions"] == 1
    assert stats["successful_decisions"] == 1
