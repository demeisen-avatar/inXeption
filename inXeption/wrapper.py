'''
💙1.0 STREAMLIT EXCEPTION HANDLING AND LOGGING

Streamlit has a fundamental limitation for AI-assisted development: when exceptions
occur in the target script, they're only visible in the browser UI with no log output.

This wrapper layer intercepts exceptions from app.py and logs them, making errors
visible to agents without browser access. This enables efficient development of app.py
and downstream components.

The wrapper also establishes logging that's used by all downstream components,
allowing test harnesses like loop_test.py to configure different logging while
maintaining the same architectural flow.
'''

import asyncio
import logging
import os
import sys
import threading
import traceback
from pathlib import Path

# Import streamlit - assume it's available since this is a Streamlit wrapper
import streamlit as st
from streamlit.runtime.app_session import AppSession
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import utility functions
from inXeption.utils.misc import create_or_replace_symlink, timestamp

# Initialize run counter in session state
if 'run_counter' not in st.session_state:
    st.session_state.run_counter = 1
else:
    st.session_state.run_counter += 1

# Setup LOG_DIR based on LOG_BASE
if 'LOG_DIR' not in st.session_state:
    # First run of a fresh session, setup LOG_DIR
    if 'LOG_BASE' not in os.environ:
        print('ERROR: LOG_BASE environment variable not set')  # noqa: T201
        sys.exit(1)

    log_base = os.environ['LOG_BASE']

    # Determine environment type from LOG_BASE path
    log_base_path = Path(log_base)
    if 'prod' in log_base_path.parts:
        env_type = 'prod'
    else:
        env_type = 'dev'

    # Construct LOG_DIR from LOG_BASE with timestamp
    log_dir_timestamp = timestamp()
    log_dir = os.path.join(log_base, log_dir_timestamp)
    os.makedirs(log_dir, exist_ok=True)

    # Export and save to session state
    os.environ['LOG_DIR'] = log_dir
    st.session_state.LOG_DIR = log_dir
    print(f'(wrapper.py) LOG_DIR={log_dir}')  # noqa: T201

    # Create the env-latest symlink
    symlink_name = f'{env_type}-latest'

    # Find the logs root directory by traversing up until we find ".logs"
    logs_root = log_base_path
    while logs_root.name != '.logs':
        logs_root = logs_root.parent
        if logs_root == logs_root.parent:  # Safety check to avoid infinite loop
            raise ValueError(f'Could not find .logs directory in path: {log_base}')

    # Create symlink in the .logs directory
    symlink_path = logs_root / symlink_name

    # Get relative path for symlink target (for portability)
    if env_type == 'prod':
        # For prod: .logs/prod/$container_id/$timestamp/
        container_id = log_base_path.name
        target = f'prod/{container_id}/{log_dir_timestamp}'
    else:
        # For dev: .logs/dev/$timestamp/
        target = f'dev/{log_dir_timestamp}'

    # Use our centralized utility function to create/replace the symlink
    create_or_replace_symlink(symlink_path=symlink_path, target_path=target)

# Set up logging configuration
LOG_FORMAT = '[%(asctime)s.%(msecs)03d] [Run-%(run_index)s] [%(filename)s:%(funcName)s:%(lineno)d] %(levelname)s: %(message)s'
DATE_FORMAT = '%M:%S'
LOG_LEVEL = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO'), logging.INFO)


# Custom formatter that handles missing run_index values
class RunIndexFormatter(logging.Formatter):
    def format(self, record):
        # Add run_index if not present - use '?' as default
        if not hasattr(record, 'run_index'):
            record.run_index = '?'
        return super().format(record)


# Set up file handler for logging
log_file = os.path.join(st.session_state.LOG_DIR, 'streamlit.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(RunIndexFormatter(LOG_FORMAT, DATE_FORMAT))

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(file_handler)

# Initialize logger for this module
logger = logging.getLogger('inXeption.wrapper')

# Log initial startup message with run counter from session state
logger.info(
    f'Wrapper starting - Run index: {st.session_state.run_counter}',
    extra={'run_index': st.session_state.run_counter},
)
logger.info(
    f'Wrapper running from {os.path.dirname(os.path.abspath(__file__))}',
    extra={'run_index': st.session_state.run_counter},
)


def monkeypatch():
    '''
    💙1.1 STREAMLIT STOP BUTTON MONKEY PATCHING
    Streamlit's default stop button behavior raises a StopException that abruptly terminates
    execution at unpredictable points, making controlled interruption impossible.

    We monkey patch AppSession._handle_stop_script_request to:
    1. Set a flag in st.session_state.stop_requested instead of raising an exception
    2. DELIBERATELY NOT call the original handler, preventing StopException
    3. Preserve script run context to ensure our custom handler works reliably

    This allows downstream components to check interrupt_check() at appropriate points
    and gracefully handle interruption, preserving state and providing user feedback.
    '''
    # Initialize stop_requested flag in session state at module level
    if 'stop_requested' not in st.session_state:
        st.session_state.stop_requested = False

    # Capture the script context at module level when script first loads
    SCRIPT_RUN_CTX = get_script_run_ctx()

    assert SCRIPT_RUN_CTX is not None

    # Store the original handler
    original_stop_handler = AppSession._handle_stop_script_request  # noqa: F841

    # Define our patched handler function
    def patched_stop_handler(self):
        # Use the already captured context from module level
        if SCRIPT_RUN_CTX is not None:
            add_script_run_ctx(threading.current_thread(), SCRIPT_RUN_CTX)
        else:
            logger.warning(
                'Cannot add script run context - SCRIPT_RUN_CTX is None',
                extra={'run_index': st.session_state.run_counter},
            )

        # Set our flag in session state
        st.session_state.stop_requested = True

        # Log that we detected the stop button press
        logger.warning(
            'Stop button pressed - setting stop_requested flag',
            extra={'run_index': st.session_state.run_counter},
        )

        # NOTE:
        #   DELIBERATELY NOT calling the original handler to eat the StopException.
        #   This prevents Streamlit from terminating our tool execution prematurely.
        #   We'll handle the tool interruption ourselves in the main loop.
        # return original_stop_handler(self)

    # Apply the monkey patch
    AppSession._handle_stop_script_request = patched_stop_handler
    logger.info(
        'Monkey patch applied for stop button detection',
        extra={'run_index': st.session_state.run_counter},
    )


monkeypatch()

# Display a banner in the UI with detailed container information
# Get current directory and determine if this is a development or production run
is_dev = __file__.startswith('/host/')
env_type = 'DEVELOPMENT' if is_dev else 'PRODUCTION'

# Import modules for container information display
import arrow
import docker
import yaml

try:
    # Connect to Docker socket
    client = docker.from_env()
    hostname = os.environ['HOSTNAME']

    # Find our container by hostname
    containers = client.containers.list()
    our_container = next(
        c for c in containers if c.attrs['Config']['Hostname'] == hostname
    )

    # Get container details
    container_info = our_container.attrs

    # Extract time information
    created = arrow.get(container_info['Created'])
    started = arrow.get(container_info['State']['StartedAt'])
    now = arrow.utcnow()

    # Calculate uptime/runtime
    uptime_delta = now - created
    runtime_delta = now - started

    # Format as readable strings
    def format_timedelta(td):
        return f'{td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m'

    uptime_str = format_timedelta(uptime_delta)
    runtime_str = format_timedelta(runtime_delta)

    # Extract network information
    network_info = {
        name: {'ip': net['IPAddress'], 'gateway': net['Gateway']}
        for name, net in container_info['NetworkSettings']['Networks'].items()
    }

    # Get environment variables from container config
    env_vars = {
        env.split('=')[0]: env.split('=')[1]
        for env in container_info['Config']['Env']
        if '=' in env
    }

    # Get session ID if available
    session_id_display = get_script_run_ctx().session_id[:6] + '...'  # noqa F821

    # Build container information structure
    container_details = {
        'container': {
            'id': our_container.id[:12],
            'name': our_container.name,
            'assigned_name': env_vars.get('CONTAINER_NAME', 'unknown'),
            'hostname': hostname,
            'lx_level': os.environ['LX'],
            'mode': env_type,
            'image': {
                'id': container_info['Image'][:12],
                'name': container_info['Config']['Image'],
            },
            'uptime': uptime_str,
            'runtime': runtime_str,
            'state': container_info['State']['Status'],
            'network': network_info,
        },
        'streamlit_session_id': session_id_display,
        'run_counter': st.session_state.run_counter,
        'script_path': {
            'wrapper': os.path.abspath(__file__),
            'working_dir': os.getcwd(),
            'script_dir': os.path.dirname(os.path.abspath(__file__)),
        },
    }

    # Display as YAML code block
    st.code(yaml.dump(container_details, default_flow_style=False), language='yaml')

except Exception as e:
    # Fall back to simple message if container info retrieval fails
    error_msg = f'Failed to retrieve container information: {e}'
    stack_trace = traceback.format_exc()

    # Log the error
    logger.error(error_msg)
    logger.error(f'Traceback: {stack_trace}')

    # Show error to user
    st.error(error_msg)
    st.code(stack_trace, language='python')
    st.write(
        f'[wrapper] Running in {env_type} mode, run_counter={st.session_state.run_counter}'
    )

# Add path to sys.path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.info(
        f'Added {current_dir} to sys.path',
        extra={'run_index': st.session_state.run_counter},
    )

# Import and run the actual application
logger.info(
    'Attempting to import the application',
    extra={'run_index': st.session_state.run_counter},
)

try:
    # For testing, we can switch between test_app and app_for_wrapper
    # Uncomment the one you want to use
    # from test_app import run
    from app import run

    logger.info(
        'Application imported successfully',
        extra={'run_index': st.session_state.run_counter},
    )

    # Run the application - handle both regular and async functions
    logger.info(
        'Running the application', extra={'run_index': st.session_state.run_counter}
    )

    # Check if the function is an async function
    if asyncio.iscoroutinefunction(run):
        # Run async function
        asyncio.run(run())
    else:
        # Run regular function
        run()

    # Add success message to UI
    # NOTE:
    #   Can uncomment this for debugging purposes
    # st.success('Application executed successfully')

except Exception as e:
    # Log the exception
    error_msg = f'Exception caught: {e}\n{traceback.format_exc()}'
    logger.error(
        f'ERROR: {error_msg}', extra={'run_index': st.session_state.run_counter}
    )

    # Display error in UI
    st.error(f'Failed to load application: {e}')
    st.code(traceback.format_exc())

# Final log statement
logger.info('Wrapper finished', extra={'run_index': st.session_state.run_counter})
