from __future__ import annotations

'''
Encapsulates an LLM response with proper API interaction and rendering.

This class manages the lifecycle of an LLM API call, handling:
- Message preparation
- Cycle string handling
- UI element generation
- Message history integration
- Usage tracking
'''

'''
💙3.0 LLM RESPONSE LIFECYCLE MANAGEMENT

LLMResponse encapsulates a complete LLM interaction as a serializable object. It maintains a single .response attribute containing a JSON-serializable dictionary with standardized structure.

Its .usage property guarantees return of a Usage object regardless of underlying data, ensuring consistent interface. The object provides tool execution detection via .has_tools boolean property and extracts tool commands via .tool_blocks.

This layer handles all presentation concerns including cycle prefixing (🚲N), suffix management, and UI rendering through get_ui_elements(). It guarantees consistent serialization for both persistence and message history via as_message().

Battery calculation happens exclusively through dedicated calculate_battery() method, never mixing concerns with query logic.

CONTRACT: A serializable object with consistent properties that shields consumers from all API complexities.
'''

import copy
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from inXeption.anthropic_config import MODEL_CONSTRAINTS
from inXeption.llm import ResponseOutcome, count_tokens, query_llm_api
from inXeption.UIObjects import UIBlockType, UIChatType, UIElement
from inXeption.Usage import Usage
from inXeption.utils.yaml_utils import dump_str

logger = logging.getLogger(__name__)


def _yaml_to_file(log_dir, file_prefix, data):
    '''Simple helper to log serialized data to a YAML file'''
    log_path = Path(log_dir) / f'{file_prefix}.yaml'
    with open(log_path, 'w') as f:
        f.write(dump_str(data))
    logger.info(f'Wrote {file_prefix} data to {log_path}')


def build_messages(
    mode: str,  # 'llm' or 'count_tokens'
    previous_interactions,  # Forward reference
    current_interaction,  # Forward reference
    prompts: dict,
):
    '''
    Build and prepare messages for LLM API.

    Args:
        mode: Either 'llm' for normal API calls or 'count_tokens' for token counting
        previous_interactions: List of Interaction objects
        current_interaction: Current Interaction object
        prompts: Dictionary containing system prompt and suffix

    Returns:
        List of properly formatted messages for the API
    '''
    # Build base messages from interactions
    messages = []

    # Process previous interactions
    for interaction in previous_interactions:
        messages.extend(interaction.as_messages(mode))

    # Add current interaction
    messages.extend(current_interaction.as_messages(mode))

    # SANITIZE: Ensure messages end with a user message
    if not (messages and messages[-1]['role'] == 'user'):
        messages.append(
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': '<dummy text to ensure final user message>',
                    }
                ],
            }
        )

    # Add suffix to the last user message
    # The suffix contains {{BATTERY}} placeholder at this point
    messages[-1]['content'].append({'type': 'text', 'text': prompts['suffix']})

    return messages


class LLMResponse(BaseModel):
    '''
    Represents an LLM response with consistent error handling and rendering.
    '''

    cycle_string: str
    outcome: ResponseOutcome | None = None
    response: dict[str, Any] | None = Field(default=None)

    model_config = {
        'arbitrary_types_allowed': True,
        'json_encoders': {Enum: lambda v: v.value},
    }

    @classmethod
    def create_tool_interrupted(cls, cycle_string):
        '''Create a response for when a tool execution has been interrupted'''
        return cls(
            cycle_string=cycle_string,
            outcome=ResponseOutcome.END_TURN,
            response={
                'outcome': ResponseOutcome.END_TURN,
                'content_blocks': [
                    {'type': 'text', 'text': '🛑 Tool execution interrupted by user.'}
                ],
                'usage': None,  # The usage property will handle converting this to a zero-usage object
            },
        )

    async def calculate_battery(
        self,
        prompts,
        tools,
        previous_interactions,
        current_interaction,
        render_fn,
    ):
        '''
        Calculate battery percentage without actually calling the LLM API.

        Returns:
            Battery percentage based on token count relative to max input tokens,
            or -1 if token counting failed
        '''
        # Build messages for token counting
        messages = build_messages(
            mode='count_tokens',
            previous_interactions=previous_interactions,
            current_interaction=current_interaction,
            prompts=prompts,
        )

        # Calculate token count and battery percentage
        current_token_count = await count_tokens(prompts, tools, messages, render_fn)

        # If token counting failed (signaled by -1), return -1 to indicate failure
        if current_token_count == -1:
            return -1

        # Normal calculation if token counting succeeded
        max_tokens = MODEL_CONSTRAINTS['max_input_tokens']
        return 100 - (current_token_count / max_tokens * 100)

    async def query(
        self,
        prompts,
        tools,
        previous_interactions,
        current_interaction,
        interrupt_check,
        render_fn,
    ):
        '''
        Query the LLM API with consistent error handling and interruption support.
        '''

        # Build and prepare messages
        messages = build_messages(
            mode='llm',
            previous_interactions=previous_interactions,
            current_interaction=current_interaction,
            prompts=prompts,
        )

        # Calculate battery for message preparation
        battery_pct = await self.calculate_battery(
            prompts, tools, previous_interactions, current_interaction, render_fn
        )

        # Prepare messages with battery information interpolated
        prepared_messages = self._prepare_messages(messages, prompts, battery_pct)

        # Log the request
        _yaml_to_file(os.environ['LOG_DIR'], 'request', prepared_messages)

        # ⚡️ Execute API call through middle layer
        self.response = await query_llm_api(
            prepared_messages, prompts, tools, interrupt_check
        )

        # Log the response
        _yaml_to_file(os.environ['LOG_DIR'], 'response', self.response)

        # Add cycle indicator to the first text block in content
        self._add_cycle_indicator()

        # Return None per original API contract

    def _prepare_messages(self, messages, prompts, battery_pct):
        '''Prepare messages with cache point and interpolated battery information'''
        messages_copy = copy.deepcopy(messages)

        # Set cache control on last message
        if messages_copy and messages_copy[-1]['role'] == 'user':
            last_content = messages_copy[-1]['content']
            # ... in penultimate block (LAST block is 'suffix')
            last_content[-2]['cache_control'] = {'type': 'ephemeral'}

            # Create battery status text
            if battery_pct == -1:
                # Special case for token counting failure
                battery_text = '⚠️ SYSTEM NOTICE: ❌ Token counting failed'
            else:
                battery_emoji = '🪫' if battery_pct < 20 else '🔋'
                battery_text = f'⚠️ SYSTEM NOTICE: {battery_emoji} {battery_pct:.0f}%'

                # Extra warning for low battery
                if battery_pct < 20:
                    battery_text += '\n⚠️ BATTERY LOW! Wrap up your current task for a clean handoff.'

            # Interpolate battery information in all content blocks
            for i, block in enumerate(last_content):
                if block['type'] == 'text' and '{{BATTERY}}' in block['text']:
                    last_content[i]['text'] = block['text'].replace(
                        '{{BATTERY}}', battery_text
                    )

        return messages_copy

    def _add_cycle_indicator(self):
        '''Add cycle indicator to first text block'''
        # Find the first text block in our content blocks
        first_textblock = next(
            (b for b in self.response['content_blocks'] if b['type'] == 'text'), None
        )
        if first_textblock is not None:
            lines = first_textblock['text'].splitlines() or ['<No content>']
            start_index = 1 if '🚲' in lines[0] else 0
            first_textblock['text'] = (
                self.cycle_string + '\n\n' + '\n'.join(lines[start_index:])
            )

    def get_ui_elements(self):
        '''Generate UI elements on demand for rendering based on response outcome and content'''

        # Handle success cases (END_TURN or TOOL_USE) with normal rendering
        if self.response['outcome'] in [
            ResponseOutcome.END_TURN,
            ResponseOutcome.TOOL_USE,
        ]:
            ui_elements = []

            # Process content blocks based on their type
            for block in self.response['content_blocks']:
                if block['type'] == 'thinking':
                    ui_elements.append(
                        UIElement.singleblock(
                            '💭',
                            UIChatType.ASSISTANT,
                            UIBlockType.MARKDOWN,
                            block['thinking'],
                        )
                    )

                elif block['type'] == 'text':
                    ui_elements.append(
                        UIElement.singleblock(
                            '🤖',
                            UIChatType.ASSISTANT,
                            UIBlockType.MARKDOWN,
                            block['text'],
                        )
                    )

                elif block['type'] == 'tool_use':
                    tool_content = dump_str(
                        {'tool': block['name'], 'input': block['input']}
                    )
                    ui_elements.append(
                        UIElement.singleblock(
                            '🔧', UIChatType.TOOL, UIBlockType.CODE, tool_content
                        )
                    )

            return ui_elements

        # Handle error cases with warning avatar
        else:
            # For errors, we expect a single text block with error details
            error_content = self.response['content_blocks'][0]['text']
            return [
                UIElement.singleblock(
                    '⚠️', UIChatType.SYSTEM, UIBlockType.CODE, error_content
                )
            ]

    def render(self, render_fn):
        '''Render UI elements for this response'''
        for ui_element in self.get_ui_elements():
            # Use the UIElement's render method instead of passing it directly
            ui_element.render(render_fn)

    def as_message(self):
        '''Convert response to format suitable for message history'''
        return {'role': 'assistant', 'content': self.response['content_blocks']}

    @property
    def has_tools(self):
        '''Check if this response has tools to execute'''
        return self.response['outcome'] == ResponseOutcome.TOOL_USE

    @property
    def tool_blocks(self):
        '''Extract tool blocks from content'''
        return (
            [
                block
                for block in self.response['content_blocks']
                if block['type'] == 'tool_use'
            ]
            if self.has_tools
            else []
        )

    @property
    def usage(self):
        '''Get usage data as a Usage object'''
        model_used = self.response.get('model_used', 'sonnet')
        return Usage.from_dict(self.response.get('usage', {}), model=model_used)
