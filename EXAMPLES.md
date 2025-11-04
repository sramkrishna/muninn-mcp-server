# Muninn Usage Examples

This document shows practical examples of using Muninn for desktop agent memory.

## Setup

```bash
cd /var/home/sri/Projects/muninn-mcp-server
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Standalone Testing

You can test Muninn tools directly via the MCP inspector or through a client like Hugin.

## Example 1: Storing Desktop Events

### Store an Extension Change Event

```python
# Via MCP tool call
{
  "event_type": "extension_change",
  "data": {
    "extension": "dash-to-panel@jderose9.github.com",
    "action": "disabled",
    "reason": "causing GNOME Shell crashes"
  },
  "description": "Disabled dash-to-panel extension due to repeated GNOME Shell crashes after system update"
}
```

**Response:**
```json
{
  "success": true,
  "event_id": 1,
  "embedding_id": "a1b2c3d4-...",
  "message": "Event stored successfully"
}
```

### Store an App Launch Event

```python
{
  "event_type": "app_launch",
  "data": {
    "app": "org.gnome.Terminal",
    "workspace": 1,
    "time_of_day": "morning"
  },
  "description": "Launched GNOME Terminal on workspace 1 at 9:15 AM"
}
```

## Example 2: Querying Events

### Get Recent Events

```python
# Tool: get_recent_events
{
  "limit": 5
}
```

**Response:** Array of 5 most recent events

### Query Events by Type

```python
# Tool: query_events
{
  "event_type": "extension_change",
  "limit": 10
}
```

### Query Events by Time Range

```python
# Tool: query_events
{
  "start_time": 1728691200,  # Unix timestamp for Oct 12, 2024
  "end_time": 1728777600,
  "limit": 50
}
```

## Example 3: Semantic Search

### Find Stability Issues

```python
# Tool: semantic_search
{
  "query": "crashes and stability problems",
  "limit": 10
}
```

**Response:**
```json
{
  "query": "crashes and stability problems",
  "results": [
    {
      "embedding_id": "a1b2c3d4-...",
      "description": "Disabled dash-to-panel extension due to repeated GNOME Shell crashes",
      "metadata": {
        "event_id": 1,
        "event_type": "extension_change"
      },
      "distance": 0.23
    },
    {
      "embedding_id": "e5f6g7h8-...",
      "description": "GNOME Shell restarted after extension error",
      "metadata": {
        "event_id": 5,
        "event_type": "system_state"
      },
      "distance": 0.31
    }
  ],
  "count": 2
}
```

### Find Similar Workflows

```python
# Tool: semantic_search
{
  "query": "morning routine with terminal and browser",
  "limit": 5,
  "search_type": "events"
}
```

## Example 4: Storing Agent Decisions

### Store Extension Management Decision

```python
# Tool: store_decision
{
  "action": "disable_extension",
  "reasoning": "Extension 'dash-to-panel' has caused 5 GNOME Shell crashes in the past hour. Disabling to restore stability.",
  "context": {
    "extension": "dash-to-panel@jderose9.github.com",
    "crash_count": 5,
    "time_window": "1 hour",
    "gnome_version": "48.4"
  },
  "outcome": "Extension disabled successfully. No crashes in following 2 hours.",
  "success": true
}
```

**Response:**
```json
{
  "success": true,
  "decision_id": 1,
  "embedding_id": "i9j0k1l2-...",
  "message": "Decision stored successfully"
}
```

### Retrieve Recent Decisions

```python
# Tool: get_recent_decisions
{
  "limit": 10
}
```

## Example 5: Pattern Detection

### Store a Detected Pattern

```python
# Tool: store_pattern
{
  "pattern_type": "morning_workflow",
  "description": "User consistently opens Terminal, Firefox, and VS Code between 9-9:30 AM on weekdays",
  "confidence": 0.87,
  "occurrence_count": 23,
  "data": {
    "apps": ["org.gnome.Terminal", "firefox", "code"],
    "time_range": "09:00-09:30",
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
  }
}
```

### Get All Patterns

```python
# Tool: get_patterns
{}
```

## Example 6: Statistics

```python
# Tool: get_statistics
{}
```

**Response:**
```json
{
  "total_events": 156,
  "events_by_type": {
    "extension_change": 12,
    "app_launch": 89,
    "app_close": 43,
    "system_state": 12
  },
  "total_patterns": 5,
  "total_decisions": 8,
  "successful_decisions": 7,
  "vector_store": {
    "events_count": 156,
    "decisions_count": 8,
    "embedding_dimension": 384,
    "model": "all-MiniLM-L6-v2"
  }
}
```

## Example 7: Agent Loop with Muninn + Ratatoskr

Here's how an agent might use both Muninn and Ratatoskr together:

```python
# Pseudo-code for desktop monitoring agent

# 1. Get current state from Ratatoskr
current_extensions = ratatoskr.get_gnome_extensions()

# 2. Get relevant history from Muninn
past_issues = muninn.semantic_search({
    "query": "extension problems and crashes",
    "limit": 10
})

# 3. Ask LLM to analyze
prompt = f"""
Current extensions: {current_extensions}
Past issues: {past_issues}

Are any current extensions known to cause problems?
Should I take any preventive action?
"""

decision = llm.analyze(prompt)

# 4. If action needed, store the decision
if decision.should_act:
    muninn.store_decision({
        "action": decision.action,
        "reasoning": decision.reasoning,
        "context": {
            "current_extensions": current_extensions,
            "past_issues": past_issues
        }
    })

# 5. Store the current state as an event
muninn.store_event({
    "event_type": "system_state",
    "data": current_extensions,
    "description": f"System check: {len(current_extensions['enabled_extensions'])} extensions enabled"
})
```

## Example 8: Using with Hugin

Add to Hugin's `config.toml`:

```toml
[servers.muninn]
command = "python3.13"
args = ["/var/home/sri/Projects/muninn-mcp-server/src/muninn_mcp_server/server.py"]

[servers.ratatoskr]
command = "python3.13"
args = ["/var/home/sri/Projects/ratatoskr-mcp-server/src/ratatoskr_mcp_server/server.py"]
```

Then ask Hugin:

- "Store an event about disabling the problematic extension"
- "What patterns have you noticed in my desktop usage?"
- "Find all past issues related to extensions"
- "What decisions have you made about extensions in the past week?"

## Data Locations

All data stored locally:
```
~/.local/share/muninn/
├── muninn.db          # SQLite database
└── chroma/            # Vector embeddings
    ├── chroma.sqlite3
    └── [embedding data]
```

## Privacy Notes

- All embeddings generated locally (no API calls)
- All data stays on your machine
- No telemetry or external connections
- You can delete `~/.local/share/muninn/` to reset all memory
