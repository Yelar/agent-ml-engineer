#!/usr/bin/env python
"""
HTTP API Server for ML Engineer Agent
Provides REST endpoints that work with Vercel AI SDK
"""

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.datasets import DatasetResolver, load_dataset
from ml_engineer.python_executor import (
    get_execution_history,
    inject_variables,
    clear_namespace,
    clear_history,
)
from ml_engineer.config import Config


app = FastAPI(title="ML Engineer Agent API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    prompt: str
    dataset: Optional[str] = "sample_sales"


async def stream_analysis(prompt: str, dataset_path: str):
    """Stream analysis results as Server-Sent Events"""

    try:
        # Initialize agent
        agent = MLEngineerAgent(
            dataset_path=dataset_path,
            model_name=Config.DEFAULT_MODEL,
            max_iterations=52,
            verbose=False,
            planning_mode=True,
        )

        # Setup workflow
        agent._setup_workflow()

        # Clear and prepare execution environment
        clear_namespace()
        clear_history()

        namespace_variables = {
            "pd": __import__("pandas"),
            "np": __import__("numpy"),
            "plt": __import__("matplotlib.pyplot"),
            "sns": __import__("seaborn"),
        }

        # Inject dataset path helpers used by the agent
        namespace_variables.update(agent.get_dataset_path_variables())

        # For single-dataset workflows, preload the DataFrame for convenience
        if not agent.multiple_datasets:
            namespace_variables["df"] = load_dataset(agent.primary_dataset_path)

        inject_variables(namespace_variables)

        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'content': 'Starting analysis...'})}\n\n"

        # Create initial messages
        from langchain_core.messages import SystemMessage, HumanMessage

        system_message = SystemMessage(content=agent._create_system_prompt())
        user_message = HumanMessage(content=prompt)

        initial_state = {"messages": [system_message, user_message], "next_step": None}

        # Track what we've sent
        plan_sent = False
        code_block_count = 0

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
                                r"<plan>(.*?)</plan>", content, re.DOTALL | re.IGNORECASE
                            )
                            if plan_match:
                                plan = plan_match.group(1).strip()
                                yield f"data: {json.dumps({'type': 'plan', 'content': plan})}\n\n"
                                plan_sent = True

                        # Extract thinking
                        think_match = re.search(
                            r"<think>(.*?)</think>", content, re.DOTALL | re.IGNORECASE
                        )
                        if think_match:
                            thinking = think_match.group(1).strip()
                            yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"

            elif "execute_tools" in event:
                # Process tool executions
                state = event["execute_tools"]

                # Get execution history to find new code blocks
                history = get_execution_history()

                # Send any new code blocks
                if len(history) > code_block_count:
                    for execution in history[code_block_count:]:
                        code_block_count += 1
                        output = execution.get("output", "")

                        # Truncate long outputs
                        if len(output) > 1000:
                            output = output[:1000] + "\n... (truncated)"

                        yield f"data: {json.dumps({'type': 'code', 'content': execution['code'], 'output': output, 'index': code_block_count})}\n\n"

            # Small delay for streaming
            await asyncio.sleep(0.05)

        # Get final solution from last message
        final_state = event.get("generate", event.get("execute_tools", {}))
        messages = final_state.get("messages", [])

        solution = "Analysis complete!"
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                solution_match = re.search(
                    r"<solution>(.*?)</solution>",
                    last_msg.content,
                    re.DOTALL | re.IGNORECASE,
                )
                if solution_match:
                    solution = solution_match.group(1).strip()

        yield f"data: {json.dumps({'type': 'solution', 'content': solution})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'codeBlocksExecuted': code_block_count})}\n\n"

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(f"Error in stream_analysis: {error_trace}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/api/ml/analyze")
async def analyze(request: AnalysisRequest):
    """Analyze data with streaming response"""
    try:
        # Resolve dataset
        dataset_path = DatasetResolver.resolve(request.dataset)

        return StreamingResponse(
            stream_analysis(request.prompt, str(dataset_path)),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datasets")
async def list_datasets():
    """List available datasets"""
    return {"datasets": DatasetResolver.list_available()}


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "ML Engineer Agent API",
        "version": "2.0.0",
        "endpoints": {
            "/api/ml/analyze": "POST - Run ML analysis (streaming)",
            "/datasets": "GET - List available datasets",
        },
    }


if __name__ == "__main__":
    print("🚀 Starting ML Engineer Agent API Server")
    print("📡 API URL: http://localhost:8000")
    print("📊 Datasets: http://localhost:8000/datasets")
    print("🤖 ML Analysis: http://localhost:8000/api/ml/analyze")
    print("\n" + "=" * 80)
    print("Ready to accept requests from Vercel AI SDK")
    print("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
