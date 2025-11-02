# ML Engineer Agent

This project contains an ML engineer agent that uses LangChain and LangGraph to plan, generate, and execute Python code against tabular datasets.

## Prerequisites

1. **Python 3.9+** 
2. **OpenAI API key** with access to the chosen chat model (default `gpt-4o-mini`).

## Setup

```bash
cd agent-ml-engineer/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside `backend/` with:

```
OPENAI_API_KEY=sk-...
```

## Running the Agent


```bash
cd agent-ml-engineer/backend
python usage.py --prompt "Explore revenue drivers" --dataset sample_sales
```

### CLI Options

- `--prompt`: High-level user objective (required).
- `--dataset` / `-d`: Dataset identifier (`sample_sales`, `xau_intraday`) or path to a CSV file.
- `--model`: OpenAI chat model (default `gpt-4o-mini`).
- `--max-iterations`: Safety cap for agent turns (default `12`).

Output is streamed to the terminal and saved to `runs/<timestamp>_<dataset>.txt`.

## Tooling Overview

Two tools are exposed to the agent:

1. `dataset_info` – inspects the dataset (columns, dtypes, preview) to ground reasoning.
2. `run_python` – executes Python code in a persistent namespace with `DATASET_PATH` defined.

The agent decides when to call each tool.

## Sample Prompts

- `Summarize top regions and channels driving revenue growth.`
- `Build a simple regression model predicting marketing ROI from the sales dataset.`
- `Identify intraday volatility patterns in gold prices and explain main factors.`

## Project Structure

```
backend/
├── cli.py               # LangGraph-based CLI entrypoint
├── ml_engineer/
│   ├── agent.py         # LangGraph workflow definition
│   ├── datasets.py      # Built-in dataset catalog & resolver
│   ├── python_executor.py
│   └── tools.py         # LangChain tool definitions
└── usage.py             # Convenient `python usage.py` runner
```

Happy hacking!
