"""Main MCP server implementation for Muninn memory storage."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
import mcp.server.stdio
import mcp.types as types

from muninn_mcp_server.storage.sqlite_store import SQLiteStore
from muninn_mcp_server.storage.vector_store import VectorStore
from muninn_mcp_server.embeddings.local_embedder import LocalEmbedder
from muninn_mcp_server.schemas.models import Event, Pattern, Decision, Interaction, ContactNote

# Configure logging with support for LOG_LEVEL environment variable
import os
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

# Configure logging to file if LOG_FILE is set, otherwise use stderr
log_file = os.getenv("LOG_FILE")
if log_file:
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode='a'
    )
else:
    logging.basicConfig(level=log_level)

logger = logging.getLogger("muninn_mcp_server")

# Initialize storage backends
embedder = LocalEmbedder()
sqlite_store = SQLiteStore()
vector_store = VectorStore(embedder=embedder)

server = Server("muninn-mcp-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available memory tools."""
    return [
        types.Tool(
            name="store_event",
            description="Store a desktop event with automatic embedding for semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Type of event (e.g., 'extension_change', 'app_launch', 'system_state')"
                    },
                    "data": {
                        "type": "object",
                        "description": "Event data as JSON object"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the event"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata"
                    }
                },
                "required": ["event_type", "data", "description"],
            },
        ),
        types.Tool(
            name="get_recent_events",
            description="Get recent events from memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of events to return (default: 10)"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Optional: filter by event type"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="query_events",
            description="Query events with time range and type filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Optional: filter by event type"
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Optional: start timestamp (Unix epoch)"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "Optional: end timestamp (Unix epoch)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results (default: 100)"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="semantic_search",
            description="Search events by semantic meaning (e.g., 'stability issues', 'crashes')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results (default: 10)"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["events", "decisions"],
                        "description": "What to search (default: events)"
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="store_pattern",
            description="Store a detected behavioral pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "description": "Type of pattern"
                    },
                    "description": {
                        "type": "string",
                        "description": "Pattern description"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0.0 - 1.0)"
                    },
                    "occurrence_count": {
                        "type": "number",
                        "description": "Number of occurrences (default: 1)"
                    },
                    "data": {
                        "type": "object",
                        "description": "Optional pattern data"
                    }
                },
                "required": ["pattern_type", "description", "confidence"],
            },
        ),
        types.Tool(
            name="get_patterns",
            description="Get detected patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "description": "Optional: filter by pattern type"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="store_decision",
            description="Store an agent decision with reasoning and outcome",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action taken"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this action was chosen"
                    },
                    "context": {
                        "type": "object",
                        "description": "Context at decision time"
                    },
                    "outcome": {
                        "type": "string",
                        "description": "Optional: outcome description"
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Optional: whether action succeeded"
                    }
                },
                "required": ["action", "reasoning", "context"],
            },
        ),
        types.Tool(
            name="get_recent_decisions",
            description="Get recent agent decisions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of decisions (default: 10)"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_statistics",
            description="Get aggregated memory statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        # CRM Tools
        types.Tool(
            name="log_interaction",
            description="Log a contact interaction (email, meeting, or manual note) with semantic search capability",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "string",
                        "description": "Contact's email address"
                    },
                    "interaction_type": {
                        "type": "string",
                        "enum": ["email", "meeting", "manual"],
                        "description": "Type of interaction"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject or title of interaction"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of the interaction"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Topics discussed (optional)"
                    },
                    "action_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Action items from interaction (optional)"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                        "description": "Sentiment of interaction (optional)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)"
                    }
                },
                "required": ["contact_email", "interaction_type", "subject", "summary"],
            },
        ),
        types.Tool(
            name="query_interactions",
            description="Query contact interactions with filters (by contact, type, or time range)",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "string",
                        "description": "Filter by contact email (optional)"
                    },
                    "interaction_type": {
                        "type": "string",
                        "description": "Filter by interaction type (optional)"
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Start timestamp (Unix epoch, optional)"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End timestamp (Unix epoch, optional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results (default: 100)"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="search_interactions",
            description="Semantic search over all interactions (e.g., 'discussions about Project X', 'conversations with positive sentiment')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results (default: 10)"
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_contact_timeline",
            description="Get complete timeline for a contact (all interactions and notes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "string",
                        "description": "Contact's email address"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum items (default: 100)"
                    }
                },
                "required": ["contact_email"],
            },
        ),
        types.Tool(
            name="get_recent_interactions",
            description="Get recent interactions across all contacts",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum interactions (default: 10)"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="add_contact_note",
            description="Add a general note about a contact (observations, preferences, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "string",
                        "description": "Contact's email address"
                    },
                    "note_text": {
                        "type": "string",
                        "description": "Note content"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)"
                    }
                },
                "required": ["contact_email", "note_text"],
            },
        ),
        types.Tool(
            name="get_contact_notes",
            description="Get notes for a contact or all contacts",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_email": {
                        "type": "string",
                        "description": "Filter by contact email (optional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results (default: 100)"
                    }
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls for memory operations."""

    if arguments is None:
        arguments = {}

    try:
        if name == "store_event":
            event = Event(
                event_type=arguments["event_type"],
                data=arguments["data"],
                description=arguments["description"],
                metadata=arguments.get("metadata")
            )

            # Store in SQLite
            event_id = sqlite_store.store_event(event)

            # Store embedding in vector DB
            embedding_id = vector_store.store_event_embedding(
                event_id=event_id,
                description=event.description,
                metadata={"event_type": event.event_type}
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "event_id": event_id,
                        "embedding_id": embedding_id,
                        "message": "Event stored successfully"
                    }, indent=2)
                )
            ]

        elif name == "get_recent_events":
            limit = arguments.get("limit", 10)
            event_type = arguments.get("event_type")

            events = sqlite_store.get_recent_events(limit=limit, event_type=event_type)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(events, indent=2)
                )
            ]

        elif name == "query_events":
            events = sqlite_store.query_events(
                event_type=arguments.get("event_type"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                limit=arguments.get("limit", 100)
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(events, indent=2)
                )
            ]

        elif name == "semantic_search":
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            search_type = arguments.get("search_type", "events")

            if search_type == "events":
                results = vector_store.semantic_search_events(query=query, limit=limit)
            else:
                results = vector_store.semantic_search_decisions(query=query, limit=limit)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "query": query,
                        "results": results,
                        "count": len(results)
                    }, indent=2)
                )
            ]

        elif name == "store_pattern":
            pattern = Pattern(
                pattern_type=arguments["pattern_type"],
                description=arguments["description"],
                confidence=arguments["confidence"],
                occurrence_count=arguments.get("occurrence_count", 1),
                data=arguments.get("data")
            )

            pattern_id = sqlite_store.store_pattern(pattern)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "pattern_id": pattern_id,
                        "message": "Pattern stored successfully"
                    }, indent=2)
                )
            ]

        elif name == "get_patterns":
            pattern_type = arguments.get("pattern_type")
            patterns = sqlite_store.get_patterns(pattern_type=pattern_type)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(patterns, indent=2)
                )
            ]

        elif name == "store_decision":
            decision = Decision(
                action=arguments["action"],
                reasoning=arguments["reasoning"],
                context=arguments["context"],
                outcome=arguments.get("outcome"),
                success=arguments.get("success")
            )

            # Store in SQLite
            decision_id = sqlite_store.store_decision(decision)

            # Store embedding in vector DB
            embedding_id = vector_store.store_decision_embedding(
                decision_id=decision_id,
                reasoning=decision.reasoning,
                metadata={"action": decision.action}
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "decision_id": decision_id,
                        "embedding_id": embedding_id,
                        "message": "Decision stored successfully"
                    }, indent=2)
                )
            ]

        elif name == "get_recent_decisions":
            limit = arguments.get("limit", 10)
            decisions = sqlite_store.get_recent_decisions(limit=limit)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(decisions, indent=2)
                )
            ]

        elif name == "get_statistics":
            sql_stats = sqlite_store.get_statistics()
            vector_stats = vector_store.get_collection_stats()

            stats = {
                **sql_stats,
                "vector_store": vector_stats
            }

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(stats, indent=2)
                )
            ]

        # CRM Tool Handlers
        elif name == "log_interaction":
            interaction = Interaction(
                contact_email=arguments["contact_email"],
                interaction_type=arguments["interaction_type"],
                subject=arguments["subject"],
                summary=arguments["summary"],
                topics=arguments.get("topics"),
                action_items=arguments.get("action_items"),
                sentiment=arguments.get("sentiment"),
                notes=arguments.get("notes"),
                metadata=arguments.get("metadata")
            )

            # Store in SQLite
            interaction_id = sqlite_store.store_interaction(interaction)

            # Store embedding in vector DB
            embedding_id = vector_store.store_interaction_embedding(
                interaction_id=interaction_id,
                summary=interaction.summary,
                subject=interaction.subject,
                metadata={
                    "contact_email": interaction.contact_email,
                    "interaction_type": interaction.interaction_type
                }
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "interaction_id": interaction_id,
                        "embedding_id": embedding_id,
                        "message": f"Interaction logged for {interaction.contact_email}"
                    }, indent=2)
                )
            ]

        elif name == "query_interactions":
            interactions = sqlite_store.query_interactions(
                contact_email=arguments.get("contact_email"),
                interaction_type=arguments.get("interaction_type"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                limit=arguments.get("limit", 100)
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "interactions": interactions,
                        "count": len(interactions)
                    }, indent=2)
                )
            ]

        elif name == "search_interactions":
            query = arguments["query"]
            limit = arguments.get("limit", 10)

            results = vector_store.semantic_search_interactions(query=query, limit=limit)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "query": query,
                        "results": results,
                        "count": len(results)
                    }, indent=2)
                )
            ]

        elif name == "get_contact_timeline":
            contact_email = arguments["contact_email"]
            limit = arguments.get("limit", 100)

            timeline = sqlite_store.get_contact_timeline(
                contact_email=contact_email,
                limit=limit
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(timeline, indent=2)
                )
            ]

        elif name == "get_recent_interactions":
            limit = arguments.get("limit", 10)
            interactions = sqlite_store.get_recent_interactions(limit=limit)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "interactions": interactions,
                        "count": len(interactions)
                    }, indent=2)
                )
            ]

        elif name == "add_contact_note":
            note = ContactNote(
                contact_email=arguments["contact_email"],
                note_text=arguments["note_text"],
                tags=arguments.get("tags"),
                metadata=arguments.get("metadata")
            )

            note_id = sqlite_store.store_contact_note(note)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "note_id": note_id,
                        "message": f"Note added for {note.contact_email}"
                    }, indent=2)
                )
            ]

        elif name == "get_contact_notes":
            notes = sqlite_store.get_contact_notes(
                contact_email=arguments.get("contact_email"),
                limit=arguments.get("limit", 100)
            )

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "notes": notes,
                        "count": len(notes)
                    }, indent=2)
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error in {name}: {str(e)}", exc_info=True)
        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "tool": name
                }, indent=2)
            )
        ]


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Muninn MCP Server...")
    logger.info(f"SQLite database: {sqlite_store.db_path}")
    logger.info(f"Vector storage: {vector_store.storage_path}")
    logger.info(f"Embedding model: {embedder.model_name}")

    options = InitializationOptions(
        server_name="muninn-mcp-server",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


def cli_main() -> None:
    """CLI entry point for the MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
