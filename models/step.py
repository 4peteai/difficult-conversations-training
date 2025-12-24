from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StepType(str, Enum):
    RECOGNITION = "recognition"
    TRANSITION = "transition"
    PRODUCTION = "production"


class Step(BaseModel):
    id: int = Field(..., ge=1, le=5, description="Step number (1-5)")
    type: StepType = Field(
        ..., description="Step type: recognition, transition, or production"
    )
    scenario: str = Field(
        ..., min_length=1, description="The scenario text presented to the user"
    )
    options: Optional[dict[str, str]] = Field(
        None, description="Multiple choice options (A-D). None if free-form only"
    )
    correct_answer: Optional[str] = Field(
        None, description="The correct option letter (A-D) for recognition steps"
    )
    gold_response: Optional[str] = Field(
        None, description="Gold standard response for transition/production steps"
    )
    allow_free_form: bool = Field(
        False, description="Whether free-form answers are allowed"
    )
    pass_threshold: float = Field(
        7.0, ge=0.0, le=10.0, description="Minimum score to pass (for production steps)"
    )

    class Config:
        use_enum_values = True
