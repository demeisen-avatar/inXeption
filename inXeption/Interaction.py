from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# LLMResponse imported here for the final battery calculation
from inXeption.LLMResponse import LLMResponse
from inXeption.stats import format_stats_lines, format_stats_text
from inXeption.tools.collection import ToolCollection
from inXeption.Turn import Turn
from inXeption.UIObjects import UIBlockType, UIChatType, UIElement
from inXeption.Usage import Usage

'''
💙4.0 INTERACTION LIFECYCLE ORCHESTRATION
Core conversational unit: user-message → one or more (LLM → tools) turns

The Interaction class manages the full conversation lifecycle with critical responsibilities:
- Creates and manages a sequence of Turn objects until completion or interruption
- Maintains tool execution context through ToolCollection lifecycle
- Builds message history from previous interactions + current turns
- Automatically adds acknowledgment turn after tool interruption
- Calculates and tracks token usage and battery percentage
- Handles rendering of all interaction components (user message, turns, tools, stats)
- Maintains consistency between what's rendered and what's in message history

This class is designed to be serializable for persistence in Streamlit's session_state
while maintaining a complete separation from the UI implementation.
'''


class Interaction(BaseModel):
    '''Represents a full interaction, coordinating turns and tracking stats'''

    user_message: str
    index: Optional[int] = None  # Added to track interaction number
    turns: List[Turn] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    stats_ui_element: Optional[Dict[str, Any]] = None
    usage: Optional[Usage] = None
    total_usage: Optional[Usage] = None
    sonnet_usage: Optional[Usage] = None
    opus_usage: Optional[Usage] = None
    total_sonnet_usage: Optional[Usage] = None
    total_opus_usage: Optional[Usage] = None
    final_battery: float = 100.0  # Default to 100% battery

    model_config = {'arbitrary_types_allowed': True}

    async def run(
        self,
        render_fn,
        interrupt_check,
        prompts,
        previous_interactions,
    ):
        '''Execute the complete interaction lifecycle'''
        # Deserialize previous interactions once at the beginning
        previous_interactions_objects = [
            Interaction.model_validate(data) for data in previous_interactions
        ]

        # Render user message
        self.render_user_message(render_fn)

        # Create tool collection
        tools = ToolCollection()

        # Process turns until completion
        async with tools.lifecycle_context():
            # Reset time for accurate measurements
            self.start_time = datetime.now()

            while True:
                # Create a new turn with interaction index (zero-based)
                interaction_index = len(previous_interactions_objects)
                turn = Turn(index=len(self.turns), interaction_index=interaction_index)

                # Run the turn and get continuation status
                continue_interaction = await turn.run(
                    tools=tools,
                    previous_interactions=previous_interactions_objects,
                    current_interaction=self,
                    prompts=prompts,
                    render_fn=render_fn,
                    interrupt_check=interrupt_check,
                )

                # Store turn
                self.turns.append(turn)

                # Check whether to continue
                if not continue_interaction:
                    # If tool execution was interrupted, add an acknowledgment turn
                    if turn.tool_results:
                        # Create an acknowledgment turn for the interrupted tool with interaction index (zero-based)
                        interaction_index = len(previous_interactions_objects)
                        ack_turn = Turn(
                            index=len(self.turns), interaction_index=interaction_index
                        )
                        # Use the factory method for creating a tool interrupted response
                        # Use the ack_turn's cycle_string property to ensure consistent formatting
                        ack_turn.llm_response = LLMResponse.create_tool_interrupted(
                            cycle_string=ack_turn.cycle_string
                        )
                        # Render the acknowledgment
                        ack_turn.llm_response.render(render_fn)
                        # Store the turn
                        self.turns.append(ack_turn)
                    break

            # Calculate usage statistics for this interaction by model
            self.sonnet_usage = Usage(model='sonnet')
            self.opus_usage = Usage(model='opus')

            for turn in self.turns:
                if turn.llm_response:
                    turn_usage = turn.llm_response.usage
                    if turn_usage.model == 'sonnet':
                        self.sonnet_usage += turn_usage
                    elif turn_usage.model == 'opus':
                        self.opus_usage += turn_usage

            # Combined usage for backward compatibility
            self.usage = self.sonnet_usage + self.opus_usage

            # Calculate total usage by model
            self.total_sonnet_usage = Usage(model='sonnet')
            self.total_opus_usage = Usage(model='opus')

            if previous_interactions:
                # Get the most recent interaction's total usage
                prev_interaction = Interaction.model_validate(previous_interactions[-1])
                if hasattr(prev_interaction, 'total_sonnet_usage'):
                    self.total_sonnet_usage = deepcopy(
                        prev_interaction.total_sonnet_usage
                    )
                if hasattr(prev_interaction, 'total_opus_usage'):
                    self.total_opus_usage = deepcopy(prev_interaction.total_opus_usage)
                # Handle old interactions without per-model tracking
                elif hasattr(prev_interaction, 'total_usage'):
                    # Assume all previous usage was sonnet
                    self.total_sonnet_usage = deepcopy(prev_interaction.total_usage)
                    self.total_sonnet_usage.model = 'sonnet'

            # Add current usage to totals
            self.total_sonnet_usage += self.sonnet_usage
            self.total_opus_usage += self.opus_usage

            # Combined total for backward compatibility
            self.total_usage = self.total_sonnet_usage + self.total_opus_usage

            # Calculate final battery percentage - INSIDE the lifecycle context using LLMResponse
            interaction_index = len(previous_interactions_objects)
            temp_llm_response = LLMResponse(
                cycle_string=f'`🚲{interaction_index}.{len(self.turns)} {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`'
            )

            # Get tools schema while context is active
            tools_schema = tools.schemas()

            # Calculate battery using the dedicated battery calculation method
            self.final_battery = await temp_llm_response.calculate_battery(
                prompts=prompts,
                tools=tools_schema,
                previous_interactions=previous_interactions_objects,
                current_interaction=self,
                render_fn=render_fn,
            )

            # Generate and render stats UI element
            await self.render_stats(render_fn, previous_interactions_objects)

        return self

    def render_user_message(self, render_fn):
        '''Render the user message'''
        UIElement.singleblock(
            '🧬', UIChatType.USER, UIBlockType.TEXT, self.user_message
        ).render(render_fn)

    def render(self, render_fn):
        '''Render the entire interaction'''
        # Render user message
        self.render_user_message(render_fn)

        # Let each turn handle its own rendering
        for turn in self.turns:
            turn.llm_response.render(render_fn)

            # Render tool results
            for tool in turn.tool_results.values():
                tool.render(render_fn)

        # Render stats if available
        if self.stats_ui_element:
            render_fn(self.stats_ui_element)

    def as_messages(self, mode='llm'):
        '''
        Convert to message objects for LLM history

        Args:
            mode: Either 'llm' for normal API calls or 'count_tokens' for token counting
        '''
        messages = [
            {
                'role': 'user',
                'content': [{'type': 'text', 'text': '🧬' + self.user_message}],
            }
        ]

        for turn in self.turns:
            messages.extend(turn.as_messages(mode))

        return messages

    async def render_stats(self, render_fn, previous_interactions):
        '''Generate and render stats UI element with rich usage information'''
        # Get previous battery percentage - let attributes exist
        prev_battery = 100.0
        if previous_interactions:
            prev_interaction = Interaction.model_validate(previous_interactions[-1])
            # Use the final_battery attribute directly - if it doesn't exist, let it raise an error
            prev_battery = prev_interaction.final_battery

        # Calculate interaction index based on previous interactions
        interaction_index = len(previous_interactions) + 1

        # Format all stats lines using utility functions
        all_lines = format_stats_lines(self, prev_battery)

        # Format as text, passing the calculated interaction index
        usage_text = format_stats_text(all_lines, self.elapsed_time, interaction_index)

        # Create stats UI element
        stats_ui = UIElement.singleblock(
            '💰', UIChatType.SYSTEM, UIBlockType.CODE, usage_text
        )

        # Store it in the interaction object for serialization
        self.stats_ui_element = stats_ui.model_dump()

        # Render the stats
        stats_ui.render(render_fn)

    @property
    def elapsed_time(self):
        '''Format elapsed time as minutes and seconds'''
        elapsed = (datetime.now() - self.start_time).total_seconds()
        minutes, seconds = divmod(int(elapsed), 60)
        return f'{minutes}m{seconds}s'
