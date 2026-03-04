# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- Always use `uv` to run Python files and manage dependencies. Never use plain `python` or `pip`.

## Commands

**Setup**
```bash
cp .env.example .env   # add ANTHROPIC_API_KEY
uv sync                # install dependencies (pyproject.toml at repo root, Python >=3.13)
```


**Run the server** (must run from repo root, not from backend/)
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App is served at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Run a one-off Python script in the backend context**
```bash
cd backend && uv run python <script.py>
```

**Force re-ingestion of all documents**
```bash
rm -rf backend/chroma_db && ./run.sh
```

## Architecture

Full-stack RAG chatbot. The FastAPI backend (`backend/`) serves the vanilla JS frontend (`frontend/`) as static files — no separate frontend server.

All backend modules live flat in `backend/`. `config.py` instantiates a single `Config` dataclass at import time (`config = Config()`); every other module receives it via `RAGSystem.__init__()`.

### Request flow for a chat message

1. **Frontend** (`frontend/script.js`) — POSTs `{query, session_id}` to `/api/query`
2. **`app.py`** — creates a session if absent, delegates to `RAGSystem.query()`
3. **`rag_system.py`** — fetches formatted history from `SessionManager`, builds the prompt, calls `AIGenerator`
4. **`ai_generator.py`** — first Claude API call with `search_course_content` tool available (`tool_choice: auto`)
5. **If `stop_reason == "tool_use"`** (Claude chose to search):
   - `_handle_tool_execution()` iterates tool-use blocks, calls `ToolManager.execute_tool()`
   - `CourseSearchTool.execute()` optionally resolves the course name via `course_catalog` semantic search, then queries `course_content` with a metadata filter
   - A second Claude API call is made with tool results appended; no tools are passed this time
6. Sources are read from `CourseSearchTool.last_sources` and immediately reset
7. `SessionManager.add_exchange()` stores the turn; response and sources returned to frontend

### Document ingestion (on startup)

`app.py` startup event calls `RAGSystem.add_course_folder("../docs")`. `DocumentProcessor` parses each `.txt` file expecting:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <title>
Lesson Link: <url>
<content...>
```
Text is sentence-split then accumulated into ~800-char chunks with 100-char overlap. Chunks are embedded with `all-MiniLM-L6-v2` and stored in ChromaDB (`backend/chroma_db/`) under two collections:
- `course_catalog` — one document per course (title text); used for fuzzy course-name resolution
  - metadata: `title`, `instructor`, `course_link`, `lesson_count`, `lessons_json` (serialised list of `{lesson_number, lesson_title, lesson_link}`)
- `course_content` — one document per chunk (lesson text); used for semantic search
  - metadata: `course_title`, `lesson_number`, `chunk_index`

Deduplication: a course is skipped if its title already exists as an ID in `course_catalog`.

### Session state

`SessionManager` is purely in-memory (a dict keyed by session ID). Sessions do not survive server restarts. `MAX_HISTORY = 2` means the last 2 full turns (4 messages) are injected into the system prompt as plain text.

### Key configuration (`backend/config.py`)

| Setting | Default | Notes |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Downloaded on first run via sentence-transformers |
| `CHUNK_SIZE` | 800 chars | Max characters per vector chunk |
| `CHUNK_OVERLAP` | 100 chars | Overlap between consecutive chunks |
| `MAX_RESULTS` | 5 | Max chunks returned per search |
| `MAX_HISTORY` | 2 | Conversation turns kept in session |
| `CHROMA_PATH` | `./chroma_db` | Relative to `backend/` directory |

### Adding a new tool

Subclass `Tool` in `backend/search_tools.py`, implement `get_tool_definition()` (Anthropic tool schema) and `execute(**kwargs) -> str`, then register via `ToolManager.register_tool()` in `RAGSystem.__init__()`. If the tool tracks sources, add a `last_sources` list attribute — `ToolManager.get_last_sources()` and `reset_sources()` pick it up automatically.
