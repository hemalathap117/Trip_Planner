# Render.com Deployment Guide

## Prerequisites

1. GitHub account with your code pushed
2. Render.com account (free tier available)

## Step 1: Create PostgreSQL Database

1. Go to Render Dashboard → New → PostgreSQL
2. Configure:
   - **Name**: `trip-planner-db`
   - **Database**: `trip_planner`
   - **User**: (auto-generated)
   - **Region**: Choose closest to you
   - **Plan**: Free
3. Click "Create Database"
4. Copy the **Internal Database URL** (starts with `postgres://`)

## Step 2: Deploy Application

1. Go to Render Dashboard → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `ai-trip-planner`
   - **Region**: Same as database
   - **Branch**: `main` (or your branch)
   - **Root Directory**: `backend` (if your code is in a subfolder)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

## Step 3: Set Environment Variables

In your Web Service settings, add these environment variables:

### Required Variables

```bash
# Database (use Internal Database URL from Step 1)
DATABASE_URL=<paste-internal-database-url-here>

# Ollama Configuration (won't work on Render free tier - see alternatives below)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# Optional
DEBUG=false
LOG_LEVEL=INFO
```

## Step 4: Deploy

1. Click "Create Web Service"
2. Wait for deployment (5-10 minutes)
3. Your app will be available at: `https://your-app-name.onrender.com`

## Important: Ollama Limitation

**Problem**: Render's free tier doesn't support running Ollama (requires GPU/high memory).

### Solutions:

### Option A: Use External LLM API (Recommended)

Replace Ollama with a cloud LLM service:

1. **OpenAI API**
   - Sign up at https://platform.openai.com
   - Get API key
   - Update `llm.py` to use OpenAI instead of Ollama
   - Add `openai` to `requirements.txt`

2. **Anthropic Claude API**
   - Sign up at https://console.anthropic.com
   - Similar integration as OpenAI

3. **Groq (Free, Fast)**
   - Sign up at https://console.groq.com
   - Free tier with fast inference
   - Compatible with OpenAI SDK

### Option B: Deploy Ollama Separately

1. **Deploy Ollama on Modal.com** (has GPU support)
2. **Use Replicate.com** (pay-per-use)
3. **Self-host Ollama** on a VPS with GPU

### Option C: Disable AI Features Temporarily

Set environment variable:
```bash
ENABLE_AI_RECOMMENDATIONS=false
```

## Step 5: Verify Deployment

1. Visit your app URL
2. Check logs in Render dashboard
3. Test creating a trip
4. If using external LLM, test AI recommendations

## Troubleshooting

### Database Connection Errors

- Verify `DATABASE_URL` is set correctly
- Use **Internal Database URL** (not External)
- Check database is in same region as app

### App Crashes on Startup

- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `requirements.txt` has all dependencies

### Ollama Connection Errors

- Expected on Render free tier
- Use Option A (External LLM API) above
- Or disable AI features with `ENABLE_AI_RECOMMENDATIONS=false`

### Port Binding Errors

- Ensure start command uses `--port $PORT`
- Render assigns port dynamically via `$PORT` variable

## Cost Estimate

### Free Tier (Render)
- Web Service: Free (sleeps after 15min inactivity)
- PostgreSQL: Free (90 days, then $7/month)
- **Total**: Free for 90 days

### With External LLM
- OpenAI: ~$0.002 per request (GPT-3.5)
- Groq: Free tier available
- **Total**: ~$5-20/month depending on usage

## Alternative: Deploy with Docker

If you need Ollama, consider:

1. **Railway.app** - Supports Docker, has GPU plans
2. **Fly.io** - Supports Docker, GPU machines available
3. **AWS/GCP/Azure** - Full control, higher cost
4. **DigitalOcean App Platform** - Docker support

## Files to Update for Production

### 1. Add `Procfile` (optional, for clarity)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 2. Update `config.py`
```python
# Add production settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    # Production-specific settings
    DEBUG = False
    LOG_LEVEL = "WARNING"
```

### 3. Add health check endpoint in `main.py`
```python
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

## Security Checklist for Production

- [ ] Set `DEBUG=false`
- [ ] Use strong database password
- [ ] Enable HTTPS (automatic on Render)
- [ ] Set CORS origins properly
- [ ] Add rate limiting
- [ ] Use environment variables for secrets
- [ ] Enable database backups
- [ ] Monitor error logs

## Next Steps

1. Set up custom domain (optional)
2. Configure monitoring/alerts
3. Set up CI/CD with GitHub Actions
4. Add database migrations (Alembic)
5. Implement caching (Redis)
