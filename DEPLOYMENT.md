# Deployment Guide

## Deploy to Render (Free - Recommended)

### Prerequisites
- GitHub account
- Render account (sign up at https://render.com)
- OpenAI API key

### Steps

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Create a new Web Service on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your repo

3. **Configure the service**
   - **Name**: `difficult-conversations-training` (or your choice)
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

4. **Set environment variables**
   - Click "Environment" tab
   - Add variables:
     - `OPENAI_API_KEY` = your-openai-api-key
     - `FLASK_SECRET_KEY` = generate-random-string (e.g., use `python -c "import secrets; print(secrets.token_hex(32))"`)
     - `FLASK_ENV` = `production`
     - `SESSION_TIMEOUT` = `3600`

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Your app will be live at `https://your-service-name.onrender.com`

### Important Notes

⚠️ **Free tier limitations:**
- App spins down after 15 minutes of inactivity
- First request after inactivity takes 30-60 seconds to wake up
- 750 hours/month free (enough for one always-on service)

⚠️ **Session storage:**
- Current implementation uses in-memory sessions
- Sessions are lost when the app restarts
- For production, consider adding Redis or database-backed sessions

---

## Alternative: Deploy to Railway

### Steps

1. **Create Railway account** at https://railway.app

2. **Create new project**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Set environment variables**
   - Go to Variables tab
   - Add:
     - `OPENAI_API_KEY`
     - `FLASK_SECRET_KEY`
     - `FLASK_ENV=production`
     - `PORT=5000`

4. **Railway auto-detects Python and deploys**
   - Live at `https://your-app.up.railway.app`

---

## Alternative: Deploy to Fly.io

### Steps

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and launch**
   ```bash
   fly auth login
   fly launch
   ```

3. **Set secrets**
   ```bash
   fly secrets set OPENAI_API_KEY=your-key
   fly secrets set FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

4. **Deploy**
   ```bash
   fly deploy
   ```

You'll need to create a `fly.toml` and `Dockerfile` for this option.

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run locally
python app.py
```

Visit http://localhost:5000

---

## Troubleshooting

### App crashes on Render
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure OpenAI API key is valid

### Sessions not persisting
- This is expected with in-memory storage on free tiers
- Consider upgrading to persistent storage or adding Redis

### Slow initial load
- Free tiers sleep after inactivity
- Consider paid tier ($7/month) for always-on service
