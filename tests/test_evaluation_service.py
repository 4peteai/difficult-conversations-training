import pytest
from unittest.mock import Mock, MagicMock
from services.evaluation_service import EvaluationService
from services.content_provider import ContentProvider
from services.llm_service import LLMService
from models.evaluation import EvaluationResult, RubricDimensions
from models.step import Step, StepType


class TestEvaluationService:

    @pytest.fixture
    def content_provider(self):
        return ContentProvider()

    @pytest.fixture
    def mock_llm_service(self):
        return Mock(spec=LLMService)

    @pytest.fixture
    def evaluation_service(self, content_provider, mock_llm_service):
        return EvaluationService(content_provider, mock_llm_service)

    def test_initialization(self, evaluation_service):
        assert evaluation_service is not None
        assert evaluation_service.content_provider is not None
        assert evaluation_service.llm_service is not None

    def test_evaluate_invalid_step(self, evaluation_service):
        with pytest.raises(ValueError, match="Step 99 not found"):
            evaluation_service.evaluate_answer(99, "Some answer")

    def test_evaluate_recognition_step_correct_answer(self, evaluation_service):
        result = evaluation_service.evaluate_answer(1, "C")

        assert result.passed is True
        assert result.score == 10.0
        assert "Correct" in result.feedback
        assert result.dimensions is None

    def test_evaluate_recognition_step_correct_answer_lowercase(
        self, evaluation_service
    ):
        result = evaluation_service.evaluate_answer(1, "c")

        assert result.passed is True
        assert result.score == 10.0

    def test_evaluate_recognition_step_correct_answer_with_whitespace(
        self, evaluation_service
    ):
        result = evaluation_service.evaluate_answer(1, "  C  ")

        assert result.passed is True
        assert result.score == 10.0

    def test_evaluate_recognition_step_incorrect_answer(self, evaluation_service):
        result = evaluation_service.evaluate_answer(1, "A")

        assert result.passed is False
        assert result.score == 0.0
        assert "Incorrect" in result.feedback
        assert result.dimensions is None

    def test_evaluate_recognition_step_invalid_option(self, evaluation_service):
        result = evaluation_service.evaluate_answer(1, "Z")

        assert result.passed is False
        assert result.score == 0.0
        assert "select one of the provided options" in result.feedback

    def test_evaluate_all_recognition_steps(self, evaluation_service):
        for step_id in range(1, 4):
            result = evaluation_service.evaluate_answer(step_id, "C")
            assert result.passed is True
            assert result.score == 10.0

    def test_evaluate_transition_step_with_predefined_option(self, evaluation_service):
        result = evaluation_service.evaluate_answer(4, "A")

        assert result.passed is False
        assert result.score == 0.0
        assert "predefined option" in result.feedback
        assert "free-form response" in result.feedback

    def test_evaluate_production_step_too_short(self, evaluation_service):
        result = evaluation_service.evaluate_answer(5, "Ok")

        assert result.passed is False
        assert result.score == 0.0
        assert "too short" in result.feedback

    def test_evaluate_production_step_empty(self, evaluation_service):
        result = evaluation_service.evaluate_answer(5, "")

        assert result.passed is False
        assert result.score == 0.0

    def test_evaluate_production_step_good_answer(
        self, evaluation_service, mock_llm_service
    ):
        dimensions = RubricDimensions(
            de_escalation=2.0, validation=2.0, clarity=1.5, autonomy=2.0, next_step=1.5
        )

        mock_result = EvaluationResult(
            passed=True,
            score=9.0,
            feedback="Excellent response",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "I understand this feels controlling. I'm accountable for the outcome, not your methods. Let's set one checkpoint."
        result = evaluation_service.evaluate_answer(5, answer)

        assert result.passed is True
        assert result.score == 9.0
        assert result.dimensions is not None
        mock_llm_service.evaluate_free_form.assert_called_once()

    def test_evaluate_production_step_mediocre_answer(
        self, evaluation_service, mock_llm_service
    ):
        dimensions = RubricDimensions(
            de_escalation=1.0, validation=1.0, clarity=1.0, autonomy=0.5, next_step=1.0
        )

        mock_result = EvaluationResult(
            passed=False,
            score=4.5,
            feedback="Needs improvement",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "We need to have a conversation about deadlines and accountability."
        result = evaluation_service.evaluate_answer(5, answer)

        assert result.passed is False
        assert result.score == 4.5
        assert result.dimensions is not None

    def test_evaluate_production_step_boundary_score_exactly_7(
        self, evaluation_service, mock_llm_service
    ):
        dimensions = RubricDimensions(
            de_escalation=1.5, validation=1.5, clarity=1.5, autonomy=1.0, next_step=1.5
        )

        mock_result = EvaluationResult(
            passed=True,
            score=7.0,
            feedback="Just passes the threshold",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "I trust your work. I need visibility. Let's agree on weekly updates."
        result = evaluation_service.evaluate_answer(5, answer)

        assert result.passed is True
        assert result.score == 7.0

    def test_evaluate_production_step_just_below_threshold(
        self, evaluation_service, mock_llm_service
    ):
        dimensions = RubricDimensions(
            de_escalation=1.5, validation=1.0, clarity=1.5, autonomy=1.0, next_step=1.0
        )

        mock_result = EvaluationResult(
            passed=False,
            score=6.0,
            feedback="Close but not quite",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "I need updates from you regularly."
        result = evaluation_service.evaluate_answer(5, answer)

        assert result.passed is False
        assert result.score == 6.0

    def test_evaluate_transition_step_free_form_passes(
        self, evaluation_service, mock_llm_service
    ):
        dimensions = RubricDimensions(
            de_escalation=1.5, validation=2.0, clarity=1.5, autonomy=2.0, next_step=1.5
        )

        mock_result = EvaluationResult(
            passed=True,
            score=8.5,
            feedback="Good response",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "I trust how you work. What I'm accountable for is the outcome. Let's set a checkpoint."
        result = evaluation_service.evaluate_answer(4, answer)

        assert result.passed is True
        assert result.score == 8.5

    def test_get_rubric(self, evaluation_service):
        rubric = evaluation_service.get_rubric()

        assert "De-escalation" in rubric
        assert "Validation" in rubric
        assert "Clarity" in rubric
        assert "Autonomy" in rubric
        assert "Next step" in rubric
        assert len(rubric) == 5

    def test_get_pass_threshold(self, evaluation_service):
        assert evaluation_service.get_pass_threshold(1) == 7.0
        assert evaluation_service.get_pass_threshold(4) == 7.0
        assert evaluation_service.get_pass_threshold(5) == 7.0

    def test_get_pass_threshold_invalid_step(self, evaluation_service):
        with pytest.raises(ValueError, match="Step 99 not found"):
            evaluation_service.get_pass_threshold(99)

    def test_llm_service_called_with_correct_parameters(
        self, evaluation_service, mock_llm_service, content_provider
    ):
        dimensions = RubricDimensions(
            de_escalation=2.0, validation=2.0, clarity=2.0, autonomy=2.0, next_step=2.0
        )

        mock_result = EvaluationResult(
            passed=True,
            score=10.0,
            feedback="Perfect",
            dimensions=dimensions,
            threshold=7.0,
        )

        mock_llm_service.evaluate_free_form.return_value = mock_result

        answer = "Great response that balances everything"
        evaluation_service.evaluate_answer(5, answer)

        step = content_provider.get_step(5)
        mock_llm_service.evaluate_free_form.assert_called_once_with(
            user_answer=answer,
            scenario=step.scenario,
            gold_response=step.gold_response,
            step_id=5,
        )

    def test_evaluate_different_recognition_steps_with_different_answers(
        self, evaluation_service
    ):
        results = [
            evaluation_service.evaluate_answer(1, "C"),
            evaluation_service.evaluate_answer(2, "C"),
            evaluation_service.evaluate_answer(3, "C"),
        ]

        for result in results:
            assert result.passed is True
            assert result.score == 10.0

        wrong_results = [
            evaluation_service.evaluate_answer(1, "A"),
            evaluation_service.evaluate_answer(2, "B"),
            evaluation_service.evaluate_answer(3, "D"),
        ]

        for result in wrong_results:
            assert result.passed is False
            assert result.score == 0.0


class TestEvaluationServiceIntegration:

    @pytest.fixture
    def content_provider(self):
        return ContentProvider()

    @pytest.fixture
    def llm_service(self):
        try:
            return LLMService()
        except ValueError:
            pytest.skip("OpenAI API key not configured")

    @pytest.fixture
    def evaluation_service(self, content_provider, llm_service):
        return EvaluationService(content_provider, llm_service)

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test - requires OpenAI API key")
    def test_real_evaluation_good_answer(self, evaluation_service):
        answer = (
            "I hear that this feels controlling. I'm accountable for delivery and escalation, "
            "not for how you work day to day. We missed the date, so let's reset expectations "
            "and agree on one checkpoint going forward."
        )

        result = evaluation_service.evaluate_answer(5, answer)

        assert result.score >= 7.0
        assert result.passed is True
        assert result.dimensions is not None

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test - requires OpenAI API key")
    def test_real_evaluation_poor_answer(self, evaluation_service):
        answer = "You need to do better and meet deadlines."

        result = evaluation_service.evaluate_answer(5, answer)

        assert result.score < 7.0
        assert result.passed is False
        assert result.dimensions is not None
