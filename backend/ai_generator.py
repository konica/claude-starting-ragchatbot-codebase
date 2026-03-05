import anthropic
from pathlib import Path
from typing import List, Optional, Dict, Any

MAX_TOOL_ROUNDS = 2

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text()


SYSTEM_PROMPT = _load_prompt("system.md")


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def _extract_text(self, content) -> str:
        """Extract text from response content blocks, handling empty or non-text blocks."""
        for block in content:
            if hasattr(block, "text"):
                return block.text
        return "I wasn't able to generate a response. Please try again."

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return self._extract_text(response.content)

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ):
        """
        Handle execution of tool calls and get follow-up response.
        Supports up to MAX_TOOL_ROUNDS sequential tool-call rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for round in range(1, MAX_TOOL_ROUNDS + 1):
            # Append assistant's tool-use content
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute tools with error handling
            tool_results = []
            tool_error = False
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                    except Exception as e:
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Tool execution error: {e}",
                            }
                        )
                        tool_error = True

            messages.append({"role": "user", "content": tool_results})

            # Include tools in intermediate rounds, exclude on last round
            is_last_round = (round == MAX_TOOL_ROUNDS) or tool_error
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }
            if not is_last_round:
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = {"type": "auto"}

            next_response = self.client.messages.create(**next_params)

            # Return if Claude doesn't want more tools or this is the last round
            if next_response.stop_reason != "tool_use" or is_last_round:
                return self._extract_text(next_response.content)

            current_response = next_response

        return self._extract_text(next_response.content)
