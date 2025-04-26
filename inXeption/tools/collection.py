'''
💙5.0 TOOLS LIFECYCLE MANAGEMENT
The tools system uses a critical async context manager pattern to ensure proper lifecycle management across turns:

- Each Interaction creates a single ToolCollection that lives for the entire interaction duration
- The async context manager in ToolCollection.lifecycle_context() ensures:
  1. Tool state persistence: Tools can maintain state across multiple turns in an interaction
  2. Resource cleanup: All tools receive cleanup signals when interactions end
  3. Process management: Bash tool can properly terminate subprocess trees to prevent orphaned processes
  4. Error resilience: Tools can safely capture partial results during interruption

This design enables critical capabilities:
- Edit tool can track file history for undo_edit across multiple turns
- Bash tool ensures process cleanup and captures partial output during interruptions
- Bash tool maintains environment state between turns (e.g., environment variables set in one turn
  are accessible in subsequent turns of the same interaction)
- All tools receive an interrupt_check callable for cooperative cancellation, though currently
  only bash tool fully implements this pattern as it's the only tool capable of consuming
  significant wall clock time

Key implementation aspects:
- ToolCollection.lifecycle_context() returns self as an async context manager
- Interaction.run() uses "async with tools.lifecycle_context()" to bind the lifecycle
- Each tool implements its own cleanup() method that ToolCollection calls during __aexit__
- Tools receive an interrupt_check callable that they periodically check to abort long-running operations
'''

import logging
import os
import traceback

from inXeption.tools.base import ToolError
from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType
from inXeption.utils.misc import play_sound
from inXeption.utils.yaml_utils import load_str

# Initialize logger
logger = logging.getLogger(__name__)


class ToolCollection:
    '''
    Collection of tools that manages their lifecycle and dispatches calls.
    '''

    def __init__(self):
        '''Initialize with the available tools.'''
        # Import tools here to avoid circular imports
        from .bash import BashTool
        from .computer import ComputerTool
        from .edit import EditTool
        from .python import PythonTool

        # Create tool instances
        self.tools = {
            'bash_tool': BashTool(),
            'computer_tool': ComputerTool(),
            'edit_tool': EditTool(),
            'python_tool': PythonTool(),
        }

    def schemas(self):
        '''Return schemas for all tools for LLM API.'''
        return [load_str(tool.yaml) for tool in self.tools.values()]

    async def execute(self, tool_use_block, interrupt_check):
        '''
        Execute a tool and return a ToolResult.

        Args:
            tool_use_block: Tool block from LLM with id, name, input
            interrupt_check: Function that returns True if execution should be interrupted

        Returns:
            ToolResult: A properly structured tool result object with UI elements
        '''
        # Access block properties as dictionary items
        tool_name = tool_use_block.get('name')
        tool_id = tool_use_block.get('id')
        tool_input = tool_use_block.get('input')

        tool = self.tools.get(tool_name)
        if not tool:
            msg = f'Tool {tool_name} is not available'
            logger.error(msg)

            # Create error UI element for tool not found
            from .ToolResult import ToolResult

            error_block = UIBlock(type=UIBlockType.ERROR, content=msg)
            return ToolResult.from_ui_element('⚠️', UIChatType.TOOL, error_block)

        try:
            # Call the tool with the input, providing ID and interrupt check
            # Tools now return proper ToolResult objects
            result = await tool(
                tool_id=tool_id, interrupt_check=interrupt_check, **tool_input
            )
            return result

        except ToolError as e:
            # Handle expected domain-specific errors
            msg = f'Tool error in {tool_name}: {str(e)}'
            logger.error(msg)

            # Create error UI element for expected tool errors
            from .ToolResult import ToolResult

            error_block = UIBlock(type=UIBlockType.ERROR, content=msg)
            return ToolResult.from_ui_element('⚠️', UIChatType.TOOL, error_block)

        except Exception as e:
            # Handle unexpected exceptions with full stack trace
            error_info = {
                'error': f'Unexpected error executing tool {tool_name}: {str(e)}',
                'error_type': e.__class__.__name__,
                'traceback': traceback.format_exc(),
            }
            from inXeption.utils.yaml_utils import dump_str

            msg = dump_str(error_info)
            logger.error(msg)

            # Create error UI element with traceback for unexpected errors
            from .ToolResult import ToolResult

            error_blocks = [
                UIBlock(
                    type=UIBlockType.ERROR,
                    content=f'Unexpected error in {tool_name}: {str(e)}',
                ),
                UIBlock(type=UIBlockType.CODE, content=traceback.format_exc()),
            ]
            return ToolResult.from_ui_element('⛔️', UIChatType.TOOL, error_blocks)

    async def __aenter__(self):
        '''Context manager entry, returns self.'''
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        '''Context manager exit, clean up tools.'''
        # Check if we're in loop test mode to use a different sound
        is_loop_test = os.environ.get('LOOP_TEST_MODE')
        sound_file = (
            'test-interaction-completed.mp3'
            if is_loop_test
            else 'interaction-completed.mp3'
        )
        play_sound(sound_file)

        for tool_name, tool in self.tools.items():
            try:
                await tool.cleanup()
            except Exception as e:
                logger.error(f'Error cleaning up tool {tool_name}: {e}')

    def lifecycle_context(self):
        '''Get the context manager for tool lifecycle.'''
        return self
