from pydantic import BaseModel, Field


class Scenario(BaseModel):
    persona_name: str = Field(..., description="Name of the persona (e.g., 'Alex')")
    dialogue: str = Field(..., min_length=1, description="What the persona says")
    context: str = Field("", description="Additional context about the situation")
    difficulty: str = Field(
        "easy", pattern="^(easy|moderate|hard)$", description="Difficulty level"
    )

    def __str__(self) -> str:
        if self.context:
            return f'{self.persona_name} says:\n"{self.dialogue}"\n\nContext: {self.context}'
        return f'{self.persona_name} says:\n"{self.dialogue}"'
