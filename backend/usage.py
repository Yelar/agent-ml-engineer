#!/usr/bin/env python
"""
ML Engineer Agent CLI - Main entry point

Usage:
    python usage.py --prompt "Your ML task" --dataset sample_sales
    python usage.py --prompt "Build a regression model" --dataset xau_intraday
    python usage.py --prompt "Analyze customer churn" --dataset /path/to/data.csv
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.datasets import DatasetResolver
from ml_engineer.notebook_generator import generate_notebook
from ml_engineer.config import Config

app = typer.Typer()
console = Console()


@app.command()
def main(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Task description for the ML agent"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name or path"),
    model: str = typer.Option(None, "--model", "-m", help="OpenAI model to use (default: gpt-5)"),
    max_iterations: int = typer.Option(None, "--max-iterations", help="Maximum iterations"),
    generate_notebook: bool = typer.Option(True, "--notebook/--no-notebook", help="Generate Jupyter notebook"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Verbose output (default: True)"),
    planning: bool = typer.Option(True, "--planning/--no-planning", help="Enable planning mode (default: True)"),
    reasoning_effort: str = typer.Option(None, "--reasoning-effort", help="Reasoning effort for GPT-5 (low, medium, high)")
):
    """
    Run the ML Engineer Agent to build a complete ML pipeline
    """
    console.print("\n[bold cyan]ML Engineer Agent[/bold cyan]", justify="center")
    console.print("[dim] ML pipeline builder[/dim]\n", justify="center")

    # Display configuration
    console.print(Panel(f"""[bold]Configuration[/bold]

📊 Dataset: {dataset}
🎯 Task: {prompt}
🤖 Model: {model or Config.DEFAULT_MODEL}
🔄 Max Iterations: {max_iterations or Config.MAX_ITERATIONS}
📓 Generate Notebook: {generate_notebook}
""", title="Run Configuration", border_style="cyan"))

    try:
        # Resolve dataset
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Resolving dataset...", total=None)
            try:
                dataset_path = DatasetResolver.resolve(dataset)
                progress.update(task, description=f"[green]✓[/green] Dataset: {dataset_path.name}")
            except FileNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)

        # Initialize agent
        if not verbose:
            console.print("\n[yellow]Initializing ML Engineer Agent...[/yellow]")
        agent = MLEngineerAgent(
            dataset_path=str(dataset_path),
            model_name=model,
            max_iterations=max_iterations,
            verbose=verbose,
            planning_mode=planning,
            reasoning_effort=reasoning_effort
        )

        # Run agent
        if not verbose:
            console.print("\n[yellow]Running agent...[/yellow]")
            console.print("[dim]The agent will analyze the dataset and build an ML pipeline.[/dim]\n")

        if verbose:
            # In verbose mode, show everything directly
            result = agent.run(prompt)
        else:
            # In quiet mode, show progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Executing ML pipeline...", total=None)
                result = agent.run(prompt)
                progress.update(task, description="[green]✓[/green] Pipeline complete")

        # Display results
        console.print("\n" + "=" * 80)
        console.print("[bold green]Execution Complete![/bold green]\n")

        # Show summary statistics
        console.print(Panel(f"""[bold]Execution Summary[/bold]

🔄 Iterations: {result['iterations']}
📊 Plots Generated: {len(result['plot_paths'])}
💾 Artifacts Directory: {result['artifacts_dir']}
📝 Log File: {result['log_path']}
""", title="Summary", border_style="green"))

        # Display solution
        if result.get('solution'):
            console.print("\n[bold cyan]Solution:[/bold cyan]\n")
            md = Markdown(result['solution'])
            console.print(md)

        # Display plot paths
        if result['plot_paths']:
            console.print("\n[bold]Generated Plots:[/bold]")
            for i, plot_path in enumerate(result['plot_paths'], 1):
                console.print(f"  {i}. {plot_path}")

        # Generate Jupyter notebook
        if generate_notebook:
            console.print("\n[yellow]Generating Jupyter notebook...[/yellow]")
            notebook_path = Path(result['artifacts_dir']) / f"{agent.dataset_name}_pipeline.ipynb"

            notebook_file = generate_notebook(
                execution_history=result['execution_history'],
                dataset_name=agent.dataset_name,
                user_prompt=prompt,
                output_path=str(notebook_path),
                solution=result.get('solution')
            )

            console.print(f"[green]✓[/green] Notebook saved: {notebook_file}")

        # Show next steps
        console.print("\n" + Panel(f"""[bold]Next Steps[/bold]

1. Review the generated artifacts in: {result['artifacts_dir']}
2. Open the Jupyter notebook to explore the pipeline
3. Check the conversation log for detailed execution trace
4. Modify and re-run the notebook as needed

[dim]Run with --help for more options[/dim]
""", title="Next Steps", border_style="cyan"))

        console.print("\n[bold green]✨ Done![/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def list_datasets():
    """List all available datasets"""
    datasets = DatasetResolver.list_available()

    if not datasets:
        console.print("[yellow]No datasets found[/yellow]")
        return

    console.print("\n[bold]Available Datasets:[/bold]\n")

    for ds in datasets:
        builtin_marker = "[cyan]★[/cyan]" if ds['builtin'] else " "
        size_mb = ds['size'] / (1024 * 1024)
        console.print(f"{builtin_marker} [bold]{ds['name']}[/bold]")
        console.print(f"   Path: {ds['path']}")
        console.print(f"   Size: {size_mb:.2f} MB\n")

    console.print("[dim]Use --dataset <name> to select a dataset[/dim]\n")


if __name__ == "__main__":
    app()
