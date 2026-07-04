"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import LessonView from "@/components/LessonView";
import Workspace from "@/components/Workspace";
import { api, streamChat } from "@/lib/api";

function QuotaChip({ health }) {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);
  if (!health?.ok) {
    return (
      <span className="chip main-chip">
        <span className="dot off" /> backend offline
      </span>
    );
  }
  // samagama reservation window: 19:00–23:00 IST
  const istMinutes =
    (now.getUTCHours() * 60 + now.getUTCMinutes() + 5 * 60 + 30) % (24 * 60);
  const open = istMinutes >= 19 * 60 && istMinutes < 23 * 60;
  return (
    <span className="chip main-chip" title="samagama model reservation: 19:00–23:00 IST">
      <span className={`dot ${open ? "" : "off"}`} />
      <b>{health.model}</b>&nbsp;·{" "}
      {open ? "quota open until 23:00 IST" : "quota closed · opens 19:00 IST"}
    </span>
  );
}

export default function Home() {
  const [sessionId, setSessionId] = useState(null);
  const [health, setHealth] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [activeLesson, setActiveLesson] = useState(null); // null = chat view
  const [lessonBody, setLessonBody] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [tree, setTree] = useState([]);
  const [consoleEntries, setConsoleEntries] = useState([]);
  const [view, setView] = useState("chat"); // narrow screens: learn | chat | workspace
  const [lastRecall, setLastRecall] = useState(null);
  const [memRefreshKey, setMemRefreshKey] = useState(0);
  const abortRef = useRef(null);

  const pushConsole = useCallback((entry) => {
    setConsoleEntries((c) => [...c, entry].slice(-60));
  }, []);

  const refreshTree = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await api(`/sessions/${sessionId}/files`);
      setTree(res.tree || []);
    } catch {}
  }, [sessionId]);

  // boot: session (persisted), health, lessons
  useEffect(() => {
    (async () => {
      try {
        setHealth(await api("/health"));
      } catch {
        setHealth({ ok: false });
      }
      try {
        setLessons(await api("/lessons"));
      } catch {}
      let sid = localStorage.getItem("w3t_session");
      if (sid) {
        try {
          const hist = await api(`/sessions/${sid}/messages`);
          setMessages(
            hist.map((m) => ({ role: m.role, content: m.content, meta: m.meta, events: [] }))
          );
        } catch {
          sid = null;
        }
      }
      if (!sid) {
        const s = await api("/sessions", { method: "POST", body: {} });
        sid = s.id;
        localStorage.setItem("w3t_session", sid);
      }
      setSessionId(sid);
    })();
  }, []);

  useEffect(() => {
    refreshTree();
  }, [refreshTree]);

  const newSession = async () => {
    const s = await api("/sessions", { method: "POST", body: {} });
    localStorage.setItem("w3t_session", s.id);
    setSessionId(s.id);
    setMessages([]);
    setTree([]);
    setConsoleEntries([]);
    setActiveLesson(null);
    setLastRecall(null);
    setMemRefreshKey((k) => k + 1);
  };

  const send = useCallback(
    async (text) => {
      if (!sessionId || streaming) return;
      setActiveLesson(null);
      setView("chat");
      setMessages((m) => [
        ...m,
        { role: "user", content: text },
        { role: "assistant", content: "", events: [], meta: null, memoryCount: 0 },
      ]);
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const patchLast = (fn) =>
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = fn({ ...copy[copy.length - 1] });
          return copy;
        });

      try {
        await streamChat({
          sessionId,
          message: text,
          signal: controller.signal,
          onEvent: (type, data) => {
            if (type === "token") {
              patchLast((msg) => ({ ...msg, content: msg.content + data.text }));
            } else if (type === "think") {
              patchLast((msg) => ({ ...msg, thinking: (msg.thinking || "") + data.text }));
            } else if (type === "memory") {
              patchLast((msg) => ({ ...msg, memoryCount: data.count }));
              setLastRecall(data.items || []);
            } else if (type === "tool_call") {
              patchLast((msg) => ({
                ...msg,
                events: [...msg.events, { name: data.name, args: data.args }],
              }));
            } else if (type === "tool_result") {
              patchLast((msg) => {
                const events = [...msg.events];
                for (let i = events.length - 1; i >= 0; i--) {
                  if (events[i].name === data.name && !events[i].result) {
                    events[i] = { ...events[i], result: data.result, ms: data.ms };
                    break;
                  }
                }
                return { ...msg, events };
              });
              if (["run_file", "run_snippet"].includes(data.name) && data.result) {
                pushConsole({
                  cmd: `sensei: ${data.name}`,
                  ok: data.result.stdout,
                  err: data.result.stderr,
                });
              }
            } else if (type === "files") {
              setTree(data.tree || []);
            } else if (type === "usage") {
              patchLast((msg) => ({ ...msg, meta: data }));
            } else if (type === "error") {
              const quotaClosed =
                data.message.includes("No active reservation") || data.message.includes("403");
              patchLast((msg) => ({
                ...msg,
                content:
                  msg.content +
                  (quotaClosed
                    ? "\n\n> ⏰ **Model quota is closed right now.** The samagama window is **19:00–23:00 IST** — Sensei can chat again then.\n> Meanwhile: lesson **▶ run** buttons and the workspace editor still work (they don't use the LLM)."
                    : `\n\n> ⚠️ **${data.message}**`),
              }));
            }
          },
        });
      } catch (e) {
        patchLast((msg) => ({ ...msg, content: msg.content + `\n\n> ⚠️ connection error: ${e}` }));
      } finally {
        setStreaming(false);
        abortRef.current = null;
        setMemRefreshKey((k) => k + 1); // memory panel re-fetches after each turn
      }
    },
    [sessionId, streaming, pushConsole]
  );

  const askTutor = useCallback(
    (code, language, customText) => {
      const text =
        customText ||
        `Explain this ${language || ""} code from the lesson step by step — what would trip up a beginner?\n\n\`\`\`${language || ""}\n${code}\n\`\`\``;
      send(text);
    },
    [send]
  );

  const openLesson = async (slug) => {
    setActiveLesson(slug);
    setLessonBody(null);
    setView("chat"); // lesson renders in the center pane

    try {
      setLessonBody(await api(`/lessons/${slug}`));
    } catch {
      setActiveLesson(null);
    }
  };

  const onRan = useCallback(
    (res) => pushConsole({ cmd: res.label, ok: res.stdout, err: res.stderr }),
    [pushConsole]
  );

  const modules = {};
  for (const l of lessons) (modules[l.module] = modules[l.module] || []).push(l);

  return (
    <div className="shell">
      <header className="header">
        <div className="brand">
          <span className="glyph">◆_</span> SENSEI
          <span className="sub">web3 tutor workspace</span>
        </div>
        <span className="spacer" />
        <QuotaChip health={health} />
        <span className="chip">
          memory <b>{health?.memory?.backend || "…"}</b>
        </span>
        <button className="btn" onClick={newSession}>
          + new session
        </button>
      </header>

      <div className={`main view-${view}`}>
        <nav className="rail">
          <button
            className={`rail-item ${activeLesson === null ? "active" : ""}`}
            onClick={() => setActiveLesson(null)}
          >
            <span className="num">◆</span> Tutor chat
          </button>
          {Object.entries(modules).map(([mod, items]) => (
            <div key={mod}>
              <div className="section">{mod}</div>
              {items.map((l) => (
                <button
                  key={l.slug}
                  className={`rail-item ${activeLesson === l.slug ? "active" : ""}`}
                  onClick={() => openLesson(l.slug)}
                >
                  <span className="num">{String(l.order).padStart(2, "0")}</span>
                  {l.title}
                  <span className="mins">{l.minutes}m</span>
                </button>
              ))}
            </div>
          ))}
          <div className="section">Session</div>
          <div style={{ padding: "4px 10px", fontFamily: "var(--mono)", fontSize: 10, color: "var(--faint)" }}>
            id {sessionId || "…"}
            <br />
            {tree.filter((t) => t.type === "file").length} files in workspace
          </div>
        </nav>

        <section className="center">
          {activeLesson && lessonBody ? (
            <LessonView
              lesson={lessonBody}
              sessionId={sessionId}
              onAskTutor={askTutor}
              onRan={onRan}
            />
          ) : activeLesson ? (
            <div className="thinking" style={{ padding: 30 }}>
              <span className="pulse" /> loading lesson…
            </div>
          ) : (
            <ChatPanel
              messages={messages}
              streaming={streaming}
              onSend={send}
              sessionId={sessionId}
              onAskTutor={askTutor}
              onRan={onRan}
            />
          )}
        </section>

        <Workspace
          sessionId={sessionId}
          tree={tree}
          refreshTree={refreshTree}
          consoleEntries={consoleEntries}
          pushConsole={pushConsole}
          lastRecall={lastRecall}
          memRefreshKey={memRefreshKey}
        />
      </div>

      <nav className="mobile-nav">
        {[
          ["learn", "▤", "learn"],
          ["chat", "◆", "tutor"],
          ["workspace", "▦", `workspace${tree.filter((t) => t.type === "file").length ? ` · ${tree.filter((t) => t.type === "file").length}` : ""}`],
        ].map(([key, icon, label]) => (
          <button
            key={key}
            className={view === key ? "active" : ""}
            onClick={() => setView(key)}
          >
            <span>{icon}</span> {label}
          </button>
        ))}
      </nav>
    </div>
  );
}
