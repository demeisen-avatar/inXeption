'''
Anthropic Model Configuration

This file contains all Anthropic-specific constants that may need updating
when new models are released or APIs are modified.

Last updated: 2025-02-26
Compatible with: Claude 3.7 Sonnet (2025-02-19)
'''

# Model Identifier - the model we're using
MODEL = 'claude-3-7-sonnet-20250219'  # Latest model

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
    'max_input_tokens': 200_000,  # Maximum context window size
    'max_output_tokens': 128_000,  # Maximum tokens to generate per response (Claude 3.7)
    'default_output_tokens': 16_384,  # Default reasonable output size
}

# Thinking Capability
THINKING_TOKENS_BUDGET = 4096  # Default budget for thinking feature

# Rate Limits
RATE_LIMITS = {
    # TODO: wire in limits (per-minute, per-day, per-model, etc.)
}

# Token Pricing (USD per million tokens)
BASE_RATE = 3.0

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
