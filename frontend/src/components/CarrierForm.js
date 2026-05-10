import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useToast } from '../hooks/useToast';

const COUNTRIES = ["FI","SE","NO","DK","DE","NL","BE","FR","PL","EE","LV","LT","AT","CH","IT","ES","PT","GB","LU","CZ","SK","HU","PL"];

function CarrierForm() {
  const { id: carrierId } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "", country: "FI", city: "", business_id: "", contact_person: "", phone: ""
  });
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (carrierId) {
      fetch(`http://127.0.0.1:5000/api/carriers`)
        .then(r => r.json())
        .then(data => {
          const found = data.find(c => c.id === carrierId);
          if (found) {
            const cleaned = {};
            Object.keys(found).forEach(k => { cleaned[k] = found[k] === null ? "" : found[k]; });
            setForm(prev => ({ ...prev, ...cleaned }));
          }
        });
    }
  }, [carrierId]);

  const handleChange = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!form.name.trim()) { setError("Nimi on pakollinen."); return; }
    setSaving(true); setError("");
    try {
      const url = carrierId
        ? `http://127.0.0.1:5000/api/carriers/${carrierId}`
        : "http://127.0.0.1:5000/api/carriers";
      const res = await fetch(url, {
        method: carrierId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      if (!res.ok) throw new Error();
      toast.success(carrierId ? `${form.name} päivitetty` : `${form.name} luotu`);
      navigate('/carriers');
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
      <input type={type} value={form[key] || ""} onChange={e => handleChange(key, e.target.value)} style={inputStyle} />
    </div>
  );

  return (
    <div style={{ maxWidth: "700px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>
            {carrierId ? "Muokkaa kuljetusyhtiötä" : "Uusi kuljetusyhtiö"}
          </h1>
        </div>
        <button onClick={() => navigate('/carriers')} style={{
          background: "transparent", color: "#94a3b8", border: "1px solid #334155",
          padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontSize: "13px"
        }}>← Takaisin</button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={sectionStyle}>
          <p style={sectionTitle}>Perustiedot</p>
          <div style={{ marginBottom: "12px" }}>
            <label style={{ ...labelStyle, color: "#f97316" }}>Nimi *</label>
            <input
              value={form.name} onChange={e => handleChange("name", e.target.value)}
              style={{ ...inputStyle, borderColor: form.name ? "#475569" : "#ef4444" }}
              placeholder="Kuljetusyhtiön nimi"
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
            <div>
              <label style={labelStyle}>Maa</label>
              <select value={form.country} onChange={e => handleChange("country", e.target.value)} style={inputStyle}>
                {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {field("city", "Kaupunki")}
            {field("business_id", "Y-tunnus / VAT")}
          </div>
        </div>

        <div style={sectionStyle}>
          <p style={sectionTitle}>Yhteyshenkilö</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {field("contact_person", "Nimi")}
            {field("phone", "Puhelin", "tel")}
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
            {saving ? "Tallennetaan..." : carrierId ? "Tallenna muutokset" : "Luo kuljetusyhtiö"}
          </button>
          <button type="button" onClick={() => navigate('/carriers')} style={{
            background: "transparent", color: "#94a3b8", border: "1px solid #334155",
            padding: "12px 20px", borderRadius: "8px", cursor: "pointer", fontSize: "14px"
          }}>Peruuta</button>
        </div>
      </form>
    </div>
  );
}

export default CarrierForm;
