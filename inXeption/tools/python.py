'''
Python tool implementation for executing Python code with state persistence.
'''

import asyncio
import logging

from pexpect import exceptions, replwrap

from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType

from .base import BaseTool, ToolError
from .ToolResult import ToolResult

# Initialize logger for this module
logger = logging.getLogger(__name__)

PYTHON_DEFAULT_TIMEOUT_S = 60


class _PythonSession:
    '''Internal session for running Python code with proper lifecycle management using REPLWrapper.'''

    command = 'python -u'  # Python with unbuffered output
    original_prompt = '>>> '  # Default Python prompt

    # Custom unique prompts that help REPLWrapper reliably detect when commands complete
    custom_prompt = '[PEXPECT_PROMPT>'
    custom_continuation_prompt = '[PEXPECT_PROMPT+'

    # Command to change Python's prompts to our custom ones
    prompt_change_cmd = (
        f"import sys; sys.ps1='{custom_prompt}'; sys.ps2='{custom_continuation_prompt}'"
    )

    def __init__(self, timeout_s=30.0):
        self._started = False
        self._timed_out = False
        self._timeout = timeout_s
        self._repl = None
        logger.debug(
            f'PythonSession initialized with timeout of {self._timeout} seconds'
        )

    async def start(self):
        if self._started:
            return

        logger.debug('Starting Python session with REPLWrapper')
        try:
            # Start Python interpreter with REPLWrapper for better prompt handling
            self._repl = replwrap.REPLWrapper(
                self.command, self.original_prompt, self.prompt_change_cmd
            )

            # Set child's interrupt method for later use
            self._child = self._repl.child

            self._started = True
            logger.debug('PythonSession started successfully')
        except Exception as e:
            logger.error(f'Error starting Python session: {e}')
            raise ToolError(f'Failed to start Python session: {str(e)}') from e

    async def stop(self):
        if not self._started or self._repl is None:
            return

        logger.debug('Stopping Python session')
        try:
            # Send exit to Python interpreter
            self._repl.run_command('exit()', timeout=2.0)
        except exceptions.EOF:
            # This is expected when the Python process exits normally
            logger.debug('Python process exited cleanly (EOF expected)')
        except Exception as e:
            logger.error(f'Error during clean exit: {e}')

        try:
            # Ensure process is terminated
            if hasattr(self._repl, 'child') and self._repl.child.isalive():
                logger.debug('Python still alive, terminating')
                self._repl.child.terminate(force=True)
        except Exception as e:
            logger.error(f'Error terminating Python session: {e}')

        self._started = False
        self._repl = None
        self._child = None
        logger.debug('PythonSession stopped')

    async def execute(self, code, tool_id, interrupt_check=None, timeout_s=None):
        if not self._started:
            logger.debug('Session not started, starting it now')
            await self.start()

        # Use specified timeout or instance timeout
        timeout = timeout_s if timeout_s is not None else self._timeout
        timeout_msg = f'⌛️ Code execution timed out after {timeout}s'

        # Prepare code for execution
        logger.debug(f'Preparing to execute code of length {len(code)}')

        # Wrap all nonempty code lines in "if True:" block with proper indentation
        # NOTE:
        #   We need this ugly hack as blank lines break it, and even with no blank lines it still falls over sometimes. Dunno if the \r\n buys anything.
        lines = ['if True:'] + [
            '    ' + line for line in code.splitlines() if line.strip()
        ]
        code = '\r\n'.join(lines) + '\n'

        # Initialize containers
        output = ''
        self._timed_out = False
        exit_code = 0

        # Create async task for interrupt checking
        interrupt_task = None
        if interrupt_check:
            interrupt_task = asyncio.create_task(self._check_interrupt(interrupt_check))

        try:
            # Execute code using REPLWrapper's run_command method
            # This automatically handles multiline code and prompt detection
            logger.debug('Running code with REPLWrapper')
            output = self._repl.run_command(code, timeout=timeout)
            logger.debug(f'Received output of length {len(output)}')

        except exceptions.TIMEOUT:
            # Timeout occurred
            logger.warning(f'Execution timed out after {timeout}s')
            self._timed_out = True
            exit_code = 1

        except Exception as e:
            # Other errors
            logger.error(f'Error during Python execution: {e}')
            output = str(e)
            exit_code = 1

        finally:
            # Cancel the interrupt task if it exists
            if interrupt_task:
                interrupt_task.cancel()
                try:
                    await interrupt_task
                except asyncio.CancelledError:
                    pass

        # Prepare result blocks
        blocks = []

        # Add output block if present
        if output.strip():
            blocks.append(
                UIBlock(
                    type=UIBlockType.CODE,
                    content=output.strip(),
                    meta='output',
                )
            )

        # Add timeout warning if execution timed out
        if self._timed_out:
            blocks.append(
                UIBlock(
                    type=UIBlockType.WARNING,
                    content=timeout_msg,
                    meta='status',
                )
            )

        # Add exit code block if non-zero
        if exit_code != 0:
            blocks.append(
                UIBlock(
                    type=UIBlockType.INFO,
                    content=f'Exit code: {exit_code}',
                    meta='exit_code',
                )
            )

        # Return a ToolResult instance with the UI element
        return ToolResult.from_ui_element('🐍', 'tool', blocks)

    async def _check_interrupt(self, interrupt_check):
        '''Monitor for interruption requests.'''
        while True:
            if interrupt_check():
                logger.warning('Python execution interrupt requested')
                # Send keyboard interrupt to the child process
                if hasattr(self, '_child') and self._child:
                    self._child.sendintr()
                return
            await asyncio.sleep(0.1)


class PythonTool(BaseTool):
    '''
    Tool for executing Python code with state persistence, timeout and interruption support.
    '''

    # Class variable for instance tracking
    _instance = None

    yaml = '''
        name: python_tool
        description: |
            Execute Python code with state persistence and host application introspection capabilities

            ## Implementation Details
            * The tool runs Python code in a separate process for stability and isolation
            * Code runs in an interactive Python interpreter that maintains state between calls
            * Variables, functions, and classes defined in one call persist in subsequent calls
            * Standard output and errors are captured and returned

            ## Key Capabilities
            * Access to the full Python standard library
            * State persistence between calls (variables and functions remain defined)
            * Timeout control and proper resource management
            * Process isolation for improved stability

            ## Usage Considerations
            * You can leverage Python's standard libraries for various tasks
            * Execution is controlled with timeouts and can be interrupted by the user
            * Use restart=True to reset the Python environment if needed
        input_schema:
            type: object
            properties:
                code:
                    description: |
                        The Python code to execute. Required unless restart=True is specified.
                        Can include introspection code using Python's standard libraries.
                    type: string
                restart:
                    description: |
                        Specify true to restart the Python interpreter (clearing all variables).
                        Use this if previous code has caused issues or you want a clean environment.
                    type: boolean
                timeout_s:
                    description: |
                        Specify this if your code may take longer than the default timeout.
                        Only use this for legitimately long-running operations, not to work around code that hangs.
                    type: integer
            required: ['code']
    '''

    def __init__(self):
        super().__init__()
        self._session = None

        # Store this instance as the class instance for future lookups
        PythonTool._instance = self

        # Initialize startup code to add host directory to sys.path
        self._startup_code = '''
# Add host directory to Python path for easier imports
import sys
if '/host' not in sys.path:
    sys.path.insert(0, '/host')
'''

    async def __call__(
        self,
        *,
        tool_id,
        code=None,
        restart=False,
        timeout_s=None,
        interrupt_check=None,
        **kwargs,
    ):
        '''Execute Python code and return a ToolResult.'''
        if timeout_s is None:
            timeout_s = PYTHON_DEFAULT_TIMEOUT_S

        # Handle restart request
        if restart:
            logger.info('Restarting Python session')
            await self.cleanup()
            self._session = None

            info_block = UIBlock(
                type=UIBlockType.INFO, content='Python session has been restarted'
            )
            return ToolResult.from_ui_element('🐍', UIChatType.TOOL, info_block)

        # Validate code parameter
        if not code:
            raise ToolError('The code parameter is required')

        # Create session if it doesn't exist
        if not self._session:
            logger.info('Creating new Python session')
            self._session = _PythonSession()

            # Execute startup code to add host to Python path
            await self._session.execute(
                self._startup_code, tool_id=tool_id, timeout_s=timeout_s
            )

        # Execute code in the session
        try:
            return await self._session.execute(
                code,
                tool_id=tool_id,
                interrupt_check=interrupt_check,
                timeout_s=timeout_s,
            )
        except Exception as e:
            # Propagate the error to be handled by collection.py
            raise ToolError(f'Error executing Python code: {str(e)}') from e

    async def cleanup(self):
        '''Clean up the Python session'''
        if self._session:
            logger.info('Cleaning up Python session')
            await self._session.stop()
            self._session = None
