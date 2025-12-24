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
    print(f"  OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    if os.getenv('OPENAI_API_KEY'):
        key = os.getenv('OPENAI_API_KEY')
        print(f"  OPENAI_API_KEY length: {len(key)}")
        print(f"  OPENAI_API_KEY prefix: {key[:15]}...")
    print("=" * 60)
