'''
Computer tool implementation for GUI interaction.
'''

import asyncio
import base64
import os
import shlex
from enum import StrEnum
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType

from .base import BaseTool, ToolError
from .run import run
from .ToolResult import ToolResult

# Constants for the computer tool
OUTPUT_DIR = '/tmp/outputs'
TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

# Actions supported by the computer tool, grouped by API version
Action_20241022 = [
    'key',
    'type',
    'mouse_move',
    'left_click',
    'left_click_drag',
    'right_click',
    'middle_click',
    'double_click',
    'screenshot',
    'cursor_position',
]

Action_20250124 = Action_20241022 + [
    'left_mouse_down',
    'left_mouse_up',
    'scroll',
    'hold_key',
    'wait',
    'triple_click',
]

ScrollDirection = ['up', 'down', 'left', 'right']

CLICK_BUTTONS = {
    'left_click': 1,
    'right_click': 3,
    'middle_click': 2,
    'double_click': '--repeat 2 --delay 10 1',
    'triple_click': '--repeat 3 --delay 10 1',
}


class Resolution:
    def __init__(self, width, height):
        self.width = width
        self.height = height


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS = {
    'XGA': Resolution(width=1024, height=768),  # 4:3
    'WXGA': Resolution(width=1280, height=800),  # 16:10
    'FWXGA': Resolution(width=1366, height=768),  # ~16:9
}


class ScalingSource(StrEnum):
    COMPUTER = 'computer'
    API = 'api'


class ComputerToolOptions:
    def __init__(self, display_height_px, display_width_px, display_number=None):
        self.display_height_px = display_height_px
        self.display_width_px = display_width_px
        self.display_number = display_number


def chunks(s, chunk_size):
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class BaseComputerTool:
    _screenshot_delay = 4.0  # Increased to 4.0 seconds as requested
    _scaling_enabled = True

    @property
    def options(self):
        width, height = self.scale_coordinates(
            ScalingSource.COMPUTER, self.width, self.height
        )
        return ComputerToolOptions(
            display_width_px=width,
            display_height_px=height,
            display_number=self.display_num,
        )

    def __init__(self):
        super().__init__()

        self.width = int(os.getenv('WIDTH') or 0)
        self.height = int(os.getenv('HEIGHT') or 0)
        assert self.width and self.height, 'WIDTH, HEIGHT must be set'
        if (display_num := os.getenv('DISPLAY_NUM')) is not None:
            self.display_num = int(display_num)
            self._display_prefix = f'DISPLAY=:{self.display_num} '
        else:
            self.display_num = None
            self._display_prefix = ''

        self.xdotool = f'{self._display_prefix}xdotool'

    async def __call__(
        self,
        *,
        tool_id,
        action,
        text=None,
        coordinate=None,
        **kwargs,
    ):
        try:
            if action in ('mouse_move', 'left_click_drag'):
                if coordinate is None:
                    raise ToolError(f'coordinate is required for {action}')
                if text is not None:
                    raise ToolError(f'text is not accepted for {action}')

                x, y = self.validate_and_get_coordinates(coordinate)

                if action == 'mouse_move':
                    command_parts = [self.xdotool, f'mousemove --sync {x} {y}']
                    result = await self.shell(' '.join(command_parts))
                    return self._create_result(result, tool_id)

                elif action == 'left_click_drag':
                    command_parts = [
                        self.xdotool,
                        f'mousedown 1 mousemove --sync {x} {y} mouseup 1',
                    ]
                    result = await self.shell(' '.join(command_parts))
                    return self._create_result(result, tool_id)

            if action in ('key', 'type'):
                if text is None:
                    raise ToolError(f'text is required for {action}')
                if coordinate is not None:
                    raise ToolError(f'coordinate is not accepted for {action}')
                if not isinstance(text, str):
                    raise ToolError(f'{text} must be a string')

                if action == 'key':
                    command_parts = [self.xdotool, f'key -- {text}']
                    result = await self.shell(' '.join(command_parts))

                    # Create keyboard-specific result
                    description = f'Pressed key: {text}'
                    content = description
                    if result['stdout'] or result['stderr']:
                        output_text = f'{description}\n'
                        if result['stdout']:
                            output_text += f'STDOUT:\n{result["stdout"]}\n'
                        if result['stderr']:
                            output_text += f'STDERR:\n{result["stderr"]}'
                        content = output_text

                    # Create UI element for key action
                    blocks = [UIBlock(type=UIBlockType.TEXT, content=content)]

                    # Add screenshot if available
                    if result.get('screenshot_data'):
                        blocks.append(
                            UIBlock(
                                type=UIBlockType.IMAGE,
                                content=result['screenshot_data'],
                            )
                        )

                    return ToolResult.from_ui_element('📷', UIChatType.TOOL, blocks)

                elif action == 'type':
                    for chunk in chunks(text, TYPING_GROUP_SIZE):
                        command_parts = [
                            self.xdotool,
                            f'type --delay {TYPING_DELAY_MS} -- {shlex.quote(chunk)}',
                        ]
                        # Just execute the command, don't need the output
                        await self.shell(' '.join(command_parts), take_screenshot=False)

                    # Get screenshot
                    screenshot_result = await self.shell(
                        'echo ""', take_screenshot=True
                    )

                    blocks = [
                        UIBlock(type=UIBlockType.TEXT, content=f'Typed text: {text}')
                    ]

                    # Add screenshot if available
                    if screenshot_result.get('screenshot_data'):
                        blocks.append(
                            UIBlock(
                                type=UIBlockType.IMAGE,
                                content=screenshot_result['screenshot_data'],
                            )
                        )

                    return ToolResult.from_ui_element('📷', UIChatType.TOOL, blocks)

            if action in (
                'left_click',
                'right_click',
                'double_click',
                'middle_click',
                'screenshot',
                'cursor_position',
            ):
                if (
                    text is not None and action != 'left_click'
                ):  # left_click can have text for key combo
                    raise ToolError(f'text is not accepted for {action}')

                if action == 'screenshot':
                    return await self.screenshot(tool_id)

                elif action == 'cursor_position':
                    command_parts = [self.xdotool, 'getmouselocation --shell']
                    result = await self.shell(
                        ' '.join(command_parts),
                        take_screenshot=False,
                    )
                    # Get the output directly
                    output = result['stdout']

                    try:
                        # Use regex to reliably extract coordinates
                        import re

                        x_match = re.search(r'X=(\d+)', output)
                        y_match = re.search(r'Y=(\d+)', output)

                        if not x_match or not y_match:
                            # Create error UI element
                            error_block = UIBlock(
                                type=UIBlockType.ERROR,
                                content=f'Failed to parse cursor position from output: {output}',
                            )
                            return ToolResult.from_ui_element(
                                '⛔️', UIChatType.TOOL, error_block
                            )

                        x = int(x_match.group(1))
                        y = int(y_match.group(1))

                        # Scale the coordinates
                        x, y = self.scale_coordinates(ScalingSource.COMPUTER, x, y)

                        text_block = UIBlock(
                            type=UIBlockType.TEXT,
                            content=f'Cursor position: X={x},Y={y}',
                        )
                        return ToolResult.from_ui_element(
                            '📷', UIChatType.TOOL, text_block
                        )

                    except Exception as e:
                        error_block = UIBlock(
                            type=UIBlockType.ERROR,
                            content=f'Error getting cursor position: {str(e)}\nRaw output: {output}',
                        )
                        return ToolResult.from_ui_element(
                            '⛔️', UIChatType.TOOL, error_block
                        )
                else:
                    # For clicks, optionally include keypresses
                    mouse_move_part = ''
                    if coordinate is not None:
                        x, y = self.validate_and_get_coordinates(coordinate)
                        mouse_move_part = f'mousemove --sync {x} {y}'

                    command_parts = [self.xdotool, mouse_move_part]
                    if text:
                        command_parts.append(f'keydown {text}')
                    command_parts.append(f'click {CLICK_BUTTONS[action]}')
                    if text:
                        command_parts.append(f'keyup {text}')

                    result = await self.shell(' '.join(command_parts))
                    return self._create_result(
                        result, tool_id, action=action, coordinate=coordinate
                    )

            # Handle new operations added in 2025
            if action in ('left_mouse_down', 'left_mouse_up'):
                if coordinate is not None:
                    raise ToolError(f'coordinate is not accepted for {action=}.')
                command_parts = [
                    self.xdotool,
                    f'{"mousedown" if action == "left_mouse_down" else "mouseup"} 1',
                ]
                result = await self.shell(' '.join(command_parts))
                return self._create_result(result, tool_id, action=action)

            elif action == 'scroll':
                if scroll_direction := kwargs.get('scroll_direction'):
                    if scroll_direction not in ScrollDirection:
                        raise ToolError(
                            f'scroll_direction={scroll_direction} must be "up", "down", "left", or "right"'
                        )
                else:
                    raise ToolError('scroll_direction is required for scroll action')

                scroll_amount = kwargs.get('scroll_amount')
                if not isinstance(scroll_amount, int) or scroll_amount < 0:
                    raise ToolError(
                        f'scroll_amount={scroll_amount} must be a non-negative int'
                    )

                mouse_move_part = ''
                if coordinate is not None:
                    x, y = self.validate_and_get_coordinates(coordinate)
                    mouse_move_part = f'mousemove --sync {x} {y}'

                scroll_button = {
                    'up': 4,
                    'down': 5,
                    'left': 6,
                    'right': 7,
                }[scroll_direction]

                command_parts = [self.xdotool, mouse_move_part]
                if text:
                    command_parts.append(f'keydown {text}')
                command_parts.append(f'click --repeat {scroll_amount} {scroll_button}')
                if text:
                    command_parts.append(f'keyup {text}')

                result = await self.shell(' '.join(command_parts))
                return self._create_result(
                    result,
                    tool_id,
                    action='scroll',
                    meta={'direction': scroll_direction, 'amount': scroll_amount},
                )

            elif action in ('hold_key', 'wait'):
                duration = kwargs.get('duration')
                if duration is None or not isinstance(duration, (int, float)):
                    raise ToolError('duration must be a number')
                if duration < 0:
                    raise ToolError('duration must be non-negative')
                if duration > 100:
                    raise ToolError('duration is too long')

                if action == 'hold_key':
                    if text is None:
                        raise ToolError(f'text is required for {action}')
                    escaped_keys = shlex.quote(text)
                    command_parts = [
                        self.xdotool,
                        f'keydown {escaped_keys}',
                        f'sleep {duration}',
                        f'keyup {escaped_keys}',
                    ]
                    result = await self.shell(' '.join(command_parts))
                    return self._create_result(
                        result,
                        tool_id,
                        action='hold_key',
                        meta={'key': text, 'duration': duration},
                    )

                if action == 'wait':
                    await asyncio.sleep(duration)
                    # Take a screenshot after waiting
                    return await self.screenshot(
                        tool_id, description=f'Waited for {duration} seconds'
                    )

            elif action == 'triple_click':
                if coordinate is None:
                    raise ToolError(f'coordinate is required for {action}')

                x, y = self.validate_and_get_coordinates(coordinate)
                command_parts = [
                    self.xdotool,
                    f'mousemove --sync {x} {y} click --repeat 3 --delay 10 1',
                ]

                result = await self.shell(' '.join(command_parts))
                return self._create_result(
                    result, tool_id, action='triple_click', coordinate=coordinate
                )

            # If we get here, the action is not supported
            raise ToolError(f'Invalid action: {action}')

        except ToolError as e:
            error_block = UIBlock(type=UIBlockType.ERROR, content=str(e))
            return ToolResult.from_ui_element('⛔️', UIChatType.TOOL, error_block)

        except Exception as e:
            # Handle unexpected errors with traceback
            import traceback

            error_trace = traceback.format_exc()

            error_blocks = [
                UIBlock(type=UIBlockType.ERROR, content=f'Error: {str(e)}'),
                UIBlock(type=UIBlockType.CODE, content=error_trace),
            ]
            return ToolResult.from_ui_element('⛔️', UIChatType.TOOL, error_blocks)

    def validate_and_get_coordinates(self, coordinate=None):
        if not isinstance(coordinate, list) or len(coordinate) != 2:
            raise ToolError(f'{coordinate} must be a tuple of length 2')
        if not all(isinstance(i, int) and i >= 0 for i in coordinate):
            raise ToolError(f'{coordinate} must be a tuple of non-negative ints')

        return self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])

    async def screenshot(self, tool_id, description='Screenshot taken'):
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f'screenshot_{uuid4().hex}.png'

        # Use scrot with bell character filtering
        screenshot_cmd = f'{self._display_prefix}scrot -p -z {path} 2>/dev/null'
        await self.shell(screenshot_cmd, take_screenshot=False)
        if self._scaling_enabled:
            x, y = self.scale_coordinates(
                ScalingSource.COMPUTER, self.width, self.height
            )
            await self.shell(
                f'convert {path} -resize {x}x{y}! {path}', take_screenshot=False
            )

        if path.exists():
            # Create an image block with the screenshot
            base64_data = base64.b64encode(path.read_bytes()).decode()

            # Play camera sound
            from inXeption.utils.misc import play_sound

            play_sound('camera-shutter.mp3')

            blocks = [
                UIBlock(type=UIBlockType.TEXT, content=description),
                UIBlock(type=UIBlockType.IMAGE, content=base64_data),
            ]
            return ToolResult.from_ui_element('📷', UIChatType.TOOL, blocks)

        error_block = UIBlock(
            type=UIBlockType.ERROR, content='Failed to take screenshot: unknown error'
        )
        return ToolResult.from_ui_element('⛔️', UIChatType.TOOL, error_block)

    async def shell(self, command, take_screenshot=True):
        result = await run(command)
        stdout = result['stdout']
        stderr = result['stderr']

        # Prepare result dictionary
        shell_result = {
            'command': command,
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': result['exit_code'],
            'screenshot_data': None,
        }

        if take_screenshot:
            # delay to let things settle before taking a screenshot
            await asyncio.sleep(self._screenshot_delay)
            # Get screenshot data
            try:
                # Direct screenshot capture
                output_dir = Path(OUTPUT_DIR)
                output_dir.mkdir(parents=True, exist_ok=True)
                path = output_dir / f'screenshot_{uuid4().hex}.png'

                screenshot_cmd = f'{self._display_prefix}scrot -p -z {path} 2>/dev/null'
                await run(screenshot_cmd)

                if self._scaling_enabled:
                    x, y = self.scale_coordinates(
                        ScalingSource.COMPUTER, self.width, self.height
                    )
                    await run(f'convert {path} -resize {x}x{y}! {path}')

                if path.exists():
                    shell_result['screenshot_data'] = base64.b64encode(
                        path.read_bytes()
                    ).decode()
            except Exception as e:
                shell_result['screenshot_error'] = str(e)

        return shell_result

    def _create_result(self, result, tool_id, action=None, coordinate=None, meta=None):
        '''Create a standardized ToolResult for computer actions.'''
        # Build the content description
        content = f'Action: {action}' if action else 'Command executed'

        # Create result with UIBlocks

        blocks = []

        # Add main content block
        if result['stdout'] or result['stderr']:
            # If we have command output, include it in the content
            detail = f'{content}\n'
            if result['stdout']:
                detail += f"STDOUT:\n{result['stdout']}\n"
            if result['stderr']:
                detail += f"STDERR:\n{result['stderr']}"
            blocks.append(UIBlock(type=UIBlockType.CODE, content=detail))
        else:
            # Just the basic content
            blocks.append(UIBlock(type=UIBlockType.TEXT, content=content))

        # Add screenshot if available
        if result.get('screenshot_data'):
            blocks.append(
                UIBlock(type=UIBlockType.IMAGE, content=result.get('screenshot_data'))
            )

        # Return ToolResult with the UI element
        return ToolResult.from_ui_element('📷', UIChatType.TOOL, blocks)

    def scale_coordinates(self, source, x, y):
        if not self._scaling_enabled:
            return x, y
        ratio = self.width / self.height
        target_dimension = None
        for dimension in MAX_SCALING_TARGETS.values():
            # allow some error in the aspect ratio - not ratios are exactly 16:9
            if abs(dimension.width / dimension.height - ratio) < 0.02:
                if dimension.width < self.width:
                    target_dimension = dimension
                break
        if target_dimension is None:
            return x, y
        # should be less than 1
        x_scaling_factor = target_dimension.width / self.width
        y_scaling_factor = target_dimension.height / self.height
        if source == ScalingSource.API:
            if x > self.width or y > self.height:
                raise ToolError(f'Coordinates {x}, {y} are out of bounds')
            # scale up
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        # scale down
        return round(x * x_scaling_factor), round(y * y_scaling_factor)


class ComputerTool(BaseComputerTool, BaseTool):
    '''Tool for interacting with the computer GUI.'''

    # YAML definition for this tool
    yaml = dedent('''\
        name: computer_tool
        description: |
          Use a mouse and keyboard to interact with a computer, and take screenshots.
          * This is an interface to a desktop GUI. You do not have direct access to a terminal (you may have access to a terminal application) or applications menu. You must click on desktop icons to start applications.
          * Some applications may take time to start or process actions, so you may need to wait to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try waiting before taking another screenshot.
          * The screen's resolution is 1024x768.
          * The display number is 1

          * You should ONLY call mouse_move if you intend to hover over an element without clicking. Otherwise, use the click or drag functions directly.
          * Whenever you intend to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
          * If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your click location so that the tip of the cursor visually falls on the element that you want to click.
          * Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.
        input_schema:
          type: object
          properties:
            action:
              description: |
                The action to perform. The available actions are:
                * `key`: Press a key or key-combination on the keyboard.
                  - This supports xdotool's `key` syntax.
                  - Examples: 'a', 'Return', 'alt+Tab', 'ctrl+s', 'Up', 'KP_0' (for the numpad 0 key).
                * `hold_key`: Hold down a key or multiple keys for a specified duration (in seconds). Supports the same syntax as `key`.
                * `type`: Type a string of text on the keyboard.
                * `cursor_position`: Get the current (x, y) pixel coordinate of the cursor on the screen.
                * `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
                * `left_mouse_down`: Press the left mouse button.
                * `left_mouse_up`: Release the left mouse button.
                * `left_click`: Click the left mouse button at the specified (x, y) pixel coordinate on the screen. You can also include a key combination to hold down while clicking using the `text` parameter.
                * `left_click_drag`: Click and drag the cursor from `start_coordinate` to a specified (x, y) pixel coordinate on the screen.
                * `right_click`: Click the right mouse button at the specified (x, y) pixel coordinate on the screen.
                * `middle_click`: Click the middle mouse button at the specified (x, y) pixel coordinate on the screen.
                * `double_click`: Double-click the left mouse button at the specified (x, y) pixel coordinate on the screen.
                * `triple_click`: Triple-click the left mouse button at the specified (x, y) pixel coordinate on the screen.
                * `scroll`: Scroll the screen in a specified direction by a specified amount of clicks of the scroll wheel, at the specified (x, y) pixel coordinate. DO NOT use PageUp/PageDown to scroll.
                * `wait`: Wait for a specified duration (in seconds).
                * `screenshot`: Take a screenshot of the screen.
              enum: ['key', 'hold_key', 'type', 'cursor_position', 'mouse_move', 'left_mouse_down', 'left_mouse_up', 'left_click', 'left_click_drag', 'right_click', 'middle_click', 'double_click', 'triple_click', 'scroll', 'wait', 'screenshot']
              type: string
            coordinate:
              description: |
                (x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=mouse_move` and `action=left_click_drag`.
              type: array
            duration:
              description: |
                The duration to hold the key down for. Required only by `action=hold_key` and `action=wait`.
              type: integer
            scroll_amount:
              description: |
                The number of 'clicks' to scroll. Required only by `action=scroll`.
              type: integer
            scroll_direction:
              description: |
                The direction to scroll the screen. Required only by `action=scroll`.
              enum:
                - up
                - down
                - left
                - right
              type: string
            start_coordinate:
              description: |
                (x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to start the drag from. Required only by `action=left_click_drag`.
              type: array
            text:
              description: |
                Required only by `action=type`, `action=key`, and `action=hold_key`. Can also be used by click or scroll actions to hold down keys while clicking or scrolling.
              type: string
          required: ['action']
    ''')

    async def cleanup(self):
        '''Clean up resources.'''
