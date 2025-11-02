# Agent ML Engineer

A full-stack agentic notebook assistant that streams real-time code, plots, and insights while it tackles your dataset. The system was built for the **Y Combinator Hackathon organised by Metorial** and pairs a Next.js front-end with a LangGraph-powered backend to deliver a smooth “observe the agent work” experience.

<div align="center">
  <img src="frontend/public/globe.svg" alt="Globe" width="140" />
</div>

## Features at a Glance

- **Pre-session workspace** with drag-and-drop CSV upload and markdown-friendly chat.
- **Live notebook view** that renders code, outputs, plots, and artifacts as the agent generates them.
- **Downloadable artifacts** (e.g., notebooks, CSVs, models) per run, hosted from the backend.
- **Session-aware chat sidebar** supporting iterative prompts during an analysis.
- **Streamed execution history** via WebSockets so you see cells appear in real time.

## Tech Stack

| Layer     | Technology                                 |
| --------- | ------------------------------------------ |
| Frontend  | Next.js 14, Tailwind, React Markdown       |
| Backend   | FastAPI, LangChain/LangGraph, Python 3.11+ |
| Streaming | Native WebSockets                          |
| Styling   | Custom dark theme with Tailwind            |

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/agent-ml-engineer.git
cd agent-ml-engineer
```

### 2. Backend Setup

Create and activate a virtual environment, install dependencies, and provide your OpenAI credentials.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env  # create if absent
# Edit .env
OPENAI_API_KEY=sk-...
```

Start the API server:

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
npm run dev
```

By default the Next.js app runs at `http://localhost:3000` and proxies API requests to `http://localhost:8000` (override with `NEXT_PUBLIC_API_BASE`).

## Usage Flow

1. Upload one or more CSV datasets in the pre-session view.
2. Type a question or analysis request and hit send.
3. Watch the Notebook view stream code cells, plots, errors, and summaries live.
4. Download generated artifacts from the sidebar once the run finishes.

Each new prompt creates a fresh agent run while keeping the session context in chat, so you can iterate without losing prior insights.

## Project Structure

```
backend/
  server.py                # FastAPI + websocket orchestration
  ml_engineer/             # Agent, execution engine, notebook generator
  artifacts/               # Per-run results (auto-created)
frontend/
  app/components/          # PreSession, Notebook, Chat sidebar
  app/hooks/               # Session event listeners
  public/                  # Static assets
```

## Development Tips

- Tailwind classes live in `frontend/app/globals.css`.
- Notebook rendering logic is centralised in `frontend/app/components/Cell.tsx`.
- Backend move/cleanup of artifacts happens in `backend/server.py`.
- To reset the agent state between runs without restarting, reuse the same session—history is purged automatically.

## Contributing

Feel free to open issues or submit pull requests. For major changes, start a discussion so we can keep the agent aligned with real-time notebook expectations.

---

Made with ❤️ by Md Aman Khan, Assanali Aukenov, Yelarys Yertaiuly for the YC Hackathon organised the Metorial team.
