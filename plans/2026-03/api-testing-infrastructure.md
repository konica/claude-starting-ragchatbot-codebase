# API Testing Infrastructure

## Context

The existing test suite (`backend/tests/test_ai_generator.py`) covers the AI generator's tool-calling logic but has no tests for the FastAPI API endpoints. Importing `backend/app.py` directly is problematic because it:

1. Instantiates `RAGSystem(config)` at module level (triggers ChromaDB, sentence-transformers)
2. Mounts `StaticFiles(directory="../frontend")` which doesn't exist in the test environment

We need API endpoint tests that avoid these import-time side effects.

## Approach

Define a **minimal test FastAPI app** in `conftest.py` that mirrors the real endpoints from `app.py` but uses a mocked `RAGSystem`. This avoids importing `app.py` entirely, sidestepping both the static file mount and the heavy module-level initialization.

## Files to Modify

### 1. `pyproject.toml` — Add pytest configuration
- Add `[tool.pytest.ini_options]` with `testpaths`, `pythonpath`, and `asyncio_mode`
- Add `httpx` and `pytest-asyncio` to dev dependencies

### 2. `backend/tests/conftest.py` (new) — Shared fixtures
- **`mock_rag_system`** — a `MagicMock` preconfigured with default return values for `query()`, `get_course_analytics()`, and `session_manager.create_session()`
- **`test_app`** — a FastAPI app that defines the same `/api/query` and `/api/courses` endpoints as `app.py`, wired to the mock RAG system (reuses the Pydantic models by importing them from `app` — but since we can't import `app`, we'll define them inline or import just the models)
- **`client`** — an `httpx.AsyncClient` configured with `ASGITransport` pointing at the test app

Since importing `app.py` is problematic, the Pydantic models (`QueryRequest`, `QueryResponse`, `Source`, `CourseStats`) will be **defined inline** in conftest.py. The endpoint logic will mirror `app.py` but delegate to the mock.

### 3. `backend/tests/test_api.py` (new) — API endpoint tests

**`/api/query` tests:**
- `test_query_success` — valid query returns 200 with answer, sources, session_id
- `test_query_with_session_id` — passing a session_id uses it instead of creating one
- `test_query_empty_string` — empty query returns 422 validation error
- `test_query_whitespace_only` — whitespace-only query returns 422
- `test_query_too_long` — query > 2000 chars returns 422
- `test_query_internal_error` — RAG system exception returns 500

**`/api/courses` tests:**
- `test_courses_success` — returns 200 with total_courses and course_titles
- `test_courses_internal_error` — exception returns 500

## Implementation Steps

1. Add `httpx` and `pytest-asyncio` to dev dependencies in `pyproject.toml`
2. Add `[tool.pytest.ini_options]` to `pyproject.toml`
3. Create `backend/tests/conftest.py` with the test app and fixtures
4. Create `backend/tests/test_api.py` with endpoint tests
5. Run `uv sync` to install new dev dependencies
6. Run tests with `cd backend && uv run pytest tests/ -v`

## Verification

- All existing tests in `test_ai_generator.py` still pass
- All new API tests pass
- `uv run pytest tests/ -v` from `backend/` shows clean output
