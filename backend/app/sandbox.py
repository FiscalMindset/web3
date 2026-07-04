"""Per-session file workspace + code runner.

Every chat session gets an isolated directory under WORKSPACES_DIR. The agent
(and the lesson "Run" buttons) can create files and execute them there.
Execution is a subprocess with CPU/time limits — good enough for tutoring
snippets, not a hard security boundary; the droplet runs it inside Docker.
"""
import os
import resource
import shutil
import subprocess
import sys
from pathlib import Path

from .config import RUN_OUTPUT_LIMIT, RUN_TIMEOUT_SECONDS, WORKSPACES_DIR

RUNNERS = {
    ".py": [sys.executable, "-I"],
    ".js": ["node"],
    ".mjs": ["node"],
    ".ts": ["node", "--experimental-strip-types"],
}

LANG_EXT = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "node": ".js",
    "typescript": ".ts",
    "solidity": ".sol",
    "sol": ".sol",
}


def session_dir(session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:64]
    d = WORKSPACES_DIR / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(session_id: str, rel: str) -> Path:
    base = session_dir(session_id).resolve()
    p = (base / rel.lstrip("/")).resolve()
    if not str(p).startswith(str(base)):
        raise ValueError(f"Path escapes workspace: {rel}")
    return p


def write_file(session_id: str, rel: str, content: str) -> dict:
    p = _safe_path(session_id, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": rel, "bytes": len(content.encode())}


def read_file(session_id: str, rel: str) -> str:
    p = _safe_path(session_id, rel)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {rel}")
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:100_000]


def delete_file(session_id: str, rel: str) -> dict:
    p = _safe_path(session_id, rel)
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()
    return {"deleted": rel}


def list_tree(session_id: str) -> list[dict]:
    base = session_dir(session_id)
    out = []
    for p in sorted(base.rglob("*")):
        if any(part.startswith(".") or part == "node_modules" for part in p.parts):
            continue
        rel = str(p.relative_to(base))
        out.append({
            "path": rel,
            "type": "dir" if p.is_dir() else "file",
            "size": p.stat().st_size if p.is_file() else 0,
        })
    return out[:400]


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (RUN_TIMEOUT_SECONDS, RUN_TIMEOUT_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (20_000_000, 20_000_000))
    os.setsid()


def _truncate(s: str) -> str:
    if len(s) > RUN_OUTPUT_LIMIT:
        return s[:RUN_OUTPUT_LIMIT] + f"\n… [truncated, {len(s)} chars total]"
    return s


def _exec(cmd: list[str], cwd: Path) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            preexec_fn=_limits,
            env={"PATH": os.environ.get("PATH", ""), "HOME": str(cwd), "NO_COLOR": "1"},
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": _truncate(proc.stdout),
            "stderr": _truncate(proc.stderr),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": f"Timed out after {RUN_TIMEOUT_SECONDS}s"}
    except FileNotFoundError:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": f"Runtime not installed: {cmd[0]}"}


def run_file(session_id: str, rel: str) -> dict:
    p = _safe_path(session_id, rel)
    if not p.is_file():
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": f"No such file: {rel}"}
    ext = p.suffix.lower()
    cwd = session_dir(session_id)

    if ext == ".sol":
        solc = shutil.which("solc")
        if not solc:
            return {"ok": False, "exit_code": -1, "stdout": "",
                    "stderr": "solc is not installed in this environment yet."}
        return _exec([solc, "--bin", "--abi", "--optimize", "-o", str(cwd / "build"),
                      "--overwrite", str(p)], cwd)

    runner = RUNNERS.get(ext)
    if not runner:
        return {"ok": False, "exit_code": -1, "stdout": "",
                "stderr": f"Don't know how to run '{ext}' files. Supported: {', '.join(RUNNERS)} + .sol"}
    return _exec([*runner, str(p)], cwd)


def run_snippet(session_id: str, language: str, code: str) -> dict:
    ext = LANG_EXT.get(language.lower().strip())
    if not ext:
        return {"ok": False, "exit_code": -1, "stdout": "",
                "stderr": f"Unsupported language '{language}'. Use python, javascript, typescript or solidity."}
    rel = f".snippets/snippet{ext}"
    p = _safe_path(session_id, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")
    return run_file(session_id, rel)
