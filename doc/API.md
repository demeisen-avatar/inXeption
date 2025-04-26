# Anthropic API Contract

## How you (the LLM) work

```
- system_prompt
- tools:
  - description and json-schema for tool 0
  - description and json-schema for tool 1
  - etc.
- messages:
  // example of non-tool-use cycle
  - role:user
  - role:assistant (stop_reason=end_turn)

  // example of tool-use cycle
  - role:user
  - (*) role:assistant (stop_reason=tool_use, contains 1 or more tool_use blocks)
  - role:(synthetic-)user, contains a tool_result block to id-match each tool_use block
  - Either goto (*), or a final role:assistant message with stop_reason=end_turn
```
^ This is what gets fed into the LLM. Notice messages alternate {user, assistant, ...} and final message is 'user', and LLM will generate an 'assistant' message.

## tool-use API

(From https://docs.anthropic.com/en/docs/build-with-claude/)

Example request:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-7-sonnet-20250219",
    "max_tokens": 16384,
    "thinking": {
      "type": "enabled",
      "budget_tokens": 4096
    },
    "tools": [
      {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "messages": [
      {
        "role": "user",
        "content": "What is the weather like in San Francisco?"
      }
    ]
  }'
```

Example API response:

```json
{
  "id": "msg_01Aq9w938a90dw8q",
  "model": "claude-3-7-sonnet-20250219",
  "stop_reason": "tool_use",
  // ^ can also be "end_turn", i.e. no tool invoked
  "role": "assistant",
  "content": [
    {
      "type": "thinking",
      "thinking": "To answer this question, I will: 1. Use the get_weather tool to get the current weather in San Francisco. 2. Use the get_time tool to get the current time in the America/Los_Angeles timezone, which covers San Francisco, CA.",
      "signature": "zbbJhbGciOiJFU8zI1NiIsImtakcjsu38219c0.eyJoYXNoIjoiYWJjMTIzIiwiaWFxxxjoxNjE0NTM0NTY3fQ...."
    },
    {
      "type": "text",
      "text": "I'll check the current weather in San Francisco for you."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": {"location": "San Francisco, CA"}
    }
  ],
  "usage": {
    "input_tokens": 4,
    "output_tokens": 503,

    // if we're using cache we'll also get these two:
    "cache_creation_input_tokens": 1854,
    "cache_read_input_tokens": 154,

    // Claude 3.7 Sonnet has 200k context window
    // Claude 3.7 Sonnet can output up to 128k tokens (significantly increased from 8192 in Claude 3.5)
  }
}
```

We then have to throw back a synthetic user-message whose "content" is a list of blocks, including one-tool_result-block-per-tool_use-block, e.g.:

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": [
        {
          "type": "text",
          "text": "Currently 15°C (59°F), Partly Cloudy, Wind: 12 mph from the west"
        }
      ]
      // ^ content can be a string or a list of blocks
      // blocks can be text-blocks or image-blocks
    }
  ]
}
```

NOTE: It's fine to add our own textblock to this list, which we DO in order to achieve "soft-terminate".

## Thinking Feature (Claude 3.7+)

Claude 3.7+ only. To enable:

```json
"thinking": {
  "type": "enabled",
  "budget_tokens": 4096  // Configurable token budget for thinking, minimum 1,024 tokens, counts against max_tokens
}
```

When using thinking with tool use, you must preserve and pass back the thinking block's signature unmodified in subsequent requests.

## Image Blocks

Can supply images in ACTUAL user messages and within tool-result blocks (within a _synthetic_ user message)

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
  "content": [
    {
      "type": "text",
      "text": "Here's the screenshot you requested"
    },
    {
      "type": "image",
      "source": {
        "type": "base64",
        "media_type": "image/jpeg", // or image/png, etc.
        "data": "base64-encoded-image-data"
      }
    }
  ]
}
```

## computer-use beta

```bash
curl https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: computer-use-2025-01-24" \
  # ^ use this flag!
  -d '{
    "model": "claude-3-7-sonnet-20250219",
    "max_tokens": 16384,
    "tools": [
      {
        "name": "computer",
        "type": "computer_20250124",
        "display_width_px": 1024,
        "display_height_px": 768,
        "display_number": 1
      },
      {
        "name": "str_replace_editor",
        "type": "text_editor_20250124"
      },
      {
        "name": "bash",
        "type": "bash_20250124"
      }
    ],
    "messages": [
      {
        "role": "user",
        "content": "Save a picture of a cat to my desktop."
      }
    ]
  }'
  # 'vanilla' tool block has keys:
  #     name, description, input_schema
  # 'special' tool block (requires beta header) has keys:
  #     type, (optionally other keys, but the server will see the header and apply description/input_schema serverside)
```

Basically what's going on is that we supply this extra `"anthropic-beta: computer-use-2025-01-24"` header, and then instead of supplying json-schemas for these tools, we just use `"type": "bash_20250124", "name": "bash"`.

Anthropic then supplies the appropriate json schemas for these tools (which I can grab, but you have them in your context-history so you can SEE them!)

We can easily just send in the schemas ourselves, and not use this beta, and we'll get the same thing!

Now it is possible that the latest (or future) claude sonnet model is fine-tuned for these tools, so writing our own tools might have downsides. But I calculate the upside is going to be greater. We will be able to control what's going on, e.g. set a custom per-tool-invocation timeout -- so we can wait 5s for an `ls` command but 10min for `apt-get install $some_big_package`

NOTE: We're now NOT using this beta-header. We're supplying the tool schemas DIRECTLY.

## Beta Features

Claude 3.7 supports several beta features that can be enabled via the `anthropic-beta` header:

```
anthropic-beta: computer-use-2025-01-24,token-efficient-tools-2025-02-19,output-128k-2025-02-19
```

Key beta features:
- `computer-use-2025-01-24`: Enables computer interaction tools
- `prompt-caching-2024-07-31`: No longer needed -- it's enabled by default now
- `token-efficient-tools-2025-02-19`: Makes tool usage more token-efficient (note: may conflict with other features)
- `output-128k-2025-02-19`: Required for 128K token output capability

## Token Counts

### Tool Token Costs
- Computer tool: 735 tokens
- Text editor tool: 700 tokens
- Bash tool: 245 tokens

### System Prompt Token Costs
- For `auto` tool choice: 466 tokens
- For `any`/`tool`: 499 tokens

## Rate Limits

The API enforces a rate limit of 400,000 input tokens per minute. If exceeded, you'll receive a 429 response:
```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "This request would exceed your organization's rate limit..."
  }
}
```

This limit is shared across all users of the API key. When hitting rate limits, pause and retry the operation later.

## Cache

In Claude 3.7, we typically add a single cache point to the last block of the user message:

```python
# Set cache point on last block of user message
last_content = messages_copy[-1]["content"]
last_content[-1]["cache_control"] = {"type": "ephemeral"}
```

Cache lasts 5 mins (300s).

Cacheing costs 1.25x, and reading cached tokens is 10x cheaper than normal reads.

NOTE: If total tokens (including system prompt and tools) < 1024 for Sonnet or < 2048 for Haiku, cache won't activate.

## Model Constraints

Claude 3.7 Sonnet has the following constraints:
- Maximum input context window: 200,000 tokens
- Maximum output tokens: 128,000 tokens (requires explicit beta header: `anthropic-beta: output-128k-2025-02-19`)
- Default reasonable output size: 16,384 tokens

## Misc Notes

### Empty assistant responses
Claude returns a response.content that is a list of blocks. It may sometimes generate an empty list. If this happens, we append a placeholder textblock to prevent API errors in the next request.

## 4xx http responses (errors)

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "<string>"
  }
}
```

### Controlling tool choice

```json
"tool_choice": {
  "type": "auto",  // (default) 0 1 or more tools can be used
  "disable_parallel_tool_use": true  // prevents > 1 tool being used
}
"tool_choice": {
  "type": "any",  // EXACTLY ONE tool is used
}
"tool_choice": {
  "type": "tool",  // forces exactly THIS tool to be used
  "name": "the_tool_name"
}
```

## Notes

We don't use computer-use header any more as we write our own tools.
