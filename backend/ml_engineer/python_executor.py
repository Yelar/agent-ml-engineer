

import io
import sys
import base64
import traceback
from typing import Dict, Any, List
from contextlib import redirect_stdout, redirect_stderr
import signal
from functools import wraps
import threading

try:
    import matplotlib

    matplotlib.use("Agg", force=True)
except Exception:
    # matplotlib is optional; ignore if unavailable
    pass


# Persistent namespace for code execution
_persistent_namespace: Dict[str, Any] = {}
_execution_history: List[Dict[str, Any]] = []
_plot_counter = 0
HAS_SIGALRM = hasattr(signal, "SIGALRM")


def timeout_handler(signum, frame):
    """Handle timeout for code execution"""
    raise TimeoutError("Code execution exceeded time limit")


def _start_timeout(timeout_seconds: int):
    """Start a SIGALRM timeout if supported; returns previous handler."""
    if not HAS_SIGALRM or timeout_seconds <= 0:
        return None
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    return previous_handler


def _clear_timeout(previous_handler):
    """Restore previous timeout handler if necessary."""
    if not HAS_SIGALRM:
        return
    signal.alarm(0)
    if previous_handler is not None:
        signal.signal(signal.SIGALRM, previous_handler)


class PlotCapture:
    """Capture matplotlib plots as base64 images"""

    def __init__(self):
        self.plots: List[str] = []
        self.original_show = None

    def __enter__(self):
        """Start capturing plots"""
        try:
            import matplotlib.pyplot as plt
            self.original_show = plt.show

            def custom_show(*args, **kwargs):
                """Custom show that captures plot instead of displaying"""
                import matplotlib.pyplot as plt
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                self.plots.append(img_base64)
                plt.close('all')

            plt.show = custom_show
        except ImportError:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing plots and restore original show"""
        try:
            import matplotlib.pyplot as plt
            if self.original_show:
                plt.show = self.original_show
        except ImportError:
            pass


def _supports_signal_timeout() -> bool:
    """Check whether the current thread can safely use signal-based alarms."""

    return threading.current_thread() is threading.main_thread()


def run_python_repl(command: str, timeout_seconds: int = 60) -> Dict[str, Any]:
    """
    Execute Python code in a persistent namespace with plot capture

    Args:
        command: Python code to execute
        timeout_seconds: Maximum execution time

    Returns:
        Dictionary with 'output', 'error', 'plots', and 'success' keys
    """
    global _persistent_namespace, _execution_history, _plot_counter

    result = {
        'output': '',
        'error': '',
        'plots': [],
        'success': False,
        'code': command
    }

    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Capture plots
    plot_capture = PlotCapture()

    use_timeout = _supports_signal_timeout()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture), plot_capture:
            # Set timeout if supported (signals only work on main thread)
            if use_timeout:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)

            try:
                # Execute the code
                exec(command, _persistent_namespace)
                result['success'] = True
            except TimeoutError:
                result['error'] = f"Execution timed out after {timeout_seconds} seconds"
            except Exception as e:
                result['error'] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            finally:
                if use_timeout:
                    signal.alarm(0)

        # Get captured output
        result['output'] = stdout_capture.getvalue()
        if stderr_capture.getvalue():
            result['error'] += stderr_capture.getvalue()

        # Get captured plots
        result['plots'] = plot_capture.plots

    except TimeoutError:
        result['error'] = f"Execution timed out after {timeout_seconds} seconds"
    except Exception as e:
        result['error'] = f"Unexpected error: {type(e).__name__}: {str(e)}"

    # Store in execution history
    _execution_history.append(result)

    return result


def inject_variables(variables: Dict[str, Any]):
    """
    Inject variables into the persistent namespace

    Args:
        variables: Dictionary of variables to inject
    """
    global _persistent_namespace
    _persistent_namespace.update(variables)


def get_namespace() -> Dict[str, Any]:
    """Get the current persistent namespace"""
    return _persistent_namespace.copy()


def get_execution_history() -> List[Dict[str, Any]]:
    """Get the execution history"""
    return _execution_history.copy()


def clear_namespace():
    """Clear the persistent namespace"""
    global _persistent_namespace
    _persistent_namespace.clear()


def clear_history():
    """Clear the execution history"""
    global _execution_history, _plot_counter
    _execution_history.clear()
    _plot_counter = 0


def save_plots_to_disk(output_dir: str) -> List[str]:
    """
    Save all captured plots to disk

    Args:
        output_dir: Directory to save plots

    Returns:
        List of saved plot paths
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    plot_num = 0

    for execution in _execution_history:
        for plot_base64 in execution.get('plots', []):
            plot_num += 1
            plot_path = output_path / f"plot_{plot_num:03d}.png"

            # Decode and save
            plot_data = base64.b64decode(plot_base64)
            plot_path.write_bytes(plot_data)
            saved_paths.append(str(plot_path))

    return saved_paths


def format_execution_output(result: Dict[str, Any]) -> str:
    """
    Format execution result for display

    Args:
        result: Execution result dictionary

    Returns:
        Formatted string
    """
    output_parts = []

    if result['output']:
        output_parts.append(f"Output:\n{result['output']}")

    if result['error']:
        output_parts.append(f"Error:\n{result['error']}")

    if result['plots']:
        output_parts.append(f"Generated {len(result['plots'])} plot(s)")

    if not output_parts:
        output_parts.append("Execution completed successfully (no output)")

    return "\n\n".join(output_parts)
