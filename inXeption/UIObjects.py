'''
Standardized UI element and block classes for consistent presentation.

This module provides formal representation of UI elements used throughout the system,
ensuring type safety, validation, and consistent rendering patterns.
'''

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class UIBlockType(str, Enum):
    '''Supported UI block types'''

    TEXT = 'text'
    CODE = 'code'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    IMAGE = 'image'
    MARKDOWN = 'markdown'


class UIChatType(str, Enum):
    '''Types of chat entities'''

    USER = 'user'
    ASSISTANT = 'assistant'
    TOOL = 'tool'
    SYSTEM = 'system'


class UIBlock(BaseModel):
    '''A UI block representing a single content element'''

    type: UIBlockType
    content: str
    meta: Optional[Union[str, Dict[str, Any]]] = None


class UIElement(BaseModel):
    '''A UI element representing a message or tool result'''

    avatar: str
    chat_type: UIChatType
    blocks: List[UIBlock]
    meta: Optional[Dict[str, Any]] = None

    @classmethod
    def singleblock(
        cls, avatar: str, chat_type: UIChatType, block_type: UIBlockType, content: str
    ) -> 'UIElement':
        '''Create a UI element with a single block'''
        return cls(
            avatar=avatar,
            chat_type=chat_type,
            blocks=[UIBlock(type=block_type, content=content)],
        )

    def render(self, render_fn):
        '''Render this UI element using the provided render function'''
        render_fn(self.model_dump())
