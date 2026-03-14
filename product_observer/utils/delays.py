"""Human-like delay utilities."""

import asyncio
import random


async def random_delay(min_ms: int, max_ms: int) -> None:
    """Sleep for a random duration within the given range.

    Used to simulate human browsing behavior and avoid burst traffic
    that could stress the target application.

    Args:
        min_ms: Minimum delay in milliseconds.
        max_ms: Maximum delay in milliseconds.
    """
    delay_ms = random.uniform(min_ms, max_ms)
    await asyncio.sleep(delay_ms / 1000.0)
