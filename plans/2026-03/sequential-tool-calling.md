# Sequential Tool Calling (Up to 2 Rounds)

## Context

The current `AIGenerator` supports exactly one tool-call round: Claude calls a tool, results are appended, and a final API call (without tools) returns the answer. This prevents Claude from chaining tool calls — e.g., calling `get_course_outline` to discover a lesson title, then calling `search_course_content` with that title.

This refactor adds a loop inside `_handle_tool_execution` to support up to 2 sequential tool-call rounds, enabling multi-step reasoning.

## Files to Modify

| File | Change |
|---|---|
| `backend/ai_generator.py` | Add loop in `_handle_tool_execution`, update `SYSTEM_PROMPT` |
| `backend/tests/__init__.py` | Create (empty) |
| `backend/tests/test_ai_generator.py` | Create with 7 test cases |

No changes to `generate_response`, `rag_system.py`, `app.py`, or `search_tools.py`.

## Implementation Steps

### 1. Update `SYSTEM_PROMPT` in `backend/ai_generator.py`

Replace:
```
- **One tool call per query maximum**
```
With:
```
- **Up to 2 sequential tool calls per query** — use a second tool only when the first result reveals information needed for a precise follow-up search (e.g., get a course outline first, then search its content)
```

### 2. Add loop to `_handle_tool_execution`

The method signature stays identical: `(self, initial_response, base_params, tool_manager)`.

Loop logic (pseudocode):
```
MAX_TOOL_ROUNDS = 2
messages = copy of base_params["messages"]
current_response = initial_response

for round in range(1, MAX_TOOL_ROUNDS + 1):
    # Append assistant's tool-use content
    messages.append({"role": "assistant", "content": current_response.content})

    # Execute tools with try/except, collect results
    tool_results = []
    tool_error = False
    for block in current_response.content where block.type == "tool_use":
        try:
            result = tool_manager.execute_tool(block.name, **block.input)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        except Exception as e:
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Tool execution error: {e}"})
            tool_error = True

    messages.append({"role": "user", "content": tool_results})

    # Decide whether next call includes tools
    is_last_round = (round == MAX_TOOL_ROUNDS) or tool_error
    next_params = {**self.base_params, "messages": messages, "system": base_params["system"]}
    if not is_last_round:
        next_params["tools"] = base_params["tools"]
        next_params["tool_choice"] = {"type": "auto"}

    next_response = self.client.messages.create(**next_params)

    # If Claude doesn't want more tools or this is the last round, return
    if next_response.stop_reason != "tool_use" or is_last_round:
        return self._extract_text(next_response.content)

    # Loop again with new response
    current_response = next_response

# Safety fallback (should not reach here)
return self._extract_text(next_response.content)
```

Key design decisions:
- **Tools included in intermediate rounds** so Claude can choose to call another tool
- **Tools excluded on last round** (max reached or error) to force a text response
- **Error handling**: exception → error string in tool_result → `is_last_round = True` → final no-tools call
- **`generate_response` unchanged** — `api_params` already contains `tools`, which `_handle_tool_execution` reads from `base_params`

### 3. Create test files

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_ai_generator.py`.

**Test setup**: Mock `anthropic.Anthropic` client and `tool_manager`. Use `side_effect` on `mock_client.messages.create` to return different responses per call.

**Test cases** (all verify external behavior — API calls made, tools executed, text returned):

1. **No tool use**: `create` returns `end_turn` on first call. Assert: 1 API call, no tools executed, correct text.

2. **Single tool round, Claude stops**: Round 1 → `tool_use`, round 2 (with tools) → `end_turn`. Assert: 2 API calls, `execute_tool` called once with correct args.

3. **Two tool rounds (max exhausted)**: Round 1 → `tool_use`, round 2 → `tool_use`, round 3 (no tools) → `end_turn`. Assert: 3 API calls, `execute_tool` called twice, last call has no tools.

4. **Tool error stops loop**: Round 1 → `tool_use`, `execute_tool` raises exception, round 2 (no tools) → `end_turn`. Assert: 2 API calls, error string in tool_result content.

5. **Intermediate calls include tools**: In the 2-round scenario, assert the second `create` call includes `tools` and `tool_choice`.

6. **Final call never includes tools**: In all multi-round scenarios, assert the last `create` call has no `tools` key.

7. **Conversation history in system prompt**: When `conversation_history` provided, assert `system` param contains both static prompt and history.

## Verification

**Unit tests:**
```bash
cd backend && uv run python -m pytest tests/test_ai_generator.py -v
```

**Manual E2E:**
1. Start server: `./run.sh`
2. Test sequential query: "What topic does lesson 4 of course X cover? Find another course that discusses the same topic."
3. Test single-tool query: "What lessons are in the MCP course?" (should use 1 round)
4. Test no-tool query: "What is RAG?" (should use 0 rounds)
