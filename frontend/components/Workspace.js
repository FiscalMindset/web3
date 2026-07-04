"use client";
import { useCallback, useEffect, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { solidity } from "@replit/codemirror-lang-solidity";
import { tokyoNight } from "@uiw/codemirror-theme-tokyo-night";
import { api } from "@/lib/api";

function langFor(path) {
  if (path.endsWith(".py")) return [python()];
  if (path.endsWith(".sol")) return [solidity];
  if (/\.(js|mjs|ts|json)$/.test(path)) return [javascript()];
  return [];
}

const FILE_ICON = (p) =>
  p.endsWith(".sol") ? "◆" : p.endsWith(".py") ? "𝜋" : /\.(js|mjs|ts)$/.test(p) ? "λ" : "▤";

export default function Workspace({ sessionId, tree, refreshTree, consoleEntries, pushConsole }) {
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  const openFile = useCallback(
    async (path) => {
      try {
        const res = await api(
          `/sessions/${sessionId}/files/content?path=${encodeURIComponent(path)}`
        );
        setSelected(path);
        setContent(res.content);
        setDirty(false);
      } catch (e) {
        pushConsole({ cmd: `open ${path}`, err: String(e) });
      }
    },
    [sessionId, pushConsole]
  );

  // If the agent just created files and nothing is open, open the newest file.
  useEffect(() => {
    const files = tree.filter((t) => t.type === "file");
    if (files.length && selected && !files.some((f) => f.path === selected)) {
      setSelected(null);
      setContent("");
    }
  }, [tree, selected]);

  const save = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/sessions/${sessionId}/files/save`, {
        method: "POST",
        body: { path: selected, content },
      });
      setDirty(false);
      pushConsole({ cmd: `save ${selected}`, ok: "✓ saved" });
    } catch (e) {
      pushConsole({ cmd: `save ${selected}`, err: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const runSelected = async () => {
    if (!selected) return;
    if (dirty) await save();
    setBusy(true);
    pushConsole({ cmd: `run ${selected}`, dim: "running…" });
    try {
      const res = await api(`/sessions/${sessionId}/files/run`, {
        method: "POST",
        body: { path: selected },
      });
      pushConsole({
        cmd: `run ${selected} · exit ${res.exit_code} · ${res.ms}ms`,
        ok: res.stdout || (res.ok ? "✓ ok" : ""),
        err: res.stderr,
      });
      refreshTree();
    } catch (e) {
      pushConsole({ cmd: `run ${selected}`, err: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const files = tree.filter((t) => t.type === "file");

  return (
    <div className="workspace">
      <div className="ws-tabs">
        <div className="ws-tab active">
          workspace<span className="count">{files.length}</span>
        </div>
        <div style={{ flex: 1 }} />
        <button className="btn" style={{ margin: 6 }} onClick={refreshTree}>
          ↻
        </button>
      </div>
      <div className="ws-body">
        {files.length === 0 ? (
          <div className="ws-empty">
            <span className="big">▦</span>
            <span>
              your workspace is empty.
              <br />
              ask sensei to create a file —<br />
              <i>&quot;make a mini blockchain in chain.js and run it&quot;</i>
            </span>
          </div>
        ) : (
          <>
            <div className="file-list" style={{ maxHeight: selected ? 140 : "none" }}>
              {files.map((f) => (
                <button
                  key={f.path}
                  className={`file-row ${selected === f.path ? "active" : ""}`}
                  onClick={() => openFile(f.path)}
                >
                  <span className="icon">{FILE_ICON(f.path)}</span>
                  {f.path}
                  <span className="size">{f.size}b</span>
                </button>
              ))}
            </div>
            {selected && (
              <div className="editor-wrap">
                <div className="editor-bar">
                  <span>{selected}</span>
                  {dirty && <span style={{ color: "var(--amber)" }}>●</span>}
                  <span className="grow" />
                  <button className="btn" onClick={save} disabled={busy || !dirty}>
                    save
                  </button>
                  <button className="btn primary" onClick={runSelected} disabled={busy}>
                    ▶ run
                  </button>
                </div>
                <div className="editor-scroll">
                  <CodeMirror
                    value={content}
                    theme={tokyoNight}
                    extensions={langFor(selected)}
                    onChange={(v) => {
                      setContent(v);
                      setDirty(true);
                    }}
                    basicSetup={{ lineNumbers: true, foldGutter: false }}
                    style={{ fontSize: 12.5 }}
                  />
                </div>
              </div>
            )}
          </>
        )}
        <div className="console">
          <div className="console-bar">
            output
            <span className="grow" />
          </div>
          <div className="console-out">
            {consoleEntries.length === 0 && (
              <span className="dim">— run something and output lands here —</span>
            )}
            {consoleEntries.map((e, i) => (
              <div key={i} className="entry">
                <div className="cmd">$ {e.cmd}</div>
                {e.dim && <span className="dim">{e.dim}</span>}
                {e.ok && <span className="ok">{e.ok}</span>}
                {e.err && <span className="err">{e.err}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
