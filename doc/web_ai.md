# Web Search Capabilities for AI Agents

This document serves as a reference for AI agents to perform web searches using the OpenAI API. At ANY TIME, you can perform a web search using your bash tool when you need information that is likely not in your model weights. This includes current/recent information and obscure topics.

## When to Use Web Search

Consider performing a web search when:
- You need up-to-date information beyond your training data
- You're asked about current events or recent developments
- You need specific details about niche topics
- You're asked for information that requires real-time verification
- You need to cite authoritative sources

## How to Perform Web Searches

The OpenAI API provides a web search tool that can be used with the Responses API endpoint. Here's how to implement it:

### Basic Request Structure

```bash
curl "https://api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o",
        "tools": [{"type": "web_search_preview"}],
        "input": "Your query here"
    }'
```

### Forcing Web Search

To ensure the model uses web search rather than relying on its existing knowledge, include the `tool_choice` parameter:

```bash
curl "https://api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o",
        "tools": [{"type": "web_search_preview"}],
        "tool_choice": {"type": "web_search_preview"},
        "input": "Your query here"
    }'
```

Note: The OPENAI_API_KEY is stored in `/host/.env` file and is also available in the bash environment.

## Best Practices for Formulating Questions

For optimal search results:

- Provide comprehensive, detailed questions - the more detail supplied, the better the response will be
- Include code or pseudocode when asking about programming topics
- Explicitly state "PERFORM A WEB SEARCH" in your query
- Force web search tool use with the `tool_choice` parameter
- Consider specifying search parameters like location or context size for more relevant results

## Additional Configuration Options

### User Location

```bash
curl "https://api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o",
        "tools": [{
            "type": "web_search_preview",
            "user_location": {
                "type": "approximate",
                "country": "US",
                "city": "San Francisco"
            }
        }],
        "tool_choice": {"type": "web_search_preview"},
        "input": "Your query here"
    }'
```

### Search Context Size

Control the amount of context retrieved with the `search_context_size` parameter:

```bash
curl "https://api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o",
        "tools": [{
            "type": "web_search_preview",
            "search_context_size": "high"
        }],
        "tool_choice": {"type": "web_search_preview"},
        "input": "Your query here"
    }'
```

Options: "low", "medium" (default), or "high"

## Reference

For complete documentation, refer to:
https://platform.openai.com/docs/guides/tools-web-search
