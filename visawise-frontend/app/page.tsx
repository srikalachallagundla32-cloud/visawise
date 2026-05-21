"use client";
console.log("VISAWISE LOADED");
import { useState, useEffect, useCallback } from "react";
import { Search, Shield, TrendingUp, AlertTriangle, CheckCircle, XCircle, Building2, MapPin, Calendar, FileText } from "lucide-react";

const API = "http://127.0.0.1:8000";

type RiskLevel = "very_safe" | "safe" | "moderate" | "risky";

interface Company {
  employer: string;
  sponsor_score: number;
  total_petitions: number;
  total_approvals: number;
  total_denials: number;
  approval_rate: number;
  years_active: number;
  latest_year: number;
  state: string;
  city: string;
  risk_level: RiskLevel;
  yearly_history?: YearlyData[];
}

interface YearlyData {
  year: number;
  approvals: number;
  denials: number;
  total: number;
  approval_rate: number;
}

interface Stats {
  total_companies: number;
  total_petitions: number;
  avg_approval_rate: number;
  years_covered: number[];
  risk_breakdown: Record<string, number>;
}

const RISK_CONFIG: Record<RiskLevel, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  very_safe: { label: "Very safe", color: "#0F6E56", bg: "#E1F5EE", icon: <CheckCircle size={14} /> },
  safe: { label: "Safe", color: "#185FA5", bg: "#E6F1FB", icon: <Shield size={14} /> },
  moderate: { label: "Moderate", color: "#854F0B", bg: "#FAEEDA", icon: <AlertTriangle size={14} /> },
  risky: { label: "Risky", color: "#A32D2D", bg: "#FCEBEB", icon: <XCircle size={14} /> },
};

function ScoreRing({ score }: { score: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 90 ? "#1D9E75" : score >= 75 ? "#378ADD" : score >= 50 ? "#BA7517" : "#E24B4A";

  return (
    <svg width="72" height="72" viewBox="0 0 72 72">
      <circle cx="36" cy="36" r={r} fill="none" stroke="#f0f0f0" strokeWidth="6" />
      <circle
        cx="36" cy="36" r={r} fill="none"
        stroke={color} strokeWidth="6"
        strokeDasharray={`${fill} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
      <text x="36" y="36" textAnchor="middle" dominantBaseline="central" fontSize="14" fontWeight="600" fill={color}>
        {score}
      </text>
    </svg>
  );
}

function MiniChart({ history }: { history: YearlyData[] }) {
  if (!history || history.length === 0) return null;
  const max = Math.max(...history.map((h) => h.total));
  const w = 200, h = 48, pad = 4;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      {history.map((d, i) => {
        const x = pad + (i / (history.length - 1)) * (w - pad * 2);
        const barH = max > 0 ? ((d.approvals / max) * (h - pad * 2)) : 0;
        const denyH = max > 0 ? ((d.denials / max) * (h - pad * 2)) : 0;
        return (
          <g key={d.year}>
            <rect x={x - 6} y={h - pad - barH} width={8} height={barH} fill="#1D9E75" rx="2" opacity="0.8" />
            <rect x={x - 6} y={h - pad - barH - denyH} width={8} height={denyH} fill="#E24B4A" rx="2" opacity="0.8" />
          </g>
        );
      })}
    </svg>
  );
}

function CompanyCard({ company, onClick }: { company: Company; onClick: () => void }) {
  const risk = RISK_CONFIG[company.risk_level];
  return (
    <div
      onClick={onClick}
      style={{
        background: "white",
        border: "0.5px solid #e5e5e5",
        borderRadius: 12,
        padding: "1rem 1.25rem",
        cursor: "pointer",
        transition: "border-color 0.15s",
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#aaa")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e5e5e5")}
    >
      <ScoreRing score={company.sponsor_score} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: "#1a1a1a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {company.employer}
          </span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 99, background: risk.bg, color: risk.color, display: "flex", alignItems: "center", gap: 3, whiteSpace: "nowrap", fontWeight: 500 }}>
            {risk.icon} {risk.label}
          </span>
        </div>
        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#888" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
            <MapPin size={11} /> {company.city}, {company.state}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
            <FileText size={11} /> {company.total_petitions.toLocaleString()} petitions
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
            <TrendingUp size={11} /> {company.approval_rate}% approval
          </span>
        </div>
      </div>
    </div>
  );
}

function CompanyDrawer({ company, onClose }: { company: Company; onClose: () => void }) {
  const risk = RISK_CONFIG[company.risk_level];
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end" }}>
      <div onClick={onClose} style={{ flex: 1, background: "rgba(0,0,0,0.3)" }} />
      <div style={{ width: 420, background: "white", height: "100%", overflowY: "auto", padding: "2rem 1.5rem", boxShadow: "-4px 0 24px rgba(0,0,0,0.08)" }}>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "#888", marginBottom: 16 }}>✕</button>

        <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 24 }}>
          <ScoreRing score={company.sponsor_score} />
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 500, margin: "0 0 6px" }}>{company.employer}</h2>
            <span style={{ fontSize: 12, padding: "3px 10px", borderRadius: 99, background: risk.bg, color: risk.color, display: "inline-flex", alignItems: "center", gap: 4, fontWeight: 500 }}>
              {risk.icon} {risk.label}
            </span>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 24 }}>
          {[
            { label: "Total petitions", value: company.total_petitions.toLocaleString() },
            { label: "Approval rate", value: `${company.approval_rate}%` },
            { label: "Years active", value: company.years_active },
            { label: "Latest filing", value: company.latest_year },
            { label: "Approvals", value: company.total_approvals.toLocaleString() },
            { label: "Denials", value: company.total_denials.toLocaleString() },
          ].map((s) => (
            <div key={s.label} style={{ background: "#f8f8f8", borderRadius: 8, padding: "0.75rem 1rem" }}>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 2 }}>{s.label}</div>
              <div style={{ fontSize: 20, fontWeight: 500, color: "#1a1a1a" }}>{s.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 6, marginBottom: 24, fontSize: 12, color: "#666" }}>
          <Building2 size={13} />
          <span>{company.city}, {company.state}</span>
          <Calendar size={13} style={{ marginLeft: 8 }} />
          <span>Last filed {company.latest_year}</span>
        </div>

        {company.yearly_history && company.yearly_history.length > 0 && (
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12, color: "#1a1a1a" }}>Filing history</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {company.yearly_history.map((y) => (
                <div key={`${y.year}-${y.total}`} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 12, color: "#888", minWidth: 36 }}>{y.year}</span>
                  <div style={{ flex: 1, height: 6, background: "#f0f0f0", borderRadius: 99, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${y.approval_rate}%`, background: "#1D9E75", borderRadius: 99, transition: "width 0.4s ease" }} />
                  </div>
                  <span style={{ fontSize: 12, color: "#1D9E75", minWidth: 36, textAlign: "right" }}>{y.approval_rate}%</span>
                  <span style={{ fontSize: 11, color: "#aaa", minWidth: 60 }}>{y.total.toLocaleString()} filed</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selected, setSelected] = useState<Company | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"top" | "search">("top");

  useEffect(() => {
    fetch(`${API}/stats`).then((r) => r.json()).then(setStats).catch(() => { });
    fetchTop();
  }, []);

  const fetchTop = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/companies/top?limit=20`);
      const d = await r.json();
      setCompanies(d.companies || []);
      setMode("top");
    } finally {
      setLoading(false);
    }
  };

  const search = useCallback(async (q: string) => {
    if (q.length < 2) { fetchTop(); return; }
    setLoading(true);
    try {
      const r = await fetch(`${API}/companies/search?q=${encodeURIComponent(q)}&limit=20`);
      const d = await r.json();
      setCompanies(d.companies || []);
      setMode("search");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(query), 300);
    return () => clearTimeout(t);
  }, [query, search]);

  const openCompany = async (c: Company) => {
    setSelected(c);
    try {
      const r = await fetch(`${API}/companies/${encodeURIComponent(c.employer.toUpperCase())}`);
      const d = await r.json();
      setSelected(d);
    } catch { }
  };

  return (
    <main style={{ minHeight: "100vh", background: "#fafafa", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "2rem 1rem" }}>

        <div style={{ marginBottom: "2rem" }}>
          <h1 style={{ fontSize: 28, fontWeight: 600, color: "#1a1a1a", margin: "0 0 4px" }}>Visawise</h1>
          <p style={{ fontSize: 14, color: "#888", margin: 0 }}>H1B sponsor intelligence — find companies that actually sponsor</p>
        </div>

        {stats && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 24 }}>
            {[
              { label: "Companies tracked", value: stats.total_companies.toLocaleString() },
              { label: "Total petitions", value: stats.total_petitions.toLocaleString() },
              { label: "Avg approval rate", value: `${stats.avg_approval_rate}%` },
            ].map((s) => (
              <div key={s.label} style={{ background: "white", border: "0.5px solid #e5e5e5", borderRadius: 10, padding: "0.875rem 1rem" }}>
                <div style={{ fontSize: 11, color: "#aaa", marginBottom: 2 }}>{s.label}</div>
                <div style={{ fontSize: 20, fontWeight: 500, color: "#1a1a1a" }}>{s.value}</div>
              </div>
            ))}
          </div>
        )}

        <div style={{ position: "relative", marginBottom: 20 }}>
          <Search size={16} style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "#aaa" }} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search any company — Google, Amazon, Rivian..."
            style={{ width: "100%", padding: "12px 14px 12px 40px", fontSize: 14, border: "0.5px solid #ddd", borderRadius: 10, outline: "none", background: "white", boxSizing: "border-box" }}
          />
        </div>

        <div style={{ fontSize: 12, color: "#aaa", marginBottom: 12 }}>
          {mode === "top" ? "Top 20 sponsors by score" : `Results for "${query}"`}
          {loading && <span style={{ marginLeft: 8 }}>Loading...</span>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {companies.map((c) => (
            <CompanyCard key={c.employer} company={c} onClick={() => openCompany(c)} />
          ))}
        </div>

        {companies.length === 0 && !loading && (
          <div style={{ textAlign: "center", padding: "3rem", color: "#aaa", fontSize: 14 }}>
            No companies found for "{query}"
          </div>
        )}
      </div>

      {selected && <CompanyDrawer company={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}