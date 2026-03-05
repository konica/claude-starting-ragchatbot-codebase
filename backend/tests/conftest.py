from unittest.mock import MagicMock
from typing import List, Optional

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, field_validator


# --- Pydantic models (mirrors app.py, avoids importing it) ---


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty or whitespace")
        if len(v) > 2000:
            raise ValueError("query must not exceed 2000 characters")
        return v

    @field_validator("session_id")
    @classmethod
    def session_id_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip() or None
        return v


class Source(BaseModel):
    label: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# --- Fixtures ---


@pytest.fixture
def mock_rag_system():
    rag = MagicMock()
    rag.query.return_value = (
        "This is a test answer.",
        [{"label": "Lesson 1", "url": "https://example.com/lesson1"}],
    )
    rag.session_manager.create_session.return_value = "test-session-123"
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to RAG", "Advanced Embeddings"],
    }
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
