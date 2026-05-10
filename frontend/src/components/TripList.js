import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from '../hooks/useToast';

const STATUS_COLORS = {
  "Suunniteltu": "#3b82f6",
  "Vahvistettu": "#eab308",
  "Käynnissä": "#f97316",
  "Toimitettu": "#22c55e",
  "Laskutettu": "#475569"
};

function TripList() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const [openMenu, setOpenMenu] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const toast = useToast();
  const scrollKey = "tms-triplist-scroll";

  // Scroll-position muisti: tallenna poistuessa, palauta mountissa
  useEffect(() => {
    const saved = sessionStorage.getItem(scrollKey);
    if (saved) window.scrollTo(0, parseInt(saved, 10));
    return () => sessionStorage.setItem(scrollKey, String(Math.round(window.scrollY)));
  }, []);

  useEffect(() => {
    fetchTrips();
  }, []);

  useEffect(() => {
    const handleClick = () => setOpenMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/trips");
      const data = await response.json();
      setTrips(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (tripId) => {
    if (!window.confirm('Poistetaanko kuljetus?')) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/trips/${tripId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error();
      toast.success('Kuljetus poistettu');
      fetchTrips(); // tai setTrips(...) tms. — säilytä entinen logiikka
    } catch (err) {
      toast.error('Poisto epäonnistui — tarkista yhteys');
    }
  };

  const handleMenuOpen = (e, tripId) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + window.scrollY + 4,
      left: rect.right + window.scrollX - 140
    });
    setOpenMenu(openMenu === tripId ? null : tripId);
  };

  const filteredTrips = useMemo(() => {
    let result = [...trips];
    if (statusFilter !== "all") {
      result = result.filter(t => t.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t =>
        (t.trip_id || "").toLowerCase().includes(q) ||
        (t.first_pickup_city || "").toLowerCase().includes(q) ||
        (t.trip_end_city || "").toLowerCase().includes(q) ||
        (t.carrier_name || "").toLowerCase().includes(q) ||
        (t.plate_number || "").toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      const av = a[sortKey] || "";
      const bv = b[sortKey] || "";
      const dir = sortDir === "asc" ? 1 : -1;
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return result;
  }, [trips, search, statusFilter, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortIcon = (key) => {
    if (sortKey !== key) return " ⇅";
    return sortDir === "asc" ? " ↑" : " ↓";
  };

  const formatRoute = (t) => {
    const start = t.first_pickup_city
      ? `${t.first_pickup_country || ""} ${t.first_pickup_city}`.trim()
      : "—";
    const end = t.trip_end_city
      ? `${t.trip_end_country || ""} ${t.trip_end_city}`.trim()
      : "—";
    return `${start} → ${end}`;
  };

  const formatDate = (d) => {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("fi-FI", {
      day: "2-digit",
      month: "2-digit"
    });
  };

  return (
    <div>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "24px"
      }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Trips</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {filteredTrips.length} / {trips.length} trippiä
          </div>
        </div>
        <button
          onClick={() => navigate('/trips/new')}
          style={{
            background: "#f97316",
            color: "#fff",
            border: "none",
            padding: "10px 20px",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: "600",
            fontSize: "14px"
          }}
        >
          + Uusi Trip
        </button>
      </div>

      {/* Filtterit */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "10px",
        padding: "16px",
        marginBottom: "16px",
        display: "flex",
        gap: "12px",
        alignItems: "center",
        flexWrap: "wrap"
      }}>
        <input
          type="text"
          placeholder="🔍 Hae tripeistä (Trip ID, kaupunki, kuljetusyhtiö...)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            minWidth: "300px",
            padding: "8px 14px",
            borderRadius: "6px",
            border: "1px solid #334155",
            background: "#0f172a",
            color: "#f1f5f9",
            fontSize: "13px",
            outline: "none"
          }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: "8px 14px",
            borderRadius: "6px",
            border: "1px solid #334155",
            background: "#0f172a",
            color: "#f1f5f9",
            fontSize: "13px",
            outline: "none"
          }}
        >
          <option value="all">Kaikki statukset</option>
          <option value="Suunniteltu">Suunniteltu</option>
          <option value="Vahvistettu">Vahvistettu</option>
          <option value="Käynnissä">Käynnissä</option>
          <option value="Toimitettu">Toimitettu</option>
          <option value="Laskutettu">Laskutettu</option>
        </select>
      </div>

      {/* Taulukko */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "10px",
        overflow: "hidden"
      }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>
            Ladataan...
          </div>
        ) : filteredTrips.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            {trips.length === 0
              ? "Ei trippejä vielä. Luo ensimmäinen yllä."
              : "Ei hakuosumia."}
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("trip_id")}>
                  Trip ID{sortIcon("trip_id")}
                </th>
                <th className="sortable" onClick={() => handleSort("status")}>
                  Status{sortIcon("status")}
                </th>
                <th>Reitti</th>
                <th className="sortable" onClick={() => handleSort("carrier_name")}>
                  Kuljetusyhtiö{sortIcon("carrier_name")}
                </th>
                <th>Traileri</th>
                <th style={{ textAlign: "center" }}>📦</th>
                <th className="sortable" onClick={() => handleSort("delivery_date")}>
                  Toimitus{sortIcon("delivery_date")}
                </th>
                <th style={{ width: "48px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredTrips.map(t => (
                <tr key={t.id} onClick={() => navigate(`/trips/${t.id}/orders`)}>
                  <td style={{ color: "#f97316", fontWeight: "600" }}>
                    {t.trip_id}
                  </td>
                  <td>
                    <span
                      className="status-badge"
                      style={{ background: STATUS_COLORS[t.status] || "#475569" }}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td>{formatRoute(t)}</td>
                  <td>{t.carrier_name || "—"}</td>
                  <td>
                    {t.plate_number
                      ? <span style={{ fontFamily: "monospace" }}>{t.plate_number}</span>
                      : "—"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <span className="tag">{t.order_count || 0}</span>
                  </td>
                  <td>{formatDate(t.delivery_date)}</td>
                  <td style={{ position: "relative" }}>
                    <button
                      onClick={(e) => handleMenuOpen(e, t.id)}
                      style={{
                        background: "transparent",
                        color: "#94a3b8",
                        border: "none",
                        cursor: "pointer",
                        padding: "4px 8px",
                        fontSize: "18px",
                        borderRadius: "4px",
                        lineHeight: 1
                      }}
                    >
                      ⋮
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Fixed menu — renderöidään portaalin tapaan dokumentin juuressa */}
      {openMenu && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: "fixed",
            top: menuPos.top,
            left: menuPos.left,
            background: "#0f172a",
            border: "1px solid #334155",
            borderRadius: "8px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            zIndex: 9999,
            minWidth: "140px",
            overflow: "hidden"
          }}
        >
          <button
            onClick={() => {
              setOpenMenu(null);
              navigate(`/trips/${openMenu}/orders`);
            }}
            style={menuItemStyle}
          >
            👁️ Avaa
          </button>
          <button
            onClick={(e) => handleDelete(openMenu, e)}
            style={{ ...menuItemStyle, color: "#fca5a5" }}
          >
            🗑️ Poista
          </button>
        </div>
      )}
    </div>
  );
}

const menuItemStyle = {
  display: "block",
  width: "100%",
  textAlign: "left",
  padding: "10px 14px",
  background: "transparent",
  color: "#cbd5e1",
  border: "none",
  cursor: "pointer",
  fontSize: "13px"
};

export default TripList;