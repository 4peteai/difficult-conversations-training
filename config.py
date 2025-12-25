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
        import sys
        
        raw_key = os.getenv('OPENAI_API_KEY')
        
        print("[CONFIG] Environment validation:", file=sys.stderr)
        print(f"  FLASK_ENV: {os.getenv('FLASK_ENV')}", file=sys.stderr)
        print(f"  Raw OPENAI_API_KEY present: {raw_key is not None}", file=sys.stderr)
        
        if raw_key:
            print(f"  Raw key length: {len(raw_key)}", file=sys.stderr)
            print(f"  Raw key starts with: '{raw_key[:15]}'", file=sys.stderr)
            print(f"  Raw key ends with: '{raw_key[-10:]}'", file=sys.stderr)
            
            stripped_key = raw_key.strip().strip('"').strip("'")
            if stripped_key != raw_key:
                print(f"  WARNING: Key has quotes/whitespace!", file=sys.stderr)
                print(f"  After stripping: '{stripped_key[:15]}'", file=sys.stderr)
        
        if not Config.OPENAI_API_KEY:
            print("[ERROR] OPENAI_API_KEY is not set!", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
        
        key = Config.OPENAI_API_KEY.strip()
        
        if key.startswith('"') or key.startswith("'"):
            print("[ERROR] OPENAI_API_KEY contains quotes!", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY contains quotes - remove them in Render dashboard")
        
        if not key.startswith('sk-'):
            print(f"[ERROR] OPENAI_API_KEY has invalid format: '{key[:20]}'", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY must start with 'sk-'")
        
        if len(key) < 40:
            print(f"[ERROR] OPENAI_API_KEY too short: {len(key)} chars", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY appears to be invalid (too short)")
