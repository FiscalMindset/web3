"""Streaming tutor agent: SSE token stream + tool loop (files, code runner).

Yields event dicts: {type, data}. Types:
  meta         — model + session info, sent first
  token        — one streamed text delta
  tool_call    — the model invoked a tool
  tool_result  — tool finished (includes output)
  files        — refreshed workspace file tree
  usage        — tokens / timing / model metadata, sent last before done
  done
  error
"""
import asyncio
import json
import time

from openai import AsyncOpenAI

from . import memory, sandbox
from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, MAX_TOOL_ROUNDS

client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=120)

SYSTEM_PROMPT = """You are Sensei, an expert Web3 tutor inside an interactive coding workspace.

You teach blockchain, Ethereum, Solidity, smart contracts, DeFi, wallets and dApp development.
You are not a passive explainer — you are hands-on:

- When a student asks you to CREATE a file, use the write_file tool, then briefly explain it.
- When a student asks you to RUN something, use run_file / run_snippet and interpret the real output for them.
- When code errors, read the error, fix the file with write_file, and re-run. Show your debugging thinking.
- Prefer small runnable examples over long lectures. JavaScript (ethers.js-style patterns, but offline-safe), Python, and Solidity (.sol files compile with solc) all work in the workspace.
- The workspace has NO network access for running code — write self-contained examples (simulate chains/hashes with built-ins like node:crypto or hashlib).

Teaching style:
- Adapt to the student's level; check understanding with one short question when it helps.
- Use analogies first, precision second, code third.
- Use markdown: headings, tables when comparing, and fenced code blocks with language tags.
- Keep answers focused. If the student is mid-exercise, don't dump theory.

You may receive [MEMORY] context recalled from earlier in this student's journey — use it to
personalise (their level, what they struggled with, project goals), never recite it verbatim.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the student's workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path, e.g. contracts/Token.sol"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_file",
            "description": "Execute a workspace file (.py, .js, .ts run; .sol compiles with solc). Returns stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_snippet",
            "description": "Run a short throwaway code snippet without creating a visible file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["python", "javascript", "typescript", "solidity"]},
                    "code": {"type": "string"},
                },
                "required": ["language", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or directory from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


class ThinkFilter:
    """Splits a token stream into visible text vs <think>…</think> reasoning.
    Handles tags split across chunk boundaries."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self):
        self.buf = ""
        self.in_think = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        self.buf += text
        out: list[tuple[str, str]] = []
        while True:
            tag = self.CLOSE if self.in_think else self.OPEN
            idx = self.buf.find(tag)
            if idx != -1:
                if idx:
                    out.append(("think" if self.in_think else "text", self.buf[:idx]))
                self.buf = self.buf[idx + len(tag):]
                self.in_think = not self.in_think
                continue
            # keep a tail that could be a partial tag, emit the rest
            keep = 0
            for n in range(min(len(tag) - 1, len(self.buf)), 0, -1):
                if tag.startswith(self.buf[-n:]):
                    keep = n
                    break
            emit = self.buf[: len(self.buf) - keep]
            if emit:
                out.append(("think" if self.in_think else "text", emit))
            self.buf = self.buf[len(self.buf) - keep:]
            return out

    def flush(self) -> list[tuple[str, str]]:
        out = []
        if self.buf:
            out.append(("think" if self.in_think else "text", self.buf))
            self.buf = ""
        return out


async def _exec_tool(session_id: str, name: str, args: dict) -> dict:
    loop = asyncio.get_running_loop()

    def _sync() -> dict:
        if name == "write_file":
            return sandbox.write_file(session_id, args["path"], args["content"])
        if name == "read_file":
            return {"content": sandbox.read_file(session_id, args["path"])}
        if name == "list_files":
            return {"files": sandbox.list_tree(session_id)}
        if name == "run_file":
            return sandbox.run_file(session_id, args["path"])
        if name == "run_snippet":
            return sandbox.run_snippet(session_id, args["language"], args["code"])
        if name == "delete_file":
            return sandbox.delete_file(session_id, args["path"])
        return {"error": f"unknown tool {name}"}

    try:
        return await loop.run_in_executor(None, _sync)
    except Exception as e:
        return {"error": str(e)}


async def run_agent(session_id: str, user_message: str, history: list[dict]):
    started = time.monotonic()
    ttft_ms = None
    total_prompt_tokens = 0
    total_completion_tokens = 0
    rounds = 0
    files_touched = False

    yield {"type": "meta", "data": {"model": LLM_MODEL, "session_id": session_id,
                                    "provider": LLM_BASE_URL.split("/")[2]}}

    # Recall long-term memory (cognee) and prepend as context.
    recalled = await memory.recall(session_id, user_message)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if recalled:
        messages.append({
            "role": "system",
            "content": "[MEMORY] Relevant notes from this student's past sessions:\n- "
                       + "\n- ".join(recalled),
        })
        yield {"type": "memory", "data": {"count": len(recalled)}}
    messages += history
    messages.append({"role": "user", "content": user_message})

    final_text_parts: list[str] = []

    try:
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            stream = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOLS,
                stream=True,
                temperature=0.7,
                stream_options={"include_usage": True},
            )

            tool_calls: dict[int, dict] = {}
            content_parts: list[str] = []
            finish_reason = None
            tf = ThinkFilter()

            async for chunk in stream:
                if chunk.usage:
                    total_prompt_tokens += chunk.usage.prompt_tokens or 0
                    total_completion_tokens += chunk.usage.completion_tokens or 0
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                if delta is None:
                    continue
                if delta.content:
                    if ttft_ms is None:
                        ttft_ms = int((time.monotonic() - started) * 1000)
                    for kind, piece in tf.feed(delta.content):
                        if kind == "think":
                            yield {"type": "think", "data": {"text": piece}}
                        else:
                            content_parts.append(piece)
                            yield {"type": "token", "data": {"text": piece}}
                for tc in delta.tool_calls or []:
                    slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["name"] += tc.function.name
                        if tc.function.arguments:
                            slot["arguments"] += tc.function.arguments

            for kind, piece in tf.flush():
                if kind == "text":
                    content_parts.append(piece)
                    yield {"type": "token", "data": {"text": piece}}
            text = "".join(content_parts).strip()
            if text:
                final_text_parts.append(text)

            if not tool_calls:
                break  # plain answer — done

            # Record the assistant turn that requested tools, then execute them.
            assistant_msg = {
                "role": "assistant",
                "content": text or None,
                "tool_calls": [
                    {"id": s["id"] or f"call_{i}", "type": "function",
                     "function": {"name": s["name"], "arguments": s["arguments"]}}
                    for i, s in sorted(tool_calls.items())
                ],
            }
            messages.append(assistant_msg)

            for i, slot in sorted(tool_calls.items()):
                try:
                    args = json.loads(slot["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                yield {"type": "tool_call", "data": {"name": slot["name"], "args": args}}
                t0 = time.monotonic()
                result = await _exec_tool(session_id, slot["name"], args)
                elapsed = int((time.monotonic() - t0) * 1000)
                if slot["name"] in ("write_file", "delete_file", "run_snippet", "run_file"):
                    files_touched = True
                yield {"type": "tool_result",
                       "data": {"name": slot["name"], "ms": elapsed, "result": result}}
                messages.append({
                    "role": "tool",
                    "tool_call_id": slot["id"] or f"call_{i}",
                    "content": json.dumps(result)[:20_000],
                })

            if files_touched:
                yield {"type": "files", "data": {"tree": sandbox.list_tree(session_id)}}

        final_text = "\n\n".join(p for p in final_text_parts if p.strip())
        elapsed_ms = int((time.monotonic() - started) * 1000)
        usage = {
            "model": LLM_MODEL,
            "elapsed_ms": elapsed_ms,
            "ttft_ms": ttft_ms,
            "prompt_tokens": total_prompt_tokens or None,
            "completion_tokens": total_completion_tokens or None,
            "tool_rounds": rounds,
            "tokens_per_s": round(total_completion_tokens / (elapsed_ms / 1000), 1)
            if total_completion_tokens and elapsed_ms else None,
        }
        yield {"type": "usage", "data": usage}
        yield {"type": "done", "data": {"text": final_text, "usage": usage}}
    except Exception as e:
        yield {"type": "error", "data": {"message": f"{type(e).__name__}: {e}"}}
