import React, { useState, useEffect } from "react";
import { useToast } from '../hooks/useToast';

const TRAILER_TYPES = ["Umpikaappi", "Sivuaukeava", "Umpikaappi 2-koneinen", "Pressutrailer", "Megatrailer"];
const STATUSES = ["Vapaa", "Käytössä", "Huollossa"];

function TrailerForm({ trailerId, onSave, onCancel }) {
  const [form, setForm] = useState({
    plate_number: "", identifier: "", trailer_type: "Umpikaappi",
    leasing_company: "TIP Trailer Services", leasing_rate: "", rental_rate: "", status: "Vapaa"
  });
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (trailerId) {
      fetch("http://127.0.0.1:5000/api/trailers")
        .then(r => r.json())
        .then(data => {
          const found = data.find(t => t.id === trailerId);
          if (found) {
            const cleaned = {};
            Object.keys(found).forEach(k => { cleaned[k] = found[k] === null ? "" : found[k]; });
            setForm(prev => ({ ...prev, ...cleaned }));
          }
        });
    }
  }, [trailerId]);

  const handleChange = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!form.plate_number.trim()) { setError("Rekisterinumero on pakollinen."); return; }
    setSaving(true); setError("");
    try {
      const url = trailerId
        ? `http://127.0.0.1:5000/api/trailers/${trailerId}`
        : "http://127.0.0.1:5000/api/trailers";
      const res = await fetch(url, {
        method: trailerId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      if (!res.ok) throw new Error();
      toast.success(trailerId ? `Traileri ${form.plate_number} päivitetty` : `Traileri ${form.plate_number} luotu`);
      onSave();
    } catch {
      toast.error("Tallennus epäonnistui");
      setError("Tallennus epäonnistui.");
    } finally { setSaving(false); }
  };

  const inputStyle = {
    width: "100%", padding: "8px 12px", borderRadius: "6px",
    border: "1px solid #475569", background: "rgba(255,255,255,0.05)",
    color: "#f1f5f9", fontSize: "13px", outline: "none", boxSizing: "border-box"
  };
  const labelStyle = { display: "block", color: "#94a3b8", fontSize: "12px", marginBottom: "4px" };
  const sectionStyle = {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "10px", padding: "20px", marginBottom: "16px"
  };
  const sectionTitle = {
    color: "#f97316", fontSize: "14px", fontWeight: "700",
    marginTop: 0, marginBottom: "16px", textTransform: "uppercase", letterSpacing: "0.5px"
  };

  const field = (key, label, type = "text") => (
    <div>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={form[key] ?? ""} onChange={e => handleChange(key, e.target.value)} style={inputStyle} />
    </div>
  );

  return (
    <div style={{ maxWidth: "700px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>
          {trailerId ? "Muokkaa traileria" : "Uusi traileri"}
        </h1>
        <button onClick={onCancel} style={{
          background: "transparent", color: "#94a3b8", border: "1px solid #334155",
          padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontSize: "13px"
        }}>← Takaisin</button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={sectionStyle}>
          <p style={sectionTitle}>Perustiedot</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", marginBottom: "12px" }}>
            <div>
              <label style={{ ...labelStyle, color: "#f97316" }}>Rekisterinumero *</label>
              <input
                value={form.plate_number} onChange={e => handleChange("plate_number", e.target.value)}
                style={{ ...inputStyle, borderColor: form.plate_number ? "#475569" : "#ef4444" }}
                placeholder="ABC-123"
              />
            </div>
            {field("identifier", "Tunniste")}
            <div>
              <label style={labelStyle}>Tyyppi</label>
              <select value={form.trailer_type} onChange={e => handleChange("trailer_type", e.target.value)} style={inputStyle}>
                {TRAILER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {field("leasing_company", "Leasingyhtiö")}
            <div>
              <label style={labelStyle}>Status</label>
              <select value={form.status} onChange={e => handleChange("status", e.target.value)} style={inputStyle}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </div>

        <div style={sectionStyle}>
          <p style={sectionTitle}>Hinnoittelu</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {field("leasing_rate", "Leasinghinta €/pv (osto)", "number")}
            {field("rental_rate", "Vuokrahinta €/pv (myynti)", "number")}
          </div>
          <div style={{ color: "#64748b", fontSize: "12px", marginTop: "10px" }}>
            Nämä hinnat käytetään automaattiseen trailervuokra-laskentaan (kulukoodit 400/401) kun keikka vahvistetaan.
          </div>
        </div>

        {error && (
          <div style={{
            color: "#fca5a5", fontSize: "13px", marginBottom: "16px",
            padding: "10px 14px", background: "rgba(239,68,68,0.1)",
            borderRadius: "6px", border: "1px solid rgba(239,68,68,0.3)"
          }}>{error}</div>
        )}

        <div style={{ display: "flex", gap: "12px" }}>
          <button type="submit" disabled={saving} style={{
            background: saving ? "#475569" : "#f97316", color: "#fff", border: "none",
            padding: "12px 28px", borderRadius: "8px",
            cursor: saving ? "not-allowed" : "pointer", fontWeight: "700", fontSize: "14px"
          }}>
            {saving ? "Tallennetaan..." : trailerId ? "Tallenna muutokset" : "Luo traileri"}
          </button>
          <button type="button" onClick={onCancel} style={{
            background: "transparent", color: "#94a3b8", border: "1px solid #334155",
            padding: "12px 20px", borderRadius: "8px", cursor: "pointer", fontSize: "14px"
          }}>Peruuta</button>
        </div>
      </form>
    </div>
  );
}

export default TrailerForm;
