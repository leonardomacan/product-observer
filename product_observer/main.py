#!/usr/bin/env python3
"""
Package entrypoint for Product Observer – domain-agnostic network capture.

This exists so that `python -m product_observer.main` works (the run orchestrator
invokes that module path), while keeping the original repo-level `main.py`
intact.
"""

import asyncio
import contextlib
import sys

from rich.console import Console

from product_observer.browser.controller import BrowserController
from product_observer.config import get_settings
from product_observer.logging_config import configure_logging
from product_observer.network.observer import NetworkObserver
from product_observer.storage.file_store import FileStorage

# Periodic reminder while capture is idle between API calls.
_PHASE1_HEARTBEAT_SECONDS = 30.0


async def _phase1_heartbeat(observer: NetworkObserver, console: Console) -> None:
    """Print capture status every N seconds so long quiet periods do not look stuck."""
    try:
        while True:
            await asyncio.sleep(_PHASE1_HEARTBEAT_SECONDS)
            n = observer.capture_count
            console.print(
                f"[dim]Phase 1 — still capturing ({n} API request(s) saved so far). "
                "Press Ctrl+C when finished.[/dim]"
            )
    except asyncio.CancelledError:
        raise


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
            f"Output directory: [cyan]{settings.output_dir}[/cyan]\n"
            "Log in and interact with the app. Matching API traffic is saved and logged below.\n"
            "Press [bold]Ctrl+C[/bold] in this terminal when you are done (then the parent run continues to Phase 2).\n"
        )

        heartbeat = asyncio.create_task(_phase1_heartbeat(observer, console))
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
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

