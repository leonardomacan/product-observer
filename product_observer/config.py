"""Configuration loading via Pydantic and python-dotenv."""

from pathlib import Path
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


def _resolve_path(value: Optional[str], default: str) -> Path:
    """Resolve a path string to an absolute Path."""
    if value is None or value.strip() == "":
        return Path(default).resolve()
    return Path(value).resolve()


class Settings(BaseModel):
    """Application settings loaded from environment."""

    target_url: str = Field(..., description="Base URL of the target web application to observe")
    output_dir: Path = Field(default_factory=lambda: Path("data/raw_requests").resolve())
    browser_profile_dir: Path = Field(default_factory=lambda: Path("./browser_profile").resolve())
    headless: bool = False
    delay_min_ms: int = Field(default=300, ge=0, description="Min delay before navigation (ms)")
    delay_max_ms: int = Field(default=1500, ge=0, description="Max delay before navigation (ms)")
    max_requests_per_session: Optional[int] = Field(default=None, description="Stop capturing after this many requests")
    filter_domain: bool = Field(default=True, description="Only capture requests from target host")
    compress_responses: bool = Field(default=False, description="Gzip large response bodies")
    large_response_threshold_bytes: int = Field(
        default=1_000_000,
        ge=0,
        description="Warn when response exceeds this size (bytes)",
    )

    model_config = {"extra": "ignore"}

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        load_dotenv()

        import os

        target_url = os.getenv("TARGET_URL", "")
        if not target_url:
            raise ValueError("TARGET_URL is required. Set it in .env or environment.")

        output_dir = _resolve_path(os.getenv("OUTPUT_DIR"), "data/raw_requests")
        browser_profile_dir = _resolve_path(os.getenv("BROWSER_PROFILE_DIR"), "./browser_profile")

        delay_min_ms = int(os.getenv("DELAY_MIN_MS", "300"))
        delay_max_ms = int(os.getenv("DELAY_MAX_MS", "1500"))

        max_raw = os.getenv("MAX_REQUESTS_PER_SESSION", "").strip()
        max_requests_per_session: Optional[int] = None
        if max_raw:
            max_requests_per_session = int(max_raw)

        filter_domain = os.getenv("FILTER_DOMAIN", "true").lower() in ("true", "1", "yes")
        compress_responses = os.getenv("COMPRESS_RESPONSES", "false").lower() in ("true", "1", "yes")
        large_response_threshold_bytes = int(os.getenv("LARGE_RESPONSE_THRESHOLD_BYTES", "1000000"))

        return cls(
            target_url=target_url,
            output_dir=output_dir,
            browser_profile_dir=browser_profile_dir,
            headless=os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes"),
            delay_min_ms=delay_min_ms,
            delay_max_ms=delay_max_ms,
            max_requests_per_session=max_requests_per_session,
            filter_domain=filter_domain,
            compress_responses=compress_responses,
            large_response_threshold_bytes=large_response_threshold_bytes,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings.from_env()
