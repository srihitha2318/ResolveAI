from typing import Optional
from pydantic import BaseModel, ConfigDict


class StatusResponse(BaseModel):
    """Schema for detailed application and subsystem status response."""
    app_name: str
    version: str
    environment: str
    database: str
    message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "app_name": "ResolveAI",
                "version": "0.1.0",
                "environment": "development",
                "database": "connected",
                "message": "All subsystems operational"
            }
        }
    )
