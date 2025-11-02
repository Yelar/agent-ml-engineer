# ML Engineer Agent with Vercel AI SDK

A production-ready ML Engineer Agent built with Vercel AI SDK, LangGraph, and shadcn/ui.

## 🎯 Features

- **Natural Language ML** - Describe what you want, the agent builds it
- **Real-time Streaming** - Watch code execute and results appear live
- **Beautiful UI** - shadcn/ui components with smooth animations
- **Type-safe** - Full TypeScript throughout
- **Production Ready** - Proper error handling, auth ready, database ready

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- pnpm

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python api_server.py
```

Backend runs on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd ai-chatbot
pnpm install
cp .env.local.example .env.local
# Edit .env.local with your credentials
pnpm dev
```

Frontend runs on `http://localhost:3000`

### 3. Environment Variables

Create `ai-chatbot/.env.local`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
AI_GATEWAY_URL=https://gateway.ai.vercel.app/v1
# Add your Vercel AI Gateway credentials
```

## 📖 Usage

Open `http://localhost:3000` and try:

```
"Analyze the sales data"
"What datasets are available?"
"Build a regression model to predict sales"
"Create a correlation heatmap"
"Clean the data and handle missing values"
```

## 🏗 Architecture

```
User Query
  ↓
Vercel AI SDK Chat (useChat hook)
  ↓
runMLAnalysis Tool
  ↓
Backend FastAPI (SSE Streaming)
  ↓
ML Engineer Agent (LangGraph)
  ↓
Python Execution (pandas, sklearn, matplotlib)
  ↓
Stream Results Back
  ↓
Beautiful shadcn UI
```

## 📦 Tech Stack

### Frontend
- **Next.js 15** - React framework
- **Vercel AI SDK** - AI chat with streaming
- **shadcn/ui** - Beautiful UI components
- **Tailwind CSS** - Styling
- **TypeScript** - Type safety

### Backend
- **FastAPI** - API framework
- **LangGraph** - Agent orchestration
- **LangChain** - LLM integration
- **pandas/numpy** - Data processing
- **scikit-learn** - ML models
- **matplotlib/seaborn** - Visualizations

## 🔧 How It Works

### 1. User asks a question

```
"Build a model to predict house prices"
```

### 2. AI decides to use runMLAnalysis tool

The Vercel AI SDK automatically calls the appropriate tool based on the user's query.

### 3. Tool calls backend API

```typescript
POST http://localhost:8000/api/ml/analyze
{
  "prompt": "Build a model to predict house prices",
  "dataset": "house_prices"
}
```

### 4. Backend streams execution

- Planning phase
- Thinking process
- Code execution
- Results and insights

### 5. Frontend displays beautifully

All streamed content appears in real-time with:
- Status indicators
- Code blocks with syntax highlighting
- Execution outputs
- Final summary

## 📁 Project Structure

```
ai-chatbot/
├── app/(chat)/
│   ├── page.tsx              # Main chat page
│   └── api/chat/route.ts     # AI SDK chat endpoint
├── components/
│   ├── chat.tsx              # Main chat component
│   ├── message.tsx           # Message renderer
│   ├── ml-data-handler.tsx   # ML streaming handler
│   └── elements/
│       └── ml-analysis.tsx   # ML results UI
└── lib/ai/tools/
    ├── run-ml-analysis.ts    # ML analysis tool
    └── list-datasets.ts      # Dataset listing tool

backend/
├── api_server.py             # FastAPI SSE server
├── ml_engineer/
│   ├── agent.py              # LangGraph agent
│   ├── python_executor.py   # Code execution
│   └── datasets.py           # Dataset handling
└── requirements.txt          # Python dependencies
```

## 🎨 UI Components

All components use shadcn/ui:
- `Card` - Content containers
- `Badge` - Status indicators  
- `Button` - Actions
- Icons from `lucide-react`
- Beautiful animations with `framer-motion`

## 🔐 Security

- ✅ Sandboxed Python execution
- ✅ Input validation with Zod
- ✅ CORS configured properly
- ✅ Auth ready (NextAuth integration points ready)

## 📊 Supported Datasets

Place CSV files in `backend/datasets/`:
- `sample_sales.csv` (included)
- `office_train.csv` (included)
- `office_test.csv` (included)

Add your own by dropping CSV files in the datasets folder!

## 🛠 Development

### Adding New Tools

Create a new tool in `ai-chatbot/lib/ai/tools/`:

```typescript
import { tool } from "ai";
import { z } from "zod";

export function myTool({ dataStream }: { dataStream: any }) {
  return tool({
    description: "What this tool does",
    inputSchema: z.object({
      param: z.string(),
    }),
    execute: async ({ param }) => {
      // Tool logic
      return { result: "success" };
    },
  });
}
```

Then add to `app/(chat)/api/chat/route.ts`:

```typescript
import { myTool } from "@/lib/ai/tools/my-tool";

// In tools object:
tools: {
  myTool: myTool({ dataStream }),
  // ... other tools
}
```

### Adding UI Components

Create components in `components/elements/` following shadcn patterns:

```typescript
import { Card } from "@/components/ui/card";

export function MyComponent() {
  return (
    <Card>
      <CardContent>
        {/* Your content */}
      </CardContent>
    </Card>
  );
}
```

## 🐛 Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.9+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is free: `lsof -i :8000`

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Clear node_modules: `rm -rf node_modules && pnpm install`
- Check .env.local exists with correct values

### Agent not responding
- Check backend is running: `curl http://localhost:8000`
- Check NEXT_PUBLIC_BACKEND_URL in .env.local
- Check browser console for errors

## 📝 License

MIT

## 🙏 Credits

Built with:
- [Vercel AI SDK](https://sdk.vercel.ai)
- [shadcn/ui](https://ui.shadcn.com)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [FastAPI](https://fastapi.tiangolo.com)

---

**Ready to build?** Start both servers and ask the agent to analyze some data! 🚀

