

from typing import TypedDict, Sequence, Literal, Optional, Union, List, Dict, Callable
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .config import Config
from .tools import create_tool_list
from .datasets import DatasetResolver
from .python_executor import (
    inject_variables,
    get_execution_history,
    clear_namespace,
    clear_history,
    save_plots_to_disk
)


class AgentState(TypedDict):
    """State for the ML Engineer Agent"""
    messages: Sequence[BaseMessage]
    next_step: Optional[str]


class MLEngineerAgent:
    """
    ML Engineer Agent that builds complete ML pipelines

    """

    def __init__(
        self,
        dataset_path: Union[str, List[str]],
        model_name: str = None,
        max_iterations: int = None,
        verbose: bool = True,
        planning_mode: bool = True,
        reasoning_effort: str = None,
        on_ai_message: Optional[Callable[[int, AIMessage], None]] = None,
    ):
        """
        Initialize the ML Engineer Agent

        Args:
            dataset_path: Path/identifier for dataset(s). Can be a single string or list of strings
            model_name: OpenAI model to use (default from config)
            max_iterations: Maximum number of iterations (default from config)
            verbose: If True, print detailed execution steps
            planning_mode: If True, create a plan before executing
            reasoning_effort: Reasoning effort for GPT-5 ("low", "medium", "high")
        """
        self.model_name = model_name or Config.DEFAULT_MODEL
        self.max_iterations = max_iterations or Config.MAX_ITERATIONS
        self.verbose = verbose
        self.planning_mode = planning_mode
        self.reasoning_effort = reasoning_effort or Config.DEFAULT_REASONING_EFFORT
        self.on_ai_message = on_ai_message

        # Resolve dataset(s) - can be single or multiple
        if isinstance(dataset_path, list):
            self.dataset_paths = [DatasetResolver.resolve(path) for path in dataset_path]
            self.dataset_names = [path.stem for path in self.dataset_paths]
            self.dataset_name = "_".join(self.dataset_names)  # Combined name for artifacts
            self.multiple_datasets = True
        else:
            self.dataset_paths = [DatasetResolver.resolve(dataset_path)]
            self.dataset_names = [self.dataset_paths[0].stem]
            self.dataset_name = self.dataset_names[0]
            self.multiple_datasets = False

        # Map dataset names to resolved paths for convenience
        self.dataset_path_map: Dict[str, Path] = {
            name: path for name, path in zip(self.dataset_names, self.dataset_paths)
        }
        # Backwards-compatible single-dataset attribute
        self.dataset_path: Optional[Path] = None
        if not self.multiple_datasets:
            self.dataset_path = self.dataset_paths[0]

        # Initialize LLM with reasoning_effort for GPT-5
        llm_kwargs = {
            "model": self.model_name,
            "temperature": 0,
            "api_key": Config.OPENAI_API_KEY,
        }

        # Add reasoning_effort for GPT-5 and reasoning models
        if self.model_name in ["gpt-5", "o1-preview", "o1-mini", "o3-mini"] or self.model_name.startswith("gpt-5"):
            llm_kwargs["model_kwargs"] = {"reasoning_effort": self.reasoning_effort}

        self.llm = ChatOpenAI(**llm_kwargs)

        # Create tools
        self.tools = create_tool_list()

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Create workflow
        self.workflow = None
        self.app = None

        # Execution tracking
        self.iteration_count = 0
        self.run_id = None
        self.artifacts_dir = None
        self.current_plan = None

    @property
    def primary_dataset_path(self) -> Path:
        """Return the first dataset path (useful for single-dataset workflows)"""
        return self.dataset_paths[0]

    def get_dataset_path_variables(self) -> Dict[str, str]:
        """
        Create a mapping of dataset path variables to inject into the Python namespace.

        Returns:
            Dictionary mapping variable names to dataset path strings
        """
        if self.multiple_datasets:
            return {
                f"DATASET_PATH_{name.upper()}": str(path)
                for name, path in self.dataset_path_map.items()
            }
        return {"DATASET_PATH": str(self.primary_dataset_path)}

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        planning_instructions = ""
        if self.planning_mode:
            planning_instructions = """
**PLANNING MODE ENABLED:**

You MUST start by creating a detailed TODO plan with checkboxes based on the user's task.

<plan>
**TODO List:**
- [ ] Step 1: [Your first step based on the task]
- [ ] Step 2: [Your second step]
- [ ] Step 3: [Continue as needed...]
</plan>

Create steps that are specific to the task at hand. Common ML workflow steps include:
- Data loading and initial exploration
- Data quality assessment
- Exploratory data analysis with visualizations
- Data preprocessing and feature engineering
- Model selection and training
- Model evaluation and validation
- Results interpretation and recommendations

After completing each step, update the plan using these status markers:
- [✓] Completed successfully (use checkmark ✓)
- [ ] Pending / Not started
- [X] Failed or encountered errors

Include the updated plan in your <think> tags whenever you complete a major step.
"""

        # Create dataset information string
        if self.multiple_datasets:
            dataset_list = chr(10).join(f"- {name}: {path}" for name, path in zip(self.dataset_names, self.dataset_paths))
            path_vars = chr(10).join(f"- `DATASET_PATH_{name.upper()}` = \"{path}\"" for name, path in zip(self.dataset_names, self.dataset_paths))

            dataset_info = f"""**Multiple Datasets Available:**
{dataset_list}

**Dataset Path Variables:**
{path_vars}

**Important:** Datasets are NOT pre-loaded. Load them yourself using appropriate libraries based on file format.
"""
        else:
            dataset_path = self.dataset_paths[0]
            dataset_info = f"""**Dataset Information:**
- Path: {dataset_path}
- Name: {self.dataset_names[0]}

**Dataset Path Variable:**
- `DATASET_PATH` = "{dataset_path}"

**Important:** Dataset is NOT pre-loaded. Load it yourself using appropriate libraries based on file format.
"""

        return f"""You are an expert ML Engineer AI assistant specialized in building complete, production-quality machine learning pipelines.

{dataset_info}

**Your Role:**
Build end-to-end ML solutions through systematic analysis, thoughtful experimentation, and clear communication.

**Python Environment:**
You have access to a persistent Python REPL with:
- Dataset path variables (DATASET_PATH or DATASET_PATH_<NAME>)
- Standard Python libraries available (install others if needed with pip)
- Automatic plot capture (matplotlib/seaborn plots saved automatically)
- Persistent namespace (variables and imports persist across executions)
- Execution timeout: {Config.TIMEOUT_SECONDS}s per code block
- **Visual feedback**: You can see the plots you generate - they are included in the tool responses

**Getting Started:** Import required libraries and load the dataset(s) using the provided path variables.
{planning_instructions}
**Structured Workflow:**

1. **Think First** - Always wrap your reasoning in <think> tags:
   <think>
   - What do I know so far?
   - What's the next logical step?
   - What specific analysis or code will help?
   - How does this relate to my plan?
   </think>

2. **Act** - Choose ONE action:
   a) Use `dataset_info` tool to inspect dataset structure
   b) Use `execute_python` tool to run code
   c) Provide final <solution> when complete

3. **Iterate** - Continue until task is complete

**Available Tools:**
- `dataset_info(dataset_path)`: Get dataset structure, types, statistics, preview
- `execute_python(code)`: Execute Python code in persistent environment

**Solution Format:**
When the task is complete, provide your findings in <solution> tags with relevant sections.

<solution>
## Summary
[Brief overview of what was accomplished]

## [Additional sections as appropriate for the task]
[Results, findings, metrics, visualizations, recommendations, etc.]
</solution>

**Best Practices:**
✓ Write clean, well-documented code
✓ Create informative visualizations when helpful
✓ Handle edge cases appropriately
✓ Validate your approach and results
✓ Explain your reasoning and choices

**Critical Rules:**
• Use <think> tags to show your reasoning
• Use tools to execute code and gather information
• Update TODO items in your plan as you progress
• Base conclusions on actual results, not assumptions
• Provide <solution> only when task is complete

Begin by creating your TODO plan, then systematically execute it."""

    def _setup_workflow(self):
        """Set up the LangGraph workflow"""

        # Create state graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("execute_tools", self._execute_tools_node)

        # Set entry point
        workflow.set_entry_point("generate")

        # Add edges
        workflow.add_conditional_edges(
            "generate",
            self._should_continue,
            {
                "continue": "execute_tools",
                "end": END
            }
        )
        workflow.add_edge("execute_tools", "generate")

        # Compile
        self.app = workflow.compile()

    def _print_section(self, title: str, content: str = None, symbol: str = "="):
        """Print a formatted section if verbose mode is enabled"""
        if not self.verbose:
            return

        print(f"\n{symbol * 80}")
        print(f"{title}")
        print(f"{symbol * 80}")
        if content:
            print(content)
        print()

    def _print_step(self, step_name: str, details: str = None):
        """Print a step if verbose mode is enabled"""
        if not self.verbose:
            return

        print(f"\n{'─' * 80}")
        print(f"🔄 {step_name}")
        if details:
            print(f"   {details}")
        print(f"{'─' * 80}")

    def _save_plan_to_file(self, plan: str):
        """Save the plan TODO list to a file"""
        if not self.artifacts_dir:
            return

        plan_file = self.artifacts_dir / "PLAN.md"
        with open(plan_file, 'w') as f:
            f.write(f"# ML Pipeline Plan\n\n")
            f.write(f"**Run ID:** {self.run_id}\n")
            f.write(f"**Dataset:** {self.dataset_name}\n")
            f.write(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(plan)

        if self.verbose:
            print(f"   💾 Plan saved to: {plan_file}")

    def _extract_and_display_tags(self, content: str):
        """Extract and display plan, think, and solution tags"""
        import re

        # Extract plan
        plan_match = re.search(r'<plan>(.*?)</plan>', content, re.DOTALL | re.IGNORECASE)
        if plan_match:
            plan = plan_match.group(1).strip()
            self._print_section("📋 PLAN", plan, "=")
            self.current_plan = plan
            # Save plan to file
            self._save_plan_to_file(plan)

        # Extract think
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL | re.IGNORECASE)
        if think_match:
            thinking = think_match.group(1).strip()
            self._print_section("🤔 THINKING", thinking, "-")

            # Check if think contains an updated plan (TODO list with checkboxes)
            # Recognize: [ ], [X], [x], [✓]
            if '- [' in thinking and ('[ ]' in thinking or '[X]' in thinking or '[x]' in thinking or '[✓]' in thinking):
                # Extract the TODO list portion and save it
                self.current_plan = thinking
                self._save_plan_to_file(thinking)

        # Extract solution
        solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL | re.IGNORECASE)
        if solution_match:
            solution = solution_match.group(1).strip()
            self._print_section("✅ SOLUTION", solution, "=")

    def _generate_node(self, state: AgentState) -> AgentState:
        """Generate node - LLM decides next action"""
        messages = state["messages"]

        # Check iteration limit
        self.iteration_count += 1
        if self.verbose:
            self._print_step(f"Iteration {self.iteration_count}/{self.max_iterations}", "Generating next action...")

        if self.iteration_count > self.max_iterations:
            if self.verbose:
                print(f"\n⚠️  Maximum iterations ({self.max_iterations}) reached. Ending execution.\n")
            return {
                "messages": messages + [AIMessage(content="<solution>Maximum iterations reached. Please review the work done so far.</solution>")],
                "next_step": "end"
            }

        # Call LLM
        if self.verbose:
            print(f"\n🤖 Calling LLM ({self.model_name})...")

        response = self.llm_with_tools.invoke(messages)

        if self.on_ai_message and isinstance(response, AIMessage):
            try:
                self.on_ai_message(self.iteration_count, response)
            except Exception as exc:
                if self.verbose:
                    print(f"   ⚠️  on_ai_message callback failed: {exc}")

        # Display the response content
        if self.verbose and hasattr(response, 'content') and response.content:
            self._extract_and_display_tags(response.content)

            # Show tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"\n🔧 Tool Calls Requested: {len(response.tool_calls)}")
                for i, tool_call in enumerate(response.tool_calls, 1):
                    print(f"   {i}. {tool_call['name']}()")

        return {
            "messages": messages + [response],
            "next_step": None
        }

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute tools node - run the requested tools"""
        messages = state["messages"]
        last_message = messages[-1]

        if self.verbose:
            self._print_step("Executing Tools", "Running requested tools...")

        # Create a mapping of tool names to tool functions
        tool_map = {tool.name: tool for tool in self.tools}

        # Execute each tool call
        tool_messages = []
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Execute the tool
                if tool_name in tool_map:
                    if self.verbose:
                        print(f"\n🔧 Executing: {tool_name}")

                        # Display code being executed (if it's execute_python)
                        if tool_name == "execute_python" and "code" in tool_args:
                            print(f"\n{'─' * 80}")
                            print("📝 Code:")
                            print(f"{'─' * 80}")
                            print(tool_args["code"])
                            print(f"{'─' * 80}")
                        elif tool_args:
                            print(f"   Arguments: {list(tool_args.keys())}")

                    try:
                        result = tool_map[tool_name].invoke(tool_args)

                        if self.verbose:
                            # Show preview of result
                            result_str = str(result)
                            preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
                            self._print_section(f"📊 {tool_name} Result", preview, "-")

                        # Create tool message with potential image content
                        tool_message_content = [{"type": "text", "text": str(result)}]

                        # If this was execute_python, check for generated plots and include them
                        if tool_name == "execute_python":
                            from .python_executor import get_execution_history
                            exec_history = get_execution_history()
                            if exec_history:
                                last_execution = exec_history[-1]
                                if last_execution.get('plots'):
                                    # Add images to the message content
                                    for plot_base64 in last_execution['plots']:
                                        tool_message_content.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{plot_base64}"
                                            }
                                        })

                        tool_messages.append(
                            ToolMessage(
                                content=tool_message_content,
                                tool_call_id=tool_call["id"],
                                name=tool_name
                            )
                        )
                    except Exception as e:
                        if self.verbose:
                            print(f"   ❌ Error: {str(e)}")

                        tool_messages.append(
                            ToolMessage(
                                content=f"Error executing {tool_name}: {str(e)}",
                                tool_call_id=tool_call["id"],
                                name=tool_name
                            )
                        )

        return {
            "messages": messages + tool_messages,
            "next_step": None
        }

    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Determine whether to continue or end"""
        messages = state["messages"]
        last_message = messages[-1]

        # Check for solution tag
        if isinstance(last_message, AIMessage):
            if "<solution>" in last_message.content.lower():
                return "end"

            # Check if there are tool calls
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "continue"

        return "end"

    def run(self, prompt: str) -> dict:
        """
        Run the agent with a user prompt

        Args:
            prompt: User's task description

        Returns:
            Dictionary with execution results
        """
        # Create run ID and artifacts directory
        self.run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.dataset_name}"
        self.artifacts_dir = Config.ARTIFACTS_DIR / self.run_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            reasoning_info = ""
            if self.model_name in ["gpt-5", "o1-preview", "o1-mini", "o3-mini"] or self.model_name.startswith("gpt-5"):
                reasoning_info = f"\nReasoning Effort: {self.reasoning_effort}"

            # Format dataset paths for display
            dataset_display = ", ".join([str(p) for p in self.dataset_paths])

            self._print_section("🚀 ML ENGINEER AGENT STARTING", f"""
Run ID: {self.run_id}
Dataset: {self.dataset_name} ({dataset_display})
Model: {self.model_name}{reasoning_info}
Max Iterations: {self.max_iterations}
Planning Mode: {'Enabled' if self.planning_mode else 'Disabled'}
Verbose Mode: Enabled

Task: {prompt}
""", "=")

        # Clear previous execution state
        clear_namespace()
        clear_history()
        self.iteration_count = 0

        # Inject dataset paths (not pre-loaded dataframes)
        # Agent will load datasets in code using these paths
        path_variables = self.get_dataset_path_variables()

        if self.verbose:
            if self.multiple_datasets:
                for name, path in self.dataset_path_map.items():
                    print(f"   Dataset available: {name} at {path}")
            else:
                print(f"   Dataset available at: {self.primary_dataset_path}")

        inject_variables(path_variables)

        # Setup workflow
        self._setup_workflow()

        # Create initial state
        system_message = SystemMessage(content=self._create_system_prompt())
        user_message = HumanMessage(content=prompt)

        initial_state = {
            "messages": [system_message, user_message],
            "next_step": None
        }

        # Run the workflow
        if self.verbose:
            print(f"\n{'═' * 80}")
            print(f"Starting execution workflow...")
            print(f"{'═' * 80}\n")

        final_state = self.app.invoke(initial_state)

        # Save artifacts
        if self.verbose:
            print(f"\n{'═' * 80}")
            print(f"💾 Saving artifacts...")
            print(f"{'═' * 80}\n")

        plot_paths = save_plots_to_disk(str(self.artifacts_dir))

        if self.verbose and plot_paths:
            print(f"   Saved {len(plot_paths)} plot(s)")

        # Get execution history
        history = get_execution_history()

        # Extract final solution
        final_message = final_state["messages"][-1]
        solution = self._extract_solution(final_message.content if isinstance(final_message, AIMessage) else "")

        # Save conversation log
        log_path = self._save_conversation_log(final_state["messages"])

        if self.verbose:
            self._print_section("✅ EXECUTION COMPLETE", f"""
Total Iterations: {self.iteration_count}
Plots Generated: {len(plot_paths)}
Artifacts Directory: {self.artifacts_dir}
Conversation Log: {log_path}

Run ID: {self.run_id}
""", "=")

        return {
            'run_id': self.run_id,
            'solution': solution,
            'messages': final_state["messages"],
            'execution_history': history,
            'plot_paths': plot_paths,
            'artifacts_dir': str(self.artifacts_dir),
            'log_path': log_path,
            'iterations': self.iteration_count,
            'plan': self.current_plan
        }

    def _extract_solution(self, content: str) -> str:
        """Extract solution from AI response"""
        match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return content

    def _save_conversation_log(self, messages: Sequence[BaseMessage]) -> str:
        """Save conversation log to file"""
        log_path = Config.RUNS_DIR / f"{self.run_id}.txt"

        with open(log_path, 'w') as f:
            f.write(f"ML Engineer Agent Run\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"Run ID: {self.run_id}\n")
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Model: {self.model_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"{'=' * 80}\n\n")

            for msg in messages:
                if isinstance(msg, SystemMessage):
                    f.write(f"[SYSTEM]\n{msg.content}\n\n")
                elif isinstance(msg, HumanMessage):
                    f.write(f"[USER]\n{msg.content}\n\n")
                elif isinstance(msg, AIMessage):
                    f.write(f"[ASSISTANT]\n{msg.content}\n\n")
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        f.write(f"[TOOL CALLS]\n")
                        for tool_call in msg.tool_calls:
                            f.write(f"  - {tool_call}\n")
                        f.write("\n")
                else:
                    f.write(f"[{type(msg).__name__}]\n{msg.content}\n\n")

                f.write("-" * 80 + "\n\n")

        return str(log_path)

    def stream_run(self, prompt: str):
        """
        Stream the agent execution (generator version)

        Args:
            prompt: User's task description

        Yields:
            Execution updates
        """
        # Create run ID and artifacts directory
        self.run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.dataset_name}"
        self.artifacts_dir = Config.ARTIFACTS_DIR / self.run_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Clear previous execution state
        clear_namespace()
        clear_history()
        self.iteration_count = 0

        # Inject dataset paths (not pre-loaded dataframes)
        inject_variables(self.get_dataset_path_variables())

        # Setup workflow
        self._setup_workflow()

        # Create initial state
        system_message = SystemMessage(content=self._create_system_prompt())
        user_message = HumanMessage(content=prompt)

        initial_state = {
            "messages": [system_message, user_message],
            "next_step": None
        }

        # Stream the workflow
        for event in self.app.stream(initial_state):
            yield event
