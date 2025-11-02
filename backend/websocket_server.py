#!/usr/bin/env python
"""
WebSocket Server for ML Engineer Agent
Connects the frontend chat UI with the backend ML agent
"""

import asyncio
import json
import re
import uuid
from typing import Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.datasets import DatasetResolver
from ml_engineer.python_executor import get_execution_history
from ml_engineer.config import Config


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
    
    async def send_message(self, message_type: str, payload: any = None):
        """Send a message to the frontend"""
        message = {"type": message_type}
        if payload is not None:
            message["payload"] = payload
        
        await self.websocket.send_json(message)
    
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
    
    async def process_agent_output(self, agent: MLEngineerAgent, prompt: str):
        """Process agent execution and stream to frontend"""
        try:
            # Send initial status
            await self.append_markdown(
                f"# Starting Analysis\n\n**Dataset:** {agent.dataset_name}\n\n**Task:** {prompt}\n\n---"
            )
            
            # Track what we've sent
            plan_sent = False
            code_block_count = 0
            
            # Initialize the agent's workflow
            agent._setup_workflow()
            
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
            
            # Create initial messages
            from langchain_core.messages import SystemMessage, HumanMessage
            
            system_message = SystemMessage(content=agent._create_system_prompt())
            user_message = HumanMessage(content=prompt)
            
            initial_state = {
                "messages": [system_message, user_message],
                "next_step": None
            }
            
            # Stream the workflow
            for event in agent.app.stream(initial_state):
                if "generate" in event:
                    # Process AI messages
                    state = event["generate"]
                    messages = state.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            content = last_msg.content
                            
                            # Extract plan
                            if not plan_sent:
                                plan_match = re.search(
                                    r'<plan>(.*?)</plan>', 
                                    content, 
                                    re.DOTALL | re.IGNORECASE
                                )
                                if plan_match:
                                    plan = plan_match.group(1).strip()
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
                                await self.append_markdown(
                                    f"## 🤔 Agent Thinking\n\n{thinking}\n\n---"
                                )
                
                elif "execute_tools" in event:
                    # Process tool executions
                    state = event["execute_tools"]
                    messages = state.get("messages", [])
                    
                    # Get execution history to find new code blocks
                    history = get_execution_history()
                    
                    # Send any new code blocks
                    if len(history) > code_block_count:
                        for execution in history[code_block_count:]:
                            code_block_count += 1
                            await self.append_code_block(
                                execution["code"],
                                f"code-{code_block_count}"
                            )
                            
                            # Show output if available
                            output = execution.get("output", "")
                            if output and output.strip():
                                # Truncate long outputs
                                display_output = output[:1000]
                                if len(output) > 1000:
                                    display_output += "\n... (truncated)"
                                
                                await self.append_markdown(
                                    f"**Output:**\n```\n{display_output}\n```"
                                )
                
                # Small delay for UI updates
                await asyncio.sleep(0.1)
            
            # Get final solution from last message
            final_state = event.get("generate", event.get("execute_tools", {}))
            messages = final_state.get("messages", [])
            
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
            
            # Get final code block count
            history = get_execution_history()
            
            # Send solution as final answer
            await self.send_final_answer(
                f"✅ **Analysis Complete**\n\n{solution}\n\n"
                f"💻 Executed {len(history)} code block(s)"
            )
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in process_agent_output: {error_trace}")
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
    
    print(f"✅ Client connected: {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
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
        print(f"❌ Client disconnected: {session_id}")
        sessions.pop(session_id, None)
    except Exception as e:
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
