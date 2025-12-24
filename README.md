# Difficult Conversations Training Platform

A deterministic training engine for teaching effective communication in difficult workplace conversations, specifically focusing on balancing **Autonomy vs Accountability**.

## Overview

This platform implements a structured learning system that combines:
- **Predefined content** for consistent training scenarios (Steps 1-5)
- **LLM-powered remediation** for personalized learning when students struggle
- **Rubric-based evaluation** for production-level responses

The system enforces strict progression rules, evaluates answers against defined criteria, and provides adaptive remediation when learners fail steps.

## Features

- **Recognition Steps (1-3)**: Multiple-choice scenarios testing concept recognition
- **Transition Step (4)**: Mixed format introducing free-form responses
- **Production Step (5)**: Full free-form response requiring complete skill demonstration
- **Adaptive Remediation**: LLM-generated explanations and simpler practice questions after failures
- **Mini-Lessons**: Expanded learning content triggered after repeated failures
- **Progress Tracking**: Session-based state management with answer history
- **Rubric Evaluation**: Standardized scoring across 5 dimensions (De-escalation, Validation, Clarity, Autonomy, Next step)

## Architecture

The application follows a **Model-View-Controller (MVC)** pattern with a service layer:

```
.
├── app.py                      # Flask application entry point
├── config.py                   # Configuration management
├── models/                     # Data models (Pydantic)
│   ├── step.py                # Step and StepType definitions
│   ├── scenario.py            # Scenario model
│   ├── session.py             # SessionState and AnswerRecord
│   └── evaluation.py          # EvaluationResult and RubricDimensions
├── services/                   # Business logic layer
│   ├── content_provider.py    # Predefined content (scenarios, answers)
│   ├── session_manager.py     # Session state management
│   ├── llm_service.py         # OpenAI API integration
│   ├── evaluation_service.py  # Answer evaluation and scoring
│   └── training_engine.py     # Core training orchestration
├── controllers/                # Request handlers
│   └── module_controller.py   # HTTP routes and views
├── templates/                  # Jinja2 HTML templates
├── static/                     # CSS and static assets
├── prompts/                    # LLM prompt templates
└── tests/                      # Test suite
```

## Tech Stack

- **Python 3.10+**
- **Flask 3.1.0**: Web framework
- **OpenAI SDK 1.58.1**: LLM integration
- **Pydantic 2.10.5**: Data validation and typing
- **pytest 8.3.4**: Testing framework
- **mypy 1.14.1**: Static type checking
- **black 24.10.0**: Code formatting
- **flake8 7.1.1**: Linting

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Installation

1. **Clone the repository** (or navigate to project directory):
   ```bash
   cd /path/to/difficult-conversations-training
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   FLASK_ENV=development
   FLASK_SECRET_KEY=your-random-secret-key
   SESSION_TIMEOUT=3600
   ```

5. **Verify installation**:
   ```bash
   python -c "import flask; import openai; import pydantic; print('All dependencies installed!')"
   ```

## Running the Application

### Start the development server:

```bash
python app.py
```

The application will be available at: **http://127.0.0.1:5000**

### Using the application:

1. Navigate to the home page
2. Click "Start Module 1"
3. Progress through steps 1-5:
   - Read Alex's statements
   - Select appropriate responses (Steps 1-3) or write free-form answers (Steps 4-5)
   - Receive immediate feedback
   - Complete remediation if you fail a step
4. Review your completion summary

## Testing

### Run all tests:

```bash
pytest tests/ -v
```

### Run with coverage:

```bash
pytest tests/ --cov=services --cov=models --cov=controllers --cov-report=html
```

Coverage report will be in `htmlcov/index.html`.

### Run specific test files:

```bash
pytest tests/test_training_engine.py -v
pytest tests/test_integration.py -v
```

### Run type checking:

```bash
mypy services/ models/ controllers/
```

### Run linting:

```bash
flake8 . --exclude=venv,__pycache__,.mypy_cache,.pytest_cache,.zenflow --max-line-length=100
```

### Run formatting:

```bash
black . --exclude='venv|__pycache__|\.mypy_cache|\.pytest_cache|\.zenflow'
```

## How It Works

### Content Hierarchy

1. **Predefined Content** (ContentProvider):
   - 5 complete scenarios with Alex (defensive, autonomy-driven persona)
   - Correct answers for recognition steps
   - Gold responses for transition/production steps
   - Mini-lesson core principle and formula

2. **LLM-Generated Content** (LLMService):
   - Failure explanations tailored to user's mistake
   - Simplified remedial questions on the same topic
   - Expanded mini-lessons with examples
   - Rubric-based scoring for free-form answers

### Progression Logic

- **Steps 1-3 (Recognition)**: Select correct option from A-D. Fail → remediation
- **Step 4 (Transition)**: All options are wrong; free-form required. Evaluated with 7/10 threshold
- **Step 5 (Production)**: Free-form only. Must score ≥7/10 on rubric

### Failure Handling

1. **First Failure**: LLM generates explanation + simpler remedial question
2. **Second Failure**: LLM provides mini-lesson + another remedial question
3. **Pass Remediation**: Return to original step with fresh attempt

### Evaluation Rubric (Steps 4-5)

Each dimension scored 0-2 points:

| Dimension     | Description                          |
|---------------|--------------------------------------|
| De-escalation | Reduces threat/tension               |
| Validation    | Acknowledges concern                 |
| Clarity       | States what/when/why clearly         |
| Autonomy      | Preserves ownership                  |
| Next step     | Proposes concrete action             |

**Total**: /10 points  
**Pass**: ≥7 points

## Key Design Principles

1. **Deterministic Happy Path**: Main scenarios and correct answers are fixed
2. **LLM as Gap Filler**: AI generates content only when predefined content is insufficient
3. **No Negotiation**: System enforces rules strictly; users cannot bypass requirements
4. **Adaptive Difficulty**: Remediation questions are simpler than original content
5. **Context Preservation**: LLM always maintains topic consistency (Autonomy vs Accountability)

## Project Structure Details

### Models (`models/`)

- **Step**: Represents a training step with scenario, options, correct answer, and gold response
- **SessionState**: Tracks user progress, failure count, remediation state, and answer history
- **EvaluationResult**: Contains pass/fail status, score, feedback, and rubric breakdown

### Services (`services/`)

- **ContentProvider**: Serves all predefined Module 1 content
- **SessionManager**: Thread-safe session storage with expiration handling
- **LLMService**: OpenAI API integration with structured prompt templates
- **EvaluationService**: Rubric-based answer evaluation
- **TrainingEngine**: Orchestrates progression, remediation, and module completion

### Controllers (`controllers/`)

- **ModuleController**: Flask routes for all user interactions (start, submit, remediation, complete)

## Known Limitations

1. **In-Memory Sessions**: Sessions stored in memory; lost on server restart
   - **Future**: Migrate to Redis or database
2. **Single Module**: Only "Autonomy vs Accountability" implemented
   - **Future**: Add more conversation topic modules
3. **No User Authentication**: Sessions identified by simple user_id
   - **Future**: Add proper auth with login/registration
4. **No Analytics**: No tracking of aggregate performance metrics
   - **Future**: Add analytics dashboard for trainers
5. **Limited UI**: Basic Bootstrap styling
   - **Future**: Enhanced UX with progress indicators, animations

## Environment Variables

| Variable           | Description                          | Default              |
|--------------------|--------------------------------------|----------------------|
| OPENAI_API_KEY     | OpenAI API key (required)            | None (must set)      |
| FLASK_ENV          | Flask environment                    | development          |
| FLASK_SECRET_KEY   | Secret key for sessions              | Random generated     |
| SESSION_TIMEOUT    | Session timeout in seconds           | 3600 (1 hour)        |

## Contributing

### Code Quality Standards

- All code must pass `flake8` (max line length: 100)
- All code must be formatted with `black`
- All code must pass `mypy` type checking
- All new features must include tests
- Test coverage should remain above 85%

### Before Committing

```bash
# Format code
black . --exclude='venv|__pycache__|\.mypy_cache|\.pytest_cache|\.zenflow'

# Run linter
flake8 . --exclude=venv,__pycache__,.mypy_cache,.pytest_cache,.zenflow --max-line-length=100

# Type check
mypy services/ models/ controllers/

# Run tests
pytest tests/ -v
```

## License

This project is proprietary training software.

## Support

For issues or questions, contact the development team.
