"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

const RUNNABLE = new Set(["javascript", "js", "python", "py", "solidity", "sol", "typescript"]);
const NORMALISE = { js: "javascript", py: "python", sol: "solidity" };

function Quiz({ spec }) {
  const [picked, setPicked] = useState(null);
  let q;
  try {
    q = JSON.parse(spec);
  } catch {
    return null;
  }
  return (
    <div className="quiz">
      <div className="q-label">◆ Checkpoint</div>
      <div className="q-text">{q.question}</div>
      {q.options.map((opt, i) => {
        let cls = "quiz-opt";
        if (picked !== null) {
          if (i === q.answer) cls += " correct";
          else if (i === picked) cls += " wrong";
        }
        return (
          <button key={i} className={cls} disabled={picked !== null} onClick={() => setPicked(i)}>
            {String.fromCharCode(65 + i)}. {opt}
          </button>
        );
      })}
      {picked !== null && (
        <div className="explain">
          {picked === q.answer ? "✅ Correct. " : "Not quite. "}
          {q.explain}
        </div>
      )}
    </div>
  );
}

function CodeBlock({ lang, code, sessionId, onAskTutor, onRan }) {
  const [output, setOutput] = useState(null);
  const [running, setRunning] = useState(false);
  const language = NORMALISE[lang] || lang;
  const runnable = RUNNABLE.has(lang) && sessionId;

  const run = async () => {
    setRunning(true);
    setOutput(null);
    try {
      const res = await api("/run", {
        method: "POST",
        body: { session_id: sessionId, language, code },
      });
      setOutput(res);
      onRan?.({ label: `run ${language} snippet`, ...res });
    } catch (e) {
      setOutput({ ok: false, stderr: String(e), stdout: "" });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="codeblock">
      <div className="codeblock-bar">
        <span className="lang">{language || "text"}</span>
        <span className="grow" />
        {onAskTutor && (
          <button className="btn" onClick={() => onAskTutor(code, language)}>
            ✦ ask tutor
          </button>
        )}
        {runnable && (
          <button className="btn primary" onClick={run} disabled={running}>
            {running ? "⏳ running…" : "▶ run"}
          </button>
        )}
      </div>
      <pre>
        <code>{code}</code>
      </pre>
      {output && (
        <div className="run-output">
          <div className="meta-line">
            {language === "solidity" ? "solc compile" : language} · exit {output.exit_code} ·{" "}
            {output.ms != null ? `${output.ms}ms` : ""}
          </div>
          {output.stdout && <span className="ok">{output.stdout}</span>}
          {output.stderr && <span className="err">{output.stderr}</span>}
          {!output.stdout && !output.stderr && output.ok && (
            <span className="ok">✓ compiled successfully (ABI + bytecode in workspace build/)</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function Markdown({ children, sessionId, onAskTutor, onRan }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children: kids, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const code = String(kids).replace(/\n$/, "");
            if (!match || (inline ?? !code.includes("\n"))) {
              return (
                <code className={className} {...props}>
                  {kids}
                </code>
              );
            }
            const lang = match[1].toLowerCase();
            if (lang === "quiz") return <Quiz spec={code} />;
            return (
              <CodeBlock
                lang={lang}
                code={code}
                sessionId={sessionId}
                onAskTutor={onAskTutor}
                onRan={onRan}
              />
            );
          },
          pre({ children: kids }) {
            return <>{kids}</>;
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
