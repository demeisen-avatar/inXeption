'''
Bash tool implementation for executing shell commands.
'''

import asyncio
import logging
import os
import signal

from inXeption.UIObjects import UIBlock, UIBlockType, UIChatType

from .base import BaseTool, ToolError
from .ToolResult import ToolResult

# Initialize logger for this module
logger = logging.getLogger(__name__)

BASH_DEFAULT_TIMEOUT_S = 60


class _BashSession:
    '''Internal session for running bash commands with proper lifecycle management.'''

    command = '/bin/bash'
    _output_delay = 0.2  # seconds

    # We split this up so that if the agent-ware examines its own code using its bash-tool we won't fall over
    _sentinel = '<<' + 'exit' + '>>'

    def __init__(self, timeout_s=30.0):
        self._started = False
        self._timed_out = False
        self._timeout = timeout_s
        logger.debug(f'BashSession initialized with timeout of {self._timeout} seconds')

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    async def stop(self):
        if not self._started:
            return

        try:
            pgid = os.getpgid(self._process.pid)
            os.killpg(pgid, signal.SIGINT)
            await asyncio.sleep(0.1)
            if self._process.returncode is None:
                os.killpg(pgid, signal.SIGTERM)
                await asyncio.sleep(0.1)
                if self._process.returncode is None:
                    os.killpg(pgid, signal.SIGKILL)
                    await self._process.wait()
        except (ProcessLookupError, PermissionError) as e:
            logger.debug(f'Process might already be gone: {e}')
        except Exception as e:
            logger.error(f'Error stopping bash session: {e}')

        logger.debug('BashSession stopped')

        self._started = False

    async def execute(self, command, tool_id, interrupt_check=None, timeout_s=None):
        if not self._started:
            await self.start()

        # Clear any previous output
        self._process.stdout._buffer.clear()
        self._process.stderr._buffer.clear()

        # Send command to bash with exit sentinel
        full_command = f'{command}; echo "{self._sentinel}$?"\n'
        self._process.stdin.write(full_command.encode())
        await self._process.stdin.drain()

        # Initialize raw byte buffers
        stdout_bytes = bytearray()
        stderr_bytes = bytearray()
        self._timed_out = False

        # Use specified timeout or instance timeout
        timeout = timeout_s if timeout_s is not None else self._timeout
        timeout_msg = f'⌛️ Command timed out after {timeout}s'

        # Start timeout clock
        start_time = asyncio.get_event_loop().time()

        # Read output until sentinel or timeout
        while True:
            # Check for timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self._timed_out = True
                logger.warning(f'Command timed out after {elapsed:.1f}s: {command}')
                break

            # Check for interrupt if provided
            if interrupt_check and interrupt_check():
                logger.warning('Command interrupted by interrupt_check')
                break

            # Read from stdout (non-blocking)
            try:
                data = await asyncio.wait_for(
                    self._process.stdout.read(1024), timeout=self._output_delay
                )
                if data:
                    stdout_bytes.extend(data)
                    # Check for sentinel in raw bytes
                    sentinel_pos = stdout_bytes.find(self._sentinel.encode('utf-8'))
                    if sentinel_pos != -1:
                        # Extract exit code from bytes after sentinel
                        exit_code_bytes = stdout_bytes[
                            sentinel_pos + len(self._sentinel.encode('utf-8')) :
                        ]
                        try:
                            # Safely decode the exit code portion
                            exit_code_str = exit_code_bytes.decode(
                                'utf-8', errors='replace'
                            ).strip()
                            exit_code = int(exit_code_str)
                        except ValueError:
                            exit_code = -1
                            logger.error(
                                f'Failed to parse exit code: {exit_code_bytes!r}'
                            )

                        # Truncate stdout at sentinel position
                        stdout_bytes = stdout_bytes[:sentinel_pos]

                        # Collect any remaining stderr bytes
                        data = self._process.stderr._buffer
                        if data:
                            stderr_bytes.extend(data)

                        # Now safely decode the complete output buffers
                        try:
                            output = stdout_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            logger.warning(
                                'UTF-8 decode error in stdout, using replacement'
                            )
                            output = stdout_bytes.decode('utf-8', errors='replace')

                        try:
                            error = stderr_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            logger.warning(
                                'UTF-8 decode error in stderr, using replacement'
                            )
                            error = stderr_bytes.decode('utf-8', errors='replace')

                        blocks = []

                        # Add stdout block if present
                        if output.strip():
                            blocks.append(
                                UIBlock(
                                    type=UIBlockType.CODE,
                                    content=output.strip(),
                                    meta='stdout',
                                )
                            )

                        # Add stderr block if present
                        if error.strip():
                            blocks.append(
                                UIBlock(
                                    type=UIBlockType.ERROR,
                                    content=error.strip(),
                                    meta='stderr',
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

                        # Clear buffers
                        self._process.stdout._buffer.clear()
                        self._process.stderr._buffer.clear()

                        # Return a ToolResult instance with the UI element
                        return ToolResult.from_ui_element('📺', 'tool', blocks)

            except asyncio.TimeoutError:
                # This is normal, just means no data was available in the timeout
                pass

            # Read from stderr (non-blocking)
            try:
                data = await asyncio.wait_for(
                    self._process.stderr.read(1024), timeout=self._output_delay
                )
                if data:
                    stderr_bytes.extend(data)
            except asyncio.TimeoutError:
                # This is normal, just means no data was available in the timeout
                pass

        # Handle timeout or interrupt
        # Attempt to terminate the command gracefully
        if self._timed_out or (interrupt_check and interrupt_check()):
            was_interrupted = not self._timed_out
            logger.debug(
                f'Command {"interrupted" if was_interrupted else "timed out"}, cleaning up'
            )

            # Kill and clean up the process tree
            try:
                pgid = os.getpgid(self._process.pid)
                logger.debug(f'Terminating process group {pgid}')
                os.killpg(pgid, signal.SIGTERM)

                try:
                    await asyncio.wait_for(self._process.wait(), timeout=0.5)
                    logger.debug(f'Process exited with code {self._process.returncode}')
                except asyncio.TimeoutError:
                    # If they don't terminate in time, force kill
                    logger.debug(
                        f'Process did not exit in time, sending SIGKILL to group {pgid}'
                    )
                    os.killpg(pgid, signal.SIGKILL)
                    await self._process.wait()
                    logger.debug(
                        f'Process exited with code {self._process.returncode} after SIGKILL'
                    )
            except ProcessLookupError:
                # Process group might already be gone
                logger.debug(f'Process group {pgid} already gone')
            except Exception as e:
                logger.error(f'Error stopping timed-out bash session: {e}')

            logger.debug('Timeout cleanup completed')

            # Collect any remaining stdout bytes
            data = self._process.stdout._buffer
            if data:
                stdout_bytes.extend(data)

            # Collect any remaining stderr bytes
            data = self._process.stderr._buffer
            if data:
                stderr_bytes.extend(data)

            # Safely decode the complete output buffers
            try:
                output = stdout_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(
                    'UTF-8 decode error in stdout during timeout handling, using replacement'
                )
                output = stdout_bytes.decode('utf-8', errors='replace')

            try:
                error = stderr_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(
                    'UTF-8 decode error in stderr during timeout handling, using replacement'
                )
                error = stderr_bytes.decode('utf-8', errors='replace')

            # Trim trailing newlines
            if output.endswith('\n'):
                output = output[:-1]
            if error.endswith('\n'):
                error = error[:-1]

            blocks = []

            # Add stdout block if present
            if output.strip():
                blocks.append(
                    UIBlock(
                        type=UIBlockType.CODE, content=output.strip(), meta='stdout'
                    )
                )

            # Add stderr block if present
            if error.strip():
                blocks.append(
                    UIBlock(
                        type=UIBlockType.ERROR, content=error.strip(), meta='stderr'
                    )
                )

            # Add timeout or interrupt warning
            if self._timed_out:
                blocks.append(
                    UIBlock(
                        type=UIBlockType.WARNING, content=timeout_msg, meta='status'
                    )
                )
            else:
                blocks.append(
                    UIBlock(
                        type=UIBlockType.WARNING,
                        content='🛑 Command interrupted by user',
                        meta='status',
                    )
                )

            # Clear buffers
            self._process.stdout._buffer.clear()
            self._process.stderr._buffer.clear()

            # Mark session as not started so next command creates a fresh process
            self._started = False

            # Return a ToolResult instance with the UI element
            return ToolResult.from_ui_element('📺', 'tool', blocks)


class BashTool(BaseTool):
    '''
    Tool for executing bash commands with timeout and interruption support.
    '''

    # Class variable for instance tracking
    _instance = None

    yaml = f'''
        name: bash_tool
        description: |
          Run commands in a bash shell
          * When invoking this tool, the contents of the 'command' parameter does NOT need to be XML-escaped.
          * You have access to a mirror of common linux and python packages via apt and pip.
          * State is persistent across command calls and discussions with the user.
          * To inspect a particular line range of a file, e.g. lines 10-25, try 'sed -n 10,25p /path/to/the/file'.
          * Please avoid commands that may produce a very large amount of output.
          * Please run long lived commands in the background, e.g. 'sleep 10 &' or start a server in the background.
        input_schema:
          type: object
          properties:
            command:
              description: |
                The bash command to run. Required unless the tool is being restarted.
              type: string
            restart:
              description: |
                Specifying true will restart this tool. Otherwise, leave this unspecified.
              type: boolean
            timeout_s:
              description: |
                Specify this if you need to perform an operation that is likely to take longer than the default value of {BASH_DEFAULT_TIMEOUT_S}. Do NOT use it blindly if a prior tool-execution timed out. Instead consider whether the timeout was due to an actual need for more time (e.g. running a test, building a docker image, installing some system package) or whether there's some more fundamental problem with the execution itself (e.g. you invoked an interactive editor by mistake, or ran a command that will never terminate like launching a dev-server, or ran a test that should have completed quickly). i.e. don't consider it a 'get-out-of-jail' fix to negotiate a prior timeout, as that will just frustrate the human user
              type: integer
              default: {BASH_DEFAULT_TIMEOUT_S}
          required: ['command']
    '''

    def __init__(self):
        super().__init__()
        self._session = None

        # Store this instance as the class instance for future lookups
        BashTool._instance = self

    async def __call__(
        self,
        *,
        tool_id,
        command,
        restart=False,
        timeout_s=None,
        interrupt_check=None,
        **kwargs,
    ):
        '''Execute a bash command and return a ToolResult.'''
        if timeout_s is None:
            timeout_s = BASH_DEFAULT_TIMEOUT_S

        # Handle restart request
        if restart:
            logger.info('Restarting bash session')
            await self.cleanup()
            self._session = None

            info_block = UIBlock(
                type=UIBlockType.INFO, content='Bash session has been restarted'
            )
            return ToolResult.from_ui_element('📺', UIChatType.TOOL, info_block)

        # Create session if it doesn't exist
        if not self._session:
            logger.info('Creating new bash session')
            self._session = _BashSession()

        # Execute command in the session
        try:
            return await self._session.execute(
                command,
                tool_id=tool_id,
                interrupt_check=interrupt_check,
                timeout_s=timeout_s,
            )
        except Exception as e:
            # Propagate the error to be handled by collection.py
            raise ToolError(f'Error executing bash command: {str(e)}') from e

    async def cleanup(self):
        '''Clean up the bash session'''
        if self._session:
            logger.info('Cleaning up bash session')
            await self._session.stop()
            self._session = None
