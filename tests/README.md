# Test Suite

This directory contains tests for the interaction loop system, focusing on proper lifecycle management, interruption handling, and resource cleanup.

## Overview

Our system implements an interaction loop that allows an AI assistant to interact with tools. It's critical that all components handle interruptions properly and clean up resources when operations terminate. These tests verify that the system behaves correctly in various scenarios.

## Loop Test Framework

The test framework consists of two main components:

1. **Test Runner** (`loop_test.py`): Loads and executes tests defined in YAML
2. **Test Definitions** (`loop_tests.yaml`): Contains test configurations with clear expectations

For details on individual test cases, refer directly to the `loop_tests.yaml` file, which contains comprehensive test definitions including expected outcomes.

## Running the Tests

To run the loop tests:

```bash
# List all available tests
python -m tests.loop_test list

# Run a specific test
python -m tests.loop_test bash-tool-use

# Run a test with process tracking enabled
python -m tests.loop_test bash-tool-use --track-processes
```

### Process Tracking

The `--track-processes` option enables verification of process cleanup after test execution:

- Tracks process creation and termination during test execution
- Verifies that no bash processes are left behind after the test completes
- Useful for debugging resource leaks, particularly with bash tool usage

## What to Look For in Test Results

When the tests run successfully, you should see:

1. **Test Description and Expectations**:
   - Each test begins with a clear description of what is being tested
   - Expected outcomes are displayed for validation

2. **Message Flow**:
   - Tracked and displayed at the end: e.g., user → assistant → user → assistant

3. **Interruption Messages** (in applicable tests):
   - LLM interruption: "🛑 Response cancelled by user"
   - Bash interruption: "🛑 Tool execution interrupted by user"

4. **Token Statistics**:
   - Usage statistics are displayed at the end of each interaction

5. **Process Tracking** (if `--track-processes` is used):
   - Initial process count
   - Process changes during execution
   - Verification of cleanup after completion

## Debugging

If tests fail, look for:

1. **Process Cleanup Issues** (with `--track-processes`):
   - "Found X leftover bash processes" would indicate resource cleanup problems

2. **Timing Issues**:
   - If timeout/interrupt tests don't complete in the expected time

3. **Message Sequence Issues**:
   - Check if the expected message sequence is not being followed
   - Verify that interruption messages are being added correctly

4. **Tool Result Problems**:
   - Verify partial output is being captured correctly when tools are interrupted

## Adding New Tests

To add a new test, add an entry to `loop_tests.yaml` with:
- `name`: Unique identifier for the test
- `description`: Brief description of what's being tested
- `user_messages`: List of messages to send to the assistant
- `interrupt_phase`: (optional) When to trigger an interrupt
- `expectation`: Detailed explanation of expected outcomes

Example:
```yaml
- name: new-test
  description: Description of new test
  user_messages:
    - |
      🧬 [TEST MODE] Test message
  expectation: |
    Expected outcomes in detail
```
