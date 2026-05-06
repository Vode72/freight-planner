import React, { useState, useEffect } from "react";
import DatePickerField from "./DatePickerField";

function TripForm({ tripId, onSave, onCancel }) {
  const [form, setForm] = useState({
    first_pickup_country: "",
    first_pickup_zip: "",
    first_pickup_city: "",
    trip_end_country: "",
    trip_end_zip: "",
    trip_end_city: "",
    transport_type: "Suora",
    carrier_id: "",
    trailer_id: "",
    trailer_type: "",
    truck_plate: "",
    loading_date: "",
    loading_time_start: "",
    loading_time_end: "",
    delivery_date: "",
    delivery_time_start: "",
    delivery_time_end: "",
    fixed_delivery_date: false,
    ferry_route: "",
    ferry_departure: "",
    ferry_arrival: "",
    adr: false,
    tail_lift: false,
    temperature_controlled: false,
    loading_instructions: "",
    notes: ""
  });

  const [carriers, setCarriers] = useState([]);
  const [trailers, setTrailers] = useState([]);
  const [transportTypes, setTransportTypes] = useState([]);
  const [ferryRoutes, setFerryRoutes] = useState([]);
  const [trucks, setTrucks] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/carriers")
      .then(r => r.json()).then(setCarriers);
    fetch("http://127.0.0.1:5000/api/trailers")
      .then(r => r.json()).then(setTrailers);
    fetch("http://127.0.0.1:5000/api/transport-types")
      .then(r => r.json()).then(setTransportTypes);
    fetch("http://127.0.0.1:5000/api/ferry-routes")
      .then(r => r.json()).then(setFerryRoutes);
    fetch("http://127.0.0.1:5000/api/trucks")
      .then(r => r.json()).then(setTrucks);
    if (tripId) {
      fetch(`http://127.0.0.1:5000/api/trips/${tripId}`)
        .then(r => r.json())
        .then(data => {
          const cleaned = {};
          Object.keys(data).forEach(k => {
            cleaned[k] = data[k] === null ? "" : data[k];
          });
          setForm(prev => ({ ...prev, ...cleaned }));
        });
    }
  }, [tripId]);

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (field === "carrier_id" && value) {
      fetch(`http://127.0.0.1:5000/api/trucks?carrier_id=${value}`)
        .then(r => r.json())
        .then(data => {
          setTrucks(data);
          setForm(prev => ({ ...prev, truck_plate: "" }));
        });
    }
  };

  const handleTrailerChange = (trailerId) => {
    const trailer = trailers.find(t => t.id === parseInt(trailerId));
    setForm(prev => ({
      ...prev,
      trailer_id: trailerId,
      trailer_type: trailer ? trailer.trailer_type : ""
    }));
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError("");
    try {
      const url = tripId
        ? `http://127.0.0.1:5000/api/trips/${tripId}`
        : "http://127.0.0.1:5000/api/trips";
      const method = tripId ? "PUT" : "POST";
      const body = {
        ...form,
        carrier_id: form.carrier_id ? parseInt(form.carrier_id) : null,
        trailer_id: form.trailer_id ? parseInt(form.trailer_id) : null
      };
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (response.ok) {
        onSave(data.id || tripId);
      } else {
        setError(data.error || "Tallennus epäonnistui");
      }
    } catch (err) {
      setError("Palvelinyhteys epäonnistui");
    } finally {
      setSaving(false);
    }
  };

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

  const grid2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" };
  const grid3 = { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" };

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
          {tripId ? "✏️ Muokkaa Trippiä" : "➕ Uusi Trip"}
        </h2>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={onCancel}
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

      {/* REITTI */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>🗺️ Reitti</h3>
        <div style={{ marginBottom: "12px", color: "#cbd5e1", fontSize: "13px" }}>
          1st Pickup Location (lähtöpaikka)
        </div>
        <div style={grid3}>
          {inputField("first_pickup_country", "Maakoodi (FI)")}
          {inputField("first_pickup_zip", "Postinro")}
          {inputField("first_pickup_city", "Kaupunki")}
        </div>
        <div style={{ marginTop: "16px", marginBottom: "12px", color: "#cbd5e1", fontSize: "13px" }}>
          Trip End Location (määränpää)
        </div>
        <div style={grid3}>
          {inputField("trip_end_country", "Maakoodi (DE)")}
          {inputField("trip_end_zip", "Postinro")}
          {inputField("trip_end_city", "Kaupunki")}
        </div>
        <div style={{ marginTop: "16px" }}>
          <label style={labelStyle}>Kuljetustyyppi</label>
          <select
            value={form.transport_type}
            onChange={(e) => handleChange("transport_type", e.target.value)}
            style={inputStyle}
          >
            {transportTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {/* KALUSTO */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>🚚 Kalusto</h3>
        <div style={grid3}>
          <div>
            <label style={labelStyle}>Kuljetusyhtiö</label>
            <select
              value={form.carrier_id}
              onChange={(e) => handleChange("carrier_id", e.target.value)}
              style={inputStyle}
            >
              <option value="">— Valitse —</option>
              {carriers.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.country} {c.city})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Traileri</label>
            <select
              value={form.trailer_id}
              onChange={(e) => handleTrailerChange(e.target.value)}
              style={inputStyle}
            >
              <option value="">— Valitse —</option>
              {trailers.map(t => (
                <option key={t.id} value={t.id}>
                  {t.plate_number} / {t.identifier} — {t.trailer_type}
                </option>
              ))}
            </select>
          </div>          
          <div>
            <label style={labelStyle}>Vetoauton rekkari</label>
            <select
              value={form.truck_plate || ""}
              onChange={(e) => handleChange("truck_plate", e.target.value)}
              style={inputStyle}
            >
              <option value="">— Valitse vetäjä —</option>
              {trucks.map(t => (
                <option key={t.id} value={t.plate_number}>
                  {t.plate_number} — {t.carrier_name}
                </option>
              ))}
            </select>
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
        <div style={{ marginTop: "12px" }}>
          {checkboxRow("fixed_delivery_date", "Kiinteä toimituspäivä")}
        </div>
      </div>

      {/* LAUTTAYHTEYS */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>⛴️ Lauttayhteys</h3>
        <div>
          <label style={labelStyle}>Reitti</label>
          <select
            value={form.ferry_route}
            onChange={(e) => handleChange("ferry_route", e.target.value)}
            style={inputStyle}
          >
            <option value="">— Ei lauttaa —</option>
            {ferryRoutes.map(f => (
              <option key={f.route} value={f.route}>
                {f.route} ({f.carrier}) — {f.price} €
              </option>
            ))}
          </select>
        </div>
        <div style={{ ...grid2, marginTop: "12px" }}>
          {inputField("ferry_departure", "Lähtö", "datetime-local")}
          {inputField("ferry_arrival", "Saapuminen", "datetime-local")}
        </div>
      </div>

      {/* LISÄPALVELUT */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>✅ Lisäpalvelut</h3>
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "12px"
        }}>
          {checkboxRow("adr", "ADR (vaarallinen aine)")}
          {checkboxRow("tail_lift", "Takalaitanostin")}
          {checkboxRow("temperature_controlled", "Lämpösäädelty")}
        </div>
      </div>

      {/* OHJEET */}
      <div style={sectionStyle}>
        <h3 style={sectionTitle}>📝 Ohjeet ja muistiinpanot</h3>
        <div>
          <label style={labelStyle}>Lastausohjeet</label>
          <textarea
            value={form.loading_instructions}
            onChange={(e) => handleChange("loading_instructions", e.target.value)}
            rows={2}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          />
        </div>
        <div style={{ marginTop: "12px" }}>
          <label style={labelStyle}>Muistiinpanot</label>
          <textarea
            value={form.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={2}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          />
        </div>
      </div>
    </div>
  );
}

export default TripForm;