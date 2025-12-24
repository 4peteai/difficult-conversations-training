from typing import Optional
from models.step import Step, StepType


class ContentProvider:
    """
    Provides all predefined content for Module 1: Autonomy vs Accountability.
    This class serves as the single source of truth for scenarios, correct answers,
    and gold responses.
    """

    def __init__(self):
        self._steps = self._initialize_steps()
        self._mini_lesson = self._initialize_mini_lesson()
        self._validate_content()

    def _initialize_steps(self) -> dict[int, Step]:
        """Initialize all 5 predefined steps for Module 1."""

        # STEP 1 — Recognition (Easy)
        step_1 = Step(
            id=1,
            type=StepType.RECOGNITION,
            scenario='Alex says:\n"Why do you keep checking on this? I\'ve got it under control."',
            options={
                "A": "I trust you. I'll stop asking.",
                "B": "Because last time it slipped.",
                "C": (
                    "I'm not doubting you. I need visibility to answer "
                    "stakeholders. A short weekly update would be enough."
                ),
                "D": "This is just how we work.",
            },
            correct_answer="C",
            gold_response=None,
            allow_free_form=False,
        )

        # STEP 2 — Recognition (Easy)
        step_2 = Step(
            id=2,
            type=StepType.RECOGNITION,
            scenario='Alex says:\n"It feels like you don\'t trust me."',
            options={
                "A": "That's not true. Don't take it personally.",
                "B": "Trust isn't the issue. Delivery is.",
                "C": (
                    "I trust your expertise. I still need a predictable way to "
                    "report progress. How would you prefer we do that?"
                ),
                "D": "Let's stay professional.",
            },
            correct_answer="C",
            gold_response=None,
            allow_free_form=False,
        )

        # STEP 3 — Recognition (Moderate)
        step_3 = Step(
            id=3,
            type=StepType.RECOGNITION,
            scenario=(
                "Alex says:\n"
                "\"You're changing requirements again. That's why things slow down.\""
            ),
            options={
                "A": "Priorities change. Deal with it.",
                "B": "You're overreacting.",
                "C": (
                    "What changed is the deadline, not the scope. I should've been "
                    "clearer. Given the new date, what adjustment makes sense to you?"
                ),
                "D": "Just do your best.",
            },
            correct_answer="C",
            gold_response=None,
            allow_free_form=False,
        )

        # STEP 4 — Transition
        step_4 = Step(
            id=4,
            type=StepType.TRANSITION,
            scenario='Alex says:\n"If you don\'t trust me, just say it."',
            options={
                "A": "I do trust you, relax.",
                "B": "This isn't about trust.",
                "C": "You're being defensive.",
                "D": "Let's keep emotions out of this.",
            },
            correct_answer=None,  # All options are wrong
            gold_response=(
                "I do trust how you work. What I'm accountable for is the outcome and timing. "
                "Let's agree on one clear checkpoint so I can cover that, and you keep ownership."
            ),
            allow_free_form=True,
            pass_threshold=7.0,
        )

        # STEP 5 — Production (Hard)
        step_5 = Step(
            id=5,
            type=StepType.PRODUCTION,
            scenario=(
                "Context: Deadline missed, escalation happened.\n\n"
                "Alex says:\n\"This keeps happening because I'm being "
                'micromanaged instead of trusted."'
            ),
            options=None,  # Free-form only
            correct_answer=None,
            gold_response=(
                "I hear that this feels controlling. I'm accountable for delivery and escalation, "
                "not for how you work day to day. We missed the date, so let's reset expectations "
                "and agree on one checkpoint going forward."
            ),
            allow_free_form=True,
            pass_threshold=7.0,
        )

        return {1: step_1, 2: step_2, 3: step_3, 4: step_4, 5: step_5}

    def _initialize_mini_lesson(self) -> dict[str, str]:
        """Initialize the mini-lesson content."""
        return {
            "principle": (
                "Autonomy lives in the *how*.\n"
                "Accountability lives in the *what and when*."
            ),
            "formula": (
                "1. Validate\n"
                "2. State constraint\n"
                "3. Offer choice\n"
                "4. Lock next step"
            ),
        }

    def _validate_content(self):
        """Validate that all required content exists and is properly structured."""
        # Verify we have all 5 steps
        if len(self._steps) != 5:
            raise ValueError(f"Expected 5 steps, but found {len(self._steps)}")

        # Verify step IDs are 1-5
        for step_id in range(1, 6):
            if step_id not in self._steps:
                raise ValueError(f"Missing step {step_id}")

        # Validate each step
        for step_id, step in self._steps.items():
            # Recognition steps (1-3) must have options and correct answer
            if step.type == StepType.RECOGNITION:
                if not step.options:
                    raise ValueError(
                        f"Step {step_id}: Recognition step missing options"
                    )
                if not step.correct_answer:
                    raise ValueError(
                        f"Step {step_id}: Recognition step missing correct answer"
                    )
                if step.correct_answer not in step.options:
                    raise ValueError(
                        f"Step {step_id}: Correct answer '{step.correct_answer}' not in options"
                    )

            # Steps 4-5 must have gold responses
            if step_id >= 4:
                if not step.gold_response:
                    raise ValueError(f"Step {step_id}: Missing gold response")
                if not step.allow_free_form:
                    raise ValueError(f"Step {step_id}: Must allow free-form answers")

        # Validate mini-lesson content
        if not self._mini_lesson.get("principle"):
            raise ValueError("Mini-lesson missing principle")
        if not self._mini_lesson.get("formula"):
            raise ValueError("Mini-lesson missing formula")

    def get_step(self, step_id: int) -> Optional[Step]:
        """
        Retrieve a step by ID.

        Args:
            step_id: The step number (1-5)

        Returns:
            Step object or None if not found
        """
        return self._steps.get(step_id)

    def get_correct_answer(self, step_id: int) -> Optional[str]:
        """
        Get the correct answer for a recognition step.

        Args:
            step_id: The step number (1-5)

        Returns:
            The correct option letter (A-D) or None if not applicable
        """
        step = self.get_step(step_id)
        return step.correct_answer if step else None

    def get_gold_response(self, step_id: int) -> Optional[str]:
        """
        Get the gold standard response for transition/production steps.

        Args:
            step_id: The step number (1-5)

        Returns:
            Gold response text or None if not applicable
        """
        step = self.get_step(step_id)
        return step.gold_response if step else None

    def get_mini_lesson(self) -> dict[str, str]:
        """
        Get the mini-lesson content.

        Returns:
            Dictionary with 'principle' and 'formula' keys
        """
        return self._mini_lesson.copy()

    def get_all_steps(self) -> dict[int, Step]:
        """
        Get all steps.

        Returns:
            Dictionary mapping step_id to Step objects
        """
        return self._steps.copy()

    def get_topic(self) -> str:
        """
        Get the module topic.

        Returns:
            Topic name
        """
        return "Autonomy vs Accountability"


# Singleton instance
_content_provider = None


def get_content_provider() -> ContentProvider:
    """Get the singleton ContentProvider instance."""
    global _content_provider
    if _content_provider is None:
        _content_provider = ContentProvider()
    return _content_provider
