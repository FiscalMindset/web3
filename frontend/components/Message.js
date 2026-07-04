"use client";
import Markdown from "./Markdown";

function ToolCard({ ev }) {
  const { name, args = {}, result, ms } = ev;
  const detail =
    args.path ||
    (args.language ? `${args.language} snippet` : "") ||
    (name === "list_files" ? "workspace" : "");
  const ok = result ? result.ok !== false && !result.error : null;
  const output =
    result &&
    [result.stdout, result.stderr, result.error]
      .filter(Boolean)
      .join("\n")
      .slice(0, 1200);

  const ICONS = {
    write_file: "✎",
    read_file: "⊙",
    list_files: "☰",
    run_file: "▶",
    run_snippet: "▶",
    delete_file: "✕",
  };

  return (
    <div className={`tool-card ${ok === true ? "ok" : ok === false ? "fail" : ""}`}>
      <span className="t-name">
        {ICONS[name] || "⚙"} {name}
      </span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <span className="t-detail">
          {detail}
          {ms != null && ` · ${ms}ms`}
          {result && ok === true && name === "write_file" && " · saved"}
        </span>
        {output && <div className="t-out">{output}</div>}
      </div>
    </div>
  );
}

function MetaChips({ meta }) {
  if (!meta || !meta.model) return null;
  const chips = [
    ["model", meta.model],
    meta.elapsed_ms != null && ["total", `${(meta.elapsed_ms / 1000).toFixed(1)}s`],
    meta.ttft_ms != null && ["first token", `${meta.ttft_ms}ms`],
    meta.prompt_tokens != null && ["in", `${meta.prompt_tokens} tok`],
    meta.completion_tokens != null && ["out", `${meta.completion_tokens} tok`],
    meta.tokens_per_s != null && ["speed", `${meta.tokens_per_s} tok/s`],
    meta.tool_rounds > 1 && ["tool rounds", meta.tool_rounds],
  ].filter(Boolean);
  return (
    <div className="msg-meta">
      {chips.map(([k, v]) => (
        <span key={k} className="meta-chip">
          {k} <b>{v}</b>
        </span>
      ))}
    </div>
  );
}

export default function Message({ msg, sessionId, onAskTutor, onRan, streaming }) {
  const isUser = msg.role === "user";
  return (
    <div className={`msg ${isUser ? "user" : "ai"}`}>
      <div className="msg-head">
        <span className={isUser ? "who-user" : "who-ai"}>
          {isUser ? "▸ you" : "◆ sensei"}
        </span>
        {msg.memoryCount > 0 && (
          <span className="time">recalled {msg.memoryCount} memories</span>
        )}
      </div>
      <div className="msg-body">
        {msg.thinking && (
          <details className="think-block" open={streaming && !msg.content}>
            <summary>
              ∴ model reasoning <span>{msg.thinking.length} chars</span>
            </summary>
            <div className="think-text">{msg.thinking}</div>
          </details>
        )}
        {(msg.events || []).map((ev, i) => (
          <ToolCard key={i} ev={ev} />
        ))}
        {isUser ? (
          <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
        ) : (
          <>
            {msg.content ? (
              <Markdown sessionId={sessionId} onAskTutor={onAskTutor} onRan={onRan}>
                {msg.content}
              </Markdown>
            ) : streaming && !(msg.events || []).length ? (
              <div className="thinking">
                <span className="pulse" /> sensei is thinking…
              </div>
            ) : null}
            {streaming && msg.content && <span className="cursor" />}
          </>
        )}
        {!streaming && !isUser && <MetaChips meta={msg.meta} />}
      </div>
    </div>
  );
}
