#!/usr/bin/env python3
'''
Test framework for Python tool functionality.
Uses YAML configuration for test definitions with human-readable expectations.
'''

import argparse
import asyncio
import logging
import sys
import textwrap
from pathlib import Path

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger('python_test')

# Make sure we have access to the project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import the actual PythonTool class directly
from inXeption.tools.python import PythonTool
from inXeption.utils.yaml_utils import dump_str, from_yaml_file


def pretty_yaml(obj, indent_spaces=4):
    '''Format YAML dump with newline and indentation for better readability.'''
    s = dump_str(obj)
    if len(s) > 10000:
        s = s[:10000] + f'\n<⚠️ Truncated {len(s) - 10000} chars>\n'
    return '\n' + textwrap.indent(s, ' ' * indent_spaces)


def load_tests():
    '''Load test definitions from YAML file.'''
    tests = from_yaml_file(Path(__file__).parent / 'python_tests.yaml')
    return {test['name']: test for test in tests}


def list_available_tests(tests):
    '''Print available tests with names and descriptions.'''
    logger.info('\nAvailable Python Tool Tests:')
    logger.info('-' * 50)
    for name, config in tests.items():
        logger.info(f'  {name}: {config["description"]}')
    logger.info('\nRun a test with: python tests/python_test.py <test_name>')
    logger.info('Run all tests with: python tests/python_test.py --all')


async def run_single_test(test_config, python_tool):
    '''Run a single Python tool test based on its configuration.'''
    test_name = test_config['name']
    code_blocks = test_config['code_blocks']

    logger.info(f'\n\n--- TEST: {test_name} ---')
    logger.info(f'Description: {test_config["description"]}')

    # Set up a function that never triggers an interrupt
    def no_interrupt():
        return False

    results = []

    try:
        # Execute each code block in sequence to test state persistence
        for i, code_block in enumerate(code_blocks):
            block_num = i + 1
            logger.info(
                f'Code Block {block_num}: {code_block.replace(chr(10), "[NL]")}'
            )

            # Call the tool directly using __call__ method
            result = await python_tool(
                tool_id=f'test_{test_name}_block{block_num}',
                interrupt_check=no_interrupt,
                code=code_block,
            )
            logger.info(f'Result Block {block_num}: {result}')
            results.append(result)

        # Show expectations
        logger.info('\nExpectation:')
        logger.info(test_config['expectation'])

        return results
    except Exception as e:
        logger.error(f'Error executing test: {e}')
        return None


async def run_tests(test_names=None, all_tests=False):
    '''Run specified tests or all tests.'''
    # Load all test configurations
    tests = load_tests()

    # Determine which tests to run
    if all_tests:
        tests_to_run = list(tests.values())
        logger.info(f'Running all {len(tests_to_run)} tests')
    elif test_names:
        tests_to_run = []
        for name in test_names:
            if name in tests:
                tests_to_run.append(tests[name])
            else:
                logger.warning(f'Test "{name}" not found')
        logger.info(f'Running {len(tests_to_run)} specified tests')
    else:
        logger.info('No tests specified')
        list_available_tests(tests)
        return

    # Create PythonTool instance
    logger.info('Creating PythonTool instance')
    python_tool = PythonTool()

    try:
        # Run each specified test
        for test_config in tests_to_run:
            await run_single_test(test_config, python_tool)
    finally:
        # Clean up
        logger.info('Cleaning up resources')
        await python_tool.cleanup()


async def main():
    '''Main entry point for the test runner.'''
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run Python tool tests')
    parser.add_argument('test_name', nargs='?', help='Name of the test to run')
    parser.add_argument('--all', action='store_true', help='Run all tests')

    args = parser.parse_args()

    # Handle special cases for help and list
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help', 'list']:
        tests = load_tests()
        list_available_tests(tests)
        return

    # Run tests based on arguments
    if args.all:
        await run_tests(all_tests=True)
    elif args.test_name:
        await run_tests(test_names=[args.test_name])
    else:
        list_available_tests(load_tests())


if __name__ == '__main__':
    asyncio.run(main())
