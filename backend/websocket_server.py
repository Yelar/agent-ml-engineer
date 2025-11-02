#!/usr/bin/env python
"""
WebSocket Server for ML Engineer Agent
Connects the frontend chat UI with the backend ML agent
"""

import asyncio
import json
import re
import uuid
import logging
from typing import Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.datasets import DatasetResolver
from ml_engineer.python_executor import get_execution_history
from ml_engineer.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket_server.log')
    ]
)
logger = logging.getLogger(__name__)


app = FastAPI(title="ML Engineer Agent WebSocket Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active sessions
sessions: Dict[str, dict] = {}


class AgentStreamer:
    """Stream agent execution to WebSocket"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.document_opened = False
        self.is_connected = True
    
    async def send_message(self, message_type: str, payload: any = None):
        """Send a message to the frontend"""
        if not self.is_connected:
            logger.warning(f"Skipping message send - websocket disconnected: {message_type}")
            return
            
        try:
            message = {"type": message_type}
            if payload is not None:
                message["payload"] = payload
            
            await self.websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send message (connection likely closed): {e}")
            self.is_connected = False
    
    async def open_document(self):
        """Open the document panel"""
        if not self.document_opened:
            await self.send_message("create_document")
            self.document_opened = True
    
    async def append_code_block(self, code: str, block_id: str = None):
        """Add a code block to the document"""
        await self.open_document()
        await self.send_message("append_to_document", {
            "id": block_id or str(uuid.uuid4()),
            "type": "code",
            "content": code
        })
    
    async def append_markdown(self, content: str, block_id: str = None):
        """Add markdown to the document"""
        await self.open_document()
        await self.send_message("append_to_document", {
            "id": block_id or str(uuid.uuid4()),
            "type": "markdown",
            "content": content
        })
    
    async def append_chart(self, title: str, data: list, block_id: str = None):
        """Add a chart to the document"""
        await self.open_document()
        await self.send_message("append_to_document", {
            "id": block_id or str(uuid.uuid4()),
            "type": "chart",
            "content": {
                "title": title,
                "data": data
            }
        })
    
    async def send_final_answer(self, content: str):
        """Send final answer to chat"""
        await self.send_message("final_answer", content)
    
    def _extract_accuracy_metrics(self, output: str) -> Dict[str, str]:
        """Extract accuracy metrics from execution output"""
        metrics = {}
        
        # Patterns to match common accuracy metrics
        patterns = {
            'accuracy': r'(?:accuracy|Accuracy|ACCURACY)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'f1_score': r'(?:f1[_\s-]?score|F1[_\s-]?Score|F1[_\s-]?SCORE)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'precision': r'(?:precision|Precision|PRECISION)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'recall': r'(?:recall|Recall|RECALL)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'r2_score': r'(?:r2[_\s-]?score|R2[_\s-]?Score|R²)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'mae': r'(?:mae|MAE|mean[_\s-]?absolute[_\s-]?error)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'rmse': r'(?:rmse|RMSE|root[_\s-]?mean[_\s-]?squared[_\s-]?error)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'test_accuracy': r'(?:test[_\s-]?accuracy|Test[_\s-]?Accuracy)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
            'train_accuracy': r'(?:train[_\s-]?accuracy|Train[_\s-]?Accuracy)[:\s=]+([0-9.]+(?:\s*%|[eE][+-]?\d+)?)',
        }
        
        for metric_name, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                metrics[metric_name] = match.group(1).strip()
        
        return metrics

    async def process_agent_output(self, agent: MLEngineerAgent, prompt: str):
        """Process agent execution and stream to frontend"""
        try:
            logger.info(f"Starting agent execution - Session: {self.session_id}, Dataset: {agent.dataset_name}")
            logger.info(f"Task: {prompt}")
            
            # Send initial status
            await self.append_markdown(
                f"# Starting Analysis\n\n**Dataset:** {agent.dataset_name}\n\n**Task:** {prompt}\n\n---"
            )
            
            # Track what we've sent
            plan_sent = False
            code_block_count = 0
            iteration_count = 0
            
            # Initialize the agent's workflow
            agent._setup_workflow()
            logger.info("Agent workflow initialized")
            
            # Load dataset
            from ml_engineer.datasets import load_dataset
            from ml_engineer.python_executor import inject_variables, clear_namespace, clear_history
            
            clear_namespace()
            clear_history()
            
            namespace_variables = {
                'pd': __import__('pandas'),
                'np': __import__('numpy'),
                'plt': __import__('matplotlib.pyplot'),
                'sns': __import__('seaborn'),
            }

            namespace_variables.update(agent.get_dataset_path_variables())

            if not agent.multiple_datasets:
                namespace_variables['df'] = load_dataset(agent.primary_dataset_path)

            inject_variables(namespace_variables)
            logger.info("Dataset loaded and namespace initialized")
            
            # Create initial messages
            from langchain_core.messages import SystemMessage, HumanMessage
            
            system_message = SystemMessage(content=agent._create_system_prompt())
            user_message = HumanMessage(content=prompt)
            
            initial_state = {
                "messages": [system_message, user_message],
                "next_step": None
            }
            
            logger.info("Starting LangGraph workflow stream")
            
            # Stream the workflow
            for event in agent.app.stream(initial_state):
                # Check if connection is still alive
                if not self.is_connected:
                    logger.warning("⚠️  Connection lost, stopping agent execution")
                    break
                    
                # Log LangGraph node execution
                # Event is a dict with single key-value pair: {node_name: state}
                for node_name, node_state in event.items():
                    logger.info(f"🔀 LangGraph Node: {node_name}")
                    
                    if node_name == "generate":
                        iteration_count += 1
                        logger.info(f"📝 Iteration {iteration_count}/{agent.max_iterations} - GENERATE Node")
                        
                        # Process AI messages
                        state = node_state
                        messages = state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, "content") and last_msg.content:
                                content = last_msg.content
                                
                                # Log tool calls if any
                                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                    tool_names = [tc.get("name", "unknown") for tc in last_msg.tool_calls]
                                    logger.info(f"🔧 Tool calls requested: {', '.join(tool_names)}")
                                    for i, tool_call in enumerate(last_msg.tool_calls, 1):
                                        logger.info(f"   Tool {i}: {tool_call.get('name')} - Args: {list(tool_call.get('args', {}).keys())}")
                                
                                # Extract plan
                                if not plan_sent:
                                    plan_match = re.search(
                                        r'<plan>(.*?)</plan>', 
                                        content, 
                                        re.DOTALL | re.IGNORECASE
                                    )
                                    if plan_match:
                                        plan = plan_match.group(1).strip()
                                        logger.info("📋 Plan extracted and sent to frontend")
                                        await self.append_markdown(
                                            f"## 📋 Execution Plan\n\n{plan}"
                                        )
                                        plan_sent = True
                                
                                # Extract thinking
                                think_match = re.search(
                                    r'<think>(.*?)</think>', 
                                    content, 
                                    re.DOTALL | re.IGNORECASE
                                )
                                if think_match:
                                    thinking = think_match.group(1).strip()
                                    logger.info("🤔 Agent reasoning extracted")
                                    await self.append_markdown(
                                        f"## 🤔 Agent Thinking\n\n{thinking}\n\n---"
                                    )
                    
                    elif node_name == "execute_tools":
                        logger.info(f"⚙️  EXECUTE_TOOLS Node - Running tools")
                        
                        # Process tool executions
                        state = node_state
                        messages = state.get("messages", [])
                        
                        # Get execution history to find new code blocks
                        history = get_execution_history()
                        
                        # Send any new code blocks
                        if len(history) > code_block_count:
                            for execution in history[code_block_count:]:
                                code_block_count += 1
                                
                                # Log code execution
                                code = execution.get("code", "")
                                logger.info(f"💻 Code Execution #{code_block_count}")
                                logger.info(f"   Code snippet: {code[:200]}..." if len(code) > 200 else f"   Code: {code}")
                                
                                await self.append_code_block(
                                    code,
                                    f"code-{code_block_count}"
                                )
                                
                                # Log execution results
                                output = execution.get("output", "")
                                error = execution.get("error", "")
                                success = execution.get("success", False)
                                plots_count = len(execution.get("plots", []))
                                
                                if success:
                                    logger.info(f"   ✅ Execution successful")
                                    if output:
                                        logger.info(f"   Output length: {len(output)} chars")
                                    if plots_count > 0:
                                        logger.info(f"   📊 Generated {plots_count} plot(s)")
                                    
                                    # Extract accuracy metrics
                                    if output:
                                        metrics = self._extract_accuracy_metrics(output)
                                        if metrics:
                                            metrics_str = ", ".join([f"{k}={v}" for k, v in metrics.items()])
                                            logger.info(f"   📈 Model Metrics: {metrics_str}")
                                            
                                            # Display metrics in markdown
                                            metrics_display = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in metrics.items()])
                                            await self.append_markdown(
                                                f"## 📈 Model Performance Metrics\n\n{metrics_display}\n\n---"
                                            )
                                else:
                                    logger.warning(f"   ❌ Execution failed: {error[:200]}")
                                
                                # Show output if available
                                if output and output.strip():
                                    # Truncate long outputs for display
                                    display_output = output[:1000]
                                    if len(output) > 1000:
                                        display_output += "\n... (truncated)"
                                    
                                    logger.debug(f"   Full output: {output[:500]}..." if len(output) > 500 else f"   Output: {output}")
                                    
                                    await self.append_markdown(
                                        f"**Output:**\n```\n{display_output}\n```"
                                    )
                                
                                # Log full output to file if there's an error
                                if error:
                                    logger.error(f"   Error details: {error}")
                
                # Small delay for UI updates
                await asyncio.sleep(0.1)
            
            # Get final solution from last message
            # Get the last event's state
            final_node_name = list(event.keys())[0] if event else None
            final_state = event.get(final_node_name, {}) if final_node_name else {}
            messages = final_state.get("messages", [])
            
            logger.info(f"🏁 LangGraph workflow completed - Total iterations: {iteration_count}")
            
            solution = "Analysis complete!"
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    solution_match = re.search(
                        r'<solution>(.*?)</solution>',
                        last_msg.content,
                        re.DOTALL | re.IGNORECASE
                    )
                    if solution_match:
                        solution = solution_match.group(1).strip()
                        logger.info("✅ Final solution extracted")
            
            # Get final code block count and extract final metrics
            history = get_execution_history()
            
            # Extract accuracy from all executions
            all_metrics = {}
            for exec_item in history:
                output = exec_item.get("output", "")
                if output:
                    exec_metrics = self._extract_accuracy_metrics(output)
                    if exec_metrics:
                        all_metrics.update(exec_metrics)
            
            if all_metrics:
                metrics_summary = ", ".join([f"{k}={v}" for k, v in all_metrics.items()])
                logger.info(f"📊 Final Model Metrics Summary: {metrics_summary}")
            
            # Log final summary
            logger.info(f"📊 Execution Summary:")
            logger.info(f"   - Total iterations: {iteration_count}")
            logger.info(f"   - Code blocks executed: {len(history)}")
            logger.info(f"   - Models trained: {len(all_metrics) > 0}")
            
            # Send solution as final answer
            final_message = f"✅ **Analysis Complete**\n\n{solution}\n\n💻 Executed {len(history)} code block(s)"
            if all_metrics:
                metrics_display = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in all_metrics.items()])
                final_message += f"\n\n📈 **Final Model Performance:**\n{metrics_display}"
            
            await self.send_final_answer(final_message)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            
            # Check if this is a disconnection error
            is_disconnect = any(term in str(e).lower() for term in ['disconnect', 'closed', 'connection'])
            
            if is_disconnect:
                logger.warning(f"⚠️  Client disconnected during processing: {str(e)}")
                self.is_connected = False
            else:
                logger.error(f"❌ Error in process_agent_output: {error_trace}")
                print(f"Error in process_agent_output: {error_trace}")
                # Only try to send error if still connected
                if self.is_connected:
                    await self.send_final_answer(
                        f"❌ Error during execution: {str(e)}"
                    )
                raise


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for agent communication"""
    await websocket.accept()
    
    # Initialize session
    sessions[session_id] = {
        "websocket": websocket,
        "dataset": None,
        "agent": None
    }
    
    streamer = AgentStreamer(websocket, session_id)
    
    logger.info(f"✅ Client connected: {session_id}")
    print(f"✅ Client connected: {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"📨 Received message type: {message.get('type')}")
            print(f"📨 Received: {message.get('type')}")
            
            if message.get("type") == "user_message":
                payload = message.get("payload", {})
                user_message = payload.get("message", "")
                
                # Check if dataset is set
                session = sessions.get(session_id)
                if not session or not session.get("dataset"):
                    # Try to use a default dataset
                    try:
                        dataset_path = DatasetResolver.resolve("sample_sales")
                        session["dataset"] = str(dataset_path)
                    except:
                        await streamer.send_final_answer(
                            "⚠️ Please upload a dataset first or specify a dataset name."
                        )
                        continue
                
                # Initialize agent if needed
                if not session.get("agent"):
                    agent = MLEngineerAgent(
                        dataset_path=session["dataset"],
                        model_name=Config.DEFAULT_MODEL,
                        max_iterations=12,
                        verbose=False,  # Disable console output
                        planning_mode=True
                    )
                    session["agent"] = agent
                else:
                    agent = session["agent"]
                
                # Process the request
                await streamer.process_agent_output(agent, user_message)
            
            elif message.get("type") == "set_dataset":
                # Set dataset for session
                payload = message.get("payload", {})
                dataset_name = payload.get("dataset", "")
                
                try:
                    dataset_path = DatasetResolver.resolve(dataset_name)
                    sessions[session_id]["dataset"] = str(dataset_path)
                    sessions[session_id]["agent"] = None  # Reset agent
                    
                    await streamer.send_final_answer(
                        f"✅ Dataset set to: {dataset_path.name}"
                    )
                except Exception as e:
                    await streamer.send_final_answer(
                        f"❌ Failed to load dataset: {str(e)}"
                    )
    
    except WebSocketDisconnect:
        logger.info(f"❌ Client disconnected: {session_id}")
        print(f"❌ Client disconnected: {session_id}")
        sessions.pop(session_id, None)
    except Exception as e:
        logger.error(f"❌ Error in websocket_endpoint: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sessions.pop(session_id, None)


@app.post("/upload")
async def upload_dataset(csv: UploadFile = File(...)):
    """Upload a CSV dataset"""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save file
        uploads_dir = Path(Config.DATASETS_DIR) / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = uploads_dir / f"{session_id}_{csv.filename}"
        
        with open(file_path, "wb") as f:
            content = await csv.read()
            f.write(content)
        
        return {
            "session_id": session_id,
            "dataset_path": str(file_path),
            "filename": csv.filename
        }
    
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "ML Engineer Agent WebSocket Server",
        "version": "1.0.0",
        "websocket_url": "/ws/{session_id}",
        "upload_url": "/upload",
        "protocol": {
            "incoming": {
                "user_message": {
                    "type": "user_message",
                    "payload": {
                        "session_id": "string",
                        "message": "string"
                    }
                },
                "set_dataset": {
                    "type": "set_dataset",
                    "payload": {
                        "dataset": "string (name or path)"
                    }
                }
            },
            "outgoing": {
                "create_document": {"type": "create_document"},
                "append_to_document": {
                    "type": "append_to_document",
                    "payload": {
                        "id": "string",
                        "type": "code|chart|markdown",
                        "content": "varies"
                    }
                },
                "final_answer": {
                    "type": "final_answer",
                    "payload": "string"
                }
            }
        },
        "available_datasets": [ds["name"] for ds in DatasetResolver.list_available()]
    }


@app.get("/datasets")
async def list_datasets():
    """List available datasets"""
    return {
        "datasets": DatasetResolver.list_available()
    }


if __name__ == "__main__":
    print("🚀 Starting ML Engineer Agent WebSocket Server")
    print("📡 WebSocket URL: ws://localhost:8000/ws/{session_id}")
    print("📤 Upload URL: http://localhost:8000/upload")
    print("📊 Available datasets: http://localhost:8000/datasets")
    print("\n" + "=" * 80)
    print("Server is running on http://localhost:8000")
    print("Connect your frontend to ws://localhost:8000/ws/{session_id}")
    print("=" * 80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")