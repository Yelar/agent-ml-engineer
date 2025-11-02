#!/usr/bin/env python
"""
Example: Running the ML Engineer Agent programmatically

This script demonstrates how to use the ML Engineer Agent from Python code
instead of the CLI.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.notebook_generator import generate_notebook


def run_example():
    """Run an example ML pipeline generation"""

    print("\n" + "="*80)
    print("ML Engineer Agent - Programmatic Example")
    print("="*80 + "\n")

    # Define the task
    prompt = """
    You have office_train.csv and office_test.csv datasets for building a machine learning model, in the end, create a submission.csv file with the predictions.
    Build a complete ML pipeline:
    n this competition, you will build a machine learning model to predict the quality category of office buildings based on their characteristics.

Goal
Predict the OfficeCategory (0, 1, 2, 3, or 4) for office buildings in the test set.

Evaluation Metric
Submissions are evaluated on Classification Accuracy:

Accuracy = (Number of Correct Predictions) / (Total Predictions)
Submission Format
Your submission file should contain exactly 15,000 predictions with two columns:

Id: Integer from 0 to 14,999
OfficeCategory: Your predicted category (0, 1, 2, 3, or 4)
Example: Id,OfficeCategory 0,3 1,2 2,4 …
    """

    # Use multiple datasets
    datasets = ["office_train", "office_test"]

    print(f"Task: {prompt.strip()}")
    print(f"Datasets: {', '.join(datasets)}\n")

    # Initialize the agent with multiple datasets
    agent = MLEngineerAgent(
        dataset_path=datasets,  # Pass list of datasets
        model_name="gpt-5",  # Use GPT-5
        max_iterations=50,
        verbose=True,  # Show all steps
        planning_mode=True,  # Create a plan first
        reasoning_effort="high"  # Use high reasoning effort
    )

    # Run the agent
    print("Running agent...\n")
    print("-" * 80)

    result = agent.run(prompt)

    print("-" * 80)
    print("\nExecution Complete!\n")

    # Display results
    print("="*80)
    print("RESULTS")
    print("="*80)

    print(f"\nRun ID: {result['run_id']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Plots Generated: {len(result['plot_paths'])}")
    print(f"Artifacts Directory: {result['artifacts_dir']}")
    print(f"Log Path: {result['log_path']}")

    # Show solution
    if result.get('solution'):
        print("\n" + "="*80)
        print("SOLUTION")
        print("="*80)
        print(result['solution'])

    # Generate notebook
    print("\n" + "="*80)
    print("GENERATING NOTEBOOK")
    print("="*80)

    notebook_path = Path(result['artifacts_dir']) / f"{agent.dataset_name}_pipeline.ipynb"
    notebook_file = generate_notebook(
        execution_history=result['execution_history'],
        dataset_name=agent.dataset_name,
        user_prompt=prompt,
        output_path=str(notebook_path),
        solution=result.get('solution')
    )

    print(f"\n✓ Notebook saved: {notebook_file}")

    # List generated plots
    if result['plot_paths']:
        print("\n" + "="*80)
        print("GENERATED PLOTS")
        print("="*80)
        for i, plot_path in enumerate(result['plot_paths'], 1):
            print(f"  {i}. {plot_path}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print(f"""
1. Review the artifacts: {result['artifacts_dir']}
2. Open the Jupyter notebook: {notebook_file}
3. Check the execution log: {result['log_path']}
4. View the generated plots
5. Modify and re-run as needed
""")

    print("="*80)
    print("Done!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        run_example()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
