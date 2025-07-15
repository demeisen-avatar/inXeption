'''
Represents token usage and cost statistics for LLM interactions.
'''

import logging

from pydantic import BaseModel

from inXeption.anthropic_config import (
    SONNET_TO_OPUS_PRICE_MULTIPLIER,
    TOKEN_PRICING_USD_PER_MILLION,
)

logger = logging.getLogger(__name__)


class Usage(BaseModel):
    '''Encapsulates token usage and cost statistics with proper operator overloading'''

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    dollar_cost: float = 0.0
    model: str = 'sonnet'  # Track which model was used

    def __add__(self, other):
        '''Add two Usage objects together'''
        # When adding, we lose model specificity - mark as 'mixed'
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens
            + other.cache_read_input_tokens,
            dollar_cost=self.dollar_cost + other.dollar_cost,
            model='mixed' if self.model != other.model else self.model,
        )

    def __iadd__(self, other):
        '''In-place addition for Usage objects'''
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens
        self.dollar_cost += other.dollar_cost
        if self.model != other.model:
            self.model = 'mixed'
        return self

    @classmethod
    def from_dict(cls, usage_dict, model='sonnet'):
        '''Create a Usage object from a dictionary of usage data'''
        if not usage_dict:
            return cls(model=model)  # Return zero-usage if None or empty

        # Apply multiplier for opus pricing
        price_multiplier = SONNET_TO_OPUS_PRICE_MULTIPLIER if model == 'opus' else 1.0

        return cls(
            **usage_dict,
            model=model,
            dollar_cost=sum(
                TOKEN_PRICING_USD_PER_MILLION[k] * v / 1e6 * price_multiplier
                for k, v in usage_dict.items()
                if k in TOKEN_PRICING_USD_PER_MILLION
            ),
        )
