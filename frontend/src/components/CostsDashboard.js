import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

const STATUS_COLORS = {
  "Suunniteltu": "#3b82f6",
  "Vahvistettu": "#eab308",
  "Käynnissä":   "#f97316",
  "Toimitettu":  "#22c55e",
  "Laskutettu":  "#475569",
};

const CATEGORIES = [
  { key: "lautta",    label: "🚢 Lautta",    color: "#0ea5e9" },
  { key: "rahti",     label: "🚛 Rahti",     color: "#f97316" },
  { key: "tiemaksut", label: "🛣️ Tiemaksut", color: "#eab308" },
  { key: "kalusto",   label: "🚜 Kalusto",   color: "#a855f7" },
  { key: "lisat",     label: "➕ Lisät",     color: "#64748b" },
];

// ── Päivämäärävälin laskenta periodin perusteella ─────────────────────────────
function getDateRange(period, customFrom, customTo) {
  const today = new Date();
  const y = today.getFullYear();
  const m = today.getMonth();
  const pad = (n) => String(n).padStart(2, "0");
  const fmt = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  if (period === "week") {
    const dow = today.getDay();
    const mon = new Date(today);
    mon.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
    const sun = new Date(mon);
    sun.setDate(mon.getDate() + 6);
    return [fmt(mon), fmt(sun)];
  }
  if (period === "month") {
    return [`${y}-${pad(m + 1)}-01`, fmt(new Date(y, m + 1, 0))];
  }
  if (period === "quarter") {
    const q = Math.floor(m / 3);
    return [fmt(new Date(y, q * 3, 1)), fmt(new Date(y, q * 3 + 3, 0))];
  }
  if (period === "year") {
    return [`${y}-01-01`, `${y}-12-31`];
  }
  // custom
  return [customFrom || "", customTo || ""];
}

// ── KPI-kortti ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, color, sub }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid #334155",
      borderRadius: "10px", padding: "20px", textAlign: "center",
    }}>
      <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
        {label}
      </div>
      <div style={{ color, fontSize: "22px", fontWeight: "700", fontFamily: "monospace" }}>{value}</div>
      {sub && <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>{sub}</div>}
    </div>
  );
}

// ── Pääkomponentti ────────────────────────────────────────────────────────────
function CostsDashboard() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState("month");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sortKey, setSortKey] = useState("loading_date");
  const [sortDir, setSortDir] = useState("desc");

  const [from, to] = useMemo(
    () => getDateRange(period, customFrom, customTo),
    [period, customFrom, customTo]
  );

  useEffect(() => {
    if (!from || !to) return;
    setLoading(true);
    fetch(`http://127.0.0.1:5000/api/costs-dashboard?from=${from}&to=${to}`)
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [from, to]);

  const sorted = useMemo(() => {
    if (!data?.trips) return [];
    return [...data.trips].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      const dir = sortDir === "asc" ? 1 : -1;
      if (av < bv) return -dir;
      if (av > bv) return dir;
      return 0;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };
  const sortIcon = (key) => sortKey !== key ? " ⇅" : sortDir === "asc" ? " ↑" : " ↓";

  // Kategoriagraafi: maksimiarvo normalisoinnille
  const catMax = useMemo(() => {
    if (!data?.categories) return 1;
    return Math.max(1, ...CATEGORIES.map(c => data.categories[c.key]?.osto || 0));
  }, [data]);

  const periodBtn = (key, label) => (
    <button
      onClick={() => setPeriod(key)}
      style={{
        background: period === key ? "#f97316" : "transparent",
        color: period === key ? "#fff" : "#94a3b8",
        border: `1px solid ${period === key ? "#f97316" : "#334155"}`,
        padding: "7px 14px", borderRadius: "6px",
        cursor: "pointer", fontSize: "13px", fontWeight: period === key ? "600" : "400"
      }}
    >{label}</button>
  );

  const inputStyle = {
    padding: "7px 12px", borderRadius: "6px", border: "1px solid #334155",
    background: "#0f172a", color: "#f1f5f9", fontSize: "13px", outline: "none"
  };

  const kpi = data?.kpi || {};
  const cats = data?.categories || {};

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>💸 Costs Dashboard</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {from && to ? `${from} – ${to}` : "Valitse aikaväli"}
            {kpi.trip_count != null && ` · ${kpi.trip_count} trippiä`}
          </div>
        </div>
        {/* Period-valitsin */}
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
          {periodBtn("week",  "Tämä viikko")}
          {periodBtn("month", "Kuukausi")}
          {periodBtn("quarter", "Kvartaali")}
          {periodBtn("year",  "Vuosi")}
          {periodBtn("custom", "Custom")}
          {period === "custom" && (
            <>
              <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)} style={inputStyle} />
              <span style={{ color: "#475569" }}>–</span>
              <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)} style={inputStyle} />
            </>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: "center", color: "#64748b", padding: "32px" }}>Ladataan...</div>
      )}

      {!loading && data && (
        <>
          {/* ── KPI-kortit ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "14px", marginBottom: "24px" }}>
            <KpiCard label="Kokonaismyynti" value={`${(kpi.revenue || 0).toFixed(2)} €`} color="#22c55e" />
            <KpiCard label="Kokonaisostot"  value={`${(kpi.costs || 0).toFixed(2)} €`}   color="#ef4444" />
            <KpiCard
              label="Kokonaiskate"
              value={`${(kpi.margin || 0).toFixed(2)} €`}
              color={(kpi.margin || 0) >= 0 ? "#22c55e" : "#ef4444"}
            />
            <KpiCard
              label="Kate %"
              value={`${(kpi.margin_pct || 0).toFixed(1)} %`}
              color={(kpi.margin_pct || 0) >= 15 ? "#22c55e" : (kpi.margin_pct || 0) >= 0 ? "#f97316" : "#ef4444"}
              sub={`${kpi.trip_count || 0} trippiä`}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "20px", marginBottom: "24px" }}>
            {/* ── Trip-taulukko ── */}
            <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
              {sorted.length === 0 ? (
                <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
                  Ei trippejä valitulla aikavälillä.
                </div>
              ) : (
                <table className="tms-table">
                  <thead>
                    <tr>
                      <th className="sortable" onClick={() => handleSort("trip_id")}>Trip ID{sortIcon("trip_id")}</th>
                      <th>Reitti</th>
                      <th className="sortable" onClick={() => handleSort("carrier_name")}>Carrier{sortIcon("carrier_name")}</th>
                      <th className="sortable" style={{ textAlign: "right" }} onClick={() => handleSort("costs")}>Ostot{sortIcon("costs")}</th>
                      <th className="sortable" style={{ textAlign: "right" }} onClick={() => handleSort("revenue")}>Myynti{sortIcon("revenue")}</th>
                      <th className="sortable" style={{ textAlign: "right" }} onClick={() => handleSort("margin")}>Kate€{sortIcon("margin")}</th>
                      <th className="sortable" style={{ textAlign: "right" }} onClick={() => handleSort("margin_pct")}>Kate%{sortIcon("margin_pct")}</th>
                      <th style={{ textAlign: "center" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map(t => (
                      <tr
                        key={t.id}
                        onClick={() => navigate(`/trips/${t.id}/orders`)}
                        style={{ cursor: "pointer" }}
                      >
                        <td style={{ color: "#f97316", fontWeight: "600", fontFamily: "monospace" }}>{t.trip_id}</td>
                        <td style={{ color: "#cbd5e1", fontSize: "12px" }}>{t.route}</td>
                        <td style={{ color: "#94a3b8" }}>{t.carrier_name}</td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", color: "#ef4444" }}>
                          {t.costs > 0 ? t.costs.toFixed(2) : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", color: "#22c55e" }}>
                          {t.revenue > 0 ? t.revenue.toFixed(2) : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: "600", color: t.margin >= 0 ? "#22c55e" : "#ef4444" }}>
                          {t.margin !== 0 ? t.margin.toFixed(2) : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", color: t.margin_pct >= 15 ? "#22c55e" : t.margin_pct >= 0 ? "#f97316" : "#ef4444" }}>
                          {t.revenue > 0 ? `${t.margin_pct.toFixed(1)} %` : "—"}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <span className="status-badge" style={{ background: STATUS_COLORS[t.status] || "#475569" }}>
                            {t.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* ── Kulujakauma ── */}
            <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", padding: "20px" }}>
              <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "16px" }}>
                Kulujakauma kategorioittain
              </div>
              {CATEGORIES.map(cat => {
                const osto   = cats[cat.key]?.osto   || 0;
                const myynti = cats[cat.key]?.myynti || 0;
                if (osto === 0 && myynti === 0) return null;
                const barW = catMax > 0 ? Math.round((osto / catMax) * 100) : 0;
                const barWRev = catMax > 0 ? Math.round((myynti / catMax) * 100) : 0;
                return (
                  <div key={cat.key} style={{ marginBottom: "16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ color: "#f1f5f9", fontSize: "13px" }}>{cat.label}</span>
                      <span style={{ fontFamily: "monospace", fontSize: "12px", color: "#94a3b8" }}>
                        {osto > 0 && <span style={{ color: "#ef4444" }}>{osto.toFixed(0)} €</span>}
                        {osto > 0 && myynti > 0 && <span style={{ color: "#475569" }}> / </span>}
                        {myynti > 0 && <span style={{ color: "#22c55e" }}>+{myynti.toFixed(0)} €</span>}
                      </span>
                    </div>
                    {/* Ostot-palkki */}
                    {osto > 0 && (
                      <div style={{ height: "8px", background: "#0f172a", borderRadius: "4px", overflow: "hidden", marginBottom: "3px" }}>
                        <div style={{
                          height: "100%", width: `${barW}%`, minWidth: "4px",
                          background: cat.color, borderRadius: "4px",
                          transition: "width 0.4s ease"
                        }} />
                      </div>
                    )}
                    {/* Myynti-palkki */}
                    {myynti > 0 && (
                      <div style={{ height: "6px", background: "#0f172a", borderRadius: "4px", overflow: "hidden" }}>
                        <div style={{
                          height: "100%", width: `${barWRev}%`, minWidth: "4px",
                          background: "rgba(34,197,94,0.5)", borderRadius: "4px",
                          transition: "width 0.4s ease"
                        }} />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Selite */}
              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #334155", display: "flex", gap: "16px", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>
                  <span style={{ display: "inline-block", width: "10px", height: "10px", background: "#ef4444", borderRadius: "2px", marginRight: "4px", verticalAlign: "middle" }} />
                  Ostot
                </span>
                <span style={{ color: "#94a3b8" }}>
                  <span style={{ display: "inline-block", width: "10px", height: "10px", background: "rgba(34,197,94,0.5)", borderRadius: "2px", marginRight: "4px", verticalAlign: "middle" }} />
                  Myynti
                </span>
              </div>

              {/* Kategoriasummat taulukko */}
              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #334155" }}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>Ostot yhteensä kategorioittain</div>
                {CATEGORIES.map(cat => {
                  const osto = cats[cat.key]?.osto || 0;
                  if (osto === 0) return null;
                  const pct = kpi.costs > 0 ? (osto / kpi.costs * 100).toFixed(0) : 0;
                  return (
                    <div key={cat.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "3px 0" }}>
                      <span style={{ color: "#94a3b8", fontSize: "12px" }}>{cat.label}</span>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span style={{ color: "#64748b", fontSize: "11px" }}>{pct}%</span>
                        <span style={{ fontFamily: "monospace", fontSize: "12px", color: "#f1f5f9" }}>{osto.toFixed(2)} €</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}

      {!loading && !data && (
        <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
          Dataa ei voitu ladata. Varmista yhteys backendiin.
        </div>
      )}
    </div>
  );
}

export default CostsDashboard;
