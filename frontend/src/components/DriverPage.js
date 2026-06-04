import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

const STEPS = [
  { key: "loading_started",   label: "Lastaus alkanut",  icon: "📦", col: "loading_started_at" },
  { key: "loading_completed", label: "Lastaus valmis",   icon: "✅", col: "loading_completed_at" },
  { key: "delivery_started",  label: "Purku alkanut",    icon: "🚚", col: "delivery_started_at" },
  { key: "delivery_completed",label: "Purku valmis",     icon: "🏁", col: "delivery_completed_at" },
];

function formatTs(ts) {
  if (!ts) return null;
  const d = new Date(ts + "Z");
  return d.toLocaleString("fi-FI", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}

export default function DriverPage() {
  const { trip_id } = useParams();
  const [trip, setTrip]     = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [busy, setBusy]     = useState(false);
  const [flash, setFlash]   = useState(null); // { text, ok }

  const fetchData = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/driver/${trip_id}`);
      if (!res.ok) { setError("Trippiä ei löydy: " + trip_id); return; }
      const data = await res.json();
      setTrip(data.trip);
      setOrders(data.orders);
    } catch {
      setError("Yhteysvirhe — tarkista verkko");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [trip_id]);

  const checkin = async (action) => {
    setBusy(true);
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/driver/${trip_id}/checkin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) { setFlash({ text: data.error || "Virhe", ok: false }); return; }
      setTrip(data.trip);
      const step = STEPS.find(s => s.key === action);
      setFlash({ text: `${step.icon} ${step.label} kuitattu!`, ok: true });
    } catch {
      setFlash({ text: "Yhteysvirhe", ok: false });
    } finally {
      setBusy(false);
      setTimeout(() => setFlash(null), 3000);
    }
  };

  // Seuraava kuittaamaton askel
  const nextStep = STEPS.find(s => !trip?.[s.col]);
  const allDone  = STEPS.every(s => trip?.[s.col]);

  if (loading) return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={{ color: "#94a3b8", textAlign: "center", padding: "40px" }}>Ladataan...</div>
      </div>
    </div>
  );

  if (error) return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={{ color: "#fca5a5", textAlign: "center", padding: "40px" }}>{error}</div>
      </div>
    </div>
  );

  return (
    <div style={styles.page}>
      {/* Flash */}
      {flash && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 9999,
          background: flash.ok ? "#15803d" : "#b91c1c",
          color: "#fff", textAlign: "center",
          padding: "16px", fontSize: "16px", fontWeight: "700"
        }}>
          {flash.text}
        </div>
      )}

      {/* Header */}
      <div style={styles.header}>
        <div style={{ fontSize: "22px", fontWeight: "800", color: "#f97316" }}>🚛 Freight Planner</div>
        <div style={{ color: "#94a3b8", fontSize: "13px", marginTop: "4px" }}>FEC — Kuljettajan kuittaus</div>
      </div>

      {/* Trip info */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <div>
            <div style={{ color: "#f97316", fontWeight: "800", fontSize: "20px" }}>{trip.trip_id}</div>
            <div style={{ color: "#94a3b8", fontSize: "13px", marginTop: "2px" }}>{trip.status}</div>
          </div>
          {trip.adr ? <span style={styles.badge("#dc2626")}>⚠️ ADR</span> : null}
          {trip.temperature_controlled ? <span style={styles.badge("#0891b2")}>🌡️ TEMP</span> : null}
        </div>

        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>Reitti</span>
          <span style={styles.infoVal}>
            {trip.first_pickup_country} {trip.first_pickup_city} → {trip.trip_end_country} {trip.trip_end_city}
          </span>
        </div>
        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>Kuljetusyhtiö</span>
          <span style={styles.infoVal}>{trip.carrier_name || "—"}</span>
        </div>
        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>Traileri</span>
          <span style={styles.infoVal}>
            {trip.plate_number || "—"}
            {trip.identifier ? ` / ${trip.identifier}` : ""}
          </span>
        </div>
        {trip.ferry_route && (
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Lauttareitti</span>
            <span style={styles.infoVal}>{trip.ferry_route}</span>
          </div>
        )}
        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>Lastaus</span>
          <span style={styles.infoVal}>
            {trip.loading_date || "—"}
            {trip.loading_time_start ? ` klo ${trip.loading_time_start}` : ""}
            {trip.loading_time_end   ? `–${trip.loading_time_end}` : ""}
          </span>
        </div>
        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>Toimitus</span>
          <span style={styles.infoVal}>
            {trip.delivery_date || "—"}
            {trip.delivery_time_start ? ` klo ${trip.delivery_time_start}` : ""}
            {trip.delivery_time_end   ? `–${trip.delivery_time_end}` : ""}
          </span>
        </div>
        {trip.loading_instructions && (
          <div style={{ marginTop: "10px", padding: "10px 12px", background: "rgba(249,115,22,0.08)", borderRadius: "8px", border: "1px solid rgba(249,115,22,0.2)" }}>
            <div style={{ color: "#f97316", fontSize: "11px", fontWeight: "700", marginBottom: "4px", textTransform: "uppercase" }}>Lastausohjeet</div>
            <div style={{ color: "#cbd5e1", fontSize: "13px", whiteSpace: "pre-wrap" }}>{trip.loading_instructions}</div>
          </div>
        )}
      </div>

      {/* Kuittausnapit */}
      <div style={styles.card}>
        <div style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "16px", fontWeight: "700" }}>
          Kuittaukset
        </div>

        {allDone ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: "40px", marginBottom: "8px" }}>🏁</div>
            <div style={{ color: "#22c55e", fontWeight: "700", fontSize: "18px" }}>Kaikki kuitattu!</div>
          </div>
        ) : (
          <button
            onClick={() => nextStep && checkin(nextStep.key)}
            disabled={busy || !nextStep}
            style={{
              width: "100%",
              padding: "20px",
              background: busy ? "#475569" : "#f97316",
              color: "#fff",
              border: "none",
              borderRadius: "12px",
              fontSize: "18px",
              fontWeight: "800",
              cursor: busy ? "not-allowed" : "pointer",
              marginBottom: "16px",
              letterSpacing: "0.3px"
            }}
          >
            {busy ? "Tallennetaan..." : nextStep ? `${nextStep.icon} ${nextStep.label}` : "—"}
          </button>
        )}

        {/* Historia */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {STEPS.map((step) => {
            const ts = trip[step.col];
            const done = !!ts;
            const isNext = !allDone && nextStep?.key === step.key;
            return (
              <div key={step.key} style={{
                display: "flex", alignItems: "center", gap: "12px",
                padding: "10px 12px",
                background: done ? "rgba(34,197,94,0.08)" : isNext ? "rgba(249,115,22,0.06)" : "rgba(255,255,255,0.02)",
                borderRadius: "8px",
                border: `1px solid ${done ? "rgba(34,197,94,0.2)" : isNext ? "rgba(249,115,22,0.2)" : "rgba(255,255,255,0.06)"}`
              }}>
                <span style={{ fontSize: "20px" }}>
                  {done ? "✅" : isNext ? step.icon : "⬜"}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ color: done ? "#22c55e" : isNext ? "#f97316" : "#64748b", fontWeight: "600", fontSize: "14px" }}>
                    {step.label}
                  </div>
                  {done && (
                    <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
                      {formatTs(ts)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Orderit */}
      {orders.length > 0 && (
        <div style={styles.card}>
          <div style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "16px", fontWeight: "700" }}>
            Orderit ({orders.length})
          </div>
          {orders.map((o, idx) => (
            <div key={o.order_id} style={{
              padding: "12px",
              background: "rgba(255,255,255,0.03)",
              borderRadius: "8px",
              border: "1px solid rgba(255,255,255,0.06)",
              marginBottom: idx < orders.length - 1 ? "8px" : 0
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ color: "#f97316", fontWeight: "700", fontSize: "13px" }}>{o.order_id}</span>
                <span style={{ color: "#64748b", fontSize: "12px" }}>{o.quantity} × {o.pallet_type}</span>
              </div>
              <div style={{ color: "#cbd5e1", fontSize: "13px", marginBottom: "4px" }}>
                {o.consignor_name} → {o.consignee_name}
              </div>
              <div style={{ color: "#64748b", fontSize: "12px" }}>
                {o.loading_point_city} ({o.loading_point_country}) → {o.unloading_point_city} ({o.unloading_point_country})
              </div>
              <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
                {o.weight} kg · {o.loading_meters} lm · {o.goods_description}
              </div>
              {o.loading_instructions && (
                <div style={{ marginTop: "8px", color: "#94a3b8", fontSize: "12px", fontStyle: "italic" }}>
                  📋 {o.loading_instructions}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div style={{ color: "#334155", fontSize: "11px", textAlign: "center", padding: "16px 0 32px" }}>
        Freight Planner FEC · {trip.trip_id}
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#0f172a",
    fontFamily: "Arial, sans-serif",
    padding: "0 0 32px",
    maxWidth: "480px",
    margin: "0 auto",
  },
  header: {
    background: "#1e293b",
    borderBottom: "1px solid #334155",
    padding: "20px 20px 16px",
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  card: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "12px",
    padding: "16px",
    margin: "12px 12px 0",
  },
  infoRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    padding: "5px 0",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
    gap: "12px",
  },
  infoLabel: {
    color: "#64748b",
    fontSize: "12px",
    flexShrink: 0,
  },
  infoVal: {
    color: "#f1f5f9",
    fontSize: "13px",
    textAlign: "right",
  },
  badge: (bg) => ({
    background: bg,
    color: "#fff",
    padding: "3px 10px",
    borderRadius: "10px",
    fontSize: "11px",
    fontWeight: "700",
  }),
};
