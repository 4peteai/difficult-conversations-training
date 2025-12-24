from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RubricDimensions(BaseModel):
    de_escalation: float = Field(
        ..., ge=0.0, le=2.0, description="Reduces threat (0-2)"
    )
    validation: float = Field(
        ..., ge=0.0, le=2.0, description="Acknowledges concern (0-2)"
    )
    clarity: float = Field(
        ..., ge=0.0, le=2.0, description="States what/when/why (0-2)"
    )
    autonomy: float = Field(
        ..., ge=0.0, le=2.0, description="Preserves ownership (0-2)"
    )
    next_step: float = Field(..., ge=0.0, le=2.0, description="Concrete action (0-2)")

    def total_score(self) -> float:
        return (
            self.de_escalation
            + self.validation
            + self.clarity
            + self.autonomy
            + self.next_step
        )


class EvaluationResult(BaseModel):
    passed: bool = Field(..., description="Whether the answer passed the evaluation")
    score: float = Field(..., ge=0.0, le=10.0, description="Overall score (0-10)")
    feedback: str = Field(..., description="Detailed feedback on the answer")
    dimensions: Optional[RubricDimensions] = Field(
        None, description="Breakdown by rubric dimensions (for free-form answers)"
    )
    threshold: float = Field(7.0, ge=0.0, le=10.0, description="Pass threshold used")

    @field_validator("passed", mode="before")
    @classmethod
    def validate_passed(cls, v, info):
        if isinstance(v, bool):
            return v
        score = info.data.get("score", 0)
        threshold = info.data.get("threshold", 7.0)
        return score >= threshold
