"""Data models for Muninn memory server."""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


class EventType(str, Enum):
    """Types of events that can be stored."""
    EXTENSION_CHANGE = "extension_change"
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    SYSTEM_STATE = "system_state"
    WORKSPACE_CHANGE = "workspace_change"
    SETTINGS_CHANGE = "settings_change"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class Event:
    """Desktop event with metadata."""
    event_type: str
    data: Dict[str, Any]
    description: str
    timestamp: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(datetime.now().timestamp())
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Pattern:
    """Detected behavioral pattern."""
    pattern_type: str
    description: str
    confidence: float
    occurrence_count: int = 1
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        now = int(datetime.now().timestamp())
        if self.first_seen is None:
            self.first_seen = now
        if self.last_seen is None:
            self.last_seen = now
        if self.data is None:
            self.data = {}


@dataclass
class Decision:
    """Agent decision and outcome."""
    action: str
    reasoning: str
    context: Dict[str, Any]
    outcome: Optional[str] = None
    success: Optional[bool] = None
    timestamp: Optional[int] = None
    embedding_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(datetime.now().timestamp())


@dataclass
class Interaction:
    """Contact interaction record for CRM."""
    contact_email: str
    interaction_type: str  # email, meeting, manual
    subject: str
    summary: str
    topics: Optional[list[str]] = None
    action_items: Optional[list[str]] = None
    sentiment: Optional[str] = None  # positive, neutral, negative
    notes: Optional[str] = None
    timestamp: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(datetime.now().timestamp())
        if self.topics is None:
            self.topics = []
        if self.action_items is None:
            self.action_items = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ContactNote:
    """General note about a contact."""
    contact_email: str
    note_text: str
    tags: Optional[list[str]] = None
    timestamp: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(datetime.now().timestamp())
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
