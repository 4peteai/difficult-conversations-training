import pytest
from unittest.mock import Mock, patch
from services.training_engine import TrainingEngine
from services.session_manager import SessionManager
from services.content_provider import ContentProvider, get_content_provider
from services.evaluation_service import EvaluationService
from services.llm_service import LLMService
from models.evaluation import EvaluationResult, RubricDimensions
from flask import Flask
from controllers.module_controller import module_bp


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def content_provider():
    return get_content_provider()


@pytest.fixture
def mock_llm_service():
    llm = Mock(spec=LLMService)

    llm.generate_remediation.return_value = {
        "explanation": "Here is why your answer needs improvement: You need to balance accountability with autonomy.",
        "remedial_scenario": 'Alex says: "I don\'t need daily check-ins."',
        "remedial_options": [
            "Fine, I'll stop checking.",
            "I need visibility. How about a brief weekly update?",
            "Just deal with it.",
            "You should be more professional.",
        ],
        "hint": "Focus on providing choice while maintaining accountability.",
    }

    llm.generate_mini_lesson.return_value = {
        "lesson_title": "Autonomy vs Accountability",
        "core_principle": "Autonomy lives in the how. Accountability lives in the what and when.",
        "examples": [
            {
                "situation": "Missed deadline",
                "wrong_approach": "Why didn't you finish on time?",
                "right_approach": "We missed the date. Let's agree on a new checkpoint.",
                "why_it_works": "It acknowledges the constraint without micromanaging.",
            }
        ],
        "common_mistakes": [
            "Confusing trust with accountability",
            "Being too defensive",
        ],
        "key_takeaway": "Preserve autonomy while maintaining clear accountability.",
    }

    llm.evaluate_free_form.return_value = EvaluationResult(
        passed=True,
        score=8.0,
        feedback="Good response. You validated the concern and maintained accountability.",
        dimensions=RubricDimensions(
            de_escalation=2.0, validation=2.0, clarity=1.0, autonomy=2.0, next_step=1.0
        ),
        threshold=7.0,
    )

    return llm


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


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = False
    app.register_blueprint(module_bp)
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


class TestFullSuccessfulFlow:
    """Test complete module flow with all correct answers"""

    def test_complete_all_steps_correctly(
        self, training_engine, content_provider, mock_llm_service
    ):
        user_id = "integration_test_user_1"

        training_engine.start_module(user_id)

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "step"
        assert state["step"].id == 1

        result = training_engine.submit_answer(user_id, "C", is_remediation=False)
        assert result["result"] == "passed"
        assert result["evaluation"].passed is True

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 2

        result = training_engine.submit_answer(user_id, "C", is_remediation=False)
        assert result["result"] == "passed"

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 3

        result = training_engine.submit_answer(user_id, "C", is_remediation=False)
        assert result["result"] == "passed"

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 4

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good response",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id,
            "I do trust how you work. What I'm accountable for is the outcome and timing.",
            is_remediation=False,
        )
        assert result["result"] == "passed"
        assert "gold_response" in result

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 5

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=9.0,
            feedback="Excellent response",
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
            user_id,
            "I hear that this feels controlling. I'm accountable for delivery. Let's reset expectations.",
            is_remediation=False,
        )
        assert result["result"] == "module_completed"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "completed"
        assert len(state["history"]) == 5


class TestFailureAndRemediation:
    """Test failure scenarios and remediation flow"""

    def test_single_failure_triggers_remediation(
        self, training_engine, mock_llm_service
    ):
        user_id = "integration_test_user_2"

        training_engine.start_module(user_id)

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] == "failed_first_attempt"
        assert "remediation" in result
        assert mock_llm_service.generate_remediation.called

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "remediation"
        assert state["failure_count"] == 1

        result = training_engine.submit_answer(user_id, "B", is_remediation=True)
        assert result["result"] == "remediation_passed"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "step"
        assert state["step"].id == 1

        result = training_engine.submit_answer(user_id, "C", is_remediation=False)
        assert result["result"] == "passed"

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 2

    def test_two_failures_trigger_mini_lesson(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_3"

        training_engine.start_module(user_id)

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] == "failed_first_attempt"

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] == "failed_second_attempt"
        assert "mini_lesson" in result
        assert mock_llm_service.generate_mini_lesson.called

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "remediation"
        assert state["failure_count"] == 2
        assert "Autonomy vs Accountability" in state["content"]

    def test_remediation_multiple_failures(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_4"

        training_engine.start_module(user_id)

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] == "failed_first_attempt"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "remediation"

        result = training_engine.submit_answer(
            user_id, "wrong answer", is_remediation=True
        )
        assert result["result"] == "remediation_failed"

        result = training_engine.submit_answer(
            user_id, "another wrong answer", is_remediation=True
        )
        assert result["result"] == "remediation_failed_multiple"
        assert "mini_lesson" in result


class TestStep4Transition:
    """Test Step 4 transition logic (options fail, free-form evaluated)"""

    def test_step4_option_selected_fails(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_5"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 4

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] in ["failed_first_attempt", "failed_second_attempt"]

    def test_step4_free_form_evaluated(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_6"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good response",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id,
            "I trust your expertise. Let's agree on a checkpoint.",
            is_remediation=False,
        )
        assert result["result"] == "passed"


class TestBoundaryScores:
    """Test edge cases with boundary scores (7/10 threshold)"""

    def test_score_exactly_7_passes(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_7"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=7.0,
            feedback="Acceptable response",
            dimensions=RubricDimensions(
                de_escalation=1.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "Some acceptable response", is_remediation=False
        )
        assert result["result"] == "passed"
        assert result["evaluation"].score == 7

    def test_score_6_fails(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_8"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=False,
            score=6.0,
            feedback="Needs improvement",
            dimensions=RubricDimensions(
                de_escalation=1.0,
                validation=1.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "Weak response", is_remediation=False
        )
        assert result["result"] == "failed_first_attempt"


class TestSessionManagement:
    """Test session creation, retrieval, and deletion"""

    def test_restart_module_clears_previous_session(self, training_engine):
        user_id = "integration_test_user_9"

        session1 = training_engine.start_module(user_id)
        training_engine.submit_answer(user_id, "C", is_remediation=False)

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 2

        session2 = training_engine.start_module(user_id)

        state = training_engine.get_current_step(user_id)
        assert state["step"].id == 1
        assert session1.user_id == session2.user_id

    def test_no_session_returns_none(self, training_engine):
        user_id = "non_existent_user"

        state = training_engine.get_current_step(user_id)
        assert state is None


@pytest.mark.skip(reason="Flask integration tests require OpenAI API key")
class TestFlaskIntegration:
    """Test Flask routes and web UI integration"""

    def test_start_module_creates_session(self, client):
        response = client.post("/module/1/start", follow_redirects=False)
        assert response.status_code == 302
        assert "/module/1/step/1" in response.location

    def test_show_step_displays_content(self, client):
        client.post("/module/1/start")
        response = client.get("/module/1/step/1")
        assert response.status_code == 200
        assert b"Alex" in response.data

    def test_submit_correct_answer(self, client):
        client.post("/module/1/start")
        response = client.post(
            "/module/1/step/1/submit", data={"answer": "C"}, follow_redirects=True
        )
        assert response.status_code == 200

    def test_complete_page_shows_history(self, client):
        client.post("/module/1/start")

        client.post("/module/1/step/1/submit", data={"answer": "C"})
        client.post("/module/1/step/2/submit", data={"answer": "C"})
        client.post("/module/1/step/3/submit", data={"answer": "C"})

        client.post(
            "/module/1/step/4/submit",
            data={
                "free_form_answer": "I do trust you. What I am accountable for is the outcome and timing. Let me know when you need support, and I will provide clear checkpoints."
            },
        )
        client.post(
            "/module/1/step/5/submit",
            data={
                "free_form_answer": "I hear that this feels controlling. I am accountable for delivery and escalation, not for how you work day to day. We missed the date, so let me reset expectations and agree on one checkpoint going forward."
            },
        )

        response = client.get("/module/1/complete")
        assert response.status_code in [200, 302]


class TestGoldResponseDisplay:
    """Test that gold responses are shown for Steps 4 and 5"""

    def test_step4_shows_gold_response(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_10"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "Good answer", is_remediation=False
        )
        assert result["result"] == "passed"
        assert "gold_response" in result
        assert result["gold_response"] is not None

    def test_step5_shows_gold_response(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_11"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        training_engine.submit_answer(user_id, "Good answer", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=9.0,
            feedback="Excellent",
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
            user_id, "Excellent answer", is_remediation=False
        )
        assert result["result"] == "module_completed"

        session = training_engine.get_session_state(user_id)
        assert session.completed is True


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_submit_answer_without_session(self, training_engine):
        user_id = "no_session_user"

        with pytest.raises(ValueError, match="No active session"):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

    def test_submit_to_completed_module(self, training_engine, mock_llm_service):
        user_id = "integration_test_user_12"

        training_engine.start_module(user_id)

        for _ in range(3):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        for _ in range(2):
            training_engine.submit_answer(user_id, "Good answer", is_remediation=False)

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "completed"

        with pytest.raises(ValueError, match="Module already completed"):
            training_engine.submit_answer(user_id, "C", is_remediation=False)

    def test_remediation_without_being_in_remediation(self, training_engine):
        user_id = "integration_test_user_13"

        training_engine.start_module(user_id)

        with pytest.raises(ValueError, match="Not in remediation mode"):
            training_engine.submit_answer(user_id, "C", is_remediation=True)


class TestCompleteUserJourney:
    """End-to-end test simulating a complete user journey with mixed results"""

    def test_realistic_user_flow_with_failures(self, training_engine, mock_llm_service):
        user_id = "realistic_user"

        training_engine.start_module(user_id)

        training_engine.submit_answer(user_id, "C", is_remediation=False)

        result = training_engine.submit_answer(user_id, "A", is_remediation=False)
        assert result["result"] == "failed_first_attempt"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "remediation"

        result = training_engine.submit_answer(user_id, "B", is_remediation=True)
        assert result["result"] == "remediation_passed"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "step"
        assert state["step"].id == 2

        training_engine.submit_answer(user_id, "C", is_remediation=False)
        training_engine.submit_answer(user_id, "C", is_remediation=False)

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=8.0,
            feedback="Good response",
            dimensions=RubricDimensions(
                de_escalation=2.0,
                validation=2.0,
                clarity=1.0,
                autonomy=2.0,
                next_step=1.0,
            ),
            threshold=7.0,
        )

        result = training_engine.submit_answer(
            user_id, "I trust you. Let's set a checkpoint.", is_remediation=False
        )
        assert result["result"] == "passed"
        assert "gold_response" in result

        mock_llm_service.evaluate_free_form.return_value = EvaluationResult(
            passed=True,
            score=9.0,
            feedback="Excellent",
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
            user_id, "I hear this feels controlling. Let's reset.", is_remediation=False
        )
        assert result["result"] == "module_completed"

        state = training_engine.get_current_step(user_id)
        assert state["type"] == "completed"
        assert len(state["history"]) == 7
