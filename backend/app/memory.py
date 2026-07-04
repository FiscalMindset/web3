"""Memory layer backed by cognee (github.com/topoteretes/cognee).

- Raw exchanges are always saved to SQLite (cheap, reliable).
- cognee builds a knowledge graph from them: `add()` on every exchange,
  `cognify()` consolidated in the background (it costs LLM calls, so it is
  throttled — the samagama quota window is 19:00–23:00).
- Retrieval prefers cognee semantic search (CHUNKS = no LLM cost) and falls
  back to SQLite keyword search whenever cognee is unavailable or errors.

Embeddings use fastembed locally so retrieval never depends on the LLM proxy
offering an /embeddings endpoint.
"""
import asyncio
import logging
import os
import threading

from . import db
from .config import COGNEE_ENABLED, DATA_DIR, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

log = logging.getLogger("memory")

_cognee = None
_cognee_ready = False
_cognify_pending: set[str] = set()
_cognify_lock = threading.Lock()


def _dataset(session_id: str) -> str:
    return f"web3_tutor_{session_id}"


def init_cognee() -> None:
    """Configure cognee env before import. Never raises."""
    global _cognee, _cognee_ready
    if not COGNEE_ENABLED:
        log.info("cognee disabled via COGNEE_ENABLED=0; using SQLite fallback memory")
        return
    try:
        os.environ.setdefault("LLM_PROVIDER", "custom")
        os.environ.setdefault("LLM_MODEL", f"openai/{LLM_MODEL}")
        os.environ.setdefault("LLM_ENDPOINT", LLM_BASE_URL)
        os.environ.setdefault("LLM_API_KEY", LLM_API_KEY)
        os.environ.setdefault("EMBEDDING_PROVIDER", "fastembed")
        os.environ.setdefault("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        os.environ.setdefault("EMBEDDING_DIMENSIONS", "384")
        os.environ.setdefault("EMBEDDING_MAX_TOKENS", "256")
        os.environ.setdefault("TELEMETRY_DISABLED", "1")
        cognee_dir = DATA_DIR / "cognee"
        cognee_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("DATA_ROOT_DIRECTORY", str(cognee_dir / "data"))
        os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", str(cognee_dir / "system"))

        import cognee  # noqa: PLC0415

        _cognee = cognee
        _cognee_ready = True
        log.info("cognee memory layer initialised (embeddings: fastembed local)")
    except Exception as e:  # pragma: no cover - import/env issues
        log.warning("cognee unavailable, falling back to SQLite memory: %s", e)
        _cognee = None
        _cognee_ready = False


def status() -> dict:
    return {
        "backend": "cognee" if _cognee_ready else "sqlite-fallback",
        "cognify_pending": len(_cognify_pending),
    }


async def remember(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """Store one exchange. Always hits SQLite; cognee add is best-effort."""
    note = f"Student asked: {user_msg}\nTutor answered: {assistant_msg[:1500]}"
    db.fallback_memory_add(session_id, note)
    if not _cognee_ready:
        return
    try:
        await _cognee.add(note, dataset_name=_dataset(session_id))
        with _cognify_lock:
            _cognify_pending.add(session_id)
    except Exception as e:
        log.warning("cognee.add failed: %s", e)


async def consolidate(session_id: str | None = None) -> dict:
    """Run cognify (LLM-heavy; called in background).

    Explicit session_id wins. Otherwise take the pending queue — and since
    that queue is process-memory (lost on restart/deploy), fall back to every
    session that has stored notes so consolidation is always possible.
    """
    if not _cognee_ready:
        return {"ok": False, "reason": "cognee not available"}
    with _cognify_lock:
        if session_id:
            targets = [session_id]
        else:
            targets = list(_cognify_pending) or db.get_memory_sessions()
        for t in targets:
            _cognify_pending.discard(t)
    done = []
    for sid in targets:
        try:
            await _cognee.cognify([_dataset(sid)])
            done.append(sid)
        except Exception as e:
            log.warning("cognee.cognify failed for %s: %s", sid, e)
    return {"ok": True, "consolidated": done}


async def recall(session_id: str, query: str, limit: int = 5) -> list[str]:
    """Semantic recall via cognee, keyword fallback via SQLite."""
    if _cognee_ready:
        try:
            from cognee import SearchType  # noqa: PLC0415

            results = await asyncio.wait_for(
                _cognee.search(
                    query_text=query,
                    query_type=SearchType.CHUNKS,
                    datasets=[_dataset(session_id)],
                    top_k=limit,
                ),
                timeout=10,
            )
            texts = []
            for r in results or []:
                if isinstance(r, dict):
                    texts.append(str(r.get("text") or r.get("chunk") or r)[:800])
                else:
                    texts.append(str(r)[:800])
            if texts:
                return texts[:limit]
        except Exception as e:
            log.warning("cognee.search failed, using fallback: %s", e)
    return db.fallback_memory_search(session_id, query, limit)
