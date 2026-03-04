# Plan: Clickable Source Links in Chat

## Context

Sources returned from the RAG pipeline are currently plain strings (e.g. `"Course Name - Lesson 2"`). The user wants each source to become a clickable link that opens the lesson video in a new tab. Lesson URLs are already stored in `course_catalog` ChromaDB collection and can be fetched via the existing `VectorStore.get_lesson_link()` method.

## Data flow today

```
CourseSearchTool._format_results()
  → last_sources: List[str]          e.g. ["Course A - Lesson 1"]
  → ToolManager.get_last_sources()
  → rag_system.query() returns (answer, sources)
  → QueryResponse.sources: List[str]
  → frontend script.js: sources.join(', ') rendered as plain text
```

## Changes

### 1. `backend/app.py` — add `Source` model, update `QueryResponse`

```python
class Source(BaseModel):
    label: str
    url: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str
```

### 2. `backend/search_tools.py` — fetch lesson URL in `_format_results()`

`CourseSearchTool` already holds `self.store` (VectorStore). Use the existing `get_lesson_link(course_title, lesson_number)` method (line 249) to attach a URL to each source:

```python
# inside _format_results(), replace the sources.append(source) block:
url = self.store.get_lesson_link(course_title, lesson_num) if lesson_num is not None else self.store.get_course_link(course_title)
sources.append({"label": source, "url": url})
```

Change `last_sources` type annotation to `List[dict]`.

### 3. `backend/rag_system.py` — no logic changes needed

Sources are passed through as-is; the dict structure flows transparently.

### 4. `frontend/script.js` — render sources as `<a>` tags

In `addMessage()` (around line 125), replace the plain `sources.join(', ')` with:

```js
sources.map(s =>
    s.url
        ? `<a href="${s.url}" target="_blank" rel="noopener noreferrer">${s.label}</a>`
        : s.label
).join(', ')
```

The URL is never shown as raw text — only the label is visible.

## Files to modify

| File | Change |
|---|---|
| `backend/app.py` | Add `Source` model; update `QueryResponse.sources: List[Source]` |
| `backend/search_tools.py` | `_format_results()` — call `get_lesson_link()` / `get_course_link()`; store dicts in `last_sources` |
| `frontend/script.js` | Render sources as `<a>` tags using `label` + `url` |

## Verification

1. Start server: `./run.sh`
2. Ask a course-specific question (e.g. "What is covered in lesson 1?")
3. Sources section in the chat should show lesson names as clickable links
4. Clicking a link should open the lesson URL in a new tab with no raw URL visible
