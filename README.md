# Muninn - Memory MCP Server

**Muninn** (Old Norse: Memory) is an MCP (Model Context Protocol) server that provides persistent memory and semantic search capabilities for agentic AI systems.

Named after Odin's raven of memory (paired with Hugin, the raven of thought), Muninn stores and recalls contextual information to enable intelligent desktop automation and workflow learning.

## Features

- **Hybrid Storage**: SQLite for structured queries + ChromaDB for semantic search
- **Local-First**: All data and embeddings stay on your machine
- **Privacy-Focused**: Uses local embedding models (no cloud API calls)
- **MCP-Compatible**: Works with any MCP client (Hugin, Claude Desktop, etc.)

## Architecture

```
┌─────────────────────────────────────────┐
│            Muninn Memory Server          │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────┐    ┌───────────────┐ │
│  │   SQLite     │    │   ChromaDB    │ │
│  │  (Structured)│    │   (Semantic)  │ │
│  └──────────────┘    └───────────────┘ │
│         ↑                    ↑          │
│         └────────┬───────────┘          │
│                  │                      │
│         ┌────────▼────────┐            │
│         │  Local Embedder │            │
│         │ sentence-trans. │            │
│         └─────────────────┘            │
│                                          │
│  Storage: ~/.local/share/muninn/        │
└─────────────────────────────────────────┘
```

## Installation

```bash
cd muninn-mcp-server
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Standalone
```bash
muninn
```

### With Hugin (MCP Client)

Add to `config.toml`:
```toml
[servers.muninn]
command = "python3.13"
args = ["/path/to/muninn-mcp-server/src/muninn_mcp_server/server.py"]
```

## Available Tools

### Storage
- `store_event` - Store desktop events with automatic embedding
- `store_pattern` - Store detected behavioral patterns
- `store_decision` - Log agent decisions and outcomes

### Retrieval (Structured)
- `query_events` - SQL-based queries on structured data
- `get_recent_events` - Get last N events
- `get_events_by_type` - Filter by event type

### Retrieval (Semantic)
- `semantic_search` - Find similar events by meaning
- `get_context` - Get relevant context for current situation

### Analytics
- `detect_patterns` - Find recurring patterns in stored data
- `get_statistics` - Aggregated statistics

## Data Storage

All data stored locally at:
```
~/.local/share/muninn/
├── muninn.db           # SQLite database
└── chroma/             # Vector embeddings
```

## Example: Store Desktop Event

```python
# Via MCP client (e.g., Hugin + LLM)
await call_tool("store_event", {
    "event_type": "extension_change",
    "data": {
        "extension": "dash-to-panel",
        "action": "disabled",
        "reason": "causing crashes"
    },
    "description": "Disabled dash-to-panel extension due to repeated GNOME Shell crashes"
})
```

## Example: Semantic Search

```python
# Find similar past issues
await call_tool("semantic_search", {
    "query": "extension stability problems",
    "limit": 5
})
```

## Privacy

- **No cloud APIs**: All embeddings generated locally
- **No telemetry**: All data stays on your machine
- **No external dependencies**: SQLite and ChromaDB run locally

## Embedding Model

Uses `all-MiniLM-L6-v2` (80MB) by default:
- Fast on CPU
- Good quality embeddings
- Runs entirely offline

## License

MIT
