"use client";
import { useEffect, useRef, useState } from "react";
import Message from "./Message";

const SUGGESTIONS = [
  {
    title: "explain",
    text: "Explain how gas fees work like I'm a backend developer who's never touched crypto",
  },
  {
    title: "build + run",
    text: "Create a file blockchain.js with a mini proof-of-work blockchain and run it",
  },
  {
    title: "solidity",
    text: "Write an ERC-20 token contract in contracts/MyToken.sol, compile it, and walk me through every line",
  },
  {
    title: "debug me",
    text: "Give me a Solidity contract with 3 hidden bugs, let me try to find them, then reveal",
  },
];

export default function ChatPanel({
  messages,
  streaming,
  onSend,
  sessionId,
  onAskTutor,
  onRan,
}) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const taRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const send = () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    onSend(text);
  };

  return (
    <>
      <div className="chat-scroll" ref={scrollRef}>
        <div className="chat-inner">
          {messages.length === 0 && (
            <div className="hero">
              <h1>
                Learn Web3 by <span className="accent">doing</span>.
              </h1>
              <p>
                Sensei doesn&apos;t just explain — it creates files in your workspace, runs
                them, compiles Solidity, and debugs alongside you. Pick a lesson on the
                left, or throw it a challenge:
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s.title} className="suggestion" onClick={() => onSend(s.text)}>
                    <span className="s-title">◆ {s.title}</span>
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <Message
              key={i}
              msg={m}
              sessionId={sessionId}
              onAskTutor={onAskTutor}
              onRan={onRan}
              streaming={streaming && i === messages.length - 1 && m.role === "assistant"}
            />
          ))}
        </div>
      </div>
      <div className="composer">
        <div className="composer-inner">
          <textarea
            ref={taRef}
            rows={1}
            placeholder='Ask anything — or say "create a file…" / "run it"'
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button className="send" onClick={send} disabled={streaming || !input.trim()}>
            {streaming ? "…" : "Send ↵"}
          </button>
        </div>
        <div className="hint">
          <span>↵ send</span>
          <span>⇧↵ newline</span>
          <span>sensei can create &amp; run files in your workspace →</span>
        </div>
      </div>
    </>
  );
}
