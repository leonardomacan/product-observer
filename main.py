#!/usr/bin/env python3
"""Entry point for Product Observer – domain-agnostic network capture."""

import asyncio
import logging
import sys

from rich.console import Console

from product_observer.browser.controller import BrowserController
from product_observer.config import get_settings
from product_observer.logging_config import configure_logging
from product_observer.network.observer import NetworkObserver
from product_observer.storage.file_store import FileStorage


async def _run() -> None:
    """Main async entry point."""
    settings = get_settings()
    logger = configure_logging()

    storage = FileStorage(
        base_dir=settings.output_dir,
        compress=settings.compress_responses,
    )

    browser = BrowserController(settings)
    observer = NetworkObserver(storage=storage, settings=settings, logger=logger)

    try:
        await browser.start()
        observer.attach(browser.context)
        await browser.open_target()

        console = Console()
        console.print(
            "\n[bold green]Product Observer – Network capture[/bold green]\n"
            "Log in and interact with the app. API traffic will be captured.\n"
            "Press [bold]Ctrl+C[/bold] to stop.\n"
        )

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await browser.stop()


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(_run())
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
