

from typing import TypedDict, Annotated, Sequence, Literal, Optional, Union
from pathlib import Path
import re
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .config import Config
from .tools import create_tool_list
from .datasets import DatasetResolver, load_dataset
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
        dataset_path: str,
        model_name: str = None,
        max_iterations: int = None,
        verbose: bool = True,
        planning_mode: bool = True,
        reasoning_effort: str = None
    ):
        """
        Initialize the ML Engineer Agent

        Args:
            dataset_path: Path or identifier for the dataset
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

        # Resolve dataset
        self.dataset_path = DatasetResolver.resolve(dataset_path)
        self.dataset_name = self.dataset_path.stem

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

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        planning_instructions = ""
        if self.planning_mode:
            planning_instructions = """
**PLANNING REQUIRED:**
Before starting execution, create a detailed plan:

<plan>
## High-Level Strategy
[Overall approach to solve the task]

## Steps
1. [Step 1: e.g., Data Exploration]
   - What to do
   - What to check
2. [Step 2: e.g., Data Preprocessing]
   - What to do
   - What to check
3. [Step 3: e.g., Feature Engineering]
   - What to do
   - What to check
4. [Step 4: e.g., Model Building]
   - What algorithms to try
   - What metrics to use
5. [Step 5: e.g., Evaluation & Results]
   - What to evaluate
   - How to present results
</plan>

After creating the plan, follow it step by step, updating the plan as you learn more about the data.
"""

        return f"""You are an expert ML Engineer assistant. Your goal is to help users build complete machine learning pipelines from their datasets.

**Dataset Information:**
- Dataset path: {self.dataset_path}
- Dataset name: {self.dataset_name}

**Your Capabilities:**
1. Analyze datasets to understand structure and patterns
2. Perform exploratory data analysis (EDA)
3. Create visualizations to reveal insights
4. Build, train, and evaluate ML models
5. Generate predictions and recommendations

**Execution Environment:**
- You have access to a persistent Python environment
- The dataset is loaded as a pandas DataFrame in the variable 'df'
- Common libraries are available: pandas (pd), numpy (np), matplotlib.pyplot (plt), seaborn (sns), sklearn
- All plots created with matplotlib are automatically captured and saved
- Variables and imports persist across code executions
{planning_instructions}
**Workflow Instructions:**
At each turn, you should provide your thinking and reasoning. Then you have two options:

1) Use tools to interact with the environment:
   - Use dataset_info to inspect the dataset structure
   - Use execute_python to run code and see results

2) When ready, provide the final solution using <solution> tags.

**Response Format:**
Each response should follow this structure:

<think>
[Your reasoning about what to do next and why]
[Analysis of previous results if any]
[Decision on next action]
</think>

Then EITHER use a tool (dataset_info or execute_python) OR provide solution:

<solution>
## Summary
[Brief overview of the task and approach]

## Key Findings
- [Finding 1]
- [Finding 2]
...

## ML Pipeline
[Description of the complete pipeline built]

## Results
[Model performance and key metrics]

## Recommendations
[Next steps or recommendations]
</solution>

**Code Execution Guidelines:**
- Write clean, well-commented code
- Create visualizations to support insights
- Handle missing values and outliers appropriately
- Use appropriate ML algorithms for the problem
- Evaluate model performance with relevant metrics
- Always check for potential issues (data quality, overfitting, etc.)
- Keep code simple and decomposed into steps

**Important:**
- Always include <think> tags to show your reasoning
- Use tools to gather information and execute code
- Provide <solution> only when the complete pipeline is ready
- Update your plan as you learn more from the data

Begin by creating a plan (if planning mode is enabled), then understanding the dataset, and proceed with systematic analysis and modeling."""

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

    def _extract_and_display_tags(self, content: str):
        """Extract and display plan, think, and solution tags"""
        import re

        # Extract plan
        plan_match = re.search(r'<plan>(.*?)</plan>', content, re.DOTALL | re.IGNORECASE)
        if plan_match:
            plan = plan_match.group(1).strip()
            self._print_section("📋 PLAN", plan, "=")
            self.current_plan = plan

        # Extract think
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL | re.IGNORECASE)
        if think_match:
            thinking = think_match.group(1).strip()
            self._print_section("🤔 THINKING", thinking, "-")

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
            for i, tool_call in enumerate(last_message.tool_calls, 1):
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Execute the tool
                if tool_name in tool_map:
                    if self.verbose:
                        print(f"\n🔧 Executing: {tool_name}")
                        if tool_args:
                            print(f"   Arguments: {list(tool_args.keys())}")

                    try:
                        result = tool_map[tool_name].invoke(tool_args)

                        if self.verbose:
                            # Show preview of result
                            result_str = str(result)
                            preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
                            self._print_section(f"📊 {tool_name} Result", preview, "-")

                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
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

            self._print_section("🚀 ML ENGINEER AGENT STARTING", f"""
Run ID: {self.run_id}
Dataset: {self.dataset_name} ({self.dataset_path})
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

        # Load dataset into namespace
        df = load_dataset(self.dataset_path)
        inject_variables({
            'df': df,
            'DATASET_PATH': str(self.dataset_path),
            'pd': __import__('pandas'),
            'np': __import__('numpy'),
            'plt': __import__('matplotlib.pyplot'),
            'sns': __import__('seaborn'),
        })

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

            for i, msg in enumerate(messages):
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

        # Load dataset into namespace
        df = load_dataset(self.dataset_path)
        inject_variables({
            'df': df,
            'DATASET_PATH': str(self.dataset_path),
            'pd': __import__('pandas'),
            'np': __import__('numpy'),
            'plt': __import__('matplotlib.pyplot'),
            'sns': __import__('seaborn'),
        })

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
