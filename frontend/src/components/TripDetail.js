import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useToast } from '../hooks/useToast';

const STATUS_COLORS = {
  "Suunniteltu": "#3b82f6",
  "Vahvistettu": "#eab308",
  "Käynnissä": "#f97316",
  "Toimitettu": "#22c55e",
  "Laskutettu": "#475569"
};

const STATUS_ORDER = ["Suunniteltu", "Vahvistettu", "Käynnissä", "Toimitettu", "Laskutettu"];

const COST_CODES = [
  { code: "100", description: "SPOT PRICE", type: "revenue" },
  { code: "120", description: "FREIGHT", type: "revenue" },
  { code: "200", description: "POLTTOAINELISÄ", type: "cost" },
  { code: "210", description: "KOTIMAAN AJO", type: "cost" },
  { code: "220", description: "MANTEREEN AJO", type: "cost" },
  { code: "300", description: "SAKSAN TIEMAKSU", type: "cost" },
  { code: "310", description: "HOLLANTI + SAKSA TIEMAKSU", type: "cost" },
  { code: "400", description: "TRAILERVUOKRA", type: "cost" },
  { code: "410", description: "TRAILERIN TANKKAUS", type: "cost" },
  { code: "500", description: "LAUTTAKUSTANNUS", type: "cost" },
  { code: "510", description: "SATAMAMAKSU", type: "cost" },
  { code: "600", description: "ADR-LISÄ", type: "cost" },
  { code: "610", description: "LÄMPÖTILALISÄ", type: "cost" },
  { code: "700", description: "KÄSITTELYMAKSU", type: "cost" },
  { code: "799", description: "MUUT KULUT", type: "cost" },
  { code: "800", description: "ODOTUSAIKA", type: "cost" },
  { code: "810", description: "LISÄKÄSITTELY", type: "cost" },
  { code: "820", description: "MUU KULU", type: "cost" },
];

const COST_GROUPS = [
  { key: "lautta",    label: "🚢 Lautta",    codes: ["500", "510"] },
  { key: "rahti",     label: "🚛 Rahti",     codes: ["100", "120", "200", "210", "220"] },
  { key: "tiemaksut", label: "🛣️ Tiemaksut", codes: ["300", "310"] },
  { key: "kalusto",   label: "🚜 Kalusto",   codes: ["400", "401", "410", "830", "831"] },
  { key: "lisat",     label: "➕ Lisät",     codes: ["600", "610", "700", "799", "800", "810", "820"] },
];

function CapacityBar({ label, value, max, unit }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const color = pct > 90 ? "#ef4444" : pct > 75 ? "#f97316" : "#22c55e";
  return (
    <div style={{ flex: 1 }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        fontSize: "12px",
        color: "#94a3b8",
        marginBottom: "4px"
      }}>
        <span>{label}</span>
        <span style={{ color: pct > 90 ? "#ef4444" : "#cbd5e1" }}>
          {value} / {max} {unit}
        </span>
      </div>
      <div style={{
        height: "8px",
        background: "#334155",
        borderRadius: "4px",
        overflow: "hidden"
      }}>
        <div style={{
          height: "100%",
          width: `${pct}%`,
          background: color,
          borderRadius: "4px",
          transition: "width 0.3s ease"
        }} />
      </div>
      <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
        {pct.toFixed(0)}%
      </div>
    </div>
  );
}

function StatusChain({ currentStatus }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0" }}>
      {STATUS_ORDER.map((status, i) => {
        const isDone = STATUS_ORDER.indexOf(currentStatus) > i;
        const isCurrent = currentStatus === status;
        const color = isDone || isCurrent ? STATUS_COLORS[status] : "#334155";
        return (
          <React.Fragment key={status}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: isCurrent ? STATUS_COLORS[status] : isDone ? "#334155" : "#1e293b",
                border: `2px solid ${color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                color: isDone ? "#22c55e" : isCurrent ? "#fff" : "#475569"
              }}>
                {isDone ? "✓" : i + 1}
              </div>
              <div style={{
                fontSize: "10px",
                marginTop: "4px",
                color: isCurrent ? STATUS_COLORS[status] : isDone ? "#64748b" : "#475569",
                fontWeight: isCurrent ? "700" : "400",
                whiteSpace: "nowrap"
              }}>
                {status}
              </div>
            </div>
            {i < STATUS_ORDER.length - 1 && (
              <div style={{
                height: "2px",
                width: "40px",
                background: STATUS_ORDER.indexOf(currentStatus) > i ? STATUS_COLORS[STATUS_ORDER[i + 1]] : "#334155",
                marginBottom: "18px"
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function TripDetail() {
  const { id: tripId, tab } = useParams();
  const navigate = useNavigate();
  const activeTab = tab || "orders";

  const toast = useToast();

  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [freeOrders, setFreeOrders] = useState([]);
  const [freeOrderSearch, setFreeOrderSearch] = useState("");
  const [freeOrderMatches, setFreeOrderMatches] = useState({});
  const [showAddOrder, setShowAddOrder] = useState(false);
  const [newCost, setNewCost] = useState({
    cost_code: "200",
    description: "POLTTOAINELISÄ",
    amount: "",
    cost_type: "cost",
    custom_description: ""
  });
  const [showAddCost, setShowAddCost] = useState(false);
  const [invoiceConfirm, setInvoiceConfirm] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [editingCostId, setEditingCostId] = useState(null);
  const [editForm, setEditForm] = useState({ cost_code: "", description: "", amount: "", cost_type: "cost", custom_description: "" });

  const fetchTrip = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/trips/${tripId}`);
      const data = await response.json();
      setTrip(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [tripId]);

  useEffect(() => {
    fetchTrip();
  }, [fetchTrip]);

  const fetchFreeOrders = async () => {
    const response = await fetch("http://127.0.0.1:5000/api/orders?status=Vapaa");
    const data = await response.json();
    setFreeOrders(data);
    setFreeOrderSearch("");

    if (!trip) return;
    const matches = {};
    await Promise.all(data.map(async (o) => {
      const params = new URLSearchParams({
        order_country: o.unloading_point_country || "",
        order_zip: o.unloading_point_zip || "",
        trip_country: trip.trip_end_country || "",
        trip_zip: trip.trip_end_zip || ""
      });
      const res = await fetch(`http://127.0.0.1:5000/api/route-match?${params}`);
      const d = await res.json();
      matches[o.id] = d.match;
    }));
    setFreeOrderMatches(matches);
  };

  const handleAddOrder = async (orderId) => {
    const response = await fetch(
      `http://127.0.0.1:5000/api/trips/${tripId}/orders/${orderId}`,
      { method: "POST" }
    );
    const data = await response.json();
    if (response.ok) {
      toast.success(`Tilaus lisätty kuljetukselle`);
      fetchTrip();
      fetchFreeOrders();
    } else {
      toast.error(data.warnings ? data.warnings.join(" ") : data.error || "Lisäys epäonnistui");
    }
  };

  const handleRemoveOrder = async (orderId) => {
    if (!window.confirm("Poistetaanko Order keikalta? Order palaa Vapaa-tilaan.")) return;
    const response = await fetch(
      `http://127.0.0.1:5000/api/trips/${tripId}/orders/${orderId}`,
      { method: "DELETE" }
    );
    if (response.ok) {
      toast.success("Tilaus poistettu keikalta");
      fetchTrip();
    } else {
      toast.error("Poisto epäonnistui");
    }
  };

  // ── Statuksen vaihto ────────────────────────────────────────────────────
  const handleStatusChange = async (newStatus) => {
    setStatusLoading(true);
    try {
      const response = await fetch(
        `http://127.0.0.1:5000/api/trips/${tripId}/status`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus })
        }
      );
      if (response.ok) {
        toast.success(`Status päivitetty: ${newStatus}`);
        fetchTrip();
      } else {
        const data = await response.json();
        toast.error(data.error || "Statuksen päivitys epäonnistui");
      }
    } catch {
      toast.error("Statuksen päivitys epäonnistui");
    } finally {
      setStatusLoading(false);
    }
  };

  // ── Laskuvahvistus ──────────────────────────────────────────────────────
  const handleConfirmInvoice = async () => {
    try {
      const response = await fetch(
        `http://127.0.0.1:5000/api/trips/${tripId}/status`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "Laskutettu" })
        }
      );
      if (response.ok) {
        toast.success("Lasku vahvistettu — kulut lukittu ✓");
        setInvoiceConfirm(false);
        fetchTrip();
      } else {
        const data = await response.json();
        toast.error(data.error || "Laskuvahvistus epäonnistui");
      }
    } catch {
      toast.error("Laskuvahvistus epäonnistui");
    }
  };

  // ── Kulun lisäys ────────────────────────────────────────────────────────
  const handleAddCost = async () => {
    const payload = {
      cost_code: newCost.cost_code,
      description: newCost.cost_code === "820"
        ? (newCost.custom_description || "MUU KULU")
        : newCost.description,
      amount: parseFloat(newCost.amount),
      cost_type: newCost.cost_type,
      custom_description: newCost.custom_description
    };

    try {
      const response = await fetch(
        `http://127.0.0.1:5000/api/trips/${tripId}/costs`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        }
      );
      if (response.ok) {
        toast.success(`Kulurivi ${newCost.cost_code} lisätty`);
        setNewCost({
          cost_code: "200",
          description: "POLTTOAINELISÄ",
          amount: "",
          cost_type: "cost",
          custom_description: ""
        });
        setShowAddCost(false);
        fetchTrip();
      } else {
        const data = await response.json();
        toast.error(data.error || "Kulun tallennus epäonnistui");
      }
    } catch {
      toast.error("Kulun tallennus epäonnistui");
    }
  };

  const handleDeleteCost = async (costId) => {
    if (!window.confirm("Poistetaanko kulu?")) return;
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/costs/${costId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        toast.success("Kulurivi poistettu");
        fetchTrip();
      } else {
        toast.error("Poisto epäonnistui");
      }
    } catch {
      toast.error("Poisto epäonnistui");
    }
  };

  const handleCostCodeChange = (code) => {
    const found = COST_CODES.find(c => c.code === code);
    setNewCost(prev => ({
      ...prev,
      cost_code: code,
      description: found ? found.description : "",
      cost_type: found ? found.type : "cost"
    }));
  };

  const openEditCost = (cost) => {
    setEditingCostId(cost.id);
    setEditForm({
      cost_code: cost.cost_code,
      description: cost.description,
      amount: String(cost.amount),
      cost_type: cost.cost_type,
      custom_description: cost.custom_description || ""
    });
  };

  const handleEditSave = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/costs/${editingCostId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...editForm, amount: parseFloat(editForm.amount) || 0 })
      });
      if (res.ok) {
        toast.success("Kulurivi päivitetty");
        setEditingCostId(null);
        fetchTrip();
      } else {
        const d = await res.json();
        toast.error(d.error || "Päivitys epäonnistui");
      }
    } catch {
      toast.error("Päivitys epäonnistui");
    }
  };

  if (loading) return (
    <div style={{ color: "#94a3b8", padding: "32px" }}>Ladataan...</div>
  );

  if (!trip) return (
    <div style={{ color: "#ef4444", padding: "32px" }}>Keikkaa ei löydy.</div>
  );

  const isLocked = trip.status === "Laskutettu";
  const currentStatusIdx = STATUS_ORDER.indexOf(trip.status);
  const prevStatus = currentStatusIdx > 0 ? STATUS_ORDER[currentStatusIdx - 1] : null;
  const nextStatus = currentStatusIdx < STATUS_ORDER.length - 1 ? STATUS_ORDER[currentStatusIdx + 1] : null;

  const sectionStyle = {
    background: "rgba(255,255,255,0.03)",
    border: "1px solid #334155",
    borderRadius: "8px",
    padding: "16px",
    marginBottom: "12px"
  };

  const inputStyle = {
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #334155",
    background: "#0f172a",
    color: "#f1f5f9",
    fontSize: "13px",
    outline: "none"
  };

  const tabs = [
    { id: "orders", label: "📦 Orderit" },
    { id: "cargo", label: "🚚 Kalusto & Reitti" },
    { id: "schedule", label: "🕐 Aikataulut" },
    { id: "costs", label: "💰 Kustannukset" }
  ];

  return (
    <div>
      {/* Takaisin-nappi */}
      <button
        onClick={() => navigate('/trips')}
        style={{
          background: "transparent",
          color: "#94a3b8",
          border: "none",
          cursor: "pointer",
          fontSize: "13px",
          marginBottom: "16px",
          padding: "0",
          display: "flex",
          alignItems: "center",
          gap: "6px"
        }}
      >
        ← Takaisin Trip-listaan
      </button>

      {/* ===== HEADER ===== */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "24px",
        marginBottom: "20px"
      }}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "20px"
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
              <h2 style={{ color: "#f97316", margin: 0, fontSize: "22px" }}>
                {trip.trip_id}
              </h2>
              <span style={{
                background: STATUS_COLORS[trip.status] || "#475569",
                color: "#fff",
                padding: "4px 14px",
                borderRadius: "12px",
                fontSize: "12px",
                fontWeight: "600"
              }}>
                {trip.status}
              </span>
              {trip.adr ? <span style={{ background: "#dc2626", color: "#fff", padding: "3px 10px", borderRadius: "10px", fontSize: "11px", fontWeight: "700" }}>⚠️ ADR</span> : null}
              {trip.temperature_controlled ? <span style={{ background: "#0891b2", color: "#fff", padding: "3px 10px", borderRadius: "10px", fontSize: "11px" }}>🌡️ TEMP</span> : null}
            </div>
            <div style={{ color: "#94a3b8", fontSize: "14px" }}>
              {trip.first_pickup_country} {trip.first_pickup_city || "—"} → {trip.trip_end_country} {trip.trip_end_city || "—"}
              {trip.ferry_route ? ` · ⛴️ ${trip.ferry_route}` : ""}
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {!isLocked && (
              <button
                onClick={() => navigate(`/trips/${tripId}/edit`)}
                style={{
                  background: "transparent",
                  color: "#94a3b8",
                  border: "1px solid #334155",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px"
                }}
              >
                ✏️ Muokkaa
              </button>
            )}
          </div>
        </div>

        {/* Statusketju */}
        <div style={{ marginBottom: "20px" }}>
          <StatusChain currentStatus={trip.status} />
        </div>

        {/* Status-napit */}
        {!isLocked && (
          <div style={{
            display: "flex",
            gap: "8px",
            marginBottom: "20px",
            flexWrap: "wrap"
          }}>
            {prevStatus && (
              <button
                onClick={() => handleStatusChange(prevStatus)}
                disabled={statusLoading}
                style={{
                  background: "transparent",
                  color: "#94a3b8",
                  border: "1px solid #475569",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px"
                }}
              >
                ← {prevStatus}
              </button>
            )}
            {nextStatus && nextStatus !== "Laskutettu" && (
              <button
                onClick={() => handleStatusChange(nextStatus)}
                disabled={statusLoading}
                style={{
                  background: STATUS_COLORS[nextStatus],
                  color: "#fff",
                  border: "none",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600"
                }}
              >
                {nextStatus} →
              </button>
            )}
            {trip.status === "Toimitettu" && (
              <button
                onClick={() => setInvoiceConfirm(true)}
                style={{
                  background: "#22c55e",
                  color: "#fff",
                  border: "none",
                  padding: "8px 20px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "700"
                }}
              >
                💶 Muodosta lasku
              </button>
            )}
          </div>
        )}

        {/* Kapasiteettipalkit */}
        <div style={{
          background: "rgba(0,0,0,0.2)",
          borderRadius: "8px",
          padding: "16px",
          display: "flex",
          gap: "24px"
        }}>
          <CapacityBar
            label="Paino"
            value={trip.capacity?.total_weight || 0}
            max={trip.max_weight || 24000}
            unit="kg"
          />
          <CapacityBar
            label="Lastausmetrit"
            value={trip.capacity?.total_loading_meters || 0}
            max={trip.max_loading_meters || 13.6}
            unit="lm"
          />
          <CapacityBar
            label="Tilavuus"
            value={trip.capacity?.total_volume || 0}
            max={trip.max_volume || 90}
            unit="m³"
          />
        </div>
      </div>

      {/* ===== VÄLILEHDET ===== */}
      <div style={{
        display: "flex",
        gap: "2px",
        marginBottom: "0",
        background: "#1e293b",
        borderRadius: "10px 10px 0 0",
        border: "1px solid #334155",
        borderBottom: "none",
        padding: "8px 8px 0"
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => navigate(`/trips/${tripId}/${tab.id}`)}
            style={{
              background: activeTab === tab.id ? "#0f172a" : "transparent",
              color: activeTab === tab.id ? "#f97316" : "#94a3b8",
              border: "none",
              borderRadius: "8px 8px 0 0",
              padding: "10px 20px",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: activeTab === tab.id ? "600" : "400",
              borderBottom: activeTab === tab.id ? "2px solid #f97316" : "2px solid transparent"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===== TAB CONTENT ===== */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderTop: "none",
        borderRadius: "0 0 12px 12px",
        padding: "24px"
      }}>

        {/* ===== ORDERIT ===== */}
        {activeTab === "orders" && (
          <div>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px"
            }}>
              <div style={{ color: "#cbd5e1", fontWeight: "600" }}>
                Keikalle yhdistetyt Orderit ({trip.orders?.length || 0})
              </div>
              {!isLocked && (
                <button
                  onClick={() => {
                    setShowAddOrder(!showAddOrder);
                    if (!showAddOrder) fetchFreeOrders();
                  }}
                  style={{
                    background: showAddOrder ? "#475569" : "#f97316",
                    color: "#fff",
                    border: "none",
                    padding: "8px 16px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "13px",
                    fontWeight: "600"
                  }}
                >
                  {showAddOrder ? "✕ Sulje" : "+ Lisää Order"}
                </button>
              )}
            </div>

            {showAddOrder && (() => {
              const MATCH_CONF = {
                good:    { icon: "✅", color: "#22c55e", border: "rgba(34,197,94,0.25)" },
                warning: { icon: "⚠️", color: "#eab308", border: "rgba(234,179,8,0.25)" },
                bad:     { icon: "❌", color: "#ef4444", border: "rgba(239,68,68,0.25)" }
              };
              const q = freeOrderSearch.toLowerCase();
              const visible = freeOrders
                .filter(o =>
                  !q ||
                  (o.order_id || "").toLowerCase().includes(q) ||
                  (o.consignor_name || "").toLowerCase().includes(q) ||
                  (o.consignee_name || "").toLowerCase().includes(q) ||
                  (o.goods_description || "").toLowerCase().includes(q)
                )
                .sort((a, b) => {
                  const ord = { good: 0, warning: 1, bad: 2 };
                  return (ord[freeOrderMatches[a.id]] ?? 1) - (ord[freeOrderMatches[b.id]] ?? 1);
                });
              return (
                <div style={{
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  padding: "16px",
                  marginBottom: "16px"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <div style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      Vapaat Orderit — klikkaa lisätäksesi
                    </div>
                    <div style={{ color: "#64748b", fontSize: "11px" }}>
                      ✅ sopii · ⚠️ tarkista · ❌ eri suunta
                    </div>
                  </div>
                  <input
                    type="text"
                    placeholder="🔍 Hae ordereista..."
                    value={freeOrderSearch}
                    onChange={e => setFreeOrderSearch(e.target.value)}
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      padding: "7px 12px",
                      borderRadius: "6px",
                      border: "1px solid #334155",
                      background: "#1e293b",
                      color: "#f1f5f9",
                      fontSize: "13px",
                      outline: "none",
                      marginBottom: "12px"
                    }}
                  />
                  {freeOrders.length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: "13px" }}>
                      Ei vapaita ordereita. Luo uusia Orderit-sivulta.
                    </div>
                  ) : visible.length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: "13px" }}>Ei hakuosumia.</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "320px", overflowY: "auto" }}>
                      {visible.map(o => {
                        const match = freeOrderMatches[o.id] || "warning";
                        const mc = MATCH_CONF[match];
                        return (
                          <div
                            key={o.id}
                            onClick={() => handleAddOrder(o.id)}
                            style={{
                              background: "#1e293b",
                              border: `1px solid ${mc.border}`,
                              borderRadius: "6px",
                              padding: "10px 14px",
                              cursor: "pointer",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              transition: "border-color 0.15s"
                            }}
                            onMouseEnter={e => e.currentTarget.style.borderColor = mc.color}
                            onMouseLeave={e => e.currentTarget.style.borderColor = mc.border}
                          >
                            <div>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                                <span style={{ color: "#f97316", fontWeight: "600" }}>{o.order_id}</span>
                                <span style={{ fontSize: "13px" }}>{mc.icon}</span>
                                <span style={{ color: "#cbd5e1", fontSize: "13px" }}>
                                  {o.consignor_name || "—"} → {o.consignee_name || "—"}
                                </span>
                              </div>
                              <div style={{ color: "#64748b", fontSize: "12px" }}>
                                {o.unloading_point_city ? `Purku: ${o.unloading_point_city} (${o.unloading_point_country}) · ` : ""}
                                {o.goods_description || "—"} · {o.weight} kg · {o.loading_meters} lm
                              </div>
                            </div>
                            <span style={{ color: mc.color, fontSize: "18px", marginLeft: "12px" }}>+</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })()}

            {trip.orders?.length === 0 ? (
              <div style={{
                padding: "32px",
                textAlign: "center",
                color: "#64748b",
                border: "1px dashed #334155",
                borderRadius: "8px"
              }}>
                Ei ordereita. Paina "+ Lisää Order" lisätäksesi.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {trip.orders.map((o, idx) => (
                  <div
                    key={o.id}
                    style={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: "8px",
                      padding: "14px 16px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <span style={{
                          color: "#64748b",
                          fontSize: "11px",
                          background: "#1e293b",
                          padding: "2px 8px",
                          borderRadius: "4px"
                        }}>
                          #{idx + 1}
                        </span>
                        <span style={{ color: "#f97316", fontWeight: "600" }}>
                          {o.order_id}
                        </span>
                        {o.adr ? <span style={{ color: "#ef4444", fontSize: "11px" }}>⚠️ ADR</span> : null}
                        {o.temperature_monitoring ? <span style={{ color: "#0891b2", fontSize: "11px" }}>🌡️</span> : null}
                      </div>
                      <div style={{ color: "#cbd5e1", fontSize: "13px", marginBottom: "2px" }}>
                        {o.consignor_name || "—"} → {o.consignee_name || "—"}
                      </div>
                      <div style={{ color: "#64748b", fontSize: "12px" }}>
                        {o.loading_point_city || "—"} → {o.unloading_point_city || "—"} ·{" "}
                        {o.goods_description || "—"} ·{" "}
                        {o.weight} kg · {o.loading_meters} lm · {o.quantity} × {o.pallet_type}
                      </div>
                    </div>
                    {!isLocked && (
                      <button
                        onClick={() => handleRemoveOrder(o.id)}
                        style={{
                          background: "transparent",
                          color: "#94a3b8",
                          border: "1px solid #334155",
                          padding: "6px 12px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          fontSize: "12px"
                        }}
                      >
                        Poista
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ===== KALUSTO & REITTI ===== */}
        {activeTab === "cargo" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
              <div style={sectionStyle}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  Kuljetusyhtiö
                </div>
                <div style={{ color: "#f1f5f9", fontSize: "15px", fontWeight: "600" }}>
                  {trip.carrier_name || "—"}
                </div>
                <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>
                  {trip.carrier_country || ""}
                </div>
              </div>
              <div style={sectionStyle}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  Kalusto
                </div>
                <div style={{ color: "#f1f5f9", fontSize: "15px", fontWeight: "600" }}>
                  {trip.plate_number || "—"}
                  {trip.identifier ? ` / ${trip.identifier}` : ""}
                </div>
                <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>
                  {trip.trailer_type || "—"}
                  {trip.truck_plate ? ` · Vetäjä: ${trip.truck_plate}` : ""}
                </div>
              </div>
              <div style={sectionStyle}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  Reitti
                </div>
                <div style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: "600" }}>
                  {trip.first_pickup_country} {trip.first_pickup_zip} {trip.first_pickup_city || "—"}
                </div>
                <div style={{ color: "#475569", fontSize: "13px", margin: "4px 0" }}>↓</div>
                <div style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: "600" }}>
                  {trip.trip_end_country} {trip.trip_end_zip} {trip.trip_end_city || "—"}
                </div>
                <div style={{ color: "#64748b", fontSize: "12px", marginTop: "6px" }}>
                  {trip.transport_type || "—"}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", marginTop: "12px", flexWrap: "wrap" }}>
              {trip.adr ? <span style={{ background: "#7f1d1d", color: "#fca5a5", padding: "4px 12px", borderRadius: "8px", fontSize: "12px" }}>⚠️ ADR</span> : null}
              {trip.temperature_controlled ? <span style={{ background: "#0c4a6e", color: "#7dd3fc", padding: "4px 12px", borderRadius: "8px", fontSize: "12px" }}>🌡️ Lämpösäädelty</span> : null}
              {trip.tail_lift ? <span style={{ background: "#1e3a5f", color: "#93c5fd", padding: "4px 12px", borderRadius: "8px", fontSize: "12px" }}>⬆️ Takalaitanostin</span> : null}
            </div>
          </div>
        )}

        {/* ===== AIKATAULUT ===== */}
        {activeTab === "schedule" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: trip.ferry_route ? "1fr 1fr 1fr" : "1fr 1fr", gap: "16px" }}>
              <div style={sectionStyle}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  🔼 Lastaus
                </div>
                <div style={{ color: "#f1f5f9", fontSize: "15px" }}>
                  {trip.loading_date || "—"}
                </div>
                <div style={{ color: "#94a3b8", fontSize: "13px", marginTop: "4px" }}>
                  {trip.loading_time_start && trip.loading_time_end
                    ? `${trip.loading_time_start} – ${trip.loading_time_end}`
                    : trip.loading_time_start || ""}
                </div>
                {trip.fixed_delivery_date ? (
                  <div style={{ color: "#f97316", fontSize: "12px", marginTop: "6px" }}>
                    📌 Kiinteä toimituspäivä
                  </div>
                ) : null}
              </div>
              <div style={sectionStyle}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  🔽 Toimitus
                </div>
                <div style={{ color: "#f1f5f9", fontSize: "15px" }}>
                  {trip.delivery_date || "—"}
                </div>
                <div style={{ color: "#94a3b8", fontSize: "13px", marginTop: "4px" }}>
                  {trip.delivery_time_start && trip.delivery_time_end
                    ? `${trip.delivery_time_start} – ${trip.delivery_time_end}`
                    : trip.delivery_time_start || ""}
                </div>
              </div>
              {trip.ferry_route && (
                <div style={sectionStyle}>
                  <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                    ⛴️ Lauttayhteys
                  </div>
                  <div style={{ color: "#f1f5f9", fontSize: "15px", fontWeight: "600" }}>
                    {trip.ferry_route}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "13px", marginTop: "6px" }}>
                    {trip.ferry_departure && <div>Lähtö: {trip.ferry_departure}</div>}
                    {trip.ferry_arrival && <div>Saapuminen: {trip.ferry_arrival}</div>}
                  </div>
                </div>
              )}
            </div>

            {trip.loading_instructions && (
              <div style={{ ...sectionStyle, marginTop: "16px" }}>
                <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
                  📝 Lastausohjeet
                </div>
                <div style={{ color: "#cbd5e1", fontSize: "13px", lineHeight: "1.6" }}>
                  {trip.loading_instructions}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ===== KUSTANNUKSET ===== */}
        {activeTab === "costs" && (
          <div>
            {/* 4-column summary cards */}
            {(() => {
              const rev = trip.costs?.filter(c => c.cost_type === "revenue").reduce((s, c) => s + c.amount, 0) || 0;
              const osto = trip.costs?.filter(c => c.cost_type === "cost").reduce((s, c) => s + c.amount, 0) || 0;
              const margin = rev - osto;
              const marginPct = rev > 0 ? (margin / rev * 100) : 0;
              return (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "12px", marginBottom: "20px" }}>
                  <div style={{ ...sectionStyle, textAlign: "center", marginBottom: 0 }}>
                    <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>Ostot</div>
                    <div style={{ color: "#ef4444", fontSize: "20px", fontWeight: "700", fontFamily: "monospace" }}>{osto.toFixed(2)} €</div>
                  </div>
                  <div style={{ ...sectionStyle, textAlign: "center", marginBottom: 0 }}>
                    <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>Myynti</div>
                    <div style={{ color: "#22c55e", fontSize: "20px", fontWeight: "700", fontFamily: "monospace" }}>{rev.toFixed(2)} €</div>
                  </div>
                  <div style={{ ...sectionStyle, textAlign: "center", marginBottom: 0 }}>
                    <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>Kate</div>
                    <div style={{ color: margin >= 0 ? "#22c55e" : "#ef4444", fontSize: "20px", fontWeight: "700", fontFamily: "monospace" }}>{margin.toFixed(2)} €</div>
                  </div>
                  <div style={{ ...sectionStyle, textAlign: "center", marginBottom: 0 }}>
                    <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>Kate %</div>
                    <div style={{ color: marginPct >= 15 ? "#22c55e" : marginPct >= 0 ? "#f97316" : "#ef4444", fontSize: "20px", fontWeight: "700", fontFamily: "monospace" }}>{marginPct.toFixed(1)} %</div>
                  </div>
                </div>
              );
            })()}

            {/* Grouped cost rows */}
            {(() => {
              const allCosts = trip.costs || [];
              const orderCount = trip.orders?.length || 0;
              const ferryTotal = allCosts.filter(c => c.cost_code === "500").reduce((s, c) => s + c.amount, 0);
              const ferryPerOrder = orderCount > 1 && ferryTotal > 0 ? ferryTotal / orderCount : null;
              const groupedIds = new Set(COST_GROUPS.flatMap(g => g.codes));

              const renderCostRow = (cost) => {
                const isEditing = editingCostId === cost.id;
                if (isEditing) {
                  return (
                    <div key={cost.id} style={{
                      display: "grid", gridTemplateColumns: "90px 1fr 110px 96px",
                      gap: "6px", padding: "8px 12px",
                      background: "rgba(249,115,22,0.08)", borderRadius: "6px",
                      marginBottom: "3px", alignItems: "center",
                      border: "1px solid rgba(249,115,22,0.3)"
                    }}>
                      <select
                        value={editForm.cost_code}
                        onChange={e => {
                          const f = COST_CODES.find(c => c.code === e.target.value);
                          setEditForm(ef => ({ ...ef, cost_code: e.target.value, description: f ? f.description : ef.description, cost_type: f ? f.type : ef.cost_type }));
                        }}
                        style={{ ...inputStyle, fontSize: "12px", padding: "4px 6px" }}
                      >
                        {COST_CODES.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
                      </select>
                      <input
                        type="text"
                        value={editForm.description}
                        onChange={e => setEditForm(ef => ({ ...ef, description: e.target.value }))}
                        style={{ ...inputStyle, fontSize: "13px", padding: "4px 8px" }}
                      />
                      <input
                        type="number"
                        value={editForm.amount}
                        onChange={e => setEditForm(ef => ({ ...ef, amount: e.target.value }))}
                        style={{ ...inputStyle, fontSize: "13px", padding: "4px 8px", textAlign: "right" }}
                      />
                      <div style={{ display: "flex", gap: "4px", justifyContent: "flex-end" }}>
                        <button onClick={handleEditSave} style={{ background: "#22c55e", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", cursor: "pointer", fontSize: "13px" }}>✓</button>
                        <button onClick={() => setEditingCostId(null)} style={{ background: "transparent", color: "#94a3b8", border: "1px solid #334155", padding: "4px 8px", borderRadius: "4px", cursor: "pointer", fontSize: "13px" }}>✕</button>
                        <button onClick={() => handleDeleteCost(cost.id)} style={{ background: "transparent", color: "#ef4444", border: "1px solid #334155", padding: "4px 8px", borderRadius: "4px", cursor: "pointer", fontSize: "13px" }}>🗑️</button>
                      </div>
                    </div>
                  );
                }
                return (
                  <div
                    key={cost.id}
                    onClick={() => !isLocked && openEditCost(cost)}
                    style={{
                      display: "grid", gridTemplateColumns: "90px 1fr 110px 24px",
                      gap: "6px", padding: "8px 12px",
                      background: cost.cost_type === "revenue" ? "rgba(34,197,94,0.05)" : "rgba(255,255,255,0.02)",
                      borderRadius: "6px", marginBottom: "3px", alignItems: "center",
                      border: `1px solid ${cost.cost_type === "revenue" ? "rgba(34,197,94,0.1)" : "#334155"}`,
                      cursor: isLocked ? "default" : "pointer",
                      transition: "background 0.1s"
                    }}
                    onMouseEnter={e => { if (!isLocked) e.currentTarget.style.background = "rgba(249,115,22,0.06)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = cost.cost_type === "revenue" ? "rgba(34,197,94,0.05)" : "rgba(255,255,255,0.02)"; }}
                  >
                    <div style={{ fontFamily: "monospace", color: cost.cost_type === "revenue" ? "#22c55e" : "#94a3b8", fontSize: "12px" }}>{cost.cost_code}</div>
                    <div style={{ color: "#cbd5e1", fontSize: "13px" }}>{cost.description}</div>
                    <div style={{ textAlign: "right", color: cost.cost_type === "revenue" ? "#22c55e" : "#f1f5f9", fontWeight: "600", fontFamily: "monospace", fontSize: "13px" }}>
                      {cost.cost_type === "revenue" ? "+" : ""}{cost.amount?.toFixed(2)} €
                    </div>
                    <div>{!isLocked && <span style={{ color: "#475569", fontSize: "11px" }}>✏️</span>}</div>
                  </div>
                );
              };

              return (
                <div style={{ marginBottom: "16px" }}>
                  {COST_GROUPS.map(group => {
                    const rows = allCosts.filter(c => group.codes.includes(c.cost_code));
                    if (rows.length === 0) return null;
                    const gRev = rows.filter(c => c.cost_type === "revenue").reduce((s, c) => s + c.amount, 0);
                    const gCost = rows.filter(c => c.cost_type === "cost").reduce((s, c) => s + c.amount, 0);
                    return (
                      <div key={group.key} style={{ marginBottom: "10px" }}>
                        <div style={{
                          display: "flex", alignItems: "center", justifyContent: "space-between",
                          padding: "5px 12px", background: "#0f172a",
                          borderRadius: "6px 6px 0 0", border: "1px solid #334155", borderBottom: "none"
                        }}>
                          <span style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600" }}>{group.label}</span>
                          <span style={{ fontFamily: "monospace", fontSize: "12px" }}>
                            {gRev > 0 && <span style={{ color: "#22c55e" }}>+{gRev.toFixed(2)} €</span>}
                            {gRev > 0 && gCost > 0 && <span style={{ color: "#475569" }}> / </span>}
                            {gCost > 0 && <span style={{ color: "#ef4444" }}>-{gCost.toFixed(2)} €</span>}
                          </span>
                        </div>
                        <div style={{ border: "1px solid #334155", borderTop: "none", borderRadius: "0 0 6px 6px", padding: "6px 0" }}>
                          {rows.map(renderCostRow)}
                          {group.key === "lautta" && ferryPerOrder !== null && (
                            <div style={{ padding: "2px 12px 4px", color: "#64748b", fontSize: "11px" }}>
                              ≈ {ferryPerOrder.toFixed(2)} € / order ({orderCount} orderia)
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {(() => {
                    const ungrouped = allCosts.filter(c => !groupedIds.has(c.cost_code));
                    if (ungrouped.length === 0) return null;
                    return (
                      <div style={{ marginBottom: "10px" }}>
                        <div style={{ padding: "5px 12px", background: "#0f172a", borderRadius: "6px 6px 0 0", border: "1px solid #334155", borderBottom: "none" }}>
                          <span style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600" }}>Muut</span>
                        </div>
                        <div style={{ border: "1px solid #334155", borderTop: "none", borderRadius: "0 0 6px 6px", padding: "6px 0" }}>
                          {ungrouped.map(renderCostRow)}
                        </div>
                      </div>
                    );
                  })()}
                  {allCosts.length === 0 && (
                    <div style={{ padding: "24px", textAlign: "center", color: "#64748b", border: "1px dashed #334155", borderRadius: "8px" }}>
                      Ei kulurivejä. Lisää kulu alla.
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Lisää kulu */}
            {!isLocked && (
              <div>
                {!showAddCost ? (
                  <button
                    onClick={() => setShowAddCost(true)}
                    style={{
                      background: "transparent", color: "#f97316",
                      border: "1px dashed #f97316", padding: "10px 20px",
                      borderRadius: "6px", cursor: "pointer", fontSize: "13px", width: "100%"
                    }}
                  >
                    + Lisää kulurivi
                  </button>
                ) : (
                  <div style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: "8px", padding: "16px" }}>
                    {newCost.cost_code === "120" && (
                      <div style={{ color: "#f97316", fontSize: "12px", marginBottom: "8px" }}>
                        ⛽ FREIGHT-rivi lisää automaattisesti POLTTOAINELISÄ (200) -rivin.
                      </div>
                    )}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 120px", gap: "12px", marginBottom: "12px" }}>
                      <div>
                        <div style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>Kulukoodi</div>
                        <select value={newCost.cost_code} onChange={(e) => handleCostCodeChange(e.target.value)} style={{ ...inputStyle, width: "100%" }}>
                          {COST_CODES.map(c => <option key={c.code} value={c.code}>{c.code} — {c.description}</option>)}
                        </select>
                      </div>
                      <div>
                        <div style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>
                          {newCost.cost_code === "820" ? "Oma kuvaus" : "Kuvaus"}
                        </div>
                        <input
                          type="text"
                          value={newCost.cost_code === "820" ? newCost.custom_description : newCost.description}
                          onChange={(e) => { if (newCost.cost_code === "820") setNewCost(prev => ({ ...prev, custom_description: e.target.value })); }}
                          readOnly={newCost.cost_code !== "820"}
                          style={{ ...inputStyle, width: "100%", opacity: newCost.cost_code !== "820" ? 0.6 : 1 }}
                        />
                      </div>
                      <div>
                        <div style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>Summa (€)</div>
                        <input
                          type="number"
                          value={newCost.amount}
                          onChange={(e) => setNewCost(prev => ({ ...prev, amount: e.target.value }))}
                          placeholder="0.00"
                          style={{ ...inputStyle, width: "100%" }}
                        />
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                      <button
                        onClick={() => setShowAddCost(false)}
                        style={{
                          background: "transparent",
                          color: "#94a3b8",
                          border: "1px solid #334155",
                          padding: "8px 16px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          fontSize: "13px"
                        }}
                      >
                        Peruuta
                      </button>
                      <button
                        onClick={handleAddCost}
                        style={{
                          background: "#f97316",
                          color: "#fff",
                          border: "none",
                          padding: "8px 16px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          fontSize: "13px",
                          fontWeight: "600"
                        }}
                      >
                        💾 Lisää
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {isLocked && (
              <div style={{ marginTop: "12px", padding: "10px 16px", background: "rgba(71,85,105,0.15)", border: "1px solid #475569", borderRadius: "8px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                🔒 Keikka on laskutettu — kulut lukittu
              </div>
            )}

            {/* Laskun vahvistus */}
            {trip.status === "Toimitettu" && !isLocked && (
              <div style={{
                marginTop: "24px",
                background: "rgba(34,197,94,0.05)",
                border: "1px solid rgba(34,197,94,0.2)",
                borderRadius: "8px",
                padding: "16px",
                textAlign: "center"
              }}>
                <div style={{ color: "#22c55e", fontWeight: "600", marginBottom: "8px" }}>
                  Keikka on toimitettu — valmis laskutukseen
                </div>
                <button
                  onClick={() => setInvoiceConfirm(true)}
                  style={{
                    background: "#22c55e",
                    color: "#fff",
                    border: "none",
                    padding: "10px 24px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: "700",
                    fontSize: "14px"
                  }}
                >
                  💶 Muodosta lasku
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ===== LASKUVAHVISTUS MODAALI ===== */}
      {invoiceConfirm && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>
          <div style={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "16px",
            padding: "32px",
            maxWidth: "400px",
            width: "90%"
          }}>
            <div style={{ fontSize: "32px", textAlign: "center", marginBottom: "16px" }}>⚠️</div>
            <h3 style={{ color: "#f1f5f9", margin: "0 0 8px", textAlign: "center" }}>
              Vahvista laskutus
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "13px", textAlign: "center", margin: "0 0 20px" }}>
              Tätä toimintoa ei voi peruuttaa. Keikka lukitaan laskutuksen jälkeen.
            </p>
            <div style={{
              background: "#0f172a",
              borderRadius: "8px",
              padding: "16px",
              marginBottom: "20px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ color: "#64748b" }}>Myynti</span>
                <span style={{ color: "#22c55e", fontWeight: "600" }}>
                  {trip.total_revenue?.toFixed(2)} €
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ color: "#64748b" }}>Kulut</span>
                <span style={{ color: "#ef4444", fontWeight: "600" }}>
                  {trip.total_costs?.toFixed(2)} €
                </span>
              </div>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                borderTop: "1px solid #334155",
                paddingTop: "8px",
                marginTop: "8px"
              }}>
                <span style={{ color: "#94a3b8", fontWeight: "600" }}>Kate</span>
                <span style={{
                  color: trip.margin >= 0 ? "#22c55e" : "#ef4444",
                  fontWeight: "700"
                }}>
                  {trip.margin?.toFixed(2)} € ({trip.margin_percent?.toFixed(1)}%)
                </span>
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => setInvoiceConfirm(false)}
                style={{
                  flex: 1,
                  background: "transparent",
                  color: "#94a3b8",
                  border: "1px solid #334155",
                  padding: "10px",
                  borderRadius: "6px",
                  cursor: "pointer"
                }}
              >
                Peruuta
              </button>
              <button
                onClick={handleConfirmInvoice}
                style={{
                  flex: 1,
                  background: "#22c55e",
                  color: "#fff",
                  border: "none",
                  padding: "10px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "700"
                }}
              >
                ✅ Vahvista lasku
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TripDetail;