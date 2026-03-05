# Feature: Course Outline Tool

**Branch:** `feat/course-outline-tool`
**Date:** 2026-03

## Context

Currently the only tool available to Claude is `search_course_content`, which performs semantic search over course content chunks. When a user asks for a course outline (e.g. "What is the outline of the MCP course?"), Claude must search content chunks and piece together the structure — often producing incomplete or inaccurate outlines.

The `course_catalog` collection already stores complete lesson metadata (`lessons_json`) for every course. A dedicated tool can return this structured data directly, giving Claude the exact course title, course link, and full lesson list to produce accurate outline responses.

## Files to Modify

| File | Change |
|------|--------|
| `backend/search_tools.py` | Add `CourseOutlineTool` class |
| `backend/rag_system.py` | Register the new tool |
| `backend/ai_generator.py` | Update system prompt to guide usage of the new tool |

## Implementation Steps

### 1. `backend/search_tools.py` — Add `CourseOutlineTool`

Add a new class after `CourseSearchTool`, following the same `Tool` pattern:

```python
class CourseOutlineTool(Tool):
    """Tool for retrieving course outline with full lesson list"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources: list = []  # For source tracking via ToolManager

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "get_course_outline",
            "description": "Get the complete outline of a course including title, link, and all lessons. Use this for questions about course structure, outlines, or lesson lists.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    }
                },
                "required": ["course_name"]
            }
        }

    def execute(self, course_name: str) -> str:
        # Resolve fuzzy course name via vector search
        resolved_title = self.store._resolve_course_name(course_name)
        if not resolved_title:
            return f"No course found matching '{course_name}'."

        # Get course metadata by ID (title)
        results = self.store.course_catalog.get(ids=[resolved_title])
        if not results or not results['metadatas'] or not results['metadatas'][0]:
            return f"No metadata found for course '{resolved_title}'."

        metadata = results['metadatas'][0]
        course_link = metadata.get('course_link', '')
        lessons = json.loads(metadata.get('lessons_json', '[]'))

        # Format output for Claude
        output = f"Course: {resolved_title}\n"
        output += f"Course Link: {course_link}\n\n"
        output += "Lessons:\n"
        for lesson in lessons:
            num = lesson.get('lesson_number', '?')
            title = lesson.get('lesson_title', 'Untitled')
            output += f"  {num}. {title}\n"

        # Set source for UI citation pill
        self.last_sources = [{"label": resolved_title, "url": course_link}]

        return output
```

Note: Add `import json` at the top of the file.

### 2. `backend/rag_system.py` — Register the new tool

Update import (line 7):
```python
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
```

Add registration after the existing `CourseSearchTool` registration (after line 25):
```python
self.outline_tool = CourseOutlineTool(self.vector_store)
self.tool_manager.register_tool(self.outline_tool)
```

### 3. `backend/ai_generator.py` — Update system prompt

Update `SYSTEM_PROMPT` to guide Claude on when to use which tool. Replace the current "Search Tool Usage" section with:

```
Tool Usage:
- **Course outline/structure questions** (e.g. "What topics does this course cover?", "List the lessons"):
  Use `get_course_outline` — returns the course title, course link, and complete lesson list with lesson numbers and titles
- **Course content/detail questions** (e.g. "Explain RAG from the MCP course", "What was covered in lesson 5"):
  Use `search_course_content` — searches actual lesson text for specific information
- **One tool call per query maximum**
- If a tool yields no results, state this clearly without offering alternatives
```

## Verification

1. Start the server (`./run.sh`)
2. Ask "What is the outline of the MCP course?" → should use `get_course_outline`, return course title, link, and full lesson list
3. Ask "What was covered in lesson 5 of the MCP course?" → should still use `search_course_content`
4. Ask a general question like "What is machine learning?" → should not use any tool
5. Verify source citation pill appears for outline queries with the correct course link
