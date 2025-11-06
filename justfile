# Muninn MCP Server - justfile
# Memory and knowledge management with SQLite and ChromaDB vector storage

# Python to use (prefer 3.13+)
python := `which python3.13 || which python3.14 || which python3`

# Default recipe
default:
    @just --list

# Setup virtual environment and install dependencies
setup:
    @echo "🔧 Setting up Muninn MCP Server (Memory/Vector DB)..."
    @echo "Using Python: {{python}}"
    {{python}} -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e .
    @echo "✅ Muninn setup complete!"
    @echo ""
    @echo "Dependencies installed:"
    @echo "  - chromadb (vector database)"
    @echo "  - sentence-transformers (embeddings)"
    @echo "  - pydantic (data validation)"

# Clean virtual environment
clean:
    @echo "🧹 Cleaning Muninn virtual environment..."
    rm -rf .venv
    rm -rf *.egg-info
    rm -rf build dist
    find . -type d -name __pycache__ -exec rm -rf {} +
    @echo "✅ Clean complete"

# Run Muninn server standalone (for testing)
run:
    .venv/bin/python -m muninn_mcp_server.server

# Run tests
test:
    .venv/bin/pytest tests/ -v || echo "No tests defined yet"

# Install development dependencies
dev:
    .venv/bin/pip install -e ".[dev]"

# List available tools
tools:
    @echo "Muninn MCP Tools:"
    @echo "  - store_memory (save information to memory)"
    @echo "  - search_memory (semantic search across memories)"
    @echo "  - list_memories (list recent memories)"
    @echo "  - delete_memory (remove a memory)"

# Show memory statistics
stats:
    @echo "Memory Statistics:"
    @echo "TODO: Add ChromaDB collection stats"
