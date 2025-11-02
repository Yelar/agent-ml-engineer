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
    Get comprehensive information about a dataset including columns, types, missing values, and preview.
    Use this tool first to understand the structure of the dataset before performing any analysis.
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
    Execute Python code in a persistent namespace. Variables and imports persist across calls.
    The dataset is available as a pandas DataFrame in the variable 'df'.
    Common libraries (pandas, numpy, matplotlib, seaborn, sklearn) are pre-imported.

    Use this tool to:
    - Perform exploratory data analysis
    - Create visualizations (plots are automatically captured)
    - Build and train ML models
    - Generate predictions
    - Perform any data processing or analysis

    The code should be complete and executable. Plots created with matplotlib will be
    automatically captured and saved.
    """
    try:
        result = run_python_repl(code, timeout_seconds=Config.TIMEOUT_SECONDS)
        return format_execution_output(result)
    except Exception as e:
        return f"Error executing code: {str(e)}"


def create_tool_list():
    """Create the list of tools available to the agent"""
    return [dataset_info, execute_python]
