# RAG Chatbot Architecture

## Component Overview

| File | Class | Role |
|---|---|---|
| `app.py` | FastAPI app | HTTP entry point; serves frontend static files |
| `rag_system.py` | `RAGSystem` | Main orchestrator tying all components together |
| `ai_generator.py` | `AIGenerator` | Wraps Anthropic API calls; handles tool-use agentic loop |
| `search_tools.py` | `ToolManager`, `CourseSearchTool` | Claude tool definitions and execution |
| `vector_store.py` | `VectorStore` | ChromaDB persistence — two collections: catalog + content |
| `document_processor.py` | `DocumentProcessor` | Parses `.txt` course files; chunks text |
| `session_manager.py` | `SessionManager` | In-memory conversation history keyed by session ID |
| `models.py` | `Course`, `Lesson`, `CourseChunk` | Shared data models |
| `config.py` | `config` | Central settings (model, paths, chunk sizes, etc.) |

---

## Phase 1 — Document Ingestion (on startup)

Triggered once by the FastAPI `startup` event. Scans `../docs/` and loads any new `.txt` course files into ChromaDB.

```mermaid
sequenceDiagram
    participant App as app.py (startup)
    participant RAG as RAGSystem
    participant DP as DocumentProcessor
    participant VS as VectorStore (ChromaDB)

    App->>RAG: add_course_folder("../docs")
    RAG->>VS: get_existing_course_titles()
    VS-->>RAG: [list of already-ingested titles]

    loop For each .txt file in /docs
        RAG->>DP: process_course_document(file_path)
        DP->>DP: read_file() → raw text
        DP->>DP: parse header (title, link, instructor)
        DP->>DP: parse lessons (number, title, link, body)
        DP->>DP: chunk_text() → sentence-split chunks (~800 chars, 100 overlap)
        DP-->>RAG: Course object + List[CourseChunk]

        alt Course title not yet in ChromaDB
            RAG->>VS: add_course_metadata(course)
            Note over VS: Stored in "course_catalog" collection
            RAG->>VS: add_course_content(chunks)
            Note over VS: Stored in "course_content" collection<br/>Embedded with all-MiniLM-L6-v2
        else Already exists
            RAG-->>App: skip (log "already exists")
        end
    end

    RAG-->>App: (total_courses, total_chunks)
```

### ChromaDB Collections

| Collection | Contents | ID scheme |
|---|---|---|
| `course_catalog` | One doc per course (title text) + metadata (instructor, link, lessons JSON) | `course.title` |
| `course_content` | One doc per chunk (lesson text) + metadata (course\_title, lesson\_number, chunk\_index) | `{course_title}_{chunk_index}` |

---

## Phase 2 — Chat Query (per request)

Every `POST /api/query` triggers a two-stage Claude call when the AI decides to search.

```mermaid
sequenceDiagram
    participant FE as Frontend (JS)
    participant App as app.py
    participant RAG as RAGSystem
    participant SM as SessionManager
    participant AI as AIGenerator
    participant TM as ToolManager
    participant ST as CourseSearchTool
    participant VS as VectorStore (ChromaDB)
    participant Claude as Anthropic API

    FE->>App: POST /api/query {query, session_id}
    App->>SM: create_session() [if no session_id]
    App->>RAG: query(query, session_id)

    RAG->>SM: get_conversation_history(session_id)
    SM-->>RAG: formatted history string (last N turns)

    RAG->>AI: generate_response(prompt, history, tools, tool_manager)

    %% ── First Claude call ──
    AI->>Claude: messages.create(system+history, user_query, tools=[search_course_content])
    Claude-->>AI: response

    alt stop_reason == "tool_use"  (Claude wants to search)
        AI->>AI: _handle_tool_execution()

        loop For each tool_use block in response
            AI->>TM: execute_tool("search_course_content", query, course_name?, lesson_number?)
            TM->>ST: execute(query, course_name, lesson_number)

            opt course_name provided
                ST->>VS: _resolve_course_name() → course_catalog.query()
                VS-->>ST: best-matching course title
            end

            ST->>VS: search(query, course_title, lesson_number)
            VS->>VS: _build_filter(course_title, lesson_number)
            VS->>VS: course_content.query(query_texts=[query], where=filter)
            Note over VS: Semantic similarity via sentence-transformers
            VS-->>ST: SearchResults (docs + metadata)
            ST->>ST: _format_results() → stores last_sources
            ST-->>TM: formatted string of matching chunks
            TM-->>AI: tool_result
        end

        %% ── Second Claude call ──
        AI->>Claude: messages.create(original_msg + tool_results)
        Claude-->>AI: final answer text
    else stop_reason == "end_turn"  (no search needed)
        AI-->>RAG: direct answer text
    end

    RAG->>TM: get_last_sources()
    TM-->>RAG: [source strings]
    RAG->>TM: reset_sources()

    RAG->>SM: add_exchange(session_id, query, response)
    RAG-->>App: (answer, sources)
    App-->>FE: {answer, sources, session_id}
```

---

## Adding a New Tool

1. Subclass `Tool` in `backend/search_tools.py`
2. Implement `get_tool_definition()` (Anthropic JSON schema) and `execute(**kwargs) -> str`
3. Register in `RAGSystem.__init__()`:
   ```python
   my_tool = MyTool(...)
   self.tool_manager.register_tool(my_tool)
   ```
Claude automatically receives the new tool definition on every query and can choose to call it.

---

## Key Configuration (`backend/config.py`)

| Setting | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Generation model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model (downloaded on first run) |
| `CHUNK_SIZE` | 800 chars | Max chars per vector chunk |
| `CHUNK_OVERLAP` | 100 chars | Sentence overlap between chunks |
| `MAX_RESULTS` | 5 | Max chunks returned per ChromaDB search |
| `MAX_HISTORY` | 2 | Conversation turns kept per session |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence directory (relative to `backend/`) |
