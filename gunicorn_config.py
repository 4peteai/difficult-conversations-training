import os

# Gunicorn configuration
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Startup hook to verify environment
def on_starting(server):
    print("=" * 60)
    print("GUNICORN STARTING - Environment Check:")
    print(f"  PORT: {os.getenv('PORT', 'not set')}")
    print(f"  FLASK_ENV: {os.getenv('FLASK_ENV', 'not set')}")
    
    raw_key = os.getenv('OPENAI_API_KEY')
    print(f"  OPENAI_API_KEY: {'SET' if raw_key else 'NOT SET'}")
    
    if raw_key:
        print(f"  Raw key length: {len(raw_key)}")
        print(f"  Raw key first 15 chars: '{raw_key[:15]}'")
        print(f"  Raw key last 10 chars: '{raw_key[-10:]}'")
        
        if raw_key.startswith('"') or raw_key.startswith("'"):
            print("  ⚠️  WARNING: API key contains quotes!")
            print("  ⚠️  This will cause authentication to fail")
            print("  ⚠️  Remove quotes in Render environment variables")
        
        stripped = raw_key.strip().strip('"').strip("'")
        if stripped != raw_key:
            print(f"  After strip would be: '{stripped[:15]}'")
        
        if not stripped.startswith('sk-'):
            print("  ⚠️  WARNING: API key doesn't start with 'sk-'")
            print("  ⚠️  This appears to be an invalid or placeholder key")
    
    print("=" * 60)
