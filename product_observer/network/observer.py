"""Network observer for capturing API traffic."""

import logging
import time
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Request, Response

from product_observer.config import Settings
from product_observer.models.network import NetworkEvent
from product_observer.storage.file_store import FileStorage


# Blocklist patterns for noise endpoints (analytics, telemetry, static assets)
NOISE_PATTERNS = (
    "analytics",
    "telemetry",
    "monitoring",
    "beacon",
    "gtm",
    "ga.js",
    "googletagmanager",
    "/static",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
)


class NetworkObserver:
    """Observes and captures API-like network traffic."""

    def __init__(
        self,
        storage: FileStorage,
        settings: Settings,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._storage = storage
        self._settings = settings
        self._logger = logger or logging.getLogger("product_observer")
        self._request_times: dict[int, float] = {}
        self._capture_count = 0
        self._limit_reached = False

    @property
    def capture_count(self) -> int:
        """Number of API responses saved this session (for Phase 1 progress)."""
        return self._capture_count

    def _is_api_call(self, request: Request) -> bool:
        """Determine if the request is likely an API call."""
        url = request.url
        resource_type = request.resource_type or ""

        # Resource type filter
        if resource_type in ("xhr", "fetch"):
            pass
        elif "/api/" in url:
            pass
        else:
            return False

        # Domain filter: only target host
        if self._settings.filter_domain:
            target_host = urlparse(self._settings.target_url).netloc
            request_host = urlparse(url).netloc
            if target_host and request_host and target_host != request_host:
                return False

        # Blocklist: exclude noise
        url_lower = url.lower()
        for pattern in NOISE_PATTERNS:
            if pattern in url_lower:
                return False

        return True

    def _record_request(self, request: Request) -> None:
        """Record request start time for response-time calculation."""
        if self._is_api_call(request):
            self._request_times[id(request)] = time.perf_counter()

    async def _handle_response(self, response: Response) -> None:
        """Process a response: capture if API-like, save, and log."""
        if self._limit_reached:
            return

        request = response.request
        if not self._is_api_call(request):
            return

        # Volume limit check
        if self._settings.max_requests_per_session is not None:
            if self._capture_count >= self._settings.max_requests_per_session:
                if self._capture_count == self._settings.max_requests_per_session:
                    self._limit_reached = True
                    self._logger.warning(
                        "Request limit reached (%d). Stopping capture.",
                        self._settings.max_requests_per_session,
                    )
                return

        # Response time
        response_time_ms: float | None = None
        req_id = id(request)
        if req_id in self._request_times:
            elapsed = (time.perf_counter() - self._request_times[req_id]) * 1000
            response_time_ms = round(elapsed, 2)
            del self._request_times[req_id]

        try:
            body = await response.body()
        except Exception as e:
            self._logger.warning("Failed to read response body for %s: %s", request.url, e)
            return

        size = len(body)
        parsed = urlparse(request.url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        self._capture_count += 1
        event_id = f"{self._capture_count:03d}"

        event = NetworkEvent(
            id=event_id,
            timestamp=datetime.utcnow(),
            method=request.method,
            url=request.url,
            path=path,
            status_code=response.status,
            response_time_ms=response_time_ms,
            response_size_bytes=size,
            resource_type=request.resource_type,
        )

        filepath = self._storage.save_event(event, body)
        event.response_saved_path = str(filepath)

        # Structured logging
        status = event.status_code or 0
        size_kb = size / 1024
        msg = f"{event.method} {path} -> {status} ({size_kb:.1f} KB) [saved to {filepath.name}]"

        if status >= 400:
            self._logger.warning("Failed request: %s", msg)
        elif size > self._settings.large_response_threshold_bytes:
            self._logger.warning("Large response: %s", msg)
        else:
            self._logger.info(msg)

    def attach(self, context: BrowserContext) -> None:
        """Register request/response handlers on the browser context."""
        context.on("request", self._record_request)
        context.on("response", self._handle_response)
