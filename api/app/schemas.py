from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"]
    environment: str


class NotImplementedResponse(ApiModel):
    feature: str
    owner: str
    status: Literal["not_implemented"] = "not_implemented"
