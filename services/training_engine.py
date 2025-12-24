from typing import Optional, Dict, Any
from models.step import Step
from models.session import SessionState
from models.evaluation import EvaluationResult
from services.session_manager import SessionManager
from services.content_provider import ContentProvider
from services.evaluation_service import EvaluationService
from services.llm_service import LLMService


class TrainingEngine:

    def __init__(
        self,
        session_manager: SessionManager,
        content_provider: ContentProvider,
        evaluation_service: EvaluationService,
        llm_service: LLMService,
    ):
        self.session_manager = session_manager
        self.content_provider = content_provider
        self.evaluation_service = evaluation_service
        self.llm_service = llm_service

    def start_module(self, user_id: str) -> SessionState:
        """
        Start Module 1 for a user (creates new session, deleting any existing one).

        Args:
            user_id: Unique identifier for the user

        Returns:
            New SessionState object initialized at step 1
        """
        existing_session = self.session_manager.get_session(user_id)
        if existing_session:
            self.session_manager.delete_session(user_id)

        session = self.session_manager.create_session(user_id)
        return session

    def get_current_step(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current step data for a user (main step or remediation).

        Args:
            user_id: Unique identifier for the user

        Returns:
            Dictionary with step data including type, question, and options.
            None if session doesn't exist.
        """
        session = self.session_manager.get_session(user_id)
        if not session:
            return None

        if session.in_remediation:
            return {
                "type": "remediation",
                "content": session.remediation_content,
                "question": session.remediation_question,
                "options": session.remediation_options,
                "correct_answer": session.remediation_correct_answer,
                "failure_count": session.failure_count,
                "original_step": session.original_step,
            }

        if session.completed:
            return {
                "type": "completed",
                "history": session.history,
                "completed_at": session.completed_at,
            }

        step = self.content_provider.get_step(session.current_step)
        if not step:
            return None

        return {"type": "step", "step": step, "failure_count": session.failure_count}

    def submit_answer(
        self, user_id: str, answer: str, is_remediation: bool = False
    ) -> Dict[str, Any]:
        session = self.session_manager.get_session(user_id)
        if not session:
            raise ValueError(f"No active session for user {user_id}")

        if session.completed:
            raise ValueError("Module already completed")

        if is_remediation:
            return self._handle_remediation_answer(user_id, session, answer)
        else:
            return self._handle_step_answer(user_id, session, answer)

    def _handle_step_answer(
        self, user_id: str, session: SessionState, answer: str
    ) -> Dict[str, Any]:
        step_id = session.current_step
        step = self.content_provider.get_step(step_id)

        if not step:
            raise ValueError(f"Step {step_id} not found")

        evaluation = self.evaluation_service.evaluate_answer(step_id, answer)

        session.add_answer(step_id, answer, evaluation.passed, evaluation.score)

        if evaluation.passed:
            return self._handle_pass(user_id, session, step, evaluation)
        else:
            return self._handle_failure(user_id, session, step, evaluation, answer)

    def _handle_remediation_answer(
        self, user_id: str, session: SessionState, answer: str
    ) -> Dict[str, Any]:
        if not session.in_remediation:
            raise ValueError("Not in remediation mode")

        answer_normalized = answer.strip().upper()

        if answer_normalized not in ["A", "B", "C", "D"]:
            return {
                "result": "invalid_answer",
                "message": "Please select one of the options (A, B, C, or D).",
            }

        is_correct = answer_normalized == session.remediation_correct_answer

        if is_correct:
            session.add_answer(
                session.original_step or session.current_step, answer, is_correct
            )

            session.exit_remediation()
            self.session_manager.update_session(
                user_id,
                in_remediation=session.in_remediation,
                remediation_content=session.remediation_content,
                remediation_question=session.remediation_question,
                remediation_options=session.remediation_options,
                remediation_correct_answer=session.remediation_correct_answer,
                current_step=session.current_step,
                original_step=session.original_step,
                failure_count=session.failure_count,
            )

            next_step = self.content_provider.get_step(session.current_step)

            return {
                "result": "remediation_passed",
                "message": (
                    "Good! You've understood the concept. "
                    "Now try the original question again."
                ),
                "next_step": next_step,
            }
        else:
            session.failure_count += 1
            session.add_answer(
                session.original_step or session.current_step, answer, False
            )

            if session.failure_count > 2:
                mini_lesson = self.llm_service.generate_mini_lesson(
                    self.content_provider.get_topic()
                )

                session.remediation_content = self._format_mini_lesson(mini_lesson)
                self.session_manager.update_session(
                    user_id,
                    failure_count=session.failure_count,
                    remediation_content=session.remediation_content,
                )

                return {
                    "result": "remediation_failed_multiple",
                    "message": "Let's review the core concepts.",
                    "mini_lesson": mini_lesson,
                    "formatted_content": session.remediation_content,
                }
            else:
                self.session_manager.update_session(
                    user_id, failure_count=session.failure_count
                )

                # Get the selected wrong option text for better feedback
                wrong_option = session.remediation_options.get(answer_normalized, "")

                return {
                    "result": "remediation_failed",
                    "message": f"Not quite. The option you selected doesn't best demonstrate the principle of balancing autonomy and accountability. Review the explanation above and try again.",
                    "selected_option": wrong_option,
                }

    def _handle_pass(
        self,
        user_id: str,
        session: SessionState,
        step: Step,
        evaluation: EvaluationResult,
    ) -> Dict[str, Any]:
        session.failure_count = 0

        if session.current_step >= 5:
            session.mark_completed()
            self.session_manager.update_session(
                user_id,
                completed=session.completed,
                completed_at=session.completed_at,
                failure_count=session.failure_count,
            )

            return {
                "result": "module_completed",
                "evaluation": evaluation,
                "message": (
                    "Congratulations! You've completed Module 1: "
                    "Autonomy vs Accountability."
                ),
                "history": session.history,
            }

        session.current_step += 1
        self.session_manager.update_session(
            user_id,
            current_step=session.current_step,
            failure_count=session.failure_count,
        )

        next_step = self.content_provider.get_step(session.current_step)

        result = {"result": "passed", "evaluation": evaluation, "next_step": next_step}

        if step.gold_response:
            result["gold_response"] = step.gold_response

        return result

    def _handle_failure(
        self,
        user_id: str,
        session: SessionState,
        step: Step,
        evaluation: EvaluationResult,
        user_answer: str,
    ) -> Dict[str, Any]:
        session.failure_count += 1

        if session.failure_count == 1:
            remediation = self.llm_service.generate_remediation(
                topic=self.content_provider.get_topic(),
                user_answer=user_answer,
                failure_reason=evaluation.feedback,
                failure_count=session.failure_count,
            )

            session.enter_remediation(
                content=remediation["explanation"],
                question=self._format_remediation_question(remediation),
                options=self._format_remediation_options(remediation),
                correct_answer=remediation["remedial_correct_answer"],
            )

            self.session_manager.update_session(
                user_id,
                failure_count=session.failure_count,
                in_remediation=session.in_remediation,
                remediation_content=session.remediation_content,
                remediation_question=session.remediation_question,
                remediation_options=session.remediation_options,
                remediation_correct_answer=session.remediation_correct_answer,
                original_step=session.original_step,
            )

            return {
                "result": "failed_first_attempt",
                "evaluation": evaluation,
                "remediation": {
                    "explanation": remediation["explanation"],
                    "scenario": remediation["remedial_scenario"],
                    "options": remediation["remedial_options"],
                    "hint": remediation["hint"],
                },
            }

        elif session.failure_count >= 2:
            mini_lesson = self.llm_service.generate_mini_lesson(
                self.content_provider.get_topic()
            )

            remediation = self.llm_service.generate_remediation(
                topic=self.content_provider.get_topic(),
                user_answer=user_answer,
                failure_reason=evaluation.feedback,
                failure_count=session.failure_count,
            )

            session.remediation_content = self._format_mini_lesson(mini_lesson)
            session.remediation_question = self._format_remediation_question(
                remediation
            )
            session.remediation_options = self._format_remediation_options(remediation)
            session.remediation_correct_answer = remediation["remedial_correct_answer"]

            self.session_manager.update_session(
                user_id,
                failure_count=session.failure_count,
                remediation_content=session.remediation_content,
                remediation_question=session.remediation_question,
                remediation_options=session.remediation_options,
                remediation_correct_answer=session.remediation_correct_answer,
            )

            return {
                "result": "failed_second_attempt",
                "evaluation": evaluation,
                "mini_lesson": mini_lesson,
                "remediation": {
                    "explanation": remediation["explanation"],
                    "scenario": remediation["remedial_scenario"],
                    "options": remediation["remedial_options"],
                    "hint": remediation["hint"],
                },
            }

        else:
            self.session_manager.update_session(
                user_id, failure_count=session.failure_count
            )

            return {"result": "failed", "evaluation": evaluation}

    def _format_remediation_question(self, remediation: Dict[str, Any]) -> str:
        """Format remediation scenario (without options - those are stored separately)"""
        return remediation["remedial_scenario"]

    def _format_remediation_options(
        self, remediation: Dict[str, Any]
    ) -> dict[str, str]:
        """Convert remedial_options list to dict with A, B, C, D keys"""
        import re

        def clean_option(option: str) -> str:
            """Remove any letter prefix (A., B., C., D.) from option text"""
            # Strip leading whitespace and letter prefixes like "A.", "A)", "A ", etc.
            # Pattern matches: letter A-D, optional punctuation (. or )), then whitespace
            cleaned = re.sub(
                r"^[A-D][.)]?\s+", "", option.strip(), flags=re.IGNORECASE
            )
            return cleaned.strip()

        return {
            chr(65 + i): clean_option(option)
            for i, option in enumerate(remediation["remedial_options"])
        }

    def _format_mini_lesson(self, mini_lesson: Dict[str, Any]) -> str:
        parts = [
            f"# {mini_lesson['lesson_title']}",
            "",
            "## Core Principle",
            mini_lesson["core_principle"],
            "",
            "## Examples",
        ]

        for i, example in enumerate(mini_lesson["examples"], 1):
            parts.extend(
                [
                    "",
                    f"### Example {i}: {example['situation']}",
                    f"**Wrong approach:** {example['wrong_approach']}",
                    f"**Right approach:** {example['right_approach']}",
                    f"**Why it works:** {example['why_it_works']}",
                ]
            )

        parts.extend(
            [
                "",
                "## Common Mistakes",
                *[f"- {mistake}" for mistake in mini_lesson["common_mistakes"]],
                "",
                "## Key Takeaway",
                mini_lesson["key_takeaway"],
            ]
        )

        return "\n".join(parts)

    def advance_to_next_step(self, user_id: str) -> Optional[Step]:
        """
        Advance user to the next step after passing current step.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Next Step object if available, None if session doesn't exist or complete
        """
        session = self.session_manager.get_session(user_id)
        if not session or session.completed:
            return None

        if session.current_step >= 5:
            return None

        session.current_step += 1
        session.failure_count = 0

        self.session_manager.update_session(
            user_id,
            current_step=session.current_step,
            failure_count=session.failure_count,
        )

        return self.content_provider.get_step(session.current_step)

    def get_session_state(self, user_id: str) -> Optional[SessionState]:
        """
        Retrieve the full session state for a user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            SessionState object if session exists, None otherwise
        """
        return self.session_manager.get_session(user_id)

    def reset_module(self, user_id: str) -> SessionState:
        """
        Reset the module for a user (delete old session, create new one).

        Args:
            user_id: Unique identifier for the user

        Returns:
            New SessionState object initialized at step 1
        """
        return self.start_module(user_id)
