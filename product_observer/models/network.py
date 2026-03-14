"""Network event models for captured API traffic."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NetworkEvent(BaseModel):
    """Captured network request/response event with enhanced metadata."""

    id: str = Field(..., description="Sequential id for deterministic filenames")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Full request URL")
    path: str = Field(..., description="URL path")
    status_code: Optional[int] = Field(default=None, description="HTTP response status")
    response_time_ms: Optional[float] = Field(default=None, description="Elapsed time from request to response (ms)")
    response_size_bytes: int = Field(default=0, description="Length of response body in bytes")
    resource_type: Optional[str] = Field(default=None, description="Playwright resource type (xhr, fetch, etc.)")
    request_body_preview: Optional[str] = Field(default=None, description="Truncated request body for debugging")
    response_saved_path: Optional[str] = Field(default=None, description="Path to saved response file")

    model_config = {"extra": "allow"}

    def to_metadata_dict(self) -> dict[str, Any]:
        """Export as dict suitable for JSON metadata (serializable)."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
            "url": self.url,
            "path": self.path,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "response_size_bytes": self.response_size_bytes,
            "resource_type": self.resource_type,
            "request_body_preview": self.request_body_preview,
            "response_saved_path": self.response_saved_path,
        }
