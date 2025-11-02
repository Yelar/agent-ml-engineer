#!/usr/bin/env python
"""
Quick test script to verify ML Engineer Agent functionality
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ml_engineer.python_executor import run_python_repl, clear_namespace
from ml_engineer.datasets import DatasetResolver, get_dataset_info
from ml_engineer.notebook_generator import generate_notebook


def test_python_executor():
    """Test Python executor with plot capture"""
    print("\n" + "="*80)
    print("TEST 1: Python Executor")
    print("="*80)

    clear_namespace()

    # Test basic execution
    result = run_python_repl("x = 5\nprint(f'x = {x}')")
    print(f"✓ Basic execution: {result['success']}")
    print(f"  Output: {result['output'].strip()}")

    # Test persistent namespace
    result = run_python_repl("print(f'x is still {x}')")
    print(f"✓ Persistent namespace: {result['success']}")
    print(f"  Output: {result['output'].strip()}")

    # Test plot capture
    code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 4))
plt.plot(x, y)
plt.title('Test Plot')
plt.show()
"""
    result = run_python_repl(code)
    print(f"✓ Plot capture: {result['success']}, plots: {len(result['plots'])}")

    print("\n✅ Python executor tests passed!\n")


def test_dataset_resolution():
    """Test dataset resolution"""
    print("="*80)
    print("TEST 2: Dataset Resolution")
    print("="*80)

    try:
        # Test resolving built-in dataset
        path = DatasetResolver.resolve("sample_sales")
        print(f"✓ Resolved 'sample_sales' to: {path}")

        # Test dataset info
        info = get_dataset_info(path)
        print(f"✓ Dataset info:")
        print(f"  Shape: {info['shape']}")
        print(f"  Columns: {len(info['columns'])}")
        print(f"  Columns: {', '.join(info['columns'][:5])}...")

        print("\n✅ Dataset tests passed!\n")
    except Exception as e:
        print(f"❌ Dataset test failed: {e}\n")


def test_notebook_generation():
    """Test notebook generation"""
    print("="*80)
    print("TEST 3: Notebook Generation")
    print("="*80)

    # Create sample execution history
    execution_history = [
        {
            'code': 'import pandas as pd\ndf = pd.read_csv("data.csv")',
            'output': '',
            'error': '',
            'plots': [],
            'success': True
        },
        {
            'code': 'print(df.shape)\ndf.head()',
            'output': '(100, 5)',
            'error': '',
            'plots': [],
            'success': True
        },
        {
            'code': 'import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nplt.show()',
            'output': '',
            'error': '',
            'plots': ['base64encodedimage'],
            'success': True
        }
    ]

    output_path = "/tmp/test_notebook.ipynb"
    notebook_path = generate_notebook(
        execution_history=execution_history,
        dataset_name="test_data",
        user_prompt="Test the notebook generation",
        output_path=output_path,
        solution="This is a test solution"
    )

    print(f"✓ Notebook generated: {notebook_path}")
    print(f"✓ File exists: {Path(notebook_path).exists()}")

    # Load and verify structure
    import json
    with open(notebook_path) as f:
        nb = json.load(f)

    print(f"✓ Notebook cells: {len(nb['cells'])}")
    print(f"✓ Notebook format: nbformat {nb['nbformat']}.{nb['nbformat_minor']}")

    print("\n✅ Notebook generation tests passed!\n")


def test_imports():
    """Test that all dependencies are available"""
    print("="*80)
    print("TEST 4: Dependencies")
    print("="*80)

    dependencies = [
        'pandas',
        'numpy',
        'matplotlib',
        'seaborn',
        'sklearn',
        'langchain',
        'langchain_openai',
        'langgraph',
        'typer',
        'rich',
        'dotenv'
    ]

    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep}")
        except ImportError as e:
            print(f"❌ {dep}: {e}")

    print("\n✅ Dependency tests passed!\n")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("ML ENGINEER AGENT - TEST SUITE")
    print("="*80)

    try:
        test_imports()
        test_python_executor()
        test_dataset_resolution()
        test_notebook_generation()

        print("="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nYou can now run the agent with:")
        print("  python usage.py --prompt 'Your task' --dataset sample_sales")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
