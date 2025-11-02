

from typing import TypedDict, Sequence, Literal, Optional, Union, List, Dict
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
        dataset_path: Union[str, List[str]] = None,
        model_name: str = None,
        max_iterations: int = None,
        verbose: bool = True,
        planning_mode: bool = True,
        reasoning_effort: str = None,
        kaggle_competition_id: str = None,
        kaggle_mode: bool = False
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
            kaggle_competition_id: Kaggle competition ID for competition mode
            kaggle_mode: If True, use Kaggle competition workflow
        """
        self.model_name = model_name or Config.DEFAULT_MODEL
        self.max_iterations = max_iterations or Config.MAX_ITERATIONS
        self.verbose = verbose
        self.planning_mode = planning_mode
        self.reasoning_effort = reasoning_effort or Config.DEFAULT_REASONING_EFFORT
        
        # Kaggle competition mode
        self.kaggle_mode = kaggle_mode
        self.kaggle_competition_id = kaggle_competition_id

        # Resolve dataset(s) - can be single or multiple
        if self.kaggle_mode and kaggle_competition_id:
            # In Kaggle mode, dataset will be downloaded from competition
            self.dataset_paths = []
            self.dataset_names = [kaggle_competition_id]
            self.dataset_name = kaggle_competition_id
            self.multiple_datasets = False
            self.dataset_path_map = {}
        elif dataset_path:
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
        else:
            # No dataset provided - agent will need to load data during execution
            self.dataset_paths = []
            self.dataset_names = ["unknown"]
            self.dataset_name = "unknown"
            self.multiple_datasets = False
            self.dataset_path_map = {}

        # Backwards-compatible single-dataset attribute
        self.dataset_path: Optional[Path] = None
        if not self.multiple_datasets and self.dataset_paths:
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
        self.tools = create_tool_list(kaggle_mode=self.kaggle_mode)

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
    def primary_dataset_path(self) -> Optional[Path]:
        """Return the first dataset path (useful for single-dataset workflows)"""
        if self.dataset_paths:
            return self.dataset_paths[0]
        return None

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
        elif self.primary_dataset_path:
            return {"DATASET_PATH": str(self.primary_dataset_path)}
        else:
            # No datasets (e.g., Kaggle mode where data will be downloaded)
            return {}

    def _create_kaggle_system_prompt(self) -> str:
        """Create system prompt specifically for Kaggle competitions"""
        return f"""You are an expert ML Engineer Agent specialized in Kaggle competitions. 

**COMPETITION MODE**: You're working on Kaggle competition '{self.kaggle_competition_id}'

**Your Goal**: Build a complete ML pipeline that maximizes competition score and generates a submission-ready CSV file.

**Kaggle Workflow**:
1. **Competition Analysis**: 
   - Get competition details and understand the problem type
   - Download competition data (train, test, sample_submission)
   - Analyze evaluation metric and competition rules

2. **Data Pipeline**:
   - Load and explore train/test data
   - Perform EDA appropriate for the problem type
   - Handle missing values, outliers, feature engineering
   - Create validation strategy matching competition setup

3. **Modeling Strategy**:
   - Choose appropriate algorithms for the problem type
   - Implement cross-validation matching competition evaluation
   - Optimize for the specific competition metric
   - Consider ensemble methods if beneficial

4. **MANDATORY Submission Generation**:
   - Generate predictions on test data using your best model
   - Format output to match sample_submission.csv exactly
   - Save as 'submission.csv' in the current directory
   - ALWAYS end with: kaggle_submit_to_competition() to upload your results
   - This is REQUIRED - every run must produce a submission file!

**Available Tools**:
- `kaggle_search_competitions(query, status)`: Search competitions
- `kaggle_get_competition_details(competition_id)`: Get competition info
- `kaggle_download_competition_data(competition_id)`: Download competition files (AUTO-FALLBACK: automatically switches to accessible competitions if 403 error)
- `kaggle_submit_to_competition(competition_id, file_path, message)`: Submit results
- `kaggle_find_accessible_competition(query)`: Find competitions that don't require rule acceptance
- `execute_python(code)`: Execute Python code in persistent environment

**AUTOMATED 403 HANDLING**: 
If a competition requires rule acceptance (403 error), the download tool will AUTOMATICALLY switch to an accessible competition like 'titanic', 'digit-recognizer', or 'house-prices-advanced-regression-techniques'. You'll get a message indicating the switch and can proceed normally with the accessible competition.

**CRITICAL FILE PATH RULE**: 
When kaggle_download_competition_data returns a result, it includes the full "download_path". 
ALWAYS use this full path when loading CSV files! For example:
- If download_path is "/path/to/competitions/titanic"  
- Load train data as: pd.read_csv("/path/to/competitions/titanic/train.csv")
- Load test data as: pd.read_csv("/path/to/competitions/titanic/test.csv")
- NEVER use just "train.csv" - always use the complete path!

**STRICT WORKFLOW ENFORCEMENT**:
1. **Phases Are MANDATORY**:
   - Iterations 1-2: Download data + basic info (shape, columns, target distribution)
   - Iteration 3: Simple feature engineering (fill missing values, encode categoricals)
   - Iterations 4-5: Build and train a basic model (RandomForest or LogisticRegression)
   - Iteration 6: Generate predictions on test set
   - Iteration 7: Create submission.csv file with proper format
   - Final iteration: Submit to Kaggle using kaggle_submit_to_competition

2. **STOP Endless Exploration**: After 2 iterations of EDA, you MUST move to modeling
3. **MANDATORY Submission**: Every run MUST end with submission.csv creation and upload
4. **No Perfectionism**: Use simple approaches that work rather than endless optimization

**CRITICAL SUCCESS PATTERN**:
✓ Download data → ✓ Basic EDA → ✓ Build model → ✓ Generate predictions → ✓ Create submission.csv → ✓ Upload to Kaggle

**Critical Requirements**:
✓ Always validate submission format matches sample_submission.csv
✓ Use competition-specific evaluation metric for validation
✓ Generate final submission.csv in artifacts directory
✓ Include submission scoring/validation in your pipeline
✓ Follow competition rules and data usage guidelines

**Structured Workflow**:

1. **Think First** - Always wrap reasoning in <think> tags:
   <think>
   - What competition problem am I solving?
   - What's the evaluation metric?
   - What does the data look like?
   - What's my modeling approach?
   </think>

2. **Act** - Choose ONE action:
   a) Use Kaggle tools to get competition info and data
   b) Use `execute_python` tool to run code
   c) Provide final <solution> when complete with submission ready

3. **Iterate** - Continue until submission is ready

**Solution Format**:
<solution>
## Competition Summary
[Competition name, problem type, metric]

## Model Performance
[Cross-validation scores, expected leaderboard performance]

## Submission Details
[Submission file location, format validation, key features used]

## Next Steps
[Potential improvements, ensemble opportunities]
</solution>

Begin by getting competition details and downloading the data."""

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        # Use Kaggle-specific prompt in Kaggle mode
        if self.kaggle_mode:
            return self._create_kaggle_system_prompt()
            
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

**AVOID REPETITIVE LOOPS:**
- Don't repeat the same analysis or visualizations multiple times
- If you've already explored the data thoroughly, move to modeling
- Each iteration should make meaningful progress toward the solution
- When stuck, take a different approach rather than repeating the same steps

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

        # Compile with proper recursion limit
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

        # Check iteration limit BEFORE incrementing
        if self.iteration_count >= self.max_iterations:
            if self.verbose:
                print(f"\n⚠️  Maximum iterations ({self.max_iterations}) reached. Ending execution.\n")
            return {
                "messages": messages + [AIMessage(content="<solution>Maximum iterations reached. Please review the work done so far.</solution>")],
                "next_step": "end"
            }

        # Increment after check
        self.iteration_count += 1
        if self.verbose:
            self._print_step(f"Iteration {self.iteration_count}/{self.max_iterations}", "Generating next action...")

        # Add workflow phase guidance based on iteration count
        if self.kaggle_mode and self.verbose:
            if self.iteration_count <= 2:
                print(f"📋 Current Phase: Data Download & Basic EDA (iteration {self.iteration_count})")
            elif self.iteration_count <= 3:
                print(f"🔧 Current Phase: Feature Engineering (iteration {self.iteration_count})")
            elif self.iteration_count <= 5:
                print(f"🤖 Current Phase: Model Building (iteration {self.iteration_count})")
            elif self.iteration_count <= 6:
                print(f"🎯 Current Phase: Predictions Generation (iteration {self.iteration_count})")
            elif self.iteration_count <= 7:
                print(f"📄 Current Phase: Submission Creation (iteration {self.iteration_count})")
                print("⚠️  MANDATORY: You MUST create submission.csv this iteration!")
            else:
                print(f"🚀 Current Phase: SUBMIT TO KAGGLE (iteration {self.iteration_count})")
                print("🚨 FINAL ITERATION: Upload submission.csv using kaggle_submit_to_competition()!")

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

                        # Create tool message - OpenAI doesn't allow images in tool messages
                        # Only include text content
                        tool_message_content = str(result)

                        # If this was execute_python and plots were generated, mention them in text
                        if tool_name == "execute_python":
                            from .python_executor import get_execution_history
                            exec_history = get_execution_history()
                            if exec_history:
                                last_execution = exec_history[-1]
                                if last_execution.get('plots'):
                                    plot_count = len(last_execution['plots'])
                                    tool_message_content += f"\n\n📊 Generated {plot_count} plot(s) - plots have been saved and are available for review."

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

        # Safety check: if we've exceeded max iterations, always end
        if self.iteration_count >= self.max_iterations:
            if self.verbose:
                print(f"🛑 _should_continue: Stopping at iteration {self.iteration_count}/{self.max_iterations}")
            return "end"

        # Check for solution tag
        if isinstance(last_message, AIMessage):
            if "<solution>" in last_message.content.lower():
                if self.verbose:
                    print(f"🏁 _should_continue: Found <solution> tag, ending")
                return "end"

            # Check if there are tool calls
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                # Detect repetitive tool calls (loop prevention)
                if len(messages) >= 6:  # Check last 3 iterations
                    recent_tool_calls = []
                    for msg in messages[-6:]:
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            recent_tool_calls.extend([call.get('name') for call in msg.tool_calls])
                    
                    # If same tool called repeatedly, warn
                    if len(recent_tool_calls) >= 4 and len(set(recent_tool_calls)) <= 2:
                        if self.verbose:
                            print(f"⚠️  _should_continue: Detected repetitive tool calls: {recent_tool_calls}")
                            print(f"   Consider moving to next phase of workflow")
                
                if self.verbose:
                    print(f"🔄 _should_continue: Found {len(last_message.tool_calls)} tool calls, continuing")
                return "continue"

        if self.verbose:
            print(f"🏁 _should_continue: No tool calls, ending")
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

        # Run with much higher recursion limit to avoid LangGraph limits
        config = {"recursion_limit": max(100, self.max_iterations * 3)}
        final_state = self.app.invoke(initial_state, config=config)

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
            'plan': self.current_plan,
            'kaggle_mode': self.kaggle_mode,
            'kaggle_competition_id': self.kaggle_competition_id
        }

    def run_kaggle_competition(self, competition_url_or_id: str, prompt: str = "") -> dict:
        """
        Special workflow for Kaggle competitions that automatically handles:
        - Competition URL parsing or direct ID
        - Competition data download
        - Submission generation and upload
        
        Args:
            competition_url_or_id: Kaggle competition URL or direct competition ID
            prompt: Optional additional instructions for the agent
            
        Returns:
            Dict with run results including submission details
        """
        # Parse competition ID from URL if needed
        if "kaggle.com" in competition_url_or_id:
            # Extract competition ID from URL
            import re
            patterns = [
                r'kaggle\.com/competitions/([^/?#\s]+)',
                r'kaggle\.com/c/([^/?#\s]+)',
            ]
            
            competition_id = None
            for pattern in patterns:
                match = re.search(pattern, competition_url_or_id)
                if match:
                    competition_id = match.group(1).strip()
                    break
            
            if not competition_id:
                raise ValueError(f"Could not extract competition ID from URL: {competition_url_or_id}")
        else:
            competition_id = competition_url_or_id.strip()

        # Update agent state for Kaggle mode
        self.kaggle_mode = True
        self.kaggle_competition_id = competition_id
        self.dataset_name = competition_id
        
        # Recreate tools with Kaggle mode enabled
        self.tools = create_tool_list(kaggle_mode=True)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Setup workflow with Kaggle mode
        self._setup_workflow()
        
        # Create Kaggle-specific prompt
        kaggle_prompt = f"""
Kaggle Competition: {competition_id}
URL: https://www.kaggle.com/competitions/{competition_id}

Task: Build a complete ML pipeline for this Kaggle competition and generate a submission-ready CSV.

Your workflow:
1. Get competition details and download data
2. Perform exploratory data analysis  
3. Build and validate ML models
4. Generate final submission CSV
5. Optionally submit to competition

Additional Instructions: {prompt}

Begin by getting competition details and downloading the competition data.

**ITERATION-BASED WORKFLOW:**
- Iterations 1-2: Download + basic dataset info only (no extensive EDA!)
- Iteration 3: Feature engineering (handle missing values, encode categories)
- Iterations 4-5: Build simple model (RandomForest/LogisticRegression + train)
- Iteration 6: Generate predictions on test set
- Iteration 7: Create submission.csv (match sample_submission format exactly)
- Final iteration: Use kaggle_submit_to_competition() to upload

**CRITICAL**: Follow this timeline strictly. Don't spend excessive iterations on EDA.

**FOOLPROOF SUBMISSION TEMPLATE** (use when technical issues arise):

STEP 1: Simple preprocessing and model training
STEP 2: Generate predictions  
STEP 3: Create submission DataFrame with PassengerId and Survived columns
STEP 4: Save as submission.csv with to_csv(index=False)
STEP 5: Use kaggle_submit_to_competition() to upload

Key points:
- Use LabelEncoder for categorical variables
- Fill missing values with median/mode  
- Use RandomForestClassifier with basic features
- Format: PassengerId, Survived columns only

**ERROR RECOVERY**: If you encounter errors, use this template with the correct file paths.
"""
        
        if self.verbose:
            self._print_section("🏆 KAGGLE COMPETITION MODE", f"""
Competition ID: {competition_id}
Competition URL: https://www.kaggle.com/competitions/{competition_id}
Additional Instructions: {prompt or 'None'}
""", "=")

        # Run the standard workflow with Kaggle prompt
        return self.run(kaggle_prompt)

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
