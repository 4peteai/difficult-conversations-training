import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from services.llm_service import LLMService
from models.evaluation import EvaluationResult, RubricDimensions


@pytest.fixture
def mock_openai_client():
    with patch("services.llm_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def llm_service(mock_openai_client):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
        service = LLMService(api_key="test-key-123")
        service.client = mock_openai_client
        return service


class TestLLMServiceInitialization:

    def test_initialization_with_api_key(self):
        service = LLMService(api_key="test-key")
        assert service.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("services.llm_service.Config") as mock_config:
                mock_config.OPENAI_API_KEY = None
                with pytest.raises(ValueError, match="OpenAI API key is required"):
                    LLMService()

    def test_prompts_loaded_successfully(self, llm_service):
        assert llm_service.remediation_prompt is not None
        assert llm_service.mini_lesson_prompt is not None
        assert llm_service.evaluation_prompt is not None
        assert "Autonomy vs Accountability" in llm_service.remediation_prompt


class TestGenerateRemediation:

    def test_generate_remediation_success(self, llm_service, mock_openai_client):
        mock_response = {
            "explanation": "Your answer lacked clarity about accountability.",
            "remedial_scenario": "Team member asks why you need status updates.",
            "remedial_options": [
                "Because I said so",
                "To track your progress",
                "I need visibility for stakeholders, how would you prefer to share updates?",
                "Company policy",
            ],
            "remedial_correct_answer": "C",
            "hint": "Think about preserving autonomy while meeting accountability needs",
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        result = llm_service.generate_remediation(
            topic="Autonomy vs Accountability",
            user_answer="Just trust me",
            failure_reason="Did not address accountability or offer autonomy",
            failure_count=1,
        )

        assert result["explanation"] == mock_response["explanation"]
        assert result["remedial_scenario"] == mock_response["remedial_scenario"]
        assert len(result["remedial_options"]) == 4
        assert result["remedial_correct_answer"] in ["A", "B", "C", "D"]
        assert "hint" in result

    def test_generate_remediation_calls_llm_with_correct_temperature(
        self, llm_service, mock_openai_client
    ):
        mock_response = {
            "explanation": "Test",
            "remedial_scenario": "Test scenario",
            "remedial_options": ["A", "B", "C", "D"],
            "remedial_correct_answer": "A",
            "hint": "Test hint",
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        llm_service.generate_remediation(
            topic="Test", user_answer="Test", failure_reason="Test", failure_count=1
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7

    def test_generate_remediation_invalid_json_response(
        self, llm_service, mock_openai_client
    ):
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Invalid JSON {"
        mock_openai_client.chat.completions.create.return_value = mock_completion

        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            llm_service.generate_remediation(
                topic="Test", user_answer="Test", failure_reason="Test", failure_count=1
            )

    def test_generate_remediation_missing_required_key(
        self, llm_service, mock_openai_client
    ):
        incomplete_response = {"explanation": "Test", "remedial_scenario": "Test"}

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(incomplete_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        with pytest.raises(ValueError, match="Missing required key"):
            llm_service.generate_remediation(
                topic="Test", user_answer="Test", failure_reason="Test", failure_count=1
            )

    def test_generate_remediation_invalid_options_count(
        self, llm_service, mock_openai_client
    ):
        invalid_response = {
            "explanation": "Test",
            "remedial_scenario": "Test scenario",
            "remedial_options": ["A", "B"],
            "remedial_correct_answer": "A",
            "hint": "Test",
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(invalid_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        with pytest.raises(ValueError, match="must be a list of 4 options"):
            llm_service.generate_remediation(
                topic="Test", user_answer="Test", failure_reason="Test", failure_count=1
            )


class TestGenerateMiniLesson:

    def test_generate_mini_lesson_success(self, llm_service, mock_openai_client):
        mock_response = {
            "lesson_title": "Balancing Autonomy and Accountability",
            "core_principle": "Autonomy lives in the HOW. Accountability lives in the WHAT and WHEN.",
            "examples": [
                {
                    "situation": "Team member misses deadline",
                    "wrong_approach": "You need to check in with me daily",
                    "right_approach": "We missed the date. Let's agree on one checkpoint.",
                    "why_it_works": "Preserves how they work while ensuring accountability",
                },
                {
                    "situation": "Request for status update",
                    "wrong_approach": "Because I need to know what you're doing",
                    "right_approach": "I need visibility for stakeholders. How would you prefer to share updates?",
                    "why_it_works": "States the constraint, offers choice",
                },
            ],
            "common_mistakes": [
                "Confusing trust with lack of visibility",
                "Micromanaging the process instead of focusing on outcomes",
                "Not stating clear expectations",
            ],
            "key_takeaway": "You can hold people accountable while preserving their autonomy",
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        result = llm_service.generate_mini_lesson(topic="Autonomy vs Accountability")

        assert result["lesson_title"] == mock_response["lesson_title"]
        assert result["core_principle"] == mock_response["core_principle"]
        assert len(result["examples"]) == 2
        assert len(result["common_mistakes"]) == 3
        assert "key_takeaway" in result

    def test_generate_mini_lesson_validates_example_structure(
        self, llm_service, mock_openai_client
    ):
        invalid_response = {
            "lesson_title": "Test",
            "core_principle": "Test principle",
            "examples": [{"situation": "Test", "wrong_approach": "Test"}],
            "common_mistakes": [],
            "key_takeaway": "Test",
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(invalid_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        with pytest.raises(ValueError, match="Missing required key in example"):
            llm_service.generate_mini_lesson(topic="Test")


class TestEvaluateFreeForm:

    def test_evaluate_free_form_success_pass(self, llm_service, mock_openai_client):
        mock_response = {
            "dimensions": {
                "de_escalation": 2.0,
                "validation": 1.5,
                "clarity": 2.0,
                "autonomy": 1.5,
                "next_step": 2.0,
            },
            "total_score": 9.0,
            "passed": True,
            "feedback": "Excellent response that demonstrates all key principles.",
            "strengths": ["Strong de-escalation", "Clear accountability statement"],
            "improvements": ["Could be slightly more specific on timeline"],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        result = llm_service.evaluate_free_form(
            user_answer="I understand this feels controlling. I'm accountable for delivery timing. Let's agree on one checkpoint.",
            scenario="Alex says: 'You're micromanaging me.'",
            gold_response="I hear that. Let me clarify what I need and give you choice in how.",
            step_id=4,
        )

        assert isinstance(result, EvaluationResult)
        assert result.passed is True
        assert result.score == 9.0
        assert result.dimensions is not None
        assert result.dimensions.de_escalation == 2.0
        assert "Strengths:" in result.feedback
        assert "Areas for improvement:" in result.feedback

    def test_evaluate_free_form_fail(self, llm_service, mock_openai_client):
        mock_response = {
            "dimensions": {
                "de_escalation": 0.5,
                "validation": 0.5,
                "clarity": 1.0,
                "autonomy": 0.5,
                "next_step": 1.0,
            },
            "total_score": 3.5,
            "passed": False,
            "feedback": "Response lacks validation and autonomy preservation.",
            "strengths": ["Some clarity"],
            "improvements": [
                "Add validation of their concern",
                "Preserve their autonomy",
                "De-escalate emotional tone",
            ],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        result = llm_service.evaluate_free_form(
            user_answer="Just do what I asked.",
            scenario="Test scenario",
            gold_response="Test gold",
            step_id=5,
        )

        assert result.passed is False
        assert result.score == 3.5
        assert result.threshold == 7.0

    def test_evaluate_free_form_uses_low_temperature(
        self, llm_service, mock_openai_client
    ):
        mock_response = {
            "dimensions": {
                "de_escalation": 1.0,
                "validation": 1.0,
                "clarity": 1.0,
                "autonomy": 1.0,
                "next_step": 1.0,
            },
            "total_score": 5.0,
            "passed": False,
            "feedback": "Test",
            "strengths": [],
            "improvements": [],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        llm_service.evaluate_free_form(
            user_answer="Test", scenario="Test", gold_response="Test", step_id=4
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.3

    def test_evaluate_free_form_boundary_score(self, llm_service, mock_openai_client):
        mock_response = {
            "dimensions": {
                "de_escalation": 1.5,
                "validation": 1.5,
                "clarity": 1.5,
                "autonomy": 1.0,
                "next_step": 1.5,
            },
            "total_score": 7.0,
            "passed": True,
            "feedback": "Meets minimum threshold.",
            "strengths": ["Adequate response"],
            "improvements": ["Could be stronger in all areas"],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai_client.chat.completions.create.return_value = mock_completion

        result = llm_service.evaluate_free_form(
            user_answer="Test", scenario="Test", gold_response="Test", step_id=5
        )

        assert result.score == 7.0
        assert result.passed is True


class TestErrorHandling:

    def test_rate_limit_error(self, llm_service, mock_openai_client):
        from openai import RateLimitError

        mock_openai_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limit exceeded", response=MagicMock(), body=None
        )

        with pytest.raises(Exception, match="rate limit exceeded"):
            llm_service.generate_remediation(
                topic="Test", user_answer="Test", failure_reason="Test", failure_count=1
            )

    def test_api_connection_error(self, llm_service, mock_openai_client):
        from openai import APIConnectionError

        mock_openai_client.chat.completions.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        with pytest.raises(Exception, match="API connection error"):
            llm_service.generate_mini_lesson(topic="Test")

    def test_generic_api_error(self, llm_service, mock_openai_client):
        from openai import APIError

        mock_openai_client.chat.completions.create.side_effect = APIError(
            "API Error", request=MagicMock(), body=None
        )

        with pytest.raises(Exception, match="API error"):
            llm_service.evaluate_free_form(
                user_answer="Test", scenario="Test", gold_response="Test", step_id=4
            )


class TestPromptFormatting:

    def test_remediation_prompt_contains_variables(self, llm_service):
        assert "{topic}" in llm_service.remediation_prompt
        assert "{user_answer}" in llm_service.remediation_prompt
        assert "{failure_reason}" in llm_service.remediation_prompt
        assert "{failure_count}" in llm_service.remediation_prompt

    def test_evaluation_prompt_contains_variables(self, llm_service):
        assert "{scenario}" in llm_service.evaluation_prompt
        assert "{user_answer}" in llm_service.evaluation_prompt
        assert "{gold_response}" in llm_service.evaluation_prompt

    def test_mini_lesson_prompt_contains_variables(self, llm_service):
        assert "{topic}" in llm_service.mini_lesson_prompt
