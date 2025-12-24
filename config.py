import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 3600))
    DEBUG = os.getenv("FLASK_ENV") == "development"

    @staticmethod
    def validate():
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
