from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from config import Config
from controllers.module_controller import module_bp

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

app.register_blueprint(module_bp)


@app.errorhandler(404)
def not_found_error(error):
    return (
        render_template("error.html", error_code=404, error_message="Page not found"),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    return (
        render_template(
            "error.html", error_code=500, error_message="Internal server error"
        ),
        500,
    )


if __name__ == "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration warning: {e}")
        print("Some features may not work without proper configuration.")

    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=5000)
