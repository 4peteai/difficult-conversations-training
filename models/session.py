from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AnswerRecord(BaseModel):
    step_id: int = Field(..., description="Step number")
    answer: str = Field(..., description="User's answer")
    correct: bool = Field(..., description="Whether the answer was correct")
    score: Optional[float] = Field(None, description="Score if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    current_step: int = Field(
        1, ge=0, le=5, description="Current step number (0 = not started, 1-5)"
    )
    failure_count: int = Field(
        0, ge=0, description="Number of consecutive failures on current step"
    )
    in_remediation: bool = Field(
        False, description="Whether user is currently in remediation"
    )
    remediation_content: Optional[str] = Field(
        None, description="LLM-generated remediation content"
    )
    remediation_question: Optional[str] = Field(
        None, description="LLM-generated remedial question"
    )
    remediation_options: Optional[dict[str, str]] = Field(
        None, description="Remedial question options (A, B, C, D)"
    )
    remediation_correct_answer: Optional[str] = Field(
        None, description="Correct answer letter for remedial question"
    )
    original_step: Optional[int] = Field(
        None, description="Original step before remediation started"
    )
    history: list[AnswerRecord] = Field(
        default_factory=list, description="History of all answers"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session start timestamp"
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )
    completed: bool = Field(False, description="Whether the module is completed")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    def update_activity(self) -> None:
        self.last_activity = datetime.utcnow()

    def add_answer(
        self, step_id: int, answer: str, correct: bool, score: Optional[float] = None
    ) -> None:
        record = AnswerRecord(
            step_id=step_id, answer=answer, correct=correct, score=score
        )
        self.history.append(record)
        self.update_activity()

    def mark_completed(self) -> None:
        self.completed = True
        self.completed_at = datetime.utcnow()
        self.update_activity()

    def enter_remediation(
        self,
        content: str,
        question: str,
        options: dict[str, str],
        correct_answer: str,
    ) -> None:
        self.in_remediation = True
        self.remediation_content = content
        self.remediation_question = question
        self.remediation_options = options
        self.remediation_correct_answer = correct_answer
        if self.original_step is None:
            self.original_step = self.current_step
        self.update_activity()

    def exit_remediation(self) -> None:
        self.in_remediation = False
        self.remediation_content = None
        self.remediation_question = None
        self.remediation_options = None
        self.remediation_correct_answer = None
        if self.original_step is not None:
            self.current_step = self.original_step
            self.original_step = None
        self.failure_count = 0
        self.update_activity()

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
