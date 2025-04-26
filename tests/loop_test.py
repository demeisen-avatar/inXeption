#!/usr/bin/env python3
'''
Test framework for interaction functionality based on our current architecture.
Uses YAML configuration for test definitions with human-readable expectations.
'''

PROMPTS = {
    'system': 'You are running an automated self-test. Do EXACTLY as instructed and no more. If you encounter unexpected behaviour, do not push through it. Instead, report back.',
    # Suffix must include {{BATTERY}} placeholder for proper battery level interpolation
    'suffix': '{{BATTERY}} [auto-appended suffix -- ignore this, it is from the agent-software, not the user]',
}

import argparse
import asyncio
import datetime
import logging
import os
import pathlib
import sys
import textwrap
import time

# Add paths correctly for test environment
SCRIPT_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INXEPTION_DIR = PROJECT_ROOT / 'inXeption'

# Add the project root to sys.path to ensure imports work
sys.path.append(str(PROJECT_ROOT))

# Import utility functions
from inXeption.utils.misc import create_or_replace_symlink, timestamp

# Set LOG_DIR environment variable for HTTP logging
# This needs to be set before importing any modules that use it
test_timestamp = timestamp()
test_log_dir = PROJECT_ROOT / '.logs' / 'test' / test_timestamp
test_log_dir.mkdir(parents=True, exist_ok=True)
os.environ['LOG_DIR'] = str(test_log_dir)

# Set LOOP_TEST_MODE environment variable to differentiate test interactions
# This allows us to use different sound effects for test vs. regular interactions
os.environ['LOOP_TEST_MODE'] = '1'

# Create the test-latest symlink
test_latest_symlink = PROJECT_ROOT / '.logs' / 'test-latest'
target_path = f'test/{test_timestamp}'

# Use our centralized utility function
create_or_replace_symlink(symlink_path=test_latest_symlink, target_path=target_path)

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# Add both the project root and inXeption directory to sys.path
# This allows both absolute and relative imports to work
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(INXEPTION_DIR))

# Import required modules
from copy import deepcopy

from Interaction import Interaction

# Import process tracking utilities (will only be used with --track-processes)
from inXeption.utils.process import (
    find_new_processes,
    get_process_info,
    log_process_changes,
)
from inXeption.utils.yaml_utils import dump_str, from_yaml_file


def strip_base64_from_yaml(ob):
    '''Strip base64 image data from the object before YAML dumping.'''
    ob_copy = deepcopy(ob)

    # Case 1: Direct render packet (UI element with avatar '📷')
    if isinstance(ob_copy, dict) and ob_copy.get('avatar') == '📷':
        for block in ob_copy.get('blocks', []):
            if block.get('type') == 'image' and 'content' in block:
                data_len = len(block['content'])
                block['content'] = f'<{data_len} base64 chars stripped>'
        return ob_copy

    # Case 2: Inside tool results in interactions list
    if isinstance(ob_copy, list):
        for interaction in ob_copy:
            if isinstance(interaction, dict) and 'turns' in interaction:
                for turn in interaction.get('turns', []):
                    for _tool_id, tool_result in turn.get('tool_results', {}).items():
                        if (
                            isinstance(tool_result, dict)
                            and 'result_elements' in tool_result
                        ):
                            for element in tool_result['result_elements']:
                                if isinstance(element, dict) and 'blocks' in element:
                                    for block in element['blocks']:
                                        if (
                                            block.get('type') == 'image'
                                            and 'content' in block
                                        ):
                                            data_len = len(block['content'])
                                            block['content'] = (
                                                f'<{data_len} base64 chars stripped>'
                                            )

    return ob_copy


# Maximum characters for YAML dump before truncation
MAXCHARS = int(1e4)


def pretty_yaml(obj, indent_spaces=4):
    '''Format YAML dump with newline and indentation for better readability.'''
    processed_obj = strip_base64_from_yaml(obj)
    s = dump_str(processed_obj)
    if len(s) > MAXCHARS:
        s = s[:MAXCHARS] + f'\n<⚠️ Truncated {len(s) - MAXCHARS} chars>\n'
    return '\n' + textwrap.indent(s, ' ' * indent_spaces)


def load_tests():
    tests = from_yaml_file(SCRIPT_DIR / 'loop_tests.yaml')
    return {test['name']: test for test in tests}


def list_available_tests(tests):
    '''Print available tests with names and descriptions'''
    logger.info('\nAvailable Tests:')
    logger.info('-' * 50)
    for name, config in tests.items():
        logger.info(f'  {name}: {config["description"]}')
    logger.info('\nRun a test with: python tests/loop_test.py <test_name>')


async def run_test(test_config, track_processes=False):
    '''Run a single test based on its configuration.'''

    logger.info(f'\n🧪\nRUNNING TEST: {test_config["name"]}\n')
    logger.info(pretty_yaml(test_config))

    # Process tracking - capture initial process state if enabled
    before_processes = None
    if track_processes:
        logger.info('Process tracking enabled - capturing initial process state...')
        before_processes = await get_process_info()
        logger.info(f'Starting with {len(before_processes)} processes')

    # Initialize interactions list
    interactions = []

    # Setup interrupt state
    interrupt_state = {'flag': False}

    # Interrupt check function (similar to app.py)
    def check_interrupt():
        return interrupt_state['flag']

    # Setup interrupt trigger based on configuration
    interrupt_phase = test_config.get('interrupt_phase', None)

    async def trigger_interrupt():
        await asyncio.sleep(2)
        logger.info('Triggering interrupt')
        interrupt_state['flag'] = True

    # Render function to display UI elements
    def render(ui_element):
        logger.info(pretty_yaml(ui_element))

        # Handle interrupt for tool execution if configured
        if (
            interrupt_phase == 'tool_execution'
            and ui_element['avatar'] == '🔧'
            and 'bash_tool' in str(ui_element['blocks'])
        ):
            logger.info('Bash tool use detected - scheduling interrupt')
            asyncio.create_task(trigger_interrupt())

    # Process each user message (similar to app.py)
    start_time = time.time()
    for user_msg_text in test_config['user_messages']:
        logger.info(f'Starting interaction at {datetime.datetime.now().isoformat()}')

        # Create interaction (like in app.py)
        interaction = Interaction(user_message=user_msg_text)

        # Setup interrupt if needed
        if interrupt_phase == 'llm':
            asyncio.create_task(trigger_interrupt())

        # Run the interaction (similar to app.py's process_message)
        await interaction.run(
            render_fn=render,
            interrupt_check=check_interrupt,
            prompts=PROMPTS,
            previous_interactions=interactions,
        )

        # Store serialized interaction
        interactions.append(interaction.model_dump())

    logger.info('INTERACTIONS:')
    logger.info(pretty_yaml(interactions))

    # Verify process cleanup if tracking was enabled
    if track_processes:
        logger.info('Verifying process cleanup...')
        # Get final process list
        after_processes = await get_process_info()

        # Log all process changes
        log_process_changes(logger, before_processes, after_processes)

        # Verify cleanup (no bash processes should remain)
        after_new = find_new_processes(before_processes, after_processes)
        bash_processes = {
            pid: info for pid, info in after_new.items() if info.get('is_bash', False)
        }

        if bash_processes:
            logger.warning(f'⚠️ Found {len(bash_processes)} leftover bash processes:')
            for pid, info in bash_processes.items():
                logger.warning(
                    f'  Leftover bash process: PID={pid}, CMD={info.get("cmd")}'
                )
        else:
            logger.info('✅ No leftover bash processes found - cleanup successful')

    # Show completion info
    elapsed = time.time() - start_time
    logger.info(f'\n=== TEST COMPLETED IN {elapsed:.2f}s ===\n')

    # Show expectations reminder
    logger.info('⚠️ NOTE TO AGENT: COMPARE RESULTS WITH EXPECTATIONS:')
    logger.info(test_config['expectation'])


async def main():
    '''Main entry point for the test runner.'''
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run interaction loop tests')
    parser.add_argument('test_name', nargs='?', help='Name of the test to run')
    parser.add_argument(
        '--track-processes',
        action='store_true',
        help='Enable process tracking to verify cleanup',
    )

    # Handle special cases for help and list
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help', 'list']:
        tests = load_tests()
        list_available_tests(tests)
        return

    args = parser.parse_args()

    # Load tests
    tests = load_tests()

    # If no test name provided, show list of tests
    if not args.test_name:
        list_available_tests(tests)
        return

    # Run the specified test
    if args.test_name in tests:
        await run_test(tests[args.test_name], track_processes=args.track_processes)
    else:
        logger.info(f'Test "{args.test_name}" not found')
        list_available_tests(tests)


if __name__ == '__main__':
    asyncio.run(main())
