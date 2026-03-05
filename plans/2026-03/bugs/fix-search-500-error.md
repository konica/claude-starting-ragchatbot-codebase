# Bug Fix: 500 Error on Course Content Search Queries

**Branch:** `feat/course-outline-tool`
**Date:** 2026-03-05

## Context

After adding the `CourseOutlineTool`, course-specific content queries like "What was covered in lesson 5 of the MCP course?" return a 500 error (`"list index out of range"`). Outline queries and general knowledge queries work fine.

The error occurs in `backend/ai_generator.py` at line 137: `final_response.content[0].text`. When the Claude API returns a response after tool execution, the code assumes `content[0]` exists and is a text block. If `content` is empty or the first block is not a text block, this raises an `IndexError`.

## Root Cause

In `ai_generator.py` `_handle_tool_execution()` (line 137) and `generate_response()` (line 89), `response.content[0].text` is accessed without verifying:
1. That `content` is non-empty
2. That the block at index `[0]` is a text block (not a `tool_use` block)

When Claude's initial response has `stop_reason == "tool_use"`, `content` can contain a mix of text and tool_use blocks. The non-tool path at line 89 is only reached when `stop_reason != "tool_use"`, so it's less likely to fail — but the final response at line 137 can fail if `content` is empty or structured unexpectedly.

## Files to Modify

| File | Change |
|------|--------|
| `backend/ai_generator.py` | Add safe text extraction from `content` blocks |

## Implementation Steps

### 1. `backend/ai_generator.py` — Add a helper to safely extract text

Add a helper method `_extract_text` to `AIGenerator` that iterates content blocks and returns the first text block's text, with a fallback message if none is found:

```python
def _extract_text(self, content) -> str:
    """Extract text from response content blocks, handling empty or non-text blocks."""
    for block in content:
        if hasattr(block, 'text'):
            return block.text
    return "I wasn't able to generate a response. Please try again."
```

### 2. Replace raw `content[0].text` accesses

- Line 89: `return response.content[0].text` → `return self._extract_text(response.content)`
- Line 137: `return final_response.content[0].text` → `return self._extract_text(final_response.content)`

## Verification

1. Start the server (`./run.sh`)
2. Ask "What was covered in lesson 5 of the MCP course?" → should return a proper answer (was failing with 500)
3. Ask "What is the outline of the MCP course?" → should still work (uses `get_course_outline`)
4. Ask "What is machine learning?" → should still work (no tool use)
5. Confirm no 500 errors in the server logs for any query type
