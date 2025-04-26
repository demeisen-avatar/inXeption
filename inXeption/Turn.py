from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from inXeption.LLMResponse import LLMResponse

# from inXeption.utils.tool_utils import result_to_llm_blocks
from inXeption.tools.ToolResult import ToolResult

'''
💙4.1 TURN EXECUTION AND COORDINATION
A Turn orchestrates one complete conversation cycle:

- Coordinates LLMResponse creation and API interaction
- Handles tool execution when requested by LLM
- Manages interruption during both LLM and tool phases
- Creates a consistent view between what's rendered to humans and what's in message history
- Returns boolean indicating whether interaction should continue
- Ensures robustness against all API outcomes (success, errors, interruptions)
- Provides serialization support for persistence across Streamlit re-renders
'''


class Turn(BaseModel):
    '''Represents a single turn in the conversation'''

    index: int
    interaction_index: int
    timestamp: datetime = Field(default_factory=datetime.now)
    llm_response: LLMResponse | None = None

    # Store tool result dictionaries
    tool_results: dict[str, ToolResult] = Field(default_factory=dict)

    model_config = {
        'arbitrary_types_allowed': True,
    }

    @property
    def cycle_string(self):
        '''Generate a cycle identifier string'''
        return f'`🚲{self.interaction_index}.{self.index} {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}`'

    async def run(
        self,
        tools,
        previous_interactions,
        current_interaction,
        prompts,
        render_fn,
        interrupt_check,
    ):
        '''Execute the full turn lifecycle'''
        # Create LLM response object
        self.llm_response = LLMResponse(cycle_string=self.cycle_string)

        # Query LLM and handle interrupts properly - battery calculation is now internal
        await self.llm_response.query(
            prompts=prompts,
            tools=tools.schemas(),
            previous_interactions=previous_interactions,
            current_interaction=current_interaction,
            interrupt_check=interrupt_check,
        )

        # Render the response
        self.llm_response.render(render_fn)

        # Check if we're done with this turn
        if not self.llm_response.has_tools:
            return False

        # Execute tools if needed - tools now return result dictionaries
        self.tool_results = {
            block['id']: await tools.execute(block, interrupt_check)
            for block in self.llm_response.tool_blocks
        }

        # Render tool results using the render method
        for result in self.tool_results.values():
            result.render(render_fn)

        # Continue if not interrupted
        return not interrupt_check()

    def as_messages(self, mode='llm'):
        '''
        Convert this turn to message objects for LLM API

        Args:
            mode: Either 'llm' for normal API calls or 'count_tokens' for token counting
        '''
        messages = []

        # Only include llm response if it exists
        if self.llm_response:
            # Get the basic message
            assistant_message = self.llm_response.as_message()

            # For token counting, strip thinking blocks
            if mode == 'count_tokens':
                assistant_message = {
                    'role': assistant_message['role'],
                    'content': [
                        b
                        for b in assistant_message['content']
                        if b['type'] != 'thinking'
                    ],
                }

            messages.append(assistant_message)

        # Add tool results if present (as "user" message with tool_result blocks)
        if self.tool_results:
            messages.append(
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'content': tool_result.as_llm_blocks(),
                        }
                        for tool_id, tool_result in self.tool_results.items()
                    ],
                }
            )

        return messages
