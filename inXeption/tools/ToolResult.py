from typing import List  # Any, Dict, List, Union

from pydantic import BaseModel, Field

from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType, UIElement


class ToolResult(BaseModel):
    '''
    Base class for all tool results

    Contains a list of UI elements for rendering tool results
    '''

    ui_elements: List[UIElement] = Field(default_factory=list)

    model_config = {
        'arbitrary_types_allowed': True,
    }

    def __init__(self, ui_elements):
        '''
        Initialize with [UIElement]
        '''
        super().__init__(ui_elements=ui_elements)

    @classmethod
    def from_ui_element(cls, avatar, chat_type, block_or_blocks):
        '''Create a ToolResult from a single UI element.

        Args:
            avatar: The avatar for the UI element
            chat_type: The chat_type for the UI element (UIChatType)
            block_or_blocks: A single UIBlock or list of UIBlocks

        Returns:
            A new ToolResult instance
        '''
        blocks = (
            block_or_blocks if isinstance(block_or_blocks, list) else [block_or_blocks]
        )
        ui_element = UIElement(avatar=avatar, chat_type=chat_type, blocks=blocks)
        return cls([ui_element])

    @classmethod
    def from_ui_elements(cls, elements):
        '''Create a ToolResult from multiple UI elements.'''
        return cls(elements)

    @classmethod
    def from_error(cls, message, include_traceback=False, traceback_text=None):
        '''Create a ToolResult representing an error.

        Args:
            message: The error message
            include_traceback: Whether to include a traceback
            traceback_text: The traceback text (required if include_traceback is True)

        Returns:
            A new ToolResult instance
        '''
        blocks = [UIBlock(type=UIBlockType.ERROR, content=message)]
        if include_traceback and traceback_text:
            blocks.append(UIBlock(type=UIBlockType.CODE, content=traceback_text))

        element = UIElement(avatar='⛔️', chat_type=UIChatType.TOOL, blocks=blocks)

        return cls([element])

    def render(self, render_fn):
        '''Render this tool result to the UI'''
        for element in self.ui_elements:
            render_fn(element.model_dump())

    def as_llm_blocks(self):
        '''Convert to LLM API block format'''

        def convert(block):
            # Convert UIBlock to LLM block format
            if block.type == UIBlockType.IMAGE:
                return {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': 'image/png',
                        'data': block.content,
                    },
                }
            else:
                meta = f'{block.meta}\n' if block.meta else ''
                return {'type': 'text', 'text': meta + block.content}

        # Convert all blocks from all elements to LLM blocks
        return [
            convert(block) for element in self.ui_elements for block in element.blocks
        ]
