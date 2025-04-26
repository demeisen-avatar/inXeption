# Streamlit Stop Button Handling - Technical Analysis

## Problem Statement

When a user presses the Streamlit STOP button during a long-running tool execution (like a bash command), we need to:

1. Detect the button press and interrupt the tool execution
2. Preserve the partial tool results
3. Add appropriate messages to the conversation history
4. Maintain state consistency across the interruption

This is challenging due to Streamlit's execution model and the behavior of StopException.

## Current Implementation

We've solved this problem by using Streamlit's session_state combined with proper ScriptRunContext management. Our solution:

1. **Monkey Patches the Stop Button Handler**: Intercepts the stop button press without raising StopException
2. **Uses Session State as a Flag**: Sets `st.session_state.stop_requested = True` when the button is pressed
3. **Periodically Checks This Flag**: Tools like the bash executor check this flag during execution
4. **Preserves Partial Results**: When interrupted, tools capture and return their partial output

This approach provides immediate interruption with proper state handling, eliminating the need for file-based signaling or waiting for a second user message.

## Understanding Streamlit's Execution Model

Streamlit's execution model creates unique challenges for interruption handling:

1. **Full Script Execution**: Every UI event triggers a complete rerun of the entire script
2. **Non-Interruptible Operations**: Long-running operations like bash commands don't have natural interrupt points
3. **StopException Limitations**: StopException is designed to be uncatchable and terminates the script unpredictably

The standard Streamlit STOP button behavior is problematic because:
- It doesn't immediately interrupt running code
- It sets an internal flag that only triggers at "interrupt points" (which may never occur during tool execution)
- It can't be fully suppressed, even when caught in try/except blocks

## The Key Innovation: ScriptRunContext

The critical insight for our solution is understanding Streamlit's ScriptRunContext:

1. **Context Requirement**: Any code accessing session_state must have the proper ScriptRunContext attached to its thread
2. **Early Capture**: Context must be captured when the script first loads, not during the stop button event
3. **Thread Sharing**: The same context must be shared between the main thread and tool execution threads

Our implementation captures the ScriptRunContext at module level initialization:

```python
# Capture the script context at module level when script first loads
SCRIPT_RUN_CTX = get_script_run_ctx()
```

And then applies it in our custom stop handler and tool execution code:

```python
# Apply context to current thread when needed
if SCRIPT_RUN_CTX:
    add_script_run_ctx(threading.current_thread(), SCRIPT_RUN_CTX)
```

This allows our tools to reliably check session_state for the stop_requested flag during execution.

## Implementation Details

Our solution has three main components:

### 1. Monkey Patching the Stop Button Handler

In `streamlit.py`, we intercept the normal stop button behavior:

```python
# Store the original handler
original_stop_handler = AppSession._handle_stop_script_request

# Define our patched handler function
def patched_stop_handler(self):
    # Use the already captured context from module level
    if SCRIPT_RUN_CTX:
        add_script_run_ctx(threading.current_thread(), SCRIPT_RUN_CTX)

    # Set our flag in session state
    st.session_state.stop_requested = True

    # Log that we detected the stop button press
    logger.warning("Stop button press detected", extra={"run_index": RUN_INDEX})

    # DELIBERATELY NOT calling the original handler to avoid StopException
    # return original_stop_handler(self)

# Apply the monkey patch
AppSession._handle_stop_script_request = patched_stop_handler
```

This approach captures the stop button press but prevents the StopException from being raised, giving us control over interruption handling.

### 2. Tool Interruption Detection

In `bash.py`, we periodically check for interruption during command execution:

```python
# Check if stop button was pressed via session_state
import threading
import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Get current script run context and attach it to this thread
ctx = get_script_run_ctx()
if ctx:
    add_script_run_ctx(threading.current_thread(), ctx)

# Check session state
if "stop_requested" in st.session_state and st.session_state.stop_requested:
    logger.info("Stop button press detected via session state")

    # Capture partial output
    output = self._process.stdout._buffer.decode()
    error = self._process.stderr._buffer.decode()

    # Return early with partial results
    return CLIResult(
        output=output.strip() if output else None,
        error=error.strip() if error else None,
        system="Command execution was interrupted"
    )
```

The bash tool checks for the flag during command execution, allowing for immediate interruption.

### 3. LLM Response Handling in loop.py

Our solution also handles interruptions during LLM API responses:

```python
# Check if stop_requested flag was set while waiting for API response
if "stop_requested" in st.session_state and st.session_state.stop_requested:
    logger.info("Stop button was pressed while waiting for LLM response - aborting response")

    # Replace the response content with a cancellation message
    response.content = [
        BetaTextBlock(
            type="text",
            text="🛑 **Response aborted by user** - The stop button was pressed."
        )
    ]

    # Change stop_reason to end_turn to prevent tool execution
    response.stop_reason = "end_turn"

    # Reset the flag
    st.session_state.stop_requested = False
```

This ensures we can interrupt at multiple points in the execution cycle.

## Benefits of the Current Solution

Our session_state-based approach has several key advantages over previous approaches:

1. **Immediate Interruption**: Tools respond to the stop button press without needing a second user message
2. **Clean State Management**: No need for external files or complex IPC mechanisms
3. **No Timing Dependencies**: Works regardless of when the stop button is pressed
4. **Multiple Interruption Points**: Can interrupt during both tool execution and LLM response

In our testing, this approach reliably handles various user interaction patterns:

1. User presses stop during a long-running bash command
2. User presses stop while waiting for an LLM API response
3. User presses stop multiple times during an interaction

When a tool is interrupted, it returns any partial results along with a clear system message indicating the interruption. This preserves valuable information while clearly communicating the interruption to the user.

## Key Technical Challenges Solved

This implementation addresses several critical technical challenges:

1. **Thread Context Management**: Ensuring proper ScriptRunContext access across threads
2. **StopException Avoidance**: Preventing unpredictable script termination
3. **Consistent State**: Maintaining conversation state through interruptions
4. **Immediate Feedback**: Providing clear user feedback without delay

The most significant innovation was understanding and properly utilizing Streamlit's ScriptRunContext. Without properly managing this context, attempts to access session_state from background threads (like during tool execution) would fail with mysterious errors or warnings.

## Streamlit Limitations and Workarounds

Our solution works around several Streamlit limitations:

1. **StopException Behavior**:
   - Inherits from BaseException (not Exception) to avoid being caught by normal try/except blocks
   - Can't be fully suppressed - Streamlit terminates scripts even if caught in try/except
   - Has unpredictable timing - most likely to trigger on session_state access
   - Not well-documented in Streamlit's official docs

2. **Documentation Gaps**:
   - Streamlit provides almost no documentation about stop button internals
   - The concept of "interrupt points" is undocumented
   - Thread safety and session_state access across threads is barely mentioned
   - ScriptRunContext requirements are not clearly explained

By monkey patching the stop handler, we effectively bypass Streamlit's default interruption mechanism while maintaining full functionality.

## Evolution of Our Implementation

Our solution evolved through several iterations:

1. **Initial File-Based Approach**: Used files as signals between script runs
   - Created status files to track running tools
   - Required a second user message to trigger interruption
   - Had timing dependencies that could cause errors

2. **Current Session_State Approach**: Direct in-memory signaling
   - Uses Streamlit's own state management
   - Provides immediate interruption
   - Works with any timing pattern
   - Maintains state consistency throughout

The key insight that made this possible was properly understanding and utilizing ScriptRunContext to enable secure cross-thread access to session_state.

## Recommendations for Maintenance

When working with this code in the future:

1. **Preserve the Module-Level Context Capture**:
   ```python
   SCRIPT_RUN_CTX = get_script_run_ctx()
   ```
   This must happen when the module is first loaded.

2. **Apply Context Before Accessing session_state**:
   ```python
   add_script_run_ctx(threading.current_thread(), SCRIPT_RUN_CTX)
   ```
   Especially in background threads and the stop handler.

3. **Handle Both Interruption Points**:
   - During LLM API response processing
   - During tool execution

4. **Reset the Flag After Handling**:
   ```python
   st.session_state.stop_requested = False
   ```
   This prevents false triggers in subsequent operations.

## Conclusion

Our stop button implementation successfully solves a challenging problem in Streamlit's execution model. By creatively working around Streamlit's limitations, we've delivered a solution that:

1. **Provides Immediate Response**: The stop button now works instantly, without requiring a second message
2. **Preserves Valuable Context**: Partial results are captured and displayed rather than lost
3. **Maintains Conversation Continuity**: The interaction can seamlessly continue after interruption
4. **Improves User Experience**: Clear feedback is provided about what happened

The core insight about properly managing ScriptRunContext across threads enabled this solution. Without this understanding, reliable interrupt handling would not be possible.

For future maintainers, this document provides both the technical details of the implementation and the rationale behind our design decisions. The combination of monkey patching the stop handler and checking for interruption flags during tool execution creates a robust solution to what was initially a complex problem with Streamlit's execution model.

## Source Code References

For future reference, here are the key files in our implementation:

1. **Monkey-patched stop handler**:
   - `/host/inXeption/app.py` (~lines 30-73)

2. **Tool interruption detection**:
   - `/host/inXeption/tools/bash.py` (~lines 113-157)

3. **LLM response interruption**:
   - `/host/inXeption/loop.py` (~lines 256-292)

The implementation is now clean, well-tested, and reliable for users.
