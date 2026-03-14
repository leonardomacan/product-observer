"""Browser controller using Playwright persistent context."""

from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from product_observer.config import Settings
from product_observer.utils.delays import random_delay


class BrowserController:
    """Manages Playwright lifecycle with persistent context for session persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def context(self) -> Optional[BrowserContext]:
        """The browser context (available after start)."""
        return self._context

    @property
    def page(self) -> Optional[Page]:
        """The main page (available after start)."""
        return self._page

    async def start(self) -> None:
        """Launch Playwright with persistent context."""
        self._playwright = await async_playwright().start()

        profile_dir = Path(self._settings.browser_profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=self._settings.headless,
            viewport={"width": 1280, "height": 720},
        )

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def open_target(self) -> None:
        """Navigate to the target URL with human-like delay."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        await random_delay(
            self._settings.delay_min_ms,
            self._settings.delay_max_ms,
        )
        await self._page.goto(self._settings.target_url, wait_until="domcontentloaded")

    async def stop(self) -> None:
        """Close context and stop Playwright."""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
