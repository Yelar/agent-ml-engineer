# ML Engineer Agent

Build complete ML pipelines from natural language prompts using GPT-5 with reasoning.

## Quick Start

```bash
# 1. Setup
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (add your OpenAI API key to .env)
cp .env.example .env

# 3. Run!
python example_run.py
```

That's it! The agent will build a complete ML pipeline with planning, execution, and Jupyter notebook generation.

## Features

- **Automated ML Pipeline Creation**: Describe your task in natural language, and the agent builds the complete pipeline
- **Multiple Dataset Support**: Work with train/test splits or multiple related datasets simultaneously
- **Smart Planning**: Creates TODO lists with status tracking (`[✓]` completed, `[ ]` pending, `[X]` failed) saved to PLAN.md
- **Dataset Analysis**: Automatic exploratory data analysis with visualizations
- **Model Building**: Trains and evaluates ML models appropriate for your data
- **Artifact Storage**: All plots, code chunks, plans, and outputs are saved for later use
- **Jupyter Notebook Generation**: Deterministically converts executed code chunks into separate notebook cells with proper formatting
- **Persistent Execution**: Code executions are connected - variables and imports persist across steps
- **Flexible System Prompt**: Generic, task-adaptive prompt without hardcoded assumptions or library requirements
- **Readable Code Display**: Executed code shown in terminal with proper formatting (multi-line, not compressed)
- **Manual Dataset Loading**: Datasets not pre-loaded - agent writes code to load them, making execution more transparent
- **Visual Feedback Loop**: Agent can see the plots it generates - images included in message history for iterative refinement

## Architecture


- **LangGraph workflow**: State machine with generate and execute nodes
- **Tool system**: LangChain tools for dataset inspection and code execution
- **Python REPL**: Persistent namespace with automatic plot capture (matplotlib)
- **Artifact management**: Structured storage of outputs, plots, and generated code

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
DEFAULT_MODEL=gpt-5
REASONING_EFFORT=medium
```

## Usage

### Quick Start (Recommended)

Run the example script with GPT-5 and high reasoning effort:

```bash
python example_run.py
```

This will:
- Use GPT-5 with high reasoning effort
- Build a complete ML pipeline using **office_train** and **office_test** datasets
- Show verbose output with planning and thinking
- Generate plots and Jupyter notebook
- Perfect for train/test ML workflows!

### CLI Usage

```bash
python usage.py --prompt "Build a classification model to predict customer churn" --dataset sample_sales
```

### List Available Datasets

```bash
python usage.py list-datasets
```

### Advanced CLI Options

```bash
python usage.py \
  --prompt "Build ensemble model with feature selection" \
  --dataset sample_sales \
  --model gpt-5 \
  --reasoning-effort high \
  --max-iterations 20 \
  --verbose
```

### CLI Options

- `--prompt, -p`: Task description (required)
- `--dataset, -d`: Dataset name or path (required)
- `--model, -m`: OpenAI model to use (default: gpt-5)
- `--reasoning-effort`: GPT-5 reasoning level: low, medium, high (default: medium)
- `--max-iterations`: Maximum agent iterations (default: 15)
- `--notebook/--no-notebook`: Generate Jupyter notebook (default: true)
- `--verbose/--quiet`: Show detailed output (default: verbose)
- `--planning/--no-planning`: Enable planning mode (default: planning)

## Example Usage

### 1. Run Example Script (Easiest)

```bash
python example_run.py
```

Runs a complete ML pipeline with:
- GPT-5 with high reasoning effort
- Full verbose output showing planning, thinking, and execution
- Automatic Jupyter notebook generation

### 2. Custom Task with CLI

```bash
# Simple exploration (low reasoning)
python usage.py \
  --prompt "Explore the dataset and show summary statistics" \
  --dataset sample_sales \
  --reasoning-effort low

# Standard model building (medium reasoning)
python usage.py \
  --prompt "Build a regression model to predict revenue" \
  --dataset sample_sales \
  --reasoning-effort medium

# Complex analysis (high reasoning)
python usage.py \
  --prompt "Build ensemble model with automated feature selection and hyperparameter tuning" \
  --dataset sample_sales \
  --reasoning-effort high
```

### 3. Programmatic Usage

```python
from ml_engineer.agent import MLEngineerAgent

agent = MLEngineerAgent(
    dataset_path="sample_sales",
    model_name="gpt-5",
    reasoning_effort="high",
    verbose=True,
    planning_mode=True
)

result = agent.run("Build a classification model with feature importance")
print(f"Solution: {result['solution']}")
print(f"Plots: {len(result['plot_paths'])}")
```

### 4. Multiple Datasets (Train/Test)

```python
from ml_engineer.agent import MLEngineerAgent

# Use multiple datasets simultaneously
agent = MLEngineerAgent(
    dataset_path=["office_train", "office_test"],  # List of datasets
    model_name="gpt-5",
    reasoning_effort="high",
    verbose=True
)

result = agent.run("""
Build a complete ML pipeline:
1. Train on df_office_train
2. Test on df_office_test
3. Evaluate and compare performance
""")

# Datasets accessed as: df_office_train, df_office_test
```

See [MULTI_DATASET.md](../MULTI_DATASET.md) for details.
```

## Output Structure

After running `example_run.py` or `usage.py`, the agent creates:

```
backend/
├── runs/
│   └── 20241102_143022_sample_sales.txt     # Conversation log with full trace
├── artifacts/
│   └── 20241102_143022_sample_sales/
│       ├── PLAN.md                           # TODO list with checkboxes [X] / [ ]
│       ├── plot_001.png                      # Generated visualizations
│       ├── plot_002.png
│       ├── plot_003.png
│       └── sample_sales_pipeline.ipynb       # Complete Jupyter notebook
```

**PLAN.md** contains the agent's TODO list with progress tracking:
```markdown
**TODO List:**
- [✓] Step 1: Data Exploration and Understanding
- [✓] Step 2: Data Quality Assessment
- [ ] Step 3: Model Training (in progress)
- [X] Step 4: Feature Engineering (failed - needs retry)
- [ ] Step 5: Model Evaluation
```

**Status Markers:**
- `[✓]` = Completed successfully
- `[ ]` = Pending / Not started
- `[X]` = Failed or encountered errors

**To view results**:
```bash
# View the plan
cat artifacts/*/PLAN.md

# Open Jupyter notebook
jupyter notebook artifacts/*/sample_sales_pipeline.ipynb

# View conversation log
cat runs/*.txt

# View plots
open artifacts/*/plot_*.png
```

## How It Works

### Quick Start Flow

1. **Run example**: `python example_run.py`
2. **Agent plans**: Creates detailed plan with steps
3. **Agent executes**: Runs code, generates plots, builds models
4. **Results saved**: Notebook, plots, and logs saved to artifacts/
5. **Review**: Open notebook to see complete pipeline

### Detailed Workflow

### 1. Agent Initialization

- Loads the specified dataset
- Injects it into a persistent Python namespace as `df`
- Pre-imports common libraries (pandas, numpy, matplotlib, seaborn, sklearn)
- Initializes GPT-5 with specified reasoning effort

### 2. Execution Loop

The agent follows a ReAct-style loop:

1. **Generate**: LLM decides next action (inspect data, run code, etc.)
2. **Execute**: Runs tools or code in the persistent environment
3. **Observe**: Captures outputs, plots, and errors
4. **Repeat**: Until task is complete or max iterations reached

### 3. Code Execution

- All Python code runs in a **persistent namespace**
- Variables and imports carry over between executions
- Matplotlib plots are **automatically captured** as base64 images
- Timeout protection prevents infinite loops

### 4. Artifact Generation

- **Plots**: Saved as PNG files
- **Code history**: All executed code chunks stored
- **Conversation log**: Complete agent reasoning and outputs
- **Jupyter notebook**: Each executed code chunk becomes a separate cell (deterministic, preserves execution order)

## Tools Available to Agent

### 1. `dataset_info`

Inspects the dataset structure:
- Column names and types
- Missing value analysis
- Numeric summaries
- Data preview

### 2. `execute_python`

Executes Python code with:
- Access to the dataset as `df`
- Pre-imported libraries
- Persistent namespace
- Automatic plot capture

## Project Structure

```
backend/
├── ml_engineer/
│   ├── __init__.py
│   ├── agent.py              # LangGraph agent implementation
│   ├── config.py             # Configuration management
│   ├── datasets.py           # Dataset resolution and loading
│   ├── python_executor.py   # REPL with plot capture
│   ├── tools.py              # LangChain tool definitions
│   └── notebook_generator.py # Jupyter notebook creation
├── datasets/
│   ├── sample_sales.csv
│   └── XAU_15m_data.csv
├── usage.py                  # CLI entry point
├── requirements.txt
└── .env                      # Configuration (create from .env.example)
```

## Extending the Agent

### Add Custom Tools

```python
from langchain_core.tools import tool
from typing import Annotated

@tool
def my_custom_tool(param: Annotated[str, "Description"]) -> str:
    """Tool description for the LLM"""
    # Implementation
    return result

# Add to tools.py create_tool_list()
```

### Add More Datasets

Simply place CSV files in `backend/datasets/` or reference external paths.

### Customize System Prompt

Edit `agent.py::_create_system_prompt()` to adjust agent behavior.

## Troubleshooting

### Import Errors

Make sure virtual environment is activated and dependencies installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### OpenAI API Errors

Check that `.env` has valid `OPENAI_API_KEY`.

### Timeout Errors

Increase timeout in `.env`:
```
TIMEOUT_SECONDS=120
```

Or use `--max-iterations` to give agent more time.
