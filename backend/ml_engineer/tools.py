"""
ML-specific tools for the agent
"""

from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool

from .datasets import get_dataset_info, load_dataset
from .python_executor import run_python_repl, format_execution_output
from .config import Config


@tool
def dataset_info(dataset_path: Annotated[str, "Path to the dataset file"]) -> str:
    """
    Get comprehensive information about a dataset including:
    - Shape (rows and columns)
    - Column names and data types
    - Missing values analysis
    - Numeric summary statistics
    - Data preview (first 5 rows)

    Use this before loading data to understand its structure.
    """
    try:
        info = get_dataset_info(Path(dataset_path))

        output = []
        output.append(f"Dataset: {info['name']}")
        output.append(f"Shape: {info['shape'][0]} rows × {info['shape'][1]} columns")
        output.append(f"\nColumns and Types:")

        for col, dtype in info['dtypes'].items():
            missing = info['missing_values'][col]
            missing_pct = (missing / info['shape'][0] * 100) if info['shape'][0] > 0 else 0
            output.append(f"  - {col}: {dtype} (missing: {missing}, {missing_pct:.1f}%)")

        if 'numeric_summary' in info:
            output.append(f"\nNumeric Columns Summary:")
            import pandas as pd
            summary_df = pd.DataFrame(info['numeric_summary'])
            output.append(summary_df.to_string())

        output.append(f"\nFirst 5 rows:")
        import pandas as pd
        preview_df = pd.DataFrame(info['preview'])
        output.append(preview_df.to_string())

        return "\n".join(output)

    except Exception as e:
        return f"Error getting dataset info: {str(e)}"


@tool
def execute_python(code: Annotated[str, "Python code to execute"]) -> str:
    """
    Execute Python code in a persistent namespace.

    - Variables and imports persist across calls
    - Dataset path(s) available as DATASET_PATH or DATASET_PATH_<NAME> variables
    - Plots (matplotlib/seaborn) automatically captured and saved
    - Execution timeout enforced for safety

    Use this to run any Python code: data loading, analysis, modeling, visualization, etc.
    """
    try:
        result = run_python_repl(code, timeout_seconds=Config.TIMEOUT_SECONDS)
        return format_execution_output(result)
    except Exception as e:
        return f"Error executing code: {str(e)}"


def create_tool_list():
    """Create the list of tools available to the agent"""
    return [dataset_info, execute_python]