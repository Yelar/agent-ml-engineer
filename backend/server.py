"""
HTTP and WebSocket server for connecting the Next.js frontend with the ML Engineer agent.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.config import Config

logger = logging.getLogger(__name__)


class SessionState:
    """In-memory state for a frontend session."""

    def __init__(self, session_id: str, dataset_paths: List[str]):
        self.session_id = session_id
        self.dataset_paths = dataset_paths
        self.created_at = datetime.utcnow()
        self.event_history: List[Dict[str, Any]] = []
        self.prompts: List[str] = []
        self.current_task: Optional[asyncio.Task] = None
        self._listeners: set[asyncio.Queue] = set()

    async def broadcast(self, event: Dict[str, Any]) -> None:
        """Store and broadcast an event to all subscribers."""
        self.event_history.append(event)

        disconnected: List[asyncio.Queue] = []
        for queue in list(self._listeners):
            try:
                await queue.put(event)
            except asyncio.CancelledError:
                disconnected.append(queue)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Dropping listener for session %s: %s", self.session_id, exc)
                disconnected.append(queue)

        for queue in disconnected:
            self._listeners.discard(queue)

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to future events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a listener queue."""
        self._listeners.discard(queue)


class SessionManager:
    """Manage active frontend sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    def generate_session_id(self) -> str:
        return uuid.uuid4().hex

    async def create_session(self, session_id: str, dataset_paths: List[str]) -> SessionState:
        session = SessionState(session_id=session_id, dataset_paths=dataset_paths)
        async with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)


session_manager = SessionManager()
app = FastAPI(title="ML Engineer Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_STORAGE_DIR = Config.BASE_DIR / "sessions"
SESSION_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACTS_ROUTE = "/artifacts"
RUNS_ROUTE = "/runs"

app.mount(ARTIFACTS_ROUTE, StaticFiles(directory=str(Config.ARTIFACTS_DIR)), name="artifacts")
app.mount(RUNS_ROUTE, StaticFiles(directory=str(Config.RUNS_DIR)), name="runs")


class UploadResponse(BaseModel):
    session_id: str
    datasets: List[str]


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Identifier returned from /upload")
    message: str = Field(..., description="Prompt or question for the agent")
    model: Optional[str] = Field(None, description="Override the default model")
    reasoning_effort: Optional[str] = Field(None, description="Reasoning effort for GPT-5 family models")
    max_iterations: Optional[int] = Field(None, description="Override maximum agent iterations")


class ChatResponse(BaseModel):
    reply: str


def create_event(event_type: str, payload: Any, step: Optional[str] = None) -> Dict[str, Any]:
    """Helper to create websocket events with consistent metadata."""
    event: Dict[str, Any] = {
        "event_id": uuid.uuid4().hex,
        "type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if step is not None:
        event["step"] = step
    return event


def _build_public_url(file_path: Path, base_dir: Path, mount_path: str) -> Optional[str]:
    """
    Build a publicly accessible URL for a file relative to a mounted directory.

    Returns None if the file is not inside the supplied base directory.
    """
    try:
        relative_path = file_path.relative_to(base_dir)
    except ValueError:
        return None

    safe_path = quote(relative_path.as_posix())
    return f"{mount_path}/{safe_path}"


async def run_agent_for_session(session: SessionState, request: ChatRequest) -> None:
    """Execute the ML Engineer agent and stream events back to the client."""
    prompt = request.message.strip()
    await session.broadcast(create_event("status", {"stage": "starting", "prompt": prompt}))

    dataset_argument: Any
    if len(session.dataset_paths) == 1:
        dataset_argument = session.dataset_paths[0]
    else:
        dataset_argument = session.dataset_paths

    try:
        try:
            agent = MLEngineerAgent(
                dataset_path=dataset_argument,
                model_name=request.model,
                max_iterations=request.max_iterations,
                verbose=False,
                reasoning_effort=request.reasoning_effort,
            )
        except Exception as exc:
            logger.exception("Failed to initialise agent", exc_info=exc)
            await session.broadcast(create_event("error", {"message": str(exc)}))
            await session.broadcast(create_event("status", {"stage": "failed"}))
            return

        await session.broadcast(create_event("status", {"stage": "running", "prompt": prompt}))

        try:
            result = await asyncio.to_thread(agent.run, prompt)
        except Exception as exc:  # pragma: no cover - depends on runtime environment
            logger.exception("Agent run failed", exc_info=exc)
            await session.broadcast(create_event("error", {"message": str(exc)}))
            await session.broadcast(create_event("status", {"stage": "failed"}))
            return

        plan = result.get("plan")
        if plan:
            await session.broadcast(
                create_event("plan", {"content": plan, "format": "markdown"})
            )

        history = result.get("execution_history", [])
        for index, execution in enumerate(history, start=1):
            code_payload = {
                "step_index": index,
                "code": str(execution.get("code", "") or ""),
                "output": str(execution.get("output", "") or ""),
                "error": str(execution.get("error", "") or ""),
                "success": bool(execution.get("success", False)),
            }
            await session.broadcast(create_event("code", code_payload, step=str(index)))

            for plot_idx, plot_base64 in enumerate(execution.get("plots", []) or [], start=1):
                plot_payload = {
                    "step_index": index,
                    "plot_index": plot_idx,
                    "image": plot_base64,
                    "format": "image/png",
                }
                await session.broadcast(create_event("plot", plot_payload, step=str(index)))

        solution = result.get("solution")
        if solution:
            await session.broadcast(
                create_event(
                    "assistant_message",
                    {"content": solution, "format": "markdown", "source": "solution"},
                )
            )
        else:
            await session.broadcast(
                create_event(
                    "assistant_message",
                    {
                        "content": "Agent run completed without a final summary. Review the notebook cells for full context.",
                        "source": "system",
                    },
                )
            )

        metadata_payload = {
            "run_id": result.get("run_id"),
            "artifacts_dir": result.get("artifacts_dir"),
            "log_path": result.get("log_path"),
            "iterations": result.get("iterations"),
        }
        await session.broadcast(create_event("metadata", metadata_payload))

        artifacts: List[Dict[str, Any]] = []

        artifacts_dir_value = result.get("artifacts_dir")
        if artifacts_dir_value:
            artifacts_dir_path = Path(artifacts_dir_value)
            if artifacts_dir_path.exists():
                for file_path in artifacts_dir_path.rglob("*"):
                    if file_path.is_file():
                        url = _build_public_url(file_path, Config.ARTIFACTS_DIR, ARTIFACTS_ROUTE)
                        if url:
                            artifacts.append(
                                {
                                    "name": file_path.name,
                                    "url": url,
                                    "path": str(file_path),
                                    "kind": "artifact",
                                }
                            )

        log_path_value = result.get("log_path")
        if log_path_value:
            log_file = Path(log_path_value)
            if log_file.exists():
                url = _build_public_url(log_file, Config.RUNS_DIR, RUNS_ROUTE)
                if url:
                    artifacts.append(
                        {
                            "name": log_file.name,
                            "url": url,
                            "path": str(log_file),
                            "kind": "log",
                        }
                    )

        if artifacts:
            await session.broadcast(create_event("artifacts", {"items": artifacts}))

        await session.broadcast(create_event("status", {"stage": "completed"}))
    finally:
        session.current_task = None


@app.post("/upload", response_model=UploadResponse)
async def upload_datasets(files: List[UploadFile] = File(...)) -> UploadResponse:
    """Upload one or more datasets and initialise a session."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    session_id = session_manager.generate_session_id()
    session_dir = SESSION_STORAGE_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    dataset_paths: List[str] = []

    for file in files:
        filename = Path(file.filename).name or "dataset.csv"
        destination = session_dir / filename
        try:
            with destination.open("wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
        finally:
            await file.close()

        dataset_paths.append(str(destination))

    await session_manager.create_session(session_id=session_id, dataset_paths=dataset_paths)
    logger.info("Created session %s with %d dataset(s)", session_id, len(dataset_paths))

    return UploadResponse(session_id=session_id, datasets=dataset_paths)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle a chat prompt by launching the agent in the background."""
    session = session_manager.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.current_task and not session.current_task.done():
        raise HTTPException(status_code=409, detail="Agent already processing a prompt for this session")

    session.prompts.append(request.message)
    session.current_task = asyncio.create_task(run_agent_for_session(session, request))

    return ChatResponse(reply="Agent is processing your request.")


@app.websocket("/sessions/{session_id}/events")
async def session_events(websocket: WebSocket, session_id: str) -> None:
    """Stream session events to the frontend."""
    session = session_manager.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.send_json(create_event("error", {"message": "Session not found"}))
        await websocket.close(code=4004)
        return

    await websocket.accept()
    queue = await session.subscribe()

    try:
        for event in session.event_history:
            await websocket.send_json(event)

        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for session %s", session_id)
    finally:
        session.unsubscribe(queue)
