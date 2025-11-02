# Backend Integration Setup

Your backend is now ready to handle all LLM logic! Here's how to complete the setup:

## Quick Setup

### 1. Backend Setup

```bash
cd backend

# Create .env file (if not exists)
cp .env.example .env

# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-actual-key-here
# DEFAULT_MODEL=gpt-4o-mini

# Install dependencies (if not done)
pip install -r requirements.txt

# Start backend
python api_server.py
```

Backend should start on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Create .env.local file
cat > .env.local << EOF
NEXT_PUBLIC_USE_BACKEND=true
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Database (Required)
POSTGRES_URL=your-postgres-connection-string

# Auth Secret (Required)
AUTH_SECRET=$(openssl rand -base64 32)
EOF

# Install dependencies
pnpm install

# Start frontend
pnpm dev
```

Frontend should start on `http://localhost:3000`

## What Changed

### Backend (`api_server.py`)

Added these endpoints:
- `/v1/chat/completions` - OpenAI-compatible endpoint for AI SDK
- `/v1/responses` - Alternative endpoint (some AI SDK versions use this)
- `/api/ml/analyze` - Your ML agent workflow (existing)
- `/datasets` - List available datasets (existing)

All LLM calls now go through your backend → your OpenAI API key.

### Frontend (`providers.ts`)

Already configured to use backend:
```typescript
const backendOpenAI = createOpenAI({
  baseURL: `${BACKEND_URL}/v1`,
  apiKey: "not-needed", // Backend handles this
});
```

## Testing

1. Open browser to `http://localhost:3000`
2. Log in / register
3. Start a chat
4. Try: "What datasets are available?"
5. Try: "Analyze the sample_sales dataset"

## Debug Output

Your backend now has debug logging. When you make a request, you'll see:
```
📥 Received request: {...}
📝 Messages count: 2, Model: gpt-4o-mini, Stream: true
  Message 0: role=system, content_length=150
  Message 1: role=user, content_length=42
✅ Converted 2 messages for LLM
```

## Common Issues

### 404 on /v1/responses
**Fixed!** Added the endpoint proxy.

### Empty messages array
Check the debug output. If you see empty messages, it means the frontend isn't sending messages correctly. This usually happens with title generation.

### OpenAI API Key Error
Make sure `OPENAI_API_KEY` is set in `backend/.env`

### Frontend can't reach backend
1. Check backend is running on port 8000
2. Check CORS settings in `api_server.py` (already configured)
3. Verify `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` in frontend `.env.local`

## Architecture

```
User Browser
    ↓
Frontend (Next.js) - Port 3000
    ↓
Backend API - Port 8000
    ↓
OpenAI API (your key)
```

All ML logic, prompts, and tools run on your backend. Frontend is just a streaming client.

## Environment Variables Summary

### Backend `.env`
```bash
OPENAI_API_KEY=sk-...  # Required
DEFAULT_MODEL=gpt-4o-mini  # Optional
```

### Frontend `.env.local`
```bash
NEXT_PUBLIC_USE_BACKEND=true
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
POSTGRES_URL=postgresql://...
AUTH_SECRET=your-secret-here
```

## Next Steps

1. **Restart backend** with the new changes
2. Try a chat request
3. Check terminal for debug logs
4. If you see empty messages, let me know what the debug output shows

The main issue was `/v1/responses` returning 404 - now fixed. The empty messages issue will be visible in debug logs.

