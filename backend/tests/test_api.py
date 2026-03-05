import pytest


class TestQueryEndpoint:
    async def test_query_success(self, client, mock_rag_system):
        resp = await client.post("/api/query", json={"query": "What is RAG?"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "This is a test answer."
        assert data["session_id"] == "test-session-123"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["label"] == "Lesson 1"
        mock_rag_system.session_manager.create_session.assert_called_once()

    async def test_query_with_session_id(self, client, mock_rag_system):
        resp = await client.post(
            "/api/query", json={"query": "Follow-up", "session_id": "my-session"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "my-session"
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("Follow-up", "my-session")

    async def test_query_empty_string(self, client):
        resp = await client.post("/api/query", json={"query": ""})
        assert resp.status_code == 422

    async def test_query_whitespace_only(self, client):
        resp = await client.post("/api/query", json={"query": "   "})
        assert resp.status_code == 422

    async def test_query_too_long(self, client):
        resp = await client.post("/api/query", json={"query": "a" * 2001})
        assert resp.status_code == 422

    async def test_query_internal_error(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("database down")

        resp = await client.post("/api/query", json={"query": "Hello"})

        assert resp.status_code == 500
        assert "database down" in resp.json()["detail"]


class TestCoursesEndpoint:
    async def test_courses_success(self, client):
        resp = await client.get("/api/courses")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert "Intro to RAG" in data["course_titles"]
        assert "Advanced Embeddings" in data["course_titles"]

    async def test_courses_internal_error(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("store error")

        resp = await client.get("/api/courses")

        assert resp.status_code == 500
        assert "store error" in resp.json()["detail"]
