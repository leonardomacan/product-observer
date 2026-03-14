"""Rich-based logging configuration."""

import logging
import sys

from rich.logging import RichHandler


def configure_logging(verbose: bool = False) -> logging.Logger:
    """Configure project logging with Rich handler.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO.

    Returns:
        The configured project logger.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger to avoid duplicate handlers
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=verbose,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root.addHandler(handler)

    # Project logger
    logger = logging.getLogger("product_observer")
    logger.setLevel(level)

    return logger
