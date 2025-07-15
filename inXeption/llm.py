'''
Pure LLM API interface with consistent error handling.

This module provides core functionality for interacting with the Anthropic Claude API,
handling common operations like HTTP requests, error handling, token counting, and logging.
'''

import asyncio
import logging
import os
import traceback
from enum import Enum

import httpx

from inXeption import anthropic_config
from inXeption.anthropic_config import (
    BETA_FLAGS,
    MODEL_CONSTRAINTS,
    MODELS,
    REQUIRED_HEADERS,
)
from inXeption.utils.misc import timestamp
from inXeption.utils.yaml_utils import dump_str

# Initialize logger
logger = logging.getLogger(__name__)

HTTP_TIMEOUT_S = 180

EMPTY_PLACEHOLDER = '<empty response from LLM>'


class ResponseOutcome(str, Enum):
    '''Possible outcomes of an LLM API call'''

    TOOL_USE = 'tool_use'  # Success with tools
    END_TURN = 'end_turn'  # Success without tools
    UNEXPECTED_STOP = 'unexpected_stop'
    HTTP_ERROR = 'http_error'
    EXCEPTION = 'exception'
    INTERRUPTED = 'interrupted'
    REFUSAL = 'refusal'  # Claude 4.0 safety refusal


async def query_llm_api(
    messages,
    prompts,
    tools,
    interrupt_check,
    timeout_s=HTTP_TIMEOUT_S,
):
    '''
    💙3.1 LLM API ORCHESTRATION

    query_llm_api guarantees a normalized response regardless of upstream contingencies:

    - ALWAYS returns dict with {outcome, usage, llm_blocks} regardless of exceptions
    - Handles all error cases: HTTP errors, timeouts, interruptions, API errors
    - Manages interruption via interrupt_check callback during API call
    - Transforms raw responses into standard structure for all outcome types
    - Determines response outcome (TOOL_USE, END_TURN, INTERRUPTED, etc.)
    - Sets appropriate default values for missing fields

    CONTRACT: Takes prepared messages, returns standardized dict even under any failure
    '''

    # Capture model being used before potential state change
    model_used = 'opus' if 'opus' in anthropic_config.state else 'sonnet'

    # Prepare request
    api_url = 'https://api.anthropic.com/v1/messages'
    request_body = _prepare_request_body(messages, prompts, tools)
    headers = _prepare_headers()

    # Create a task for the API call (without passing interrupt_check)
    api_task = asyncio.create_task(
        _core_api_call(api_url, request_body, headers, timeout_s)
    )

    # Handle interruption at this level
    while not api_task.done():
        await asyncio.sleep(0.5)
        if interrupt_check():
            # Cancel the API call
            api_task.cancel()
            try:
                await api_task
            except asyncio.CancelledError:
                pass

            # Create interrupt response
            result = {
                'outcome': ResponseOutcome.INTERRUPTED,
                'usage': None,
                'content_blocks': [
                    {'type': 'text', 'text': '🛑 Response cancelled by user'}
                ],
                'model_used': model_used,
            }

            return result

    # Process the API response
    try:
        response = await api_task

        # Extract status code and data
        status_code = response.status_code

        # Handle successful responses
        if status_code == 200:
            # Parse response JSON
            response_data = response.json()

            # Get content blocks
            content_blocks = response_data['content']

            # Extract usage information as a dictionary
            usage_dict = response_data.get('usage', {})

            # Determine outcome based on stop_reason
            if response_data['stop_reason'] == 'tool_use':
                outcome = ResponseOutcome.TOOL_USE
            elif response_data['stop_reason'] == 'end_turn':
                outcome = ResponseOutcome.END_TURN
            elif response_data['stop_reason'] == 'refusal':
                outcome = ResponseOutcome.REFUSAL
                logger.warning(
                    f'Model refused to generate content: {response_data.get("stop_sequence", "No stop sequence provided")}'
                )
            else:
                outcome = ResponseOutcome.UNEXPECTED_STOP
                logger.warning(
                    f'Unexpected stop_reason: {response_data["stop_reason"]}'
                )

            result = {
                'outcome': outcome,
                'usage': usage_dict,
                'content_blocks': content_blocks,
                'model_used': model_used,
            }

            # Reset state if it was opus-for-one-cycle
            if anthropic_config.state == 'opus-for-one-cycle':
                anthropic_config.state = 'sonnet'

            return result

        else:
            # Handle HTTP errors with standardized format
            response.raise_for_status()  # Will raise an exception with proper status code

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors
        error_data = {
            'status': 'error',
            'error_type': 'http_error',
            'status_code': e.response.status_code,
        }

        # Try to extract response detail
        try:
            error_body = e.response.json()
            error_data['response'] = error_body
        except Exception:
            error_data['response_text'] = e.response.text

        # Create error response with standardized format
        result = {
            'outcome': ResponseOutcome.HTTP_ERROR,
            'usage': None,
            'content_blocks': [
                {
                    'type': 'text',
                    'text': f'⚠️ HTTP Error ({e.response.status_code}):\n{dump_str(error_data)}',
                }
            ],
            'model_used': model_used,
        }

        return result

    except Exception as e:
        # Handle any other exceptions with standardized format
        error_data = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
        }

        # Create error response
        result = {
            'outcome': ResponseOutcome.EXCEPTION,
            'usage': None,
            'content_blocks': [
                {
                    'type': 'text',
                    'text': f'⚠️ Exception during API call:\n{dump_str(error_data)}',
                }
            ],
            'model_used': model_used,
        }

        return result


async def _core_api_call(
    api_url,
    request_body,
    headers,
    timeout_s,
):
    '''
    💙3.2 LLM CORE HTTP COMMUNICATION

    _core_api_call performs pure HTTP operations with zero business logic. It accepts a fully formed API URL, headers and request body, returning only the raw httpx.Response object on success.

    This layer performs no error handling, no interruption detection, and no response normalization. It raises exceptions directly for any HTTP failure, connection issue or timeout.

    The sole responsibility is executing the HTTP request and returning its raw result or raising its raw exception.

    CONTRACT: Executes HTTP operation, returns raw response or raises exception.
    '''
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        # Build request and send it
        request = client.build_request(
            'POST', api_url, headers=headers, json=request_body
        )

        # Execute the request directly - no task or interruption handling
        # Will raise appropriate exceptions that the middle layer will handle
        response = await client.send(request)

        # Return the raw response object
        return response


def _prepare_request_body(messages, prompts, tools):
    '''Prepare the request body for the API call'''
    # Select model based on current state
    model = MODELS['opus' if 'opus' in anthropic_config.state else 'sonnet']

    request_body = {
        'model': model,
        'max_tokens': MODEL_CONSTRAINTS['default_output_tokens'],
        'messages': messages,
        'thinking': {'type': 'enabled', 'budget_tokens': 4096},
    }

    # Add system prompt if provided
    system_prompt = prompts['system']
    if system_prompt:
        request_body['system'] = [{'type': 'text', 'text': system_prompt}]

    # Add tools if provided
    if tools:
        request_body['tools'] = tools

    return request_body


def _prepare_headers():
    '''Prepare headers for the API call'''
    headers = {
        'x-api-key': os.environ['ANTHROPIC_API_KEY'],
        'content-type': 'application/json',
        'anthropic-version': REQUIRED_HEADERS['anthropic-version'],
    }

    # Add enabled beta flags
    enabled_flags = [flag for flag, enabled in BETA_FLAGS.items() if enabled]
    if enabled_flags:
        headers['anthropic-beta'] = ','.join(enabled_flags)

    return headers


async def count_tokens(prompts, tools, messages, render_fn):
    '''Count tokens accurately using Anthropic API'''
    async with httpx.AsyncClient(timeout=10) as client:
        # strip thinking tokens
        def sanitize(message):
            return {
                'role': message['role'],
                'content': [b for b in message['content'] if b['type'] != 'thinking'],
            }

        sanitized_messages = [sanitize(u) for u in messages]

        # API error if last message isn't a user-message
        if sanitized_messages[-1]['role'] == 'assistant':
            sanitized_messages.append(
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': prompts['suffix'],
                        }
                    ],
                }
            )

        # Prepare request body
        model = MODELS['opus' if 'opus' in anthropic_config.state else 'sonnet']
        request_body = {
            'model': model,
            'system': [{'type': 'text', 'text': prompts['system']}],
            'tools': tools,
            'messages': sanitized_messages,
        }

        # Setup headers
        headers = {
            'x-api-key': os.environ['ANTHROPIC_API_KEY'],
            'content-type': 'application/json',
            'anthropic-version': REQUIRED_HEADERS['anthropic-version'],
        }

        def log_error(request_data, error_data):
            # Log the failed request and error
            log_timestamp = timestamp()
            req_file = f'/tmp/token_count_request_{log_timestamp}.yaml'
            err_file = f'/tmp/token_count_error_{log_timestamp}.yaml'

            with open(req_file, 'w') as f:
                f.write(dump_str(request_data))

            with open(err_file, 'w') as f:
                f.write(dump_str(error_data))

            # Use error details from the error_data instead of referencing response
            error_summary = error_data.get('status_code', 'Unknown status')
            if 'exception' in error_data:
                error_summary = f"Exception: {error_data['exception']}"

            logger.error(f'Token counting request failed: {error_summary}')
            logger.error(f'Debug info: request at {req_file}, error at {err_file}')

        try:
            response = await client.post(
                'https://api.anthropic.com/v1/messages/count_tokens',
                headers=headers,
                json=request_body,
            )

            if response.status_code != 200:
                request_data = {
                    'headers': {k: v for k, v in headers.items() if k != 'x-api-key'},
                    'request_body': request_body,
                }

                response_data = {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.text,
                }

                log_error(request_data, response_data)
                return 0

            response.raise_for_status()
            result = response.json()

        except Exception as e:
            request_data = {
                'request_body': request_body,
                'headers': {k: v for k, v in headers.items() if k != 'x-api-key'},
            }

            error_data = {'exception': str(e), 'traceback': traceback.format_exc()}

            log_error(request_data, error_data)

            # Show UI notification of the error
            from inXeption.UIObjects import UIBlockType, UIChatType, UIElement

            error_message = f'⚠️ Token counting failed: {str(e)}'

            ui_element = UIElement.singleblock(
                '⚠️', UIChatType.SYSTEM, UIBlockType.ERROR, error_message
            )

            render_fn(ui_element)

            # Return -1 to signal token counting failure
            return -1

        # Return input tokens count - let error propagate if not present
        return result['input_tokens']
