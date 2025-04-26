'''
Utilities for calculating and formatting statistics for LLM interactions.
'''

from inXeption.anthropic_config import EMOJI_FOR_TOKEN_TYPE, MODEL_CONSTRAINTS
from inXeption.llm import count_tokens


async def calculate_battery(prompts, tools, messages):
    '''Calculate battery percentage based on context window consumption'''
    current_token_count = await count_tokens(prompts, tools, messages)
    max_tokens = MODEL_CONSTRAINTS['max_input_tokens']
    return 100 - (current_token_count / max_tokens * 100)


def format_number(num):
    '''Format a number to human-readable format with k, M, etc.'''
    if num < 1000:
        return str(num)
    elif num < 1000000:
        return f'{num/1000:.1f}k'.replace('.0k', 'k')
    else:
        return f'{num/1000000:.1f}M'.replace('.0M', 'M')


def format_stats_lines(interaction, prev_battery=100.0):
    '''Format stats into lines for display'''
    all_lines = []

    # Add token usage data with a list comprehension
    token_types = [
        'input_tokens',
        'output_tokens',
        'cache_creation_input_tokens',
        'cache_read_input_tokens',
    ]
    all_lines.extend(
        [
            (
                EMOJI_FOR_TOKEN_TYPE[token_type],
                f'+{format_number(getattr(interaction.usage, token_type))}',
                f'{format_number(getattr(interaction.total_usage, token_type))}',
            )
            for token_type in token_types
        ]
    )

    # Add cost
    all_lines.append(
        (
            '💰',
            f'+${interaction.usage.dollar_cost:.2f}',
            f'${interaction.total_usage.dollar_cost:.2f}',
        )
    )

    # Add battery indicator with accurate delta
    battery_emoji = '🪫' if interaction.final_battery < 20 else '🔋'
    delta = interaction.final_battery - prev_battery
    all_lines.append(
        (battery_emoji, f'{delta:+.1f}%', f'{interaction.final_battery:.1f}%')
    )

    return all_lines


def format_stats_text(all_lines, elapsed_time, index=None):
    '''Format stats lines into display text'''
    max_delta_len = max(len(delta) for _, delta, _ in all_lines) if all_lines else 0
    usage_text = '\n'.join(
        f'{emoji} {delta.rjust(max_delta_len)}  {total}'
        for emoji, delta, total in all_lines
    )

    if index is not None:
        return f'Interaction {index} completed in {elapsed_time}\n\n{usage_text}'
    else:
        return f'Interaction completed in {elapsed_time}\n\n{usage_text}'
