import { useState, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Metadata {
  full_name: string;
  description: string;
  stars: number;
  forks: number;
  open_issues: number;
  default_branch: string;
  license: string | null;
  topics: string[];
  visibility: string;
  created_at: string;
  pushed_at: string;
  size_kb: number;
  url: string;
}

interface Complexity {
  score: number;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  estimated_dev_time: string;
}

interface ArchitectureGraphNode {
  id: string;
  label: string;
  category: string;
  type: string;
  position: { x: number; y: number };
}

interface ArchitectureGraphEdge {
  id: string;
  source: string;
  target: string;
}

interface ArchitectureGraph {
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
}

interface Insights {
  project_type: string;
  frameworks: string[];
  main_modules: string[];
  architecture_hint: string;
  tech_stack: string[];
  complexity: Complexity;
  architecture_graph?: ArchitectureGraph;
}

interface ReadmeAnalysis {
  purpose: string;
  key_features: string[];
  setup: string;
}

interface Architecture {
  layers: string[];
  structure: string[];
  explanation: string;
}

interface CodeReview {
  quality_score: number;
  security_risks: string[];
  performance_notes: string[];
  best_practices: string[];
}

interface RepoDocumentation {
  project_overview: string;
  tech_stack: string[];
  architecture_summary: string;
  installation_steps: string[];
  usage_guide: string[];
}

interface AnalysisResult {
  owner: string;
  repo: string;
  metadata: Metadata;
  languages: Record<string, number>;
  insights: Insights;
  summary?: string;
  readme_analysis?: ReadmeAnalysis;
  architecture?: Architecture;
  code_review?: CodeReview;
  documentation?: RepoDocumentation;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DIFFICULTY_META: Record<
  Complexity["difficulty"],
  { color: string; glow: string; icon: string; bar: string }
> = {
  Beginner: {
    color: "#00e5a0",
    glow: "rgba(0,229,160,0.25)",
    icon: "◈",
    bar: "#00e5a0",
  },
  Intermediate: {
    color: "#f5a623",
    glow: "rgba(245,166,35,0.25)",
    icon: "◈◈",
    bar: "#f5a623",
  },
  Advanced: {
    color: "#ff4d6d",
    glow: "rgba(255,77,109,0.25)",
    icon: "◈◈◈",
    bar: "#ff4d6d",
  },
};

function langPercents(
  langs: Record<string, number>
): { name: string; pct: number }[] {
  const total = Object.values(langs).reduce((s, v) => s + v, 0);
  if (!total) return [];
  return Object.entries(langs)
    .map(([name, bytes]) => ({ name, pct: Math.round((bytes / total) * 100) }))
    .sort((a, b) => b.pct - a.pct);
}

const LANG_COLORS = [
  "#4cc9f0","#7b2ff7","#f72585","#4361ee","#3a0ca3",
  "#480ca8","#560bad","#7209b7","#b5179e","#f77f00",
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 4,
      padding: "14px 22px",
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 12,
      minWidth: 100,
    }}>
      <span style={{ fontSize: 22, fontWeight: 700, color: accent ?? "#fff", fontFamily: "'DM Mono', monospace" }}>
        {value}
      </span>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        {label}
      </span>
    </div>
  );
}

function Tag({ text, accent }: { text: string; accent?: string }) {
  return (
    <span style={{
      padding: "4px 10px",
      background: accent ? `${accent}18` : "rgba(255,255,255,0.07)",
      border: `1px solid ${accent ? `${accent}44` : "rgba(255,255,255,0.12)"}`,
      borderRadius: 6,
      fontSize: 12,
      color: accent ?? "rgba(255,255,255,0.75)",
      fontFamily: "'DM Mono', monospace",
      whiteSpace: "nowrap" as const,
    }}>
      {text}
    </span>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{
      margin: "0 0 18px",
      fontSize: 13,
      fontWeight: 600,
      letterSpacing: "0.14em",
      textTransform: "uppercase" as const,
      color: "rgba(255,255,255,0.35)",
      display: "flex",
      alignItems: "center",
      gap: 10,
    }}>
      <span style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
      {children}
      <span style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
    </h2>
  );
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16,
      padding: "22px 24px",
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── Complexity Section ────────────────────────────────────────────────────────

function ComplexitySection({ complexity }: { complexity: Complexity }) {
  const meta = DIFFICULTY_META[complexity.difficulty];
  const scorePercent = Math.min((complexity.score / 10) * 100, 100);

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Project Complexity</SectionHeading>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 16,
      }}>

        {/* Score Card */}
        <Card style={{ position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", inset: 0,
            background: `radial-gradient(ellipse at top left, ${meta.glow}, transparent 65%)`,
            pointerEvents: "none",
          }} />
          <p style={{ margin: "0 0 10px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
            Score
          </p>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 14 }}>
            <span style={{ fontSize: 44, fontWeight: 800, color: meta.color, fontFamily: "'DM Mono', monospace", lineHeight: 1 }}>
              {complexity.score}
            </span>
            <span style={{ fontSize: 18, color: "rgba(255,255,255,0.25)", fontFamily: "'DM Mono', monospace" }}>
              / 10
            </span>
          </div>
          {/* Score bar */}
          <div style={{ height: 5, background: "rgba(255,255,255,0.08)", borderRadius: 99, overflow: "hidden" }}>
            <div style={{
              height: "100%",
              width: `${scorePercent}%`,
              background: meta.color,
              borderRadius: 99,
              transition: "width 1s cubic-bezier(.4,0,.2,1)",
              boxShadow: `0 0 10px ${meta.color}`,
            }} />
          </div>
        </Card>

        {/* Difficulty Card */}
        <Card style={{ position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", inset: 0,
            background: `radial-gradient(ellipse at bottom right, ${meta.glow}, transparent 65%)`,
            pointerEvents: "none",
          }} />
          <p style={{ margin: "0 0 10px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
            Difficulty
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: 36, fontWeight: 800, color: meta.color, lineHeight: 1 }}>
              {complexity.difficulty}
            </span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {(["Beginner", "Intermediate", "Advanced"] as Complexity["difficulty"][]).map((level) => {
              const active = DIFFICULTY_META[level].color;
              const isActive = level === complexity.difficulty;
              return (
                <div key={level} style={{
                  flex: 1, height: 5, borderRadius: 99,
                  background: isActive ? active : "rgba(255,255,255,0.08)",
                  boxShadow: isActive ? `0 0 8px ${active}` : "none",
                  transition: "all 0.3s ease",
                }} />
              );
            })}
          </div>
        </Card>

        {/* Dev Time Card */}
        <Card style={{ position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", inset: 0,
            background: `radial-gradient(ellipse at top right, ${meta.glow}, transparent 65%)`,
            pointerEvents: "none",
          }} />
          <p style={{ margin: "0 0 10px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
            Estimated Dev Time
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 32, color: "rgba(255,255,255,0.2)" }}>⏱</span>
            <span style={{ fontSize: 30, fontWeight: 800, color: "#fff", fontFamily: "'DM Mono', monospace", lineHeight: 1 }}>
              {complexity.estimated_dev_time}
            </span>
          </div>
          <p style={{ margin: "10px 0 0", fontSize: 12, color: "rgba(255,255,255,0.35)" }}>
            Estimated from size, language count & modules
          </p>
        </Card>

      </div>
    </section>
  );
}

// ── Insights Section ──────────────────────────────────────────────────────────

function InsightsSection({ insights }: { insights: Insights }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Insights</SectionHeading>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>

        <Card>
          <p style={{ margin: "0 0 8px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>Project Type</p>
          <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#fff" }}>{insights.project_type}</p>
        </Card>

        <Card>
          <p style={{ margin: "0 0 8px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>Architecture</p>
          <p style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#c4b5fd" }}>{insights.architecture_hint}</p>
        </Card>

        <Card style={{ gridColumn: "1 / -1" }}>
          <p style={{ margin: "0 0 12px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>Frameworks & Libraries</p>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {insights.frameworks.length > 0
              ? insights.frameworks.map((f) => <Tag key={f} text={f} accent="#4cc9f0" />)
              : <span style={{ color: "rgba(255,255,255,0.3)", fontSize: 13 }}>None detected</span>
            }
          </div>
        </Card>

        <Card style={{ gridColumn: "1 / -1" }}>
          <p style={{ margin: "0 0 12px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>Main Modules</p>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {insights.main_modules.map((m) => <Tag key={m} text={m} />)}
          </div>
        </Card>

        <Card style={{ gridColumn: "1 / -1" }}>
          <p style={{ margin: "0 0 12px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>Tech Stack</p>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {insights.tech_stack.map((t) => <Tag key={t} text={t} accent="#f72585" />)}
          </div>
        </Card>

      </div>
    </section>
  );
}

// ── Languages Section ─────────────────────────────────────────────────────────

function LanguagesSection({ languages }: { languages: Record<string, number> }) {
  const items = langPercents(languages);
  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Languages</SectionHeading>
      <Card>
        {/* Stacked bar */}
        <div style={{ display: "flex", height: 10, borderRadius: 99, overflow: "hidden", marginBottom: 20, gap: 2 }}>
          {items.map((l, i) => (
            <div key={l.name} style={{
              width: `${l.pct}%`, height: "100%",
              background: LANG_COLORS[i % LANG_COLORS.length],
              transition: "width 0.8s ease",
            }} />
          ))}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 14 }}>
          {items.map((l, i) => (
            <div key={l.name} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: LANG_COLORS[i % LANG_COLORS.length], flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: "rgba(255,255,255,0.75)" }}>{l.name}</span>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.35)", fontFamily: "'DM Mono', monospace" }}>{l.pct}%</span>
            </div>
          ))}
        </div>
      </Card>
    </section>
  );
}

// ── README Analysis Section ──────────────────────────────────────────────────

function ReadmeAnalysisSection({ readme }: { readme: ReadmeAnalysis }) {
  const subLabel: React.CSSProperties = {
    margin: "0 0 8px",
    fontSize: 11,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.4)",
  };

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>README Analysis</SectionHeading>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Purpose */}
        <Card>
          <p style={subLabel}>Purpose</p>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.82)" }}>
            {readme.purpose}
          </p>
        </Card>

        {/* Key Features */}
        {readme.key_features.length > 0 && (
          <Card>
            <p style={subLabel}>Key Features</p>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 9 }}>
              {readme.key_features.map((feature, i) => (
                <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span style={{
                    flexShrink: 0,
                    marginTop: 5,
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "#4cc9f0",
                    boxShadow: "0 0 6px rgba(76,201,240,0.6)",
                  }} />
                  <span style={{ fontSize: 14, lineHeight: 1.6, color: "rgba(255,255,255,0.75)" }}>
                    {feature}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Setup */}
        <Card>
          <p style={subLabel}>Setup</p>
          <pre style={{
            margin: 0,
            fontFamily: "'DM Mono', monospace",
            fontSize: 13,
            lineHeight: 1.75,
            color: "rgba(255,255,255,0.72)",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "rgba(0,0,0,0.25)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10,
            padding: "14px 16px",
          }}>
            {readme.setup}
          </pre>
        </Card>

      </div>
    </section>
  );
}

// ── Architecture Overview Section ─────────────────────────────────────────────

function ArchitectureOverviewSection({ arch }: { arch: Architecture }) {
  const subLabel: React.CSSProperties = {
    margin: "0 0 12px",
    fontSize: 11,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.4)",
  };

  // Accent colours cycle across layer badges to help visually distinguish them
  const LAYER_ACCENTS = ["#4cc9f0", "#7b2ff7", "#f72585", "#f5a623", "#34d399", "#a78bfa"];

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Architecture Overview</SectionHeading>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Layers */}
        {arch.layers.length > 0 && (
          <Card>
            <p style={subLabel}>Layers</p>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
              {arch.layers.map((layer, i) => (
                <li key={layer} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  {/* Coloured left-border accent bar */}
                  <span style={{
                    flexShrink: 0,
                    width: 3,
                    height: 20,
                    borderRadius: 99,
                    background: LAYER_ACCENTS[i % LAYER_ACCENTS.length],
                    boxShadow: `0 0 8px ${LAYER_ACCENTS[i % LAYER_ACCENTS.length]}88`,
                  }} />
                  <span style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: "rgba(255,255,255,0.82)",
                  }}>
                    {layer}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Project Structure */}
        {arch.structure.length > 0 && (
          <Card>
            <p style={subLabel}>Project Structure</p>
            <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
              {arch.structure.map((entry) => {
                // Visually distinguish folders (no extension) from files
                const isFolder = !entry.includes(".");
                return (
                  <span key={entry} style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "5px 11px",
                    background: isFolder ? "rgba(76,201,240,0.07)" : "rgba(255,255,255,0.04)",
                    border: `1px solid ${isFolder ? "rgba(76,201,240,0.2)" : "rgba(255,255,255,0.08)"}`,
                    borderRadius: 7,
                    fontFamily: "'DM Mono', monospace",
                    fontSize: 12,
                    color: isFolder ? "#4cc9f0" : "rgba(255,255,255,0.55)",
                  }}>
                    <span style={{ opacity: 0.6, fontSize: 11 }}>{isFolder ? "📁" : "📄"}</span>
                    {isFolder ? `${entry}/` : entry}
                  </span>
                );
              })}
            </div>
          </Card>
        )}

        {/* Explanation */}
        {arch.explanation && (
          <Card>
            <p style={subLabel}>Explanation</p>
            <p style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.75,
              color: "rgba(255,255,255,0.72)",
            }}>
              {arch.explanation}
            </p>
          </Card>
        )}

      </div>
    </section>
  );
}

// ── Architecture Diagram Section ──────────────────────────────────────────────

// Category → visual style token used for node background / border / glow
const GRAPH_CATEGORY_STYLES: Record<string, { bg: string; border: string; glow: string; icon: string }> = {
  frontend: { bg: "rgba(76,201,240,0.12)",  border: "rgba(76,201,240,0.45)",  glow: "rgba(76,201,240,0.25)",  icon: "◱" },
  api:      { bg: "rgba(123,47,247,0.14)",   border: "rgba(123,47,247,0.50)",  glow: "rgba(123,47,247,0.28)",  icon: "⬡" },
  auth:     { bg: "rgba(247,37,133,0.12)",   border: "rgba(247,37,133,0.45)",  glow: "rgba(247,37,133,0.25)",  icon: "⬤" },
  data:     { bg: "rgba(245,166,35,0.12)",   border: "rgba(245,166,35,0.45)",  glow: "rgba(245,166,35,0.25)",  icon: "◉" },
  queue:    { bg: "rgba(52,211,153,0.12)",   border: "rgba(52,211,153,0.45)",  glow: "rgba(52,211,153,0.25)",  icon: "◈" },
  ml:       { bg: "rgba(0,229,160,0.10)",    border: "rgba(0,229,160,0.40)",   glow: "rgba(0,229,160,0.22)",   icon: "◇" },
  infra:    { bg: "rgba(167,139,250,0.10)",  border: "rgba(167,139,250,0.40)", glow: "rgba(167,139,250,0.22)", icon: "▣" },
};
const GRAPH_DEFAULT_STYLE = { bg: "rgba(255,255,255,0.06)", border: "rgba(255,255,255,0.2)", glow: "rgba(255,255,255,0.1)", icon: "○" };

function ArchitectureDiagramSection({ graph }: { graph: ArchitectureGraph }) {
  // Canvas dimensions derived from node positions
  const NODE_W = 160;
  const NODE_H = 52;
  const PAD    = 48;   // padding around the graph canvas

  if (!graph || !graph.nodes || graph.nodes.length === 0) return null;

  // Compute canvas size from node positions
  const maxX = Math.max(...graph.nodes.map((n) => n.position.x)) + NODE_W + PAD * 2;
  const maxY = Math.max(...graph.nodes.map((n) => n.position.y)) + NODE_H + PAD * 2;
  const canvasW = Math.max(maxX, 480);
  const canvasH = Math.max(maxY, 180);

  // Build a position lookup for edge routing
  const posMap: Record<string, { x: number; y: number }> = {};
  for (const node of graph.nodes) {
    posMap[node.id] = {
      x: node.position.x + PAD,
      y: node.position.y + PAD,
    };
  }

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Architecture Diagram</SectionHeading>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        {/* Legend strip */}
        <div style={{
          display: "flex", flexWrap: "wrap" as const, gap: 12,
          padding: "14px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}>
          {Object.entries(GRAPH_CATEGORY_STYLES).map(([cat, s]) => (
            <span key={cat} style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              fontSize: 11, color: "rgba(255,255,255,0.45)",
              fontFamily: "'DM Mono', monospace",
            }}>
              <span style={{
                display: "inline-block", width: 10, height: 10, borderRadius: 3,
                background: s.bg, border: `1px solid ${s.border}`,
              }} />
              {cat}
            </span>
          ))}
        </div>

        {/* SVG canvas — scrollable horizontally on small screens */}
        <div style={{ overflowX: "auto", overflowY: "hidden" }}>
          <svg
            width={canvasW}
            height={canvasH}
            viewBox={`0 0 ${canvasW} ${canvasH}`}
            style={{ display: "block", background: "transparent" }}
          >
            {/* ── Definitions: arrowhead marker ── */}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L8,3 L0,6 Z" fill="rgba(255,255,255,0.25)" />
              </marker>
              {/* Per-category arrowheads for coloured edges */}
              {Object.entries(GRAPH_CATEGORY_STYLES).map(([cat, s]) => (
                <marker
                  key={cat}
                  id={`arrow-${cat}`}
                  markerWidth="8"
                  markerHeight="6"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L8,3 L0,6 Z" fill={s.border} />
                </marker>
              ))}
            </defs>

            {/* ── Edges (drawn first, under nodes) ── */}
            {graph.edges.map((edge) => {
              const src = posMap[edge.source];
              const tgt = posMap[edge.target];
              if (!src || !tgt) return null;

              // Connect centre-right of source to centre-left of target
              const x1 = src.x + NODE_W;
              const y1 = src.y + NODE_H / 2;
              const x2 = tgt.x;
              const y2 = tgt.y + NODE_H / 2;

              // Bezier control points for a smooth curve
              const cx1 = x1 + (x2 - x1) * 0.45;
              const cy1 = y1;
              const cx2 = x1 + (x2 - x1) * 0.55;
              const cy2 = y2;

              // Use the source node's category colour for the edge
              const srcNode = graph.nodes.find((n) => n.id === edge.source);
              const cat = srcNode?.category ?? "api";
              const style = GRAPH_CATEGORY_STYLES[cat] ?? GRAPH_DEFAULT_STYLE;

              return (
                <path
                  key={edge.id}
                  d={`M${x1},${y1} C${cx1},${cy1} ${cx2},${cy2} ${x2},${y2}`}
                  fill="none"
                  stroke={style.border}
                  strokeWidth="1.5"
                  strokeOpacity="0.6"
                  markerEnd={`url(#arrow-${cat})`}
                />
              );
            })}

            {/* ── Nodes ── */}
            {graph.nodes.map((node) => {
              const { x, y } = posMap[node.id];
              const style = GRAPH_CATEGORY_STYLES[node.category] ?? GRAPH_DEFAULT_STYLE;

              return (
                <g key={node.id}>
                  {/* Glow rect */}
                  <rect
                    x={x - 4}
                    y={y - 4}
                    width={NODE_W + 8}
                    height={NODE_H + 8}
                    rx={14}
                    fill={style.glow}
                    opacity="0.5"
                  />
                  {/* Main node rect */}
                  <rect
                    x={x}
                    y={y}
                    width={NODE_W}
                    height={NODE_H}
                    rx={10}
                    fill={style.bg}
                    stroke={style.border}
                    strokeWidth="1.5"
                  />
                  {/* Category icon */}
                  <text
                    x={x + 14}
                    y={y + NODE_H / 2 + 1}
                    dominantBaseline="middle"
                    textAnchor="middle"
                    fontSize="13"
                    fill={style.border}
                    opacity="0.85"
                  >
                    {style.icon}
                  </text>
                  {/* Category label (top line, small) */}
                  <text
                    x={x + 28}
                    y={y + 16}
                    fontSize="9"
                    fill={style.border}
                    opacity="0.7"
                    fontFamily="DM Mono, monospace"
                    letterSpacing="0.08em"
                  >
                    {node.category.toUpperCase()}
                  </text>
                  {/* Module label (main text) */}
                  <text
                    x={x + 28}
                    y={y + 33}
                    fontSize="12"
                    fontWeight="600"
                    fill="rgba(255,255,255,0.88)"
                    fontFamily="DM Sans, sans-serif"
                  >
                    {node.label.length > 18 ? node.label.slice(0, 17) + "…" : node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Footer note */}
        <div style={{
          padding: "10px 20px",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          fontSize: 11,
          color: "rgba(255,255,255,0.2)",
          fontFamily: "'DM Mono', monospace",
        }}>
          Auto-generated from detected modules · {graph.nodes.length} nodes · {graph.edges.length} edges
        </div>
      </Card>
    </section>
  );
}

// ── Code Review Section ───────────────────────────────────────────────────────

// Score thresholds → colour + glow for the quality score display
function scoreColor(score: number): { color: string; glow: string } {
  if (score >= 8) return { color: "#00e5a0", glow: "rgba(0,229,160,0.2)" };
  if (score >= 5) return { color: "#f5a623", glow: "rgba(245,166,35,0.2)" };
  return { color: "#ff4d6d", glow: "rgba(255,77,109,0.2)" };
}

function CodeReviewSection({ review }: { review: CodeReview }) {
  const subLabel: React.CSSProperties = {
    margin: "0 0 14px",
    fontSize: 11,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.4)",
  };

  const { color, glow } = scoreColor(review.quality_score);
  const scorePercent = (review.quality_score / 10) * 100;

  // Shared bullet-list renderer used for all three string-array sub-sections
  function BulletList({
    items,
    accent,
  }: {
    items: string[];
    accent: string;
  }) {
    if (items.length === 0) {
      return (
        <p style={{ margin: 0, fontSize: 13, color: "rgba(255,255,255,0.3)" }}>
          None detected
        </p>
      );
    }
    return (
      <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((item, i) => (
          <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <span style={{
              flexShrink: 0,
              marginTop: 5,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: accent,
              boxShadow: `0 0 6px ${accent}99`,
            }} />
            <span style={{ fontSize: 14, lineHeight: 1.65, color: "rgba(255,255,255,0.78)" }}>
              {item}
            </span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Code Review</SectionHeading>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Quality Score */}
        <Card style={{ position: "relative", overflow: "hidden" }}>
          {/* Ambient glow behind the card */}
          <div style={{
            position: "absolute", inset: 0,
            background: `radial-gradient(ellipse at top left, ${glow}, transparent 65%)`,
            pointerEvents: "none",
          }} />
          <p style={subLabel}>Quality Score</p>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 14 }}>
            <span style={{
              fontSize: 52,
              fontWeight: 800,
              color,
              fontFamily: "'DM Mono', monospace",
              lineHeight: 1,
            }}>
              {review.quality_score}
            </span>
            <span style={{
              fontSize: 20,
              color: "rgba(255,255,255,0.25)",
              fontFamily: "'DM Mono', monospace",
            }}>
              / 10
            </span>
          </div>
          {/* Score progress bar */}
          <div style={{
            height: 5,
            background: "rgba(255,255,255,0.08)",
            borderRadius: 99,
            overflow: "hidden",
          }}>
            <div style={{
              height: "100%",
              width: `${scorePercent}%`,
              background: color,
              borderRadius: 99,
              transition: "width 1s cubic-bezier(.4,0,.2,1)",
              boxShadow: `0 0 10px ${color}`,
            }} />
          </div>
        </Card>

        {/* Security Risks */}
        <Card>
          <p style={subLabel}>Security Risks</p>
          <BulletList items={review.security_risks} accent="#ff4d6d" />
        </Card>

        {/* Performance Notes */}
        <Card>
          <p style={subLabel}>Performance Notes</p>
          <BulletList items={review.performance_notes} accent="#f5a623" />
        </Card>

        {/* Best Practices */}
        <Card>
          <p style={subLabel}>Best Practices</p>
          <BulletList items={review.best_practices} accent="#4cc9f0" />
        </Card>

      </div>
    </section>
  );
}

// ── AI Documentation Section ──────────────────────────────────────────────────

function AiDocumentationSection({ doc }: { doc: RepoDocumentation }) {
  const subLabel: React.CSSProperties = {
    margin: "0 0 12px",
    fontSize: 11,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.4)",
  };

  // Numbered step list used for installation and usage
  function NumberedList({ items, accent }: { items: string[]; accent: string }) {
    if (items.length === 0) {
      return <p style={{ margin: 0, fontSize: 13, color: "rgba(255,255,255,0.3)" }}>No steps available</p>;
    }
    return (
      <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((step, i) => (
          <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            {/* Step number badge */}
            <span style={{
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: `${accent}18`,
              border: `1px solid ${accent}44`,
              fontSize: 11,
              fontWeight: 700,
              color: accent,
              fontFamily: "'DM Mono', monospace",
              marginTop: 1,
            }}>
              {i + 1}
            </span>
            <span style={{ fontSize: 14, lineHeight: 1.65, color: "rgba(255,255,255,0.78)" }}>
              {step}
            </span>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>AI Documentation</SectionHeading>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Project Overview */}
        <Card style={{ position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", inset: 0,
            background: "radial-gradient(ellipse at top left, rgba(76,201,240,0.07), transparent 65%)",
            pointerEvents: "none",
          }} />
          <p style={subLabel}>Project Overview</p>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.75, color: "rgba(255,255,255,0.82)" }}>
            {doc.project_overview}
          </p>
        </Card>

        {/* Tech Stack */}
        {doc.tech_stack.length > 0 && (
          <Card>
            <p style={subLabel}>Tech Stack</p>
            <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
              {doc.tech_stack.map((tech) => (
                <span key={tech} style={{
                  padding: "5px 12px",
                  background: "rgba(76,201,240,0.08)",
                  border: "1px solid rgba(76,201,240,0.22)",
                  borderRadius: 7,
                  fontSize: 12,
                  fontWeight: 500,
                  color: "#4cc9f0",
                  fontFamily: "'DM Mono', monospace",
                  whiteSpace: "nowrap" as const,
                }}>
                  {tech}
                </span>
              ))}
            </div>
          </Card>
        )}

        {/* Architecture Summary */}
        {doc.architecture_summary && (
          <Card>
            <p style={subLabel}>Architecture Summary</p>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.75, color: "rgba(255,255,255,0.72)" }}>
              {doc.architecture_summary}
            </p>
          </Card>
        )}

        {/* Installation Steps */}
        <Card>
          <p style={subLabel}>Installation Steps</p>
          <NumberedList items={doc.installation_steps} accent="#a78bfa" />
        </Card>

        {/* Usage Guide */}
        <Card>
          <p style={subLabel}>Usage Guide</p>
          <NumberedList items={doc.usage_guide} accent="#34d399" />
        </Card>

      </div>
    </section>
  );
}

// ── Metadata Section ──────────────────────────────────────────────────────────

function MetadataSection({ metadata }: { metadata: Metadata }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <SectionHeading>Repository Stats</SectionHeading>
      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 12 }}>
        <StatPill label="Stars" value={metadata.stars.toLocaleString()} accent="#f5a623" />
        <StatPill label="Forks" value={metadata.forks.toLocaleString()} accent="#4cc9f0" />
        <StatPill label="Open Issues" value={metadata.open_issues.toLocaleString()} accent="#ff4d6d" />
        <StatPill label="Size" value={metadata.size_kb >= 1000 ? `${(metadata.size_kb / 1000).toFixed(1)} MB` : `${metadata.size_kb} KB`} />
        <StatPill label="Branch" value={metadata.default_branch} accent="#a78bfa" />
        {metadata.license && <StatPill label="License" value={metadata.license} accent="#34d399" />}
      </div>
      {metadata.topics.length > 0 && (
        <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
          {metadata.topics.map((t) => <Tag key={t} text={t} />)}
        </div>
      )}
    </section>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  // ── Unified AI Agent state ────────────────────────────────────────────────
  const [agentQuestion, setAgentQuestion]   = useState("");
  const [agentToolUsed, setAgentToolUsed]   = useState<string | null>(null);
  const [agentToolLabel, setAgentToolLabel] = useState<string | null>(null);
  const [agentAnswer, setAgentAnswer]       = useState<string | null>(null);
  const [agentLoading, setAgentLoading]     = useState(false);
  const [agentError, setAgentError]         = useState<string | null>(null);

  // ── Multi-repo memory state ────────────────────────────────────────────────
  const [loadedRepos, setLoadedRepos]           = useState<string[]>([]);
  const [selectedRepos, setSelectedRepos]       = useState<Set<string>>(new Set());
  const [compareAnswer, setCompareAnswer]       = useState<string | null>(null);
  const [compareRepos, setCompareRepos]         = useState<string[]>([]);
  const [compareLoading, setCompareLoading]     = useState(false);
  const [compareError, setCompareError]         = useState<string | null>(null);
  const [compareQuestion, setCompareQuestion]   = useState("");

  // Ref for "Analyze Another Repository" scroll-to behaviour
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleAnalyse() {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(
        `http://127.0.0.1:8000/analyse?url=${encodeURIComponent(url)}`
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data: AnalysisResult = await res.json();
      setResult(data);
      // Refresh the loaded repos list from server memory and auto-select new repo
      fetch("http://127.0.0.1:8000/repos")
        .then((r) => r.json())
        .then((names: string[]) => {
          setLoadedRepos(names);
          // Auto-select any repo not already in selectedRepos
          setSelectedRepos((prev) => {
            const next = new Set(prev);
            names.forEach((n) => next.add(n));
            return next;
          });
        })
        .catch(() => {});
    } catch (e: unknown) {
      // Network errors (ECONNREFUSED, DNS, CORS) surface as TypeError with
      // message "Failed to fetch" — replace with a clearer user-facing message.
      const raw = e instanceof Error ? e.message : "Unknown error";
      const isFetchFailure =
        raw.toLowerCase().includes("failed to fetch") ||
        raw.toLowerCase().includes("networkerror") ||
        raw.toLowerCase().includes("load failed");
      setError(
        isFetchFailure
          ? "⚠ Failed to fetch repository data"
          : raw
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAgent() {
    if (!agentQuestion.trim() || !result) return;
    setAgentLoading(true);
    setAgentError(null);
    setAgentAnswer(null);
    setAgentToolUsed(null);
    setAgentToolLabel(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/agent/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: agentQuestion.trim(), repo_data: result }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setAgentToolUsed(data.tool_used ?? null);
      setAgentToolLabel(data.tool_label ?? null);
      setAgentAnswer(data.answer ?? null);
    } catch (e: unknown) {
      const raw = e instanceof Error ? e.message : "Unknown error";
      const isFetchFailure =
        raw.toLowerCase().includes("failed to fetch") ||
        raw.toLowerCase().includes("networkerror") ||
        raw.toLowerCase().includes("load failed");
      setAgentError(isFetchFailure ? "⚠ Failed to reach the AI agent" : raw);
    } finally {
      setAgentLoading(false);
    }
  }

  async function handleCompare() {
    if (!compareQuestion.trim()) return;
    const selected = Array.from(selectedRepos).filter((r) => loadedRepos.includes(r));
    if (selected.length < 2) return;
    setCompareLoading(true);
    setCompareError(null);
    setCompareAnswer(null);
    setCompareRepos([]);

    try {
      const res = await fetch("http://127.0.0.1:8000/agent/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: compareQuestion.trim(),
          selected_repos: selected,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setCompareAnswer(data.answer ?? null);
      setCompareRepos(data.repos_compared ?? []);
    } catch (e: unknown) {
      const raw = e instanceof Error ? e.message : "Unknown error";
      const isFetchFailure =
        raw.toLowerCase().includes("failed to fetch") ||
        raw.toLowerCase().includes("networkerror") ||
        raw.toLowerCase().includes("load failed");
      setCompareError(isFetchFailure ? "⚠ Failed to reach the comparison agent" : raw);
    } finally {
      setCompareLoading(false);
    }
  }

  function handleToggleRepo(name: string) {
    setSelectedRepos((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
    // Clear stale comparison result whenever selection changes
    setCompareAnswer(null);
    setCompareError(null);
    setCompareRepos([]);
  }

  async function handleRemoveRepo(name: string) {
    try {
      await fetch(`http://127.0.0.1:8000/repos/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
    } catch {
      // Ignore network errors — still clean up local state
    }
    setLoadedRepos((prev) => prev.filter((r) => r !== name));
    setSelectedRepos((prev) => {
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
    setCompareAnswer(null);
    setCompareError(null);
    setCompareRepos([]);
  }

  return (
    <>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: #090b10;
          color: #fff;
          font-family: 'DM Sans', sans-serif;
          min-height: 100vh;
        }

        ::selection { background: #4cc9f055; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 99px; }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .fade-up { animation: fadeUp 0.5s ease both; }
      `}</style>

      {/* Background grid */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        backgroundImage: `
          linear-gradient(rgba(76,201,240,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(76,201,240,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "48px 48px",
      }} />

      {/* Gradient orbs */}
      <div style={{
        position: "fixed", top: -200, left: -200, width: 600, height: 600,
        background: "radial-gradient(circle, rgba(123,47,247,0.12), transparent 65%)",
        pointerEvents: "none", zIndex: 0,
      }} />
      <div style={{
        position: "fixed", bottom: -200, right: -100, width: 500, height: 500,
        background: "radial-gradient(circle, rgba(247,37,133,0.08), transparent 65%)",
        pointerEvents: "none", zIndex: 0,
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 900, margin: "0 auto", padding: "48px 24px 80px" }}>

        {/* Header */}
        <header style={{ marginBottom: 52, textAlign: "center" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 10,
            padding: "5px 14px", borderRadius: 99,
            background: "rgba(76,201,240,0.08)",
            border: "1px solid rgba(76,201,240,0.2)",
            marginBottom: 20,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4cc9f0", boxShadow: "0 0 6px #4cc9f0" }} />
            <span style={{ fontSize: 11, color: "#4cc9f0", letterSpacing: "0.12em", textTransform: "uppercase" }}>
              GitHub Analysis Engine
            </span>
          </div>
          <h1 style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: "clamp(36px, 6vw, 58px)",
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            background: "linear-gradient(135deg, #fff 40%, rgba(255,255,255,0.4))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: 12,
          }}>
            RepoLens<span style={{ color: "#4cc9f0", WebkitTextFillColor: "#4cc9f0" }}> AI</span>
          </h1>
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 16, maxWidth: 420, margin: "0 auto" }}>
            Paste any GitHub URL and get an instant deep-dive into its architecture, stack, and complexity.
          </p>
        </header>

        {/* Search bar */}
        {/* Instruction text */}
        <p style={{
          textAlign: "center", marginBottom: 12,
          fontSize: 13, color: "rgba(255,255,255,0.35)", lineHeight: 1.5,
        }}>
          Analyze multiple repositories to enable comparison.
        </p>
        <div style={{
          display: "flex", gap: 10, marginBottom: 48,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 14, padding: 6,
        }}>
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyse()}
            placeholder="https://github.com/owner/repository"
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: "#fff", fontSize: 15, padding: "10px 14px",
              fontFamily: "'DM Mono', monospace",
            }}
          />
          <button
            onClick={handleAnalyse}
            disabled={loading}
            style={{
              padding: "10px 24px", borderRadius: 10, border: "none",
              background: loading ? "rgba(76,201,240,0.2)" : "linear-gradient(135deg, #4cc9f0, #7b2ff7)",
              color: "#fff", fontWeight: 600, fontSize: 14, cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "'DM Sans', sans-serif", letterSpacing: "0.02em",
              transition: "opacity 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {loading ? "Analysing…" : "Analyse →"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: "14px 18px", borderRadius: 12, marginBottom: 32,
            background: "rgba(255,77,109,0.1)", border: "1px solid rgba(255,77,109,0.3)",
            color: "#ff4d6d", fontSize: 14,
          }}>
            {error.startsWith("⚠") ? error : `⚠ ${error}`}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="fade-up">

            {/* Repo title bar */}
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              flexWrap: "wrap", gap: 12, marginBottom: 36,
              padding: "18px 22px",
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.09)",
              borderRadius: 14,
            }}>
              <div>
                <p style={{ margin: "0 0 3px", fontSize: 11, color: "rgba(255,255,255,0.35)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                  Repository
                </p>
                <h2 style={{ margin: 0, fontFamily: "'Syne', sans-serif", fontSize: 22, fontWeight: 700 }}>
                  {result.metadata.full_name}
                </h2>
                {result.metadata.description && (
                  <p style={{ margin: "5px 0 0", fontSize: 14, color: "rgba(255,255,255,0.5)", maxWidth: 520 }}>
                    {result.metadata.description}
                  </p>
                )}
              </div>
              <a
                href={result.metadata.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: "8px 16px", borderRadius: 8,
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "rgba(255,255,255,0.7)", fontSize: 13,
                  textDecoration: "none", whiteSpace: "nowrap",
                }}
              >
                Open on GitHub ↗
              </a>
            </div>

            {/* AI Summary */}
            {result.summary && (
              <section style={{ marginBottom: 40 }}>
                <SectionHeading>AI Summary</SectionHeading>
                <Card>
                  <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.75)" }}>
                    {result.summary}
                  </p>
                </Card>
              </section>
            )}

            {/* README Analysis — shown immediately after AI Summary */}
            {result.readme_analysis && (
              <ReadmeAnalysisSection readme={result.readme_analysis} />
            )}

            {/* Architecture Overview + Diagram */}
            <>
              {result.architecture && (
                <ArchitectureOverviewSection arch={result.architecture} />
              )}

              {/* Architecture Diagram */}
              {result.insights.architecture_graph &&
                result.insights.architecture_graph.nodes?.length > 0 && (
                  <ArchitectureDiagramSection
                    graph={result.insights.architecture_graph}
                  />
              )}
            </>

            {/* Code Review — shown after Architecture Overview */}
            {result.code_review && (
              <CodeReviewSection review={result.code_review} />
            )}

            {/* AI Documentation — shown after Code Review */}
            {result.documentation && (
              <AiDocumentationSection doc={result.documentation} />
            )}

            {/* Repository Stats */}
            <MetadataSection metadata={result.metadata} />

            {/* Languages */}
            <LanguagesSection languages={result.languages} />

            {/* Insights */}
            <InsightsSection insights={result.insights} />

            {/* ── Project Complexity ── */}
            <ComplexitySection complexity={result.insights.complexity} />


            {/* ── RepoLens AI Agent ── */}
            <section style={{ marginBottom: 40 }}>
              <SectionHeading>RepoLens AI Agent</SectionHeading>

              <Card style={{ position: "relative", overflow: "hidden" }}>
                {/* Amber ambient glow */}
                <div style={{
                  position: "absolute", inset: 0,
                  background: "radial-gradient(ellipse at top left, rgba(245,166,35,0.08), transparent 65%)",
                  pointerEvents: "none",
                }} />

                {/* Description */}
                <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.7)" }}>
                  Intent detection · Automatic tool selection
                </p>
                <p style={{ margin: "0 0 20px", fontSize: 13, color: "rgba(255,255,255,0.38)", lineHeight: 1.6 }}>
                  Ask any question — the agent detects your intent and routes it to the right analysis tool automatically.
                </p>

                {/* Input row */}
                <div style={{
                  display: "flex", gap: 8,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 11, padding: 5,
                  marginBottom: 16,
                }}>
                  <input
                    type="text"
                    value={agentQuestion}
                    onChange={(e) => setAgentQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAgent()}
                    placeholder="Ask anything about this repository…"
                    style={{
                      flex: 1, background: "transparent", border: "none", outline: "none",
                      color: "#fff", fontSize: 14, padding: "9px 12px",
                      fontFamily: "'DM Sans', sans-serif",
                    }}
                  />
                  <button
                    onClick={handleAgent}
                    disabled={agentLoading || !agentQuestion.trim()}
                    style={{
                      padding: "9px 20px", borderRadius: 8, border: "none",
                      background: (agentLoading || !agentQuestion.trim())
                        ? "rgba(245,166,35,0.15)"
                        : "linear-gradient(135deg, #f5a623, #ff6b6b)",
                      color: (agentLoading || !agentQuestion.trim()) ? "rgba(255,255,255,0.4)" : "#fff",
                      fontWeight: 700, fontSize: 13,
                      cursor: (agentLoading || !agentQuestion.trim()) ? "not-allowed" : "pointer",
                      fontFamily: "'DM Sans', sans-serif",
                      whiteSpace: "nowrap",
                      transition: "all 0.2s",
                    }}
                  >
                    {agentLoading ? "Thinking…" : "Ask RepoLens →"}
                  </button>
                </div>

                {/* Suggested prompts */}
                <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 7, marginBottom: 20 }}>
                  {[
                    "How do I run this project?",
                    "Explain the architecture",
                    "Any security risks?",
                    "What frameworks are used?",
                    "What does this project do?",
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => {
                        setAgentQuestion(prompt);
                        setAgentAnswer(null);
                        setAgentToolUsed(null);
                        setAgentToolLabel(null);
                        setAgentError(null);
                      }}
                      style={{
                        padding: "4px 11px",
                        background: "rgba(245,166,35,0.07)",
                        border: "1px solid rgba(245,166,35,0.2)",
                        borderRadius: 99, fontSize: 11,
                        color: "rgba(245,166,35,0.8)",
                        cursor: "pointer",
                        fontFamily: "'DM Mono', monospace",
                        transition: "background 0.15s",
                      }}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                {/* Error */}
                {agentError && (
                  <div style={{
                    padding: "12px 16px", borderRadius: 10, marginBottom: 14,
                    background: "rgba(255,77,109,0.1)", border: "1px solid rgba(255,77,109,0.25)",
                    color: "#ff4d6d", fontSize: 13,
                  }}>
                    {agentError.startsWith("⚠") ? agentError : `⚠ ${agentError}`}
                  </div>
                )}

                {/* Answer */}
                {agentAnswer && (
                  <div style={{
                    borderRadius: 12, overflow: "hidden",
                    border: "1px solid rgba(245,166,35,0.2)",
                  }}>
                    {/* Tool badge header */}
                    <div style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "10px 16px",
                      background: "rgba(245,166,35,0.08)",
                      borderBottom: "1px solid rgba(245,166,35,0.12)",
                    }}>
                      <span style={{ fontSize: 14, opacity: 0.7 }}>⚙</span>
                      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", letterSpacing: "0.09em", textTransform: "uppercase" }}>
                        Tool used
                      </span>
                      <span style={{
                        padding: "2px 10px", borderRadius: 99,
                        background: "linear-gradient(135deg, #f5a623, #ff6b6b)",
                        fontSize: 11, fontWeight: 700, color: "#fff",
                        fontFamily: "'DM Mono', monospace", letterSpacing: "0.04em",
                      }}>
                        {agentToolLabel ?? agentToolUsed}
                      </span>
                    </div>

                    {/* Answer body */}
                    <div style={{ padding: "16px 18px", background: "rgba(245,166,35,0.04)" }}>
                      <p style={{
                        margin: 0, fontSize: 14, lineHeight: 1.8,
                        color: "rgba(255,255,255,0.85)",
                        whiteSpace: "pre-line",
                      }}>
                        {agentAnswer}
                      </p>
                    </div>
                  </div>
                )}

              </Card>
            </section>

          </div>
        )}

        {/* ── Loaded Repositories memory panel ──────────────────────────────── */}
        {loadedRepos.length > 0 && (() => {
          const activeSelected = Array.from(selectedRepos).filter((r) => loadedRepos.includes(r));
          const readyToCompare = activeSelected.length >= 2;
          return (
            <section style={{ marginBottom: 40 }}>

              {/* Heading row: title + selected/total badge */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
                <span style={{
                  fontFamily: "'Syne', sans-serif", fontSize: 13, fontWeight: 700,
                  letterSpacing: "0.12em", textTransform: "uppercase",
                  color: "rgba(255,255,255,0.55)",
                }}>
                  Loaded Repositories
                </span>
                {/* Badge: selected / total */}
                <span style={{
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                  height: 22, borderRadius: 99,
                  background: readyToCompare
                    ? "linear-gradient(135deg, #00e5a0, #4cc9f0)"
                    : "rgba(255,255,255,0.12)",
                  color: readyToCompare ? "#090b10" : "rgba(255,255,255,0.5)",
                  fontSize: 11, fontWeight: 800,
                  fontFamily: "'DM Mono', monospace",
                  padding: "0 8px",
                  gap: 3,
                }}>
                  {activeSelected.length}
                  <span style={{ opacity: 0.55, fontWeight: 500 }}>/ {loadedRepos.length}</span>
                </span>
                <span style={{
                  fontSize: 11, color: "rgba(255,255,255,0.25)",
                  fontFamily: "'DM Mono', monospace",
                }}>
                  selected for comparison
                </span>
              </div>

              <Card style={{ position: "relative", overflow: "hidden" }}>
                {/* Green ambient glow */}
                <div style={{
                  position: "absolute", inset: 0,
                  background: "radial-gradient(ellipse at bottom left, rgba(0,229,160,0.06), transparent 65%)",
                  pointerEvents: "none",
                }} />

                {/* ── Repo chips: click to toggle, ✕ to remove ── */}
                <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8, marginBottom: 20 }}>
                  {loadedRepos.map((name) => {
                    const isSelected = selectedRepos.has(name);
                    return (
                      <div
                        key={name}
                        style={{
                          display: "inline-flex", alignItems: "center",
                          borderRadius: 99,
                          border: isSelected
                            ? "1px solid rgba(0,229,160,0.45)"
                            : "1px solid rgba(255,255,255,0.12)",
                          background: isSelected
                            ? "rgba(0,229,160,0.1)"
                            : "rgba(255,255,255,0.04)",
                          transition: "background 0.15s, border-color 0.15s, opacity 0.15s",
                          opacity: isSelected ? 1 : 0.55,
                          overflow: "hidden",
                        }}
                      >
                        {/* Toggle button — the main chip area */}
                        <button
                          onClick={() => handleToggleRepo(name)}
                          title={isSelected ? "Deselect from comparison" : "Select for comparison"}
                          style={{
                            display: "inline-flex", alignItems: "center", gap: 7,
                            padding: "5px 10px 5px 12px",
                            background: "transparent", border: "none",
                            cursor: "pointer",
                            fontFamily: "'DM Mono', monospace",
                            fontSize: 12, fontWeight: 500,
                            color: isSelected ? "rgba(0,229,160,0.95)" : "rgba(255,255,255,0.45)",
                            transition: "color 0.15s",
                          }}
                        >
                          {/* Checkbox indicator */}
                          <span style={{
                            display: "inline-flex", alignItems: "center", justifyContent: "center",
                            width: 15, height: 15, borderRadius: 4,
                            border: isSelected
                              ? "1.5px solid rgba(0,229,160,0.7)"
                              : "1.5px solid rgba(255,255,255,0.2)",
                            background: isSelected ? "rgba(0,229,160,0.2)" : "transparent",
                            flexShrink: 0,
                            transition: "all 0.15s",
                          }}>
                            {isSelected && (
                              <span style={{ fontSize: 9, color: "#00e5a0", lineHeight: 1 }}>✓</span>
                            )}
                          </span>
                          {name}
                        </button>

                        {/* Remove button — thin separator + ✕ */}
                        <button
                          onClick={() => handleRemoveRepo(name)}
                          title="Remove from memory"
                          style={{
                            display: "inline-flex", alignItems: "center", justifyContent: "center",
                            width: 26, height: "100%",
                            background: "transparent", border: "none",
                            borderLeft: "1px solid rgba(255,255,255,0.08)",
                            cursor: "pointer",
                            color: "rgba(255,255,255,0.25)",
                            fontSize: 12, lineHeight: 1,
                            padding: "0 6px",
                            transition: "color 0.15s, background 0.15s",
                          }}
                          onMouseEnter={(e) => {
                            (e.currentTarget as HTMLButtonElement).style.color = "#ff4d6d";
                            (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,77,109,0.08)";
                          }}
                          onMouseLeave={(e) => {
                            (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.25)";
                            (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}

                  {/* Analyze Another Repository — scrolls to input */}
                  <button
                    onClick={() => {
                      inputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                      setTimeout(() => inputRef.current?.focus(), 400);
                    }}
                    style={{
                      display: "inline-flex", alignItems: "center", gap: 6,
                      padding: "5px 13px",
                      background: "rgba(76,201,240,0.07)",
                      border: "1px dashed rgba(76,201,240,0.3)",
                      borderRadius: 99,
                      fontSize: 12, fontWeight: 500,
                      color: "rgba(76,201,240,0.7)",
                      cursor: "pointer",
                      fontFamily: "'DM Mono', monospace",
                      transition: "background 0.15s, border-color 0.15s",
                    }}
                  >
                    <span style={{ fontSize: 14, lineHeight: 1 }}>+</span>
                    Analyze Another Repository
                  </button>
                </div>

                {/* Hint text under chips */}
                <p style={{
                  margin: "0 0 0",
                  fontSize: 11,
                  color: "rgba(255,255,255,0.22)",
                  fontFamily: "'DM Mono', monospace",
                  marginBottom: 20,
                }}>
                  Click a repository to toggle selection · ✕ to remove from memory
                </p>

                {/* Divider + comparison zone */}
                <div style={{
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                  paddingTop: 20,
                }}>

                  {/* Context-aware status text */}
                  <p style={{
                    margin: "0 0 16px",
                    fontSize: 13,
                    color: readyToCompare ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.28)",
                    lineHeight: 1.6,
                  }}>
                    {!readyToCompare
                      ? `Select at least two repositories to enable comparison. (${activeSelected.length} selected)`
                      : `Ask RepoLens to compare ${activeSelected.length === loadedRepos.length ? "these" : `${activeSelected.length} selected`} repositories.`}
                  </p>

                  {/* Compare UI — only rendered when 2+ repos selected */}
                  {readyToCompare && (
                    <>
                      {/* Selected repos preview row */}
                      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6, marginBottom: 14 }}>
                        {activeSelected.map((r) => (
                          <span key={r} style={{
                            padding: "2px 9px", borderRadius: 99,
                            background: "rgba(0,229,160,0.1)",
                            border: "1px solid rgba(0,229,160,0.25)",
                            fontSize: 11, color: "rgba(0,229,160,0.85)",
                            fontFamily: "'DM Mono', monospace",
                          }}>
                            {r}
                          </span>
                        ))}
                      </div>

                      {/* Compare input row */}
                      <div style={{
                        display: "flex", gap: 8,
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 11, padding: 5,
                        marginBottom: 14,
                      }}>
                        <input
                          type="text"
                          value={compareQuestion}
                          onChange={(e) => setCompareQuestion(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleCompare()}
                          placeholder="Compare these repos, which has better architecture?"
                          style={{
                            flex: 1, background: "transparent", border: "none", outline: "none",
                            color: "#fff", fontSize: 14, padding: "9px 12px",
                            fontFamily: "'DM Sans', sans-serif",
                          }}
                        />
                        <button
                          onClick={handleCompare}
                          disabled={compareLoading || !compareQuestion.trim()}
                          style={{
                            padding: "9px 20px", borderRadius: 8, border: "none",
                            background: (compareLoading || !compareQuestion.trim())
                              ? "rgba(0,229,160,0.12)"
                              : "linear-gradient(135deg, #00e5a0, #4cc9f0)",
                            color: (compareLoading || !compareQuestion.trim())
                              ? "rgba(255,255,255,0.35)" : "#090b10",
                            fontWeight: 700, fontSize: 13,
                            cursor: (compareLoading || !compareQuestion.trim()) ? "not-allowed" : "pointer",
                            fontFamily: "'DM Sans', sans-serif",
                            whiteSpace: "nowrap",
                            transition: "all 0.2s",
                          }}
                        >
                          {compareLoading ? "Comparing…" : `Compare ${activeSelected.length} repos →`}
                        </button>
                      </div>

                      {/* Suggested compare prompts */}
                      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 7, marginBottom: 16 }}>
                        {[
                          "Compare these repos",
                          "Which has better architecture?",
                          "Which is most secure?",
                          "Compare tech stacks",
                          "Which is easiest to maintain?",
                        ].map((prompt) => (
                          <button
                            key={prompt}
                            onClick={() => { setCompareQuestion(prompt); setCompareAnswer(null); setCompareError(null); }}
                            style={{
                              padding: "4px 11px",
                              background: "rgba(0,229,160,0.06)",
                              border: "1px solid rgba(0,229,160,0.18)",
                              borderRadius: 99, fontSize: 11,
                              color: "rgba(0,229,160,0.75)",
                              cursor: "pointer",
                              fontFamily: "'DM Mono', monospace",
                            }}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  {/* Compare error */}
                  {compareError && (
                    <div style={{
                      padding: "12px 16px", borderRadius: 10, marginBottom: 14,
                      background: "rgba(255,77,109,0.1)", border: "1px solid rgba(255,77,109,0.25)",
                      color: "#ff4d6d", fontSize: 13,
                    }}>
                      {compareError.startsWith("⚠") ? compareError : `⚠ ${compareError}`}
                    </div>
                  )}

                  {/* Compare answer */}
                  {compareAnswer && (
                    <div style={{
                      borderRadius: 12, overflow: "hidden",
                      border: "1px solid rgba(0,229,160,0.2)",
                      marginTop: 4,
                    }}>
                      <div style={{
                        display: "flex", alignItems: "center",
                        padding: "10px 16px",
                        background: "rgba(0,229,160,0.08)",
                        borderBottom: "1px solid rgba(0,229,160,0.12)",
                        flexWrap: "wrap" as const, gap: 8,
                      }}>
                        <span style={{ fontSize: 14, opacity: 0.7 }}>⚖</span>
                        <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", letterSpacing: "0.09em", textTransform: "uppercase" }}>
                          Comparison
                        </span>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" as const }}>
                          {compareRepos.map((r) => (
                            <span key={r} style={{
                              padding: "2px 8px", borderRadius: 99,
                              background: "rgba(0,229,160,0.15)",
                              fontSize: 10, color: "rgba(0,229,160,0.9)",
                              fontFamily: "'DM Mono', monospace",
                              border: "1px solid rgba(0,229,160,0.2)",
                            }}>
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div style={{ padding: "16px 18px", background: "rgba(0,229,160,0.03)" }}>
                        <p style={{
                          margin: 0, fontSize: 13, lineHeight: 1.85,
                          color: "rgba(255,255,255,0.82)",
                          whiteSpace: "pre-line",
                          fontFamily: "'DM Mono', monospace",
                        }}>
                          {compareAnswer}
                        </p>
                      </div>
                    </div>
                  )}

                </div>
              </Card>
            </section>
          );
        })()}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div style={{ textAlign: "center", paddingTop: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.15 }}>⬡</div>
            <p style={{ color: "rgba(255,255,255,0.2)", fontSize: 14 }}>
              Enter a GitHub repository URL above to get started
            </p>
          </div>
        )}

      </div>
    </>
  );
}