import React, { useState, useEffect, useMemo } from "react";
import { useToast } from '../hooks/useToast';

function CustomerList({ onSelect, onCreate, refreshTrigger }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const [openMenu, setOpenMenu] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const toast = useToast();

  useEffect(() => {
    fetchCustomers();
  }, [refreshTrigger]);

  useEffect(() => {
    const handleClick = () => setOpenMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/customers");
      const data = await response.json();
      setCustomers(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, e) => {
    if (e) e.stopPropagation();
    setOpenMenu(null);
    if (!window.confirm("Haluatko varmasti poistaa asiakkaan?")) return;
    const customer = customers.find(c => c.id === id);
    const name = customer?.name || id;
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/customers/${id}`, {
        method: "DELETE"
      });
      if (response.ok) {
        toast.success(`Asiakas "${name}" poistettu`);
        fetchCustomers();
      } else {
        const data = await response.json();
        toast.error(data.error || "Poisto epäonnistui");
      }
    } catch {
      toast.error("Poisto epäonnistui — tarkista yhteys");
    }
  };

  const handleMenuOpen = (e, customerId) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + window.scrollY + 4,
      left: rect.right + window.scrollX - 140
    });
    setOpenMenu(openMenu === customerId ? null : customerId);
  };

  const TYPE_LABELS = {
    consignor: "Lähettäjä",
    consignee: "Vastaanottaja",
    molemmat: "Molemmat"
  };

  const TYPE_COLORS = {
    consignor: "#3b82f6",
    consignee: "#22c55e",
    molemmat: "#a855f7"
  };

  const filteredCustomers = useMemo(() => {
    let result = [...customers];
    if (typeFilter !== "all") {
      result = result.filter(c => c.customer_type === typeFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(c =>
        (c.name || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q) ||
        (c.country || "").toLowerCase().includes(q) ||
        (c.contact_person || "").toLowerCase().includes(q) ||
        (c.business_id || "").toLowerCase().includes(q)
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
  }, [customers, search, sortKey, sortDir]);

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
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Asiakkaat</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {filteredCustomers.length} / {customers.length} asiakasta
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
          + Uusi asiakas
        </button>
      </div>

      {/* Haku */}
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "10px",
        padding: "16px",
        marginBottom: "16px"
      }}>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <input
            type="text"
            placeholder="🔍 Hae nimellä, kaupungilla, maalla tai yhteyshenkilöllä..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
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
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
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
            <option value="all">Kaikki tyypit</option>
            <option value="consignor">Lähettäjä</option>
            <option value="consignee">Vastaanottaja</option>
            <option value="molemmat">Molemmat</option>
          </select>
        </div>
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
        ) : filteredCustomers.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            {customers.length === 0
              ? "Ei asiakkaita vielä. Luo ensimmäinen yllä."
              : "Ei hakuosumia."}
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("name")}>
                  Nimi{sortIcon("name")}
                </th>
                <th className="sortable" onClick={() => handleSort("country")}>
                  Maa{sortIcon("country")}
                </th>
                <th className="sortable" onClick={() => handleSort("city")}>
                  Kaupunki{sortIcon("city")}
                </th>
                <th className="sortable" onClick={() => handleSort("customer_type")}>
                  Tyyppi{sortIcon("customer_type")}
                </th>
                <th>Yhteyshenkilö</th>
                <th>Puhelin</th>
                <th>Sähköposti</th>
                <th style={{ width: "48px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.map(c => (
                <tr key={c.id} onClick={() => onSelect(c.id)}>
                  <td>
                    <div style={{ color: "#f1f5f9", fontWeight: "600" }}>{c.name}</div>
                    {c.business_id && (
                      <div style={{ color: "#64748b", fontSize: "12px" }}>{c.business_id}</div>
                    )}
                  </td>
                  <td>
                    <span className="tag">{c.country || "—"}</span>
                  </td>
                  <td style={{ color: "#cbd5e1" }}>
                    {c.zip ? `${c.zip} ` : ""}{c.city || "—"}
                  </td>
                  <td>
                    <span className="status-badge" style={{
                      background: TYPE_COLORS[c.customer_type] || "#475569"
                    }}>
                      {TYPE_LABELS[c.customer_type] || c.customer_type || "—"}
                    </span>
                  </td>
                  <td style={{ color: "#cbd5e1" }}>{c.contact_person || "—"}</td>
                  <td style={{ color: "#94a3b8", fontSize: "13px" }}>{c.phone || "—"}</td>
                  <td style={{ color: "#94a3b8", fontSize: "13px" }}>{c.email || "—"}</td>
                  <td>
                    <button
                      onClick={(e) => handleMenuOpen(e, c.id)}
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

      {/* Kontekstivaihko */}
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
            minWidth: "160px",
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

export default CustomerList;
