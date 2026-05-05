import React, { useState } from "react";

const FERRY_ROUTES = [
  { route: "Ei lauttaa", price: 0 },
  { route: "Helsinki - Travemünde (Finnlines)", price: 1050 },
  { route: "Hanko - Lübeck (Transfennica)", price: 1010 },
  { route: "Hanko - Rostock (Finnlines)", price: 750 },
  { route: "Kotka - Antwerpen (Transfennica)", price: 1800 },
];

const DEFAULT_RATES = {
  domestic_km: 0,
  domestic_rate: 1.45,
  continental_km: 0,
  continental_rate: 1.28,
  fuel_factor: 0.18,
  germany_toll: 0.35,
  benelux_toll: 0.27,
  trailer_rate: 70.0,
  trailer_days: 0,
  trailer_fuel: 0,
  ferry_route: "Ei lauttaa",
  ferry_price: 0,
  other_costs: 0,
  margin_percent: 20,
};

function Row({ label, value, highlight = false }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "8px 0",
      borderBottom: "1px solid rgba(255,255,255,0.04)"
    }}>
      <span style={{
        color: highlight ? "#f1f5f9" : "#94a3b8",
        fontSize: "13px",
        fontWeight: highlight ? "600" : "400"
      }}>
        {label}
      </span>
      <span style={{
        color: highlight ? "#f97316" : "#cbd5e1",
        fontWeight: highlight ? "700" : "400",
        fontSize: highlight ? "15px" : "13px",
        fontFamily: "monospace"
      }}>
        {typeof value === "number" ? value.toFixed(2) : value} €
      </span>
    </div>
  );
}

function InputField({ label, field, value, onChange, step = "1" }) {
  return (
    <div>
      <label style={{
        display: "block",
        color: "#94a3b8",
        fontSize: "12px",
        marginBottom: "4px"
      }}>
        {label}
      </label>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(field, parseFloat(e.target.value) || 0)}
        style={{
          width: "100%",
          padding: "8px 12px",
          borderRadius: "6px",
          border: "1px solid #334155",
          background: "#0f172a",
          color: "#f1f5f9",
          fontSize: "13px",
          outline: "none",
          boxSizing: "border-box"
        }}
      />
    </div>
  );
}

function CostCalculator() {
  const [rates, setRates] = useState(DEFAULT_RATES);
  const [tollOption, setTollOption] = useState("germany");

  const handleChange = (field, value) => {
    setRates(prev => ({ ...prev, [field]: value }));
  };

  const handleFerryChange = (route) => {
    const found = FERRY_ROUTES.find(f => f.route === route);
    setRates(prev => ({
      ...prev,
      ferry_route: route,
      ferry_price: found ? found.price : 0
    }));
  };

  const handleReset = () => {
    setRates(DEFAULT_RATES);
    setTollOption("germany");
  };

  // ===== LASKENTA =====
  const domestic_cost = rates.domestic_km * rates.domestic_rate;
  const continental_cost = rates.continental_km * rates.continental_rate;
  const fuel_cost = rates.continental_km * rates.fuel_factor;

  // Tiemaksu: vain yksi kerroin kerrallaan
  const toll_cost = tollOption === "germany"
    ? rates.continental_km * rates.germany_toll
    : tollOption === "germany_benelux"
    ? rates.continental_km * rates.benelux_toll
    : 0;

  const toll_label = tollOption === "germany"
    ? "Saksan tiemaksu"
    : tollOption === "germany_benelux"
    ? "Saksa + Hollanti tiemaksu"
    : null;

  const trailer_cost = rates.trailer_rate * rates.trailer_days;
  const ferry_cost = rates.ferry_price;
  const fuel_fill_cost = rates.trailer_fuel;
  const other = rates.other_costs;

  const total_costs =
    domestic_cost +
    continental_cost +
    fuel_cost +
    toll_cost +
    trailer_cost +
    ferry_cost +
    fuel_fill_cost +
    other;

  const margin = rates.margin_percent / 100;
  const selling_price = margin < 1 ? total_costs / (1 - margin) : 0;
  const margin_eur = selling_price - total_costs;

  const sectionStyle = {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "10px",
    padding: "20px",
    marginBottom: "16px"
  };

  const sectionTitle = {
    color: "#f97316",
    fontSize: "13px",
    fontWeight: "700",
    marginTop: 0,
    marginBottom: "16px",
    textTransform: "uppercase",
    letterSpacing: "0.5px"
  };

  const tollOptions = [
    {
      value: "none",
      label: "Ei tiemaksua",
      detail: "esim. Ruotsi, Baltia"
    },
    {
      value: "germany",
      label: "Saksa",
      detail: `${rates.germany_toll} €/km — esim. Hamburg, München`
    },
    {
      value: "germany_benelux",
      label: "Saksa + Hollanti",
      detail: `${rates.benelux_toll} €/km — esim. Rotterdam, Antwerpen`
    },
  ];

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
          <h1 style={{ color: "#f1f5f9", margin: 0, fontSize: "24px" }}>
            Kustannuslaskin
          </h1>
          <div style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Tarjous- ja katelaskuri
          </div>
        </div>
        <button
          onClick={handleReset}
          style={{
            background: "transparent",
            color: "#94a3b8",
            border: "1px solid #334155",
            padding: "8px 16px",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "13px"
          }}
        >
          ↺ Nollaa
        </button>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 380px",
        gap: "24px",
        alignItems: "start"
      }}>

        {/* ===== VASEN: SYÖTTEET ===== */}
        <div>

          {/* Ajo */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>🚛 Ajo</h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px"
            }}>
              <InputField
                label="Kotimaan km"
                field="domestic_km"
                value={rates.domestic_km}
                onChange={handleChange}
              />
              <InputField
                label="Kotimaan hinta €/km"
                field="domestic_rate"
                value={rates.domestic_rate}
                onChange={handleChange}
                step="0.01"
              />
              <div style={{
                background: "rgba(249,115,22,0.05)",
                border: "1px solid rgba(249,115,22,0.1)",
                borderRadius: "6px",
                padding: "8px 12px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center"
              }}>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>
                  Kotimaan kustannus
                </div>
                <div style={{
                  color: "#f97316",
                  fontFamily: "monospace",
                  fontSize: "15px",
                  fontWeight: "600"
                }}>
                  {domestic_cost.toFixed(2)} €
                </div>
              </div>
            </div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px",
              marginTop: "12px"
            }}>
              <InputField
                label="Mantereen km"
                field="continental_km"
                value={rates.continental_km}
                onChange={handleChange}
              />
              <InputField
                label="Mantereen hinta €/km"
                field="continental_rate"
                value={rates.continental_rate}
                onChange={handleChange}
                step="0.01"
              />
              <div style={{
                background: "rgba(249,115,22,0.05)",
                border: "1px solid rgba(249,115,22,0.1)",
                borderRadius: "6px",
                padding: "8px 12px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center"
              }}>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>
                  Mantereen kustannus
                </div>
                <div style={{
                  color: "#f97316",
                  fontFamily: "monospace",
                  fontSize: "15px",
                  fontWeight: "600"
                }}>
                  {continental_cost.toFixed(2)} €
                </div>
              </div>
            </div>
          </div>

          {/* Polttoaine */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>⛽ Polttoaine</h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px"
            }}>
              <InputField
                label="Polttoainekerroin (€/km)"
                field="fuel_factor"
                value={rates.fuel_factor}
                onChange={handleChange}
                step="0.01"
              />
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <div style={{ color: "#64748b", fontSize: "12px" }}>
                  Lasketaan mantereen km:stä
                </div>
              </div>
              <div style={{
                background: "rgba(249,115,22,0.05)",
                border: "1px solid rgba(249,115,22,0.1)",
                borderRadius: "6px",
                padding: "8px 12px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center"
              }}>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>
                  Polttoainekustannus
                </div>
                <div style={{
                  color: "#f97316",
                  fontFamily: "monospace",
                  fontSize: "15px",
                  fontWeight: "600"
                }}>
                  {fuel_cost.toFixed(2)} €
                </div>
              </div>
            </div>
          </div>

          {/* Tiemaksu */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>🛣️ Tiemaksu</h3>
            <div style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              marginBottom: "16px"
            }}>
              {tollOptions.map(opt => (
                <label
                  key={opt.value}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "12px 16px",
                    borderRadius: "8px",
                    border: `1px solid ${tollOption === opt.value ? "#f97316" : "#334155"}`,
                    background: tollOption === opt.value
                      ? "rgba(249,115,22,0.08)"
                      : "transparent",
                    cursor: "pointer",
                    transition: "all 0.15s"
                  }}
                >
                  <input
                    type="radio"
                    name="tollOption"
                    value={opt.value}
                    checked={tollOption === opt.value}
                    onChange={() => setTollOption(opt.value)}
                    style={{
                      accentColor: "#f97316",
                      width: "16px",
                      height: "16px",
                      cursor: "pointer"
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{
                      color: tollOption === opt.value ? "#f1f5f9" : "#94a3b8",
                      fontSize: "14px",
                      fontWeight: tollOption === opt.value ? "600" : "400"
                    }}>
                      {opt.label}
                    </div>
                    <div style={{
                      color: "#64748b",
                      fontSize: "11px",
                      marginTop: "2px"
                    }}>
                      {opt.detail}
                    </div>
                  </div>
                  {tollOption === opt.value && opt.value !== "none" && (
                    <div style={{
                      color: "#f97316",
                      fontFamily: "monospace",
                      fontSize: "14px",
                      fontWeight: "600"
                    }}>
                      {toll_cost.toFixed(2)} €
                    </div>
                  )}
                </label>
              ))}
            </div>

            {/* Kertoimet muokattavissa */}
            <div style={{
              background: "rgba(0,0,0,0.2)",
              borderRadius: "6px",
              padding: "12px",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px"
            }}>
              <InputField
                label="Saksan kerroin (€/km)"
                field="germany_toll"
                value={rates.germany_toll}
                onChange={handleChange}
                step="0.01"
              />
              <InputField
                label="Saksa+Hollanti kerroin (€/km)"
                field="benelux_toll"
                value={rates.benelux_toll}
                onChange={handleChange}
                step="0.01"
              />
            </div>
          </div>

          {/* Traileri */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>🚌 Traileri</h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px"
            }}>
              <InputField
                label="Trailerin vuokra €/pv"
                field="trailer_rate"
                value={rates.trailer_rate}
                onChange={handleChange}
                step="0.5"
              />
              <InputField
                label="Traileripäivät"
                field="trailer_days"
                value={rates.trailer_days}
                onChange={handleChange}
              />
              <InputField
                label="Trailerin tankkaus €"
                field="trailer_fuel"
                value={rates.trailer_fuel}
                onChange={handleChange}
              />
            </div>
          </div>

          {/* Lautta */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>⛴️ Lautta</h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px"
            }}>
              <div>
                <label style={{
                  display: "block",
                  color: "#94a3b8",
                  fontSize: "12px",
                  marginBottom: "4px"
                }}>
                  Lauttareitti
                </label>
                <select
                  value={rates.ferry_route}
                  onChange={(e) => handleFerryChange(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #334155",
                    background: "#0f172a",
                    color: "#f1f5f9",
                    fontSize: "13px",
                    outline: "none"
                  }}
                >
                  {FERRY_ROUTES.map(f => (
                    <option key={f.route} value={f.route}>
                      {f.route}{f.price > 0 ? ` — ${f.price} €` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{
                  display: "block",
                  color: "#94a3b8",
                  fontSize: "12px",
                  marginBottom: "4px"
                }}>
                  Lauttahinta € (muokattavissa)
                </label>
                <input
                  type="number"
                  value={rates.ferry_price}
                  onChange={(e) => handleChange("ferry_price", parseFloat(e.target.value) || 0)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #334155",
                    background: "#0f172a",
                    color: "#f1f5f9",
                    fontSize: "13px",
                    outline: "none",
                    boxSizing: "border-box"
                  }}
                />
              </div>
            </div>
          </div>

          {/* Muut */}
          <div style={sectionStyle}>
            <h3 style={sectionTitle}>📋 Muut kulut & Kate</h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px"
            }}>
              <InputField
                label="Muut kulut €"
                field="other_costs"
                value={rates.other_costs}
                onChange={handleChange}
              />
              <InputField
                label="Kateprosentti % (myyntihinnasta)"
                field="margin_percent"
                value={rates.margin_percent}
                onChange={handleChange}
                step="0.5"
              />
            </div>
          </div>
        </div>

        {/* ===== OIKEA: YHTEENVETO ===== */}
        <div style={{ position: "sticky", top: "24px" }}>
          <div style={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "12px",
            padding: "24px"
          }}>
            <h3 style={{
              color: "#f97316",
              fontSize: "14px",
              fontWeight: "700",
              margin: "0 0 20px",
              textTransform: "uppercase",
              letterSpacing: "0.5px"
            }}>
              📊 Laskelma
            </h3>

            {/* Kuluerittely */}
            <div style={{ marginBottom: "16px" }}>
              <div style={{
                color: "#475569",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                marginBottom: "8px"
              }}>
                Kuluerittely
              </div>
              {domestic_cost > 0 && <Row label="Kotimaan ajo" value={domestic_cost} />}
              {continental_cost > 0 && <Row label="Mantereen ajo" value={continental_cost} />}
              {fuel_cost > 0 && <Row label="Polttoainelisä" value={fuel_cost} />}
              {toll_cost > 0 && toll_label && <Row label={toll_label} value={toll_cost} />}
              {trailer_cost > 0 && <Row label="Trailervuokra" value={trailer_cost} />}
              {fuel_fill_cost > 0 && <Row label="Trailerin tankkaus" value={fuel_fill_cost} />}
              {ferry_cost > 0 && <Row label="Lauttakustannus" value={ferry_cost} />}
              {other > 0 && <Row label="Muut kulut" value={other} />}
              {total_costs === 0 && (
                <div style={{ color: "#475569", fontSize: "13px", padding: "8px 0" }}>
                  Syötä arvot vasemmalle...
                </div>
              )}
            </div>

            {/* Yhteensä */}
            <div style={{
              borderTop: "2px solid #334155",
              paddingTop: "12px",
              marginBottom: "16px"
            }}>
              <Row label="KULUT YHTEENSÄ" value={total_costs} highlight />
            </div>

            {/* Kate ja myyntihinta */}
            <div style={{
              background: "rgba(249,115,22,0.05)",
              border: "1px solid rgba(249,115,22,0.15)",
              borderRadius: "8px",
              padding: "16px",
              marginBottom: "16px"
            }}>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "8px"
              }}>
                <span style={{ color: "#94a3b8", fontSize: "13px" }}>Kate %</span>
                <span style={{
                  color: "#f97316",
                  fontFamily: "monospace",
                  fontWeight: "600"
                }}>
                  {rates.margin_percent} %
                </span>
              </div>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "10px"
              }}>
                <span style={{ color: "#94a3b8", fontSize: "13px" }}>Kate €</span>
                <span style={{
                  color: "#22c55e",
                  fontFamily: "monospace",
                  fontWeight: "600"
                }}>
                  {margin_eur.toFixed(2)} €
                </span>
              </div>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                borderTop: "1px solid rgba(249,115,22,0.15)",
                paddingTop: "10px"
              }}>
                <span style={{
                  color: "#f1f5f9",
                  fontSize: "15px",
                  fontWeight: "700"
                }}>
                  MYYNTIHINTA
                </span>
                <span style={{
                  color: "#f97316",
                  fontSize: "22px",
                  fontWeight: "700",
                  fontFamily: "monospace"
                }}>
                  {selling_price.toFixed(2)} €
                </span>
              </div>
            </div>

            <button
              onClick={handleReset}
              style={{
                width: "100%",
                background: "transparent",
                color: "#64748b",
                border: "1px solid #334155",
                padding: "10px",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "13px"
              }}
            >
              ↺ Nollaa laskelma
            </button>
          </div>

          {/* Ohje */}
          <div style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid #334155",
            borderRadius: "8px",
            padding: "16px",
            marginTop: "12px"
          }}>
            <div style={{ color: "#64748b", fontSize: "12px", lineHeight: "1.8" }}>
              <div style={{ color: "#94a3b8", fontWeight: "600", marginBottom: "6px" }}>
                Tiemaksulogiikka:
              </div>
              <div>🇩🇪 Saksa → valitse "Saksa" (0.35 €/km)</div>
              <div>🇳🇱 Hollanti → valitse "Saksa + Hollanti" (0.27 €/km)</div>
              <div>🇸🇪 Ruotsi / Baltia → valitse "Ei tiemaksua"</div>
              <div style={{ marginTop: "8px", color: "#475569" }}>
                Myyntihinta = Kulut ÷ (1 - Kate%)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CostCalculator;