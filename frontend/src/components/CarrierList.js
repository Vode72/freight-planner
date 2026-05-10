import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from '../hooks/useToast';

const TRUCK_STATUSES = ["Vapaa", "Ajossa", "Huollossa"];

function CarrierList() {
  const navigate = useNavigate();
  const [carriers, setCarriers] = useState([]);
  const [trucks, setTrucks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [openMenu, setOpenMenu] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [truckForm, setTruckForm] = useState(null);
  const [savingTruck, setSavingTruck] = useState(false);
  const toast = useToast();

  useEffect(() => { fetchAll(); }, []);

  useEffect(() => {
    const handleClick = () => setOpenMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [cRes, tRes] = await Promise.all([
        fetch("http://127.0.0.1:5000/api/carriers"),
        fetch("http://127.0.0.1:5000/api/trucks")
      ]);
      setCarriers(await cRes.json());
      setTrucks(await tRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCarrier = async (id, e) => {
    if (e) e.stopPropagation();
    setOpenMenu(null);
    const carrier = carriers.find(c => c.id === id);
    if (!window.confirm(`Poistetaanko "${carrier?.name}"? Myös kaikki sen vetäjät poistetaan.`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/carriers/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        toast.success(`${carrier?.name} poistettu`);
        fetchAll();
        if (expandedId === id) setExpandedId(null);
      } else {
        toast.error(data.error || "Poisto epäonnistui");
      }
    } catch {
      toast.error("Poisto epäonnistui — tarkista yhteys");
    }
  };

  const handleDeleteTruck = async (truckId, carrierId) => {
    const truck = trucks.find(t => t.id === truckId);
    if (!window.confirm(`Poistetaanko vetäjä ${truck?.plate_number}?`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/trucks/${truckId}`, { method: "DELETE" });
      if (res.ok) {
        toast.success(`Vetäjä ${truck?.plate_number} poistettu`);
        fetchAll();
      } else {
        const data = await res.json();
        toast.error(data.error || "Poisto epäonnistui");
      }
    } catch {
      toast.error("Poisto epäonnistui");
    }
  };

  const handleSaveTruck = async () => {
    if (!truckForm?.plate_number?.trim()) {
      toast.error("Rekisterinumero on pakollinen");
      return;
    }
    setSavingTruck(true);
    try {
      const isEdit = !!truckForm.id;
      const url = isEdit
        ? `http://127.0.0.1:5000/api/trucks/${truckForm.id}`
        : "http://127.0.0.1:5000/api/trucks";
      const res = await fetch(url, {
        method: isEdit ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(truckForm)
      });
      if (res.ok) {
        toast.success(isEdit ? "Vetäjä päivitetty" : "Vetäjä lisätty");
        setTruckForm(null);
        fetchAll();
      } else {
        const data = await res.json();
        toast.error(data.error || "Tallennus epäonnistui");
      }
    } catch {
      toast.error("Tallennus epäonnistui");
    } finally {
      setSavingTruck(false);
    }
  };

  const handleMenuOpen = (e, carrierId) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setMenuPos({ top: rect.bottom + window.scrollY + 4, left: rect.right + window.scrollX - 140 });
    setOpenMenu(openMenu === carrierId ? null : carrierId);
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return carriers;
    const q = search.toLowerCase();
    return carriers.filter(c =>
      (c.name || "").toLowerCase().includes(q) ||
      (c.city || "").toLowerCase().includes(q) ||
      (c.country || "").toLowerCase().includes(q)
    );
  }, [carriers, search]);

  const trucksOf = (carrierId) => trucks.filter(t => t.carrier_id === carrierId);

  const inputStyle = {
    padding: "7px 10px", borderRadius: "6px", border: "1px solid #334155",
    background: "#0f172a", color: "#f1f5f9", fontSize: "13px", outline: "none"
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>Kuljetusyhtiöt</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            {filtered.length} / {carriers.length} yhtiötä · {trucks.length} vetäjää
          </div>
        </div>
        <button onClick={() => navigate('/carriers/new')} style={{
          background: "#f97316", color: "#fff", border: "none",
          padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
          fontWeight: "600", fontSize: "14px"
        }}>
          + Uusi yhtiö
        </button>
      </div>

      <div style={{
        background: "#1e293b", border: "1px solid #334155",
        borderRadius: "10px", padding: "16px", marginBottom: "16px"
      }}>
        <input
          type="text"
          placeholder="🔍 Hae nimellä, kaupungilla tai maalla..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }}
        />
      </div>

      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>Ladataan...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            {carriers.length === 0 ? "Ei kuljetusyhtiöitä. Luo ensimmäinen yllä." : "Ei hakuosumia."}
          </div>
        ) : (
          <div>
            {filtered.map((carrier, idx) => {
              const carrierTrucks = trucksOf(carrier.id);
              const isExpanded = expandedId === carrier.id;
              return (
                <div key={carrier.id} style={{ borderBottom: idx < filtered.length - 1 ? "1px solid #334155" : "none" }}>
                  {/* Carrier rivi */}
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : carrier.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: "12px",
                      padding: "14px 20px", cursor: "pointer",
                      background: isExpanded ? "rgba(249,115,22,0.05)" : "transparent",
                      transition: "background 0.15s"
                    }}
                    onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                    onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ color: "#64748b", fontSize: "13px", width: "16px" }}>
                      {isExpanded ? "▼" : "▶"}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span style={{ color: "#f1f5f9", fontWeight: "600", fontSize: "15px" }}>{carrier.name}</span>
                        <span className="tag">{carrier.country}</span>
                        <span style={{ color: "#64748b", fontSize: "13px" }}>{carrier.city}</span>
                      </div>
                      <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
                        {carrier.contact_person || ""}{carrier.phone ? ` · ${carrier.phone}` : ""}
                        {carrier.business_id ? ` · ${carrier.business_id}` : ""}
                      </div>
                    </div>
                    <span style={{
                      background: "#334155", color: "#94a3b8",
                      borderRadius: "12px", padding: "2px 10px", fontSize: "12px"
                    }}>
                      {carrierTrucks.length} vetäjää
                    </span>
                    <button
                      onClick={e => handleMenuOpen(e, carrier.id)}
                      style={{
                        background: "transparent", color: "#94a3b8", border: "none",
                        cursor: "pointer", padding: "4px 8px", fontSize: "18px",
                        borderRadius: "4px", lineHeight: 1
                      }}
                    >⋮</button>
                  </div>

                  {/* Vetäjät (expanded) */}
                  {isExpanded && (
                    <div style={{ background: "#0f172a", borderTop: "1px solid #334155", padding: "16px 20px 16px 48px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                        <span style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                          Vetäjät
                        </span>
                        <button
                          onClick={() => setTruckForm({ plate_number: "", carrier_id: carrier.id, status: "Vapaa" })}
                          style={{
                            background: "#334155", color: "#cbd5e1", border: "none",
                            padding: "5px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px"
                          }}
                        >
                          + Lisää vetäjä
                        </button>
                      </div>

                      {/* Uusi/muokkaa vetäjä -lomake */}
                      {truckForm && truckForm.carrier_id === carrier.id && (
                        <div style={{
                          background: "#1e293b", border: "1px solid #475569",
                          borderRadius: "8px", padding: "12px", marginBottom: "12px",
                          display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap"
                        }}>
                          <div>
                            <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Rekisterinumero *</div>
                            <input
                              type="text"
                              value={truckForm.plate_number}
                              onChange={e => setTruckForm(p => ({ ...p, plate_number: e.target.value }))}
                              style={{ ...inputStyle, width: "140px" }}
                              placeholder="ABC-123"
                              autoFocus
                            />
                          </div>
                          <div>
                            <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Status</div>
                            <select
                              value={truckForm.status}
                              onChange={e => setTruckForm(p => ({ ...p, status: e.target.value }))}
                              style={inputStyle}
                            >
                              {TRUCK_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </div>
                          <button
                            onClick={handleSaveTruck}
                            disabled={savingTruck}
                            style={{
                              background: "#f97316", color: "#fff", border: "none",
                              padding: "8px 16px", borderRadius: "6px", cursor: "pointer",
                              fontSize: "13px", fontWeight: "600"
                            }}
                          >
                            {savingTruck ? "..." : truckForm.id ? "Tallenna" : "Lisää"}
                          </button>
                          <button
                            onClick={() => setTruckForm(null)}
                            style={{
                              background: "transparent", color: "#94a3b8",
                              border: "1px solid #334155", padding: "8px 12px",
                              borderRadius: "6px", cursor: "pointer", fontSize: "13px"
                            }}
                          >
                            Peruuta
                          </button>
                        </div>
                      )}

                      {carrierTrucks.length === 0 ? (
                        <div style={{ color: "#475569", fontSize: "13px" }}>Ei vetäjiä.</div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                          {carrierTrucks.map(truck => (
                            <div key={truck.id} style={{
                              display: "flex", alignItems: "center", gap: "12px",
                              background: "#1e293b", borderRadius: "6px", padding: "8px 12px"
                            }}>
                              <span style={{ color: "#f1f5f9", fontWeight: "600", fontSize: "13px", flex: 1 }}>
                                {truck.plate_number}
                              </span>
                              <span className="status-badge" style={{
                                background: truck.status === "Vapaa" ? "#22c55e"
                                  : truck.status === "Ajossa" ? "#f97316" : "#64748b"
                              }}>
                                {truck.status}
                              </span>
                              <button
                                onClick={() => setTruckForm({ id: truck.id, plate_number: truck.plate_number, carrier_id: carrier.id, status: truck.status })}
                                style={{
                                  background: "transparent", color: "#64748b", border: "none",
                                  cursor: "pointer", fontSize: "13px", padding: "2px 6px"
                                }}
                              >✏️</button>
                              <button
                                onClick={() => handleDeleteTruck(truck.id, carrier.id)}
                                style={{
                                  background: "transparent", color: "#64748b", border: "none",
                                  cursor: "pointer", fontSize: "13px", padding: "2px 6px"
                                }}
                              >🗑️</button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ⋮-menu */}
      {openMenu && (
        <div onClick={e => e.stopPropagation()} style={{
          position: "fixed", top: menuPos.top, left: menuPos.left,
          background: "#0f172a", border: "1px solid #334155", borderRadius: "8px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)", zIndex: 9999,
          minWidth: "160px", overflow: "hidden"
        }}>
          <button onClick={() => { setOpenMenu(null); navigate(`/carriers/${openMenu}/edit`); }} style={menuItemStyle}>
            ✏️ Muokkaa
          </button>
          <button onClick={e => handleDeleteCarrier(openMenu, e)} style={{ ...menuItemStyle, color: "#fca5a5" }}>
            🗑️ Poista
          </button>
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

export default CarrierList;
