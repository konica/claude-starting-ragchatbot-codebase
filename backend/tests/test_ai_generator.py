from unittest.mock import MagicMock, patch
import pytest
from ai_generator import AIGenerator


# --- Helpers ---

def _text_block(text="Hello"):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(name="search_course_content", tool_id="tu_1", tool_input=None):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = tool_input or {"query": "test"}
    return block


def _response(stop_reason="end_turn", content=None):
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content or [_text_block()]
    return resp


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="test-model")
        yield gen, mock_client


@pytest.fixture
def tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "tool result text"
    return tm


TOOLS = [{"name": "search_course_content", "description": "Search", "input_schema": {"type": "object"}}]


# --- Tests ---

class TestNoToolUse:
    def test_direct_response(self, generator, tool_manager):
        gen, mock_client = generator
        mock_client.messages.create.return_value = _response(
            stop_reason="end_turn", content=[_text_block("Direct answer")]
        )

        result = gen.generate_response("What is RAG?", tools=TOOLS, tool_manager=tool_manager)

        assert result == "Direct answer"
        assert mock_client.messages.create.call_count == 1
        tool_manager.execute_tool.assert_not_called()


class TestSingleToolRound:
    def test_claude_stops_after_one_round(self, generator, tool_manager):
        gen, mock_client = generator
        mock_client.messages.create.side_effect = [
            # First call: Claude wants to use a tool
            _response(stop_reason="tool_use", content=[_tool_use_block()]),
            # Second call (with tools): Claude responds with text
            _response(stop_reason="end_turn", content=[_text_block("Answer after search")]),
        ]

        result = gen.generate_response("Search something", tools=TOOLS, tool_manager=tool_manager)

        assert result == "Answer after search"
        assert mock_client.messages.create.call_count == 2
        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="test")


class TestTwoToolRounds:
    def test_max_rounds_exhausted(self, generator, tool_manager):
        gen, mock_client = generator
        mock_client.messages.create.side_effect = [
            # First call: tool use
            _response(stop_reason="tool_use", content=[_tool_use_block("get_course_outline", "tu_1", {"course": "MCP"})]),
            # Second call (round 1 follow-up, with tools): tool use again
            _response(stop_reason="tool_use", content=[_tool_use_block("search_course_content", "tu_2", {"query": "lesson 4"})]),
            # Third call (round 2, no tools): final text
            _response(stop_reason="end_turn", content=[_text_block("Final answer")]),
        ]

        result = gen.generate_response("Complex query", tools=TOOLS, tool_manager=tool_manager)

        assert result == "Final answer"
        assert mock_client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2


class TestToolError:
    def test_error_stops_loop(self, generator, tool_manager):
        gen, mock_client = generator
        tool_manager.execute_tool.side_effect = RuntimeError("connection failed")
        mock_client.messages.create.side_effect = [
            # First call: tool use
            _response(stop_reason="tool_use", content=[_tool_use_block()]),
            # Second call (no tools due to error): final text
            _response(stop_reason="end_turn", content=[_text_block("Error recovery answer")]),
        ]

        result = gen.generate_response("Search something", tools=TOOLS, tool_manager=tool_manager)

        assert result == "Error recovery answer"
        assert mock_client.messages.create.call_count == 2
        # Verify error string was passed in tool_result
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]  # last message is tool results
        assert "Tool execution error: connection failed" in tool_result_msg["content"][0]["content"]


class TestIntermediateCallsIncludeTools:
    def test_tools_in_intermediate_round(self, generator, tool_manager):
        gen, mock_client = generator
        mock_client.messages.create.side_effect = [
            _response(stop_reason="tool_use", content=[_tool_use_block("get_course_outline", "tu_1", {"course": "MCP"})]),
            _response(stop_reason="tool_use", content=[_tool_use_block("search_course_content", "tu_2", {"query": "lesson 4"})]),
            _response(stop_reason="end_turn", content=[_text_block("Done")]),
        ]

        gen.generate_response("Multi-step query", tools=TOOLS, tool_manager=tool_manager)

        # Second API call (intermediate) should include tools
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert second_call_kwargs["tool_choice"] == {"type": "auto"}


class TestFinalCallExcludesTools:
    def test_no_tools_in_final_call(self, generator, tool_manager):
        gen, mock_client = generator
        # Single round scenario
        mock_client.messages.create.side_effect = [
            _response(stop_reason="tool_use", content=[_tool_use_block()]),
            _response(stop_reason="end_turn", content=[_text_block("Answer")]),
        ]

        gen.generate_response("Query", tools=TOOLS, tool_manager=tool_manager)

        # When Claude stops after round 1, the follow-up call still includes tools
        # (it's an intermediate call). But if it returns end_turn, we're done.
        # Let's test the 2-round case where the last call must exclude tools.
        mock_client.messages.create.reset_mock()
        mock_client.messages.create.side_effect = [
            _response(stop_reason="tool_use", content=[_tool_use_block("t1", "tu_1")]),
            _response(stop_reason="tool_use", content=[_tool_use_block("t2", "tu_2")]),
            _response(stop_reason="end_turn", content=[_text_block("Final")]),
        ]

        gen.generate_response("Query 2", tools=TOOLS, tool_manager=tool_manager)

        last_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in last_call_kwargs
        assert "tool_choice" not in last_call_kwargs


class TestConversationHistory:
    def test_history_in_system_prompt(self, generator, tool_manager):
        gen, mock_client = generator
        mock_client.messages.create.return_value = _response(
            stop_reason="end_turn", content=[_text_block("With context")]
        )

        gen.generate_response(
            "Follow-up question",
            conversation_history="User: Hi\nAssistant: Hello",
            tools=TOOLS,
            tool_manager=tool_manager,
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "Previous conversation:" in call_kwargs["system"]
        assert "User: Hi" in call_kwargs["system"]
