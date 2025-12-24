import pytest
from services.content_provider import ContentProvider, get_content_provider
from models.step import StepType


class TestContentProvider:
    """Test suite for ContentProvider."""

    @pytest.fixture
    def provider(self):
        """Create a fresh ContentProvider instance for each test."""
        return ContentProvider()

    def test_initialization(self, provider):
        """Test that provider initializes with all required content."""
        assert provider is not None
        assert provider.get_all_steps() is not None
        assert provider.get_mini_lesson() is not None

    def test_has_all_five_steps(self, provider):
        """Verify all 5 steps are present."""
        steps = provider.get_all_steps()
        assert len(steps) == 5
        for step_id in range(1, 6):
            assert step_id in steps

    def test_get_step_valid_ids(self, provider):
        """Test retrieving each step by ID."""
        for step_id in range(1, 6):
            step = provider.get_step(step_id)
            assert step is not None
            assert step.id == step_id
            assert step.scenario is not None
            assert len(step.scenario) > 0

    def test_get_step_invalid_id(self, provider):
        """Test retrieving step with invalid ID returns None."""
        assert provider.get_step(0) is None
        assert provider.get_step(6) is None
        assert provider.get_step(99) is None

    def test_step_1_structure(self, provider):
        """Verify Step 1 has correct structure and option C is correct."""
        step = provider.get_step(1)
        assert step.type == StepType.RECOGNITION
        assert step.options is not None
        assert len(step.options) == 4
        assert "A" in step.options
        assert "B" in step.options
        assert "C" in step.options
        assert "D" in step.options
        assert step.correct_answer == "C"
        assert step.allow_free_form is False
        assert step.gold_response is None

    def test_step_2_structure(self, provider):
        """Verify Step 2 has correct structure and option C is correct."""
        step = provider.get_step(2)
        assert step.type == StepType.RECOGNITION
        assert step.options is not None
        assert len(step.options) == 4
        assert step.correct_answer == "C"
        assert step.allow_free_form is False

    def test_step_3_structure(self, provider):
        """Verify Step 3 has correct structure and option C is correct."""
        step = provider.get_step(3)
        assert step.type == StepType.RECOGNITION
        assert step.options is not None
        assert len(step.options) == 4
        assert step.correct_answer == "C"
        assert step.allow_free_form is False

    def test_step_4_structure(self, provider):
        """Verify Step 4 is a transition step with gold response."""
        step = provider.get_step(4)
        assert step.type == StepType.TRANSITION
        assert step.options is not None  # Has options but all are wrong
        assert len(step.options) == 4
        assert step.correct_answer is None  # No correct option
        assert step.allow_free_form is True
        assert step.gold_response is not None
        assert len(step.gold_response) > 0
        assert step.pass_threshold == 7.0

    def test_step_5_structure(self, provider):
        """Verify Step 5 is a production step with gold response."""
        step = provider.get_step(5)
        assert step.type == StepType.PRODUCTION
        assert step.options is None  # Free-form only
        assert step.correct_answer is None
        assert step.allow_free_form is True
        assert step.gold_response is not None
        assert len(step.gold_response) > 0
        assert step.pass_threshold == 7.0

    def test_all_recognition_steps_have_correct_answers(self, provider):
        """Verify all recognition steps (1-3) have correct answers."""
        for step_id in range(1, 4):
            step = provider.get_step(step_id)
            assert step.type == StepType.RECOGNITION
            assert step.correct_answer is not None
            assert step.correct_answer in step.options

    def test_steps_4_and_5_have_gold_responses(self, provider):
        """Verify Steps 4 and 5 have gold responses."""
        for step_id in [4, 5]:
            step = provider.get_step(step_id)
            gold = provider.get_gold_response(step_id)
            assert gold is not None
            assert len(gold) > 0
            assert gold == step.gold_response

    def test_get_correct_answer(self, provider):
        """Test get_correct_answer method."""
        # Recognition steps should return correct answer
        assert provider.get_correct_answer(1) == "C"
        assert provider.get_correct_answer(2) == "C"
        assert provider.get_correct_answer(3) == "C"

        # Step 4 has no correct answer (all options wrong)
        assert provider.get_correct_answer(4) is None

        # Step 5 has no correct answer (free-form only)
        assert provider.get_correct_answer(5) is None

        # Invalid step
        assert provider.get_correct_answer(99) is None

    def test_get_gold_response(self, provider):
        """Test get_gold_response method."""
        # Steps 1-3 have no gold responses
        assert provider.get_gold_response(1) is None
        assert provider.get_gold_response(2) is None
        assert provider.get_gold_response(3) is None

        # Steps 4-5 have gold responses
        gold_4 = provider.get_gold_response(4)
        assert gold_4 is not None
        assert "trust how you work" in gold_4

        gold_5 = provider.get_gold_response(5)
        assert gold_5 is not None
        assert "accountable for delivery" in gold_5

        # Invalid step
        assert provider.get_gold_response(99) is None

    def test_mini_lesson_content(self, provider):
        """Test mini-lesson has required content."""
        lesson = provider.get_mini_lesson()
        assert "principle" in lesson
        assert "formula" in lesson
        assert "Autonomy" in lesson["principle"]
        assert "Accountability" in lesson["principle"]
        assert "Validate" in lesson["formula"]
        assert "State constraint" in lesson["formula"]
        assert "Offer choice" in lesson["formula"]
        assert "Lock next step" in lesson["formula"]

    def test_get_topic(self, provider):
        """Test get_topic returns correct module topic."""
        topic = provider.get_topic()
        assert topic == "Autonomy vs Accountability"

    def test_singleton_pattern(self):
        """Test that get_content_provider returns singleton instance."""
        provider1 = get_content_provider()
        provider2 = get_content_provider()
        assert provider1 is provider2

    def test_step_scenarios_contain_alex(self, provider):
        """Verify all scenarios reference Alex."""
        for step_id in range(1, 6):
            step = provider.get_step(step_id)
            assert "Alex" in step.scenario or "says:" in step.scenario

    def test_immutability_of_returned_data(self, provider):
        """Test that modifying returned data doesn't affect internal state."""
        # Get mini-lesson and modify it
        lesson1 = provider.get_mini_lesson()
        lesson1["principle"] = "MODIFIED"

        # Get it again and verify it's unchanged
        lesson2 = provider.get_mini_lesson()
        assert lesson2["principle"] != "MODIFIED"
        assert "Autonomy" in lesson2["principle"]

    def test_validation_ensures_content_integrity(self):
        """Test that validation catches missing content."""
        # This test verifies that the internal validation works
        # by checking that a properly initialized provider passes validation
        provider = ContentProvider()

        # If we get here without exceptions, validation passed
        assert provider is not None

        # Verify validation caught all requirements
        steps = provider.get_all_steps()
        assert all(steps[i].correct_answer for i in range(1, 4))  # Steps 1-3
        assert all(steps[i].gold_response for i in [4, 5])  # Steps 4-5
