import pytest
from unittest.mock import Mock, MagicMock, patch
from services.training_engine import TrainingEngine
from services.session_manager import SessionManager
from services.content_provider import ContentProvider, get_content_provider
from services.evaluation_service import EvaluationService
from services.llm_service import LLMService
from models.step import Step, StepType
from models.session import SessionState
from models.evaluation import EvaluationResult, RubricDimensions


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def content_provider():
    return get_content_provider()


@pytest.fixture
def mock_llm_service():
    return Mock(spec=LLMService)


@pytest.fixture
def evaluation_service(content_provider, mock_llm_service):
    return EvaluationService(content_provider, mock_llm_service)


@pytest.fixture
def training_engine(
    session_manager, content_provider, evaluation_service, mock_llm_service
):
    return TrainingEngine(
        session_manager=session_manager,
        content_provider=content_provider,
        evaluation_service=evaluation_service,
        llm_service=mock_llm_service,
    )


class TestStartModule:
    def test_start_module_creates_new_session(self, training_engine, session_manager):
        user_id = "test_user_1"

        session = training_engine.start_module(user_id)

        assert session is not None
        assert session.user_id == user_id
        assert session.current_step == 1
        assert session.failure_count == 0
        assert session.in_remediation == False
        assert session.completed == False

    def test_start_module_replaces_existing_session(
        self, training_engine, session_manager
    ):
        user_id = "test_user_2"

        session1 = training_engine.start_module(user_id)
        session_manager.update_session(user_id, current_step=3)

        session2 = training_engine.start_module(user_id)

        assert session2.current_step == 1
        assert session2.user_id == user_id


class TestGetCurrentStep:
    def test_get_current_step_returns_step_data(self, training_engine):
        user_id = "test_user_3"
        training_engine.start_module(user_id)

        current = training_engine.get_current_step(user_id)

        assert current is not None
        assert current["type"] == "step"
        assert current["step"].id == 1
        assert current["failure_count"] == 0

    def test_get_current_step_returns_none_for_nonexistent_user(self, training_engine):
        current = training_engine.get_current_step("nonexistent_user")

        assert current is None

    def test_get_current_step_returns_remediation_data(
        self, training_engine, session_manager
    ):
        user_id = "test_user_4"
        session = training_engine.start_module(user_id)

        test_options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
        session.enter_remediation(
            "Explanation here",
            "Question here",
            test_options,
            "A",
        )
        session_manager.update_session(
            user_id,
            in_remediation=True,
            remediation_content="Explanation here",
            remediation_question="Question here",
            remediation_options=test_options,
            remediation_correct_answer="A",
            original_step=1,
        )

        current = training_engine.get_current_step(user_id)

        assert current["type"] == "remediation"
        assert current["content"] == "Explanation here"
        assert current["question"] == "Question here"
        assert current["options"] == test_options
        assert current["correct_answer"] == "A"

    def test_get_current_step_returns_completed_data(
        self, training_engine, session_manager
    ):
        user_id = "test_user_5"
        session = training_engine.start_module(user_id)

        session.mark_completed()
        session_manager.update_session(
            user_id, completed=True, completed_at=session.completed_at
        )

        current = training_engine.get_current_step(user_id)

        assert current["type"] == "completed"
        assert current["completed_at"] is not None


class TestSubmitAnswerRecognitionSteps:
    def test_submit_correct_answer_step_1(self, training_engine):
        user_id = "test_user_6"
        training_engine.start_module(user_id)

        result = training_engine.submit_answer(user_id, "C")

        assert result["result"] == "passed"
        assert result["evaluation"].passed == True
        assert result["next_step"].id == 2

    def test_submit_incorrect_answer_step_1_triggers_remediation(
        self, training_engine, mock_llm_service
    ):
        user_id = "test_user_7"
        training_engine.start_module(user_id)

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Here's why that didn't work...",
            "remedial_scenario": "Alex says something",
            "remedial_options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "remedial_correct_answer": "C",
            "hint": "Think about autonomy",
        }

        result = training_engine.submit_answer(user_id, "A")

        assert result["result"] == "failed_first_attempt"
        assert result["evaluation"].passed == False
        assert "remediation" in result
        assert mock_llm_service.generate_remediation.called

    def test_all_recognition_steps_advance_on_correct_answer(
        self, training_engine, session_manager
    ):
        user_id = "test_user_8"
        training_engine.start_module(user_id)

        result1 = training_engine.submit_answer(user_id, "C")
        assert result1["result"] == "passed"
        assert result1["next_step"].id == 2

        result2 = training_engine.submit_answer(user_id, "C")
        assert result2["result"] == "passed"
        assert result2["next_step"].id == 3

        result3 = training_engine.submit_answer(user_id, "C")
        assert result3["result"] == "passed"
        assert result3["next_step"].id == 4


class TestSubmitAnswerTransitionStep:
    def test_step_4_selecting_option_fails(self, training_engine, session_manager):
        user_id = "test_user_9"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=4)

        mock_llm_service = training_engine.llm_service
        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Options don't work here",
            "remedial_scenario": "Try again",
            "remedial_options": ["Opt 1", "Opt 2", "Opt 3", "Opt 4"],
            "remedial_correct_answer": "B",
            "hint": "Use free-form",
        }

        result = training_engine.submit_answer(user_id, "A")

        assert result["evaluation"].passed == False

    def test_step_4_free_form_evaluated_by_llm(
        self, training_engine, session_manager, mock_llm_service
    ):
        user_id = "test_user_10"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=4)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Great response!",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=1.5,
                clarity=1.5,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "I trust how you work. Let's agree on checkpoints."
        )

        assert result["result"] == "passed"
        assert result["evaluation"].score == 8.0
        assert "gold_response" in result


class TestSubmitAnswerProductionStep:
    def test_step_5_passing_free_form_completes_module(
        self, training_engine, session_manager, mock_llm_service
    ):
        user_id = "test_user_11"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=5)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=9.0,
            feedback="Excellent!",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=2.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "I hear that this feels controlling. Let's reset expectations."
        )

        assert result["result"] == "module_completed"
        assert result["evaluation"].passed == True

        session = training_engine.get_session_state(user_id)
        assert session.completed == True

    def test_step_5_failing_triggers_remediation(
        self, training_engine, session_manager, mock_llm_service
    ):
        user_id = "test_user_12"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=5)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=False,
            score=4.0,
            feedback="Missing key elements",
            dimensions=RubricDimensions(
                de_escalation=1.0,
                validation=1.0,
                clarity=1.0,
                autonomy=0.5,
                next_step=0.5,
            ),
            threshold=7.0,
        )

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Your answer lacked validation",
            "remedial_scenario": "Simpler scenario",
            "remedial_options": ["A1", "A2", "A3", "A4"],
            "remedial_correct_answer": "D",
            "hint": "Focus on validation",
        }

        result = training_engine.submit_answer(user_id, "Just do better next time")

        assert result["result"] == "failed_first_attempt"
        assert result["evaluation"].passed == False


class TestRemediationFlow:
    def test_first_failure_generates_simple_remediation(
        self, training_engine, mock_llm_service
    ):
        user_id = "test_user_13"
        training_engine.start_module(user_id)

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "The issue is...",
            "remedial_scenario": "Alex says...",
            "remedial_options": ["Opt A", "Opt B", "Opt C", "Opt D"],
            "remedial_correct_answer": "B",
            "hint": "Think about clarity",
        }

        result = training_engine.submit_answer(user_id, "A")

        assert result["result"] == "failed_first_attempt"
        assert mock_llm_service.generate_remediation.call_count == 1
        assert mock_llm_service.generate_mini_lesson.call_count == 0

        session = training_engine.get_session_state(user_id)
        assert session.in_remediation == True
        assert session.failure_count == 1

    def test_second_failure_generates_mini_lesson(
        self, training_engine, mock_llm_service, session_manager
    ):
        user_id = "test_user_14"
        training_engine.start_module(user_id)

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Still not quite right",
            "remedial_scenario": "Another scenario",
            "remedial_options": ["O1", "O2", "O3", "O4"],
            "remedial_correct_answer": "A",
            "hint": "Remember the formula",
        }

        mock_llm_service.generate_mini_lesson.return_value = {
            "lesson_title": "Understanding Autonomy",
            "core_principle": "Autonomy in how, accountability in what/when",
            "examples": [
                {
                    "situation": "Deadline pressure",
                    "wrong_approach": "Micromanaging",
                    "right_approach": "Clear checkpoints",
                    "why_it_works": "Preserves ownership",
                }
            ],
            "common_mistakes": ["Being too vague", "Being too controlling"],
            "key_takeaway": "Balance is key",
        }

        training_engine.submit_answer(user_id, "A")

        session_manager.update_session(user_id, failure_count=1)

        result = training_engine.submit_answer(user_id, "B")

        assert result["result"] == "failed_second_attempt"
        assert mock_llm_service.generate_mini_lesson.called
        assert "mini_lesson" in result

    def test_passing_remediation_returns_to_original_step(
        self, training_engine, mock_llm_service, session_manager
    ):
        user_id = "test_user_15"
        session = training_engine.start_module(user_id)

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Try this",
            "remedial_scenario": "Scenario",
            "remedial_options": ["O1", "O2", "O3", "O4"],
            "remedial_correct_answer": "C",
            "hint": "Hint",
        }

        training_engine.submit_answer(user_id, "A")

        session = training_engine.get_session_state(user_id)
        assert session.in_remediation == True
        original_step = session.original_step

        result = training_engine.submit_answer(user_id, "C", is_remediation=True)

        assert result["result"] == "remediation_passed"

        session = training_engine.get_session_state(user_id)
        assert session.in_remediation == False
        assert session.current_step == original_step
        assert session.failure_count == 0


class TestFullModuleFlow:
    def test_complete_module_all_correct_answers(
        self, training_engine, mock_llm_service
    ):
        user_id = "test_user_16"
        training_engine.start_module(user_id)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=1.5,
                clarity=1.5,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result1 = training_engine.submit_answer(user_id, "C")
        assert result1["result"] == "passed"

        result2 = training_engine.submit_answer(user_id, "C")
        assert result2["result"] == "passed"

        result3 = training_engine.submit_answer(user_id, "C")
        assert result3["result"] == "passed"

        result4 = training_engine.submit_answer(user_id, "Good free-form response")
        assert result4["result"] == "passed"

        result5 = training_engine.submit_answer(user_id, "Another good response")
        assert result5["result"] == "module_completed"

        session = training_engine.get_session_state(user_id)
        assert session.completed == True
        assert len(session.history) == 5

    def test_complete_module_with_one_remediation(
        self, training_engine, mock_llm_service
    ):
        user_id = "test_user_17"
        training_engine.start_module(user_id)

        mock_llm_service.generate_remediation.return_value = {
            "explanation": "Not quite",
            "remedial_scenario": "Try again",
            "remedial_options": ["A", "B", "C", "D"],
            "remedial_correct_answer": "B",
            "hint": "Hint",
        }

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=1.5,
                clarity=1.5,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result1 = training_engine.submit_answer(user_id, "A")
        assert result1["result"] == "failed_first_attempt"

        remediation_result = training_engine.submit_answer(
            user_id, "B", is_remediation=True
        )
        assert remediation_result["result"] == "remediation_passed"

        result1_retry = training_engine.submit_answer(user_id, "C")
        assert result1_retry["result"] == "passed"

        result2 = training_engine.submit_answer(user_id, "C")
        assert result2["result"] == "passed"

        result3 = training_engine.submit_answer(user_id, "C")
        assert result3["result"] == "passed"

        result4 = training_engine.submit_answer(user_id, "Good answer")
        assert result4["result"] == "passed"

        result5 = training_engine.submit_answer(user_id, "Final answer")
        assert result5["result"] == "module_completed"


class TestEdgeCases:
    def test_cannot_submit_answer_without_session(self, training_engine):
        with pytest.raises(ValueError, match="No active session"):
            training_engine.submit_answer("nonexistent_user", "C")

    def test_cannot_submit_answer_after_completion(
        self, training_engine, session_manager
    ):
        user_id = "test_user_18"
        session = training_engine.start_module(user_id)

        session.mark_completed()
        session_manager.update_session(
            user_id, completed=True, completed_at=session.completed_at
        )

        with pytest.raises(ValueError, match="already completed"):
            training_engine.submit_answer(user_id, "C")

    def test_advance_to_next_step_manual(self, training_engine):
        user_id = "test_user_19"
        training_engine.start_module(user_id)

        next_step = training_engine.advance_to_next_step(user_id)

        assert next_step is not None
        assert next_step.id == 2

        session = training_engine.get_session_state(user_id)
        assert session.current_step == 2
        assert session.failure_count == 0

    def test_advance_past_step_5_returns_none(self, training_engine, session_manager):
        user_id = "test_user_20"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=5)

        next_step = training_engine.advance_to_next_step(user_id)

        assert next_step is None

    def test_reset_module_clears_progress(self, training_engine, session_manager):
        user_id = "test_user_21"
        training_engine.start_module(user_id)

        session_manager.update_session(user_id, current_step=3, failure_count=2)

        new_session = training_engine.reset_module(user_id)

        assert new_session.current_step == 1
        assert new_session.failure_count == 0
        assert len(new_session.history) == 0
