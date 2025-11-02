# ML Engineer Agent - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│  "Build a classification model to predict customer churn"       │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ML ENGINEER AGENT                             │
│                   (LangGraph Workflow)                           │
│                                                                  │
│  ┌────────────┐         ┌────────────┐                         │
│  │  GENERATE  │◄───────►│  EXECUTE   │                         │
│  │   (LLM)    │         │  (Tools)   │                         │
│  └────────────┘         └────────────┘                         │
│        │                      │                                 │
│        │                      ├─► dataset_info()               │
│        │                      └─► execute_python()             │
│        │                                                        │
│        └─► Iteration Control (max 15)                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ARTIFACT GENERATION                           │
│                                                                  │
│  ├─ Plots (PNG files)                                          │
│  ├─ Conversation Log (TXT)                                     │
│  ├─ Execution History (Python dict)                           │
│  └─ Jupyter Notebook (IPYNB)                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                  ml_engineer/                           │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ agent.py                                         │  │   │
│  │  │ - MLEngineerAgent                                │  │   │
│  │  │ - LangGraph workflow setup                       │  │   │
│  │  │ - System prompt generation                       │  │   │
│  │  │ - Run/stream execution                           │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ python_executor.py                               │  │   │
│  │  │ - run_python_repl()                              │  │   │
│  │  │ - PlotCapture context manager                    │  │   │
│  │  │ - Persistent namespace (_persistent_namespace)   │  │   │
│  │  │ - Execution history tracking                     │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ tools.py                                         │  │   │
│  │  │ - @tool dataset_info()                           │  │   │
│  │  │ - @tool execute_python()                         │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ datasets.py                                      │  │   │
│  │  │ - DatasetResolver.resolve()                      │  │   │
│  │  │ - load_dataset()                                 │  │   │
│  │  │ - get_dataset_info()                             │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ notebook_generator.py                            │  │   │
│  │  │ - NotebookGenerator                              │  │   │
│  │  │ - generate_from_execution_history()              │  │   │
│  │  │ - _infer_section_name()                          │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │ config.py                                        │  │   │
│  │  │ - Config class                                   │  │   │
│  │  │ - Environment variables                          │  │   │
│  │  │ - Path management                                │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ usage.py - CLI Entry Point                             │   │
│  │ - Typer commands                                       │   │
│  │ - Rich UI formatting                                   │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## LangGraph Workflow

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  GENERATE   │
                    │   (Node)    │
                    │             │
                    │ - LLM call  │
                    │ - Reasoning │
                    │ - Tool call │
                    │   decision  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   ROUTING   │
                    │  (Cond.)    │
                    └──┬─────┬────┘
                       │     │
              Has tool │     │ No tools /
              calls?   │     │ <solution>
                       │     │
                 ┌─────▼─┐   │
                 │ TOOLS │   │
                 │(Node) │   │
                 │       │   │
                 │Execute│   │
                 │tools  │   │
                 └───┬───┘   │
                     │       │
                     │       │
              ┌──────▼───────▼────┐
              │   Iteration < Max? │
              └──┬──────────────┬──┘
                 │              │
          Yes    │              │ No / Done
                 │              │
          ┌──────▼──────┐       │
          │   GENERATE  │       │
          │  (continue) │       │
          └─────────────┘       │
                                │
                         ┌──────▼──────┐
                         │     END     │
                         │             │
                         │ - Solution  │
                         │ - Artifacts │
                         └─────────────┘
```

## State Flow

```python
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]  # Conversation history
    next_step: str | None            # Routing decision
```

### Message Types

1. **SystemMessage**: Agent instructions and context
2. **HumanMessage**: User's task prompt
3. **AIMessage**: LLM responses (with tool calls)
4. **ToolMessage**: Tool execution results

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                                │
├─────────────────────────────────────────────────────────────────┤
│   - Load dataset from datasets/                                 │
│   - Inject into persistent namespace as 'df'                    │
│   - Pre-import common libraries (pandas, numpy, etc.)           │
│   - Create artifacts directory                                  │
│   - Initialize LLM and tools                                    │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. AGENT LOOP (max 15 iterations)                               │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ GENERATE NODE                                           │  │
│   │ - LLM receives system prompt + conversation history     │  │
│   │ - LLM decides: inspect data, run code, or finish        │  │
│   │ - Returns AIMessage with optional tool calls            │  │
│   └─────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ ROUTING                                                  │  │
│   │ - Has tool calls? → Execute tools                       │  │
│   │ - Has <solution>? → End                                 │  │
│   │ - Otherwise → End (max iterations or no action)         │  │
│   └─────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ TOOLS NODE (if tool calls)                              │  │
│   │ - Execute dataset_info() or execute_python()            │  │
│   │ - Capture outputs, plots, errors                        │  │
│   │ - Add ToolMessage to conversation                       │  │
│   │ - Loop back to GENERATE                                 │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. POST-PROCESSING                                               │
├─────────────────────────────────────────────────────────────────┤
│   - Save plots to artifacts/                                    │
│   - Generate Jupyter notebook                                   │
│   - Save conversation log                                       │
│   - Return results to user                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Tool Execution Detail

### dataset_info Tool

```
Input: dataset_path (string)
    │
    ▼
┌───────────────────────┐
│ Load dataset          │
│ (pandas read_csv)     │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ Extract metadata:     │
│ - Shape               │
│ - Column names/types  │
│ - Missing values      │
│ - Numeric stats       │
│ - Preview rows        │
└──────────┬────────────┘
           │
           ▼
Output: Formatted string with dataset info
```

### execute_python Tool

```
Input: code (string)
    │
    ▼
┌───────────────────────────────┐
│ PlotCapture.__enter__()       │
│ - Monkey-patch plt.show()     │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ exec(code, namespace)         │
│ - Persistent namespace        │
│ - Timeout protection          │
│ - Capture stdout/stderr       │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ PlotCapture.__exit__()        │
│ - Collect plot base64 data    │
│ - Restore original plt.show() │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Return execution result:      │
│ - output (stdout)             │
│ - error (stderr/exceptions)   │
│ - plots (list of base64)      │
│ - success (boolean)           │
└───────────────────────────────┘
```

## Persistent Namespace

```python
# Global persistent namespace
_persistent_namespace = {}

# First execution
exec("import pandas as pd\ndf = pd.DataFrame(...)", _persistent_namespace)
# _persistent_namespace now contains: {'pd': <module>, 'df': <DataFrame>}

# Second execution (same namespace)
exec("print(df.shape)", _persistent_namespace)
# Can access 'df' from previous execution
# Output: (100, 5)

# Third execution
exec("df['new_col'] = df['old_col'] * 2", _persistent_namespace)
# Modifies the same DataFrame
```

## Notebook Generation Flow

```
Execution History
    │
    ├─ Execution 1: {code, output, plots, success}
    ├─ Execution 2: {code, output, plots, success}
    └─ Execution N: {code, output, plots, success}
            │
            ▼
┌─────────────────────────────────┐
│ NotebookGenerator               │
│                                 │
│ For each execution:             │
│   1. Infer section name         │
│      (EDA, Model, etc.)         │
│   2. Create markdown cell       │
│      with section header        │
│   3. Create code cell           │
│      with code + outputs        │
│   4. Attach plots as outputs    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Jupyter Notebook (.ipynb)       │
│                                 │
│ {                               │
│   "cells": [                    │
│     {"cell_type": "markdown"},  │
│     {"cell_type": "code"},      │
│     ...                         │
│   ],                            │
│   "metadata": {...},            │
│   "nbformat": 4                 │
│ }                               │
└─────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────┐
│ Dataset  │
│  (CSV)   │
└────┬─────┘
     │
     │ DatasetResolver.resolve()
     ▼
┌────────────┐
│ Dataset    │
│  Path      │
└────┬───────┘
     │
     │ load_dataset()
     ▼
┌────────────┐
│ DataFrame  │
│   (df)     │
└────┬───────┘
     │
     │ inject_variables()
     ▼
┌────────────────────┐
│ Persistent         │
│ Namespace          │
│                    │
│ {                  │
│   'df': DataFrame, │
│   'pd': pandas,    │
│   'np': numpy,     │
│   ...              │
│ }                  │
└────────┬───────────┘
         │
         │ execute_python()
         │ (multiple times)
         ▼
┌────────────────────┐
│ Execution History  │
│                    │
│ [                  │
│   {code, output,   │
│    plots, ...},    │
│   ...              │
│ ]                  │
└────────┬───────────┘
         │
         │ generate_notebook()
         ▼
┌────────────────────┐
│ Jupyter Notebook   │
│   (.ipynb)         │
└────────────────────┘
```

## File System Layout

```
agent-ml-engineer/backend/
│
├── ml_engineer/              # Core package
│   ├── __init__.py
│   ├── agent.py             # 300+ lines - Main agent logic
│   ├── config.py            # 50 lines - Configuration
│   ├── datasets.py          # 150 lines - Dataset handling
│   ├── notebook_generator.py # 250 lines - Notebook creation
│   ├── python_executor.py   # 200 lines - Code execution
│   └── tools.py             # 75 lines - LangChain tools
│
├── datasets/                # Input datasets
│   ├── sample_sales.csv
│   └── XAU_15m_data.csv
│
├── runs/                    # Generated logs (auto-created)
│   └── 20241102_143022_sample_sales.txt
│
├── artifacts/               # Generated outputs (auto-created)
│   └── 20241102_143022_sample_sales/
│       ├── plot_001.png
│       ├── plot_002.png
│       └── sample_sales_pipeline.ipynb
│
├── usage.py                 # CLI entry point
├── test_agent.py           # Test suite
├── example_run.py          # Programmatic example
├── requirements.txt        # Dependencies
├── .env                    # Configuration (not in git)
└── .env.example           # Template
```

## Dependency Graph

```
usage.py
  │
  ├─► ml_engineer.agent
  │     │
  │     ├─► ml_engineer.config
  │     ├─► ml_engineer.tools
  │     │     │
  │     │     ├─► ml_engineer.datasets
  │     │     └─► ml_engineer.python_executor
  │     │
  │     └─► ml_engineer.datasets
  │
  └─► ml_engineer.notebook_generator
```

## External Dependencies

```
LangChain Ecosystem
  ├─► langchain (core framework)
  ├─► langchain-core (abstractions)
  ├─► langchain-openai (OpenAI integration)
  └─► langgraph (state machine)

OpenAI
  └─► openai (API client)

ML Stack
  ├─► pandas (data manipulation)
  ├─► numpy (numerical computing)
  ├─► matplotlib (plotting)
  ├─► seaborn (statistical viz)
  └─► scikit-learn (ML algorithms)

CLI/UI
  ├─► typer (CLI framework)
  └─► rich (terminal UI)

Utilities
  └─► python-dotenv (env vars)
```

## Key Design Patterns

### 1. **Persistent Context Pattern**
- Global namespace preserves state across executions
- Enables multi-step workflows without explicit state passing

### 2. **Monkey Patching Pattern**
- `PlotCapture` intercepts `plt.show()` calls
- Transparently captures plots without code changes

### 3. **Tool Abstraction Pattern**
- LangChain `@tool` decorator for LLM integration
- Clean separation between tool logic and agent logic

### 4. **State Machine Pattern**
- LangGraph manages complex agent workflow
- Clear transitions between generate and execute phases

### 5. **Artifact Generation Pattern**
- All outputs stored with timestamp + dataset name
- Organized directory structure for reproducibility

## Scalability Considerations

### Current Scale
- **Datasets**: Small to medium (< 1GB)
- **Iterations**: 15 max (configurable)
- **Concurrent runs**: 1 (sequential)
- **Code timeout**: 60 seconds

### Scaling Options
- **Larger datasets**: Add chunking/sampling
- **Parallel execution**: Use Ray or Dask
- **Distributed LLM**: Use local models (Ollama)
- **Caching**: Cache dataset info, execution results

## Security Considerations

- ⚠️ **Code execution**: Runs arbitrary Python code
- ⚠️ **API keys**: Stored in .env (not committed)
- ⚠️ **Timeout**: Prevents infinite loops
- ⚠️ **Sandboxing**: Not implemented (runs in same process)

### Production Recommendations
- Use Docker containers for isolation
- Implement resource limits (CPU, memory)
- Add code review/approval step
- Use read-only dataset mounts
