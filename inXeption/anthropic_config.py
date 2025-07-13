'''
Anthropic Model Configuration

This file contains all Anthropic-specific constants that may need updating
when new models are released or APIs are modified.

Last updated: 2025-07-13
Compatible with: Claude 4.0 Opus (2025-05-14)
'''

# Model Identifier - the model we're using
MODEL = 'claude-opus-4-20250514'  # Claude 4.0 Opus

# HTTP Headers
REQUIRED_HEADERS = {
    'anthropic-version': '2023-06-01',  # API version
    # 'anthropic-beta': '2024-01-01',  # Beta API version if different
}

# Beta Feature Flags
# Each flag has a boolean to indicate whether it should be used
BETA_FLAGS = {
    'computer-use-2025-01-24': False,  # Disabled - we're using our own tool definitions
    'prompt-caching-2024-07-31': False,  # Caching support
    'token-efficient-tools-2025-02-19': False,  # Not using as it conflicts with other features
}

# Model Constraints
MODEL_CONSTRAINTS = {
    'max_input_tokens': 200_000,  # Maximum context window size (same for Claude 3.7 and 4.0)
    'max_output_tokens': 32_000,  # Maximum tokens to generate per response (Claude 4.0 Opus)
    # Note: Claude 4.0 Sonnet supports 64,000 max output tokens
    # Note: Claude 3.7 Sonnet supported 128,000 max output tokens
    'default_output_tokens': 16_384,  # Default reasonable output size
}

# Thinking Capability
THINKING_TOKENS_BUDGET = 4096  # Default budget for thinking feature

# Rate Limits
RATE_LIMITS = {
    # TODO: wire in limits (per-minute, per-day, per-model, etc.)
}

# Token Pricing (USD per million tokens)
BASE_RATE = 15.0  # Claude 4.0 Opus is 5x more expensive than Claude 3.7 Sonnet

TOKEN_PRICING_USD_PER_MILLION = {
    'input_tokens': BASE_RATE * 1.0,  # Base rate for fresh input
    'cache_creation_input_tokens': BASE_RATE * 1.25,  # 25% premium for cache storage
    'cache_read_input_tokens': BASE_RATE * 0.1,  # 90% discount for cache hits
    'output_tokens': BASE_RATE * 5.0,  # 5x base rate for generated tokens
}

# Emoji mapping for token types in usage display
EMOJI_FOR_TOKEN_TYPE = {
    'input_tokens': '➕',
    'output_tokens': '🖋️',
    'cache_creation_input_tokens': '📀',
    'cache_read_input_tokens': '♻️',
}
