from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from services.training_engine import TrainingEngine
from services.session_manager import SessionManager
from services.content_provider import ContentProvider
from services.evaluation_service import EvaluationService
from services.llm_service import LLMService
from config import Config
import uuid

module_bp = Blueprint("module", __name__)

_session_manager = None
_content_provider = None
_llm_service = None
_evaluation_service = None
_training_engine = None


def get_training_engine():
    global _session_manager, _content_provider, _llm_service, _evaluation_service, _training_engine

    if _training_engine is None:
        _session_manager = SessionManager()
        _content_provider = ContentProvider()
        _llm_service = LLMService(api_key=Config.OPENAI_API_KEY)
        _evaluation_service = EvaluationService(
            llm_service=_llm_service, content_provider=_content_provider
        )
        _training_engine = TrainingEngine(
            session_manager=_session_manager,
            content_provider=_content_provider,
            evaluation_service=_evaluation_service,
            llm_service=_llm_service,
        )

    return _training_engine


def get_content_provider():
    global _content_provider
    if _content_provider is None:
        _content_provider = ContentProvider()
    return _content_provider


def get_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]


@module_bp.route("/")
def index():
    return render_template("index.html")


@module_bp.route("/module/1/start", methods=["POST"])
def start_module():
    user_id = get_user_id()

    try:
        engine = get_training_engine()
        engine.start_module(user_id)
        return redirect(url_for("module.show_step", step_id=1))
    except Exception as e:
        flash(f"Error starting module: {str(e)}", "error")
        return redirect(url_for("module.index"))


@module_bp.route("/module/1/step/<int:step_id>", methods=["GET"])
def show_step(step_id):
    user_id = get_user_id()

    if step_id < 1 or step_id > 5:
        flash("Invalid step number", "error")
        return redirect(url_for("module.index"))

    try:
        engine = get_training_engine()
        current_state = engine.get_current_step(user_id)

        if not current_state:
            flash("No active session. Please start the module first.", "warning")
            return redirect(url_for("module.index"))

        if current_state["type"] == "remediation":
            return redirect(url_for("module.show_remediation"))

        if current_state["type"] == "completed":
            return redirect(url_for("module.show_complete"))

        if current_state["type"] == "step":
            step = current_state["step"]

            if step.id != step_id:
                return redirect(url_for("module.show_step", step_id=step.id))

            return render_template(
                "step.html",
                step=step,
                feedback=None,
                gold_response=None,
                passed=False,
                next_step_id=None,
            )

        flash("Unexpected state", "error")
        return redirect(url_for("module.index"))

    except Exception as e:
        flash(f"Error loading step: {str(e)}", "error")
        return redirect(url_for("module.index"))


@module_bp.route("/module/1/step/<int:step_id>/submit", methods=["POST"])
def submit_answer(step_id):
    user_id = get_user_id()

    if step_id < 1 or step_id > 5:
        flash("Invalid step number", "error")
        return redirect(url_for("module.index"))

    try:
        # Check if step_id matches current backend state to prevent desync
        engine = get_training_engine()
        provider = get_content_provider()
        current_state = engine.get_current_step(user_id)
        
        if current_state and current_state.get("type") == "step":
            actual_step_id = current_state["step"].id
            if actual_step_id != step_id:
                # Redirect to correct step - user is out of sync
                flash(
                    f"Please complete Step {actual_step_id} first.",
                    "warning",
                )
                return redirect(url_for("module.show_step", step_id=actual_step_id))

        answer = request.form.get("answer")
        free_form_answer = request.form.get("free_form_answer")

        if free_form_answer and free_form_answer.strip():
            answer = free_form_answer.strip()

        if not answer:
            flash("Please provide an answer", "warning")
            return redirect(url_for("module.show_step", step_id=step_id))

        result = engine.submit_answer(user_id, answer, is_remediation=False)

        if result["result"] == "passed":
            # Step passed - show feedback and provide navigation to next step
            # Get the step that was just completed (for showing gold response)
            current_step_data = provider.get_step(step_id)
            gold_response = result.get("gold_response")
            next_step_obj = result.get("next_step")

            return render_template(
                "step.html",
                step=current_step_data,
                feedback=result["evaluation"],
                gold_response=gold_response,
                passed=True,
                next_step_id=next_step_obj.id if next_step_obj else None,
            )

        elif result["result"] == "module_completed":
            return redirect(url_for("module.show_complete"))

        elif result["result"] == "failed_first_attempt":
            return redirect(url_for("module.show_remediation"))

        elif result["result"] == "failed_second_attempt":
            return redirect(url_for("module.show_remediation"))

        else:
            # Failed or other result - stay on current step
            provider = get_content_provider()
            step_data = provider.get_step(step_id)
            return render_template(
                "step.html",
                step=step_data,
                feedback=result.get("evaluation"),
                gold_response=None,
                passed=False,
                next_step_id=None,
            )

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("module.index"))
    except Exception as e:
        # On error, preserve user's answer and show retry option
        flash(
            "Error generating feedback. Please try again. If the problem persists, try a different response.",
            "error",
        )
        provider = get_content_provider()
        step_data = provider.get_step(step_id)
        return render_template(
            "step.html",
            step=step_data,
            feedback=None,
            gold_response=None,
            previous_answer=answer if "answer" in locals() else None,
            passed=False,
            next_step_id=None,
        )


@module_bp.route("/module/1/remediation", methods=["GET"])
def show_remediation():
    user_id = get_user_id()

    try:
        engine = get_training_engine()
        current_state = engine.get_current_step(user_id)

        if not current_state or current_state["type"] != "remediation":
            flash("Not in remediation mode", "warning")
            return redirect(url_for("module.index"))

        return render_template(
            "remediation.html",
            content=current_state["content"],
            question=current_state["question"],
            options=current_state.get("options", {}),
            correct_answer=current_state.get("correct_answer"),
            failure_count=current_state["failure_count"],
        )

    except Exception as e:
        flash(f"Error loading remediation: {str(e)}", "error")
        return redirect(url_for("module.index"))


@module_bp.route("/module/1/remediation/submit", methods=["POST"])
def submit_remediation():
    user_id = get_user_id()

    try:
        answer = request.form.get("answer")
        free_form_answer = request.form.get("free_form_answer")

        if free_form_answer and free_form_answer.strip():
            answer = free_form_answer.strip()

        if not answer:
            flash("Please provide an answer", "warning")
            return redirect(url_for("module.show_remediation"))

        engine = get_training_engine()
        result = engine.submit_answer(user_id, answer, is_remediation=True)

        if result["result"] == "remediation_passed":
            flash("Great! You've understood the concept.", "success")
            next_step = result.get("next_step")
            if next_step:
                return redirect(url_for("module.show_step", step_id=next_step.id))
            else:
                return redirect(url_for("module.index"))

        elif result["result"] == "remediation_failed":
            # Re-render with feedback
            current_state = engine.get_current_step(user_id)
            return render_template(
                "remediation.html",
                content=current_state["content"],
                question=current_state["question"],
                options=current_state.get("options", {}),
                correct_answer=current_state.get("correct_answer"),
                failure_count=current_state["failure_count"],
                feedback_message=result.get("message"),
            )

        elif result["result"] == "remediation_failed_multiple":
            # Re-render with updated content (mini lesson)
            current_state = engine.get_current_step(user_id)
            return render_template(
                "remediation.html",
                content=current_state["content"],
                question=current_state["question"],
                options=current_state.get("options", {}),
                correct_answer=current_state.get("correct_answer"),
                failure_count=current_state["failure_count"],
                feedback_message="Let's review the core concepts before trying again.",
            )

        else:
            return redirect(url_for("module.show_remediation"))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("module.index"))
    except Exception as e:
        # On error, preserve user's answer and show retry option
        flash(
            "Error generating feedback. Please try again. If the problem persists, refresh the page.",
            "error",
        )
        # Try to get current state to re-render remediation with error
        try:
            engine = get_training_engine()
            current_state = engine.get_current_step(user_id)
            return render_template(
                "remediation.html",
                content=current_state.get("content", ""),
                question=current_state.get("question", ""),
                failure_count=current_state.get("failure_count", 1),
                previous_answer=answer if "answer" in locals() else None,
            )
        except:
            return redirect(url_for("module.show_remediation"))


@module_bp.route("/module/1/complete", methods=["GET"])
def show_complete():
    user_id = get_user_id()

    try:
        engine = get_training_engine()
        current_state = engine.get_current_step(user_id)

        if not current_state:
            flash("No active session", "warning")
            return redirect(url_for("module.index"))

        if current_state["type"] != "completed":
            flash("Module not yet completed", "warning")
            step_id = engine.get_session_state(user_id).current_step
            return redirect(url_for("module.show_step", step_id=step_id))

        return render_template(
            "complete.html",
            history=current_state["history"],
            completed_at=current_state.get("completed_at"),
        )

    except Exception as e:
        flash(f"Error loading completion page: {str(e)}", "error")
        return redirect(url_for("module.index"))


@module_bp.route("/module/1/reset", methods=["POST"])
def reset_module():
    user_id = get_user_id()

    try:
        engine = get_training_engine()
        engine.reset_module(user_id)
        flash("Module reset successfully", "success")
        return redirect(url_for("module.index"))
    except Exception as e:
        flash(f"Error resetting module: {str(e)}", "error")
        return redirect(url_for("module.index"))


@module_bp.errorhandler(404)
def not_found_error(error):
    return (
        render_template("error.html", error_code=404, error_message="Page not found"),
        404,
    )


@module_bp.errorhandler(500)
def internal_error(error):
    return (
        render_template(
            "error.html", error_code=500, error_message="Internal server error"
        ),
        500,
    )
