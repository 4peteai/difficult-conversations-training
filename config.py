import os
from dotenv import load_dotenv

# Only load .env file in local development
# In production (Render), environment variables are set directly
load_dotenv(override=False)


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))
    DEBUG = os.getenv("FLASK_ENV") == "development"

    @staticmethod
    def validate():
        if not Config.OPENAI_API_KEY:
            # More detailed error message
            import sys
            print("[ERROR] OPENAI_API_KEY is not set!", file=sys.stderr)
            print(f"[DEBUG] Environment check:", file=sys.stderr)
            print(f"  - FLASK_ENV: {os.getenv('FLASK_ENV')}", file=sys.stderr)
            print(f"  - OPENAI_API_KEY present: {bool(os.getenv('OPENAI_API_KEY'))}", file=sys.stderr)
            if os.getenv('OPENAI_API_KEY'):
                key = os.getenv('OPENAI_API_KEY')
                print(f"  - OPENAI_API_KEY length: {len(key)}", file=sys.stderr)
                print(f"  - OPENAI_API_KEY starts with: {key[:10]}...", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
