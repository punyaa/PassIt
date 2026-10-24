from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"]
    environment: str


class NotImplementedResponse(ApiModel):
    feature: str
    owner: str
    status: Literal["not_implemented"] = "not_implemented"


class DateWindow(ApiModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ordered(self) -> "DateWindow":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self
