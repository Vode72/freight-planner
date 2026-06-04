import React, { useState, useEffect } from "react";
import { useToast } from '../hooks/useToast';

const MATCH_CONFIG = {
  good: {
    icon: "✅",
    label: "Sopii hyvin",
    color: "#22c55e",
    border: "rgba(34,197,94,0.2)"
  },
  warning: {
    icon: "⚠️",
    label: "Tarkista reitti",
    color: "#eab308",
    border: "rgba(234,179,8,0.2)"
  },
  bad: {
    icon: "❌",
    label: "Eri suunta",
    color: "#ef4444",
    border: "rgba(239,68,68,0.2)"
  }
};

const STATUS_COLORS = {
  "Suunniteltu": "#3b82f6",
  "Vahvistettu": "#eab308",
  "Käynnissä": "#f97316",
};

function AddToTripModal({ order, onClose, onSuccess, onCreateNewTrip }) {
  // ── useToast AINA komponentin sisällä ───────────────────────────────────
  const toast = useToast();

  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(null);
  const [matchCache, setMatchCache] = useState({});

  useEffect(() => {
    fetchActiveTrips();
  }, []);

  const fetchActiveTrips = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/trips");
      const data = await response.json();
      const active = data.filter(t =>
        t.status !== "Laskutettu" && t.status !== "Toimitettu"
      );

      const matches = {};
      await Promise.all(active.map(async (trip) => {
        const params = new URLSearchParams({
          order_country: order.unloading_point_country || "",
          order_zip: order.unloading_point_zip || "",
          trip_country: trip.trip_end_country || "",
          trip_zip: trip.trip_end_zip || ""
        });
        const res = await fetch(`http://127.0.0.1:5000/api/route-match?${params}`);
        const matchData = await res.json();
        matches[trip.id] = matchData.match;
      }));

      setMatchCache(matches);

      const sorted = [...active].sort((a, b) => {
        const order = { good: 0, warning: 1, bad: 2 };
        return (order[matches[a.id]] || 1) - (order[matches[b.id]] || 1);
      });

      setTrips(sorted);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // ── KORJATTU handleAddToTrip — saa trip-objektin, ei erillistä tripRef ─
  const handleAddToTrip = async (trip) => {
    setAdding(trip.id);
    try {
      const response = await fetch(
        `http://127.0.0.1:5000/api/trips/${trip.id}/orders/${order.id}`,
        { method: "POST" }
      );
      const data = await response.json();
      if (response.ok) {
        toast.success(`Tilaus ${order.order_id} lisätty kuljetukselle ${trip.trip_id}`);
        onClose();
        if (onSuccess) onSuccess();
      } else {
        toast.error(data.warnings ? data.warnings.join(" ") : data.error || "Lisäys epäonnistui");
      }
    } catch {
      toast.error("Lisäys epäonnistui — tarkista yhteys");
    } finally {
      setAdding(null);
    }
  };
  // ────────────────────────────────────────────────────────────────────────

  const getCapacityColor = (used, max) => {
    const pct = max > 0 ? (used / max) * 100 : 0;
    if (pct > 90) return "#ef4444";
    if (pct > 70) return "#f97316";
    return "#22c55e";
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999
    }}>
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "16px",
        padding: "32px",
        maxWidth: "640px",
        width: "90%",
        maxHeight: "85vh",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column"
      }}>
        {/* Header */}
        <div style={{ marginBottom: "20px" }}>
          <h3 style={{ color: "#f97316", margin: "0 0 12px" }}>
            🚚 Lisää Order Tripille
          </h3>
          <div style={{
            background: "#0f172a",
            borderRadius: "8px",
            padding: "12px 16px"
          }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "4px"
            }}>
              <span style={{ color: "#f97316", fontWeight: "600" }}>
                {order.order_id}
              </span>
              {order.unloading_point_country && (
                <span style={{
                  background: "#1e293b",
                  color: "#94a3b8",
                  padding: "2px 8px",
                  borderRadius: "6px",
                  fontSize: "11px"
                }}>
                  Purku: {order.unloading_point_country} {order.unloading_point_zip} {order.unloading_point_city}
                </span>
              )}
            </div>
            <div style={{ color: "#cbd5e1", fontSize: "13px" }}>
              {order.consignor_name || "—"} → {order.consignee_name || "—"}
            </div>
            <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
              {order.goods_description || "—"} · {order.weight} kg · {order.loading_meters} lm
            </div>
          </div>
        </div>

        {/* "+ Luo uusi Trip" nappi */}
        <button
          onClick={onCreateNewTrip}
          style={{
            background: "#22c55e",
            color: "#fff",
            border: "none",
            padding: "12px",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: "700",
            fontSize: "14px",
            marginBottom: "16px"
          }}
        >
          + Luo uusi Trip tästä Orderista
        </button>

        {/* Erottaja */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "16px"
        }}>
          <div style={{ flex: 1, height: "1px", background: "#334155" }} />
          <span style={{ color: "#475569", fontSize: "12px" }}>
            tai lisää olemassa olevaan
          </span>
          <div style={{ flex: 1, height: "1px", background: "#334155" }} />
        </div>

        {/* Trip lista */}
        <div style={{ flex: 1, overflowY: "auto", marginBottom: "16px" }}>
          {loading ? (
            <div style={{ color: "#94a3b8", textAlign: "center", padding: "24px" }}>
              Ladataan...
            </div>
          ) : trips.length === 0 ? (
            <div style={{
              color: "#64748b",
              textAlign: "center",
              padding: "24px",
              border: "1px dashed #334155",
              borderRadius: "8px"
            }}>
              Ei avoimia trippejä.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {trips.map(trip => {
                const match = matchCache[trip.id] || "warning";
                const matchConf = MATCH_CONFIG[match];
                const weightUsed = trip.total_weight || 0;
                const lmUsed = trip.total_loading_meters || 0;
                const maxWeight = 24000;
                const maxLm = 13.6;

                return (
                  <div
                    key={trip.id}
                    style={{
                      background: "#0f172a",
                      border: `1px solid ${matchConf.border}`,
                      borderRadius: "8px",
                      padding: "14px 16px",
                      display: "flex",
                      gap: "12px",
                      alignItems: "center"
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "4px",
                        flexWrap: "wrap"
                      }}>
                        <span style={{ color: "#f97316", fontWeight: "600", fontSize: "14px" }}>
                          {trip.trip_id}
                        </span>
                        <span style={{
                          background: STATUS_COLORS[trip.status] || "#475569",
                          color: "#fff",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          fontSize: "11px",
                          fontWeight: "600"
                        }}>
                          {trip.status}
                        </span>
                        <span style={{
                          color: matchConf.color,
                          fontSize: "12px",
                          fontWeight: "600"
                        }}>
                          {matchConf.icon} {matchConf.label}
                        </span>
                      </div>

                      <div style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "8px" }}>
                        {trip.first_pickup_country} {trip.first_pickup_city} → {trip.trip_end_country} {trip.trip_end_zip} {trip.trip_end_city}
                        {trip.carrier_name ? ` · ${trip.carrier_name}` : ""}
                      </div>

                      {/* Kapasiteettipalkit */}
                      <div style={{ display: "flex", gap: "16px" }}>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "11px",
                            color: "#64748b",
                            marginBottom: "2px"
                          }}>
                            <span>Paino</span>
                            <span>{weightUsed} / {maxWeight} kg</span>
                          </div>
                          <div style={{
                            height: "6px",
                            background: "#334155",
                            borderRadius: "3px",
                            overflow: "hidden"
                          }}>
                            <div style={{
                              height: "100%",
                              width: `${Math.min((weightUsed / maxWeight) * 100, 100)}%`,
                              background: getCapacityColor(weightUsed, maxWeight),
                              borderRadius: "3px"
                            }} />
                          </div>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "11px",
                            color: "#64748b",
                            marginBottom: "2px"
                          }}>
                            <span>Lastausmetrit</span>
                            <span>{lmUsed} / {maxLm} lm</span>
                          </div>
                          <div style={{
                            height: "6px",
                            background: "#334155",
                            borderRadius: "3px",
                            overflow: "hidden"
                          }}>
                            <div style={{
                              height: "100%",
                              width: `${Math.min((lmUsed / maxLm) * 100, 100)}%`,
                              background: getCapacityColor(lmUsed, maxLm),
                              borderRadius: "3px"
                            }} />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Lisää-nappi — välittää koko trip-objektin */}
                    <button
                      onClick={() => handleAddToTrip(trip)}
                      disabled={adding === trip.id}
                      style={{
                        background: adding === trip.id ? "#475569" : matchConf.color,
                        color: "#fff",
                        border: "none",
                        padding: "8px 16px",
                        borderRadius: "6px",
                        cursor: adding === trip.id ? "not-allowed" : "pointer",
                        fontSize: "13px",
                        fontWeight: "600",
                        whiteSpace: "nowrap",
                        opacity: adding === trip.id ? 0.7 : 1
                      }}
                    >
                      {adding === trip.id ? "..." : "Lisää →"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Peruuta */}
        <button
          onClick={onClose}
          style={{
            width: "100%",
            background: "transparent",
            color: "#94a3b8",
            border: "1px solid #334155",
            padding: "10px",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "13px"
          }}
        >
          Peruuta
        </button>
      </div>
    </div>
  );
}

export default AddToTripModal;