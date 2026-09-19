"""Response schemas for the health endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Liveness payload returned by ``GET /health``.

    The shape is deliberately small and stable: the frontend and any uptime
    check may depend on it, so fields are added rather than renamed.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "community-intelligence-api",
            }
        }
    )

    status: str = Field(description="Service liveness indicator.", examples=["ok"])
    service: str = Field(
        description="Identifier of the service answering the request.",
        examples=["community-intelligence-api"],
    )
