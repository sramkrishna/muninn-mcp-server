# Muninn Architecture

## Overview

Muninn is a local-first memory MCP server that provides persistent storage and semantic search for agentic AI systems.

## Design Philosophy

1. **Privacy First**: All data stays local, no cloud APIs
2. **Hybrid Storage**: Structured (SQLite) + Semantic (ChromaDB)
3. **Local Embeddings**: No external dependencies for embeddings
4. **MCP Standard**: Works with any MCP client

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Muninn MCP Server                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             MCP Protocol Layer (server.py)                │  │
│  │  - handle_list_tools()                                    │  │
│  │  - handle_call_tool()                                     │  │
│  │  - 9 tools exposed via MCP                                │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                          │
│         ┌─────────────┴──────────────┐                          │
│         │                            │                          │
│  ┌──────▼───────┐            ┌──────▼───────┐                  │
│  │  SQLiteStore │            │ VectorStore  │                  │
│  │              │            │              │                  │
│  │ - events     │            │ - event_emb  │                  │
│  │ - patterns   │            │ - decision_  │                  │
│  │ - decisions  │            │   emb        │                  │
│  │              │            │              │                  │
│  │ Structured   │            │ Semantic     │                  │
│  │ SQL queries  │            │ similarity   │                  │
│  └──────────────┘            └──────┬───────┘                  │
│                                     │                           │
│                              ┌──────▼────────┐                  │
│                              │ LocalEmbedder │                  │
│                              │ (sentence-    │                  │
│                              │  transformers)│                  │
│                              └───────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
            ┌───────▼────────┐  ┌────────▼─────────┐
            │  muninn.db     │  │  chroma/         │
            │  (SQLite)      │  │  (ChromaDB)      │
            └────────────────┘  └──────────────────┘

    ~/.local/share/muninn/
```

## Component Details

### 1. MCP Protocol Layer (`server.py`)

**Responsibilities:**
- Expose MCP-compliant interface
- Handle tool registration and execution
- Coordinate between storage backends
- Error handling and logging

**Tools Provided:**
- `store_event` - Store events with auto-embedding
- `get_recent_events` - Retrieve recent events
- `query_events` - Filtered queries
- `semantic_search` - Similarity search
- `store_pattern` - Store detected patterns
- `get_patterns` - Retrieve patterns
- `store_decision` - Store agent decisions
- `get_recent_decisions` - Retrieve decisions
- `get_statistics` - Aggregated stats

### 2. SQLite Storage (`storage/sqlite_store.py`)

**Purpose:** Structured storage for queryable data

**Tables:**
```sql
events (
    id, timestamp, event_type, data,
    description, embedding_id, metadata
)

patterns (
    id, pattern_type, description,
    first_seen, last_seen, occurrence_count,
    confidence, data
)

decisions (
    id, timestamp, action, reasoning,
    context, outcome, success, embedding_id
)
```

**Operations:**
- Store events/patterns/decisions
- Query by type, time range, filters
- Aggregate statistics
- Link to vector embeddings via embedding_id

### 3. Vector Storage (`storage/vector_store.py`)

**Purpose:** Semantic search over textual data

**Technology:** ChromaDB (local, persistent)

**Collections:**
- `events` - Event descriptions
- `decisions` - Decision reasoning

**Operations:**
- Store embeddings with metadata
- Semantic similarity search
- Retrieve by embedding ID
- Delete embeddings

**Linking:** Uses `embedding_id` UUID to link back to SQLite records

### 4. Local Embedder (`embeddings/local_embedder.py`)

**Purpose:** Generate embeddings without cloud APIs

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- Size: ~80MB
- Dimension: 384
- Quality: Good for semantic search
- Speed: Fast on CPU

**Operations:**
- Embed single text or batches
- Lazy loading (only loads on first use)
- Returns numpy arrays as lists

### 5. Data Models (`schemas/models.py`)

**Purpose:** Type-safe data structures

**Classes:**
- `Event` - Desktop events with metadata
- `Pattern` - Detected behavioral patterns
- `Decision` - Agent decisions with reasoning
- `EventType` - Enum of event types

## Data Flow

### Storing an Event

```
1. Client calls store_event tool
       │
       ▼
2. server.py receives MCP request
       │
       ▼
3. Create Event object from arguments
       │
       ├─> 4a. SQLiteStore.store_event()
       │        └─> Insert into events table
       │        └─> Return event_id
       │
       └─> 4b. LocalEmbedder.embed(description)
                └─> Generate embedding vector
                └─> VectorStore.store_event_embedding()
                     └─> Store in ChromaDB
                     └─> Return embedding_id
       │
       ▼
5. Return success response with IDs
```

### Semantic Search

```
1. Client calls semantic_search tool
       │
       ▼
2. server.py receives query text
       │
       ▼
3. LocalEmbedder.embed(query)
       │
       ▼
4. VectorStore.semantic_search_events()
       │
       └─> ChromaDB query with embedding
       └─> Find similar vectors
       └─> Return matches with distances
       │
       ▼
5. Return formatted results
```

### Combined Query (Structured + Semantic)

```
1. Agent wants context for current situation
       │
       ├─> Semantic search: "stability issues"
       │   └─> Returns: embedding_ids + metadata
       │
       └─> SQL query: events by embedding_ids
           └─> Returns: full event records
       │
       ▼
2. Combined results with both semantic relevance
   and structured data
```

## Storage Locations

```
~/.local/share/muninn/
├── muninn.db              # SQLite database
│   ├── events table
│   ├── patterns table
│   └── decisions table
│
└── chroma/                # ChromaDB storage
    ├── chroma.sqlite3     # ChromaDB metadata
    └── [HNSW indices]     # Vector indices
```

## Memory Usage

- **Embedding Model**: ~200MB RAM (loaded once)
- **SQLite**: Minimal (pages loaded on demand)
- **ChromaDB**: ~50-100MB for indices
- **Total**: ~300-400MB typical

## Performance Characteristics

### SQLite
- **Insert**: <1ms per event
- **Query**: <10ms for filtered queries
- **Stats**: <50ms for aggregations

### Vector Search
- **Embed**: ~10-50ms per text
- **Search**: ~10-100ms depending on collection size
- **Scaling**: Good up to 100k+ embeddings

### First Run
- Downloads embedding model (~80MB)
- One-time delay of ~30-60 seconds
- Subsequent runs: instant

## Scaling Considerations

**Current design handles:**
- 100k+ events
- 10k+ patterns
- 10k+ decisions
- Real-time semantic search

**If scaling beyond:**
- Consider vector index tuning
- Add database archiving
- Implement cleanup policies

## Privacy & Security

**Local-First Design:**
- No network calls for embeddings
- No telemetry or analytics
- All data in user's home directory
- ChromaDB configured with `anonymized_telemetry=False`

**Data Control:**
- User owns all data
- Easy to backup: `~/.local/share/muninn/`
- Easy to delete: `rm -rf ~/.local/share/muninn/`
- No vendor lock-in

## Integration with Ratatoskr + Hugin

```
Agent System Architecture:

Hugin (MCP Client + LLM)
    ├─> Ratatoskr (GNOME state)
    │   └─> Current desktop status
    │
    └─> Muninn (Memory)
        ├─> Past events
        ├─> Historical patterns
        └─> Previous decisions

Example Flow:
1. Hugin asks: "Should I disable any extensions?"
2. Calls Ratatoskr: get_gnome_extensions()
3. Calls Muninn: semantic_search("extension problems")
4. LLM reasons with both current + historical data
5. Makes decision, stores in Muninn
6. Executes via Ratatoskr (future write capability)
```

## Extension Points

**Adding New Event Types:**
1. Add to `EventType` enum in `models.py`
2. No code changes needed elsewhere

**Adding New Tools:**
1. Add tool definition in `handle_list_tools()`
2. Add handler in `handle_call_tool()`
3. Use existing storage backends

**Adding New Storage Backend:**
1. Create new class in `storage/`
2. Initialize in `server.py`
3. Add methods as needed
4. Integrate in tool handlers

## Testing Strategy

**Unit Tests:**
- `test_sqlite_store.py` - Database operations
- `test_vector_store.py` - Semantic search

**Integration Tests:**
- `test_muninn.py` - End-to-end functionality

**Manual Testing:**
- Run standalone with `muninn`
- Test via Hugin client
- Verify data persistence

## Future Enhancements

**Potential additions:**
- Time-series analysis
- Pattern detection algorithms
- Event correlation
- Automatic cleanup policies
- Export/import functionality
- Multi-user support
- Remote backup sync
