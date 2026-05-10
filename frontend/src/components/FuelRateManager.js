import React, { useState, useEffect } from "react";
import { useToast } from "../hooks/useToast";

const MONTHS_FI = [
  "Tammikuu", "Helmikuu", "Maaliskuu", "Huhtikuu",
  "Toukokuu", "Kesäkuu", "Heinäkuu", "Elokuu",
  "Syyskuu", "Lokakuu", "Marraskuu", "Joulukuu"
];

function monthLabel(from, to) {
  if (!from) return "—";
  const d = new Date(from);
  return `${MONTHS_FI[d.getMonth()]} ${d.getFullYear()}`;
}

function FuelRateManager() {
  const toast = useToast();
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentRate, setCurrentRate] = useState(null);
  const [editId, setEditId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ valid_from: "", valid_to: "", multiplier: "" });

  const today = new Date().toISOString().slice(0, 10);

  useEffect(() => {
    fetchRates();
    fetchCurrent();
  }, []);

  const fetchRates = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:5000/api/fuel-rates");
      setRates(await res.json());
    } catch { toast.error("Lataus epäonnistui"); }
    finally { setLoading(false); }
  };

  const fetchCurrent = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/fuel-rates/current?date=${today}`);
      if (res.ok) setCurrentRate(await res.json());
      else setCurrentRate(null);
    } catch { setCurrentRate(null); }
  };

  const prefillMonth = () => {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1;
    const pad = n => String(n).padStart(2, "0");
    const lastDay = new Date(y, m, 0).getDate();
    setForm({
      valid_from: `${y}-${pad(m)}-01`,
      valid_to: `${y}-${pad(m)}-${lastDay}`,
      multiplier: ""
    });
  };

  const openNew = () => {
    prefillMonth();
    setEditId(null);
    setShowForm(true);
  };

  const openEdit = (rate) => {
    setForm({
      valid_from: rate.valid_from,
      valid_to: rate.valid_to,
      multiplier: String(rate.multiplier)
    });
    setEditId(rate.id);
    setShowForm(true);
  };

  const handleCancel = () => { setShowForm(false); setEditId(null); };

  const handleSave = async () => {
    const mult = parseFloat(form.multiplier);
    if (!form.valid_from || !form.valid_to || isNaN(mult) || mult <= 0) {
      toast.error("Täytä kaikki kentät. Kertoimen on oltava positiivinen luku.");
      return;
    }
    try {
      const url = editId
        ? `http://127.0.0.1:5000/api/fuel-rates/${editId}`
        : "http://127.0.0.1:5000/api/fuel-rates";
      const res = await fetch(url, {
        method: editId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, multiplier: mult })
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.error || "Tallennus epäonnistui"); return; }
      toast.success(editId ? "Kerroin päivitetty" : "Kerroin lisätty");
      setShowForm(false);
      setEditId(null);
      fetchRates();
      fetchCurrent();
    } catch { toast.error("Tallennus epäonnistui"); }
  };

  const handleDelete = async (id, label) => {
    if (!window.confirm(`Poistetaanko kerroin (${label})?`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/fuel-rates/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) { toast.success("Kerroin poistettu"); fetchRates(); fetchCurrent(); }
      else toast.error(data.error || "Poisto epäonnistui");
    } catch { toast.error("Poisto epäonnistui"); }
  };

  const inputStyle = {
    width: "100%", padding: "8px 12px", borderRadius: "6px",
    border: "1px solid #475569", background: "rgba(255,255,255,0.05)",
    color: "#f1f5f9", fontSize: "13px", outline: "none", boxSizing: "border-box"
  };

  const surchargePercent = currentRate ? ((currentRate.multiplier - 1) * 100).toFixed(1) : null;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>⛽ Polttoainekerroin</h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Kuukausittainen kerroin polttoainelisän automaattilaskentaan (koodi 200)
          </div>
        </div>
        <button
          onClick={openNew}
          style={{
            background: "#f97316", color: "#fff", border: "none",
            padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
            fontWeight: "600", fontSize: "14px"
          }}
        >
          + Lisää kuukausi
        </button>
      </div>

      {/* Nykyinen kerroin */}
      <div style={{
        background: currentRate ? "rgba(249,115,22,0.08)" : "rgba(100,116,139,0.1)",
        border: `1px solid ${currentRate ? "rgba(249,115,22,0.3)" : "#334155"}`,
        borderRadius: "12px", padding: "20px", marginBottom: "20px",
        display: "flex", alignItems: "center", gap: "24px"
      }}>
        <div style={{ fontSize: "32px" }}>⛽</div>
        <div style={{ flex: 1 }}>
          <div style={{ color: "#64748b", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px" }}>
            Voimassaoleva kerroin tänään ({today})
          </div>
          {currentRate ? (
            <div style={{ display: "flex", alignItems: "baseline", gap: "16px" }}>
              <div style={{ color: "#f97316", fontSize: "28px", fontWeight: "700", fontFamily: "monospace" }}>
                ×{currentRate.multiplier}
              </div>
              <div style={{ color: "#94a3b8", fontSize: "14px" }}>
                = {surchargePercent}% polttoainelisä rahdista
              </div>
              <div style={{ color: "#64748b", fontSize: "13px" }}>
                {monthLabel(currentRate.valid_from, currentRate.valid_to)}
              </div>
            </div>
          ) : (
            <div style={{ color: "#ef4444", fontSize: "15px" }}>
              Ei voimassaolevaa kerrointa — polttoainelisää ei lisätä automaattisesti
            </div>
          )}
        </div>
        {currentRate && (
          <div style={{
            background: "#0f172a", borderRadius: "8px", padding: "12px 16px",
            fontFamily: "monospace", fontSize: "13px", color: "#94a3b8"
          }}>
            <div>Esim. FREIGHT 3 000 €</div>
            <div style={{ color: "#f97316", marginTop: "4px" }}>
              → Polttoainelisä: {(3000 * (currentRate.multiplier - 1)).toFixed(0)} €
            </div>
          </div>
        )}
      </div>

      {/* Lisäys/muokkaus -lomake */}
      {showForm && (
        <div style={{
          background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "10px", padding: "20px", marginBottom: "20px"
        }}>
          <div style={{
            color: "#f97316", fontSize: "14px", fontWeight: "700",
            textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "16px"
          }}>
            {editId ? "Muokkaa kerrointa" : "Uusi kuukausi"}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", marginBottom: "16px" }}>
            <div>
              <label style={{ display: "block", color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>
                Voimassa alkaen *
              </label>
              <input
                type="date" value={form.valid_from}
                onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ display: "block", color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>
                Voimassa asti *
              </label>
              <input
                type="date" value={form.valid_to}
                onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ display: "block", color: "#94a3b8", fontSize: "12px", marginBottom: "4px" }}>
                Kerroin * (esim. 1.19)
              </label>
              <input
                type="number" step="0.01" min="1" max="2"
                value={form.multiplier}
                onChange={e => setForm(f => ({ ...f, multiplier: e.target.value }))}
                placeholder="1.19"
                style={inputStyle}
              />
              {form.multiplier && !isNaN(parseFloat(form.multiplier)) && parseFloat(form.multiplier) > 1 && (
                <div style={{ color: "#f97316", fontSize: "11px", marginTop: "4px" }}>
                  = {((parseFloat(form.multiplier) - 1) * 100).toFixed(1)}% lisä rahdista
                </div>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={handleSave}
              style={{
                background: "#f97316", color: "#fff", border: "none",
                padding: "10px 24px", borderRadius: "6px", cursor: "pointer",
                fontWeight: "700", fontSize: "13px"
              }}
            >
              💾 {editId ? "Tallenna muutokset" : "Lisää kerroin"}
            </button>
            <button
              onClick={handleCancel}
              style={{
                background: "transparent", color: "#94a3b8",
                border: "1px solid #334155", padding: "10px 16px",
                borderRadius: "6px", cursor: "pointer", fontSize: "13px"
              }}
            >
              Peruuta
            </button>
          </div>
        </div>
      )}

      {/* Kertoimet-taulukko */}
      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>Ladataan...</div>
        ) : rates.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748b" }}>
            Ei kertoimia. Lisää ensimmäinen yllä.
          </div>
        ) : (
          <table className="tms-table">
            <thead>
              <tr>
                <th>Kuukausi</th>
                <th>Voimassa alkaen</th>
                <th>Voimassa asti</th>
                <th style={{ textAlign: "right" }}>Kerroin</th>
                <th style={{ textAlign: "right" }}>Lisä rahdista</th>
                <th style={{ textAlign: "center" }}>Status</th>
                <th style={{ width: "80px" }}></th>
              </tr>
            </thead>
            <tbody>
              {rates.map(r => {
                const isCurrent = r.valid_from <= today && r.valid_to >= today;
                const isPast = r.valid_to < today;
                const pct = ((r.multiplier - 1) * 100).toFixed(1);
                return (
                  <tr key={r.id} style={{ opacity: isPast ? 0.6 : 1 }}>
                    <td style={{ color: "#f1f5f9", fontWeight: isCurrent ? "700" : "400" }}>
                      {monthLabel(r.valid_from, r.valid_to)}
                    </td>
                    <td style={{ color: "#94a3b8", fontFamily: "monospace", fontSize: "13px" }}>
                      {r.valid_from}
                    </td>
                    <td style={{ color: "#94a3b8", fontFamily: "monospace", fontSize: "13px" }}>
                      {r.valid_to}
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "monospace", color: "#f97316", fontWeight: "700", fontSize: "15px" }}>
                      ×{r.multiplier}
                    </td>
                    <td style={{ textAlign: "right", color: "#cbd5e1", fontFamily: "monospace" }}>
                      {pct}%
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {isCurrent ? (
                        <span style={{ background: "#22c55e", color: "#fff", padding: "3px 10px", borderRadius: "10px", fontSize: "11px", fontWeight: "600" }}>
                          Voimassa
                        </span>
                      ) : isPast ? (
                        <span style={{ background: "#334155", color: "#64748b", padding: "3px 10px", borderRadius: "10px", fontSize: "11px" }}>
                          Vanhentunut
                        </span>
                      ) : (
                        <span style={{ background: "#1e3a5f", color: "#93c5fd", padding: "3px 10px", borderRadius: "10px", fontSize: "11px" }}>
                          Tuleva
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => openEdit(r)}
                          style={{
                            background: "transparent", color: "#94a3b8",
                            border: "1px solid #334155", padding: "4px 10px",
                            borderRadius: "4px", cursor: "pointer", fontSize: "12px"
                          }}
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDelete(r.id, monthLabel(r.valid_from, r.valid_to))}
                          style={{
                            background: "transparent", color: "#94a3b8",
                            border: "1px solid #334155", padding: "4px 10px",
                            borderRadius: "4px", cursor: "pointer", fontSize: "12px"
                          }}
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Ohje */}
      <div style={{
        marginTop: "16px", padding: "14px 16px",
        background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)",
        borderRadius: "8px", color: "#64748b", fontSize: "12px", lineHeight: "1.7"
      }}>
        <strong style={{ color: "#93c5fd" }}>Miten automaatti toimii:</strong> Kun TripDetailissa lisätään kulurivi FREIGHT (120),
        järjestelmä hakee tripin lastausajan perusteella voimassaolevan kertoimen ja lisää automaattisesti
        POLTTOAINELISÄ (200) -rivin. Kaava: <span style={{ fontFamily: "monospace", color: "#f97316" }}>FREIGHT × (kerroin − 1.0)</span>.
        Dispatcheri voi muokata tai poistaa rivin tarvittaessa.
      </div>
    </div>
  );
}

export default FuelRateManager;
