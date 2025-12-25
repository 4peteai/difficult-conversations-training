from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from config import Config
from controllers.module_controller import module_bp
import os

app = Flask(__name__)
app.config.from_object(Config)

# Debug logging for deployment
import sys
raw_key = os.getenv('OPENAI_API_KEY')
print(f"[APP STARTUP] Environment check:", file=sys.stderr)
print(f"  Raw OPENAI_API_KEY in env: {bool(raw_key)}", file=sys.stderr)

if raw_key:
    if raw_key.startswith('"') or raw_key.startswith("'"):
        print(f"  ⚠️  PROBLEM: API key has quotes: '{raw_key[:20]}'", file=sys.stderr)
    elif not raw_key.startswith('sk-'):
        print(f"  ⚠️  PROBLEM: Invalid key format: '{raw_key[:20]}'", file=sys.stderr)
    else:
        print(f"  ✓ API key format looks valid: '{raw_key[:15]}'", file=sys.stderr)

if Config.OPENAI_API_KEY:
    print(f"  ✓ Config.OPENAI_API_KEY loaded successfully", file=sys.stderr)
else:
    print(f"  ✗ Config.OPENAI_API_KEY is None/empty", file=sys.stderr)

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
