from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Schema for basic process health probe."""
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok"
            }
        }
    )
