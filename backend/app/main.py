"""Web3 Tutor backend — FastAPI + SSE streaming agent + cognee memory."""
import asyncio
import json
import logging
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import db, lessons, memory, sandbox
from .agent import run_agent
from .config import LLM_BASE_URL, LLM_MODEL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

app = FastAPI(title="Web3 Tutor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    db.init_db()
    memory.init_cognee()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class RunRequest(BaseModel):
    session_id: str
    language: str
    code: str


class SessionCreate(BaseModel):
    title: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
async def health() -> dict:
    return {
        "ok": True,
        "model": LLM_MODEL,
        "provider": LLM_BASE_URL,
        "memory": memory.status(),
        "time": time.time(),
    }


# ---------- sessions ----------

@app.post("/api/sessions")
async def create_session(body: SessionCreate) -> dict:
    return db.create_session(body.title or "New session")


@app.get("/api/sessions")
async def get_sessions() -> list[dict]:
    return db.list_sessions()


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str) -> list[dict]:
    return db.get_messages(session_id)


# ---------- chat (SSE) ----------

@app.post("/api/chat")
async def chat(body: ChatRequest, background: BackgroundTasks) -> StreamingResponse:
    session_id = body.session_id
    user_message = body.message.strip()
    if not user_message:
        raise HTTPException(400, "Empty message")

    history = db.get_history_for_llm(session_id)
    if not history:
        db.rename_session(session_id, user_message[:60])
    db.add_message(session_id, "user", user_message)

    async def stream():
        final_text = ""
        usage: dict = {}
        try:
            async for event in run_agent(session_id, user_message, history):
                if event["type"] == "done":
                    final_text = event["data"].get("text", "")
                    usage = event["data"].get("usage", {})
                yield _sse(event["type"], event["data"])
        except asyncio.CancelledError:
            return
        finally:
            if final_text:
                db.add_message(session_id, "assistant", final_text, meta=usage)
                try:
                    await memory.remember(session_id, user_message, final_text)
                except Exception as e:
                    log.warning("memory.remember failed: %s", e)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- memory ----------

@app.post("/api/memory/consolidate")
async def consolidate(background: BackgroundTasks) -> dict:
    background.add_task(memory.consolidate)
    return {"scheduled": True, **memory.status()}


@app.get("/api/memory/status")
async def memory_status() -> dict:
    return memory.status()


# ---------- workspace ----------

@app.get("/api/sessions/{session_id}/files")
async def files(session_id: str) -> dict:
    return {"tree": sandbox.list_tree(session_id)}


@app.get("/api/sessions/{session_id}/files/content")
async def file_content(session_id: str, path: str) -> dict:
    try:
        return {"path": path, "content": sandbox.read_file(session_id, path)}
    except FileNotFoundError:
        raise HTTPException(404, f"No such file: {path}")
    except ValueError as e:
        raise HTTPException(400, str(e))


class SaveFileRequest(BaseModel):
    path: str
    content: str


class RunFileRequest(BaseModel):
    path: str


@app.post("/api/sessions/{session_id}/files/save")
async def save_file(session_id: str, body: SaveFileRequest) -> dict:
    try:
        return sandbox.write_file(session_id, body.path, body.content)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/sessions/{session_id}/files/run")
async def run_workspace_file(session_id: str, body: RunFileRequest) -> dict:
    loop = asyncio.get_running_loop()
    t0 = time.monotonic()
    result = await loop.run_in_executor(None, sandbox.run_file, session_id, body.path)
    result["ms"] = int((time.monotonic() - t0) * 1000)
    return result


@app.post("/api/run")
async def run(body: RunRequest) -> dict:
    loop = asyncio.get_running_loop()
    t0 = time.monotonic()
    result = await loop.run_in_executor(
        None, sandbox.run_snippet, body.session_id, body.language, body.code
    )
    result["ms"] = int((time.monotonic() - t0) * 1000)
    return result


# ---------- lessons ----------

@app.get("/api/lessons")
async def all_lessons() -> list[dict]:
    return lessons.list_lessons()


@app.get("/api/lessons/{slug}")
async def one_lesson(slug: str) -> dict:
    lesson = lessons.get_lesson(slug)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson
