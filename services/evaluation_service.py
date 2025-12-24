from models.evaluation import EvaluationResult
from models.step import Step, StepType
from services.content_provider import ContentProvider
from services.llm_service import LLMService


class EvaluationService:

    def __init__(self, content_provider: ContentProvider, llm_service: LLMService):
        self.content_provider = content_provider
        self.llm_service = llm_service

    def evaluate_answer(self, step_id: int, answer: str) -> EvaluationResult:
        step = self.content_provider.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")

        if step.type == StepType.RECOGNITION:
            return self._evaluate_recognition(step, answer)
        elif step.type in (StepType.TRANSITION, StepType.PRODUCTION):
            return self._evaluate_production(step, answer)
        else:
            raise ValueError(f"Unknown step type: {step.type}")

    def _evaluate_recognition(self, step: Step, answer: str) -> EvaluationResult:
        answer_normalized = answer.strip().upper()

        if answer_normalized == step.correct_answer:
            return EvaluationResult(
                passed=True,
                score=10.0,
                feedback=(
                    "Correct! This is the best response that balances "
                    "accountability with autonomy."
                ),
                dimensions=None,
                threshold=10.0,
            )
        else:
            if step.options and answer_normalized in step.options:
                wrong_option_text = step.options[answer_normalized]
                feedback = (
                    f"Incorrect. You selected: '{wrong_option_text}'. "
                    f"This approach doesn't effectively balance autonomy and accountability. "
                    f"Try again."
                )
            else:
                feedback = (
                    "Incorrect answer. Please select one of the provided options (A-D)."
                )

            return EvaluationResult(
                passed=False,
                score=0.0,
                feedback=feedback,
                dimensions=None,
                threshold=10.0,
            )

    def _evaluate_production(self, step: Step, answer: str) -> EvaluationResult:
        if step.options and answer.strip().upper() in step.options.keys():
            return EvaluationResult(
                passed=False,
                score=0.0,
                feedback=(
                    "You selected a predefined option, but none of them are "
                    "effective for this situation. "
                    "Please provide a free-form response that balances autonomy "
                    "and accountability."
                ),
                dimensions=None,
                threshold=step.pass_threshold,
            )

        if not answer or len(answer.strip()) < 10:
            return EvaluationResult(
                passed=False,
                score=0.0,
                feedback=(
                    "Your response is too short. Please provide a thoughtful, "
                    "complete response."
                ),
                dimensions=None,
                threshold=step.pass_threshold,
            )

        if not step.gold_response:
            raise ValueError(f"Step {step.id} missing gold response for evaluation")

        return self.llm_service.evaluate_free_form(
            user_answer=answer,
            scenario=step.scenario,
            gold_response=step.gold_response,
            step_id=step.id,
        )

    def get_rubric(self) -> dict[str, str]:
        return {
            "De-escalation": "Reduces threat (0-2)",
            "Validation": "Acknowledges concern (0-2)",
            "Clarity": "States what/when/why (0-2)",
            "Autonomy": "Preserves ownership (0-2)",
            "Next step": "Concrete action (0-2)",
        }

    def get_pass_threshold(self, step_id: int) -> float:
        step = self.content_provider.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        return step.pass_threshold
