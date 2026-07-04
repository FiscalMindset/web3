"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Live view of the cognee memory pipeline:
 *  exchange stored → knowledge graph (cognify) → recalled into prompt */
export default function MemoryPanel({ sessionId, lastRecall, refreshKey }) {
  const [info, setInfo] = useState(null);
  const [consolidating, setConsolidating] = useState(false);
  const [flash, setFlash] = useState("");

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setInfo(await api(`/sessions/${sessionId}/memory`));
    } catch {}
  }, [sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh, refreshKey]);

  const consolidate = async () => {
    setConsolidating(true);
    setFlash("");
    try {
      await api("/memory/consolidate", { method: "POST", body: { session_id: sessionId } });
      setFlash("cognify running on this session — graph builds in background (uses LLM quota)");
      setTimeout(refresh, 4000);
    } catch (e) {
      setFlash(`failed: ${e}`);
    } finally {
      setConsolidating(false);
    }
  };

  const backend = info?.backend || "…";
  const isCognee = backend === "cognee";

  return (
    <div className="mem-panel">
      <div className="mem-pipeline">
        <div className="mem-stage">
          <div className="stage-tag">stage 01 · store</div>
          <div className="stage-title">exchange saved</div>
          <div className="stage-val">
            {info ? `${info.count} note${info.count === 1 ? "" : "s"}` : "…"}
          </div>
          <div className="stage-sub">SQLite · every turn, always</div>
        </div>

        <div className="mem-arrow">▼ cognee.add()</div>

        <div className={`mem-stage ${isCognee ? "live" : "degraded"}`}>
          <div className="stage-tag">stage 02 · graph</div>
          <div className="stage-title">knowledge graph</div>
          <div className="stage-val">
            {isCognee ? "cognee" : "fallback"}
            {info?.cognify_pending > 0 && (
              <span className="pending"> · {info.cognify_pending} pending</span>
            )}
          </div>
          <div className="stage-sub">
            {isCognee
              ? "fastembed local embeddings · cognify on demand"
              : "cognee offline — SQLite keyword search active"}
          </div>
          {isCognee && (
            <button className="btn amber" onClick={consolidate} disabled={consolidating}>
              {consolidating ? "⏳ scheduling…" : "⚡ consolidate graph"}
            </button>
          )}
        </div>

        <div className="mem-arrow">▼ search(CHUNKS) · no LLM cost</div>

        <div className={`mem-stage ${lastRecall?.length ? "live" : ""}`}>
          <div className="stage-tag">stage 03 · recall</div>
          <div className="stage-title">injected into prompt</div>
          <div className="stage-val">
            {lastRecall ? `${lastRecall.length} recalled last turn` : "nothing yet"}
          </div>
          {(lastRecall || []).map((r, i) => (
            <div key={i} className="recall-item">
              {r}
            </div>
          ))}
        </div>
      </div>

      {flash && <div className="mem-flash">{flash}</div>}

      <div className="mem-list-head">
        stored notes <span>{info?.count ?? 0}</span>
        <button className="btn" onClick={refresh}>
          ↻
        </button>
      </div>
      <div className="mem-list">
        {!info?.notes?.length && (
          <div className="ws-empty" style={{ padding: 16 }}>
            <span>no memories yet — chat with sensei and every exchange lands here</span>
          </div>
        )}
        {(info?.notes || []).map((n, i) => (
          <div key={i} className="mem-note">
            {n.content}
          </div>
        ))}
      </div>
    </div>
  );
}
