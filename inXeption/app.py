'''
Main application entry point for the LLM agent with tools.
'''

'''
💙2.0 UI ABSTRACTION AND RENDERING PROTOCOL
The rendering protocol completely decouples the interaction lifecycle from the UI
implementation (currently Streamlit). This achieves several critical goals:

1. Test-driven development: Tests can run the entire interaction flow without a
   UI, using a custom render function to capture and validate outputs

2. Future-proofing: The entire interaction system (Interaction.py and downstream)
   can be lifted unchanged into a different UI implementation

3. Separation of concerns: Interaction logic is isolated from presentation details,
   making both easier to maintain and evolve independently

The render_fn function passed to Interaction.run creates this clean separation,
allowing interaction flows to be developed and tested without spinning up Streamlit.
'''

import asyncio
import os
from base64 import b64decode

import streamlit as st
from Interaction import Interaction

from inXeption.UIObjects import UIBlockType, UIChatType, UIElement
from inXeption.utils.yaml_utils import from_yaml_file

# Custom CSS for styling the UI to match the original
STREAMLIT_STYLE = '''
<style>
    /* Hide chat input while agent loop is running */
    .stApp[data-teststate=running] .stChatInput textarea,
    .stApp[data-test-script-state=running] .stChatInput textarea {
        display: none;
    }
    /* Hide the streamlit deploy button */
    .stAppDeployButton {
        visibility: hidden;
    }
    /* Highlight the stop button in red */
    button[kind=header] {
        background-color: rgb(255, 75, 75);
        border: 1px solid rgb(255, 75, 75);
        color: rgb(255, 255, 255);
    }
    button[kind=header]:hover {
        background-color: rgb(255, 51, 51);
    }
</style>
'''


def run():
    '''Main application entry point called by wrapper.py'''
    # Initialize session state
    initialize_session_state()

    # Apply custom CSS
    st.markdown(STREAMLIT_STYLE, unsafe_allow_html=True)

    # Build UI
    st.title('💫 inXeption.')

    # Display conversation history
    render_conversation_history()

    # User input and controls
    handle_user_input()


def load_prompts():
    '''Load prompts from the YAML configuration file'''
    prompts_path = os.path.join(os.path.dirname(__file__), 'prompts.yaml')
    return from_yaml_file(prompts_path)


def initialize_session_state():
    '''Initialize session state variables'''
    # Initialize interactions list
    if 'interactions' not in st.session_state:
        st.session_state.interactions = []

    # Initialize interaction index
    if 'interaction_index' not in st.session_state:
        st.session_state.interaction_index = 0

    # Stop requested flag for interruption
    if 'stop_requested' not in st.session_state:
        st.session_state.stop_requested = False

    # Initialize battery percentage for token tracking
    if 'prev_battery_pct' not in st.session_state:
        st.session_state.prev_battery_pct = 100  # Start at 100%


def render_conversation_history():
    '''Render all previous interactions'''
    for interaction_data in st.session_state.interactions:
        # Deserialize and render the interaction
        Interaction.model_validate(interaction_data).render(render_ui_element)


def handle_user_input():
    '''Handle user input and process new messages'''
    # Get new message via chat input
    new_message = st.chat_input(
        'Type a message to send to Claude to control the computer...'
    )

    # Process new message if there is one
    if new_message:
        # Reset stop flag
        st.session_state.stop_requested = False

        # Increment interaction index
        st.session_state.interaction_index += 1

        # Process the message
        asyncio.run(process_message(new_message))


# Function to check if interrupt is pending
def interrupt_pending():
    '''Check if an interrupt is pending via stop button press'''
    return st.session_state.stop_requested


async def process_message(user_message):
    '''Process a user message by creating and running an interaction'''
    from inXeption import anthropic_config

    # Handle model switching commands
    message_lower = user_message.strip().lower()

    # Split the message to handle both spaces and newlines
    message_parts = message_lower.split()

    if not message_parts:
        # Empty message, continue with normal processing
        pass
    elif message_parts[0] == '/opus':
        if len(message_parts) == 1:
            # Just the command alone - switch default to opus
            anthropic_config.state = 'opus'
            UIElement.singleblock(
                '⚙️',
                UIChatType.SYSTEM,
                UIBlockType.TEXT,
                '✅ Default model set to Claude 4.0 Opus',
            ).render(render_ui_element)
            return
        else:
            # Command with content - use opus for just this message
            anthropic_config.state = 'opus-for-one-cycle'
            # Continue processing with the rest of the message
            user_message = user_message.strip()[6:].strip()
    elif message_parts[0] == '/sonnet':
        if len(message_parts) == 1:
            # Just the command alone - switch default to sonnet
            anthropic_config.state = 'sonnet'
            UIElement.singleblock(
                '⚙️',
                UIChatType.SYSTEM,
                UIBlockType.TEXT,
                '✅ Default model set to Claude 3.7 Sonnet',
            ).render(render_ui_element)
            return
        else:
            # Command with content - use sonnet for just this message
            anthropic_config.state = 'sonnet'
            # Continue processing with the rest of the message
            user_message = user_message.strip()[8:].strip()

    # Create interaction
    interaction = Interaction(user_message=user_message)

    # Load prompts from configuration file
    prompts = load_prompts()

    # Run the interaction
    await interaction.run(
        render_fn=render_ui_element,
        interrupt_check=interrupt_pending,
        prompts=prompts,
        previous_interactions=st.session_state.interactions,
    )

    # Store serialized interaction
    st.session_state.interactions.append(interaction.model_dump())


def render_ui_element(ui_element):
    '''
    Render a UI element to the Streamlit interface using chat_message

    Accepts either a UIElement object or a dictionary with the legacy format.
    '''
    # Handle dictionary format (coming from model_dump or legacy code)
    if isinstance(ui_element, dict):
        chat_type = ui_element['chat_type']
        avatar = ui_element['avatar']
        blocks = ui_element['blocks']
    else:
        # It's a UIElement object
        chat_type = ui_element.chat_type
        avatar = ui_element.avatar
        blocks = ui_element.blocks

    with st.chat_message(chat_type, avatar=avatar):
        for block in blocks:
            # Handle either dictionary or UIBlock object
            if isinstance(block, dict):
                block_type = block['type']
                content = block['content']
            else:
                block_type = block.type
                content = block.content

            if block_type == 'code' or block_type == UIBlockType.CODE:
                st.code(content, wrap_lines=True)
            elif block_type == 'markdown' or block_type == UIBlockType.MARKDOWN:
                st.markdown(content)
            elif block_type == 'text' or block_type == UIBlockType.TEXT:
                st.markdown(content)
            elif block_type == 'error' or block_type == UIBlockType.ERROR:
                # Use code block with backticks to prevent markdown rendering
                st.error(f'```\n{content}\n```')
            elif block_type == 'warning' or block_type == UIBlockType.WARNING:
                st.warning(content)
            elif block_type == 'info' or block_type == UIBlockType.INFO:
                st.info(content)
            elif block_type == 'image' or block_type == UIBlockType.IMAGE:
                # Decode base64 data before passing to st.image()
                st.image(b64decode(content))
            else:
                raise ValueError(f"Unknown UI block type: '{block_type}'")
