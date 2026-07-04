"""SQLite persistence for sessions, chat history and fallback memory."""
import json
import sqlite3
import threading
import time
import uuid

from .config import DB_PATH

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT 'New session',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                meta TEXT DEFAULT '{}',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                content TEXT,
                created_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
            """
        )


def create_session(title: str = "New session") -> dict:
    sid = uuid.uuid4().hex[:12]
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO sessions (id, title, created_at) VALUES (?,?,?)",
            (sid, title, time.time()),
        )
    return {"id": sid, "title": title}


def list_sessions() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return [dict(r) for r in rows]


def rename_session(sid: str, title: str) -> None:
    with _lock, _conn() as c:
        c.execute("UPDATE sessions SET title=? WHERE id=?", (title[:80], sid))


def add_message(session_id: str, role: str, content: str, meta: dict | None = None) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO messages (session_id, role, content, meta, created_at) VALUES (?,?,?,?,?)",
            (session_id, role, content, json.dumps(meta or {}), time.time()),
        )


def get_messages(session_id: str, limit: int = 200) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT role, content, meta, created_at FROM messages "
            "WHERE session_id=? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["meta"] = json.loads(d["meta"] or "{}")
        out.append(d)
    return out


def get_history_for_llm(session_id: str, limit: int = 24) -> list[dict]:
    """Last N user/assistant turns in OpenAI message format."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE session_id=? AND role IN ('user','assistant') "
            "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ---- fallback keyword memory (used when cognee is unavailable) ----

def fallback_memory_add(session_id: str, content: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO memories (session_id, content, created_at) VALUES (?,?,?)",
            (session_id, content, time.time()),
        )


def get_memories(session_id: str, limit: int = 100) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT content, created_at FROM memories WHERE session_id=? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def fallback_memory_search(session_id: str, query: str, limit: int = 5) -> list[str]:
    words = [w for w in query.lower().split() if len(w) > 3][:6]
    if not words:
        return []
    clause = " OR ".join(["lower(content) LIKE ?"] * len(words))
    params = [f"%{w}%" for w in words]
    with _lock, _conn() as c:
        rows = c.execute(
            f"SELECT content FROM memories WHERE session_id=? AND ({clause}) "
            "ORDER BY id DESC LIMIT ?",
            (session_id, *params, limit),
        ).fetchall()
    return [r["content"] for r in rows]
