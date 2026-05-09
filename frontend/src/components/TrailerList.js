import React, { useState, useEffect, useMemo } from "react";
import { useToast } from '../hooks/useToast';

const STATUS_COLORS = { "Vapaa": "#22c55e", "Käytössä": "#f97316", "Huollossa": "#64748b" };

function TrailerList({ onSelect, onCreate, refreshTrigger }) {
  const [trailers, setTrailers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sortKey, setSortKey] = useState("trailer_type");
  const [sortDir, setSortDir] = useState("asc");
  const [openMenu, setOpenMenu] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const toast = useToast();

  useEffect(() => { fetchTrailers(); }, [refreshTrigger]);

  useEffect(() => {
    const handleClick = () => setOpenMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const fetchTrailers = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:5000/api/trailers");
      setTrailers(await res.json());
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleDelete = async (id, e) => {
    if (e) e.stopPropagation();
    setOpenMenu(null);
    const trailer = trailers.find(t => t.id === id);
    if (!window.confirm(`Poistetaanko traileri ${trailer?.plate_number}?`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/trailers/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) { toast.success(`Traileri ${trailer?.plate_number} poistettu`); fetchTrailers(); }
      else toast.error(data.error || "Poisto epäonnistui");
    } catch { toast.error("Poisto epäonnistui"); }
  };

  const handleMenuOpen = (e, id) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setMenuPos({ top: rect.bottom + window.scrollY + 4, left: rect.right + window.scrollX - 140 });
    setOpenMenu(openMenu === id ? null : id);
  };

  const trailerTypes = useMemo(() => [...new Set(trailers.map(t => t.trailer_type))].sort(), [trailers]);

  const filtered = useMemo(() => {
    let result = [...trailers];
    if (typeFilter !== "all") result = result.filter(t => t.trailer_type === typeFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t =>
        (t.plate_number || "").toLowerCase().includes(q) ||
        (t.identifier || "").toLowerCase().includes(q) ||
        (t.trailer_type || "").toLowerCase().includes(q) ||
        (t.leasing_company || "").toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      const av = a[sortKey] || ""; const bv = b[sortKey] || "";
      const dir = sortDir === "asc" ? 1 : -1;
      return av < bv ? -dir : av > bv ? dir : 0;
    });
    return result;
  }, [trailers, search, typeFilter, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };
  const sortIcon = (key) => sortKey !== key ? " ⇅" : sortDir === "asc" ? " ↑" : " ↓";

  const inputStyle = {
    padding: "8px 14px", borderRadius: "6px", border: "1px solid #334155",
    background: "#0f172a", color: "#f1f5f9", fontSize: "13px", outline: "none"
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Trailerit</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {filtered.length} / {trailers.length} traileria
          </div>
        </div>
        <button onClick={onCreate} style={{
          background: "#f97316", color: "#fff", border: "none",
          padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
          fontWeight: "600", fontSize: "14px"
        }}>+ Uusi traileri</button>
      </div>

      <div style={{
        background: "#1e293b", border: "1px solid #334155",
        borderRadius: "10px", padding: "16px", marginBottom: "16px",
        display: "flex", gap: "12px", flexWrap: "wrap"
      }}>
        <input
          type="text" placeholder="🔍 Hae rekisterinumerolla, tunnisteella tai tyypillä..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ ...inputStyle, flex: 1, minWidth: "260px" }}
        />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={inputStyle}>
          <option value="all">Kaikki tyypit</option>
          {trailerTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>Ladataan...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            {trailers.length === 0 ? "Ei trailereita. Luo ensimmäinen yllä." : "Ei hakuosumia."}
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("plate_number")}>Rekisteri{sortIcon("plate_number")}</th>
                <th className="sortable" onClick={() => handleSort("identifier")}>Tunniste{sortIcon("identifier")}</th>
                <th className="sortable" onClick={() => handleSort("trailer_type")}>Tyyppi{sortIcon("trailer_type")}</th>
                <th>Leasingyhtiö</th>
                <th style={{ textAlign: "right" }}>Leasing €/pv</th>
                <th style={{ textAlign: "right" }}>Vuokra €/pv</th>
                <th className="sortable" onClick={() => handleSort("status")}>Status{sortIcon("status")}</th>
                <th style={{ width: "48px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => (
                <tr key={t.id} onClick={() => onSelect(t.id)}>
                  <td style={{ color: "#f97316", fontWeight: "600" }}>{t.plate_number}</td>
                  <td style={{ color: "#cbd5e1" }}>{t.identifier || "—"}</td>
                  <td><span className="tag">{t.trailer_type}</span></td>
                  <td style={{ color: "#94a3b8", fontSize: "13px" }}>{t.leasing_company || "—"}</td>
                  <td style={{ textAlign: "right", fontFamily: "monospace", color: "#cbd5e1" }}>{t.leasing_rate} €</td>
                  <td style={{ textAlign: "right", fontFamily: "monospace", color: "#cbd5e1" }}>{t.rental_rate} €</td>
                  <td>
                    <span className="status-badge" style={{ background: STATUS_COLORS[t.status] || "#475569" }}>
                      {t.status}
                    </span>
                  </td>
                  <td>
                    <button onClick={e => handleMenuOpen(e, t.id)} style={{
                      background: "transparent", color: "#94a3b8", border: "none",
                      cursor: "pointer", padding: "4px 8px", fontSize: "18px",
                      borderRadius: "4px", lineHeight: 1
                    }}>⋮</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {openMenu && (
        <div onClick={e => e.stopPropagation()} style={{
          position: "fixed", top: menuPos.top, left: menuPos.left,
          background: "#0f172a", border: "1px solid #334155", borderRadius: "8px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)", zIndex: 9999,
          minWidth: "160px", overflow: "hidden"
        }}>
          <button onClick={() => { setOpenMenu(null); onSelect(openMenu); }} style={menuItemStyle}>✏️ Muokkaa</button>
          <button onClick={e => handleDelete(openMenu, e)} style={{ ...menuItemStyle, color: "#fca5a5" }}>🗑️ Poista</button>
        </div>
      )}
    </div>
  );
}

const menuItemStyle = {
  display: "block", width: "100%", textAlign: "left",
  padding: "10px 14px", background: "transparent",
  color: "#cbd5e1", border: "none", cursor: "pointer", fontSize: "13px"
};

export default TrailerList;
