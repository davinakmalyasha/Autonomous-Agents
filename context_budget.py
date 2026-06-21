"""
Context Budget Management.
Provides token estimation and context budget calculations to prevent context window overflow.
"""
from typing import NamedTuple

class ContextBudget(NamedTuple):
    model_limit: int       # e.g. 1000000 for deepseek-v4
    reserved_output: int   # max_tokens for response
    system_tokens: int     # system prompt tokens
    dynamic_tokens: int    # dynamic context tokens
    history_tokens: int    # current message history tokens

    @property
    def available_for_history(self) -> int:
        return self.model_limit - self.reserved_output - self.system_tokens - self.dynamic_tokens

    @property
    def utilization(self) -> float:
        return self.history_tokens / max(self.available_for_history, 1)

    @property
    def needs_compaction(self) -> bool:
        # Compact when message history consumes > 75% of available space
        return self.utilization > 0.75


def estimate_tokens(text: str) -> int:
    """Fast heuristic: DeepSeek averages ~3.5 chars per token for mixed code/text."""
    if not text:
        return 0
    return max(1, len(text) // 3)
