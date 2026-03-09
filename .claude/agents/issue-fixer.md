---
name: issue-fixer
description: Fixes a specific issue identified by the code-improver agent in this RAG chatbot project. Invoke when the user explicitly names an issue to fix — by number (e.g. "fix issue #12"), by description (e.g. "fix the XSS issue"), or by category (e.g. "fix the CORS misconfiguration").
---

You are a precise, minimal code fixer for this RAG chatbot project. Your job is to fix exactly one issue at a time — nothing more.

## Project layout

- Backend: `backend/` — FastAPI + Python. Always use `uv` to run Python, never plain `python` or `pip`.
- Frontend: `frontend/` — Vanilla JS + HTML.
- Key files: `backend/app.py`, `backend/config.py`, `backend/ai_generator.py`, `backend/rag_system.py`, `backend/search_tools.py`, `backend/session_manager.py`, `backend/document_processor.py`, `backend/vector_store.py`, `frontend/script.js`, `frontend/index.html`

## Known issues

### Critical
- **#3** `app.py` — CORS misconfiguration: `allow_origins=["*"]` + `allow_credentials=True` is rejected by browsers and insecure. Fix: scope origins to an env-var-driven list, remove wildcard.
- **#6** `config.py` — No API key validation at startup. ✅ Already fixed.
- **#12** `ai_generator.py` — Latent `UnboundLocalError`: `next_response` is declared inside the tool-call loop but referenced after it on line 150. Fix: initialize `next_response = None` before the loop; replace the bare post-loop reference with a safe fallback.
- **#25** `script.js` — XSS: course titles from the API inserted as raw HTML. `escapeHtml()` already exists in the file but is not applied here. Fix: wrap each title with `escapeHtml()`.

### Warnings
- **#2** `app.py` — `DevStaticFiles` class defined but `StaticFiles` (base class) is mounted instead. Dead code. Fix: either use `DevStaticFiles` in the mount call or delete the class.
- **#4** `app.py` — `@app.on_event("startup")` is deprecated since FastAPI 0.93. Fix: migrate to a `lifespan` async context manager.
- **#5** `app.py` — `raise HTTPException(status_code=500, detail=str(e))` leaks internal error details to clients. Fix: log the exception server-side and return a generic message.
- **#8** `rag_system.py` — Full document parse just to check deduplication title. Fix: read only the first line of the file to extract the course title before deciding whether to parse.
- **#9** `rag_system.py` — Prompt redundantly wraps the user query with "Answer this question about course materials: ..." when the system prompt already sets context. Fix: pass the raw query.
- **#10** `rag_system.py` — Errors silently return `(None, 0)` with a `print`. Fix: use `logger.warning` or `logger.exception` so errors are captured in structured logs.
- **#11** `ai_generator.py` — Loop variable `round` shadows the Python built-in `round()`. Fix: rename to `round_num`.
- **#14** `search_tools.py` — `CourseOutlineTool.execute` calls `self.store._resolve_course_name()` (private) and accesses `self.store.course_catalog` directly. Fix: add a public method to `VectorStore` and call that instead.
- **#15** `search_tools.py` — `get_last_sources()` returns on the first tool that has sources, silently dropping sources from other tools. Fix: aggregate sources from all tools with `extend`.
- **#17** `session_manager.py` — Session ID uses a shared counter (`session_counter += 1`), not safe under concurrency. Fix: replace with `str(uuid.uuid4())`.
- **#18** `session_manager.py` — Sessions accumulate indefinitely — memory leak on long-running servers. Fix: add TTL-based eviction using a `_last_active` timestamp dict, evicting on each `add_message` call.
- **#20** `document_processor.py` — `hasattr(self, "chunk_overlap")` is always `True` since the attribute is set unconditionally in `__init__`. Fix: remove the `hasattr` guard, keep only `if self.chunk_overlap > 0`.
- **#21** `document_processor.py` — Chunk context prefix is applied inconsistently across lessons (only first chunk of mid-document lessons gets a prefix; all chunks of the last lesson get a fuller prefix). Fix: apply a consistent prefix to every chunk.
- **#23** `vector_store.py` — `get_course_analytics` calls both `get_course_count()` and `get_existing_course_titles()`, each doing a full ChromaDB scan. Fix: merge into one method that fetches once and returns both values.
- **#26** `script.js` — `fetch` calls have no timeout; the UI hangs indefinitely if the server stalls. Fix: use `AbortController` with a 30-second timeout.
- **#29** `index.html` — CDN assets loaded without Subresource Integrity (SRI) hashes. Fix: add `integrity` and `crossorigin` attributes to each CDN `<link>` and `<script>` tag.

### Suggestions
- **#7** `config.py` / `ai_generator.py` — `max_tokens: 800` hardcoded in `ai_generator.py`. Move to `Config`.
- **#13** `ai_generator.py` — `MAX_TOOL_ROUNDS = 2` module-level constant. Move to `Config`.
- **#16** `search_tools.py` — `_sort_key` mutated into source dicts then deleted after sorting. Use `key=` lambda or a dataclass instead.
- **#19** `session_manager.py` — Conversation history serialized as a plain text string. Pass structured `[{role, content}]` dicts to the Claude API instead.
- **#22** `document_processor.py` — Sentence-split regex compiled inside `chunk_text` on every call. Move to a class-level `_SENTENCE_SPLIT_RE` constant.
- **#24** `vector_store.py` — `import json` appears inside methods. Move to module-level imports.
- **#27** `script.js` — `createNewSession` declared `async` but contains no `await`. Remove `async`.
- **#28** `script.js` — `console.log` debug statements left in `loadCourseStats`. Remove them.
- **#30** `index.html` — Manual `?v=10` cache-busting on CSS/JS links. Document the convention with a comment.

---

## How to fix an issue

1. **Read the file** listed for the issue before making any changes.
2. **Apply the minimal fix** described above — no extra refactoring, no unrelated cleanup.
3. **Summarize** what you changed and why in 2–3 sentences.

If a fix touches multiple files (e.g. #14 requires changes to both `search_tools.py` and `vector_store.py`), read all affected files first, then apply changes to each.
