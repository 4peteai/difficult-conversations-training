# Render Deployment - API Key Debug Guide

## Problem
Application fails to start on Render with error: **"Error starting module: OpenAI API key is required"**

## Root Causes (Most Common)

### 1. Environment Variable Has Quotes
**Symptom**: Render shows the env var is set, but app fails to start  
**Cause**: The API key value in Render has quotes around it: `"sk-proj-..."`  
**Fix**: In Render Dashboard → Environment → Edit OPENAI_API_KEY → Remove ALL quotes

```bash
# WRONG - Has quotes
"sk-proj-abc123..."

# CORRECT - No quotes
sk-proj-abc123...
```

### 2. Environment Variable Not Set
**Symptom**: App logs show "OPENAI_API_KEY present: False"  
**Cause**: Environment variable wasn't created or was deleted  
**Fix**: Add environment variable in Render Dashboard:
- Key: `OPENAI_API_KEY` (exact case matters)
- Value: Your actual OpenAI API key starting with `sk-`

### 3. API Key Format Invalid
**Symptom**: App logs show "Invalid API key format"  
**Cause**: API key doesn't start with `sk-` or is a placeholder  
**Fix**: Use a real OpenAI API key from https://platform.openai.com/api-keys

### 4. Whitespace in API Key
**Symptom**: App starts but OpenAI calls fail  
**Cause**: Extra spaces or newlines in the API key value  
**Fix**: Copy/paste key carefully with no trailing spaces

## Updated Code - Enhanced Validation

### Changes Made

**1. `config.py` - Detailed Environment Diagnostics**
- Shows raw environment variable value
- Detects quotes and whitespace
- Validates API key format (must start with `sk-`)
- Validates API key length (must be >40 chars)

**2. `services/llm_service.py` - Automatic Quote Stripping**
- Strips quotes and whitespace from API key
- Validates format before creating OpenAI client
- Better error messages showing actual key prefix

## How to Debug on Render

### Step 1: Check Render Logs
Go to Render Dashboard → Your Service → Logs

Look for these debug messages:

```
[CONFIG] Environment validation:
  FLASK_ENV: production
  Raw OPENAI_API_KEY present: True/False
  Raw key length: XXX
  Raw key starts with: 'sk-...' or '"sk-...'
```

### Step 2: Identify the Issue

**If you see:**
```
Raw key starts with: '"sk-...'
WARNING: Key has quotes/whitespace!
```
→ **Solution**: Remove quotes from Render environment variable

**If you see:**
```
Raw OPENAI_API_KEY present: False
```
→ **Solution**: Add OPENAI_API_KEY environment variable in Render

**If you see:**
```
Raw key starts with: 'your-api-key' or 'placeholder'
```
→ **Solution**: Replace with real OpenAI API key

### Step 3: Fix Environment Variable in Render

1. Go to Render Dashboard
2. Click your service
3. Click "Environment" in left sidebar
4. Find `OPENAI_API_KEY`
5. Click Edit
6. Ensure value:
   - Starts with `sk-`
   - Has NO quotes (`"` or `'`)
   - Has NO extra spaces
   - Is a real API key (not placeholder)
7. Click Save
8. Render will automatically redeploy

### Step 4: Verify Fix

After redeployment, check logs for:
```
[CONFIG] Environment validation:
  Raw OPENAI_API_KEY present: True
  Raw key starts with: 'sk-proj-'
  
[GUNICORN STARTING] - Environment Check:
  OPENAI_API_KEY: SET
```

If you see this → ✅ **Success!**

## Testing Locally

To verify the fixes work locally:

```bash
# Test with quotes (should auto-strip)
export OPENAI_API_KEY='"sk-proj-abc123..."'
python3 app.py

# Test with whitespace (should auto-strip)
export OPENAI_API_KEY='  sk-proj-abc123...  '
python3 app.py

# Test with invalid format (should fail with clear error)
export OPENAI_API_KEY='invalid-key'
python3 app.py
```

## Common Render Environment Variable Mistakes

### ❌ Wrong: Quotes in Value Field
```
Key: OPENAI_API_KEY
Value: "sk-proj-abc123..."
```

### ✅ Correct: No Quotes
```
Key: OPENAI_API_KEY
Value: sk-proj-abc123...
```

### ❌ Wrong: Using .env File Syntax
```
Value: OPENAI_API_KEY=sk-proj-abc123...
```

### ✅ Correct: Just the Value
```
Value: sk-proj-abc123...
```

## If Issue Persists

1. **Check Render build logs** - Ensure build completed successfully
2. **Verify OpenAI API key is active** - Test it with curl:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```
3. **Check for multiple services** - Ensure you're editing the correct service
4. **Try manual deploy** - Click "Manual Deploy" → "Clear build cache & deploy"

## Support Resources

- Render Environment Variables: https://render.com/docs/environment-variables
- OpenAI API Keys: https://platform.openai.com/api-keys
- Render Logs: Dashboard → Service → Logs tab
