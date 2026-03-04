# Chatbot Tools

## Overview

The chatbot uses an extensible tool system defined in `backend/search_tools.py`. All tools implement the abstract `Tool` base class and are registered with the `ToolManager`, which exposes them to Claude via the Anthropic tool-calling API.

Currently there is **1 tool** registered.

---

## Registered Tools

### `search_course_content`

**Class:** `CourseSearchTool`
**File:** `backend/search_tools.py`

Searches the ChromaDB vector store for course material relevant to a user query. Supports optional filtering by course name and lesson number. Course name matching is fuzzy — partial or approximate names are resolved to the canonical title via a semantic similarity search on the `course_catalog` collection before the main content search is performed on `course_content`.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | The text to search for in course content |
| `course_name` | string | No | Course title filter; partial matches work (e.g. `"MCP"`, `"Introduction"`) |
| `lesson_number` | integer | No | Restrict search to a specific lesson number |

**Returns:** Formatted string of matching chunks, each prefixed with `[Course Title - Lesson N]`, or an error/empty message if nothing is found. Also populates `last_sources` with `"Course Title - Lesson N"` strings used by the frontend to display source attribution.

---

## ToolManager

**Class:** `ToolManager`
**File:** `backend/search_tools.py`

`ToolManager` sits at the pivot point between Claude's decision to call a tool and the actual execution of that tool. It plays four distinct roles:

| Role | Method | Description |
|---|---|---|
| **Registry** | `register_tool(tool)` | Stores each `Tool` instance in a dict keyed by its Anthropic tool name. Adding a new capability requires only one call here — no other layer needs to change. |
| **Schema provider** | `get_tool_definitions()` | Collects the Anthropic-format JSON schema from every registered tool and returns them as a list passed directly into the Claude API call. Claude reads these schemas to know what it can invoke and what arguments each tool expects. |
| **Dispatcher** | `execute_tool(name, **kwargs)` | Receives the tool name and arguments that Claude selected, looks up the correct `Tool` instance, and calls its `execute()`. Neither `AIGenerator` nor `RAGSystem` needs to know which tool was chosen. |
| **Source aggregator** | `get_last_sources()` / `reset_sources()` | After execution, scans all tools for a `last_sources` attribute and collects them for the frontend to display source attribution, then clears them for the next query. |

### Why ToolManager Fits the RAG Pattern

The RAG loop in this codebase follows this sequence:

```
User query
  → Claude (1st API call) decides whether to search
  → If yes: ToolManager.execute_tool() → VectorStore.search() → chunks returned
  → Claude (2nd API call) synthesizes chunks into an answer
  → Frontend displays answer + sources
```

Without `ToolManager`, `AIGenerator` would have to know about `CourseSearchTool` directly, coupling the LLM layer to the retrieval layer. Instead, the design separates three concerns cleanly:

| Layer | Responsibility | Knows about |
|---|---|---|
| `AIGenerator` | Claude API calls, message formatting | `ToolManager` interface only |
| `ToolManager` | Route tool calls, aggregate schemas/sources | `Tool` abstract class only |
| `CourseSearchTool` | Vector search logic | `VectorStore` only |

This means Claude decides **when** to search and **what** to search for — `ToolManager` only decides **how** to execute the chosen tool.

---

## Adding a New Tool

1. Subclass `Tool` in `backend/search_tools.py`.
2. Implement `get_tool_definition()` returning a valid Anthropic tool schema dict.
3. Implement `execute(**kwargs)` with the tool logic.
4. Register it in `RAGSystem.__init__()` via `self.tool_manager.register_tool(YourTool(...))`.
