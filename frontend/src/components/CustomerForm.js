import React, { useState, useEffect } from "react";
import { useToast } from '../hooks/useToast';

const COUNTRIES = [
  "FI", "SE", "NO", "DK", "DE", "NL", "BE", "FR", "PL",
  "EE", "LV", "LT", "AT", "CH", "IT", "ES", "PT", "GB"
];

function CustomerForm({ customerId, onSave, onCancel }) {
  const [form, setForm] = useState({
    name: "",
    business_id: "",
    address: "",
    zip: "",
    city: "",
    country: "FI",
    contact_person: "",
    phone: "",
    email: "",
    customer_type: "molemmat",
    notes: ""
  });

  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (customerId) {
      fetch(`http://127.0.0.1:5000/api/customers/${customerId}`)
        .then(r => r.json())
        .then(data => {
          const cleaned = {};
          Object.keys(data).forEach(k => {
            cleaned[k] = data[k] === null ? "" : data[k];
          });
          setForm(prev => ({ ...prev, ...cleaned }));
        });
    }
  }, [customerId]);

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!form.name.trim()) {
      setError("Asiakkaan nimi on pakollinen.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const url = customerId
        ? `http://127.0.0.1:5000/api/customers/${customerId}`
        : "http://127.0.0.1:5000/api/customers";
      const method = customerId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      if (!res.ok) throw new Error();
      toast.success(customerId
        ? `Asiakas "${form.name}" päivitetty`
        : `Asiakas "${form.name}" luotu`
      );
      onSave();
    } catch {
      toast.error("Tallennus epäonnistui");
      setError("Tallennus epäonnistui.");
    } finally {
      setSaving(false);
    }
  };

  const sectionStyle = {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "10px",
    padding: "20px",
    marginBottom: "16px"
  };

  const sectionTitle = {
    color: "#f97316",
    fontSize: "14px",
    fontWeight: "700",
    marginTop: 0,
    marginBottom: "16px",
    textTransform: "uppercase",
    letterSpacing: "0.5px"
  };

  const labelStyle = {
    display: "block",
    color: "#94a3b8",
    fontSize: "12px",
    marginBottom: "4px"
  };

  const inputStyle = {
    width: "100%",
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #475569",
    background: "rgba(255,255,255,0.05)",
    color: "#f1f5f9",
    fontSize: "13px",
    outline: "none",
    boxSizing: "border-box"
  };

  const grid2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" };
  const grid3 = { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" };

  const inputField = (field, label, type = "text") => (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={form[field] || ""}
        onChange={(e) => handleChange(field, e.target.value)}
        style={inputStyle}
      />
    </div>
  );

  return (
    <div style={{ maxWidth: "900px" }}>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "28px"
      }}>
        <div>
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>
            {customerId ? "Muokkaa asiakasta" : "Uusi asiakas"}
          </h1>
          {customerId && (
            <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
              ID #{customerId}
            </div>
          )}
        </div>
        <button
          onClick={onCancel}
          style={{
            background: "transparent",
            color: "#94a3b8",
            border: "1px solid #334155",
            padding: "8px 16px",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "13px"
          }}
        >
          ← Takaisin
        </button>
      </div>

      <form onSubmit={handleSubmit}>

        {/* Perustiedot */}
        <div style={sectionStyle}>
          <p style={sectionTitle}>Perustiedot</p>
          <div style={{ marginBottom: "12px" }}>
            <label style={{ ...labelStyle, color: "#f97316" }}>Nimi *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              style={{ ...inputStyle, borderColor: form.name ? "#475569" : "#ef4444" }}
              placeholder="Asiakkaan nimi"
            />
          </div>
          <div style={grid3}>
            {inputField("business_id", "Y-tunnus / VAT")}
            <div>
              <label style={labelStyle}>Maa</label>
              <select
                value={form.country}
                onChange={(e) => handleChange("country", e.target.value)}
                style={inputStyle}
              >
                {COUNTRIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Tyyppi</label>
              <select
                value={form.customer_type}
                onChange={(e) => handleChange("customer_type", e.target.value)}
                style={inputStyle}
              >
                <option value="consignor">Lähettäjä (Consignor)</option>
                <option value="consignee">Vastaanottaja (Consignee)</option>
                <option value="molemmat">Molemmat</option>
              </select>
            </div>
          </div>
        </div>

        {/* Osoite */}
        <div style={sectionStyle}>
          <p style={sectionTitle}>Osoite</p>
          <div style={{ marginBottom: "12px" }}>
            {inputField("address", "Katuosoite")}
          </div>
          <div style={grid3}>
            {inputField("zip", "Postinumero")}
            {inputField("city", "Kaupunki")}
          </div>
        </div>

        {/* Yhteyshenkilö */}
        <div style={sectionStyle}>
          <p style={sectionTitle}>Yhteyshenkilö</p>
          <div style={grid3}>
            {inputField("contact_person", "Nimi")}
            {inputField("phone", "Puhelin", "tel")}
            {inputField("email", "Sähköposti", "email")}
          </div>
        </div>

        {/* Muistiinpanot */}
        <div style={sectionStyle}>
          <p style={sectionTitle}>Muistiinpanot</p>
          <textarea
            value={form.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={3}
            placeholder="Vapaamuotoiset muistiinpanot..."
            style={{
              ...inputStyle,
              resize: "vertical",
              fontFamily: "inherit"
            }}
          />
        </div>

        {error && (
          <div style={{
            color: "#fca5a5",
            fontSize: "13px",
            marginBottom: "16px",
            padding: "10px 14px",
            background: "rgba(239,68,68,0.1)",
            borderRadius: "6px",
            border: "1px solid rgba(239,68,68,0.3)"
          }}>
            {error}
          </div>
        )}

        {/* Toimintopainikkeet */}
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            type="submit"
            disabled={saving}
            style={{
              background: saving ? "#475569" : "#f97316",
              color: "#fff",
              border: "none",
              padding: "12px 28px",
              borderRadius: "8px",
              cursor: saving ? "not-allowed" : "pointer",
              fontWeight: "700",
              fontSize: "14px"
            }}
          >
            {saving ? "Tallennetaan..." : customerId ? "Tallenna muutokset" : "Luo asiakas"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            style={{
              background: "transparent",
              color: "#94a3b8",
              border: "1px solid #334155",
              padding: "12px 20px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "14px"
            }}
          >
            Peruuta
          </button>
        </div>
      </form>
    </div>
  );
}

export default CustomerForm;
