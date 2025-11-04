"""SQLite storage backend for structured data."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from muninn_mcp_server.schemas.models import Event, Pattern, Decision, Interaction, ContactNote


class SQLiteStore:
    """SQLite-based storage for events, patterns, and decisions."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.local/share/muninn/muninn.db
        """
        if db_path is None:
            db_path = Path.home() / ".local" / "share" / "muninn" / "muninn.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Create database schema if it doesn't exist."""
        cursor = self.conn.cursor()

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                timestamp_iso TEXT,
                event_type TEXT NOT NULL,
                data JSON NOT NULL,
                description TEXT NOT NULL,
                embedding_id TEXT,
                metadata JSON,
                created_at INTEGER NOT NULL,
                created_at_iso TEXT
            )
        """)

        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                first_seen INTEGER NOT NULL,
                first_seen_iso TEXT,
                last_seen INTEGER NOT NULL,
                last_seen_iso TEXT,
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                confidence REAL NOT NULL,
                data JSON,
                created_at INTEGER NOT NULL,
                created_at_iso TEXT
            )
        """)

        # Decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                timestamp_iso TEXT,
                action TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                context JSON NOT NULL,
                outcome TEXT,
                success BOOLEAN,
                embedding_id TEXT,
                created_at INTEGER NOT NULL,
                created_at_iso TEXT
            )
        """)

        # Interactions table (CRM)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                timestamp_iso TEXT,
                contact_email TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                summary TEXT NOT NULL,
                topics JSON,
                action_items JSON,
                sentiment TEXT,
                notes TEXT,
                embedding_id TEXT,
                metadata JSON,
                created_at INTEGER NOT NULL,
                created_at_iso TEXT
            )
        """)

        # Contact notes table (CRM)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                timestamp_iso TEXT,
                contact_email TEXT NOT NULL,
                note_text TEXT NOT NULL,
                tags JSON,
                metadata JSON,
                created_at INTEGER NOT NULL,
                created_at_iso TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_contact ON interactions(contact_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_notes_contact ON contact_notes(contact_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_notes_timestamp ON contact_notes(timestamp)")

        self.conn.commit()

        # Run migration for existing databases
        self._migrate_add_iso_timestamps()

    def _migrate_add_iso_timestamps(self):
        """Add ISO timestamp columns to existing databases if they don't exist."""
        cursor = self.conn.cursor()

        # Check if timestamp_iso column exists in events table
        cursor.execute("PRAGMA table_info(events)")
        events_columns = [row[1] for row in cursor.fetchall()]

        if 'timestamp_iso' not in events_columns:
            # Add columns
            cursor.execute("ALTER TABLE events ADD COLUMN timestamp_iso TEXT")
            cursor.execute("ALTER TABLE events ADD COLUMN created_at_iso TEXT")

            # Backfill existing data
            cursor.execute("SELECT id, timestamp, created_at FROM events")
            for row in cursor.fetchall():
                event_id, timestamp, created_at = row
                timestamp_iso = datetime.fromtimestamp(timestamp).isoformat() + 'Z'
                created_at_iso = datetime.fromtimestamp(created_at).isoformat() + 'Z'
                cursor.execute(
                    "UPDATE events SET timestamp_iso = ?, created_at_iso = ? WHERE id = ?",
                    (timestamp_iso, created_at_iso, event_id)
                )
            self.conn.commit()

        # Check patterns table
        cursor.execute("PRAGMA table_info(patterns)")
        patterns_columns = [row[1] for row in cursor.fetchall()]

        if 'first_seen_iso' not in patterns_columns:
            cursor.execute("ALTER TABLE patterns ADD COLUMN first_seen_iso TEXT")
            cursor.execute("ALTER TABLE patterns ADD COLUMN last_seen_iso TEXT")
            cursor.execute("ALTER TABLE patterns ADD COLUMN created_at_iso TEXT")

            # Backfill existing data
            cursor.execute("SELECT id, first_seen, last_seen, created_at FROM patterns")
            for row in cursor.fetchall():
                pattern_id, first_seen, last_seen, created_at = row
                first_seen_iso = datetime.fromtimestamp(first_seen).isoformat() + 'Z'
                last_seen_iso = datetime.fromtimestamp(last_seen).isoformat() + 'Z'
                created_at_iso = datetime.fromtimestamp(created_at).isoformat() + 'Z'
                cursor.execute(
                    "UPDATE patterns SET first_seen_iso = ?, last_seen_iso = ?, created_at_iso = ? WHERE id = ?",
                    (first_seen_iso, last_seen_iso, created_at_iso, pattern_id)
                )
            self.conn.commit()

        # Check decisions table
        cursor.execute("PRAGMA table_info(decisions)")
        decisions_columns = [row[1] for row in cursor.fetchall()]

        if 'timestamp_iso' not in decisions_columns:
            cursor.execute("ALTER TABLE decisions ADD COLUMN timestamp_iso TEXT")
            cursor.execute("ALTER TABLE decisions ADD COLUMN created_at_iso TEXT")

            # Backfill existing data
            cursor.execute("SELECT id, timestamp, created_at FROM decisions")
            for row in cursor.fetchall():
                decision_id, timestamp, created_at = row
                timestamp_iso = datetime.fromtimestamp(timestamp).isoformat() + 'Z'
                created_at_iso = datetime.fromtimestamp(created_at).isoformat() + 'Z'
                cursor.execute(
                    "UPDATE decisions SET timestamp_iso = ?, created_at_iso = ? WHERE id = ?",
                    (timestamp_iso, created_at_iso, decision_id)
                )
            self.conn.commit()

    def store_event(self, event: Event) -> int:
        """Store an event.

        Args:
            event: Event to store

        Returns:
            Event ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        created_at = int(now.timestamp())
        created_at_iso = now.isoformat() + 'Z'
        timestamp_iso = datetime.fromtimestamp(event.timestamp).isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO events (timestamp, timestamp_iso, event_type, data, description, embedding_id, metadata, created_at, created_at_iso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.timestamp,
            timestamp_iso,
            event.event_type,
            json.dumps(event.data),
            event.description,
            event.embedding_id,
            json.dumps(event.metadata),
            created_at,
            created_at_iso
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_recent_events(self, limit: int = 10, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events.

        Args:
            limit: Maximum number of events to return
            event_type: Optional filter by event type

        Returns:
            List of events as dictionaries
        """
        cursor = self.conn.cursor()

        if event_type:
            cursor.execute("""
                SELECT * FROM events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def query_events(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query events with filters.

        Args:
            event_type: Filter by event type
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum results

        Returns:
            List of matching events
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def store_pattern(self, pattern: Pattern) -> int:
        """Store a detected pattern.

        Args:
            pattern: Pattern to store

        Returns:
            Pattern ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        created_at = int(now.timestamp())
        created_at_iso = now.isoformat() + 'Z'
        first_seen_iso = datetime.fromtimestamp(pattern.first_seen).isoformat() + 'Z'
        last_seen_iso = datetime.fromtimestamp(pattern.last_seen).isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO patterns (
                pattern_type, description, first_seen, first_seen_iso, last_seen, last_seen_iso,
                occurrence_count, confidence, data, created_at, created_at_iso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.pattern_type,
            pattern.description,
            pattern.first_seen,
            first_seen_iso,
            pattern.last_seen,
            last_seen_iso,
            pattern.occurrence_count,
            pattern.confidence,
            json.dumps(pattern.data),
            created_at,
            created_at_iso
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get stored patterns.

        Args:
            pattern_type: Optional filter by pattern type

        Returns:
            List of patterns
        """
        cursor = self.conn.cursor()

        if pattern_type:
            cursor.execute("""
                SELECT * FROM patterns
                WHERE pattern_type = ?
                ORDER BY confidence DESC, occurrence_count DESC
            """, (pattern_type,))
        else:
            cursor.execute("""
                SELECT * FROM patterns
                ORDER BY confidence DESC, occurrence_count DESC
            """)

        return [dict(row) for row in cursor.fetchall()]

    def store_decision(self, decision: Decision) -> int:
        """Store an agent decision.

        Args:
            decision: Decision to store

        Returns:
            Decision ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        created_at = int(now.timestamp())
        created_at_iso = now.isoformat() + 'Z'
        timestamp_iso = datetime.fromtimestamp(decision.timestamp).isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO decisions (
                timestamp, timestamp_iso, action, reasoning, context,
                outcome, success, embedding_id, created_at, created_at_iso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.timestamp,
            timestamp_iso,
            decision.action,
            decision.reasoning,
            json.dumps(decision.context),
            decision.outcome,
            decision.success,
            decision.embedding_id,
            created_at,
            created_at_iso
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of decisions
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM decisions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics.

        Returns:
            Dictionary with various statistics
        """
        cursor = self.conn.cursor()

        stats = {}

        # Event counts
        cursor.execute("SELECT COUNT(*) as count FROM events")
        stats['total_events'] = cursor.fetchone()['count']

        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
        """)
        stats['events_by_type'] = {row['event_type']: row['count'] for row in cursor.fetchall()}

        # Pattern counts
        cursor.execute("SELECT COUNT(*) as count FROM patterns")
        stats['total_patterns'] = cursor.fetchone()['count']

        # Decision counts
        cursor.execute("SELECT COUNT(*) as count FROM decisions")
        stats['total_decisions'] = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM decisions
            WHERE success = 1
        """)
        stats['successful_decisions'] = cursor.fetchone()['count']

        # CRM counts
        cursor.execute("SELECT COUNT(*) as count FROM interactions")
        stats['total_interactions'] = cursor.fetchone()['count']

        cursor.execute("""
            SELECT interaction_type, COUNT(*) as count
            FROM interactions
            GROUP BY interaction_type
        """)
        stats['interactions_by_type'] = {row['interaction_type']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) as count FROM contact_notes")
        stats['total_contact_notes'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(DISTINCT contact_email) as count FROM interactions")
        stats['contacts_with_interactions'] = cursor.fetchone()['count']

        return stats

    def store_interaction(self, interaction: Interaction) -> int:
        """Store a contact interaction.

        Args:
            interaction: Interaction to store

        Returns:
            Interaction ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        created_at = int(now.timestamp())
        created_at_iso = now.isoformat() + 'Z'
        timestamp_iso = datetime.fromtimestamp(interaction.timestamp).isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO interactions (
                timestamp, timestamp_iso, contact_email, interaction_type, subject,
                summary, topics, action_items, sentiment, notes, embedding_id,
                metadata, created_at, created_at_iso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.timestamp,
            timestamp_iso,
            interaction.contact_email,
            interaction.interaction_type,
            interaction.subject,
            interaction.summary,
            json.dumps(interaction.topics),
            json.dumps(interaction.action_items),
            interaction.sentiment,
            interaction.notes,
            interaction.embedding_id,
            json.dumps(interaction.metadata),
            created_at,
            created_at_iso
        ))

        self.conn.commit()
        return cursor.lastrowid

    def query_interactions(
        self,
        contact_email: Optional[str] = None,
        interaction_type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query interactions with filters.

        Args:
            contact_email: Filter by contact email
            interaction_type: Filter by interaction type
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum results

        Returns:
            List of matching interactions
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM interactions WHERE 1=1"
        params = []

        if contact_email:
            query += " AND contact_email = ?"
            params.append(contact_email)

        if interaction_type:
            query += " AND interaction_type = ?"
            params.append(interaction_type)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_contact_timeline(self, contact_email: str, limit: int = 100) -> Dict[str, Any]:
        """Get complete timeline for a contact (interactions + notes).

        Args:
            contact_email: Contact email address
            limit: Maximum items to return

        Returns:
            Dictionary with interactions and notes
        """
        interactions = self.query_interactions(contact_email=contact_email, limit=limit)
        notes = self.get_contact_notes(contact_email=contact_email, limit=limit)

        return {
            "contact_email": contact_email,
            "interactions": interactions,
            "notes": notes,
            "total_interactions": len(interactions),
            "total_notes": len(notes)
        }

    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interactions across all contacts.

        Args:
            limit: Maximum number of interactions to return

        Returns:
            List of recent interactions
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def store_contact_note(self, note: ContactNote) -> int:
        """Store a contact note.

        Args:
            note: ContactNote to store

        Returns:
            Note ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        created_at = int(now.timestamp())
        created_at_iso = now.isoformat() + 'Z'
        timestamp_iso = datetime.fromtimestamp(note.timestamp).isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO contact_notes (
                timestamp, timestamp_iso, contact_email, note_text,
                tags, metadata, created_at, created_at_iso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note.timestamp,
            timestamp_iso,
            note.contact_email,
            note.note_text,
            json.dumps(note.tags),
            json.dumps(note.metadata),
            created_at,
            created_at_iso
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_contact_notes(
        self,
        contact_email: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get contact notes.

        Args:
            contact_email: Optional filter by contact email
            limit: Maximum results

        Returns:
            List of contact notes
        """
        cursor = self.conn.cursor()

        if contact_email:
            cursor.execute("""
                SELECT * FROM contact_notes
                WHERE contact_email = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (contact_email, limit))
        else:
            cursor.execute("""
                SELECT * FROM contact_notes
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        self.conn.close()
