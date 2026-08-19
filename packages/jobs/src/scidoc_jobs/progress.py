from pydantic import BaseModel, ConfigDict, Field


class JobProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    pages_completed: int
    pages_total: int
    progress: float = Field(ge=0, le=1)
    stage: str
