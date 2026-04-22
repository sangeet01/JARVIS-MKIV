/**
 * JARVIS-MKIV — ReasonerFeed.jsx
 *
 * React component for the HUD MISSIONS tab.
 * Shows the live Goal Reasoner decision history — what JARVIS decided,
 * when, confidence level, and why.
 *
 * Add to hud/src/tabs/MissionBoardTab.jsx:
 *   import ReasonerFeed from '../components/ReasonerFeed';
 *   // Then inside your JSX:
 *   <ReasonerFeed backendUrl="http://localhost:8000" />
 */

import { useState, useEffect, useRef } from "react";

// ── Decision color map ────────────────────────────────────────────────────────

const DECISION_COLORS = {
  ACT_SILENT:  { bg: "#0a1a0a", border: "#00ff41", text: "#00ff41", label: "ACTED" },
  ACT_NOTIFY:  { bg: "#0a120a", border: "#39ff14", text: "#39ff14", label: "ACTED + NOTIFIED" },
  ESCALATE:    { bg: "#1a1200", border: "#ffaa00", text: "#ffaa00", label: "ESCALATED" },
  DISCARD:     { bg: "#0d0d0d", border: "#333",    text: "#666",    label: "DISCARDED" },
};

const ACTION_ICONS = {
  send_brief:    "📋",
  log_domain:    "📊",
  send_whatsapp: "💬",
  surface_alert: "🔔",
  fetch_intel:   "🌐",
  suggest_focus: "🎯",
  rest_advisory: "😴",
  null:          "—",
};

// ── Confidence bar ────────────────────────────────────────────────────────────

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color =
    pct >= 85 ? "#00ff41" :
    pct >= 60 ? "#39ff14" :
    pct >= 40 ? "#ffaa00" : "#555";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        width: 80, height: 4,
        background: "#1a1a1a",
        borderRadius: 2,
        overflow: "hidden",
      }}>
        <div style={{
          width: `${pct}%`,
          height: "100%",
          background: color,
          transition: "width 0.3s ease",
        }} />
      </div>
      <span style={{ color, fontSize: 11, fontFamily: "monospace" }}>
        {pct}%
      </span>
    </div>
  );
}

// ── Single cycle card ─────────────────────────────────────────────────────────

function CycleCard({ cycle, index }) {
  const [expanded, setExpanded] = useState(false);
  const colors = DECISION_COLORS[cycle.decision] || DECISION_COLORS.DISCARD;
  const icon   = ACTION_ICONS[cycle.action] || "—";

  const ts = cycle.timestamp
    ? new Date(cycle.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "—";

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background:   colors.bg,
        border:       `1px solid ${colors.border}`,
        borderRadius: 6,
        padding:      "10px 14px",
        marginBottom: 6,
        cursor:       "pointer",
        transition:   "border-color 0.2s",
        opacity:      index > 5 ? 0.7 : 1,
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <span style={{
            color:      colors.text,
            fontSize:   11,
            fontFamily: "monospace",
            fontWeight: 600,
            letterSpacing: 1,
          }}>
            {colors.label}
          </span>
          {cycle.action && (
            <span style={{ color: "#555", fontSize: 10, fontFamily: "monospace" }}>
              [{cycle.action}]
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ConfidenceBar value={cycle.confidence} />
          <span style={{ color: "#444", fontSize: 10, fontFamily: "monospace" }}>{ts}</span>
          <span style={{ color: "#333", fontSize: 10 }}>{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Emotion pill */}
      {cycle.emotion && (
        <div style={{ marginTop: 4 }}>
          <span style={{
            background: "#111",
            border:     "1px solid #222",
            borderRadius: 3,
            padding:    "1px 6px",
            fontSize:   9,
            color:      "#555",
            fontFamily: "monospace",
            letterSpacing: 0.5,
          }}>
            {cycle.emotion.toUpperCase()}
          </span>
        </div>
      )}

      {/* Expanded reasoning */}
      {expanded && cycle.reasoning && (
        <div style={{
          marginTop:  10,
          paddingTop: 10,
          borderTop:  "1px solid #1a1a1a",
          color:      "#888",
          fontSize:   12,
          lineHeight: 1.6,
          fontFamily: "monospace",
        }}>
          <span style={{ color: "#444", fontSize: 10 }}>REASONING: </span>
          {cycle.reasoning}
        </div>
      )}
    </div>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ cycles }) {
  const counts = cycles.reduce((acc, c) => {
    acc[c.decision] = (acc[c.decision] || 0) + 1;
    return acc;
  }, {});

  const total    = cycles.length || 1;
  const actRate  = Math.round(((counts.ACT_SILENT || 0) + (counts.ACT_NOTIFY || 0)) / total * 100);
  const avgConf  = cycles.length
    ? Math.round(cycles.reduce((s, c) => s + (c.confidence || 0), 0) / cycles.length * 100)
    : 0;

  return (
    <div style={{
      display:       "flex",
      gap:           16,
      padding:       "8px 0",
      marginBottom:  12,
      borderBottom:  "1px solid #1a1a1a",
    }}>
      {[
        { label: "ACTED",     value: (counts.ACT_SILENT || 0) + (counts.ACT_NOTIFY || 0), color: "#00ff41" },
        { label: "ESCALATED", value: counts.ESCALATE || 0,  color: "#ffaa00" },
        { label: "DISCARDED", value: counts.DISCARD || 0,   color: "#333" },
        { label: "ACT RATE",  value: `${actRate}%`,         color: "#39ff14" },
        { label: "AVG CONF",  value: `${avgConf}%`,         color: "#39ff14" },
      ].map(({ label, value, color }) => (
        <div key={label} style={{ textAlign: "center" }}>
          <div style={{ color, fontSize: 14, fontFamily: "monospace", fontWeight: 700 }}>
            {value}
          </div>
          <div style={{ color: "#333", fontSize: 9, letterSpacing: 1 }}>{label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReasonerFeed({ backendUrl = "http://localhost:8000" }) {
  const [cycles,     setCycles]     = useState([]);
  const [status,     setStatus]     = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const intervalRef = useRef(null);

  const fetchData = async () => {
    try {
      const [histRes, statusRes] = await Promise.all([
        fetch(`${backendUrl}/reasoner/history?limit=20`),
        fetch(`${backendUrl}/reasoner/status`),
      ]);

      if (histRes.ok) {
        const hist = await histRes.json();
        setCycles(hist.cycles || []);
      }
      if (statusRes.ok) {
        setStatus(await statusRes.json());
      }

      setError(null);
      setLastRefresh(new Date());
    } catch (e) {
      setError("Reasoner offline or backend unreachable.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 30_000); // refresh every 30s
    return () => clearInterval(intervalRef.current);
  }, [backendUrl]);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={{
      background: "#080808",
      border:     "1px solid #111",
      borderRadius: 8,
      padding:    "16px",
      fontFamily: "monospace",
      minWidth:   340,
    }}>
      {/* Title bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: status?.status === "healthy" ? "#00ff41" :
                        status?.status === "degraded" ? "#ffaa00" : "#ff3333",
            boxShadow: `0 0 6px ${status?.status === "healthy" ? "#00ff41" : "#ffaa00"}`,
          }} />
          <span style={{ color: "#888", fontSize: 11, letterSpacing: 2 }}>
            GOAL REASONER
          </span>
        </div>
        <div style={{ color: "#333", fontSize: 9 }}>
          {status?.minutes_ago != null
            ? `last cycle ${status.minutes_ago}min ago`
            : "no cycles yet"}
          {lastRefresh && (
            <span style={{ marginLeft: 8 }}>
              · refreshed {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div style={{
          color: "#ff4444", fontSize: 11, padding: "8px 12px",
          background: "#1a0000", borderRadius: 4, marginBottom: 12,
          border: "1px solid #330000",
        }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ color: "#333", fontSize: 11, textAlign: "center", padding: 24 }}>
          INITIALIZING...
        </div>
      )}

      {/* Stats */}
      {!loading && cycles.length > 0 && <StatsBar cycles={cycles} />}

      {/* Cycle feed */}
      {!loading && cycles.length === 0 && !error && (
        <div style={{ color: "#333", fontSize: 11, textAlign: "center", padding: 24 }}>
          NO CYCLES YET — REASONER IS INITIALIZING
        </div>
      )}

      {!loading && cycles.map((cycle, i) => (
        <CycleCard key={cycle.timestamp || i} cycle={cycle} index={i} />
      ))}

      {/* Total */}
      {status?.total_cycles > 20 && (
        <div style={{ color: "#333", fontSize: 9, textAlign: "center", marginTop: 8 }}>
          showing last 20 of {status.total_cycles} total cycles
        </div>
      )}
    </div>
  );
}
