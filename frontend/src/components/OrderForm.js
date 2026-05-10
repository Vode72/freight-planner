import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DatePickerField from "./DatePickerField";
import { useToast } from '../hooks/useToast';

const PALLET_PRESETS = {
  "FIN-lava": { width: 1.0, length: 1.2 },
  "EUR-lava": { width: 0.8, length: 1.2 },
  "Teholava": { width: "", length: "" },
  "IBC-kontti": { width: 1.0, length: 1.2, height: 1.15 },
  "Muu": { width: "", length: "" }
};

function OrderForm() {
  const { id: orderId } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    order_reference: "",
    pickup_reference: "",
    goods_description: "",
    incoterms: "",
    consignor_name: "",
    consignor_address: "",
    consignor_country: "",
    consignee_name: "",
    consignee_address: "",
    consignee_country: "",
    loading_point_name: "",
    loading_point_country: "",
    loading_point_zip: "",
    loading_point_city: "",
    unloading_point_name: "",
    unloading_point_country: "",
    unloading_point_zip: "",
    unloading_point_city: "",
    pallet_type: "FIN-lava",
    quantity: 1,
    pallet_width: 1.0,
    pallet_length: 1.2,
    pallet_height: "",
    weight: "",
    stackable: false,
    adr: false,
    tail_lift: false,
    insured: false,
    high_value: false,
    pre_advise: false,
    time_slot_loading: false,
    time_slot_delivery: false,
    min_temperature: "",
    max_temperature: "",
    temperature_monitoring: false,
    required_compartment: "koko kärry",
    loading_instructions: "",
    loading_date: "",
    loading_time_start: "",
    loading_time_end: "",
    delivery_date: "",
    delivery_time_start: "",
    delivery_time_end: ""
  });

  const toast = useToast();
  const [incoterms, setIncoterms] = useState([]);
  const [palletTypes, setPalletTypes] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [activeDropdown, setActiveDropdown] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/incoterms")
      .then(r => r.json()).then(setIncoterms);
    fetch("http://127.0.0.1:5000/api/pallet-types")
      .then(r => r.json()).then(setPalletTypes);
    fetch("http://127.0.0.1:5000/api/customers")
      .then(r => r.json()).then(setCustomers);

    if (orderId) {
      fetch(`http://127.0.0.1:5000/api/orders/${orderId}`)
        .then(r => r.json())
        .then(data => {
          const cleaned = {};
          Object.keys(data).forEach(k => {
            cleaned[k] = data[k] === null ? "" : data[k];
          });
          setForm(prev => ({ ...prev, ...cleaned }));
        });
    } else {
      fetch("http://127.0.0.1:5000/api/next-order-reference")
        .then(r => r.json())
        .then(data => {
          setForm(prev => ({ ...prev, order_reference: data.reference }));
        });
    }
  }, [orderId]);

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handlePalletTypeChange = (type) => {
    const preset = PALLET_PRESETS[type] || {};
    setForm(prev => ({
      ...prev,
      pallet_type: type,
      pallet_width: preset.width !== undefined ? preset.width : prev.pallet_width,
      pallet_length: preset.length !== undefined ? preset.length : prev.pallet_length,
      pallet_height: preset.height !== undefined ? preset.height : prev.pallet_height
    }));
  };

  // ── KORJATTU handleSubmit ────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const url = orderId
        ? `http://127.0.0.1:5000/api/orders/${orderId}`
        : "http://127.0.0.1:5000/api/orders";
      const method = orderId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) throw new Error();

      toast.success(orderId
        ? `Tilaus ${form.order_reference} päivitetty`
        : `Tilaus ${form.order_reference} luotu`
      );
      navigate('/orders');
    } catch {
      toast.error("Tilauksen tallennus epäonnistui");
      setError("Tallennus epäonnistui.");
    } finally {
      setSaving(false);
    }
  };
  // ────────────────────────────────────────────────────────────────────────

  // ===== TYYLIT =====
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

  const grid3 = { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" };
  const grid4 = { display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "12px" };

  const customerAutocomplete = (nameField, addressField, countryField, label, dropdownKey) => {
    const value = form[nameField] || "";
    const filtered = value.length >= 1
      ? customers.filter(c => c.name.toLowerCase().includes(value.toLowerCase())).slice(0, 6)
      : [];
    const isOpen = activeDropdown === dropdownKey && filtered.length > 0;

    return (
      <div style={{ position: "relative" }}>
        <label style={labelStyle}>{label}</label>
        <input
          type="text"
          value={value}
          onChange={(e) => {
            handleChange(nameField, e.target.value);
            setActiveDropdown(dropdownKey);
          }}
          onFocus={() => value && setActiveDropdown(dropdownKey)}
          onBlur={() => setTimeout(() => setActiveDropdown(null), 150)}
          style={inputStyle}
          placeholder="Kirjoita hakemaan..."
        />
        {isOpen && (
          <div style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "#1e293b",
            border: "1px solid #475569",
            borderRadius: "6px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            zIndex: 1000,
            overflow: "hidden",
            marginTop: "2px"
          }}>
            {filtered.map(c => (
              <div
                key={c.id}
                onMouseDown={() => {
                  setForm(prev => ({
                    ...prev,
                    [nameField]: c.name,
                    [addressField]: c.address || "",
                    [countryField]: c.country || ""
                  }));
                  setActiveDropdown(null);
                }}
                style={{
                  padding: "8px 12px",
                  cursor: "pointer",
                  borderBottom: "1px solid #334155",
                  transition: "background 0.1s"
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(249,115,22,0.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <div style={{ color: "#f1f5f9", fontSize: "13px" }}>{c.name}</div>
                <div style={{ color: "#64748b", fontSize: "11px" }}>
                  {[c.zip, c.city, c.country].filter(Boolean).join(" ")}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const checkboxRow = (field, label) => (
    <label style={{
      display: "flex",
      alignItems: "center",
      gap: "8px",
      color: "#cbd5e1",
      fontSize: "13px",
      cursor: "pointer"
    }}>
      <input
        type="checkbox"
        checked={form[field] || false}
        onChange={(e) => handleChange(field, e.target.checked)}
        style={{ width: "16px", height: "16px", cursor: "pointer" }}
      />
      {label}
    </label>
  );

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
    <div>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "20px"
      }}>
        <h2 style={{ color: "#f97316", margin: 0 }}>
          {orderId ? "✏️ Muokkaa Orderia" : "➕ Uusi Order"}
        </h2>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => navigate('/orders')}
            style={{
              background: "transparent",
              color: "#94a3b8",
              border: "1px solid #475569",
              padding: "10px 20px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "14px"
            }}
          >
            Peruuta
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{
              background: "#22c55e",
              color: "#fff",
              border: "none",
              padding: "10px 20px",
              borderRadius: "8px",
              cursor: saving ? "not-allowed" : "pointer",
              fontWeight: "600",
              fontSize: "14px"
            }}
          >
            {saving ? "Tallennetaan..." : "💾 Tallenna"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: "rgba(239,68,68,0.15)",
          border: "1px solid rgba(239,68,68,0.4)",
          borderRadius: "8px",
          padding: "12px 16px",
          color: "#fca5a5",
          marginBottom: "16px"
        }}>
          {error}
        </div>
      )}

      {/* PERUSTIEDOT */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>📋 Perustiedot</h3>
        <div style={grid3}>
          {inputField("order_reference", "Tilausviite")}
          {inputField("pickup_reference", "Noutoviite")}
          <div>
            <label style={labelStyle}>Incoterms</label>
            <select
              value={form.incoterms}
              onChange={(e) => handleChange("incoterms", e.target.value)}
              style={inputStyle}
            >
              <option value="">— Valitse —</option>
              {incoterms.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: "12px" }}>
          {inputField("goods_description", "Tavaran kuvaus")}
        </div>
      </div>

      {/* CONSIGNOR + CONSIGNEE rinnakkain */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div style={sectionStyle}>
          <h3 style={sectionTitle}>📤 Lähettäjä (Consignor)</h3>
          <div style={{ marginBottom: "12px" }}>
            {customerAutocomplete("consignor_name", "consignor_address", "consignor_country", "Nimi", "consignor")}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
            {inputField("consignor_address", "Osoite")}
            {inputField("consignor_country", "Maa")}
          </div>
        </div>
        <div style={sectionStyle}>
          <h3 style={sectionTitle}>📥 Vastaanottaja (Consignee)</h3>
          <div style={{ marginBottom: "12px" }}>
            {customerAutocomplete("consignee_name", "consignee_address", "consignee_country", "Nimi", "consignee")}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
            {inputField("consignee_address", "Osoite")}
            {inputField("consignee_country", "Maa")}
          </div>
        </div>
      </div>

      {/* LOADING POINT + UNLOADING POINT rinnakkain */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div style={sectionStyle}>
          <h3 style={sectionTitle}>📍 Lastauspaikka (Loading Point)</h3>
          <div style={{ marginBottom: "12px" }}>
            {inputField("loading_point_name", "Yritys")}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr 2fr", gap: "12px" }}>
            {inputField("loading_point_country", "Maa")}
            {inputField("loading_point_zip", "Postinro")}
            {inputField("loading_point_city", "Kaupunki")}
          </div>
        </div>
        <div style={sectionStyle}>
          <h3 style={sectionTitle}>🏁 Purkupaikka (Unloading Point)</h3>
          <div style={{ marginBottom: "12px" }}>
            {inputField("unloading_point_name", "Yritys")}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr 2fr", gap: "12px" }}>
            {inputField("unloading_point_country", "Maa")}
            {inputField("unloading_point_zip", "Postinro")}
            {inputField("unloading_point_city", "Kaupunki")}
          </div>
        </div>
      </div>

      {/* TAVARA */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>📦 Tavara ja mitat</h3>
        <div style={grid4}>
          <div>
            <label style={labelStyle}>Kollityyppi</label>
            <select
              value={form.pallet_type}
              onChange={(e) => handlePalletTypeChange(e.target.value)}
              style={inputStyle}
            >
              {palletTypes.map(p => (
                <option key={p.type} value={p.type}>{p.type}</option>
              ))}
            </select>
          </div>
          {inputField("quantity", "Määrä", "number")}
          {inputField("weight", "Paino (kg)", "number")}
          <div>
            <label style={labelStyle}>Osasto</label>
            <select
              value={form.required_compartment}
              onChange={(e) => handleChange("required_compartment", e.target.value)}
              style={inputStyle}
            >
              <option value="koko kärry">Koko kärry</option>
              <option value="etukärry">Etukärry</option>
              <option value="takakärry">Takakärry</option>
            </select>
          </div>
        </div>
        <div style={{ ...grid3, marginTop: "12px" }}>
          {inputField("pallet_width", "Leveys (m)", "number")}
          {inputField("pallet_length", "Pituus (m)", "number")}
          {inputField("pallet_height", "Korkeus (m)", "number")}
        </div>
      </div>

      {/* LÄMPÖTILA */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>🌡️ Lämpötila</h3>
        <div style={grid3}>
          {inputField("min_temperature", "Min °C", "number")}
          {inputField("max_temperature", "Max °C", "number")}
          <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: "8px" }}>
            {checkboxRow("temperature_monitoring", "Lämpötilaseuranta printille")}
          </div>
        </div>
      </div>

      {/* AIKAIKKUNAT */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>🕐 Aikaikkunat</h3>
        <div style={{ marginBottom: "12px", color: "#cbd5e1", fontSize: "13px" }}>
          Lastaus
        </div>
        <div style={grid3}>
          <DatePickerField
            label="Päivä"
            value={form.loading_date}
            onChange={(val) => handleChange("loading_date", val)}
            labelStyle={labelStyle}
            inputStyle={inputStyle}
          />
          {inputField("loading_time_start", "Klo alku", "time")}
          {inputField("loading_time_end", "Klo loppu", "time")}
        </div>
        <div style={{ marginTop: "16px", marginBottom: "12px", color: "#cbd5e1", fontSize: "13px" }}>
          Toimitus
        </div>
        <div style={grid3}>
          <DatePickerField
            label="Päivä"
            value={form.delivery_date}
            onChange={(val) => handleChange("delivery_date", val)}
            labelStyle={labelStyle}
            inputStyle={inputStyle}
          />
          {inputField("delivery_time_start", "Klo alku", "time")}
          {inputField("delivery_time_end", "Klo loppu", "time")}
        </div>
      </div>

      {/* LISÄPALVELUT */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>✅ Lisäpalvelut ja huomiot</h3>
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: "12px"
        }}>
          {checkboxRow("adr", "ADR (vaarallinen aine)")}
          {checkboxRow("tail_lift", "Takalaitanostin")}
          {checkboxRow("stackable", "Pinottava")}
          {checkboxRow("insured", "Vakuutettu")}
          {checkboxRow("high_value", "Korkea arvo/riski")}
          {checkboxRow("pre_advise", "Pre-Advise Delivery")}
          {checkboxRow("time_slot_loading", "Time slot lastaus")}
          {checkboxRow("time_slot_delivery", "Time slot purku")}
        </div>
      </div>

      {/* OHJEET */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>📝 Lastausohjeet</h3>
        <textarea
          value={form.loading_instructions}
          onChange={(e) => handleChange("loading_instructions", e.target.value)}
          rows={3}
          style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          placeholder="Esim. Käytetään liinoja sidonnassa..."
        />
      </div>
    </div>
  );
}

export default OrderForm;