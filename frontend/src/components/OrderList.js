import React, { useState, useEffect, useMemo } from "react";

const STATUS_COLORS = {
  "Vapaa": "#3b82f6",
  "Tripillä": "#22c55e"
};

function OrderList({ onSelect, onCreate, refreshTrigger }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const [openMenu, setOpenMenu] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    fetchOrders();
  }, [refreshTrigger]);

  useEffect(() => {
    const handleClick = () => setOpenMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/orders");
      const data = await response.json();
      setOrders(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    setOpenMenu(null);
    if (!window.confirm("Haluatko varmasti poistaa Orderin?")) return;
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/orders/${id}`, {
        method: "DELETE"
      });
      if (response.ok) {
        fetchOrders();
      } else {
        const data = await response.json();
        alert(data.error || "Poisto epäonnistui");
      }
    } catch (err) {
      alert("Virhe poistossa");
    }
  };

  const handleMenuOpen = (e, orderId) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + window.scrollY + 4,
      left: rect.right + window.scrollX - 140
    });
    setOpenMenu(openMenu === orderId ? null : orderId);
  };

  const filteredOrders = useMemo(() => {
    let result = [...orders];
    if (statusFilter !== "all") {
      result = result.filter(o => o.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(o =>
        (o.order_id || "").toLowerCase().includes(q) ||
        (o.consignor_name || "").toLowerCase().includes(q) ||
        (o.consignee_name || "").toLowerCase().includes(q) ||
        (o.goods_description || "").toLowerCase().includes(q) ||
        (o.order_reference || "").toLowerCase().includes(q)
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
  }, [orders, search, statusFilter, sortKey, sortDir]);

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
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Orderit</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {filteredOrders.length} / {orders.length} orderia
          </div>
        </div>
        <button
          onClick={onCreate}
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
          + Uusi Order
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
          placeholder="🔍 Hae ordereista (ID, lähettäjä, vastaanottaja, tavara...)"
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
          <option value="Vapaa">Vapaa</option>
          <option value="Tripillä">Tripillä</option>
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
        ) : filteredOrders.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            {orders.length === 0
              ? "Ei ordereita vielä. Luo ensimmäinen yllä."
              : "Ei hakuosumia."}
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("order_id")}>
                  Order ID{sortIcon("order_id")}
                </th>
                <th className="sortable" onClick={() => handleSort("status")}>
                  Status{sortIcon("status")}
                </th>
                <th>Lähettäjä → Vastaanottaja</th>
                <th>Tavara</th>
                <th className="sortable"
                  onClick={() => handleSort("weight")}
                  style={{ textAlign: "right" }}>
                  Paino{sortIcon("weight")}
                </th>
                <th style={{ textAlign: "right" }}>Lm</th>
                <th>Lavat</th>
                <th style={{ width: "48px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map(o => (
                <tr key={o.id} onClick={() => onSelect(o.id)}>
                  <td style={{ color: "#f97316", fontWeight: "600" }}>
                    {o.order_id}
                  </td>
                  <td>
                    <span
                      className="status-badge"
                      style={{ background: STATUS_COLORS[o.status] || "#475569" }}
                    >
                      {o.status}
                    </span>
                  </td>
                  <td>
                    <div style={{ color: "#cbd5e1" }}>{o.consignor_name || "—"}</div>
                    <div style={{ color: "#64748b", fontSize: "12px" }}>
                      → {o.consignee_name || "—"}
                    </div>
                  </td>
                  <td>{o.goods_description || "—"}</td>
                  <td style={{ textAlign: "right", fontFamily: "monospace" }}>
                    {o.weight} kg
                  </td>
                  <td style={{ textAlign: "right", fontFamily: "monospace" }}>
                    {o.loading_meters}
                  </td>
                  <td>
                    <span className="tag">
                      {o.quantity} × {o.pallet_type || "—"}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={(e) => handleMenuOpen(e, o.id)}
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

      {/* Fixed menu */}
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
              onSelect(openMenu);
            }}
            style={menuItemStyle}
          >
            ✏️ Muokkaa
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

export default OrderList;