'''
Editor tool implementation for viewing, creating and editing files.
'''

from collections import defaultdict
from pathlib import Path

from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType

from .base import BaseTool, ToolError
from .run import maybe_truncate, run
from .ToolResult import ToolResult

# Constants
Command = [
    'view',
    'create',
    'str_replace',
    'insert',
    'undo_edit',
]
SNIPPET_LINES = 4


class EditTool(BaseTool):
    '''
    A filesystem editor tool that allows the agent to view, create, and edit files.
    '''

    # File history for undo operations
    _file_history = None

    # YAML definition for this tool
    yaml = '''
        name: edit_tool
        description: |
          Custom editing tool for viewing, creating and editing files
          * State is persistent across turns in an interaction
          * If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
          * The `create` command cannot be used if the specified `path` already exists as a file
          * If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
          * The `undo_edit` command will revert the last edit made to the file at `path`

          Notes for using the `str_replace` command:
          * The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
          * If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
          * The `new_str` parameter should contain the edited lines that should replace the `old_str`
        input_schema:
          type: object
          properties:
            command:
              description: |
                The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.
              enum:
                - view
                - create
                - str_replace
                - insert
                - undo_edit
              type: string
            file_text:
              description: |
                Required parameter of `create` command, with the content of the file to be created.
              type: string
            insert_line:
              description: |
                Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.
              type: integer
            new_str:
              description: |
                Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.
              type: string
            old_str:
              description: |
                Required parameter of `str_replace` command containing the string in `path` to replace.
              type: string
            path:
              description: |
                Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.
              type: string
            view_range:
              description: |
                Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.
              items:
                type: integer
              type: array
          required: ['command', 'path']
    '''

    def __init__(self):
        self._file_history = defaultdict(list)
        super().__init__()

    async def __call__(
        self,
        *,
        tool_id,
        command,
        path,
        file_text=None,
        view_range=None,
        old_str=None,
        new_str=None,
        insert_line=None,
        **kwargs,
    ):
        '''Execute the edit tool commands and return a ToolResult'''
        _path = Path(path)
        self.validate_path(command, _path)

        if command == 'view':
            return await self.view(tool_id, _path, view_range)

        elif command == 'create':
            if file_text is None:
                raise ToolError('Parameter `file_text` is required for command: create')
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)

            return ToolResult.from_ui_element(
                '🌱',
                UIChatType.TOOL,
                [
                    UIBlock(
                        type=UIBlockType.TEXT,
                        content=f'File created successfully at: {_path}',
                    ),
                    UIBlock(type=UIBlockType.CODE, content=file_text),
                ],
            )

        elif command == 'str_replace':
            if old_str is None:
                raise ToolError(
                    'Parameter `old_str` is required for command: str_replace'
                )
            return self.str_replace(tool_id, _path, old_str, new_str)

        elif command == 'insert':
            if insert_line is None:
                raise ToolError(
                    'Parameter `insert_line` is required for command: insert'
                )
            if new_str is None:
                raise ToolError('Parameter `new_str` is required for command: insert')
            return self.insert(tool_id, _path, insert_line, new_str)

        elif command == 'undo_edit':
            return self.undo_edit(tool_id, _path)

        else:
            # Create error UI element
            error_message = f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(Command)}'

            return ToolResult.from_ui_element(
                '⛔️',
                UIChatType.TOOL,
                [UIBlock(type=UIBlockType.ERROR, content=error_message)],
            )

    def validate_path(self, command, path):
        '''Validate the provided path for the requested command.'''

        # Check if it's an absolute path
        if not path.is_absolute():
            suggested_path = Path('') / path
            raise ToolError(
                f'The path {path} is not an absolute path, it should start with `/`. Maybe you meant {suggested_path}?'
            )
        # Check if path exists
        if not path.exists() and command != 'create':
            raise ToolError(
                f'The path {path} does not exist. Please provide a valid path.'
            )
        if path.exists() and command == 'create':
            raise ToolError(
                f'File already exists at: {path}. Cannot overwrite files using command `create`.'
            )
        # Check if the path points to a directory
        if path.is_dir():
            if command != 'view':
                raise ToolError(
                    f'The path {path} is a directory and only the `view` command can be used on directories'
                )

    async def view(self, tool_id, path, view_range=None):
        '''View a file or directory contents.'''
        if path.is_dir():
            if view_range:
                raise ToolError(
                    'The `view_range` parameter is not allowed when `path` points to a directory.'
                )

            result = await run(rf'find {path} -maxdepth 2 -not -path "*/\.*"')
            stdout = result['stdout']
            stderr = result['stderr']

            blocks = [
                UIBlock(
                    type=UIBlockType.TEXT,
                    content=f'Here are the files and directories up to 2 levels deep in {path}, excluding hidden items:',
                )
            ]

            # Add stdout block if present
            if stdout.strip():
                blocks.append(
                    UIBlock(
                        type=UIBlockType.CODE, content=stdout.strip(), meta='stdout'
                    )
                )

            # Add stderr block if present
            if stderr.strip():
                blocks.append(
                    UIBlock(
                        type=UIBlockType.ERROR, content=stderr.strip(), meta='stderr'
                    )
                )

            return ToolResult.from_ui_element(
                '👀',
                UIChatType.TOOL,
                blocks,
            )

        # Handle file view
        file_content = self.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    'Invalid `view_range`. It should be a list of two integers.'
                )
            file_lines = file_content.split('\n')
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its first element `{init_line}` should be within the range of lines of the file: {[1, n_lines_file]}'
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its second element `{final_line}` should be smaller than the number of lines in the file: `{n_lines_file}`'
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its second element `{final_line}` should be larger or equal than its first `{init_line}`'
                )

            if final_line == -1:
                file_content = '\n'.join(file_lines[init_line - 1 :])
            else:
                file_content = '\n'.join(file_lines[init_line - 1 : final_line])

        # Separate intro text from the file content
        intro_text = f'Here is the result of running `cat -n` on {str(path)}:'

        # Format file content with line numbers but without the intro text
        file_lines = '\n'.join(
            [
                f'{i + init_line:6}\t{line}'
                for i, line in enumerate(file_content.split('\n'))
            ]
        )

        # Create separate blocks for intro text and code content

        # Directly return ToolResult with multiple blocks
        return ToolResult.from_ui_element(
            '👀',
            UIChatType.TOOL,
            [
                UIBlock(type=UIBlockType.TEXT, content=intro_text),
                UIBlock(type=UIBlockType.CODE, content=file_lines),
            ],
        )

    def str_replace(self, tool_id, path, old_str, new_str):
        '''Replace text in a file.'''

        # Read the file content
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ''

        # Check if old_str is unique in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f'No replacement was performed, the value of `old_str` did not appear verbatim in {path}.'
            )
        elif occurrences > 1:
            file_content_lines = file_content.split('\n')
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f'No replacement was performed. Multiple occurrences of the value of `old_str` found in lines {lines}. Please ensure it is unique'
            )

        # Replace old_str with new_str
        new_file_content = file_content.replace(old_str, new_str)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the content to history
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section
        replacement_line = file_content.split(old_str)[0].count('\n')
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count('\n')
        snippet = '\n'.join(new_file_content.split('\n')[start_line : end_line + 1])

        # Prepare separate blocks for text explanation and code snippet
        intro_msg = f'The file {path} has been edited.'
        outro_msg = 'Review the changes and make sure they are as expected. Edit the file again if necessary.'

        return ToolResult.from_ui_element(
            '🪛',
            UIChatType.TOOL,
            [
                UIBlock(type=UIBlockType.TEXT, content=intro_msg),
            ]
            + self._make_output(snippet, f'a snippet of {path}', start_line + 1)
            + [
                UIBlock(type=UIBlockType.TEXT, content=outro_msg),
            ],
        )

    def insert(self, tool_id, path, insert_line, new_str):
        '''Insert text at a specific line in a file.'''

        file_text = self.read_file(path).expandtabs()
        new_str = new_str.expandtabs()
        file_text_lines = file_text.split('\n')
        n_lines_file = len(file_text_lines)

        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f'Invalid `insert_line` parameter: {insert_line}. It should be within the range of lines of the file: {[0, n_lines_file]}'
            )

        new_str_lines = new_str.split('\n')
        new_file_text_lines = (
            file_text_lines[:insert_line]
            + new_str_lines
            + file_text_lines[insert_line:]
        )
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + new_str_lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]
        )

        new_file_text = '\n'.join(new_file_text_lines)
        snippet = '\n'.join(snippet_lines)

        self.write_file(path, new_file_text)
        self._file_history[path].append(file_text)

        # Prepare separate blocks for text explanation and code snippet
        intro_msg = f'The file {path} has been edited.'
        outro_msg = 'Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary.'

        return ToolResult.from_ui_element(
            '✏️',
            UIChatType.TOOL,
            [
                UIBlock(type=UIBlockType.TEXT, content=intro_msg),
            ]
            + self._make_output(
                snippet,
                'a snippet of the edited file',
                max(1, insert_line - SNIPPET_LINES + 1),
            )
            + [
                UIBlock(type=UIBlockType.TEXT, content=outro_msg),
            ],
        )

    def undo_edit(self, tool_id, path):
        '''Undo the last edit to a file.'''

        if not self._file_history[path]:
            raise ToolError(f'No edit history found for {path}.')

        old_text = self._file_history[path].pop()
        self.write_file(path, old_text)

        # Prepare separate blocks for explanatory text and file content
        intro_msg = f'Last edit to {path} undone successfully.'

        return ToolResult.from_ui_element(
            '↩️',
            UIChatType.TOOL,
            [
                UIBlock(type=UIBlockType.TEXT, content=intro_msg),
            ]
            + self._make_output(old_text, str(path)),
        )

    def read_file(self, path):
        '''Read a file's content.'''
        try:
            return path.read_text()
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to read {path}') from None

    def write_file(self, path, file):
        '''Write content to a file.'''
        try:
            path.write_text(file)
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to write to {path}') from None

    def _make_output(
        self,
        file_content,
        file_descriptor,
        init_line=1,
        expand_tabs=True,
    ):
        '''Format file content with line numbers and return as UI blocks.'''
        file_content = maybe_truncate(file_content)
        if expand_tabs:
            file_content = file_content.expandtabs()

        formatted_content = '\n'.join(
            [
                f'{i + init_line:6}\t{line}'
                for i, line in enumerate(file_content.split('\n'))
            ]
        )

        return [
            UIBlock(
                type=UIBlockType.TEXT,
                content=f'Here is the result of running `cat -n` on {file_descriptor}:',
            ),
            UIBlock(type=UIBlockType.CODE, content=formatted_content),
        ]

    async def cleanup(self):
        '''Nothing to clean up for this tool.'''
