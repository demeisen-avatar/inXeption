# Gemini API Usage Guide

This document provides instructions for effectively utilizing Google's Gemini models through API calls. It focuses specifically on maintaining free usage through non-billing projects.

## Related Documentation

- **[/host/doc/gcloud.md](./gcloud.md)** - Contains comprehensive documentation on Google Cloud infrastructure, authentication methods, and administration capabilities. Refer to this document for details on Google Cloud account management, project setup, and authentication persistence.

- **[/host/doc/.private/gcloud-notes.md](./.private/gcloud-notes.md)** - Contains sensitive information including API keys for various projects, account details, and organization IDs. This document lists all available API keys, which accounts they're associated with, which projects they belong to, and most importantly, whether those projects have billing enabled.

## Free Usage Strategy

Each Google Cloud project can have its own API key for accessing Gemini models. The key advantage of this approach is that **each project receives its own separate quota of free Gemini API calls**. By using non-billing projects, we can effectively use Gemini without incurring any costs.

⚠️ **PRICING MODEL WARNING:** Gemini API pricing is based on **TOKEN COUNT**, not request count. A single request with large input/output can consume thousands of tokens and potentially exhaust daily quotas quickly.

Here's how it works:
- Each non-billing project gets 100 requests per day (RPD) for Gemini 2.5 Pro
- Each non-billing project is limited to 5 requests per minute (RPM)
- Quotas reset daily, likely at midnight PST/PDT
- Projects are completely independent - exhausting the quota on one project does not affect others
- **Token limits may be reached before request limits** with large context queries

## ⚠️ CRITICAL WARNING ⚠️

**GENERALLY, DO NOT USE API KEYS FROM PROJECTS WITH BILLING ENABLED.**

Only use API keys from projects explicitly marked as having no billing enabled (indicated by `billing: false` in the gclouds.yaml file). Using API keys from billed projects could potentially incur significant costs.

It is PARAMOUNT that we avoid racking up unexpected charges. Always verify that the API key you're using is appropriate for your use case.

## Verifying Billing Status

Before using any API key, verify its billing status with:

```bash
gcloud alpha billing projects describe PROJECT_ID --quiet
```

If `billingEnabled: true` appears in the output, be extremely cautious about using this API key.

## Strategic Use of Billed Projects

There is ONE important exception to the "no billed projects" rule:

**Use API keys from projects with billing enabled ONLY when processing sensitive code or proprietary information that should not be used to train Google's models.**

⚠️ **CRITICAL BILLING WARNING:** When a project has billing enabled:
1. Google treats the data differently and doesn't use it to train their models
2. Your code and sensitive information remain private
3. **ALL API usage is charged from the first token** - there is NO free tier for billing-enabled projects
4. Pricing is based on TOKEN COUNT, not request count - a single large query can cost significant money

**Cost Example:** A typical large code analysis query (500K input + 10K output tokens) costs approximately £0.60-£1.00 in billing-enabled projects.

**$300 Free Credit Plans:** Some Google Cloud accounts have an initial 90-day "$300 free credit" plan that provides free usage up to the credit limit without charging your payment method.

**TODO:** Use gcloud CLI to detect if an account has free credits and determine remaining balance. If credits are available, billing-enabled projects become safe to use for sensitive queries up to the credit limit, with automatic protection against charges once credits are exhausted.

For any queries that contain complete proprietary codebases, sensitive business logic, or other confidential information, use the designated billed project API key found in gclouds.yaml (project marked with `billing: true`) - but be aware of the token-based costs involved.

## Available API Keys

Refer to `/host/doc/.private/gcloud-notes.md` for the full list of available API keys. This document contains:
- API key strings
- Which account each key belongs to
- Which project each key is associated with
- Whether the project has billing enabled
- Additional notes about each key

## Gemini API Setup

To use the Gemini API, you'll need to enable the Generative Language API on your Google Cloud project. This can be done through the Google Cloud Console or via the gcloud command-line tool.

For detailed instructions on creating projects and API keys, refer to the private documentation at `/host/doc/.private/gcloud-notes.md`.

### Common API Issues

When using the Gemini API, you might encounter these common issues:

1. **503 Error (Service Unavailable)**: This usually means the Gemini API is temporarily overloaded. Implement retry logic with exponential backoff, as these errors typically resolve on retry.

2. **429 Error (Too Many Requests)**: You've exceeded the rate limit. Add delay between requests and implement proper rate limiting.

3. **400 Error (Bad Request)**: Check your request format, as this usually indicates malformed JSON or incorrect parameters.

These issues are typically transient and don't reflect a problem with your project configuration.

## Using Gemini with Google Search Grounding

Google Search Grounding is a powerful feature that allows Gemini to perform real-time web searches to provide up-to-date, factual information. This feature is available through the API and does not require a billing-enabled project.

### Recommended Implementation: Using the python_tool

The most reliable way to execute Google-grounded searches is using the built-in `python_tool` with an appropriate timeout value. The `python_tool` provides a clean execution environment and proper timeout handling, which is crucial for grounded search queries that may take longer to complete.

Here's a complete implementation that can be executed directly using the `python_tool`:

```python
import requests
import json
import time

# Use an API key from a NON-BILLING project
API_KEY = "YOUR_NON_BILLING_PROJECT_API_KEY"  # Replace with actual key from .private/gcloud-notes.md

def gemini_grounded_request(prompt):
    """Execute a Google-grounded Gemini search request"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "tools": [
            {
                "google_search": {}
            }
        ]
    }

    # Implement retry logic with exponential backoff
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            print(f"Sending query: {prompt}")
            response = requests.post(url, headers=headers, data=json.dumps(data))

            if response.status_code == 200:
                return response.json()
            elif response.status_code in [429, 503]:
                # Rate limit or service overloaded
                print(f"Rate limit or service overload (attempt {attempt+1}/{max_retries}). Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}", "response": response.text}

        except Exception as e:
            print(f"Request exception (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            return {"error": str(e)}

    return {"error": "Maximum retries exceeded"}

def extract_text_response(response):
    """Extract just the text response from Gemini API response"""
    if "candidates" in response and len(response["candidates"]) > 0:
        if "content" in response["candidates"][0]:
            text_parts = [
                part["text"]
                for part in response["candidates"][0]["content"]["parts"]
                if "text" in part
            ]
            return "\n".join(text_parts)
    return "No response text found"

# Example usage - uncomment and modify as needed
# prompt = "What's the latest research on quantum computing?"
# response = gemini_grounded_request(prompt)
# text_response = extract_text_response(response)
# print("\n=== SEARCH RESULTS ===\n")
# print(text_response)
# print("\n=== END OF RESULTS ===\n")
```

### Critical Usage Notes

When using this script with the `python_tool`:

1. **Always specify an appropriate timeout**: Google-grounded searches can take 30-60+ seconds to complete
   ```python
   # Example with 120 second timeout - ALWAYS specify this for grounded searches
   python_tool(code="...", timeout_s=120)
   ```

2. **Use direct function calls instead of heredoc/EOF syntax**: The bash_tool with EOF syntax can become unstable with long-running commands, so using python_tool directly is preferred.

3. **Keep queries focused**: More specific queries tend to complete faster and provide more relevant results.

### Response Structure

A successful grounded response will include:
- The model's answer in `candidates[0].content.parts[0].text`
- Search metadata in `groundingMetadata`
- The web search queries used in `webSearchQueries`
- Sources for the information in `groundingChunks`

## Using Gemini for Large Context Processing

Gemini 2.5 Pro offers a massive 1M token context window, making it ideal for processing and analyzing large volumes of code, logs, and documentation in a single query. This capability can be leveraged even when your primary agent has more limited context.

### File-Based Context Aggregation

For comprehensive analysis of large codebases or complex problems:

1. **Collect context in a single file:**
   ```bash
   # Create or clear the prompt file
   echo "# ANALYSIS REQUEST" > /tmp/prompt.txt

   # Add relevant source files
   find /path/to/project -name "*.py" -type f | sort | while read file; do
     echo -e "\n## FILE: $file\n\`\`\`python" >> /tmp/prompt.txt
     cat -n "$file" >> /tmp/prompt.txt
     echo -e "\`\`\`\n" >> /tmp/prompt.txt
   done

   # Add your specific question
   cat >> /tmp/prompt.txt << 'QUESTION'

   Based on the above code, please analyze...
   QUESTION
   ```

2. **Submit to Gemini and save the response:**
   ```python
   # Using the Python API
   with open('/tmp/prompt.txt', 'r') as f:
       prompt_text = f.read()

   response = gemini_request(prompt_text)

   # Save the response to file
   with open('/tmp/gemini_analysis.md', 'w') as f:
       f.write(extract_text_response(response))
   ```

### Simulated Conversational Context

You can simulate a conversation with Gemini while maintaining the full context:

1. **Build a conversational chain:**
   ```python
   # After getting the initial response
   with open('/tmp/prompt.txt', 'r') as f:
       original_prompt = f.read()

   with open('/tmp/gemini_analysis.md', 'r') as f:
       first_response = f.read()

   # Create follow-up with full history
   follow_up = (
       original_prompt +
       "\n\n## GEMINI RESPONSE:\n\n" +
       first_response +
       "\n\n## FOLLOW-UP QUESTION:\n\n" +
       "Based on your analysis, can you explain in more detail..."
   )

   # Write to file and submit again
   with open('/tmp/prompt_followup.txt', 'w') as f:
       f.write(follow_up)

   # Submit the follow-up and save the new response
   with open('/tmp/prompt_followup.txt', 'r') as f:
       followup_text = f.read()

   response2 = gemini_request(followup_text)
   ```

This approach allows you to:
- Process extremely large contexts (up to ~700-800K tokens)
- Maintain full conversation history between queries
- Conduct deep analysis impossible with smaller context windows
- Effectively utilize Gemini's capabilities while staying within free quota limits

## Taking Initiative with Gemini

**You should use Gemini proactively whenever it would be helpful.** Do not wait for explicit instructions to leverage Gemini's capabilities. Consider Gemini as a tool at your disposal that you should use at your own discretion.

Examples of when to take initiative with Gemini:
- Analyzing large codebases or logs that exceed your context window
- Getting expert analysis of complex technical problems
- Processing and summarizing extensive documentation
- Running code reviews on large pull requests or features
- Exploring architectural alternatives for complex systems

Always use your `python_tool` to interact with Gemini when appropriate. You can create custom scripts to automate interactions or process results in ways that best serve your current task.

## When to Use Google-Grounded Search

**Use your initiative regarding Google-grounded Gemini searches.** If you're in ANY situation where doing a Google-grounded Gemini query would help, USE IT. Examples include:

- When you need up-to-date information that might not be in your training data
- When you need specific technical documentation
- When you need to verify facts or check current events
- When debugging issues with third-party libraries or frameworks
- When researching complex topics requiring multiple sources

Remember that each grounded request counts against the daily quota, so use this capability thoughtfully. However, don't hesitate to use it when it would genuinely help solve a problem or provide better assistance.

## Quota Management Strategy

When working on tasks that might require multiple Gemini calls:

1. Start with non-grounded requests when factual accuracy is less critical
2. Reserve grounded requests for when accuracy and up-to-date information is essential
3. If one API key's quota is exhausted, switch to another non-billing project API key
4. If all available API keys are exhausted, inform the human operator

## Future Considerations

As documented in `/parent/gemini/free/README.md`, there are ongoing experiments to better understand Gemini API limits and capabilities. The knowledge in this document will evolve as those experiments yield new insights.
