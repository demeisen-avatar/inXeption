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

    # Check if we have per-model usage (new format) or just combined usage (old format)
    has_per_model = hasattr(interaction, 'sonnet_usage') and hasattr(
        interaction, 'opus_usage'
    )

    if has_per_model:
        # Add token usage data with both sonnet and opus columns
        token_types = [
            'input_tokens',
            'output_tokens',
            'cache_creation_input_tokens',
            'cache_read_input_tokens',
        ]

        for token_type in token_types:
            sonnet_val = getattr(interaction.sonnet_usage, token_type, 0)
            opus_val = getattr(interaction.opus_usage, token_type, 0)
            total_sonnet = getattr(interaction.total_sonnet_usage, token_type, 0)
            total_opus = getattr(interaction.total_opus_usage, token_type, 0)

            # Format: emoji [+sonnet, +opus] [total_sonnet, total_opus]
            delta_str = f'[+{format_number(sonnet_val)}, +{format_number(opus_val)}]'
            total_str = f'[{format_number(total_sonnet)}, {format_number(total_opus)}]'

            all_lines.append((EMOJI_FOR_TOKEN_TYPE[token_type], delta_str, total_str))

        # Add cost line with combined format
        sonnet_cost = interaction.sonnet_usage.dollar_cost
        opus_cost = interaction.opus_usage.dollar_cost
        total_sonnet_cost = interaction.total_sonnet_usage.dollar_cost
        total_opus_cost = interaction.total_opus_usage.dollar_cost
        total_cost = interaction.total_usage.dollar_cost

        delta_cost_str = f'[+${sonnet_cost:.2f}, +${opus_cost:.2f}]'
        total_cost_str = (
            f'[${total_sonnet_cost:.2f}, ${total_opus_cost:.2f}]  ${total_cost:.2f}'
        )
        all_lines.append(('💰', delta_cost_str, total_cost_str))

    else:
        # Old format for backward compatibility
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
