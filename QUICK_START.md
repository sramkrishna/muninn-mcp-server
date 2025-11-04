# Muninn Quick Start Guide

Get Muninn (memory server) running in 5 minutes.

## What is Muninn?

Muninn is a memory server for agentic AI systems. It stores and recalls desktop events, decisions, and patterns using:
- **SQLite** for structured queries
- **ChromaDB** for semantic search
- **Local embeddings** (no cloud APIs)

Named after Odin's raven of memory, Muninn works with Hugin (thought) and Ratatoskr (messenger).

## Prerequisites

- Python 3.10+
- ~500MB disk space (for embedding model + data)
- 2GB+ RAM recommended

## Installation

```bash
cd /var/home/sri/Projects/muninn-mcp-server
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**First run will download the embedding model (~80MB)** - this happens automatically.

## Quick Test

Test Muninn standalone:

```bash
# In one terminal
muninn

# In another terminal, use MCP inspector or test client
# Or add to Hugin config (see below)
```

## Usage with Hugin

### 1. Edit Hugin's Config

```bash
cd /var/home/sri/Projects/hugin-mcp-client
nano config.toml
```

Add Muninn server:

```toml
[servers.muninn]
command = "python3.13"
args = ["/var/home/sri/Projects/muninn-mcp-server/src/muninn_mcp_server/server.py"]

[servers.ratatoskr]
command = "python3.13"
args = ["/var/home/sri/Projects/ratatoskr-mcp-server/src/ratatoskr_mcp_server/server.py"]
```

### 2. Start Hugin

```bash
cd /var/home/sri/Projects/hugin-mcp-client
./run-local.sh
```

### 3. Try These Queries

**Store an event:**
> "Store an event: I disabled the dash-to-panel extension because it was causing crashes"

**Query history:**
> "What events have been stored recently?"

**Semantic search:**
> "Find all past issues related to stability or crashes"

**Get statistics:**
> "Show me memory statistics"

## Available Tools

Muninn provides 9 tools:

### Storage
- `store_event` - Store desktop events
- `store_pattern` - Store detected patterns
- `store_decision` - Store agent decisions

### Retrieval (Structured)
- `get_recent_events` - Get last N events
- `query_events` - Filter by type/time
- `get_patterns` - Get detected patterns
- `get_recent_decisions` - Get agent decisions

### Retrieval (Semantic)
- `semantic_search` - Find similar events/decisions by meaning

### Analytics
- `get_statistics` - Aggregated stats

## Example: Agent Loop

Combine Ratatoskr (GNOME data) + Muninn (memory):

```
1. Check GNOME state (Ratatoskr)
   ├─> Get installed extensions
   └─> Get desktop version

2. Query relevant history (Muninn)
   ├─> Find past extension issues
   └─> Get previous decisions

3. LLM analyzes and decides
   └─> "Extension X caused crashes before"

4. Store decision (Muninn)
   └─> Record action + reasoning

5. Execute action (Ratatoskr)
   └─> Disable problematic extension
```

## Data Storage

All data stored locally:
```
~/.local/share/muninn/
├── muninn.db          # SQLite (events, patterns, decisions)
└── chroma/            # Vector embeddings
```

**Privacy:** Nothing leaves your machine. No cloud APIs, no telemetry.

## Testing

Run tests:

```bash
source .venv/bin/activate
pip install pytest pytest-asyncio
pytest tests/
```

## Troubleshooting

**Issue: "No module named 'sentence_transformers'"**
```bash
source .venv/bin/activate
pip install sentence-transformers
```

**Issue: "No module named 'chromadb'"**
```bash
source .venv/bin/activate
pip install chromadb
```

**Issue: Model download takes too long**
- First run downloads ~80MB model
- Be patient, it's a one-time download
- Subsequent runs are instant

**Issue: Memory too high**
- Embedding model uses ~200MB RAM
- This is normal and unavoidable for local embeddings
- Consider using swap if RAM constrained

## Architecture

```
┌─────────────────────────────────────────┐
│         Hugin (MCP Client)              │
│         + Local LLM (Ollama)            │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      │             │
┌─────▼──────┐ ┌───▼──────────┐
│ Ratatoskr  │ │   Muninn     │
│  (GNOME)   │ │  (Memory)    │
└────────────┘ └──────────────┘
      │              │
      │              ├─> SQLite
      │              └─> ChromaDB
      │
  D-Bus/GNOME
```

## Next Steps

See [EXAMPLES.md](EXAMPLES.md) for detailed usage examples.

## Philosophy

**Muninn remembers so the agent can learn.**

- Store what happened (events)
- Store what was decided (decisions)
- Store what patterns emerged (patterns)
- Search semantically (not just keywords)
- Build context over time
- Enable true desktop intelligence
