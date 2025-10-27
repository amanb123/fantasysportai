# Deployment Guide

## Frontend Deployment (Vercel)

The frontend is configured to deploy to Vercel automatically.

### Setup

1. **Connect your GitHub repo to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your `fantasysportai` repository
   - Vercel will auto-detect the configuration from `vercel.json`

2. **Configure Environment Variables in Vercel**
   - Go to Project Settings → Environment Variables
   - Add the following:
     - `VITE_API_BASE_URL` = Your backend URL (e.g., `https://your-backend.railway.app`)
     - `VITE_WS_BASE_URL` = Your WebSocket URL (e.g., `wss://your-backend.railway.app`)

3. **Deploy**
   - Vercel will automatically build and deploy on every push to `main`
   - Build command: `cd frontend && npm install && npm run build`
   - Output directory: `frontend/dist`

## Backend Deployment (Railway/Render/Fly.io)

The backend requires:
- Python 3.11+
- Redis instance
- Environment variables from `backend/.env`

### Recommended Platform: Railway

1. **Create new project** on [railway.app](https://railway.app)
2. **Add Redis service** (from Railway templates)
3. **Deploy backend**:
   - Connect your GitHub repo
   - Set root directory to `/backend`
   - Add environment variables:
     - `REDIS_HOST` = (provided by Railway Redis)
     - `REDIS_PORT` = (provided by Railway Redis)
     - `OPENAI_API_KEY` = Your OpenAI key
     - `NBA_MCP_ENABLED` = `false` (MCP won't work in serverless)
     - All other variables from `backend/.env.example`

4. **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Alternative: Render.com

Similar setup to Railway, but you'll need to:
- Create a Redis instance separately
- Add web service for the FastAPI backend
- Configure build and start commands

## Full Stack Local Development

```bash
# Start backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 3002

# Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Environment Variables Reference

### Frontend (.env.production)
```
VITE_API_BASE_URL=https://your-backend-url.com
VITE_WS_BASE_URL=wss://your-backend-url.com
VITE_POLLING_INTERVAL=2000
VITE_TOKEN_STORAGE_KEY=fantasy_bb_token
```

### Backend (.env)
See `backend/.env.example` for full list.

## Notes

- **NBA MCP Server**: Not recommended for serverless deployment (requires subprocess)
- **Redis**: Required for caching - use Railway/Render's managed Redis
- **CORS**: Backend is configured to accept requests from your Vercel domain
- **WebSockets**: May need additional configuration depending on hosting platform
