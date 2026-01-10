# Railway Usage in RegimeFlex

## 🚂 What is Railway?

**Railway** is a cloud hosting platform (similar to Heroku, Render, or Fly.io) that provides:
- **Serverless/Container hosting** for applications
- **Automatic deployments** from GitHub
- **Environment variable management**
- **Health checks and auto-restarts**
- **Public domain URLs** for services
- **Process management** and monitoring

## 📦 What RegimeFlex Uses Railway For

### 1. **Backend API Server** (Primary Service)

**Deployed Service**: Flask application (`run_http_trigger.py`)

**Purpose**: 
- Hosts the trading system's HTTP API
- Provides endpoints for triggering trades, checking status, and monitoring
- Serves data to the frontend dashboard

**Configuration** (`railway.json`):
```json
{
  "startCommand": "python regimeflex/scripts/run_http_trigger.py",
  "healthcheckPath": "/health",
  "healthcheckTimeout": 100,
  "restartPolicyType": "ON_FAILURE",
  "restartPolicyMaxRetries": 10
}
```

**Endpoints**:
- `GET /trigger-daily` - Execute daily trading cycle
- `GET /health` - Simple health check (for Railway monitoring)
- `GET /health-full` - Detailed health diagnostics
- `GET /replay/latest` - Latest trading replay data (for frontend)
- `GET /status` - System status and receipt
- `GET /incidents` - Recent incident logs

### 2. **Frontend Dashboard** (Potentially Separate Service)

**Deployed Service**: Next.js web application (`web/`)

**Purpose**:
- Provides web dashboard for monitoring trading system
- Displays current regime, positions, and system status
- Connects to backend API for real-time data

**Connection**:
- Frontend calls backend via Railway service URL
- Uses `RAILWAY_SERVICE_URL` or `RAILWAY_PUBLIC_DOMAIN` environment variables
- Falls back to `localhost:8080` for local development

## 🔧 Railway Features Used

### Auto-Deployment
- **GitHub Integration**: Automatically deploys when code is pushed to `main` branch
- **Build Process**: Uses NIXPACKS builder (auto-detects Python)
- **Zero-Downtime**: Deploys new version without stopping service

### Health Monitoring
- **Health Checks**: Railway pings `/health` endpoint every few seconds
- **Auto-Restart**: If health check fails, Railway restarts the service
- **Retry Policy**: Up to 10 retries before marking as failed

### Environment Management
- **Automatic PORT**: Railway sets `PORT` environment variable
- **Custom Variables**: Set via Railway dashboard:
  - `ALPACA_KEY`, `ALPACA_SECRET`
  - `POLYGON_KEY`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - `REGIMEFLEX_TRIGGER_TOKEN`
  - `PYTHON_BACKEND_URL` (for frontend)

### Service Discovery
- **Public Domain**: Railway provides public URL (e.g., `your-app.railway.app`)
- **Service URLs**: Internal service-to-service communication
- **Environment Variables**: `RAILWAY_PUBLIC_DOMAIN`, `RAILWAY_SERVICE_URL`

## 🏗️ Architecture

### Option 1: Single Service (Current)
```
Railway Service
├── Backend API (Flask)
│   └── run_http_trigger.py
└── Frontend (Next.js) - Optional, can be separate
    └── web/
```

### Option 2: Separate Services (Recommended for Production)
```
Railway Project
├── Backend Service
│   └── Flask API (run_http_trigger.py)
│   └── Port: Railway PORT env var
│   └── Public URL: backend.railway.app
│
└── Frontend Service
    └── Next.js Dashboard (web/)
    └── Port: Railway PORT env var
    └── Public URL: frontend.railway.app
    └── Connects to: backend.railway.app
```

## 📊 Current Setup

**Service**: Single Railway service running Flask backend

**Start Command**: `python regimeflex/scripts/run_http_trigger.py`

**Port**: Railway sets `PORT` automatically (Flask uses `os.environ.get("PORT", "5000")`)

**Health Check**: `/health` endpoint returns `{"status": "ok"}`

**Auto-Restart**: On failure, Railway restarts up to 10 times

## 🔍 Monitoring

### Railway Dashboard
- **Logs**: View real-time application logs
- **Metrics**: CPU, memory, network usage
- **Deployments**: View deployment history
- **Environment**: Manage environment variables

### Application Logs
- Check for `SHADOW TEST FAILED` messages
- Monitor `CRITICAL_ERROR` logs
- Review health check responses
- Track API endpoint usage

## 🚀 Deployment Flow

1. **Push to GitHub**: `git push origin main`
2. **Railway Detects**: Railway watches GitHub repository
3. **Auto-Build**: Railway builds Docker container (via NIXPACKS)
4. **Auto-Deploy**: New version deployed automatically
5. **Health Check**: Railway pings `/health` endpoint
6. **Service Live**: Application available at Railway URL

## 💰 Cost Considerations

Railway offers:
- **Free Tier**: Limited hours/month
- **Pro Tier**: Pay-as-you-go pricing
- **Cost Factors**: 
  - CPU usage
  - Memory usage
  - Network egress
  - Build minutes

## 🔗 Related Files

- `railway.json` - Railway deployment configuration
- `regimeflex/scripts/run_http_trigger.py` - Flask API server
- `web/app/api/regime/route.ts` - Frontend API route (connects to Railway backend)
- `RAILWAY_CONNECTION_FIX.md` - Connection troubleshooting guide

## 📝 Summary

**Railway is used for**:
1. ✅ Hosting the Flask backend API server
2. ✅ Providing HTTP endpoints for trading operations
3. ✅ Serving data to the frontend dashboard
4. ✅ Auto-deployment from GitHub
5. ✅ Health monitoring and auto-restarts
6. ✅ Environment variable management
7. ✅ Public URL for external access

**Benefits**:
- Zero-configuration deployment
- Automatic scaling and restarts
- Easy environment management
- GitHub integration
- Health monitoring built-in

