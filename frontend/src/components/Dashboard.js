import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const STATUS_COLORS = {
  "Suunniteltu": "#64748b",
  "Vahvistettu": "#3b82f6",
  "Käynnissä": "#f97316",
  "Toimitettu": "#22c55e",
  "Laskutettu": "#a855f7"
};

function KpiCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: "12px",
      padding: "20px 24px"
    }}>
      <div style={{ color: "#64748b", fontSize: "12px", fontWeight: "700",
        textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
        {label}
      </div>
      <div style={{ color: color || "#f1f5f9", fontSize: "28px", fontWeight: "700" }}>
        {value}
      </div>
      {sub && (
        <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>{sub}</div>
      )}
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/dashboard")
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ color: "#94a3b8", padding: "48px", textAlign: "center" }}>
      Ladataan...
    </div>
  );

  if (!data) return (
    <div style={{ color: "#fca5a5", padding: "48px", textAlign: "center" }}>
      Tietojen lataus epäonnistui.
    </div>
  );

  const { kpi, trips, status_counts } = data;

  const marginColor = kpi.margin >= 0 ? "#22c55e" : "#ef4444";

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Dashboard</h1>
        <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
          Yhteenveto kaikista keikkoista
        </div>
      </div>

      {/* KPI-kortit */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: "16px",
        marginBottom: "28px"
      }}>
        <KpiCard label="Keikkoja" value={kpi.total_trips} />
        <KpiCard label="Ordereita" value={kpi.total_orders} />
        <KpiCard
          label="Liikevaihto"
          value={`${kpi.total_revenue.toLocaleString("fi-FI")} €`}
          color="#f97316"
        />
        <KpiCard
          label="Kulut"
          value={`${kpi.total_costs.toLocaleString("fi-FI")} €`}
          color="#94a3b8"
        />
        <KpiCard
          label="Kate"
          value={`${kpi.margin.toLocaleString("fi-FI")} €`}
          sub={`${kpi.margin_percent} %`}
          color={marginColor}
        />
      </div>

      {/* Status-jako */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "20px 24px",
        marginBottom: "24px"
      }}>
        <div style={{ color: "#64748b", fontSize: "12px", fontWeight: "700",
          textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "16px" }}>
          Keikkojen tila
        </div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          {status_counts.map(s => (
            <div key={s.status} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{
                display: "inline-block",
                width: "10px", height: "10px",
                borderRadius: "50%",
                background: STATUS_COLORS[s.status] || "#475569"
              }} />
              <span style={{ color: "#cbd5e1", fontSize: "13px" }}>
                {s.status}
              </span>
              <span style={{
                background: "#334155",
                color: "#f1f5f9",
                borderRadius: "12px",
                padding: "1px 8px",
                fontSize: "12px",
                fontWeight: "700"
              }}>
                {s.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Keikka-taulukko */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        overflow: "hidden"
      }}>
        <div style={{
          padding: "16px 20px",
          borderBottom: "1px solid #334155",
          color: "#64748b",
          fontSize: "12px",
          fontWeight: "700",
          textTransform: "uppercase",
          letterSpacing: "0.5px"
        }}>
          Viimeisimmät keikät — kate per keikka
        </div>
        {trips.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            Ei keikkoja vielä.
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th>Keikka</th>
                <th>Status</th>
                <th>Reitti</th>
                <th>Rahdinantaja</th>
                <th style={{ textAlign: "right" }}>Orderit</th>
                <th style={{ textAlign: "right" }}>Liikevaihto</th>
                <th style={{ textAlign: "right" }}>Kulut</th>
                <th style={{ textAlign: "right" }}>Kate</th>
                <th style={{ textAlign: "right" }}>Kate %</th>
              </tr>
            </thead>
            <tbody>
              {trips.map(t => {
                const marginColor = t.margin > 0 ? "#22c55e" : t.margin < 0 ? "#ef4444" : "#64748b";
                return (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/trips/${t.id}/orders`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td style={{ color: "#f97316", fontWeight: "600" }}>{t.trip_id}</td>
                    <td>
                      <span className="status-badge"
                        style={{ background: STATUS_COLORS[t.status] || "#475569" }}>
                        {t.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ color: "#cbd5e1", fontSize: "13px" }}>
                        {t.first_pickup_city || "—"} → {t.trip_end_city || "—"}
                      </div>
                      <div style={{ color: "#64748b", fontSize: "11px" }}>
                        {t.loading_date || ""}
                      </div>
                    </td>
                    <td style={{ color: "#94a3b8", fontSize: "13px" }}>
                      {t.carrier_name || "—"}
                    </td>
                    <td style={{ textAlign: "right", color: "#94a3b8" }}>{t.order_count}</td>
                    <td style={{ textAlign: "right", fontFamily: "monospace", color: "#f97316" }}>
                      {t.total_revenue > 0 ? `${t.total_revenue.toLocaleString("fi-FI")} €` : "—"}
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "monospace", color: "#94a3b8" }}>
                      {t.total_costs > 0 ? `${t.total_costs.toLocaleString("fi-FI")} €` : "—"}
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "monospace", color: marginColor, fontWeight: "600" }}>
                      {t.total_revenue > 0 || t.total_costs > 0
                        ? `${t.margin.toLocaleString("fi-FI")} €`
                        : "—"}
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "monospace", color: marginColor }}>
                      {t.total_revenue > 0 ? `${t.margin_percent} %` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
