"use client";

import { useState, useRef, useCallback } from "react";
import type { DiagnosticResult, PerModelResult, SseEvent, Verification } from "@/lib/types";

// ── Constants ──────────────────────────────────────────────────────────────

// Empty string → same-origin (production monolith on Fly.io).
// Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local for local dev.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

const COMPANY_META: Record<string, { company: string; badge: string; logo: string }> = {
  "Llama 3.3 70B":        { company: "Meta",    badge: "badge-meta",    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/200px-Meta_Platforms_Inc._logo.svg.png" },
  "GPT-OSS 120B":         { company: "OpenAI",  badge: "badge-openai",  logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/OpenAI_Logo.svg/200px-OpenAI_Logo.svg.png" },
  "Llama 4 Scout 17B":    { company: "Meta",    badge: "badge-meta",    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/200px-Meta_Platforms_Inc._logo.svg.png" },
  "Llama 3.1 8B Instant": { company: "Meta",    badge: "badge-meta",    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/200px-Meta_Platforms_Inc._logo.svg.png" },
  "GPT-OSS 20B":          { company: "OpenAI",  badge: "badge-openai",  logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/OpenAI_Logo.svg/200px-OpenAI_Logo.svg.png" },
  "Qwen3 32B":            { company: "Alibaba", badge: "badge-alibaba", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Alibaba_Group_Logo.svg/200px-Alibaba_Group_Logo.svg.png" },
};

// ── Colour helpers ─────────────────────────────────────────────────────────

function gradeClass(g: string): string {
  if (g === "A+" || g === "A") return "grade-a";
  if (g === "B") return "grade-b";
  if (g === "C") return "grade-c";
  if (g === "D") return "grade-d";
  return "grade-f";
}

function mentionColor(rate: number): string {
  if (rate <= 0.5)  return "#dc2626";  // red
  if (rate <= 0.75) return "#f59e0b";  // orange
  return "#0d9b6c";                    // green
}

function positionColor(pos: number | null): string {
  if (pos === null) return "#dc2626";
  if (pos <= 3) return "#0d9b6c";
  if (pos <= 6) return "#f59e0b";
  return "#dc2626";
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl p-4 border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="text-xs uppercase tracking-widest" style={{ color: "var(--muted)" }}>{label}</div>
      <div className="text-2xl font-semibold mt-1" style={{ color: color ?? "var(--text)" }}>{value}</div>
    </div>
  );
}

function CompanyLogo({ label }: { label: string }) {
  const meta = COMPANY_META[label];
  if (!meta) return null;
  return (
    <img
      src={meta.logo}
      alt={meta.company}
      title={meta.company}
      className="company-logo h-4 max-w-[60px] object-contain align-middle"
      onError={(e) => {
        // Fallback to badge if logo fails
        const img = e.currentTarget;
        img.style.display = "none";
        const span = document.createElement("span");
        span.className = `rounded px-1.5 py-0.5 text-xs font-semibold ${meta.badge}`;
        span.textContent = meta.company;
        img.parentNode?.insertBefore(span, img);
      }}
    />
  );
}

function ModelTable({ rows }: { rows: PerModelResult[] }) {
  const thStyle: React.CSSProperties = {
    padding: "8px 12px",
    textAlign: "left",
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "var(--muted)",
    borderBottom: "2px solid var(--border)",
    background: "var(--surface)",
    whiteSpace: "nowrap",
  };
  const tdStyle: React.CSSProperties = {
    padding: "10px 12px",
    verticalAlign: "middle",
    borderBottom: "1px solid var(--border)",
    fontSize: "14px",
  };

  return (
    <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={thStyle}>Model</th>
            <th style={{ ...thStyle, textAlign: "center" }}>Mentioned</th>
            <th style={{ ...thStyle, textAlign: "center" }}>Position</th>
            <th style={thStyle}>Sentiment</th>
            <th style={thStyle}>Top Competitors</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.model_label} className="hover:brightness-95 transition-all">
              <td style={tdStyle}>
                <div className="flex items-center gap-2">
                  <CompanyLogo label={m.model_label} />
                  <span className="font-medium" style={{ color: "var(--text)" }}>{m.model_label}</span>
                </div>
                {m.error && (
                  <div className="text-xs mt-0.5" style={{ color: "#f87171" }}>{m.error}</div>
                )}
              </td>
              <td style={{ ...tdStyle, textAlign: "center" }}>
                {m.mentioned ? "✅" : "❌"}
              </td>
              <td style={{ ...tdStyle, textAlign: "center", color: "var(--text)" }}>
                {m.position ?? "–"}
              </td>
              <td style={{ ...tdStyle, color: "var(--text)" }}>
                {m.sentiment}
              </td>
              <td style={{ ...tdStyle, color: "var(--muted)", fontSize: "13px" }}>
                {m.competitors.slice(0, 3).join(", ") || "–"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CitationList({ verifications }: { verifications: Verification[] }) {
  // Deduplicate by lowercased brand name
  const seen = new Set<string>();
  const deduped = verifications.filter((v) => {
    const key = v.brand.toLowerCase().trim();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  if (deduped.length === 0) {
    return <p style={{ color: "var(--muted)" }}>No brands extracted to verify (or verification was skipped).</p>;
  }

  return (
    <ul className="space-y-1.5">
      {deduped.map((v) => (
        <li key={v.brand} className="flex items-center gap-2 text-sm" style={{ color: "var(--text)" }}>
          <span>{v.found ? "✅" : "❌"}</span>
          <span className="font-semibold">{v.brand}</span>
          {v.top_hit_url && (
            <>
              <span style={{ color: "var(--muted)" }}>—</span>
              <a
                href={v.top_hit_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:opacity-80 truncate max-w-xs"
                style={{ color: "#3b82f6" }}
              >
                {v.top_hit_title ?? v.top_hit_url}
              </a>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

function DeepAnalysis({ markdown }: { markdown: string }) {
  // Minimal markdown-to-HTML (headings, bullets, bold, code)
  const lines = markdown.split("\n");
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    if (line.startsWith("### ")) {
      elements.push(<h3 key={key++}>{line.slice(4)}</h3>);
    } else if (line.startsWith("## ")) {
      elements.push(<h3 key={key++} style={{ fontWeight: 700, fontSize: "1.05rem", marginTop: "1rem" }}>{line.slice(3)}</h3>);
    } else if (line.startsWith("# ")) {
      elements.push(<h3 key={key++} style={{ fontWeight: 700, fontSize: "1.1rem", marginTop: "1rem" }}>{line.slice(2)}</h3>);
    } else if (line.match(/^\s*[-*•]\s/)) {
      elements.push(<li key={key++}>{renderInline(line.replace(/^\s*[-*•]\s/, ""))}</li>);
    } else if (line.trim()) {
      elements.push(<p key={key++}>{renderInline(line)}</p>);
    }
  }

  return <div className="prose-aeo text-sm" style={{ color: "var(--text)" }}>{elements}</div>;
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--text)" }}>
      {children}
    </h2>
  );
}

function Divider() {
  return <hr className="my-6" style={{ borderColor: "var(--border)" }} />;
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function Home() {
  const [dark, setDark] = useState(false);
  const [query, setQuery] = useState("best magnesium supplement for seniors");
  const [target, setTarget] = useState("Nature Made");
  const [verify, setVerify] = useState(true);
  const [deep, setDeep] = useState(false);

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rawExpanded, setRawExpanded] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const runDiagnostic = useCallback(async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    setStatus("Starting…");
    setRawExpanded(false);

    abortRef.current = new AbortController();

    try {
      const resp = await fetch(`${API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, target, verify_citations: verify, deep_analysis: deep }),
        signal: abortRef.current.signal,
      });

      if (!resp.ok) {
        throw new Error(`Server error ${resp.status}`);
      }

      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: SseEvent = JSON.parse(line.slice(6));
            if (event.type === "status") setStatus(event.message);
            else if (event.type === "result") setResult(event.data);
            else if (event.type === "error") setError(event.message);
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setError(err.message);
      }
    } finally {
      setLoading(false);
      setStatus("");
    }
  }, [query, target, verify, deep]);

  // ── Render ───────────────────────────────────────────────────────────────

  const inputCls =
    "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 transition";
  const inputStyle: React.CSSProperties = {
    background: "var(--bg)",
    borderColor: "var(--border)",
    color: "var(--text)",
  };

  return (
    <div data-theme={dark ? "dark" : "light"} className="min-h-screen flex flex-col">
      {/* Header */}
      <header
        className="sticky top-0 z-50 border-b backdrop-blur-sm"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between px-6 h-14 max-w-screen-2xl mx-auto">
          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>
            🔍 AEO Diagnostic
          </span>
          <button
            onClick={() => setDark((d) => !d)}
            className="rounded-full w-9 h-9 flex items-center justify-center border transition hover:opacity-80"
            style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--text)" }}
            title="Toggle night mode"
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </div>
      </header>

      <div className="flex flex-1 max-w-screen-2xl mx-auto w-full">
        {/* Sidebar */}
        <aside
          className="w-72 shrink-0 border-r sticky top-14 self-start h-[calc(100vh-56px)] overflow-y-auto p-5 flex flex-col gap-4"
          style={{ borderColor: "var(--border)" }}
        >
          <div>
            <p className="text-xs mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
              How does your brand rank when shoppers ask AI? Query a panel of{" "}
              <strong>6 LLMs</strong> and get an actionable score.
            </p>

            <label className="block mb-1 text-xs font-medium" style={{ color: "var(--muted)" }}>
              Shopper query
            </label>
            <textarea
              className={inputCls + " resize-none"}
              style={inputStyle}
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. best magnesium supplement for seniors"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-medium" style={{ color: "var(--muted)" }}>
              Your brand
            </label>
            <input
              className={inputCls}
              style={inputStyle}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="e.g. Nature Made"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--text)" }}>
              <input
                type="checkbox"
                checked={verify}
                onChange={(e) => setVerify(e.target.checked)}
                className="accent-blue-500"
              />
              Verify citations on the web
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--text)" }}>
              <input
                type="checkbox"
                checked={deep}
                onChange={(e) => setDeep(e.target.checked)}
                className="accent-blue-500"
              />
              Deep agent analysis
            </label>
          </div>

          <button
            onClick={runDiagnostic}
            disabled={loading || !query.trim() || !target.trim()}
            className="w-full rounded-lg py-2.5 font-semibold text-sm transition disabled:opacity-50"
            style={{ background: "#3b82f6", color: "#fff" }}
          >
            {loading ? "Running…" : "Run diagnostic"}
          </button>

          {loading && (
            <p className="text-xs animate-pulse" style={{ color: "var(--muted)" }}>
              {status}
            </p>
          )}

          <hr style={{ borderColor: "var(--border)" }} />

          <div className="text-xs leading-relaxed space-y-0.5" style={{ color: "var(--muted)" }}>
            <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>LLM Panel (Groq)</p>
            <p>• Llama 3.3 70B <em>Meta</em></p>
            <p>• Llama 4 Scout 17B <em>Meta</em></p>
            <p>• Llama 3.1 8B Instant <em>Meta</em></p>
            <p>• GPT-OSS 120B <em>OpenAI</em></p>
            <p>• GPT-OSS 20B <em>OpenAI</em></p>
            <p>• Qwen3 32B <em>Alibaba</em></p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 min-w-0">
          {error && (
            <div className="rounded-xl border border-red-300 bg-red-50 p-4 mb-6 text-sm text-red-700">
              ⚠️ {error}
            </div>
          )}

          {!result && !loading && (
            <div
              className="h-full min-h-64 flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              <span className="text-4xl">🔍</span>
              <p className="text-sm">Fill in the form and click <strong>Run diagnostic</strong> to start.</p>
            </div>
          )}

          {loading && !result && (
            <div
              className="h-64 flex flex-col items-center justify-center gap-3 rounded-2xl border"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm" style={{ color: "var(--muted)" }}>{status}</p>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Grade hero */}
              <div className="flex items-center gap-6">
                <div
                  className="rounded-2xl border p-6 text-center min-w-[100px]"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  <div className={`text-6xl font-bold leading-none ${gradeClass(result.grade)}`}>
                    {result.grade}
                  </div>
                  <div className="text-sm mt-1" style={{ color: "var(--muted)" }}>
                    {result.overall.toFixed(1)} / 100
                  </div>
                </div>
                <div>
                  <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>{result.target}</h1>
                  <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
                    Query: <em>{result.query}</em>
                  </p>
                </div>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard
                  label="Mention rate"
                  value={`${(result.mention_rate * 100).toFixed(0)}%`}
                  color={mentionColor(result.mention_rate)}
                />
                <StatCard
                  label="Avg position"
                  value={result.avg_position !== null ? result.avg_position.toFixed(1) : "–"}
                  color={positionColor(result.avg_position)}
                />
                <StatCard label="Sentiment" value={result.sentiment_score.toFixed(0)} />
                <StatCard label="Citation grounding" value={`${result.citation_score.toFixed(0)}%`} />
              </div>

              <Divider />

              {/* Per-model table */}
              <section>
                <SectionHeader>How each model answered</SectionHeader>
                <ModelTable rows={result.per_model} />
              </section>

              <Divider />

              {/* Citations */}
              <section>
                <SectionHeader>Citation verification</SectionHeader>
                <CitationList verifications={result.verifications} />
              </section>

              {/* Deep analysis */}
              {result.deep_analysis && (
                <>
                  <Divider />
                  <section>
                    <SectionHeader>Deep Agent Analysis</SectionHeader>
                    <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                      Includes temporal analysis — knowledge cutoff dates of each model are compared
                      so divergence between newer and older models reveals whether recent strategy
                      changes are working.
                    </p>
                    <div
                      className="rounded-xl border p-5"
                      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                    >
                      <DeepAnalysis markdown={result.deep_analysis} />
                    </div>
                  </section>
                </>
              )}

              <Divider />

              {/* Raw responses expander */}
              <section>
                <button
                  onClick={() => setRawExpanded((x) => !x)}
                  className="flex items-center gap-2 text-sm font-medium hover:opacity-80 transition"
                  style={{ color: "var(--text)" }}
                >
                  <span>{rawExpanded ? "▲" : "▼"}</span>
                  Raw model responses
                </button>
                {rawExpanded && (
                  <div className="mt-3 space-y-4">
                    {result.raw_responses.map((r) => (
                      <div
                        key={r.model_label}
                        className="rounded-xl border p-4"
                        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <CompanyLogo label={r.model_label} />
                          <span className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                            {r.model_label}
                          </span>
                          <span className="text-xs" style={{ color: "var(--muted)" }}>
                            {r.latency_ms} ms
                          </span>
                        </div>
                        {r.error ? (
                          <p className="text-sm" style={{ color: "#f87171" }}>{r.error}</p>
                        ) : (
                          <pre
                            className="text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed"
                            style={{ color: "var(--muted)" }}
                          >
                            {r.text}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
